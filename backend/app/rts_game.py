"""Server-authoritative single-board RTS using existing zodiac skills."""
import math
import random
from .rts_combat import RtsCombat, distance, COMBAT_RULES, MAX_LEVEL, xp_next
from .rts_waves import RtsWaves, WAVE_INTERVAL
from .rts_spacing import RtsSpacing
from .zodiac_rules import ZODIAC, HP_SCALE
from .rts_map import EXTENT, STARTS, CELL, OUTDOOR, CHESTS, DOOR_AT, MANOR_FLOORS, KEEPS, resource_points, bounds, blocked, is_door, cell, closed_for
from .squad_items import ITEMS, SLOTS, BAG_SIZE, RtsItems
from .rts_path import find_path, walk_clear, line_clear, nearest_open
from .rts_vehicles import RtsVehicles


CHEST_RESPAWN = 180.  # seconds until an opened chest can be opened again
BUFF_NAMES = dict(heal='체력 회복', speed='이동 속도 증가', attack='공격력 증가', super_jump='슈퍼점프')  # chest buff text shown to players


BELL_HP = 1500.  # shortcut: first guess, tune after playtests


class RtsGame(RtsWaves, RtsCombat, RtsSpacing, RtsItems, RtsVehicles):
    rts = True

    def __init__(self, ids, team_size=1, seed=None):
        if team_size not in (1, 2) or len(ids) != team_size * 2 or len(set(ids)) != len(ids):
            raise ValueError('invalid_rts_roster')
        self.rng = random.Random(seed)
        self.team_size = team_size
        self.elapsed, self.winner, self.reason = 0., None, ''
        self.heroes, self.units, self.minions, self.monsters = {}, {}, {}, {}
        self.bases, self.camps, self.effects, self.bells = [], [], [], []
        self.bombs, self.projectiles, self.items, self.ground = [], [], [], []
        # long whip destroys outdoor wall blocks; 2:2 starts with the 1:1-only manors opened (absent)
        self.opened, self.broken_walls, self.broken_props = closed_for(team_size), [], []
        self.next_id = 0
        self.next_wave = WAVE_INTERVAL
        self.init_vehicles()
        self.chests = {c['id']: dict(c, ready_at=0.) for c in CHESTS if team_size == 1 or c['floor'] not in MANOR_FLOORS}
        for index, pid in enumerate(ids):
            team = index % 2
            x, y = STARTS[index]
            base = self.actor('base-' + pid, 'base', team, x, y, 2200, 1)
            base['owner_id'] = pid
            self.bases.append(base)
            self.camps.append(dict(team=team, owner_id=pid, x=x, y=y, radius=180., resources=resource_points(x, y)))
            dx, dy = (1 if x < EXTENT/2 else -1), (1 if y < EXTENT/2 else -1)
            h = self.actor(pid, 'hero', team, x+dx*180, y+dy*180, ZODIAC['rat']['hp'], 1)
            h.update(owner_id=pid, name='플레이어', character='rat', character_locked=False, level=1, xp=0, streak=0,
                     sequence=-1, input={}, input_at=-1., command='hold', recruited=True,
                     _pending_actions={}, weapon='', armor='', _bag=['']*BAG_SIZE,
                     curse_attack_left=0., curse_skill_left=0., curse_ultimate_left=0.,
                     speed_left=0., rally_left=0., door_cooldown=0., attack_left=0., axe_left=0., order_x=h['x'], order_y=h['y'],
                     super_jump=False, super_jump_left=0., super_jump_duration=0., _leap=None,
                     vehicle='', vehicle_id='', vehicle_left=0., vehicle_hits=0, _vehicle_hit_at=-1.,
                     portal_left=0., portal_out_left=0., portal_x=0., portal_y=0., _portal_from=None, _portal_to=None)
            self.heroes[pid] = self.units[pid] = h
            keep = KEEPS[index]
            bell = self.actor('bell-' + pid, 'bell', team, *keep['bell'], BELL_HP, keep['top'])
            bell['owner_id'] = pid
            self.bells.append(bell)

    def all_targets(self):
        return [*self.units.values(), *self.bases, *self.bells]

    def closed(self, a, x, y):
        cx, cy = cell(x, y)
        return blocked(a['floor'], cx, cy, self.opened) or (a['kind'] != 'hero' and is_door(a['floor'], cx, cy, self.opened))

    def move(self, a, x, y, speed, dt):
        if a['stun_left'] > 0: return
        dx, dy = x-a['x'], y-a['y']
        norm = math.hypot(dx, dy)
        if norm <= 1e-8: return
        step = min(norm, speed * (.55 if a['slow_left'] > 0 else 1) * dt)
        nx, ny = self.avoid_heroes(a, dx/norm, dy/norm, x, y)
        x0, y0, x1, y1 = bounds(a['floor'])
        px, py = a['x'], a['y']
        # Sub-steps no longer than half a cell so dashes cannot tunnel through walls;
        # a blocked step slides along whichever axis is still open.
        count = max(1, math.ceil(step / 20))
        for _ in range(count):
            tx = max(x0, min(x1, px + nx*step/count))
            ty = max(y0, min(y1, py + ny*step/count))
            # A body already inside a wall (old save, teleport edge) may walk out.
            if self.closed(a, px, py) or not self.closed(a, tx, ty): px, py = tx, ty
            elif not self.closed(a, tx, py): px = tx
            elif not self.closed(a, px, ty): py = ty
            else: break
        a.update(x=px, y=py, fx=nx, fy=ny)

    def walk(self, u, gx, gy, speed, dt):
        """move() along an A* route when the straight line is blocked."""
        # Ordered heroes only use a door when the order targets that door; otherwise a
        # blocked goal could resolve to the door cell and teleport them inside.
        doors = u['kind'] == 'hero' and is_door(u['floor'], *cell(gx, gy), self.opened)
        gx, gy = nearest_open(u['floor'], gx, gy, doors, self.opened)
        if walk_clear(u['floor'], u['x'], u['y'], gx, gy, doors, self.opened):
            u['_path'] = []
            return self.move(u, gx, gy, speed, dt)
        old = u.get('_path_goal')
        if (not u.get('_path') or old is None or old[2] != u['floor']
                or math.hypot(old[0]-gx, old[1]-gy) > CELL and self.elapsed >= u.get('_repath_at', 0)):
            u.update(_path=find_path(u['floor'], u['x'], u['y'], gx, gy, doors, self.opened),
                     _path_goal=(gx, gy, u['floor']), _repath_at=self.elapsed + .5)
        path = u['_path']
        # Crowds cannot all stand on a corner waypoint (spacing pushes them apart), so a
        # waypoint is done once the next one is in straight walking line.
        while path and (math.hypot(path[0]['x']-u['x'], path[0]['y']-u['y']) <= 12 or len(path) > 1
                        and walk_clear(u['floor'], u['x'], u['y'], path[1]['x'], path[1]['y'], doors, self.opened)):
            path.pop(0)
        target = path[0] if path else dict(x=gx, y=gy)
        self.move(u, target['x'], target['y'], speed, dt)

    def input(self, pid, data):
        hero = self.heroes[pid]
        if self.reason or data.get('sequence', -1) <= hero['sequence']: return
        super().input(pid, data)
        for action in ('item', 'drop'):  # inventory slot 0..9 to use / drop on the ground
            if 0 <= data.get(action, -1) < SLOTS and hero['hp'] > 0:
                hero['_pending_actions'].setdefault(action, dict(data=dict(data), expires=self.elapsed + .65))
        if data.get('vehicle') and hero['hp'] > 0:
            hero['_pending_actions'].setdefault('vehicle', dict(data=dict(data), expires=self.elapsed + .65))
        if data.get('super_jump') and hero['super_jump'] and hero['hp'] > 0:
            hero['_pending_actions'].setdefault('super_jump', dict(data=dict(data), expires=self.elapsed + .65))
        if data.get('move_x') or data.get('move_y'): hero['command'] = 'hold'
        command = data.get('command', 'none')
        if command not in ('move', 'attack_move', 'focus', 'hold', 'retreat'): return
        ids = data.get('unit_ids', [])
        for uid in set(ids):
            unit = self.units.get(uid)
            if not unit or unit['owner_id'] != pid or unit['hp'] <= 0: continue
            unit.update(command=command,
                        order_x=max(35., min(EXTENT-35, data.get('order_x', unit['x']))),
                        order_y=max(35., min(EXTENT-35, data.get('order_y', unit['y']))), target_id=data.get('target_id', ''))

    def can_hit(self, a, b):
        return a['floor'] == b['floor'] and line_clear(a['floor'], a['x'], a['y'], b['x'], b['y'], self.opened)

    def interact(self, h):
        """Doors move heroes between floors; chests grant one random reward and respawn after CHEST_RESPAWN."""
        door = DOOR_AT.get((h['floor'], *cell(h['x'], h['y'])))
        if door and not self.riding(h) and h['door_cooldown'] <= 0 and is_door(h['floor'], *cell(h['x'], h['y']), self.opened):
            h.update(floor=door['to_floor'], x=door['to_x'], y=door['to_y'], door_cooldown=1.,
                     command='hold', order_x=door['to_x'], order_y=door['to_y'], _path=[])
            self.event(h, 'door', 60.)
        for chest in self.chests.values():
            if (chest['floor'] == h['floor'] and chest['ready_at'] <= self.elapsed
                    and math.hypot(chest['x']-h['x'], chest['y']-h['y']) <= 40):
                chest['ready_at'] = self.elapsed + CHEST_RESPAWN
                reward = self.chest_reward(h)
                if reward in ITEMS: self.give(h, reward)  # a full inventory drops slot 10 on the ground
                if reward == 'heal': h['hp'] = h['max_hp']
                elif reward == 'speed': h['speed_left'] = 20.
                elif reward == 'attack': h['attack_left'] = 30.
                elif reward == 'super_jump':
                    h['super_jump'] = True
                    self.notify(h, '슈퍼점프를 얻었습니다!\nE 옆 칸 또는 R 키로 사용', False)
                self.event(h, 'chest', 60., text=ITEMS[reward]['name'] if reward in ITEMS else BUFF_NAMES[reward])
        self.pickup(h)

    def home(self, pid):
        return next(b for b in self.bases if b['owner_id'] == pid)

    def command_tick(self, unit, dt):
        command = unit.get('command', 'hold')
        enemies = [a for a in self.all_targets() if a['team'] != unit['team'] and a['hp'] > 0]
        focused = next((a for a in enemies if a['id']==unit.get('target_id')), None)
        target = focused or min((a for a in enemies if distance(a,unit)<420 and self.can_hit(unit,a)), key=lambda a:distance(a,unit), default=None)
        hero = unit['kind'] == 'hero'
        if hero and self.riding(unit): target = None  # riders cannot attack
        reach = ZODIAC[unit['character']]['reach'] if hero else 320 if unit['kind'] == 'archer' else 110
        if target and command != 'move' and command != 'retreat':
            if distance(unit,target) - (target['body_radius'] if hero else 0) <= reach and self.can_hit(unit,target):
                if unit['attack_cooldown'] <= 0 and hero:
                    d = distance(unit,target) or 1.
                    unit.update(character_locked=True, fx=(target['x']-unit['x'])/d, fy=(target['y']-unit['y'])/d)
                    self.basic_attack(unit)
                elif unit['attack_cooldown'] <= 0:
                    self.damage(target, 14 if unit['kind']=='guard' else 10, unit)
                    unit['attack_cooldown'] = .7
                    self.start_action(unit,'bow' if unit['kind']=='archer' else 'attack',.3)
                return
            if command in ('attack_move','focus'):
                self.walk(unit,target['x'],target['y'],180,dt)
                return
        if command in ('move','attack_move','retreat'):
            goal = self.home(unit['owner_id']) if command=='retreat' else dict(x=unit['order_x'],y=unit['order_y'])
            if unit['kind']=='hero' and distance(unit,goal)>1: unit['character_locked']=True
            self.walk(unit,goal['x'],goal['y'],self.stats(unit)['speed'] if unit['kind']=='hero' else 180,dt)

    def hero_tick(self, h, dt):
        home = self.home(h['id'])
        if h['hp'] <= 0:
            if h['respawn_left'] <= 1e-8 and home['hp'] > 0:
                h.update(hp=h['max_hp'], x=home['x'], y=home['y'], floor=OUTDOOR, protected=3., input={}, poison_left=0., command='hold',
                         _leap=None, super_jump_left=0.)
            return
        if h['_leap']:  # super jump in flight: straight line over anything, nothing else happens until landing
            x0, y0, x1, y1 = h['_leap']
            t = 1 - h['super_jump_left'] / h['super_jump_duration']
            h.update(x=x0 + (x1-x0)*t, y=y0 + (y1-y0)*t)
            if h['super_jump_left'] <= 0: h.update(_leap=None, order_x=x1, order_y=y1)
            return
        if h['_portal_to']: return self.portal_pull(h)  # bus portal: being drawn in
        data = h['input'] if self.elapsed-h['input_at'] <= .35 else {}
        if h['stun_left'] > 0: return
        dx,dy = data.get('move_x',0),data.get('move_y',0)
        fx0,fy0 = h['fx'],h['fy']
        if h['cast_left'] > 0: dx = dy = 0  # tiger Q/E cast: rooted (no keys, no move orders, no basic attack), can still aim
        elif h['action_kind'] == 'attack' and h['action_left'] > 0: dx = dy = 0  # basic-attack swing: rooted, can still aim
        elif dx or dy:
            norm=max(1.,math.hypot(dx,dy))
            self.move(h,h['x']+dx/norm*1000,h['y']+dy/norm*1000,self.stats(h)['speed'],dt)
            h['character_locked']=True
        else: self.command_tick(h,dt)
        if self.riding(h): self.steer(h,fx0,fy0,dt)
        # Running faces the key direction (move() set it); the mouse only turns the hero when standing,
        # attacking, casting or mid-action, so strikes still go where the player aims. Rides never aim: they keep the driving direction.
        aiming=not self.riding(h) and (not (dx or dy) or data.get('attack') or h['action_left']>0 or 'skill1' in h['_pending_actions'] or 'skill2' in h['_pending_actions'])
        ax,ay=data.get('aim_x',h['x']+h['fx'])-h['x'],data.get('aim_y',h['y']+h['fy'])-h['y']
        norm=math.hypot(ax,ay)
        if norm and aiming: h.update(fx=ax/norm,fy=ay/norm)
        for action, pending in list(h['_pending_actions'].items()):
            if pending['expires']<self.elapsed: del h['_pending_actions'][action]; continue
            if h.get(action+'_cooldown',0)>0 or (action=='dodge' and h['cast_left']>0): continue
            del h['_pending_actions'][action]
            if action=='vehicle': self.vehicle_key(h); continue
            if self.riding(h) and action in ('skill1','skill2','super_jump','dodge','jump'): continue  # riders only drive
            if action in ('skill1','skill2'): self.use_skill(h,action,pending['data'])
            elif action=='item': self.use_item(h,pending['data'])
            elif action=='drop': self.drop_slot(h,pending['data']['drop'])
            elif action=='jump': h.update(jump_left=.65,jump_cooldown=.8)
            elif action=='super_jump': self.leap(h,pending['data'])  # no cooldown: the 0.9s flight is the only wait
            elif action=='dodge':
                self.move(h,h['x']+h['fx']*110,h['y']+h['fy']*110,110,1)
                h.update(dodge_left=.22,dodge_cooldown=3.)
        if data.get('attack') and h['attack_cooldown']<=0 and h['cast_left']<=0 and not self.riding(h):
            h['character_locked']=True
            self.basic_attack(h)
        if h['axe_left']>0 and not self.riding(h): self.axe_swing(h)
        if home['hp']>0 and h['floor']==home['floor'] and distance(h,home)<240: h['hp']=min(h['max_hp'],h['hp']+8*HP_SCALE*dt)
        self.interact(h)

    def tick(self, dt):
        if self.reason: return
        self.elapsed += dt
        for a in self.all_targets():
            for key in ('attack_cooldown','dodge_cooldown','skill1_cooldown','skill2_cooldown','dodge_left','protected','hit_flash','respawn_left','jump_left','jump_cooldown','slow_left','stun_left','action_left','shield_left','cast_left'):
                a[key]=max(0.,a[key]-dt)
            if a['shield_left']<=0: a['shield']=0
            if a['poison_left']>0:
                source=self.heroes.get(a['poison_owner'])
                if source: self.damage(a,a['poison_damage']*min(dt,a['poison_left']),source,'true')
                a['poison_left']=max(0.,a['poison_left']-dt)
        for h in self.heroes.values():
            for key in ('portal_left','portal_out_left','speed_left','rally_left','door_cooldown','attack_left','axe_left','super_jump_left','curse_attack_left','curse_skill_left','curse_ultimate_left'): h[key]=max(0.,h[key]-dt)
            self.hero_tick(h,dt)
            self.vehicle_tick(h,dt)
        self.vehicles_tick()
        for uid,a in list(self.minions.items()):
            if a['hp']<=0: self.minions.pop(uid);self.units.pop(uid)
            elif a['stun_left']<=0:
                if a.get('command') == 'wave': self.wave_tick(a,dt)
                else: self.command_tick(a,dt)
        self.items_tick(dt)
        self.ground_tick()
        for base in self.bases:
            enemies=[a for a in self.units.values() if a['team']!=base['team'] and a['hp']>0 and distance(a,base)<380 and self.can_hit(base,a)]
            if base['hp']>0 and enemies and base['attack_cooldown']<=0:
                self.damage(min(enemies,key=lambda a:distance(a,base)),26,base);base['attack_cooldown']=1.
        self.effects=[e for e in self.effects if e['expires']>self.elapsed]
        self.open_keeps()
        # A fallen base only opens its keep; the match is won by breaking the golden bell on the keep's 2F.
        dead=[team for team in (0,1) if all(b['hp']<=0 for b in self.bells if b['team']==team)]
        if dead:
            self.winner=1-dead[0] if len(dead)==1 else None
            self.reason='bell_destroyed' if len(dead)==1 else 'simultaneous_destruction'
        if not self.reason:
            self.update_waves()
        self.separate_units()

    def open_keeps(self):
        for index, base in enumerate(self.bases):
            door = ('keep', *KEEPS[index]['door'])
            if base['hp'] > 0 or door in self.opened: continue
            self.opened.add(door)
            for h in self.heroes.values():
                self.notify(h, '우리 성문이 무너졌습니다!\n성 2층의 황금종을 지키세요' if h['team'] == base['team']
                            else '적 성문이 무너졌습니다!\n성 안 2층의 황금종을 부수면 승리합니다', True)

    def bot_input(self,pid):
        h=self.heroes[pid]
        enemies=[b for b in self.bases if b['team']!=h['team'] and b['hp']>0]
        if enemies: goal=min(enemies,key=lambda b:distance(h,b))
        else:  # gate down: walk in, climb the stairs, ring the bell to pieces
            index=next((i for i,b in enumerate(self.bells) if b['team']!=h['team'] and b['hp']>0),None)
            if index is None: return
            keep,bell=KEEPS[index],self.bells[index]
            if h['floor']==keep['top']: goal=bell
            else:
                c=keep['stairs'] if h['floor']==keep['floor'] else keep['door']
                goal=dict(x=(c[0]+.5)*CELL,y=(c[1]+.5)*CELL)
        self.input(pid,dict(sequence=h['sequence']+1,command='attack_move',unit_ids=[u['id'] for u in self.units.values() if u['owner_id']==pid and u.get('command') != 'wave'],order_x=goal['x'],order_y=goal['y'],aim_x=goal['x'],aim_y=goal['y']))

    def snapshot(self,pid,code,now):
        h=self.heroes[pid];team=h['team'];stats=self.stats(h)
        return dict(zone='squad',instance_id=code,world_width=EXTENT,world_height=EXTENT,you_id=pid,last_sequence=h['sequence'],server_time=now,rts=True,floor=h['floor'],
                    profile=dict(level=h['level'],xp=h['xp'],xp_next=xp_next(h['level']) if h['level']<MAX_LEVEL else 0,gold=0,role=0,weapon_rank=0,armor_rank=0,attack=stats['attack'],max_hp=stats['health'],equipped_weapon='',equipped_armor='',quest=None,inventory=[]),
                    players=[self.public(a) for a in self.units.values() if a['team']==team],enemies=[self.public(a) for a in self.all_targets() if a['team']!=team],
                    effects=[dict({k:v for k,v in e.items() if k not in ('expires','started')},age=self.elapsed-e['started']) for e in self.effects],hazards=[],projectiles=[],bombs=[],combat_rules=dict(COMBAT_RULES),obstacles=[],party=dict(code=f'squad-{team}',leader_id=pid,members=[]),
                    chests=[dict(id=c['id'],floor=c['floor'],x=c['x'],y=c['y'],ready=c['ready_at']<=self.elapsed) for c in self.chests.values() if c['floor']==h['floor']],
                    squad_items=self.items_public(h['floor']),ground_items=self.ground_public(h['floor']),broken_walls=list(self.broken_walls),broken_props=list(self.broken_props),vehicles=self.vehicles_public(h['floor']),bells=[self.public(b) for b in self.bells])

    def battle_snapshot(self,pid):
        h=self.heroes[pid]
        return dict(rts=True,floor=h['floor'],character=h['character'],character_locked=h['character_locked'],next_wave=0. if self.reason else max(0., self.next_wave-self.elapsed),stats=self.stats(h),characters=[dict(id=k,**v) for k,v in ZODIAC.items()],weapon=h['weapon'],armor=h['armor'],bag=list(h['_bag']),notice=h.get('_notice',''),notice_id=h.get('_notice_id',0),notice_alert=h.get('_notice_alert',False))

"""Server-authoritative single-board RTS using existing zodiac skills."""
import math
import random
from .rts_combat import RtsCombat, distance, COMBAT_RULES
from .rts_waves import RtsWaves, WAVE_INTERVAL
from .rts_spacing import RtsSpacing
from .zodiac_rules import ZODIAC
from .rts_map import EXTENT, STARTS, CELL, OUTDOOR, CHESTS, DOOR_AT, resource_points, bounds, blocked, is_door, cell
from .rts_path import find_path, walk_clear, line_clear


class RtsGame(RtsWaves, RtsCombat, RtsSpacing):
    rts = True

    def __init__(self, ids, team_size=1, seed=None):
        if team_size not in (1, 2) or len(ids) != team_size * 2 or len(set(ids)) != len(ids):
            raise ValueError('invalid_rts_roster')
        self.rng = random.Random(seed)
        self.team_size = team_size
        self.elapsed, self.winner, self.reason = 0., None, ''
        self.heroes, self.units, self.minions, self.monsters = {}, {}, {}, {}
        self.bases, self.camps, self.effects, self.pings = [], [], [], []
        self.bombs, self.projectiles = [], []
        self.next_id = 0
        self.next_wave = WAVE_INTERVAL
        self.rally_points = {}
        self.chests = {c['id']: dict(c, ready_at=0.) for c in CHESTS}
        for index, pid in enumerate(ids):
            team = index % 2
            x, y = STARTS[index]
            base = self.actor('base-' + pid, 'base', team, x, y, 2200, 1)
            base['owner_id'] = pid
            self.bases.append(base)
            self.camps.append(dict(team=team, owner_id=pid, x=x, y=y, radius=180., resources=resource_points(x, y)))
            dx, dy = (1 if x < EXTENT/2 else -1), (1 if y < EXTENT/2 else -1)
            h = self.actor(pid, 'hero', team, x+dx*180, y+dy*180, 160, 1)
            h.update(owner_id=pid, name='플레이어', character='rat', character_locked=False,
                     sequence=-1, input={}, input_at=-1., command='hold', recruited=True,
                     _pending_actions={},
                     speed_left=0., rally_left=0., door_cooldown=0., attack_left=0., order_x=h['x'], order_y=h['y'])
            self.heroes[pid] = self.units[pid] = h

    def all_targets(self):
        return [*self.units.values(), *self.bases]

    def closed(self, a, x, y):
        cx, cy = cell(x, y)
        return blocked(a['floor'], cx, cy) or (a['kind'] != 'hero' and is_door(a['floor'], cx, cy))

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
        doors = u['kind'] == 'hero'
        if walk_clear(u['floor'], u['x'], u['y'], gx, gy, doors):
            u['_path'] = []
            return self.move(u, gx, gy, speed, dt)
        old = u.get('_path_goal')
        if (not u.get('_path') or old is None or old[2] != u['floor']
                or math.hypot(old[0]-gx, old[1]-gy) > CELL and self.elapsed >= u.get('_repath_at', 0)):
            u.update(_path=find_path(u['floor'], u['x'], u['y'], gx, gy, doors),
                     _path_goal=(gx, gy, u['floor']), _repath_at=self.elapsed + .5)
        path = u['_path']
        # Crowds cannot all stand on a corner waypoint (spacing pushes them apart), so a
        # waypoint is done once the next one is in straight walking line.
        while path and (math.hypot(path[0]['x']-u['x'], path[0]['y']-u['y']) <= 12 or len(path) > 1
                        and walk_clear(u['floor'], u['x'], u['y'], path[1]['x'], path[1]['y'], doors)):
            path.pop(0)
        target = path[0] if path else dict(x=gx, y=gy)
        self.move(u, target['x'], target['y'], speed, dt)

    def input(self, pid, data):
        hero = self.heroes[pid]
        if self.reason or data.get('sequence', -1) <= hero['sequence']: return
        super().input(pid, data)
        if data.get('move_x') or data.get('move_y'): hero['command'] = 'hold'
        command = data.get('command', 'none')
        if command not in ('move', 'attack_move', 'focus', 'hold', 'gather', 'retreat'): return
        ids = data.get('unit_ids', [])
        if command == 'gather':
            self.rally_points[pid] = dict(x=max(35., min(EXTENT-35, data.get('order_x', hero['x']))),
                                          y=max(35., min(EXTENT-35, data.get('order_y', hero['y']))))
            ids = [u['id'] for u in self.minions.values() if u['owner_id'] == pid]
            self.pings.append(dict(owner_id=pid, team=hero['team'], x=data.get('order_x', hero['x']), y=data.get('order_y', hero['y']), expires=self.elapsed+5))
        for uid in set(ids):
            unit = self.units.get(uid)
            if not unit or unit['owner_id'] != pid or unit['hp'] <= 0: continue
            unit.update(command='attack_move' if command=='gather' else command,
                        order_x=max(35., min(EXTENT-35, data.get('order_x', unit['x']))),
                        order_y=max(35., min(EXTENT-35, data.get('order_y', unit['y']))), target_id=data.get('target_id', ''))

    def can_hit(self, a, b):
        return a['floor'] == b['floor'] and line_clear(a['floor'], a['x'], a['y'], b['x'], b['y'])

    def interact(self, h):
        """Doors move heroes between floors; chests grant one random 60s-respawning reward."""
        door = DOOR_AT.get((h['floor'], *cell(h['x'], h['y'])))
        if door and h['door_cooldown'] <= 0:
            h.update(floor=door['to_floor'], x=door['to_x'], y=door['to_y'], door_cooldown=1.,
                     command='hold', order_x=door['to_x'], order_y=door['to_y'], _path=[])
            self.event(h, 'door', 60.)
        for chest in self.chests.values():
            if (chest['floor'] == h['floor'] and chest['ready_at'] <= self.elapsed
                    and math.hypot(chest['x']-h['x'], chest['y']-h['y']) <= 40):
                chest['ready_at'] = self.elapsed + 60.
                reward = self.rng.choice(('heal', 'speed', 'attack'))
                if reward == 'heal': h['hp'] = h['max_hp']
                elif reward == 'speed': h['speed_left'] = 20.
                else: h['attack_left'] = 30.
                self.event(h, 'chest', 60., text=reward)

    def home(self, pid):
        return next(b for b in self.bases if b['owner_id'] == pid)

    def command_tick(self, unit, dt):
        command = unit.get('command', 'hold')
        enemies = [a for a in self.all_targets() if a['team'] != unit['team'] and a['hp'] > 0]
        focused = next((a for a in enemies if a['id']==unit.get('target_id')), None)
        target = focused or min((a for a in enemies if distance(a,unit)<420 and self.can_hit(unit,a)), key=lambda a:distance(a,unit), default=None)
        reach = 320 if unit['kind'] in ('archer','hero') else 110
        if target and command != 'move' and command != 'retreat':
            if distance(unit,target) <= reach and self.can_hit(unit,target):
                if unit['attack_cooldown'] <= 0:
                    if unit['kind']=='hero': unit['character_locked']=True
                    self.damage(target, self.stats(unit)['attack'] if unit['kind']=='hero' else 14 if unit['kind']=='guard' else 10, unit)
                    unit['attack_cooldown'] = .7
                    self.start_action(unit,'bow' if unit['kind']=='archer' else 'attack',.3)
                return
            if command in ('attack_move','focus'):
                self.walk(unit,target['x'],target['y'],180,dt)
                return
        if command in ('move','attack_move','retreat'):
            goal = self.home(unit['owner_id']) if command=='retreat' else dict(x=unit['order_x'],y=unit['order_y'])
            if unit['kind']=='hero' and distance(unit,goal)>1: unit['character_locked']=True
            self.walk(unit,goal['x'],goal['y'],245 if unit['kind']=='hero' else 180,dt)

    def hero_tick(self, h, dt):
        home = self.home(h['id'])
        if h['hp'] <= 0:
            if h['respawn_left'] <= 1e-8 and home['hp'] > 0:
                h.update(hp=h['max_hp'], x=home['x'], y=home['y'], floor=OUTDOOR, protected=3., input={}, poison_left=0., command='hold')
            return
        data = h['input'] if self.elapsed-h['input_at'] <= .35 else {}
        if h['stun_left'] > 0: return
        dx,dy = data.get('move_x',0),data.get('move_y',0)
        if dx or dy:
            norm=max(1.,math.hypot(dx,dy))
            self.move(h,h['x']+dx/norm*1000,h['y']+dy/norm*1000,self.stats(h)['speed'],dt)
            h['character_locked']=True
        else: self.command_tick(h,dt)
        ax,ay=data.get('aim_x',h['x']+h['fx'])-h['x'],data.get('aim_y',h['y']+h['fy'])-h['y']
        norm=math.hypot(ax,ay)
        if norm: h.update(fx=ax/norm,fy=ay/norm)
        for action, pending in list(h['_pending_actions'].items()):
            if pending['expires']<self.elapsed: del h['_pending_actions'][action]; continue
            if h.get(action+'_cooldown',0)>0: continue
            del h['_pending_actions'][action]
            if action in ('skill1','skill2'): self.use_skill(h,action,pending['data'])
            elif action=='jump': h.update(jump_left=.65,jump_cooldown=.8)
            elif action=='dodge':
                self.move(h,h['x']+h['fx']*110,h['y']+h['fy']*110,110,1)
                h.update(dodge_left=.22,dodge_cooldown=3.)
        if data.get('attack') and h['attack_cooldown']<=0:
            h['character_locked']=True
            targets=[a for a in self.all_targets() if a['team']!=h['team'] and a['hp']>0 and distance(a,h)<650 and (a['x']-h['x'])*h['fx']+(a['y']-h['y'])*h['fy']>=distance(a,h)*.85 and self.can_hit(h,a)]
            if targets: self.damage(min(targets,key=lambda a:distance(a,h)),self.stats(h)['attack'],h)
            h['attack_cooldown']=.55
            self.start_action(h,'attack',.28)
            self.event(h,'shot',650.)
        if home['hp']>0 and h['floor']==home['floor'] and distance(h,home)<240: h['hp']=min(h['max_hp'],h['hp']+8*dt)
        self.interact(h)

    def tick(self, dt):
        if self.reason: return
        self.elapsed += dt
        for a in self.all_targets():
            for key in ('attack_cooldown','dodge_cooldown','skill1_cooldown','skill2_cooldown','dodge_left','protected','hit_flash','respawn_left','jump_left','jump_cooldown','slow_left','stun_left','action_left','shield_left'):
                a[key]=max(0.,a[key]-dt)
            if a['shield_left']<=0: a['shield']=0
            if a['poison_left']>0:
                source=self.heroes.get(a['poison_owner'])
                if source: self.damage(a,a['poison_damage']*min(dt,a['poison_left']),source)
                a['poison_left']=max(0.,a['poison_left']-dt)
        for h in self.heroes.values():
            for key in ('speed_left','rally_left','door_cooldown','attack_left'): h[key]=max(0.,h[key]-dt)
            self.hero_tick(h,dt)
        for uid,a in list(self.minions.items()):
            if a['hp']<=0: self.minions.pop(uid);self.units.pop(uid)
            elif a['stun_left']<=0:
                if a.get('command') == 'wave': self.wave_tick(a,dt)
                else: self.command_tick(a,dt)
        for base in self.bases:
            enemies=[a for a in self.units.values() if a['team']!=base['team'] and a['hp']>0 and distance(a,base)<380 and self.can_hit(base,a)]
            if base['hp']>0 and enemies and base['attack_cooldown']<=0:
                self.damage(min(enemies,key=lambda a:distance(a,base)),26,base);base['attack_cooldown']=1.
        self.effects=[e for e in self.effects if e['expires']>self.elapsed]
        self.pings=[p for p in self.pings if p['expires']>self.elapsed]
        dead=[team for team in (0,1) if all(b['hp']<=0 for b in self.bases if b['team']==team)]
        if dead:
            self.winner=1-dead[0] if len(dead)==1 else None
            self.reason='headquarters_destroyed' if len(dead)==1 else 'simultaneous_destruction'
        if not self.reason:
            self.update_waves()
        self.separate_units()

    def bot_input(self,pid):
        h=self.heroes[pid]
        enemies=[b for b in self.bases if b['team']!=h['team'] and b['hp']>0]
        if not enemies: return
        goal=min(enemies,key=lambda b:distance(h,b))
        self.input(pid,dict(sequence=h['sequence']+1,command='attack_move',unit_ids=[u['id'] for u in self.units.values() if u['owner_id']==pid and u.get('command') != 'wave'],order_x=goal['x'],order_y=goal['y'],aim_x=goal['x'],aim_y=goal['y']))

    def snapshot(self,pid,code,now):
        h=self.heroes[pid];team=h['team'];stats=self.stats(h)
        return dict(zone='squad',instance_id=code,world_width=EXTENT,world_height=EXTENT,you_id=pid,last_sequence=h['sequence'],server_time=now,rts=True,floor=h['floor'],
                    profile=dict(level=1,xp=0,xp_next=100,gold=0,role=0,weapon_rank=0,armor_rank=0,attack=stats['attack'],max_hp=stats['health'],equipped_weapon='',equipped_armor='',quest=None,inventory=[]),
                    players=[self.public(a) for a in self.units.values() if a['team']==team],enemies=[self.public(a) for a in self.all_targets() if a['team']!=team],
                    effects=[dict({k:v for k,v in e.items() if k not in ('expires','started')},age=self.elapsed-e['started']) for e in self.effects],hazards=[],projectiles=[],bombs=[],combat_rules=dict(COMBAT_RULES),obstacles=[],party=dict(code=f'squad-{team}',leader_id=pid,members=[]),
                    chests=[dict(id=c['id'],floor=c['floor'],x=c['x'],y=c['y'],ready=c['ready_at']<=self.elapsed) for c in self.chests.values() if c['floor']==h['floor']])

    def battle_snapshot(self,pid):
        h=self.heroes[pid]
        return dict(rts=True,floor=h['floor'],character=h['character'],character_locked=h['character_locked'],next_wave=0. if self.reason else max(0., self.next_wave-self.elapsed),characters=[dict(id=k,**v) for k,v in ZODIAC.items()],pings=[{k:v for k,v in p.items() if k!='expires'} for p in self.pings if p['team']==h['team']])

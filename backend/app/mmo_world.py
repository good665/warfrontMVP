"""One-process authoritative 20 Hz world; SQL owns durable character rewards."""
import asyncio
import copy
import logging
import math
import secrets
import threading
import time
import uuid
from fastapi import HTTPException
from .database import SessionLocal
from .models import Player
from .mmo_models import Avatar

OBSTACLES = [dict(x=900., y=350., width=120., height=110.),
             dict(x=650., y=800., width=180., height=90.),
             dict(x=1500., y=500., width=90., height=140.)]


class World:
    def __init__(self, session_factory=SessionLocal, clock=time.monotonic):
        self.factory, self.clock = session_factory, clock
        self.lock = threading.RLock()
        self.last = clock()
        self.actors, self.zones, self.parties = {}, {}, {}
        self.task = None
        self.healthy = True
        self.last_loop_tick = self.clock()

    def avatar(self, db, pid):
        if db.get(Player, pid) is None:
            raise HTTPException(401, 'unauthorized')
        a = db.get(Avatar, pid)
        if a is None:
            a = Avatar(player_id=pid)
            db.add(a)
            db.flush()
        if not a.loadouts:
            selection = dict(weapon=a.weapon, armor=a.armor, helmet=a.helmet)
            a.loadouts = [selection.copy() for _ in range(3)]
            a.active_loadout = 0
        return a

    def stats(self, a):
        powers = {i['id']: i['power'] for i in a.inventory}
        return 18 + 3 * (a.level - 1) + 4 * a.weapon_rank + powers.get(a.weapon, 0), 100 + 10 * (a.level - 1) + 8 * a.armor_rank + powers.get(a.armor, 0) + 8 * a.helmet_rank + powers.get(a.helmet, 0)

    def serialize(self, a):
        attack, hp = self.stats(a)
        quest = self.quest(a)
        return dict(level=a.level, xp=a.xp, xp_next=100*a.level, gold=a.gold, role=a.role,
                    weapon_rank=a.weapon_rank, armor_rank=a.armor_rank, attack=attack, max_hp=hp,
                    equipped_weapon=a.weapon, equipped_armor=a.armor, equipped_helmet=a.helmet,
                    helmet_rank=a.helmet_rank, active_loadout=a.active_loadout, loadouts=copy.deepcopy(a.loadouts),
                    quest=quest,
                    inventory=[dict(i, equipped=i['id'] in (a.weapon, a.armor, a.helmet)) for i in a.inventory])

    def quest(self, a):
        if not a.quest_state:
            target = a.quest_stage * 5
            return dict(id=f'hunt-{a.quest_stage}', kind='hunt', zone='frontier',
                        title=f'적 {target}명 처치', description='어느 지역에서든 적을 처치하세요.',
                        x=0., y=0., progress=min(a.kills, target), target=target,
                        ready=a.kills >= target, reward_xp=50*a.quest_stage,
                        reward_gold=75*a.quest_stage)
        q = a.quest_state.copy()
        if q['kind'] in ('hunt', 'elite') and not q.get('zone'):
            q['zone'] = 'frontier'
            a.quest_state = q.copy()
        q['ready'] = q['progress'] >= q['target']
        return q

    def next_quest(self, stage):
        kind = ('hunt', 'elite', 'explore', 'boss')[(stage-2) % 4]
        cycle = (stage-2)//4
        zone = ('frontier' if cycle % 2 == 0 else 'minefield') if kind == 'explore' else ('ruins' if kind == 'boss' else 'frontier')
        x, y = ((1200., 1800.) if zone == 'frontier' else (3000., 1900.)) if kind == 'explore' else (0., 0.)
        titles = dict(hunt='전선 정리', elite='정예 경비대 격파', explore='안전 경로 정찰', boss='유적 지휘관 토벌')
        descriptions = dict(hunt='아무 지역에서 적 5명을 처치하세요.', elite='경비병(guard) 3명을 처치하세요.',
                            explore='표시된 안전 지점의 100 거리 안으로 이동하세요.', boss='유적에서 지휘관을 처치하세요.')
        return dict(id=f'{kind}-{stage}', kind=kind, zone=zone, title=titles[kind], description=descriptions[kind],
                    x=x, y=y, target=dict(hunt=5, elite=3, explore=1, boss=1)[kind], progress=0,
                    reward_xp=50*stage, reward_gold=75*stage)

    def progress_quest(self, av, kind, zone='', x=0., y=0.):
        if not av.quest_state:
            return
        q = av.quest_state.copy()
        matches = (q['kind'] == 'hunt' and kind in ('raider', 'guard', 'boss') or
                   q['kind'] == 'elite' and kind == 'guard' or
                   q['kind'] == 'boss' and kind == 'boss' and zone == 'ruins' or
                   q['kind'] == 'explore' and kind == 'explore' and q['zone'] == zone and
                   math.hypot(x-q['x'], y-q['y']) <= 100.)
        if matches:
            q['progress'] = min(q['target'], q['progress']+1)
            av.quest_state = q

    def profile(self, pid):
        with self.lock, self.factory() as db:
            a = self.avatar(db, pid)
            result = self.serialize(a)
            db.commit()
            return result

    def party_code(self, pid):
        return next((c for c, members in self.parties.items() if pid in members), '')

    def party_view(self, pid):
        code = self.party_code(pid)
        ids = self.parties.get(code, [])
        with self.factory() as db:
            members = [dict(id=p, name=db.get(Player, p).display_name, level=self.avatar(db, p).level,
                            zone=self.actors.get(p, {}).get('zone', '')) for p in ids]
        return dict(code=code, leader_id=ids[0] if ids else '', members=members)

    def party(self, pid, action, code):
        with self.lock:
            self.profile(pid)
            old = self.party_code(pid)
            if action == 'leave':
                if old:
                    self.parties[old].remove(pid)
                    if not self.parties[old]: del self.parties[old]
            elif action == 'create':
                if old: return self.party_view(pid)
                if len(self.parties) >= 4096: raise HTTPException(503, 'mmo_party_capacity')
                code = secrets.token_hex(3).upper()
                self.parties[code] = [pid]
            elif action == 'join':
                if code == old and old: return self.party_view(pid)
                if old: raise HTTPException(409, 'mmo_already_in_party')
                if code not in self.parties: raise HTTPException(404, 'mmo_party_not_found')
                if len(self.parties[code]) >= 4: raise HTTPException(409, 'mmo_party_full')
                self.parties[code].append(pid)
            # Immediately remove access to a former party's dungeon.
            if pid in self.actors and self.actors[pid]['zone'] == 'ruins':
                actor = self.actors[pid]
                actor.update(key='', zone='', input={}, expires=0.)
                try:
                    self.enter(pid, 'frontier', actor['role'])
                except HTTPException as exc:
                    if exc.detail != 'mmo_zone_full':
                        raise
            return self.party_view(pid)

    def zone(self, key):
        if key not in self.zones:
            if len(self.zones) >= 1024:
                used = {a.get('key') for a in self.actors.values()}
                disposable = [k for k in self.zones if k not in used]
                if not disposable: raise HTTPException(503, 'mmo_instance_capacity')
                del self.zones[min(disposable,key=lambda k:self.zones[k]['seen'])]
            boss = key.startswith('ruins:')
            enemies = []
            for i in range(1 if boss else 8):
                maximum = 650 if boss else 65
                enemies.append(dict(id=f'{key}:{i}', kind='boss' if boss else ('guard' if i%3 == 0 else 'raider'),
                    name='유적 지휘관' if boss else '약탈자', x=650.0+i*250, y=450.0+(i%3)*300,
                    hp=maximum, max_hp=maximum, hit_flash=0., respawn_left=0., cooldown=0., contributors=set(), windup_left=0., windup_duration=1. if boss else .7,
                    attack_radius=150. if boss else 90., attack_x=0., attack_y=0., stagger_left=0.))
            self.zones[key] = dict(enemies=enemies, effects=[], age=0., seen=self.clock())
        return self.zones[key]

    def enter(self, pid, zone, role):
        with self.lock:
            self.advance()
            key = zone if zone != 'ruins' else f'ruins:{self.party_code(pid) or pid}'
            if sum(a['key'] == key and p != pid for p,a in self.actors.items()) >= (4 if zone == 'ruins' else 32):
                raise HTTPException(409, 'mmo_zone_full')
            self.zone(key)
            with self.factory() as db:
                av = self.avatar(db, pid)
                av.role = role
                attack, maximum = self.stats(av)
                if pid not in self.actors:
                    if len(self.actors) >= 4096:
                        disposable = [p for p,a in self.actors.items() if not a.get('key')]
                        if not disposable: raise HTTPException(503, 'mmo_session_capacity')
                        del self.actors[min(disposable,key=lambda p:self.actors[p]['seen'])]
                    self.actors[pid] = dict(id=pid, name=db.get(Player,pid).display_name, role=role, level=av.level,
                        x=300., y=300., fx=1., fy=0., hp=av.hp, max_hp=maximum, attack_cooldown=0.,
                        dodge_cooldown=0., skill1_cooldown=0., skill2_cooldown=0., dodge_left=0., hit_flash=0.,
                        sequence=-1, input={}, expires=0., revive=5. if av.hp <= 0 else 0.)
                actor = self.actors[pid]
                if actor.get('key') != key: actor.update(x=300., y=300., input={}, expires=0.)
                actor.update(zone=zone, key=key, role=role, seen=self.clock(), attack=attack, max_hp=maximum)
                actor['hp'] = min(actor['hp'], maximum)
                db.commit()
            return self.snapshot(pid)

    def state(self, pid):
        with self.lock:
            self.advance()
            self.require(pid)['seen'] = self.clock()
            return self.snapshot(pid)

    def input(self, pid, payload):
        with self.lock:
            self.advance()
            a = self.require(pid)
            a['seen'] = self.clock()
            if payload['sequence'] > a['sequence']:
                a.update(sequence=payload['sequence'], input=payload.copy(), expires=self.clock()+.35)
            return self.snapshot(pid)

    def require(self, pid):
        if pid not in self.actors: raise HTTPException(409, 'mmo_not_in_world')
        return self.actors[pid]

    def leave(self, pid):
        with self.lock:
            self.advance()
            # Keep actor cooldown/HP/sequence tombstone but remove from visible world.
            if pid in self.actors:
                self.actors[pid].update(key='', zone='', input={}, expires=0.)
            return self.profile(pid)

    def effect(self, zone, x, y, text, kind):
        zone['effects'].append(dict(id=uuid.uuid4().hex, x=x, y=y, text=text, kind=kind))
        zone['effects'] = zone['effects'][-30:]

    def reward(self, a, xp, gold):
        a.gold += gold
        a.xp += xp
        while a.level < 50 and a.xp >= 100*a.level:
            a.xp -= 100*a.level
            a.level += 1
        if a.level == 50: a.xp = min(a.xp, 5000)

    def advance(self):
        try:
            self._advance()
        except Exception:
            self.healthy = False
            raise

    def _advance(self):
        now = self.clock()
        # Never advance beyond actual elapsed monotonic time. Drop long stalls.
        elapsed = min(max(0., now-self.last), 2.)
        start = now-elapsed
        self.last = now
        while elapsed >= .000001:
            dt = min(.05, elapsed)
            start += dt
            before = (copy.deepcopy(self.actors), copy.deepcopy(self.zones))
            try:
                self.tick(dt, start)
            except Exception:
                self.actors, self.zones = before
                raise
            elapsed -= dt

    def tick(self, dt, at):
        for pid,a in list(self.actors.items()):
            if a.get('key') and at-a['seen'] > 30:
                a.update(key='', zone='', input={}, expires=0.)
            if at-a.get('seen',at) > 1800:
                del self.actors[pid]
        for key,z in list(self.zones.items()):
            if at-z['seen'] > 1800 and not any(a.get('key') == key for a in self.actors.values()):
                del self.zones[key]
        active = [a for a in self.actors.values() if a.get('key')]
        if not active: return
        with self.factory() as db:
            avatars = {a['id']: self.avatar(db,a['id']) for a in active}
            for a in active:
                av = avatars[a['id']]
                attack, maximum = self.stats(av)
                a.update(max_hp=maximum, attack=attack, level=av.level)
                a['hp'] = min(a['hp'], maximum)
                for field in ('attack_cooldown','dodge_cooldown','skill1_cooldown','skill2_cooldown','dodge_left','hit_flash'):
                    a[field] = max(0., a[field]-dt)
                if a['hp'] <= 0:
                    a['revive'] -= dt
                    if a['revive'] <= 0: a.update(hp=maximum, x=300., y=300., input={})
                    av.hp = a['hp']
                    continue
                inp = a['input'] if at <= a['expires'] else {}
                dx,dy = inp.get('move_x',0),inp.get('move_y',0)
                length = max(1., math.hypot(dx,dy))
                if inp.get('dodge') and a['dodge_cooldown'] <= 0:
                    a.update(dodge_left=.3,dodge_cooldown=3.)
                    a['input']['dodge'] = False
                speed = 550 if a['dodge_left'] > 0 else 220
                self.move(a,dx/length*speed*dt,dy/length*speed*dt)
                self.progress_quest(av, 'explore', a['zone'], a['x'], a['y'])
                ax,ay = inp.get('aim_x',a['x']+1)-a['x'],inp.get('aim_y',a['y'])-a['y']
                norm = math.hypot(ax,ay)
                if norm > .01: a.update(fx=ax/norm,fy=ay/norm)
                z = self.zones[a['key']]
                z['seen'] = at
                if inp.get('skill2') and a['skill2_cooldown'] <= 0:
                    a['skill2_cooldown'] = 10.
                    a['hp'] = min(maximum,a['hp']+35)
                    a['input']['skill2'] = False
                    self.effect(z,a['x'],a['y'],'+35','heal')
                grenade = inp.get('skill1') and a['skill1_cooldown'] <= 0
                shot = inp.get('attack') and a['attack_cooldown'] <= 0
                if grenade: a['skill1_cooldown'] = 6.; a['input']['skill1'] = False
                if shot: a['attack_cooldown'] = .45
                if shot or grenade:
                    for e in z['enemies']:
                        ex,ey = e['x']-a['x'],e['y']-a['y']
                        dist = math.hypot(ex,ey)
                        if e['hp'] <= 0 or dist > (420 if grenade else 600): continue
                        if not grenade and (ex*a['fx']+ey*a['fy'])/max(1.,dist) < .85: continue
                        damage = attack*(2.5 if grenade else 1)
                        e['hp'] = max(0.,e['hp']-damage)
                        e['hit_flash'] = .15
                        e['stagger_left'] = .18
                        e['contributors'].add(a['id'])
                        self.effect(z,e['x'],e['y'],str(int(damage)),'damage')
                        if e['hp'] == 0:
                            e['windup_left'] = 0.
                            e['respawn_left'] = 45. if e['kind']=='boss' else 12.
                            for winner in e['contributors']:
                                if winner not in avatars or self.actors[winner]['key'] != a['key']: continue
                                earned = avatars[winner]
                                self.reward(earned,150 if e['kind']=='boss' else 30,100 if e['kind']=='boss' else 15)
                                earned.kills += 1
                                self.progress_quest(earned, e['kind'], a['zone'])
                                if len(earned.inventory) < 100:
                                    earned.inventory = earned.inventory + [dict(id=uuid.uuid4().hex, name='지휘관 전리품' if e['kind']=='boss' else '전장 회수 장비',slot=('weapon', 'armor', 'helmet')[(earned.kills-1) % 3],power=12 if e['kind']=='boss' else 3+earned.level,rarity=2 if e['kind']=='boss' else 1)]
                                self.effect(z,a['x'],a['y'],'XP + loot','loot')
                        if not grenade: break
                av.hp = a['hp']
            for key,z in self.zones.items():
                occupants = [a for a in active if a['key']==key and a['hp']>0]
                z['age'] += dt
                for e in z['enemies']:
                    e['hit_flash'] = max(0.,e['hit_flash']-dt)
                    if e['hp'] <= 0:
                        e['respawn_left'] = max(0.,e['respawn_left']-dt)
                        if e['respawn_left'] <= 0: e.update(hp=e['max_hp'],contributors=set())
                        continue
                    e['cooldown'] = max(0.,e['cooldown']-dt)
                    e['stagger_left'] = max(0.,e['stagger_left']-dt)
                    if e['windup_left'] > 0:
                        e['windup_left'] = max(0., e['windup_left']-dt)
                        if e['windup_left'] <= .000001:
                            e['windup_left'] = 0.
                            e['cooldown'] = 1.
                            self.effect(z,e['attack_x'],e['attack_y'],'','enemy_attack')
                            for victim in occupants:
                                if math.hypot(victim['x']-e['attack_x'],victim['y']-e['attack_y']) <= e['attack_radius']:
                                    self.hurt(victim,20 if e['kind']=='boss' else 8)
                        continue
                    if e['stagger_left'] > 0 or not occupants: continue
                    target = min(occupants,key=lambda a:math.hypot(a['x']-e['x'],a['y']-e['y']))
                    dx,dy = target['x']-e['x'],target['y']-e['y']; dist=math.hypot(dx,dy)
                    if dist <= 55 and e['cooldown'] <= 0:
                        e.update(windup_left=e['windup_duration'], attack_x=target['x'], attack_y=target['y'])
                    elif 45 < dist < 700:
                        self.move(e,dx/dist*90*dt,dy/dist*90*dt)
                if key == 'minefield':
                    for a in occupants:
                        for h in self.hazards(z):
                            if math.hypot(a['x']-h['x'],a['y']-h['y']) <= h['radius']: self.hurt(a,14*dt)
            for a in active: avatars[a['id']].hp = a['hp']
            db.commit()

    def hurt(self,a,damage):
        if a['dodge_left']>0 or a['hp']<=0: return
        self.effect(self.zones[a['key']], a['x'], a['y'], str(int(damage)), 'player_damage')
        a['hp']=max(0.,a['hp']-damage); a['hit_flash']=.15
        if a['hp']<=0: a.update(revive=5.,input={})

    def move(self, actor, dx, dy):
        # Rectangles use their top-left world coordinate, with an 18-unit actor radius.
        def blocked(x,y):
            return any(o['x']-18 < x < o['x']+o['width']+18 and
                       o['y']-18 < y < o['y']+o['height']+18 for o in OBSTACLES)
        x=min(3550.,max(50.,actor['x']+dx))
        if not blocked(x,actor['y']): actor['x']=x
        y=min(2350.,max(50.,actor['y']+dy))
        if not blocked(actor['x'],y): actor['y']=y

    def hazards(self,z):
        return [dict(x=900.+i*650,y=700.+(i%2)*600,radius=35.+(z['age']%8)*12,age=z['age']%8) for i in range(4)]

    def snapshot(self,pid):
        a=self.require(pid)
        if not a.get('key'): raise HTTPException(409,'mmo_not_in_world')
        z=self.zones[a['key']]
        fields=('id','name','role','level','x','y','fx','fy','hp','max_hp','attack_cooldown','dodge_cooldown','skill1_cooldown','skill2_cooldown','dodge_left','hit_flash')
        players=[dict({f:p[f] for f in fields},party_code=self.party_code(p['id'])) for p in self.actors.values() if p.get('key')==a['key']]
        return dict(zone=a['zone'],instance_id=a['key'],world_width=3600.,world_height=2400.,you_id=pid,last_sequence=a['sequence'],server_time=self.clock(),
            profile=self.profile(pid),players=players,enemies=[{k:v for k,v in e.items() if k not in ('contributors','cooldown')} for e in z['enemies']],
            hazards=self.hazards(z) if a['zone']=='minefield' else [],effects=z['effects'][:],obstacles=[o.copy() for o in OBSTACLES],party=self.party_view(pid))

    def claim(self,pid):
        with self.lock,self.factory() as db:
            a=self.avatar(db,pid)
            q = self.quest(a)
            if not q['ready']: raise HTTPException(409,'mmo_quest_not_ready')
            self.reward(a,q['reward_xp'],q['reward_gold'])
            a.quest_stage += 1
            a.quest_state = self.next_quest(a.quest_stage)
            db.commit()
            return self.serialize(a)

    def validate_loadout(self, index):
        if type(index) is not int or not 0 <= index <= 2:
            raise HTTPException(422, 'mmo_invalid_loadout')

    def gear_hp(self, pid, a):
        attack, maximum = self.stats(a)
        actor = self.actors.get(pid)
        a.hp = min(actor['hp'] if actor else a.hp, maximum)
        return dict(attack=attack, max_hp=maximum, hp=a.hp)

    def loadout(self, pid, index):
        self.validate_loadout(index)
        with self.lock, self.factory() as db:
            a = self.avatar(db, pid)
            sets = copy.deepcopy(a.loadouts)
            sets[a.active_loadout] = dict(weapon=a.weapon, armor=a.armor, helmet=a.helmet)
            selected = sets[index]
            for slot in ('weapon', 'armor', 'helmet'):
                item_id = selected[slot]
                if item_id and not any(i['id'] == item_id and i['slot'] == slot for i in a.inventory):
                    raise HTTPException(404, 'mmo_item_not_owned')
            for slot, item_id in selected.items():
                setattr(a, slot, item_id)
            a.loadouts = sets
            a.active_loadout = index
            stats = self.gear_hp(pid, a)
            result = self.serialize(a)
            db.commit()
            if pid in self.actors: self.actors[pid].update(stats)
            return result

    def equip(self,pid,item_id,loadout=None):
        if loadout is not None: self.validate_loadout(loadout)
        with self.lock,self.factory() as db:
            a=self.avatar(db,pid)
            item=next((i for i in a.inventory if i['id']==item_id),None)
            if item is None: raise HTTPException(404,'mmo_item_not_owned')
            if item['slot'] not in ('weapon', 'armor', 'helmet'):
                raise HTTPException(422, 'mmo_invalid_slot')
            index = a.active_loadout if loadout is None else loadout
            sets = copy.deepcopy(a.loadouts)
            sets[a.active_loadout] = dict(weapon=a.weapon, armor=a.armor, helmet=a.helmet)
            sets[index][item['slot']] = item_id
            a.loadouts = sets
            stats = None
            if index == a.active_loadout:
                setattr(a,item['slot'],item_id)
                stats = self.gear_hp(pid, a)
            result = self.serialize(a)
            db.commit()
            if stats and pid in self.actors: self.actors[pid].update(stats)
            return result

    def upgrade(self,pid,slot):
        if slot not in ('weapon', 'armor', 'helmet'):
            raise HTTPException(422, 'mmo_invalid_slot')
        with self.lock,self.factory() as db:
            a=self.avatar(db,pid)
            rank=getattr(a,slot+'_rank'); cost=50*(rank+1)
            if rank>=20: raise HTTPException(409,'mmo_upgrade_max')
            if a.gold<cost: raise HTTPException(409,'mmo_insufficient_gold')
            a.gold-=cost; setattr(a,slot+'_rank',rank+1)
            stats = self.gear_hp(pid, a)
            result = self.serialize(a)
            db.commit()
            if pid in self.actors: self.actors[pid].update(stats)
            return result

    def start(self):
        self.actors.clear()
        self.zones.clear()
        self.parties.clear()
        self.last=self.clock()
        self.last_loop_tick=self.clock()
        self.healthy=True
        self.task=asyncio.create_task(self.run())

    async def run(self):
        while True:
            await asyncio.sleep(.05)
            try:
                with self.lock:
                    self.advance()
                    self.healthy=True
                    self.last_loop_tick=self.clock()
            except Exception as exc:
                # Deliberately omit database exception messages, SQL and parameters.
                logging.getLogger(__name__).error('MMO tick failed (%s)', type(exc).__name__)
                await asyncio.sleep(.5)

    def ready(self):
        return bool(self.task is not None and not self.task.done() and self.healthy
                    and self.clock()-self.last_loop_tick < 5)

    async def stop(self):
        if self.task:
            self.task.cancel()
            try: await self.task
            except asyncio.CancelledError: pass
            self.task=None
        self.actors.clear()
        self.zones.clear()
        self.parties.clear()


world=World()

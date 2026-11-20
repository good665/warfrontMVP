"""Bounded, authenticated room membership and a single authoritative clock."""
import asyncio
import logging
import secrets
import threading
import time
from fastapi import HTTPException
from .rts_game import RtsGame
from .squad_bot import SquadBot


class SquadRooms:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.rooms, self.membership = {}, {}
        self.task = None
        self.last_loop_tick = clock()
        self.healthy = True

    def start(self):
        if self.task is None or self.task.done():
            self.healthy = True
            self.last_loop_tick = self.clock()
            self.task = asyncio.create_task(self.run())

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

    def ready(self):
        return self.healthy and self.task is not None and not self.task.done() and self.clock()-self.last_loop_tick <= 5

    async def run(self):
        try:
            while True:
                self.tick()
                await asyncio.sleep(.05)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.healthy = False
            logging.getLogger(__name__).exception('Squad loop failed')

    def tick(self):
        with self.lock:
            now = self.clock()
            self.last_loop_tick = now
            for room in list(self.rooms.values()):
                if room['status'] == 'active':
                    absent = [p for p in room['ids'] if not p.startswith('bot:') and (p in room['left'] or now >= room['seen'][p]+30)]
                    if absent:
                        self.resolve_absent(room, absent, 'disconnect')
                    # Fixed steps; reads never advance combat, stalled loops never fast-forward.
                    room['carry'] += 0. if room.get('paused_by') else min(.25, max(0., now-room['advanced']))
                    while room['carry'] >= .05 and not room['game'].reason:
                        for bot in room.get('bots',[]):
                            bot.tick(room['game'])
                        room['game'].tick(.05)
                        room['carry'] -= .05
                    room['advanced'] = now
                    if room['game'].reason:
                        room['status'], room['ended'] = 'finished', now
                if (room['status'] == 'waiting' and now-room['created'] > 300 or room['status'] == 'finished' and now-room['ended'] > 120):
                    self.remove(room)

    def resolve_absent(self, room, absent, reason):
        if room.get('paused_by') in absent:
            room['paused_by'] = ''
            room['advanced'], room['carry'] = self.clock(), 0.
        for pid in absent:
            hero=room['game'].heroes[pid]
            hero['input']={};hero['_pending_actions'].clear()
            for unit in room['game'].units.values():
                if unit['owner_id']==pid: unit['command']='hold'
        lost=[team for team in (0,1) if all(p in absent for i,p in enumerate(room['ids']) if i%2==team)]
        if lost:
            room['game'].winner=1-lost[0] if len(lost)==1 else None
            room['game'].reason=reason

    def remove(self, room):
        self.rooms.pop(room['code'], None)
        for pid in room['ids']:
            if self.membership.get(pid) == room['code']:
                self.membership.pop(pid, None)

    def require(self, code, pid):
        room = self.rooms.get(code.strip().upper())
        if room is None:
            raise HTTPException(404, 'squad_room_not_found')
        if pid == room.get('bot_id') or pid not in room['ids'] or self.membership.get(pid) != room['code']:
            raise HTTPException(403, 'squad_not_member')
        room['seen'][pid] = self.clock()
        return room

    def create(self, pid, queue=False, name='영웅', team_size=1):
        with self.lock:
            if team_size not in (1, 2):
                raise HTTPException(422, 'invalid_team_size')
            self.human_id(pid)
            current = self.membership.get(pid)
            if current:
                room = self.rooms[current]
                if room['status'] != 'finished':
                    return self.state(current, pid)
                self.membership.pop(pid)
            if queue:
                waiting = next((r for r in self.rooms.values() if r['queue'] and r['team_size']==team_size and r['status'] == 'waiting' and self.clock()-r['seen'][r['ids'][0]] < 30), None)
                if waiting:
                    return self.join(waiting['code'], pid, name)
            if len(self.rooms) >= 512:
                raise HTTPException(503, 'squad_capacity')
            code = secrets.token_hex(3).upper()
            while code in self.rooms:
                code = secrets.token_hex(3).upper()
            now = self.clock()
            self.rooms[code] = dict(code=code, ids=[pid], team_size=team_size, capacity=team_size*2, left=set(), names={pid: name}, seen={pid: now}, status='waiting', queue=queue, mode='pvp', created=now, advanced=now, carry=0., ended=0., game=None)
            self.membership[pid] = code
            return self.state(code, pid)

    @staticmethod
    def human_id(pid):
        if pid.startswith('bot:'):
            raise HTTPException(403, 'squad_reserved_player_id')

    def computer(self, pid, name='영웅', team_size=1, character=''):
        with self.lock:
            self.human_id(pid)
            current = self.membership.get(pid)
            if current and self.rooms[current]['status'] != 'finished':
                return self.state(current, pid)
            state = self.create(pid, name=name, team_size=team_size)
            room = self.rooms[state['code']]
            room['bots']=[]
            for slot in range(room['capacity']-1):
                bot_id = 'bot:'+secrets.token_hex(16)
                room['ids'].append(bot_id)
                room['names'][bot_id] = '컴퓨터' if team_size==1 else '컴퓨터 '+str(slot+1)
                room['seen'][bot_id] = self.clock()
                room['bots'].append(SquadBot(bot_id))
            room.update(mode='computer', bot_id=room['ids'][1], bot=room['bots'][0],
                        status='active', game=RtsGame(room['ids'],team_size=team_size))
            for member in room['ids']:
                room['game'].heroes[member]['name'] = room['names'][member]
            # Spawn as the picked hero so the first snapshot doesn't show the default rat.
            room['game'].choose_character(room['game'].heroes[pid], character)
            return self.state(room['code'], pid)

    def join(self, code, pid, name='영웅'):
        with self.lock:
            self.human_id(pid)
            room = self.rooms.get(code.strip().upper())
            if room is None:
                raise HTTPException(404, 'squad_room_not_found')
            if room.get('mode') == 'computer' and pid not in room['ids']:
                raise HTTPException(409, 'squad_computer_room_private')
            if pid in room['ids'] and self.membership.get(pid) == room['code']:
                return self.state(room['code'], pid)
            if self.membership.get(pid):
                raise HTTPException(409, 'squad_already_in_room')
            if room['status'] != 'waiting' or len(room['ids']) >= room['capacity']:
                raise HTTPException(409, 'squad_room_full')
            room['ids'].append(pid)
            room['names'][pid] = name
            room['seen'][pid] = self.clock()
            room['seen'][room['ids'][0]] = self.clock()
            self.membership[pid] = room['code']
            if len(room['ids']) == room['capacity']:
                room.update(status='active', game=RtsGame(room['ids'],team_size=room['team_size']), advanced=self.clock(), carry=0.)
                for member in room['ids']:
                    room['game'].heroes[member]['name'] = room['names'][member]
            return self.state(room['code'], pid)

    def current(self, pid):
        with self.lock:
            code = self.membership.get(pid)
            return self.state(code, pid) if code else dict(code='', status='none', mode='pvp', opponent_name='', you_id=pid, team=-1, winner=-1, reason='', elapsed=0., respawn_left=0., recruited=False, command='none', bases=[], camps=[], roster=[], world=None)

    def state(self, code, pid):
        with self.lock:
            room = self.require(code, pid)
            game = room['game']
            hero = game.heroes[pid] if game else None
            team = room['ids'].index(pid)%2
            return dict(team_size=room['team_size'], capacity=room['capacity'], members=[dict(owner_id=p,team=i%2,base_id='base-'+p,name=room['names'][p]) for i,p in enumerate(room['ids'])], code=room['code'], status=room['status'], mode=room.get('mode', 'pvp'), paused=room['status'] == 'active' and bool(room.get('paused_by')), paused_by=room.get('paused_by', '') if room['status'] == 'active' else '', pause_remaining=-1 if room.get('mode') == 'computer' else 3-room.get('pause_counts', {}).get(pid, 0), opponent_name=next((room['names'][member] for member in room['ids'] if member != pid), ''), you_id=pid, team=team, winner=game.winner if game and game.winner is not None else -1, reason=game.reason if game else '', elapsed=game.elapsed if game else 0., respawn_left=hero['respawn_left'] if hero else 0., recruited=hero['recruited'] if hero else False, command=hero['command'] if hero else 'none', bases=[dict(b) for b in game.bases] if game else [], camps=game.camps if game else [], battle=game.battle_snapshot(pid) if game else None, world=game.snapshot(pid, room['code'], self.clock()) if game else None)

    def pause(self, code, pid, paused):
        with self.lock:
            room = self.require(code, pid)
            if room['status'] != 'active':
                raise HTTPException(409, 'squad_not_active')
            owner = room.get('paused_by', '')
            if owner and owner != pid:
                raise HTTPException(409, 'squad_pause_owner')
            if bool(owner) == paused:
                return self.state(code, pid)
            counts = room.setdefault('pause_counts', {})
            if paused:
                if room.get('mode') != 'computer' and counts.get(pid, 0) >= 3:
                    raise HTTPException(409, 'squad_pause_limit')
                counts[pid] = counts.get(pid, 0)+1
            room['paused_by'] = pid if paused else ''
            room['advanced'], room['carry'] = self.clock(), 0.
            # Never replay held movement or buffered abilities after resuming.
            for hero in room['game'].heroes.values():
                hero['input'] = {}
                hero['_pending_actions'].clear()
            return self.state(code, pid)

    def input(self, code, pid, data):
        with self.lock:
            room = self.require(code, pid)
            if room['status'] == 'active' and not room.get('paused_by'):
                room['game'].input(pid, data)
            return self.state(code, pid)

    def dev(self, code, pid, data):
        with self.lock:
            room = self.require(code, pid)
            if room['status'] != 'active':
                raise HTTPException(409, 'squad_not_active')
            try:
                room['game'].dev_command(pid, **data)
            except ValueError as error:
                raise HTTPException(422, str(error))
            return self.state(code, pid)

    def leave(self, pid):
        with self.lock:
            code = self.membership.get(pid)
            if not code:
                return self.current(pid)
            room = self.require(code, pid)
            if room['status'] == 'waiting':
                room['ids'].remove(pid)
                room['names'].pop(pid, None)
                room['seen'].pop(pid, None)
                self.membership.pop(pid, None)
                if not room['ids']: self.remove(room)
            else:
                if room['status'] == 'active':
                    room['left'].add(pid)
                    self.resolve_absent(room, room['left'], 'forfeit')
                    if room['game'].reason: room['status'], room['ended'] = 'finished', self.clock()
                self.membership.pop(pid, None)
            return self.current(pid)


squad_rooms = SquadRooms()

"""Single-process friend rooms; server clock and atomic database settlement."""
import asyncio
import logging
import secrets
import threading
import time
from dataclasses import dataclass, field

from fastapi import HTTPException
from sqlalchemy import select, update

from . import game_rules as rules
from .database import SessionLocal
from .models import Match, Player
from .online_arena import OnlineArena

logger = logging.getLogger(__name__)
STEP = 0.05
DISCONNECT_SECONDS = 15


@dataclass
class Member:
    player_id: str
    name: str
    role: int
    seen: float
    ready: bool = False
    sequence: int = -1
    control: dict = field(default_factory=dict)
    input_at: float = 0
    rate_at: float = 0
    rate_count: int = 0


@dataclass
class Room:
    code: str
    members: list[Member]
    created: float
    team_size: int = 1
    matchmaking: bool = False
    status: str = "waiting"
    game: OnlineArena | None = None
    matches: list[str] = field(default_factory=list)
    advanced: float = 0
    carry: float = 0
    ended: float = 0
    settled: bool = False
    reason: str = ""


class RoomManager:
    def __init__(self):
        self.rooms = {}
        self.membership = {}
        self.lock = threading.RLock()
        self.task = None
        self.clock = time.monotonic

    def start(self):
        # Rooms are in memory and this prototype runs with one worker. Recover
        # uncompleted rows left by an unclean restart before accepting players.
        with SessionLocal() as db:
            orphaned = db.scalars(select(Match).where(Match.mode.in_(("online1", "online3")), Match.status == "active")).all()
            for match in orphaned:
                player = db.get(Player, match.player_id)
                if player:
                    player.stamina = min(rules.MAX_STAMINA, player.stamina + rules.GAME_COST)
                match.status, match.finished_at = "abandoned", rules.utcnow()
            db.commit()
        self.task = asyncio.create_task(self._run())

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        with self.lock:
            # A graceful shutdown never leaves a partially paid result.
            for room in self.rooms.values():
                if room.status == "active":
                    room.game.finish(-1, "SERVER SHUTDOWN")
                    self._complete(room, "server_shutdown")
            self.rooms.clear()
            self.membership.clear()

    async def _run(self):
        while True:
            await asyncio.sleep(STEP)
            try:
                await asyncio.to_thread(self.tick)
            except Exception:
                logger.exception("Room tick failed; settlement will be retried")

    def tick(self):
        with self.lock:
            now = self.clock()
            for code, room in list(self.rooms.items()):
                if room.status == "waiting" and room.matchmaking:
                    stale_members = [m for m in room.members if now - m.seen > DISCONNECT_SECONDS]
                    for member in stale_members:
                        if self.membership.get(member.player_id) == code:
                            self.membership.pop(member.player_id, None)
                        room.members.remove(member)
                    if not room.members:
                        del self.rooms[code]
                        continue
                if room.status == "waiting" and now - room.created >= 600:
                    room.status, room.reason, room.ended = "closed", "room_expired", now
                if room.status == "active":
                    stale = [now - member.seen > DISCONNECT_SECONDS for member in room.members]
                    if any(stale):
                        stale_teams = {slot % 2 for slot, disconnected in enumerate(stale) if disconnected}
                        winner = -1 if len(stale_teams) == 2 else 1 - next(iter(stale_teams))
                        room.game.finish(winner, "CONNECTION LOST")
                        self._complete(room, "disconnect")
                    else:
                        room.carry += max(0, now - room.advanced)
                        room.advanced = now
                        # Heartbeat timeout above bounds catch-up work after a suspended process.
                        while room.carry >= STEP and not room.game.finished:
                            controls = [m.control if now - m.input_at < .35 else {} for m in room.members]
                            room.game.step(STEP, controls)
                            for member in room.members:
                                for key in ("dodge", "skill1", "skill2"):
                                    member.control[key] = False
                            room.carry -= STEP
                        if room.game.finished:
                            self._complete(room, "completed")
                if room.status == "finished" and not room.settled:
                    self._settle(room)
                if room.status in ("closed", "finished") and now - room.ended > 300:
                    self._release(room)
                    del self.rooms[code]

    def _release(self, room):
        for member in room.members:
            if self.membership.get(member.player_id) == room.code:
                self.membership.pop(member.player_id, None)

    def _available(self, player_id):
        previous = self.rooms.get(self.membership.get(player_id))
        if previous and previous.status in ("waiting", "active"):
            raise HTTPException(409, "already_in_room")
        self.membership.pop(player_id, None)

    def _member(self, code, player_id):
        room = self.rooms.get(code.upper())
        if room is None:
            raise HTTPException(404, "room_not_found")
        for slot, member in enumerate(room.members):
            if member.player_id == player_id:
                return room, slot, member
        raise HTTPException(403, "not_room_member")

    def create(self, player_id, role, team_size=1):
        with self.lock:
            self.tick()
            self._available(player_id)
            if len(self.rooms) >= 128:
                raise HTTPException(503, "rooms_full")
            with SessionLocal() as db:
                player = db.get(Player, player_id)
                if player is None:
                    raise HTTPException(401, "unauthorized")
                name = player.display_name
            alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            code = "".join(secrets.choice(alphabet) for _ in range(6))
            while code in self.rooms:
                code = "".join(secrets.choice(alphabet) for _ in range(6))
            now = self.clock()
            room = Room(code, [Member(player_id, name, role, now)], now, team_size=team_size)
            self.rooms[code] = room
            self.membership[player_id] = code
            return self._snapshot(room, 0)

    def join(self, code, player_id, role, quick=False):
        with self.lock:
            self.tick()
            room = self.rooms.get(code.upper())
            if room is None:
                raise HTTPException(404, "room_not_found")
            if room.matchmaking and not quick:
                raise HTTPException(409, "use_quick_match")
            if any(m.player_id == player_id for m in room.members):
                return self.state(code, player_id)
            self._available(player_id)
            if room.status != "waiting" or len(room.members) >= room.team_size * 2:
                raise HTTPException(409, "room_full")
            with SessionLocal() as db:
                player = db.get(Player, player_id)
                if player is None:
                    raise HTTPException(401, "unauthorized")
                room.members.append(Member(player_id, player.display_name, role, self.clock()))
            self.membership[player_id] = room.code
            return self._snapshot(room, len(room.members) - 1)

    def quick_match(self, player_id, role, team_size):
        with self.lock:
            self.tick()
            self._available(player_id)
            candidates = [r for r in self.rooms.values() if r.matchmaking and r.status == "waiting"
                          and r.team_size == team_size and len(r.members) < team_size * 2]
            if candidates:
                room = min(candidates, key=lambda r: r.created)
                self.join(room.code, player_id, role, quick=True)
                slot = len(room.members) - 1
            else:
                created = self.create(player_id, role, team_size)
                room, slot = self.rooms[created["code"]], 0
                room.matchmaking = True
            room.members[slot].ready = True
            if len(room.members) == team_size * 2:
                try:
                    self._start(room)
                except Exception:
                    room.status, room.reason, room.ended = "closed", "match_start_failed", self.clock()
                    self._release(room)
                    raise
            return self._snapshot(room, slot)

    def state(self, code, player_id):
        with self.lock:
            self.tick()
            room, slot, member = self._member(code, player_id)
            member.seen = self.clock()
            return self._snapshot(room, slot)

    def current(self, player_id):
        with self.lock:
            code = self.membership.get(player_id)
            return self.state(code, player_id) if code else {"code": "", "status": "none"}

    def ready(self, code, player_id, ready, role):
        with self.lock:
            self.tick()
            room, slot, member = self._member(code, player_id)
            if room.status != "waiting":
                return self._snapshot(room, slot)
            if room.matchmaking:
                return self._snapshot(room, slot)
            member.ready, member.role, member.seen = ready, role, self.clock()
            if len(room.members) == room.team_size * 2 and all(m.ready for m in room.members):
                try:
                    self._start(room)
                except Exception:
                    for m in room.members:
                        m.ready = False
                    raise
            return self._snapshot(room, slot)

    def _start(self, room):
        if any(self.clock() - member.seen > DISCONNECT_SECONDS for member in room.members):
            raise HTTPException(409, "participant_offline")
        with SessionLocal() as db:
            players = {}
            # Stable lock ordering is required when two friends ready simultaneously.
            for player_id in sorted(m.player_id for m in room.members):
                player = db.scalar(select(Player).where(Player.id == player_id).with_for_update())
                if player is None:
                    raise HTTPException(401, "unauthorized")
                rules.recover_stamina(player)
                if player.stamina < rules.GAME_COST:
                    raise HTTPException(400, "participant_stamina_low")
                active_online = db.scalar(select(Match.id).where(Match.player_id == player_id, Match.mode.in_(("online1", "online3")), Match.status == "active"))
                if active_online:
                    raise HTTPException(409, "online_match_active")
                players[player_id] = player
            matches = []
            for member in room.members:
                player = players[member.player_id]
                rules.spend_stamina(player, rules.GAME_COST)
                db.execute(update(Match).where(Match.player_id == player.id, Match.status == "active").values(status="abandoned"))
                match = Match(player_id=player.id, mode="online1" if room.team_size == 1 else "online3")
                db.add(match)
                matches.append(match)
            db.flush()
            ids = [m.id for m in matches]
            db.commit()
        room.matches = ids
        room.game = OnlineArena([m.name for m in room.members], [m.role for m in room.members])
        room.status = "active"
        room.advanced = self.clock()
        for member in room.members:
            member.seen = room.advanced

    def input(self, code, player_id, command):
        with self.lock:
            self.tick()
            room, slot, member = self._member(code, player_id)
            now = self.clock()
            member.seen = now
            if room.status == "active":
                if now - member.rate_at >= 1:
                    member.rate_at, member.rate_count = now, 0
                member.rate_count += 1
                if member.rate_count > 40:
                    raise HTTPException(429, "input_rate_limited")
                if command["sequence"] > member.sequence:
                    member.sequence = command["sequence"]
                    for key in ("dodge", "skill1", "skill2"):
                        command[key] = command.get(key, False) or member.control.get(key, False)
                    member.control, member.input_at = command, now
            return self._snapshot(room, slot)

    def leave(self, code, player_id, waiting_only=False):
        with self.lock:
            self.tick()
            room, slot, member = self._member(code, player_id)
            if waiting_only and room.status in ("active", "finished"):
                # A queue cancel racing the final join must not forfeit a match.
                return self._snapshot(room, slot)
            if room.status == "active":
                room.game.finish(1 - slot % 2, "OPPONENT LEFT")
                self._complete(room, "forfeit")
            elif room.status == "waiting":
                if room.matchmaking:
                    room.members.remove(member)
                    if self.membership.get(player_id) == room.code:
                        self.membership.pop(player_id, None)
                    if not room.members:
                        del self.rooms[room.code]
                    return {"code": "", "status": "none"}
                room.status, room.reason, room.ended = "closed", "participant_left", self.clock()
            result = self._snapshot(room, slot)
            self._release(room)
            return result

    def _complete(self, room, reason):
        room.status, room.reason, room.ended = "finished", reason, self.clock()
        self._settle(room)

    def _settle(self, room):
        with SessionLocal() as db:
            for slot, match_id in enumerate(room.matches):
                match = db.scalar(select(Match).where(Match.id == match_id).with_for_update())
                if match is None or match.status != "active":
                    continue
                player = db.scalar(select(Player).where(Player.id == match.player_id).with_for_update())
                if player is None:
                    raise RuntimeError("Online participant missing")
                won = room.game.winner == slot % 2
                match.status, match.won, match.finished_at = "finished", won, rules.utcnow()
                if room.reason == "server_shutdown":
                    player.stamina = min(rules.MAX_STAMINA, player.stamina + rules.GAME_COST)
                elif won:
                    player.diamonds += 3 if room.team_size == 1 else 5
            db.commit()
        room.settled = True

    def _snapshot(self, room, slot):
        result = dict(code=room.code, status=room.status, slot=slot, reason=room.reason,
                      matchmaking=room.matchmaking,
                      team=slot % 2, team_size=room.team_size, capacity=room.team_size * 2,
                      last_sequence=room.members[slot].sequence,
                      settled=room.settled, match_id=room.matches[slot] if room.matches else "",
                      reward=(3 if room.team_size == 1 else 5) if room.settled and room.game.winner == slot % 2 else 0,
                      members=[dict(name=m.name, role=m.role, ready=m.ready, team=i % 2) for i, m in enumerate(room.members)])
        if room.game:
            result.update(room.game.snapshot())
        return result


rooms = RoomManager()

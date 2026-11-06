"""Version 2 training rules: integer 100 Hz simulation shared with Unity.

Only replay() is a submission boundary. Session is the deterministic rule engine;
its inputs must already be validated. A tick-N input acts after N advanced ticks.
"""
from math import isqrt

RULES_VERSION = 2
TICK_RATE = 100
DURATION_TICKS = 4500
COORD_SCALE = 100
METRICS = ('score', 'hits', 'friendly_hits', 'misses', 'shots', 'deliveries',
           'collisions', 'completed_codes', 'mistakes', 'played_ticks', 'elapsed_ticks')


class XorShift32:
    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFF or 2463534242

    def next_uint(self):
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state

    def next(self, maximum):
        return self.next_uint() % maximum


def _distance_squared(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _trunc_div(a, b):
    return a // b if a >= 0 else -((-a) // b)


class Session:
    def __init__(self, game, seed):
        self.game = game
        self.rng = XorShift32(seed)
        for name in METRICS:
            setattr(self, name, 0)
        self.targets = []  # id, x, y, remaining ticks, friendly
        self.next_id = self.combo = 0
        self.drone = self.depot = self.destination = (10000, 20000)
        self.supply = (88000, 20000)
        self.carrying = False
        self.stun = self.preview = self.progress = 0
        self.sequence = []
        if game == 'range':
            self._spawn()
        elif game == 'cipher':
            self._new_sequence(2)

    @property
    def finished(self):
        return self.elapsed_ticks >= DURATION_TICKS

    @property
    def accepting_signals(self):
        return self.game == 'cipher' and not self.finished and self.preview >= len(self.sequence) * 75 + 40

    def _spawn(self):
        self.targets.append([self.next_id, 7000 + self.rng.next(86000),
                             6000 + self.rng.next(28000), 180, (self.next_id + 1) % 4 == 0])
        self.next_id += 1

    def advance(self, ticks):
        for _ in range(min(ticks, DURATION_TICKS - self.elapsed_ticks)):
            self.played_ticks += 1
            self.elapsed_ticks += 1
            if self.game == 'range':
                for t in self.targets[:]:
                    t[3] -= 1
                    if t[3] == 0:
                        if not t[4]:
                            self.misses += 1
                            self.combo = 0
                        self.targets.remove(t)
                if self.played_ticks % 72 == 0:
                    self._spawn()
            elif self.game == 'drone':
                self._drone_tick()
            else:
                self.preview += 1

    @staticmethod
    def _blocked(p):
        x, y = p
        for ox, oy, w, h in ((39000, 13500, 9000, 13000), (65000, 26000, 8500, 8500)):
            if ox - 1600 < x < ox + w + 1600 and oy - 1600 < y < oy + h + 1600:
                return True
        return _distance_squared(p, (70000, 17000)) < 4300 ** 2

    def _drone_tick(self):
        if self.stun:
            self.stun -= 1
            return
        distance = isqrt(_distance_squared(self.drone, self.destination))
        if distance:
            if distance <= 320:
                p = self.destination
            else:
                p = tuple(self.drone[i] + _trunc_div((self.destination[i] - self.drone[i]) * 320, distance)
                          for i in range(2))
            if self._blocked(p):
                self.collisions += 1
                self.carrying = False
                self.stun = 65
                self.destination = self.drone
                return
            self.drone = p
        if not self.carrying and _distance_squared(self.drone, self.supply) <= 3200 ** 2:
            self.carrying = True
        if self.carrying and _distance_squared(self.drone, self.depot) <= 3400 ** 2:
            self.carrying = False
            self.deliveries += 1
            self.score += 250
            self._spawn_supply()

    def _spawn_supply(self):
        for _ in range(100):
            p = (54000 + self.rng.next(40000), 5500 + self.rng.next(29000))
            if not self._blocked(p):
                self.supply = p
                return
        self.supply = (88000, 8000)

    def _new_sequence(self, length):
        self.sequence = [self.rng.next(4) for _ in range(length)]
        self.progress = self.preview = 0

    def apply(self, event):
        if self.finished:
            return
        if event['action'] == 0:
            self.shots += 1
            for t in reversed(self.targets):
                if _distance_squared((event['x'], event['y']), (t[1], t[2])) > 3000 ** 2:
                    continue
                self.targets.remove(t)
                if t[4]:
                    self.friendly_hits += 1
                    self.combo = 0
                    self.score = max(0, self.score - 150)
                else:
                    self.hits += 1
                    self.combo += 1
                    self.score += 100 + min(5, self.combo - 1) * 20
                return
            self.misses += 1
            self.combo = 0
        elif event['action'] == 1:
            self.destination = (max(1800, min(98200, event['x'])), max(1800, min(38200, event['y'])))
        elif self.accepting_signals:
            if self.sequence[self.progress] != event['index']:
                self.mistakes += 1
                self.elapsed_ticks = min(DURATION_TICKS, self.elapsed_ticks + 300)
                self._new_sequence(len(self.sequence))
            else:
                self.progress += 1
                if self.progress == len(self.sequence):
                    self.completed_codes += 1
                    self.score += len(self.sequence) * 100
                    self._new_sequence(min(8, len(self.sequence) + 1))

    def metrics(self):
        return {name: getattr(self, name) for name in METRICS}

    def snapshot(self):
        return dict(targets=[t[:] for t in self.targets], drone=list(self.drone), supply=list(self.supply),
                    carrying=self.carrying, stun=self.stun, sequence=self.sequence[:],
                    progress=self.progress, preview=self.preview, rng=self.rng.state, combo=self.combo)


def replay(game: str, seed: int, total_ticks: int, events: list[dict]) -> dict:
    """Verify a complete canonical v2 run, returning only authoritative integer metrics."""
    if not isinstance(game, str) or game not in ('range', 'drone', 'cipher'):
        raise ValueError('unknown training game')
    if type(seed) is not int or not 1 <= seed <= 2147483647:
        raise ValueError('invalid seed')
    if type(total_ticks) is not int or not 0 <= total_ticks <= DURATION_TICKS:
        raise ValueError('invalid total_ticks')
    if type(events) is not list or len(events) > DURATION_TICKS + 1:
        raise ValueError('invalid event list')
    action = ('range', 'drone', 'cipher').index(game)
    previous = -1
    for e in events:
        if type(e) is not dict or set(e) != {'tick', 'action', 'x', 'y', 'index'}:
            raise ValueError('invalid event fields')
        if any(type(v) is not int for v in e.values()):
            raise ValueError('event values must be integers')
        if not previous < e['tick'] <= total_ticks or e['action'] != action:
            raise ValueError('invalid event tick or action')
        if not 0 <= e['x'] <= 100000 or not 0 <= e['y'] <= 40000 or not 0 <= e['index'] <= 3:
            raise ValueError('event out of bounds')
        if (action == 2 and (e['x'] or e['y'])) or (action != 2 and e['index']):
            raise ValueError('unused event fields must be zero')
        previous = e['tick']
    session = Session(game, seed)
    for e in events:
        session.advance(e['tick'] - session.played_ticks)
        if session.finished or session.played_ticks != e['tick']:
            raise ValueError('event after termination')
        session.apply(e)
    session.advance(total_ticks - session.played_ticks)
    if not session.finished or session.played_ticks != total_ticks:
        raise ValueError('run must terminate at exactly total_ticks')
    return session.metrics()

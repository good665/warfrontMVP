"""1:1 vehicles parked outside the two manors (F to ride / leave).

car: 60 s, x1.5 speed, touching an enemy hero kills it; the car soaks hits and breaks after 5.
bike: 120 s, x2 speed, any hit throws the rider off.
The time runs from the first boarding: getting off (F, thrown off, death) parks the ride where it stopped, and anyone may
take it again until the time is up or the car breaks; then it goes home and respawns like a chest.
Riders cannot attack, cast, super jump or go through doors.
bus: F at the bus boards it; the bus drives into a portal opening in front of it (PORTAL_ENTER s, the hero rides inside,
untouchable), then the hero steps out of an exit portal in the other manor's yard (one way). The server moves the hero
from the bus to the portal; Unity draws the bus on the hero and shrinks/grows it from portal_left / portal_out_left.
Each manor yard gets one random kind per match. A used vehicle (and the bus) is back after VEHICLE_RESPAWN, like a chest.
"""
import math
from .rts_map import CELL, OUTDOOR, SIZE

VEHICLE_RESPAWN = 180.
RIDE_SECONDS = dict(car=60., bike=120.)
RIDE_SPEED = dict(car=1.5, bike=2.)
CAR_HITS = 5
CAR_HIT_GAP = .25  # damage ticks (poison) closer than this count as one hit
KINDS = ('car', 'bike', 'bus')
REACH = 110.       # F reaches a vehicle this far from its centre (models are drawn 1.5x, the bus ~6 cells long)
RAM = 80.          # car body reach beyond the victim's body radius
NAMES = dict(car='자동차', bike='오토바이', bus='버스')
PORTAL_ENTER = 1.2  # seconds of the bus driving into its portal
BUS_REACH = 170.   # the bus is ~6 cells long, so F reaches it from either end
BUS_THROUGH = 170. # the bus centre ends this far past the portal: the whole (1.5x, ~6 cell) bus has gone through
PORTAL_EXIT = .8    # seconds the exit portal shows at the far yard
TURN_RATE = math.radians(270)  # rides turn at most this fast (rad/s)


def _point(cx, cy, half_turn=False):
    if half_turn: cx, cy = SIZE-1-cx, SIZE-1-cy
    return (cx+.5)*CELL, (cy+.5)*CELL


# North-east manor yard (door 123,11); the south-west set is the half turn, like the map itself.
NE_PARK = (115, 15)
NE_YARD = (123, 14)
NE_PORTAL = (115, 21)  # the portal opens in front of the bus (parked facing south)


def _vehicles(kinds):
    out = []
    for side, turn in (('ne', False), ('sw', True)):
        kind = kinds[side]
        x, y = _point(*NE_PARK, turn)
        v = dict(id=f'{kind}-{side}', kind=kind, x=x, y=y, home_x=x, home_y=y, fx=0., fy=-1., ready_at=0., expires_at=0., hits=0)
        if kind == 'bus':
            v['to_x'], v['to_y'] = _point(*NE_YARD, not turn)  # one way, to the other yard
            v['portal_x'], v['portal_y'] = _point(*NE_PORTAL, turn)
        out.append(v)
    return out


class RtsVehicles:
    def init_vehicles(self, kinds=None):
        kinds = kinds or {side: self.rng.choice(KINDS) for side in ('ne', 'sw')}
        self.vehicles = {v['id']: v for v in _vehicles(kinds)} if self.team_size == 1 else {}

    def riding(self, h):
        return h.get('vehicle', '')

    def vehicle_key(self, h):
        """F: leave the ride, or take the nearest ready vehicle in reach."""
        if self.riding(h): return self.dismount(h, '내렸습니다')
        if h['floor'] != OUTDOOR or h['_leap']: return
        gap = lambda v: math.hypot(v['x']-h['x'], v['y']-h['y'])
        near = [v for v in self.vehicles.values() if v['ready_at'] <= self.elapsed
                and gap(v) <= (BUS_REACH if v['kind'] == 'bus' else REACH)]
        if not near: return
        v = min(near, key=gap)
        if v['kind'] == 'bus':
            v['ready_at'] = self.elapsed + VEHICLE_RESPAWN  # the bus leaves through the portal
            dx, dy = v['portal_x'] - v['x'], v['portal_y'] - v['y']
            n = math.hypot(dx, dy) or 1.
            h.update(x=v['x'], y=v['y'], fx=dx/n, fy=dy/n, portal_left=PORTAL_ENTER, portal_x=v['portal_x'], portal_y=v['portal_y'],
                     _portal_from=(v['x'], v['y']), _portal_to=(v['to_x'], v['to_y']),
                     protected=max(h['protected'], PORTAL_ENTER + .1), command='hold', _path=[])
            h['_pending_actions'].clear()
            return
        if not v['expires_at']:  # first boarding starts the clock
            v.update(expires_at=self.elapsed + RIDE_SECONDS[v['kind']], hits=CAR_HITS if v['kind'] == 'car' else 0)
        v['ready_at'] = math.inf  # out of the yard while ridden
        h.update(vehicle=v['kind'], vehicle_id=v['id'], vehicle_left=v['expires_at'] - self.elapsed,
                 vehicle_hits=v['hits'], _vehicle_hit_at=-1., fx=v['fx'], fy=v['fy'])
        h['_pending_actions'].pop('super_jump', None)
        self.notify(h, f"{NAMES[v['kind']]} 탑승! F 키로 내리기", False)

    def steer(self, h, fx0, fy0, dt):
        """Rides turn at TURN_RATE: letting go of one diagonal key a moment early no longer snaps the car straight."""
        a0 = math.atan2(fy0, fx0)
        d = (math.atan2(h['fy'], h['fx']) - a0 + math.pi) % (2*math.pi) - math.pi
        a = a0 + max(-TURN_RATE*dt, min(TURN_RATE*dt, d))
        h.update(fx=math.cos(a), fy=math.sin(a))

    def send_home(self, v):
        v.update(x=v['home_x'], y=v['home_y'], fx=0., fy=-1., ready_at=self.elapsed + VEHICLE_RESPAWN, expires_at=0., hits=0)

    def dismount(self, h, text=''):
        """Off the ride: parked where it stopped while its time lasts, else home."""
        v = self.vehicles.get(h.get('vehicle_id', ''))
        if v:
            if v['expires_at'] <= self.elapsed or (v['kind'] == 'car' and h['vehicle_hits'] <= 0): self.send_home(v)
            else: v.update(x=h['x'], y=h['y'], fx=h['fx'], fy=h['fy'], hits=h['vehicle_hits'], ready_at=0.)
        h.update(vehicle='', vehicle_id='', vehicle_left=0., vehicle_hits=0)
        if text: self.notify(h, text, False)

    def vehicle_hit(self, target, kind):
        """damage() hook. True when the car swallows the hit (the rider takes nothing)."""
        ride = self.riding(target)
        if ride == 'bike':
            self.dismount(target, '공격을 받아 오토바이에서 떨어졌습니다')
            return False
        if ride != 'car': return False
        if self.elapsed - target['_vehicle_hit_at'] >= CAR_HIT_GAP:
            target['_vehicle_hit_at'] = self.elapsed
            target['vehicle_hits'] -= 1
            target['hit_flash'] = .16
            if target['vehicle_hits'] <= 0: self.dismount(target, '자동차가 부서졌습니다')
        return True

    def portal_pull(self, h):
        """hero_tick while the bus drives into its portal: the hero rides along, nothing else happens."""
        (x0, y0), t = h['_portal_from'], min(1., (1 - h['portal_left'] / PORTAL_ENTER) / .9)
        dx, dy = h['portal_x'] - x0, h['portal_y'] - y0
        k = 1 + BUS_THROUGH / (math.hypot(dx, dy) or 1.)  # Unity hides whatever is past the portal plane
        h.update(x=x0 + dx*k*t, y=y0 + dy*k*t)

    def vehicles_tick(self):
        """Parked rides whose time ran out go home."""
        for v in self.vehicles.values():
            if v['ready_at'] <= self.elapsed and v['expires_at'] and v['expires_at'] <= self.elapsed: self.send_home(v)

    def vehicle_tick(self, h, dt):
        if h['_portal_to'] and h['portal_left'] <= 0:
            x, y = h['_portal_to']
            self.teleport(h, OUTDOOR, x, y)  # same short guard as the portal item
            h.update(_portal_to=None, _portal_from=None, portal_out_left=PORTAL_EXIT, portal_x=x, portal_y=y)
            self.notify(h, '차원 포탈로 반대편 저택에 도착했습니다', False)
        if not self.riding(h): return
        v = self.vehicles.get(h['vehicle_id'])
        h['vehicle_left'] = max(0., v['expires_at'] - self.elapsed) if v else 0.
        if h['floor'] != OUTDOOR:  # teleported indoors: the ride cannot park there
            if v: self.send_home(v)
            return self.dismount(h)
        if h['hp'] <= 0: return self.dismount(h)
        if h['vehicle_left'] <= 0: return self.dismount(h, '탑승 시간이 끝났습니다')
        if h['vehicle'] == 'car':
            for e in self.heroes.values():
                if (e['team'] != h['team'] and e['hp'] > 0 and e['floor'] == h['floor']
                        and math.hypot(e['x']-h['x'], e['y']-h['y']) <= RAM + e['body_radius']):
                    self.damage(e, e['hp'] + e.get('shield', 0) + 1e6, h, 'true')

    def vehicles_public(self, floor):
        return [dict(id=v['id'], kind=v['kind'], x=v['x'], y=v['y'], fx=v['fx'], fy=v['fy'], ready=True,
                     left=max(0., v['expires_at'] - self.elapsed) if v['expires_at'] else 0.)
                for v in self.vehicles.values() if floor == OUTDOOR and v['ready_at'] <= self.elapsed]

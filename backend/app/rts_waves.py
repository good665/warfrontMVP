"""Server-owned wave cadence and resumable waypoint routes."""
from .rts_map import EXTENT, CELL, NAVE
from .rts_combat import distance
from .rts_spacing import UNIT_SPACING
from .zodiac_rules import HP_SCALE

WAVE_INTERVAL = 30.
WAVE_KINDS = ('guard', 'guard', 'guard', 'archer', 'archer')


def nave_route(unit, destination):
    """Crossing the map: in the cathedral end on the unit's side, out the far end. Same side: no detour."""
    x0, y0, x1, y1 = NAVE
    y = (y0 + y1 + 1) / 2 * CELL
    west, east = dict(x=(x0 + .5) * CELL, y=y), dict(x=(x1 + .5) * CELL, y=y)
    side = unit['x'] < EXTENT / 2
    if side == (destination['x'] < EXTENT / 2):
        return []
    return [west, east] if side else [east, west]


class RtsWaves:
    def wave_destination(self, unit):
        return min((b for b in self.bases if b['team'] != unit['team'] and b['hp'] > 0),
                   key=lambda b: distance(unit, b), default=None)

    def set_wave_route(self, unit, destination):
        def approach(base):
            return dict(x=base['x'] + (200 if base['x'] < EXTENT / 2 else -200),
                        y=base['y'] + (200 if base['y'] < EXTENT / 2 else -200))

        unit['_wave_destination'] = destination['id']
        unit['_waypoints'] = [approach(self.home(unit['owner_id'])), *nave_route(unit, destination),
                              approach(destination), dict(x=destination['x'], y=destination['y'])]
        unit['_waypoint'] = 0

    def spawn_wave(self):
        for base in self.bases:
            if base['hp'] <= 0:
                continue
            destination = self.wave_destination(base)
            if destination is None:
                continue
            sx = 1 if base['x'] < EXTENT / 2 else -1
            sy = 1 if base['y'] < EXTENT / 2 else -1
            for i, kind in enumerate(WAVE_KINDS):
                self.next_id += 1
                uid = f'wave-{self.next_id}'
                unit = self.actor(uid, kind, base['team'], base['x'] + sx * 120 + (i - 2) * 30,
                                  base['y'] + sy * 120, (180 if kind == 'guard' else 100) * HP_SCALE, 1)
                unit.update(owner_id=base['owner_id'], command='wave', wave=True,
                            order_x=destination['x'], order_y=destination['y'], target_id='')
                self.set_wave_route(unit, destination)
                self.units[uid] = self.minions[uid] = unit

    def update_waves(self):
        while self.elapsed + 1e-8 >= self.next_wave:
            self.spawn_wave()
            self.next_wave += WAVE_INTERVAL

    def wave_tick(self, unit, dt):
        destination = next((b for b in self.bases if b['id'] == unit['_wave_destination'] and b['hp'] > 0), None)
        if destination is None:
            destination = self.wave_destination(unit)
            if destination is None:
                return
            self.set_wave_route(unit, destination)
            # A redirected wave continues from its current position, not its home.
            unit['_waypoint'] = 1
        enemies = [a for a in self.all_targets() if a['team'] != unit['team'] and a['hp'] > 0
                   and (a['kind'] != 'base' or unit['_waypoint'] >= len(unit['_waypoints']) - 1)
                   and distance(a, unit) < 420 and self.can_hit(unit, a)]
        if enemies:
            # Reuse existing attack-move targeting, without replacing the route.
            unit['command'], unit['_fought'] = 'attack_move', True
            try:
                self.command_tick(unit, dt)
            finally:
                unit['command'] = 'wave'
            return
        route = unit['_waypoints']
        index = unit['_waypoint']
        if unit.pop('_fought', False):
            # Chasing during a fight can carry units past a waypoint: count it as done instead of walking back to it.
            while index < len(route) - 1 and distance(unit, route[index + 1]) < distance(route[index], route[index + 1]):
                index += 1
        while index < len(route) - 1:
            reached = distance(unit, route[index]) <= UNIT_SPACING + 1
            occupied = any(h['hp'] > 0 and h['id'] in self.units
                           and distance(h, route[index]) <= UNIT_SPACING
                           and distance(h, unit) <= UNIT_SPACING + 1 for h in self.heroes.values())
            if not reached and not occupied:
                break
            index += 1
        unit['_waypoint'] = index
        self.walk(unit, route[index]['x'], route[index]['y'], 180, dt)

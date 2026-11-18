"""Resolve character overlap on the server without changing issued orders."""
import math
from .rts_map import EXTENT, bounds

# 80 logical units = 1.6 Unity world units, including visible equipment.
UNIT_SPACING = 80.


class RtsSpacing:
    def avoid_heroes(self, actor, nx, ny, goal_x, goal_y):
        if actor['kind'] == 'hero':
            return nx, ny
        for hero in self.heroes.values():
            if hero['hp'] <= 0 or hero['id'] not in self.units:
                continue
            if math.hypot(goal_x-hero['x'], goal_y-hero['y']) <= UNIT_SPACING:
                continue
            dx, dy = hero['x']-actor['x'], hero['y']-actor['y']
            length = math.hypot(dx, dy)
            forward, side = nx*dx + ny*dy, nx*dy - ny*dx
            if 1e-8 < length < UNIT_SPACING*2 and forward > 0 and abs(side) < UNIT_SPACING:
                # Walk tangentially around an immovable hero instead of repeatedly
                # walking into the same contact point and being pushed back.
                turn = 1 if side >= 0 else -1
                tx, ty = turn*dy/length, -turn*dx/length
                def clearance(sign):
                    x = max(35., min(EXTENT-35, actor['x'] + tx*20*sign))
                    y = max(35., min(EXTENT-35, actor['y'] + ty*20*sign))
                    return (x-actor['x'])**2 + (y-actor['y'])**2
                if clearance(-1) > clearance(1) + .01:
                    tx, ty = -tx, -ty
                if self.closed(actor, actor['x'] + tx*20, actor['y'] + ty*20):
                    return nx, ny
                return tx, ty
        return nx, ny

    def separate_units(self):
        actors = sorted((a for a in self.units.values() if a['hp'] > 0), key=lambda a: a['id'])
        for _ in range(12):
            cells = {}
            for i, actor in enumerate(actors):
                cell = (math.floor(actor['x'] / UNIT_SPACING), math.floor(actor['y'] / UNIT_SPACING))
                cells.setdefault(cell, []).append(i)
            corrected = False
            for i, a in enumerate(actors):
                cx, cy = math.floor(a['x'] / UNIT_SPACING), math.floor(a['y'] / UNIT_SPACING)
                for x in range(cx-1, cx+2):
                    for y in range(cy-1, cy+2):
                        for j in cells.get((x, y), ()):
                            if j <= i:
                                continue
                            b = actors[j]
                            wa, wb = int(a['kind'] != 'hero'), int(b['kind'] != 'hero')
                            if not wa + wb:
                                continue
                            dx, dy = b['x']-a['x'], b['y']-a['y']
                            length = math.hypot(dx, dy)
                            if length >= UNIT_SPACING - .05:
                                continue
                            if length < 1e-8:
                                # Stable direction even when characters occupy exactly the same point.
                                angle = math.radians((i*97 + j*57) % 360)
                                nx, ny = math.cos(angle), math.sin(angle)
                            else:
                                nx, ny = dx/length, dy/length
                            push = (UNIT_SPACING-length) / (wa+wb)
                            for actor, weight in ((a, -wa), (b, wb)):
                                if weight:
                                    x0, y0, x1, y1 = bounds(actor['floor'])
                                    x = max(x0, min(x1, actor['x'] + nx*push*weight))
                                    y = max(y0, min(y1, actor['y'] + ny*push*weight))
                                    # Never push a body into a wall; the other body still yields.
                                    if self.closed(actor, actor['x'], actor['y']) or not self.closed(actor, x, y):
                                        actor['x'], actor['y'] = x, y
                                        corrected = True
            if not corrected:
                break

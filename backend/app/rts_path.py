"""Grid A* and line-of-sight on the squad map (one cell = 50 server units)."""
import heapq
import math
from .rts_map import CELL, blocked, cell, is_door, sight_blocked

DIAGONAL = math.sqrt(2)


def _closed(floor, cx, cy, doors_open):
    return blocked(floor, cx, cy) or (not doors_open and is_door(floor, cx, cy))


def _center(cx, cy):
    return (cx + .5) * CELL, (cy + .5) * CELL


def nearest_open(floor, x, y, doors_open=True):
    cx, cy = cell(x, y)
    if not _closed(floor, cx, cy, doors_open):
        return x, y
    for r in range(1, 20):
        ring = [(cx+dx, cy+dy) for dx in range(-r, r+1) for dy in range(-r, r+1) if max(abs(dx), abs(dy)) == r]
        ring = [p for p in ring if not _closed(floor, *p, doors_open)]
        if ring:
            return _center(*min(ring, key=lambda p: math.hypot(_center(*p)[0]-x, _center(*p)[1]-y)))
    return x, y


def _line(floor, ax, ay, bx, by, closed):
    steps = max(1, int(math.hypot(bx-ax, by-ay) // (CELL / 4)))
    return not any(closed(*cell(ax + (bx-ax)*i/steps, ay + (by-ay)*i/steps)) for i in range(steps+1))


def line_clear(floor, ax, ay, bx, by):
    return _line(floor, ax, ay, bx, by, lambda cx, cy: sight_blocked(floor, cx, cy))


def find_path(floor, sx, sy, gx, gy, doors_open=True):
    """Waypoints (cell centres, last = goal) from (sx, sy); [] when already there or unreachable."""
    gx, gy = nearest_open(floor, gx, gy, doors_open)
    start, goal = cell(sx, sy), cell(gx, gy)
    if start == goal:
        return []
    closed = lambda cx, cy: _closed(floor, cx, cy, doors_open)
    came, cost, todo = {start: None}, {start: 0.}, [(0., start)]
    while todo:
        _, cur = heapq.heappop(todo)
        if cur == goal:
            break
        cx, cy = cur
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nxt = (cx+dx, cy+dy)
            if closed(*nxt) or dx and dy and (closed(cx+dx, cy) or closed(cx, cy+dy)):
                continue
            new = cost[cur] + (DIAGONAL if dx and dy else 1.)
            if new < cost.get(nxt, math.inf):
                cost[nxt], came[nxt] = new, cur
                ox, oy = abs(goal[0]-nxt[0]), abs(goal[1]-nxt[1])
                heapq.heappush(todo, (new + max(ox, oy) + (DIAGONAL-1) * min(ox, oy), nxt))
    if goal not in came:
        return []
    cells, cur = [], goal
    while cur != start:
        cells.append(cur); cur = came[cur]
    cells.reverse()
    points = [_center(*p) for p in cells[:-1]] + [(gx, gy)]
    # String pulling: skip waypoints while the straight walk stays on open cells.
    pulled, x, y, i = [], sx, sy, 0
    while i < len(points):
        j = len(points) - 1
        while j > i and not _line(floor, x, y, *points[j], closed):
            j -= 1
        x, y = points[j]
        pulled.append(dict(x=x, y=y))
        i = j + 1
    return pulled

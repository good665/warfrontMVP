from collections import deque
from app import rts_map as m


def reachable(floor, start):
    seen, todo = {start}, deque([start])
    while todo:
        cx, cy = todo.popleft()
        for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
            if (nx, ny) not in seen and not m.blocked(floor, nx, ny):
                seen.add((nx, ny)); todo.append((nx, ny))
    return seen


def test_map_is_symmetric():
    for cx in range(m.SIZE):
        for cy in range(m.SIZE):
            b = m.blocked(m.OUTDOOR, cx, cy)
            assert b == m.blocked(m.OUTDOOR, m.SIZE-1-cx, cy) == m.blocked(m.OUTDOOR, cx, m.SIZE-1-cy)


def test_starts_and_center_open():
    for x, y in m.STARTS:
        sx, sy = m.cell(x, y)
        assert not any(m.blocked(m.OUTDOOR, sx+dx, sy+dy) for dx in range(-8, 9) for dy in range(-8, 9))
    assert not any(m.blocked(m.OUTDOOR, 63+dx, 63+dy) for dx in range(3) for dy in range(3))


def test_outdoor_connected():
    seen = reachable(m.OUTDOOR, m.cell(*m.STARTS[0]))
    assert all(m.cell(x, y) in seen for x, y in m.STARTS)
    assert (64, 64) in seen
    assert all((d['cx'], d['cy']) in seen for d in m.DOORS if d['floor'] == m.OUTDOOR)


def test_interiors_connected():
    floors = {d['floor'] for d in m.DOORS if d['floor'] != m.OUTDOOR}
    assert floors == set(range(2, 8))
    for floor in floors:
        doors = [(d['cx'], d['cy']) for d in m.DOORS if d['floor'] == floor]
        seen = reachable(floor, doors[0])
        assert all(door in seen for door in doors)
        assert all(m.cell(c['x'], c['y']) in seen for c in m.CHESTS if c['floor'] == floor)


def test_doors_pair_up():
    for d in m.DOORS:
        tx, ty = m.cell(d['to_x'], d['to_y'])
        assert not m.blocked(d['to_floor'], tx, ty)
        back = [b for b in m.DOORS if b['floor'] == d['to_floor'] and b['to_floor'] == d['floor']
                and abs(b['cx']-tx) + abs(b['cy']-ty) <= 2]
        assert len(back) == 1


def test_interiors_off_board():
    for floor in range(2, 8):
        x0, y0, x1, y1 = m.bounds(floor)
        assert x0 >= 6800 and x1 <= 8400
    assert len(m.map_payload()['interiors']) == 6

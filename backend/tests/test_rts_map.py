from collections import deque
from app import rts_map as m

DUO = m.closed_for(2)  # 2:2 has no manors: their cells are open ground and their doors are off


def reachable(floor, start, opened=frozenset()):
    seen, todo = {start}, deque([start])
    while todo:
        cx, cy = todo.popleft()
        for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
            if (nx, ny) not in seen and not m.blocked(floor, nx, ny, opened):
                seen.add((nx, ny)); todo.append((nx, ny))
    return seen


def test_duo_map_is_mirror_symmetric():
    for cx in range(m.SIZE):
        for cy in range(m.SIZE):
            b = m.blocked(m.OUTDOOR, cx, cy, DUO)
            assert b == m.blocked(m.OUTDOOR, m.SIZE-1-cx, cy, DUO) == m.blocked(m.OUTDOOR, cx, m.SIZE-1-cy, DUO)


def test_solo_map_is_point_symmetric():
    # 1:1 bases sit on the NW-SE diagonal, so a half turn swaps the players.
    for cx in range(m.SIZE):
        for cy in range(m.SIZE):
            assert m.blocked(m.OUTDOOR, cx, cy) == m.blocked(m.OUTDOOR, m.SIZE-1-cx, m.SIZE-1-cy)


def test_starts_and_center_open():
    for team_size, opened in ((1, frozenset()), (2, DUO)):
        for x, y in m.STARTS[:team_size*2]:
            sx, sy = m.cell(x, y)
            assert not any(m.blocked(m.OUTDOOR, sx+dx, sy+dy, opened) for dx in range(-8, 9) for dy in range(-8, 9))
        assert not any(m.blocked(m.OUTDOOR, 63+dx, 63+dy, opened) for dx in range(3) for dy in range(3))


def test_outdoor_connected():
    for team_size, opened in ((1, frozenset()), (2, DUO)):  # 1:1 only uses the NW/SE starts
        seen = reachable(m.OUTDOOR, m.cell(*m.STARTS[0]), opened)
        assert all(m.cell(x, y) in seen for x, y in m.STARTS[:team_size*2])
        assert (64, 64) in seen
        assert all((d['cx'], d['cy']) in seen for d in m.DOORS if m.is_door(d['floor'], d['cx'], d['cy'], opened) and d['floor'] == m.OUTDOOR)


def test_interiors_connected():
    floors = {d['floor'] for d in m.DOORS if d['floor'] != m.OUTDOOR}
    assert floors == set(range(2, 10))
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
    for floor in range(2, 10):
        x0, y0, x1, y1 = m.bounds(floor)
        assert x0 >= 6800 and x1 <= 8400
    assert len(m.map_payload()['interiors']) == 8


def test_manors_fill_the_empty_solo_corners_with_doors_facing_inward():
    assert {r[:5] for r in m.RECTS if r[0] == 'manor'} == {('manor', 108, 0, 127, 11), ('manor', 0, 116, 19, 127)}
    outer = {(d['cx'], d['cy']): d for d in m.DOORS if d['floor'] == m.OUTDOOR}
    for cy, exit_y, xs in ((11, 13, (123,)), (116, 114, (4,))):  # NE manor exits south, SW manor exits north
        for cx in xs:
            inner = next(d for d in m.DOORS if d['floor'] == outer[(cx, cy)]['to_floor'] and m.cell(d['to_x'], d['to_y']) == (cx, exit_y))
            assert inner['to_floor'] == m.OUTDOOR
    assert [i['kind'] for i in m.map_payload()['interiors']].count('manor') == 2
    # The way in and out is the stair niche beside the six-chair table (column 15 of the bottom row).
    assert [row.find('D') for row in m.MANOR] == [-1] * 11 + [15] and m.MANOR[-1].count('D') == 1
    # Each manor's way out is on the side its outdoor door faces: NE enters from the south, SW from the north.
    for cx, cy, side in ((123, 11, 'bottom'), (4, 116, 'top')):
        floor = outer[(cx, cy)]['to_floor']
        ox, oy, rows, _ = m.INTERIORS[floor]
        inner = next(d for d in m.DOORS if d['floor'] == floor)
        assert inner['cy'] - oy == (len(rows) - 1 if side == 'bottom' else 0)
        assert m.cell(outer[(cx, cy)]['to_x'], outer[(cx, cy)]['to_y'])[1] - oy == (len(rows) - 2 if side == 'bottom' else 1)


def test_duo_map_has_no_manors_and_keeps_wall_indices():
    solo, duo = m.map_payload(1), m.map_payload(2)
    assert not any(r['kind'] == 'manor' for r in duo['outdoor'])
    assert not any(i['kind'] == 'manor' for i in duo['interiors'])
    floors = {i['floor'] for i in duo['interiors']}
    assert floors == set(range(2, 8)) and all(d['floor'] in floors | {m.OUTDOOR} and d['to_floor'] in floors | {m.OUTDOOR} for d in duo['doors'])
    # broken_walls are indices into outdoor, so both modes share the same prefix.
    assert solo['outdoor'][:len(duo['outdoor'])] == duo['outdoor']
    for x, y in m.STARTS[2:]:
        assert not m.blocked(m.OUTDOOR, *m.cell(x, y), DUO)
    assert not any(m.is_door(m.OUTDOOR, cx, cy, DUO) for _, x0, y0, x1, y1, _ in m.MANOR_RECTS
                   for cx in range(x0, x1+1) for cy in range(y0, y1+1))

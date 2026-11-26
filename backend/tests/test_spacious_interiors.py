from collections import deque

from app import rts_map as m
from app.squad_routes import SquadInput


def test_hanok_and_passage_dimensions_are_doubled():
    assert (len(m.HOUSE[0]), len(m.HOUSE)) == (32, 24)
    assert (len(m.PASSAGE[0]), len(m.PASSAGE)) == (48, 18)
    assert all(len(row) == len(rows[0]) for rows in (m.HOUSE, m.PASSAGE) for row in rows)


def test_enlarged_rooms_do_not_overlap_visually():
    boxes = [m.bounds(floor) for floor in m.INTERIORS]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] + 200 <= b[1] or b[3] + 200 <= a[1]


def test_wide_doorway_cells_all_use_the_same_exit():
    for floor, (ox, oy, rows, kind) in m.INTERIORS.items():
        if kind not in ('house', 'passage'):
            continue
        door_cells = [(ox+c, oy+r) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == 'D']
        assert len(door_cells) == (4 if kind == 'house' else 8)
        for cx, cy in door_cells:
            assert m.is_door(floor, cx, cy)
            target = m.DOOR_AT[(floor, cx, cy)]
            assert target['to_floor'] == m.OUTDOOR
            assert not m.blocked(m.OUTDOOR, *m.cell(target['to_x'], target['to_y']))


def test_all_walkable_space_and_chests_reachable_from_entry():
    for floor, (ox, oy, rows, kind) in m.INTERIORS.items():
        if kind not in ('house', 'passage'):
            continue
        entry = next(d for d in m.DOORS if d['floor'] == m.OUTDOOR and d['to_floor'] == floor)
        start = m.cell(entry['to_x'], entry['to_y'])
        seen, todo = {start}, deque([start])
        while todo:
            x, y = todo.popleft()
            for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if p not in seen and not m.blocked(floor, *p):
                    seen.add(p)
                    todo.append(p)
        walkable = {(ox+c,oy+r) for r,row in enumerate(rows) for c,_ in enumerate(row) if not m.blocked(floor,ox+c,oy+r)}
        assert walkable == seen
        assert all(m.cell(p['x'],p['y']) in seen for p in m.CHESTS if p['floor'] == floor)


def test_passage_has_six_cell_clear_central_spine():
    for r in range(6, 12):
        assert all(ch == '.' for ch in m.PASSAGE[r][1:-1])


def test_aim_accepts_the_new_interior_coordinate_range():
    payload = SquadInput(sequence=1, aim_x=9150, aim_y=14500)
    assert payload.aim_x == 9150 and payload.aim_y == 14500


def test_redesigned_rooms_have_breakable_furniture_and_three_chests():
    for floor, (_, _, _, kind) in m.INTERIORS.items():
        if kind in ('house', 'passage'):
            assert any(p['floor'] == floor and p['kind'] == 'table' for p in m.PROPS)
        if floor not in m.KEEP_FLOORS:
            assert len([c for c in m.CHESTS if c['floor'] == floor]) == 3

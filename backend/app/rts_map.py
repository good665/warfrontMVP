"""Shared logical board: one cell is 50 server units / one Unity unit.

The outdoor board is floor 1. Building interiors are separate floors placed off
the board (x >= 6800) so clients render them once and simply follow the hero.
"""
SIZE = 128
CELL = 50.
EXTENT = SIZE * CELL
STARTS = ((600., 600.), (5800., 5800.), (600., 5800.), (5800., 600.))
OUTDOOR = 1

# Top-left quadrant, inclusive cell rectangles. Mirrored on both axes so 1:1
# (diagonal bases) and 2:2 (left vs right) are equally fair.
QUADRANT = (
    ('house', 26, 8, 33, 15, (29, 15)),
    ('wall', 8, 26, 15, 33, None),
    ('wall', 36, 30, 44, 38, None),
    ('wall', 22, 40, 27, 50, None),
    # Village block: 2-3 cell alleys between house, sheds and the passage.
    ('wall', 36, 8, 41, 13, None),
    ('wall', 36, 17, 41, 24, None),
    ('wall', 45, 9, 52, 15, None),
    ('wall', 45, 19, 52, 26, None),
    ('wall', 22, 22, 26, 27, None),
    ('wall', 30, 42, 34, 50, None),
    ('wall', 48, 32, 53, 42, None),
    ('wall', 49, 46, 53, 51, None),
    ('water', 0, 54, 17, 57, None),     # bridge gap at x 18..21
    ('water', 22, 54, 44, 57, None),
    ('passage', 58, 18, 69, 27, (58, 22)),
    ('plaza', 48, 52, 79, 75, None),
    # Central cathedral on the plaza (Unity: Resources/Cathedral, real size 1 m = 1 cell): solid shell with the
    # 4-cell nave open at both ends (west/east), so waves that cross the map centre walk in one end and out the other.
    ('cathedral', 50, 56, 77, 71, None),
    ('nave', 50, 62, 77, 65, None),
)
# 1:1 only: vintage manors (Sketchfab living room) in the two corners 1:1 leaves empty (NE, SW; bases are NW/SE),
# a half turn apart so both players are equally far. One door each, facing into the board at the model's stair
# niche (column 15 of 20, beside the six-chair table).
MANOR_RECTS = (
    ('manor', 108, 0, 127, 11, (123, 11)),
    ('manor', 0, 116, 19, 127, (4, 116)),
)
SOLID = ('house', 'wall', 'passage', 'manor', 'cathedral')

def _room(width, height):
    return [['#' if c in (0, width-1) or r in (0, height-1) else '.'
             for c in range(width)] for r in range(height)]


def _furnish(rows, ch, cells):
    for c, r in cells:
        assert rows[r][c] == '.', (ch, c, r)
        rows[r][c] = ch


def _house_rows():
    rows = _room(32, 24)
    # Two ondol rooms open onto the broad central daecheong and front gathering hall.
    for c in (10, 21):
        for r in range(1, 14):
            if r not in range(7, 11): rows[r][c] = '#'
    for c in range(14, 18): rows[23][c] = 'D'
    _furnish(rows, 'K', [(2, 2), (3, 2), (4, 2), (26, 2), (27, 2), (28, 2)])
    _furnish(rows, 'T', [(4, 5), (5, 5), (4, 6), (5, 6), (25, 5), (26, 5), (25, 6), (26, 6)])
    _furnish(rows, 'S', [(3, 5), (6, 6), (24, 5), (27, 6)])
    _furnish(rows, 'C', [(27, 16), (4, 16), (16, 3)])  # three chests per building
    return tuple(''.join(row) for row in rows)


def _passage_rows():
    rows = _room(48, 18)
    # Six-cell-wide central route; screens and seating remain in the side bays.
    for c in (12, 24, 36):
        for r in (*range(1, 5), *range(13, 17)): rows[r][c] = '#'
    for r in range(7, 11): rows[r][0] = rows[r][47] = 'D'
    _furnish(rows, 'K', [(17, 2), (18, 2), (19, 2), (41, 15), (42, 15), (43, 15)])
    _furnish(rows, 'T', [(5, 3), (6, 3), (5, 4), (6, 4), (29, 13), (30, 13), (29, 14), (30, 14)])
    _furnish(rows, 'S', [(4, 3), (7, 4), (28, 13), (31, 14)])
    _furnish(rows, 'C', [(42, 3), (30, 3), (6, 14)])
    return tuple(''.join(row) for row in rows)


HOUSE = _house_rows()
PASSAGE = _passage_rows()
# Ray-cast in Blender from Resources/Manor/Interior.fbx over its bounds (20 x 12): '.' = floor clear of walls
# and furniture taller than ~0.3 m in game. North-east bay; the one door is the stair niche in the south wall.
# T/S/K/F: the breakable pieces (Unity matches the model's Object_* nodes to them): dining set (table + six chairs) at
# columns 11-13, coffee table at 4, armchair at 6, sofa at 3-4, bookcase on the back wall (row 3), glass cabinet on the
# angled wall, the green corner set (two small armchairs, side table, lamp; 15,1 and 16-18,2) and the fireplace in the south wall (row 11).
MANOR = (
    '####################',
    '#############K.S####',
    '############K...SSS#',
    '#.KKKKK...........##',
    '#.................##',
    '#..SS.............##',
    '#.....S.....T.....##',
    '#...T.S....TTT....##',
    '#.................##',
    '#.................##',
    '#.................##',
    '###FF##########D####',
)
_manor = [list(row) for row in MANOR]
_furnish(_manor, 'C', [(2, 9), (9, 4), (16, 8)])
MANOR = tuple(''.join(row) for row in _manor)
# Breakable manor furniture (axe; squad_items.AXE). Blocks walking, not sight, until broken. Touching cells (diagonals
# too) with the same letter are one piece. The fireplace sits in the wall line, so breaking it never opens its cells.
PROP_KINDS = dict(T='table', S='chair', K='cabinet', F='fireplace')
SOLID_PROPS = frozenset({'fireplace'})
ROWS = dict(house=HOUSE, passage=PASSAGE, manor=MANOR)
INTERIOR_X = 136  # cell column of every interior origin (6800 units)
INTERIOR_STRIDE = 40  # enlarged rooms remain separated in the shared visual world


def _door_groups(rows):
    """Contiguous D cells are one wide doorway, represented by its middle cell."""
    remaining = {(c, r) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == 'D'}
    groups = []
    while remaining:
        first = min(remaining); remaining.remove(first)
        group, todo = [first], [first]
        while todo:
            c, r = todo.pop()
            for cell_ in ((c-1, r), (c+1, r), (c, r-1), (c, r+1)):
                if cell_ in remaining:
                    remaining.remove(cell_); group.append(cell_); todo.append(cell_)
        mx, my = sum(c for c, _ in group)/len(group), sum(r for _, r in group)/len(group)
        center = min(group, key=lambda p: ((p[0]-mx)**2+(p[1]-my)**2, p))
        groups.append((center, tuple(sorted(group))))
    return sorted(groups)


def _mirror(kind, x0, y0, x1, y1, door):
    out = set()
    for fx in (False, True):
        for fy in (False, True):
            a0, a1 = (SIZE-1-x1, SIZE-1-x0) if fx else (x0, x1)
            b0, b1 = (SIZE-1-y1, SIZE-1-y0) if fy else (y0, y1)
            d = None
            if door:
                d = (SIZE-1-door[0] if fx else door[0], SIZE-1-door[1] if fy else door[1])
            out.add((kind, a0, b0, a1, b1, d))
    return out


# Manors go last so the shared prefix (wall indices used by broken_walls, floors 2-7) is the same in both modes.
SHARED_RECTS = sorted({r for q in QUADRANT for r in _mirror(*q)}, key=lambda r: (r[0], r[2], r[1]))
RECTS = SHARED_RECTS + list(MANOR_RECTS)


def _pieces(floor, ox, oy, rows):
    """Group touching same-letter furniture cells into pieces; cells are absolute (cx, cy)."""
    seen, out = set(), []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch not in PROP_KINDS or (c, r) in seen: continue
            todo, cells = [(c, r)], []
            seen.add((c, r))
            while todo:
                a, b = todo.pop()
                cells.append((ox+a, oy+b))
                for n in ((a+da, b+db) for da in (-1, 0, 1) for db in (-1, 0, 1) if da or db):
                    if 0 <= n[1] < len(rows) and 0 <= n[0] < len(rows[0]) and rows[n[1]][n[0]] == ch and n not in seen:
                        seen.add(n); todo.append(n)
            cells.sort()
            out.append(dict(id=f'prop-{floor}-{c}-{r}', kind=PROP_KINDS[ch], floor=floor, cx=ox+c, cy=oy+r,
                            cells=[list(x) for x in cells],
                            x=(sum(x for x, _ in cells)/len(cells)+.5)*CELL, y=(sum(y for _, y in cells)/len(cells)+.5)*CELL))
    return out


def _build():
    solid, water, interiors = set(), set(), {}
    for kind, x0, y0, x1, y1, door in RECTS:
        cells = {(x, y) for x in range(x0, x1+1) for y in range(y0, y1+1)}
        if kind in SOLID: solid |= cells
        elif kind == 'water': water |= cells
    for kind, x0, y0, x1, y1, _ in RECTS:
        if kind == 'nave': solid -= {(x, y) for x in range(x0, x1+1) for y in range(y0, y1+1)}
    doors, chests, props, floor = [], [], [], 1
    # A passage straddles the x mirror line, so its two mirrored copies are one
    # building with two doors.
    order = lambda r: (r[0] == 'manor', r[0] != 'house', r[2], r[1])
    buildings = sorted({r[:5] for r in RECTS if r[0] in ROWS}, key=order)
    for kind, x0, y0, x1, y1 in buildings:
        floor += 1
        outer = sorted(r[5] for r in RECTS if r[:5] == (kind, x0, y0, x1, y1))
        rows = ROWS[kind]
        # A manor entered from its north side gets the interior turned half round, so the way out is on the same side.
        if kind == 'manor' and outer[0][1] == y0:
            rows = tuple(row[::-1] for row in reversed(rows))
        ox, oy = INTERIOR_X, (floor-2) * INTERIOR_STRIDE
        interiors[floor] = (ox, oy, rows, kind)
        inner = [center for center, _ in _door_groups(rows)]
        # Doors pair west-to-east with the interior's 'D' cells.
        for (c, r), (cx, cy) in zip(inner, outer):
            solid.discard((cx, cy))
            dx = -1 if cx == x0 else 1 if cx == x1 else 0
            dy = 0 if dx else (-1 if cy == y0 else 1)
            ic, ir = next((c+a, r+b) for a, b in ((0, -1), (1, 0), (-1, 0), (0, 1))
                          if 0 <= r+b < len(rows) and 0 <= c+a < len(rows[0]) and rows[r+b][c+a] in '.C')
            doors.append(dict(floor=OUTDOOR, cx=cx, cy=cy, to_floor=floor,
                              to_x=(ox+ic+.5)*CELL, to_y=(oy+ir+.5)*CELL))
            doors.append(dict(floor=floor, cx=ox+c, cy=oy+r, to_floor=OUTDOOR,
                              to_x=(cx+2*dx+.5)*CELL, to_y=(cy+2*dy+.5)*CELL))
        chests += [dict(id=f'chest-{floor}-{c}-{r}', floor=floor, x=(ox+c+.5)*CELL, y=(oy+r+.5)*CELL)
                   for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == 'C']
        props += _pieces(floor, ox, oy, rows)
    return frozenset(solid), frozenset(water), doors, chests, props, interiors


SOLID_CELLS, WATER_CELLS, DOORS, CHESTS, PROPS, INTERIORS = _build()
DOOR_AT = {(d['floor'], d['cx'], d['cy']): d for d in DOORS}
NAVE = next(r[1:5] for r in RECTS if r[0] == 'nave')  # x0, y0, x1, y1 cells
for _floor, (_ox, _oy, _rows, _) in INTERIORS.items():
    for (_c, _r), _cells in _door_groups(_rows):
        _door = DOOR_AT[(_floor, _ox+_c, _oy+_r)]
        for _a, _b in _cells:
            DOOR_AT[(_floor, _ox+_a, _oy+_b)] = dict(_door, cx=_ox+_a, cy=_oy+_b)
MANOR_CELLS = frozenset((x, y) for _, x0, y0, x1, y1, _ in MANOR_RECTS for x in range(x0, x1+1) for y in range(y0, y1+1))
MANOR_FLOORS = frozenset(f for f, i in INTERIORS.items() if i[3] == 'manor')


def closed_for(team_size):
    """Outdoor cells a match starts with 'opened': 2:2 uses all four corners for bases, so no manors."""
    return set() if team_size == 1 else set(MANOR_CELLS)


def cell(x, y):
    return int(x // CELL), int(y // CELL)


def _interior_char(floor, cx, cy):
    ox, oy, rows, _ = INTERIORS[floor]
    c, r = cx - ox, cy - oy
    return rows[r][c] if 0 <= r < len(rows) and 0 <= c < len(rows[0]) else '#'


def blocked(floor, cx, cy, opened=frozenset()):
    """opened: outdoor wall cells (x, y) a match has destroyed (long whip) and broken furniture (floor, x, y) (axe)."""
    if floor == OUTDOOR:
        return (not (0 <= cx < SIZE and 0 <= cy < SIZE) or (cx, cy) in WATER_CELLS
                or (cx, cy) in SOLID_CELLS and (cx, cy) not in opened)
    if floor not in INTERIORS: return True
    ch = _interior_char(floor, cx, cy)
    return ch == '#' or ch in PROP_KINDS and (floor, cx, cy) not in opened


def sight_blocked(floor, cx, cy, opened=frozenset()):
    if floor == OUTDOOR:
        return not (0 <= cx < SIZE and 0 <= cy < SIZE) or (cx, cy) in SOLID_CELLS and (cx, cy) not in opened
    return floor not in INTERIORS or _interior_char(floor, cx, cy) == '#'  # furniture is low: see over it


def is_door(floor, cx, cy, opened=frozenset()):
    """A door cell that is 'opened' (2:2 manor footprint) is plain ground."""
    return (floor, cx, cy) in DOOR_AT and not (floor == OUTDOOR and (cx, cy) in opened)


def bounds(floor):
    if floor == OUTDOOR:
        return 35., 35., EXTENT-35, EXTENT-35
    ox, oy, rows, _ = INTERIORS[floor]
    return ox*CELL, oy*CELL, (ox+len(rows[0]))*CELL, (oy+len(rows))*CELL


# Includes room coordinates plus aiming beyond a far wall; outdoor order bounds stay unchanged.
AIM_LIMIT = max(EXTENT, *(max(bounds(floor)) for floor in INTERIORS)) + 1000.


def map_payload(team_size=1):
    rect = lambda kind, x0, y0, x1, y1: dict(kind=kind, x=x0*CELL, y=y0*CELL, width=(x1-x0+1)*CELL, height=(y1-y0+1)*CELL)
    manors = sorted({r[:5] for r in MANOR_RECTS}, key=lambda r: (r[2], r[1])) if team_size == 1 else []
    floors = {f for f in INTERIORS if team_size == 1 or f not in MANOR_FLOORS}
    return dict(version='squad-map-interiors-2', cell=CELL,
                outdoor=[rect(*r[:5]) for r in SHARED_RECTS] + [rect(*r) for r in manors],
                interiors=[dict(floor=f, x=ox*CELL, y=oy*CELL, rows=list(rows), kind=kind) for f, (ox, oy, rows, kind) in sorted(INTERIORS.items()) if f in floors],
                doors=[dict(d) for d in DOORS if d['floor'] in floors | {OUTDOOR} and d['to_floor'] in floors | {OUTDOOR}],
                chests=[dict(c) for c in CHESTS if c['floor'] in floors],
                props=[dict(p) for p in PROPS if p['floor'] in floors])


def resource_points(x, y):
    sx, sy = (1 if x < EXTENT / 2 else -1), (1 if y < EXTENT / 2 else -1)
    return [dict(x=x + sx * (180 + i * 70), y=y + sy * 200) for i in range(5)]

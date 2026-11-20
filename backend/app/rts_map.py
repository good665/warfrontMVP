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
    ('plaza', 56, 56, 71, 71, None),
)
# 1:1 only: vintage manors (Sketchfab living room) in the two corners 1:1 leaves empty (NE, SW; bases are NW/SE),
# a half turn apart so both players are equally far. One door each, facing into the board at the model's stair
# niche (column 15 of 20, beside the six-chair table).
MANOR_RECTS = (
    ('manor', 108, 0, 127, 11, (123, 11)),
    ('manor', 0, 116, 19, 127, (4, 116)),
)
SOLID = ('house', 'wall', 'passage', 'manor')

HOUSE = (
    '################',
    '#..C...#.......#',
    '#......#..###..#',
    '#......#..#....#',
    '#..##..........#',
    '#..##...####...#',
    '#.......#......#',
    '####..###..##..#',
    '#..........##..#',
    '#..####........#',
    '#.......D......#',
    '################',
)
PASSAGE = (
    '########################',
    '#....#.........#.......#',
    '#....#..####...#..##...#',
    'D......#..C.#.......#..D',
    '#..##..#....####..###..#',
    '#..##.....#............#',
    '#.....###.#..#####..#..#',
    '#..........#..........##',
    '########################',
)
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
# Breakable manor furniture (axe; squad_items.AXE). Blocks walking, not sight, until broken. Touching cells (diagonals
# too) with the same letter are one piece. The fireplace sits in the wall line, so breaking it never opens its cells.
PROP_KINDS = dict(T='table', S='chair', K='cabinet', F='fireplace')
SOLID_PROPS = frozenset({'fireplace'})
ROWS = dict(house=HOUSE, passage=PASSAGE, manor=MANOR)
INTERIOR_X = 136  # cell column of every interior origin (6800 units)


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
        ox, oy = INTERIOR_X, (floor-2) * 20
        interiors[floor] = (ox, oy, rows, kind)
        inner = sorted((c, r) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == 'D')
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


def map_payload(team_size=1):
    rect = lambda kind, x0, y0, x1, y1: dict(kind=kind, x=x0*CELL, y=y0*CELL, width=(x1-x0+1)*CELL, height=(y1-y0+1)*CELL)
    manors = sorted({r[:5] for r in MANOR_RECTS}, key=lambda r: (r[2], r[1])) if team_size == 1 else []
    floors = {f for f in INTERIORS if team_size == 1 or f not in MANOR_FLOORS}
    return dict(version='squad-map-1', cell=CELL,
                outdoor=[rect(*r[:5]) for r in SHARED_RECTS] + [rect(*r) for r in manors],
                interiors=[dict(floor=f, x=ox*CELL, y=oy*CELL, rows=list(rows), kind=kind) for f, (ox, oy, rows, kind) in sorted(INTERIORS.items()) if f in floors],
                doors=[dict(d) for d in DOORS if d['floor'] in floors | {OUTDOOR} and d['to_floor'] in floors | {OUTDOOR}],
                chests=[dict(c) for c in CHESTS if c['floor'] in floors],
                props=[dict(p) for p in PROPS if p['floor'] in floors])


def resource_points(x, y):
    sx, sy = (1 if x < EXTENT / 2 else -1), (1 if y < EXTENT / 2 else -1)
    return [dict(x=x + sx * (180 + i * 70), y=y + sy * 200) for i in range(5)]

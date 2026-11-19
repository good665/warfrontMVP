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
SOLID = ('house', 'wall', 'passage')

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


RECTS = sorted({r for q in QUADRANT for r in _mirror(*q)}, key=lambda r: (r[0], r[2], r[1]))


def _build():
    solid, water, interiors = set(), set(), {}
    for kind, x0, y0, x1, y1, door in RECTS:
        cells = {(x, y) for x in range(x0, x1+1) for y in range(y0, y1+1)}
        if kind in SOLID: solid |= cells
        elif kind == 'water': water |= cells
    doors, chests, floor = [], [], 1
    # A passage straddles the x mirror line, so its two mirrored copies are one
    # building with two doors.
    buildings = sorted({r[:5] for r in RECTS if r[0] in ('house', 'passage')},
                       key=lambda r: (r[0] != 'house', r[2], r[1]))
    for kind, x0, y0, x1, y1 in buildings:
        floor += 1
        rows = HOUSE if kind == 'house' else PASSAGE
        ox, oy = INTERIOR_X, (floor-2) * 20
        interiors[floor] = (ox, oy, rows)
        inner = sorted((c, r) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == 'D')
        # Doors pair west-to-east with the interior's 'D' cells.
        outer = sorted(r[5] for r in RECTS if r[:5] == (kind, x0, y0, x1, y1))
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
    return frozenset(solid), frozenset(water), doors, chests, interiors


SOLID_CELLS, WATER_CELLS, DOORS, CHESTS, INTERIORS = _build()
DOOR_AT = {(d['floor'], d['cx'], d['cy']): d for d in DOORS}


def cell(x, y):
    return int(x // CELL), int(y // CELL)


def _interior_char(floor, cx, cy):
    ox, oy, rows = INTERIORS[floor]
    c, r = cx - ox, cy - oy
    return rows[r][c] if 0 <= r < len(rows) and 0 <= c < len(rows[0]) else '#'


def blocked(floor, cx, cy, opened=frozenset()):
    """opened: outdoor wall cells a match has destroyed (long whip)."""
    if floor == OUTDOOR:
        return (not (0 <= cx < SIZE and 0 <= cy < SIZE) or (cx, cy) in WATER_CELLS
                or (cx, cy) in SOLID_CELLS and (cx, cy) not in opened)
    return floor not in INTERIORS or _interior_char(floor, cx, cy) == '#'


def sight_blocked(floor, cx, cy, opened=frozenset()):
    if floor == OUTDOOR:
        return not (0 <= cx < SIZE and 0 <= cy < SIZE) or (cx, cy) in SOLID_CELLS and (cx, cy) not in opened
    return blocked(floor, cx, cy)


def is_door(floor, cx, cy):
    return (floor, cx, cy) in DOOR_AT


def bounds(floor):
    if floor == OUTDOOR:
        return 35., 35., EXTENT-35, EXTENT-35
    ox, oy, rows = INTERIORS[floor]
    return ox*CELL, oy*CELL, (ox+len(rows[0]))*CELL, (oy+len(rows))*CELL


def map_payload():
    rect = lambda kind, x0, y0, x1, y1: dict(kind=kind, x=x0*CELL, y=y0*CELL, width=(x1-x0+1)*CELL, height=(y1-y0+1)*CELL)
    return dict(version='squad-map-1', cell=CELL,
                outdoor=[rect(*r[:5]) for r in RECTS],
                interiors=[dict(floor=f, x=ox*CELL, y=oy*CELL, rows=list(rows)) for f, (ox, oy, rows) in sorted(INTERIORS.items())],
                doors=[dict(d) for d in DOORS], chests=[dict(c) for c in CHESTS])


def resource_points(x, y):
    sx, sy = (1 if x < EXTENT / 2 else -1), (1 if y < EXTENT / 2 else -1)
    return [dict(x=x + sx * (180 + i * 70), y=y + sy * 200) for i in range(5)]

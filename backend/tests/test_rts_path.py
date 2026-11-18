from app import rts_map as m
from app.rts_path import find_path, line_clear, nearest_open

C = m.CELL


def c(cx, cy):
    return (cx + .5) * C, (cy + .5) * C


def walk_cells(floor, start, path):
    """Every cell touched while walking the waypoints in straight lines."""
    cells, (x, y) = [], start
    for p in path:
        steps = max(1, int(max(abs(p['x']-x), abs(p['y']-y)) // 10))
        for i in range(1, steps+1):
            cells.append(m.cell(x + (p['x']-x)*i/steps, y + (p['y']-y)*i/steps))
        x, y = p['x'], p['y']
    return cells


def test_path_goes_around_wall():
    # Wall block x 36..44, y 30..38: go from its west side to its east side.
    start, goal = c(34, 34), c(46, 34)
    path = find_path(m.OUTDOOR, *start, *goal)
    assert path and (path[-1]['x'], path[-1]['y']) == goal
    assert not any(m.blocked(m.OUTDOOR, *cell) for cell in walk_cells(m.OUTDOOR, start, path))


def test_path_never_cuts_corners():
    start, goal = c(35, 29), c(45, 39)  # diagonal past both wall corners
    path = find_path(m.OUTDOOR, *start, *goal)
    assert not any(m.blocked(m.OUTDOOR, *cell) for cell in walk_cells(m.OUTDOOR, start, path))


def test_blocked_goal_uses_nearest_open_cell():
    x, y = nearest_open(m.OUTDOOR, *c(40, 34))
    assert not m.blocked(m.OUTDOOR, *m.cell(x, y))
    path = find_path(m.OUTDOOR, *c(30, 34), *c(40, 34))
    assert (path[-1]['x'], path[-1]['y']) == (x, y)


def test_same_cell_is_empty_path():
    assert find_path(m.OUTDOOR, 610, 610, 620, 620) == []


def test_line_of_sight():
    assert not line_clear(m.OUTDOOR, *c(34, 34), *c(46, 34))  # through wall
    assert line_clear(m.OUTDOOR, *c(5, 52), *c(5, 59))        # across water
    assert line_clear(m.OUTDOOR, *c(5, 5), *c(15, 15))

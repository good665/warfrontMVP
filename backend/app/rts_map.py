"""Shared logical board: one cell is 50 server units / one Unity unit."""
SIZE = 128
CELL = 50.
EXTENT = SIZE * CELL
STARTS = ((600., 600.), (5800., 5800.), (600., 5800.), (5800., 600.))


def resource_points(x, y):
    sx, sy = (1 if x < EXTENT / 2 else -1), (1 if y < EXTENT / 2 else -1)
    return [dict(x=x + sx * (180 + i * 70), y=y + sy * 200) for i in range(5)]

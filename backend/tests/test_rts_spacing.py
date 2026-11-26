import math
import pytest
from app.rts_game import RtsGame


def closest(units):
    return min(math.hypot(a['x']-b['x'], a['y']-b['y'])
               for i, a in enumerate(units) for b in units[i+1:])


@pytest.mark.parametrize('point', [(1500, 600), (35, 35)])
def test_stacked_minions_separate_even_at_map_edge(point):
    game = RtsGame(['a', 'b'])
    game.tick(30)
    units = [u for u in game.minions.values() if u['owner_id'] == 'a']
    for unit in units:
        unit.update(x=point[0], y=point[1], command='hold')
    for _ in range(40):
        game.tick(.05)
    assert closest(units) >= 79
    assert all(35 <= u['x'] <= 6365 and 35 <= u['y'] <= 6365 for u in units)


@pytest.mark.parametrize('hero_point', [(800, 800), (750, 750), (1200, 1200)])
def test_hero_on_or_before_waypoint_does_not_block_wave(hero_point):
    game = RtsGame(['a', 'b'])
    game.heroes['a'].update(x=hero_point[0], y=hero_point[1])
    game.tick(30)
    for _ in range(200):
        game.tick(.05)
    hero = game.heroes['a']
    units = [u for u in game.minions.values() if u['owner_id'] == 'a']
    assert (hero['x'], hero['y']) == hero_point
    assert all(math.hypot(u['x']-800, u['y']-800) > 1000 for u in units)
    assert closest(units) >= 78


def test_separation_does_not_change_ownership_or_manual_orders():
    game = RtsGame(['a', 'b', 'c', 'd'], team_size=2)
    game.tick(30)
    units = [u for u in game.minions.values() if u['team'] == 0]
    for u in units:
        u.update(x=1600, y=1200, command='hold')
    before = [(u['id'], u['owner_id'], u['team'], u['order_x'], u['order_y']) for u in units]
    for _ in range(40):
        game.tick(.05)
    assert closest(units) >= 79
    assert before == [(u['id'], u['owner_id'], u['team'], u['order_x'], u['order_y']) for u in units]
    assert all(u['command'] == 'hold' for u in units)


@pytest.mark.parametrize('hero_point', [(750, 750), (1200, 1200)])
def test_single_minion_can_walk_around_hero_without_crowd_pushing(hero_point):
    game = RtsGame(['a', 'b'])
    game.heroes['a'].update(x=hero_point[0], y=hero_point[1])
    game.tick(30)
    unit = next(u for u in game.minions.values() if u['owner_id'] == 'a')
    for other in game.minions.values():
        if other is not unit:
            other['hp'] = 0
    unit.update(x=600, y=600)
    for _ in range(400):
        game.tick(.05)
    assert unit['_waypoint'] > 0
    assert unit['x'] > 2200 and unit['y'] > 2200


@pytest.mark.parametrize('start,obstacle,goal', [
    ((1000, 35), (1200, 35), (2000, 35)),
    ((1000, 6365), (1200, 6365), (2000, 6365)),
    ((35, 1000), (35, 1200), (35, 2000)),
    ((6365, 1000), (6365, 1200), (6365, 2000)),
])
def test_minion_chooses_clear_side_of_hero_at_map_boundary(start, obstacle, goal):
    game = RtsGame(['a', 'b'])
    game.tick(30)
    unit = next(u for u in game.minions.values() if u['owner_id'] == 'a')
    for other in game.minions.values():
        if other is not unit:
            other['hp'] = 0
    game.heroes['a'].update(x=obstacle[0], y=obstacle[1])
    unit.update(x=start[0], y=start[1])
    game.input('a', dict(sequence=1, command='move', unit_ids=[unit['id']], order_x=goal[0], order_y=goal[1]))
    for _ in range(200):
        game.tick(.05)
    assert math.hypot(unit['x']-goal[0], unit['y']-goal[1]) < 10

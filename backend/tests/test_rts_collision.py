import math
import random
from app import rts_map as m
from app.rts_game import RtsGame
from app.rts_combat import distance

C = m.CELL


def c(cx, cy):
    return (cx + .5) * C, (cy + .5) * C


def in_wall(a):
    return m.blocked(a['floor'], *m.cell(a['x'], a['y']))


def test_move_slides_along_wall():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero['x'], hero['y'] = c(35, 34)  # wall block starts at x cell 36
    y0 = hero['y']
    for _ in range(20):
        game.move(hero, hero['x'] + 1000, hero['y'] + 300, 245, .05)
    assert hero['x'] < 36 * C and hero['y'] > y0 + 50


def test_move_never_enters_blocked():
    game = RtsGame(['a', 'b'])
    hero, rng = game.heroes['a'], random.Random(3)
    for _ in range(1000):
        game.move(hero, rng.uniform(0, m.EXTENT), rng.uniform(0, m.EXTENT), 245, rng.uniform(.05, 1))
        assert not in_wall(hero)


def test_dash_stops_at_wall():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero['x'], hero['y'] = c(20, 24)  # shed x 22..26 is 5 cells = 250 units thick
    game.move(hero, hero['x'] + 280, hero['y'], 280, 1.)
    assert hero['x'] < 22 * C and not in_wall(hero)


def test_ordered_unit_walks_around_building():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero['x'], hero['y'] = c(34, 34)
    goal = c(46, 34)
    game.input('a', dict(sequence=1, command='move', unit_ids=['a'], order_x=goal[0], order_y=goal[1]))
    for _ in range(1200):
        game.tick(.05)
        if math.hypot(hero['x'] - goal[0], hero['y'] - goal[1]) < 30: break
    assert math.hypot(hero['x'] - goal[0], hero['y'] - goal[1]) < 30


def test_waves_reach_enemy_base():
    game = RtsGame(['a', 'b'])
    enemy_base = game.home('b')
    game.heroes['b'].update(hp=0, respawn_left=1e9)
    reached = False
    for _ in range(int(180 / .05)):
        game.tick(.05)
        for uid in [u for u, a in game.minions.items() if a['team'] == 1]:
            game.minions.pop(uid); game.units.pop(uid)
        if any(a['team'] == 0 and distance(a, enemy_base) < 420 for a in game.minions.values()):
            reached = True; break
    assert reached


def test_separation_keeps_out_of_walls():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero['x'], hero['y'] = c(35, 34)
    unit = game.actor('g1', 'guard', 0, hero['x'] + 5, hero['y'], 180, 1)
    unit.update(owner_id='a', command='hold')
    game.units['g1'] = game.minions['g1'] = unit
    game.separate_units()
    assert not in_wall(unit)


def test_unit_ordered_onto_door_stops_nearby():
    game = RtsGame(['a', 'b'])
    door = next(d for d in m.DOORS if d['floor'] == m.OUTDOOR and (d['cx'], d['cy']) == (29, 15))
    unit = game.actor('g1', 'guard', 0, *c(29, 19), 180, 1)
    unit.update(owner_id='a', command='hold')
    game.units['g1'] = game.minions['g1'] = unit
    game.input('a', dict(sequence=1, command='move', unit_ids=['g1'], order_x=c(29, 15)[0], order_y=c(29, 15)[1]))
    for _ in range(400):
        game.tick(.05)
    assert unit['floor'] == m.OUTDOOR
    assert m.cell(unit['x'], unit['y']) != (door['cx'], door['cy'])
    assert math.hypot(unit['x'] - c(29, 15)[0], unit['y'] - c(29, 15)[1]) < 150

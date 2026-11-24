import math
import pytest

from app import rts_map as m
from app.rts_game import RtsGame
from app.squad_items import AXE, grant


def first_cell(prop):
    cx, cy = prop['cells'][0]
    return dict(x=(cx + .5) * m.CELL, y=(cy + .5) * m.CELL)


def beside(game, hero, prop):
    """Stand the hero on an open cell next to the piece's first cell."""
    cx, cy = prop['cells'][0]
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        if not m.blocked(prop['floor'], cx + dx, cy + dy, game.opened):
            hero.update(floor=prop['floor'], x=(cx + dx + .5) * m.CELL, y=(cy + dy + .5) * m.CELL, fx=dx, fy=dy,
                        protected=0)  # facing away: the swing must turn toward the aim
            return
    raise AssertionError('furniture with no open side')


def use_axe(game, pid, at):
    hero = game.heroes[pid]
    grant(hero, 'axe')
    game.input(pid, dict(sequence=hero['sequence'] + 1, item=2, aim_x=at['x'], aim_y=at['y']))
    game.tick(.05)


def near_prop(seed=3):
    game = RtsGame(['a', 'b'], seed=seed)
    hero, prop = game.heroes['a'], m.PROPS[0]
    beside(game, hero, prop)
    return game, hero, prop


def test_axe_is_one_swing_not_gear():
    game, hero, prop = near_prop()
    use_axe(game, 'a', first_cell(prop))
    assert hero['_bag'][0] == '' and hero['weapon'] == ''
    assert hero['action_kind'] == 'axe' and 0 < hero['axe_left'] <= AXE['swing']
    for _ in range(int(AXE['swing'] / .05) + 2): game.tick(.05)
    assert hero['axe_left'] == 0


def test_map_ships_furniture_that_blocks_walking_but_not_sight():
    props = m.map_payload(1)['props']
    assert props and {p['kind'] for p in props} == {'table', 'chair', 'cabinet', 'fireplace'}
    assert all(p['floor'] in m.INTERIORS for p in props)
    assert all(any(p['floor'] == floor for p in props) for floor, room in m.INTERIORS.items() if room[3] in ('house', 'passage'))
    p = props[0]
    assert m.blocked(p['floor'], p['cx'], p['cy']) and not m.sight_blocked(p['floor'], p['cx'], p['cy'])
    assert not any(p['floor'] in m.MANOR_FLOORS for p in m.map_payload(2)['props'])  # no manors in 2:2


def test_each_manor_has_its_furniture_pieces():
    for floor in m.MANOR_FLOORS:
        pieces = [p for p in m.PROPS if p['floor'] == floor]
        assert sorted((p['kind'], len(p['cells'])) for p in pieces) == [
            ('cabinet', 2), ('cabinet', 5), ('chair', 2), ('chair', 2), ('chair', 4), ('fireplace', 2), ('table', 1), ('table', 4)]


def test_broken_fireplace_stays_solid():
    game = RtsGame(['a', 'b'], seed=3)
    hero = game.heroes['a']
    fire = next(p for p in m.PROPS if p['kind'] == 'fireplace')
    cx, cy = fire['cells'][0]
    hero.update(floor=fire['floor'], x=(cx + .5) * m.CELL, y=(cy - .5) * m.CELL, fx=0., fy=1., protected=0)
    use_axe(game, 'a', dict(x=(cx + .5) * m.CELL, y=(cy + .5) * m.CELL))
    assert fire['id'] in game.broken_props and all(m.blocked(fire['floor'], x, y, game.opened) for x, y in fire['cells'])


def test_fireplace_loot_lands_on_open_floor_away_from_the_hero():
    game = RtsGame(['a', 'b'], seed=3)
    hero = game.heroes['a']
    fire = next(p for p in m.PROPS if p['kind'] == 'fireplace')
    cx, cy = fire['cells'][0]
    hero.update(floor=fire['floor'], x=(cx + .5) * m.CELL, y=(cy - .5) * m.CELL, fx=0., fy=1., protected=0)
    game.rng.random = lambda: 0.
    use_axe(game, 'a', dict(x=(cx + .5) * m.CELL, y=(cy + .5) * m.CELL))
    loot = [g for g in game.ground if g['floor'] == fire['floor']]
    assert len(loot) == 1
    assert all(not m.blocked(fire['floor'], *m.cell(g['x'], g['y']), game.opened) for g in loot)
    assert all(m.cell(g['x'], g['y']) != m.cell(hero['x'], hero['y']) for g in loot)


def test_multi_cell_table_breaks_as_one_piece():
    game = RtsGame(['a', 'b'], seed=3)
    hero = game.heroes['a']
    table = next(p for p in m.PROPS if p['floor'] in m.MANOR_FLOORS and len(p['cells']) == 4)
    beside(game, hero, table)
    use_axe(game, 'a', first_cell(table))
    assert table['id'] in game.broken_props
    assert all(not m.blocked(table['floor'], cx, cy, game.opened) for cx, cy in table['cells'])


def test_swing_smashes_the_aimed_furniture_and_can_drop_one_item():
    game, hero, prop = near_prop()
    game.rng.random = lambda: 0.  # always lucky
    use_axe(game, 'a', first_cell(prop))
    assert prop['id'] in game.broken_props and game.snapshot('b', 'R', 0)['broken_props'] == [prop['id']]
    assert not game.closed(hero, prop['x'], prop['y'])
    loot = [g for g in game.ground if g['floor'] == prop['floor']]
    assert len(loot) == 1 and all(list(m.cell(g['x'], g['y'])) in prop['cells'] for g in loot)
    assert all(g['_by'] == '' for g in loot)  # anyone can grab it, the smasher included


@pytest.mark.parametrize('roll, item', [(0., 'fitted_armor_pig'), (.0499, 'fitted_armor_pig'), (.05, 'weapon_pig'),
                                        (.0999, 'weapon_pig'), (.1, None)])
def test_loot_is_fitted_armor_5_percent_zodiac_weapon_5_percent_else_nothing(roll, item):
    game, hero, prop = near_prop()
    game.rng.random = lambda: roll
    game.rng.choice = lambda options: 'pig'  # any of the 12 zodiacs
    use_axe(game, 'a', first_cell(prop))
    assert [g['item'] for g in game.ground] == ([item] if item else [])
    assert len(game.snapshot('a', 'R', 0)['ground_items']) == (1 if item else 0)


def test_unlucky_smash_drops_nothing():
    game, hero, prop = near_prop()
    game.rng.random = lambda: .99
    use_axe(game, 'a', first_cell(prop))
    assert prop['id'] in game.broken_props and game.ground == []


def test_hero_can_walk_while_swinging():
    game, hero, prop = near_prop()
    use_axe(game, 'a', first_cell(prop))
    start = (hero['x'], hero['y'])
    cx, cy = m.cell(*start)
    dx, dy = next(d for d in ((1, 0), (-1, 0), (0, 1), (0, -1)) if not m.blocked(hero['floor'], cx + d[0], cy + d[1], game.opened))
    for i in range(10):
        game.input('a', dict(sequence=hero['sequence'] + 1, move_x=dx, move_y=dy))
        game.tick(.05)
    assert hero['axe_left'] > 0 and (hero['x'], hero['y']) != start


def test_basic_attacks_never_break_furniture():
    game, hero, prop = near_prop()
    at = first_cell(prop)
    for i in range(3):
        game.input('a', dict(sequence=hero['sequence'] + 1, attack=True, aim_x=at['x'], aim_y=at['y']))
        game.tick(.6)
    assert game.broken_props == [] and game.closed(hero, at['x'], at['y'])


def manor_spot(c, r, floor=None):
    """Server point at manor row/col (c, r) of the NE manor (rows as written in rts_map.MANOR)."""
    floor = floor or min(m.MANOR_FLOORS)
    ox, oy, _, _ = m.INTERIORS[floor]
    return floor, ((ox + c + .5) * m.CELL, (oy + r + .5) * m.CELL)


def piece_at(floor, c, r):
    ox, oy, _, _ = m.INTERIORS[floor]
    return next(p for p in m.PROPS if [ox + c, oy + r] in p['cells'])


def test_one_chop_breaks_every_piece_in_reach():
    game = RtsGame(['a', 'b'], seed=3)
    hero = game.heroes['a']
    floor, (x, y) = manor_spot(5, 6)  # between the armchair (6,6) and the coffee table (4,7)
    hero.update(floor=floor, x=x, y=y, fx=0., fy=1., protected=0)
    use_axe(game, 'a', dict(x=x, y=y + 100))
    broken = set(game.broken_props)
    assert {piece_at(floor, 6, 6)['id'], piece_at(floor, 4, 7)['id']} <= broken
    assert piece_at(floor, 4, 5)['id'] not in broken  # the sofa is behind the hero


def test_walking_through_the_swing_breaks_what_it_meets_until_the_swing_ends():
    game = RtsGame(['a', 'b'], seed=3)
    hero = game.heroes['a']
    floor, (x, y) = manor_spot(8, 7)  # open floor three cells left of the dining table
    hero.update(floor=floor, x=x, y=y, fx=1., fy=0., protected=0)
    use_axe(game, 'a', dict(x=x + 100, y=y))
    table = piece_at(floor, 11, 7)
    assert table['id'] not in game.broken_props  # out of reach at the first chop
    for _ in range(int(AXE['swing'] / .05)):
        game.input('a', dict(sequence=hero['sequence'] + 1, move_x=1, aim_x=hero['x'] + 100, aim_y=hero['y']))
        game.tick(.05)
    assert table['id'] in game.broken_props
    for _ in range(4): game.tick(.05)
    assert hero['axe_left'] == 0
    before = list(game.broken_props)
    hero.update(x=x, y=y, fx=-1., fy=0.)  # facing the coffee table side with the axe put away
    game.tick(.05)
    assert game.broken_props == before

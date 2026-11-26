from app.rts_game import RtsGame
from app.rts_combat import XP, MAX_LEVEL, xp_next


def test_hero_kill_and_assist_give_xp_and_level_up_grows_stats():
    game = RtsGame(['a', 'b', 'c', 'd'], team_size=2)  # a, c vs b, d
    a, b, c = game.heroes['a'], game.heroes['b'], game.heroes['c']
    hp1, attack1 = game.stats(a)['health'], game.stats(a)['attack']
    b['hp'] = 5.
    game.damage(b, 1., c)  # c helps
    game.damage(b, 999., a)
    assert b['hp'] <= 0 and a['xp'] == 0 and a['level'] == 2  # 100 xp = exactly level 2
    assert c['xp'] == XP['assist'] and c['level'] == 1
    assert game.stats(a)['health'] == hp1 * 1.06 and game.stats(a)['attack'] == attack1 * 1.05
    assert a['max_hp'] == hp1 * 1.06 and a['hp'] == a['max_hp']
    assert game.public(a)['level'] == 2 and game.snapshot('a', 'x', 0)['profile']['xp_next'] == xp_next(2)


def test_unit_kill_feeds_the_killer_and_nearby_allies_and_level_caps_at_ten():
    game = RtsGame(['a', 'b', 'c', 'd'], team_size=2)
    a, c = game.heroes['a'], game.heroes['c']
    unit = game.actor('u', 'guard', 1, a['x'] + 50, a['y'], 1.)
    game.units['u'] = unit
    c.update(x=a['x'] + 100, y=a['y'], floor=a['floor'])
    game.damage(unit, 5., a)
    assert a['xp'] == XP['unit'] and c['xp'] == XP['nearby']
    game.gain_xp(a, 10**6)
    assert a['level'] == MAX_LEVEL and a['xp'] == 0
    assert game.snapshot('a', 'x', 0)['profile']['xp_next'] == 0


def test_dev_level_up_adds_one_level():
    game = RtsGame(['a', 'b'])
    game.heroes['a']['xp'] = 30
    game.dev_command('a', 'level_up')
    assert game.heroes['a']['level'] == 2 and game.heroes['a']['xp'] == 0


def test_dev_set_level_goes_up_and_down():
    game = RtsGame(['a', 'b'])
    h = game.heroes['a']
    game.dev_command('a', 'set_level', level=10)
    assert h['level'] == 10 and h['hp'] == h['max_hp'] == game.stats(h)['health']
    game.dev_command('a', 'set_level', level=1)
    assert h['level'] == 1 and h['max_hp'] == game.stats(h)['health']

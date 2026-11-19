import pytest
from app.rts_game import RtsGame
from app.zodiac_rules import ZODIAC

STATS = ('hp', 'attack', 'armor', 'magic_armor', 'speed', 'armor_pen', 'magic_pen', 'lifesteal')


def duel(character='rat', enemy='rat'):
    game = RtsGame(['a', 'b'], seed=7)
    a, b = game.heroes['a'], game.heroes['b']
    game.input('a', dict(sequence=1, character=character))
    game.input('b', dict(sequence=1, character=enemy))
    a.update(x=1000., y=1500., floor=1, fx=1., fy=0., protected=0)
    b.update(x=1150., y=1500., floor=1, protected=0)
    return game, a, b


def test_battle_snapshot_reports_all_stats():
    game, a, _ = duel('tiger')
    stats = game.battle_snapshot('a')['stats']
    assert set(STATS) <= set(stats)
    assert stats['attack'] == ZODIAC['tiger']['attack'] and a['max_hp'] == a['hp'] == ZODIAC['tiger']['hp']


def test_armor_and_penetration_reduce_physical_damage():
    game, a, b = duel('rat', 'ox')
    dealt = game.damage(b, 100, a)
    effective = ZODIAC['ox']['armor'] * (1 - ZODIAC['rat']['armor_pen'])
    assert dealt == pytest.approx(100 * 100 / (100 + effective))
    magic = game.damage(b, 100, a, 'magic')
    assert magic == pytest.approx(100 * 100 / (100 + ZODIAC['ox']['magic_armor']))


def test_lifesteal_heals_attacker():
    game, a, b = duel('tiger')
    a['hp'] = 50.
    dealt = game.damage(b, 40, a)
    assert a['hp'] == pytest.approx(50 + dealt * ZODIAC['tiger']['lifesteal'])


@pytest.mark.parametrize('character,seconds', [('rat', 5.), ('ox', 1.5)])
def test_q_grants_invulnerability(character, seconds):
    game, a, b = duel(character)
    game.use_skill(a, 'skill1', dict(aim_x=2000., aim_y=1500.))
    assert a['protected'] == seconds
    assert game.damage(a, 50, b) == 0


def test_doubled_skill_range_hits_far_target():
    game, a, b = duel('tiger')
    b['x'] = a['x'] + 450  # beyond the old 260 cone, inside the doubled 520
    game.use_skill(a, 'skill1', dict(aim_x=b['x'], aim_y=b['y']))
    assert b['hp'] < b['max_hp']


def test_short_basic_attack_has_short_reach_and_fan():
    game, a, b = duel('ox')
    b['x'] = a['x'] + 400
    game.input('a', dict(sequence=2, attack=True, aim_x=b['x'], aim_y=b['y']))
    game.tick(.05)
    assert b['hp'] == b['max_hp']
    b.update(x=a['x'] + 120, y=a['y'] + 90)
    a['attack_cooldown'] = 0
    game.input('a', dict(sequence=3, attack=True, aim_x=a['x'] + 200, aim_y=a['y']))
    game.tick(.05)
    assert b['hp'] < b['max_hp']


def test_rat_basic_attack_pierces_in_a_line():
    game, a, b = duel('rat')
    other = game.actor('m', 'guard', 1, a['x'] + 500, a['y'], 100, 1)
    game.units['m'] = game.minions['m'] = other
    other.update(owner_id='b', command='hold')
    game.input('a', dict(sequence=2, attack=True, aim_x=a['x'] + 600, aim_y=a['y']))
    game.tick(.05)
    assert b['hp'] < b['max_hp'] and other['hp'] < 100


def test_attack_and_skill_events_carry_no_map_text():
    game, a, _ = duel('dragon')
    game.input('a', dict(sequence=2, attack=True, aim_x=2000, aim_y=1500))
    game.tick(.05)
    game.use_skill(a, 'skill2', dict(aim_x=1500., aim_y=1500.))
    effects = game.snapshot('a', 'T', 0)['effects']
    assert effects and all(e['text'] == '' for e in effects)
    assert any(e['skill'] == 'a' and e['character'] == 'dragon' for e in effects)


def test_hero_and_minion_hp_are_scaled():
    from app.rts_game import RtsGame
    from app.zodiac_rules import HP_SCALE, ZODIAC
    assert ZODIAC['rat']['hp'] == 140 * HP_SCALE and ZODIAC['pig']['hp'] == 190 * HP_SCALE
    game = RtsGame(['a', 'b'])
    assert game.heroes['a']['max_hp'] == ZODIAC['rat']['hp']
    game.spawn_wave()
    hp = {u['kind']: u['max_hp'] for u in game.minions.values()}
    assert hp == {'guard': 180 * HP_SCALE, 'archer': 100 * HP_SCALE}

from app.rts_game import RtsGame
from app.rts_combat import XP, MAX_LEVEL, BOUNTY_XP, xp_next


def total_xp(h):
    return sum(xp_next(level) for level in range(1, h['level'])) + h['xp']


def kill(game, victim, killer):
    victim.update(hp=5., respawn_left=0.)
    game.damage(victim, 999., killer)
    assert victim['hp'] <= 0
    victim.update(hp=victim['max_hp'], respawn_left=0.)  # revive for the next fight


def duel():
    game = RtsGame(['a', 'b'])
    return game, game.heroes['a'], game.heroes['b']


def bounty_on_a(game, a, b, **gear):
    a.update(**gear)
    kill(game, b, a)
    kill(game, b, a)
    assert a['streak'] == 2


def test_two_kills_put_a_bounty_and_notify_both_teams():
    game, a, b = duel()
    kill(game, b, a)
    assert a['streak'] == 1 and '_notice' not in a
    kill(game, b, a)
    assert a['streak'] == 2
    assert a['_notice'].endswith('에게 현상금이 걸렸습니다')
    assert b['_notice'].startswith('적 ') and '처치하면 장비를 떨굽니다' in b['_notice']
    assert a['_notice_alert'] is False and game.public(a)['streak'] == 2


def test_killing_bounty_drops_better_gear_and_gives_bonus_xp():
    game, a, b = duel()
    bounty_on_a(game, a, b, weapon='weapon_rat', armor='fitted_armor_rat*2')
    before = total_xp(b)
    kill(game, a, b)
    assert a['streak'] == 0 and a['armor'] == 'fitted_armor_rat' and a['weapon'] == 'weapon_rat'
    assert [g['item'] for g in game.ground] == ['fitted_armor_rat'] and game.ground[0]['_by'] == 'a'
    assert total_xp(b) - before == XP['hero'] + 2 * BOUNTY_XP
    assert '차지' in b['_notice'] and '차지' in a['_notice']


def test_stacked_gear_drops_one_copy():
    game, a, b = duel()
    bounty_on_a(game, a, b, weapon='weapon_rat*9')
    kill(game, a, b)
    assert a['weapon'] == 'weapon_rat*8' and [g['item'] for g in game.ground] == ['weapon_rat']


def test_tie_drops_weapon():
    game, a, b = duel()
    bounty_on_a(game, a, b, weapon='weapon_rat', armor='fitted_armor_rat')
    kill(game, a, b)
    assert a['weapon'] == '' and a['armor'] == 'fitted_armor_rat'
    assert [g['item'] for g in game.ground] == ['weapon_rat']


def test_no_gear_gives_xp_only():
    game, a, b = duel()
    bounty_on_a(game, a, b)
    before = total_xp(b)
    kill(game, a, b)
    assert game.ground == [] and total_xp(b) - before == XP['hero'] + 2 * BOUNTY_XP


def test_minion_kill_resets_streak_without_drop():
    game, a, b = duel()
    bounty_on_a(game, a, b, weapon='weapon_rat')
    unit = game.actor('u', 'guard', b['team'], a['x'] + 50, a['y'], 1., a['floor'])
    game.units['u'] = unit
    kill(game, a, unit)
    assert a['streak'] == 0 and a['weapon'] == 'weapon_rat' and game.ground == []


def test_max_level_killer_still_makes_gear_drop():
    game, a, b = duel()
    bounty_on_a(game, a, b, weapon='weapon_rat')
    game.gain_xp(b, 10**6)
    assert b['level'] == MAX_LEVEL
    kill(game, a, b)
    assert len(game.ground) == 1 and b['xp'] == 0


def test_claiming_counts_toward_own_streak():
    game, a, b = duel()
    bounty_on_a(game, a, b)
    b['streak'] = 1  # b already had one kill this life
    kill(game, a, b)
    assert b['streak'] == 2 and b['_notice'].endswith('에게 현상금이 걸렸습니다')


def test_assist_does_not_count():
    game = RtsGame(['a', 'b', 'c', 'd'], team_size=2)  # a, c vs b, d
    a, b, c = game.heroes['a'], game.heroes['b'], game.heroes['c']
    b['hp'] = 5.
    game.damage(b, 1., c)
    game.damage(b, 999., a)
    assert a['streak'] == 1 and c['streak'] == 0

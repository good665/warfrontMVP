import math

import pytest

from app import rts_map as m
from app.rts_game import RtsGame
from app.squad_items import BAG_SIZE, CURSE_TIME, ITEMS, SLOTS, TOP, WEAPON_ATTACK, get_slot, grant
from app.zodiac_rules import ZODIAC

EMPTY = [''] * BAG_SIZE


def test_gear_equips_and_armor_raises_defense():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    base = ZODIAC['rat']['armor']
    assert grant(hero, 'axe') == '' and hero['weapon'] == 'axe'
    assert grant(hero, 'armor') == '' and hero['armor'] == 'armor'
    assert game.stats(hero)['armor'] == pytest.approx(base + ITEMS['armor']['armor'])
    hero['armor'] = 'fitted_armor_rat'
    assert game.stats(hero)['armor'] == pytest.approx(base + ITEMS['fitted_armor_rat']['armor'])
    hero['character'] = 'ox'  # someone else's fitted armor only counts as plain armor
    assert game.stats(hero)['armor'] == pytest.approx(ZODIAC['ox']['armor'] + ITEMS['armor']['armor'])


def test_zodiac_weapon_is_halved_on_another_character():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero.update(character='tiger', weapon='weapon_tiger')
    assert game.stats(hero)['attack'] == pytest.approx(ZODIAC['tiger']['attack'] + WEAPON_ATTACK)
    hero['weapon'] = 'weapon_rat'  # a tiger holding the rat's teeth
    assert game.stats(hero)['attack'] == pytest.approx(ZODIAC['tiger']['attack'] + WEAPON_ATTACK / 2)
    assert {ITEMS['weapon_' + z]['name'] for z in ZODIAC} >= {'쥐 이빨', '발톱', '당근', '돼지꼬리'}


def test_chest_fitted_armor_fits_the_opener_and_weapons_are_random_zodiac():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero['character'] = 'dog'
    game.rng.choice = lambda options: 'fitted_armor'
    assert game.chest_reward(hero) == 'fitted_armor_dog'
    picks = iter(['zodiac_weapon', 'monkey'])
    game.rng.choice = lambda options: next(picks)
    assert game.chest_reward(hero) == 'weapon_monkey'


def test_new_gear_goes_to_bag_and_full_inventory_drops_slot_ten():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    grant(hero, 'axe')
    assert grant(hero, 'weapon_ox') == '' and hero['weapon'] == 'axe' and hero['_bag'][0] == 'weapon_ox'
    grant(hero, 'armor')
    for _ in range(BAG_SIZE - 1): grant(hero, 'portal')
    assert all(get_slot(hero, i) for i in range(SLOTS))
    assert grant(hero, 'top') == 'portal' and hero['_bag'][-1] == 'top'
    # Through a chest the displaced item lands on the ground.
    game.rng.choice = lambda options: 'long_whip'
    chest = m.CHESTS[0]
    hero.update(floor=chest['floor'], x=chest['x'], y=chest['y'])
    game.tick(.05)
    assert hero['_bag'][-1] == 'long_whip' and [g['item'] for g in game.ground] == ['top']


def test_using_bag_gear_swaps_with_equipped():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    grant(hero, 'axe')
    grant(hero, 'weapon_rat')
    use(game, 'a', 2)
    assert hero['weapon'] == 'weapon_rat' and hero['_bag'][0] == 'axe'
    use(game, 'a', 0)  # equipped slots do nothing when pressed
    assert hero['weapon'] == 'weapon_rat'


def test_ctrl_drop_puts_item_on_ground_for_others():
    game = RtsGame(['a', 'b'])
    hero, other = game.heroes['a'], game.heroes['b']
    hero.update(x=3200., y=3200.)
    grant(hero, 'axe')
    game.input('a', dict(sequence=hero['sequence'] + 1, drop=0))
    game.tick(.05)
    assert hero['weapon'] == '' and game.ground_public(m.OUTDOOR)[0]['name'] == '도끼'
    game.tick(.05)
    assert hero['weapon'] == ''  # the dropper standing on it does not re-pick it
    seen = game.snapshot('b', 'R', 0)['ground_items']
    assert [g['item'] for g in seen] == ['axe']
    other.update(x=3200., y=3200., floor=m.OUTDOOR)
    game.tick(.05)
    assert other['weapon'] == 'axe' and game.ground == []


def test_dropper_can_pick_up_again_after_walking_away():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero.update(x=3200., y=3200.)
    grant(hero, 'top')
    game.input('a', dict(sequence=hero['sequence'] + 1, drop=2))
    game.tick(.05)
    hero['x'] += 200
    game.tick(.05)
    hero['x'] -= 200
    game.tick(.05)
    assert hero['_bag'][0] == 'top' and game.ground == []


def test_full_inventory_does_not_pick_from_ground():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    game.ground.append(dict(id='g', item='top', floor=hero['floor'], x=hero['x'], y=hero['y'], _by=''))
    for _ in range(BAG_SIZE): grant(hero, 'portal')
    game.tick(.05)
    assert len(game.ground) == 1 and hero['_bag'] == ['portal'] * BAG_SIZE


def open_chest(game, pid, reward):
    game.rng.choice = lambda options: reward
    chest = m.CHESTS[0]
    game.heroes[pid].update(floor=chest['floor'], x=chest['x'], y=chest['y'])
    game.tick(.05)


def test_chest_item_reaches_owner_snapshot_only():
    game = RtsGame(['a', 'b'])
    open_chest(game, 'a', 'top')
    assert game.battle_snapshot('a')['bag'] == ['top'] + EMPTY[1:]
    enemy_view = game.snapshot('b', 'ROOM', 0)['enemies']
    seen = next(a for a in enemy_view if a['id'] == 'a')
    assert 'weapon' in seen and '_bag' not in seen


def use(game, pid, slot, **extra):
    hero = game.heroes[pid]
    game.input(pid, dict(sequence=hero['sequence'] + 1, item=slot, **extra))
    game.tick(.05)


def test_consumable_is_used_once():
    game = RtsGame(['a', 'b'], seed=1)
    hero = game.heroes['a']
    grant(hero, 'portal')
    grant(hero, 'top')
    use(game, 'a', 2)
    # Slots keep their numbers: the top stays in slot 4.
    assert hero['_bag'][:2] == ['', 'top'] and hero['floor'] in m.INTERIORS and hero['protected'] > 2.9
    use(game, 'a', 2)  # empty slot does nothing
    assert hero['_bag'][:2] == ['', 'top']


def test_portal_never_lands_in_the_same_building():
    game = RtsGame(['a', 'b'], seed=2)
    hero = game.heroes['a']
    for _ in range(10):
        before = hero['floor']
        grant(hero, 'portal')
        use(game, 'a', 2)
        assert hero['floor'] in m.INTERIORS and hero['floor'] != before


def test_upgraded_portal_returns_to_home_walls():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    door = next(d for d in m.DOORS if d['floor'] == m.OUTDOOR)
    hero.update(floor=door['to_floor'], x=door['to_x'], y=door['to_y'])
    grant(hero, 'portal_plus')
    use(game, 'a', 2)
    home = game.home('a')
    assert hero['floor'] == m.OUTDOOR and math.hypot(hero['x'] - home['x'], hero['y'] - home['y']) < 300
    assert hero['protected'] > 2.9


def test_top_spins_on_target_for_ten_seconds():
    game = RtsGame(['a', 'b'])
    hero, enemy = game.heroes['a'], game.heroes['b']
    hero.update(x=3200., y=3200.)
    enemy.update(x=3400., y=3200.)
    grant(hero, 'top')
    use(game, 'a', 2, aim_x=3400., aim_y=3200.)
    assert game.snapshot('b', 'R', 0)['squad_items'][0]['kind'] == 'top'  # enemies see it too
    for _ in range(20): game.tick(.05)
    assert enemy['hp'] < enemy['max_hp']
    for _ in range(int(TOP['time'] / .05)): game.tick(.05)
    assert game.items == []


def test_bouncy_ball_bounces_ten_times_then_vanishes():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    door = next(d for d in m.DOORS if d['floor'] == m.OUTDOOR)
    hero.update(floor=door['to_floor'], x=door['to_x'], y=door['to_y'], fx=.6, fy=-.8)
    grant(hero, 'bouncy_ball')
    use(game, 'a', 2)
    ball = game.items[0]
    seen = 0
    for _ in range(400):
        seen = max(seen, ball['bounces'])
        game.tick(.05)
        if not game.items: break
        x0, y0, x1, y1 = m.bounds(ball['floor'])
        assert x0 <= ball['x'] <= x1 and y0 <= ball['y'] <= y1
    assert game.items == [] and seen >= 9


def test_long_whip_blows_away_stone_wall_block():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    index = next(i for i, r in enumerate(m.RECTS) if r[:5] == ('wall', 8, 26, 15, 33))
    hero.update(x=600., y=1240., fx=0., fy=1.)  # just above the block, facing it
    assert not game.can_hit(hero, dict(floor=1, x=600., y=1760.))
    grant(hero, 'long_whip')
    use(game, 'a', 2)
    assert index in game.broken_walls and game.snapshot('b', 'R', 0)['broken_walls'] == game.broken_walls
    assert game.can_hit(hero, dict(floor=1, x=600., y=1760.))
    assert not game.closed(hero, 600., 1500.)


@pytest.mark.parametrize('curse,blocked', [('curse_attack', 'attack'), ('curse_skill', 'skill1'), ('curse_ultimate', 'skill2')])
def test_curse_fires_on_pickup_and_blocks_enemy(curse, blocked):
    game = RtsGame(['a', 'b'])
    open_chest(game, 'a', curse)
    enemy = game.heroes['b']
    assert game.heroes['a']['_bag'] == EMPTY and enemy[curse + '_left'] == pytest.approx(CURSE_TIME, abs=.1)
    assert game.heroes['a'][curse + '_left'] == 0
    mine, theirs = game.battle_snapshot('a'), game.battle_snapshot('b')
    word = {'curse_attack': '일반공격', 'curse_skill': '스킬', 'curse_ultimate': '필살기'}[curse]
    assert mine['notice'] == f'상대편 {word}을 1분간 금지시킵니다' and not mine['notice_alert'] and mine['notice_id'] == 1
    assert word in theirs['notice'] and theirs['notice_alert'] and theirs['notice_id'] == 1
    game.input('b', dict(sequence=enemy['sequence'] + 1, **{blocked: True}))
    game.tick(.05)
    assert enemy['attack_cooldown' if blocked == 'attack' else blocked + '_cooldown'] == 0
    game.heroes['a'].update(floor=m.OUTDOOR, x=3200., y=3200.)  # off the chest so it is not reopened
    for _ in range(int(CURSE_TIME / .5) + 2): game.tick(.5)
    assert enemy[curse + '_left'] == 0


def test_identical_gear_stacks_to_silver_then_gold():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero['character'] = 'tiger'
    base_attack = ZODIAC['tiger']['attack']
    grant(hero, 'weapon_tiger')
    grant(hero, 'weapon_tiger')
    assert hero['weapon'] == 'weapon_tiger*2' and hero['_bag'] == EMPTY
    assert game.stats(hero)['attack'] == pytest.approx(base_attack + WEAPON_ATTACK * 2)
    grant(hero, 'weapon_tiger')
    assert hero['weapon'] == 'weapon_tiger*3'
    assert game.stats(hero)['attack'] == pytest.approx(base_attack + WEAPON_ATTACK * 3)
    grant(hero, 'weapon_tiger')  # gold is the cap; a fourth starts a new stack
    assert hero['weapon'] == 'weapon_tiger*3' and hero['_bag'][0] == 'weapon_tiger'
    hero['character'] = 'rat'  # someone else's gold weapon: still halved
    assert game.stats(hero)['attack'] == pytest.approx(ZODIAC['rat']['attack'] + WEAPON_ATTACK * 1.5)


def test_bag_gear_stacks_too_and_armor_scales():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    grant(hero, 'axe')
    grant(hero, 'weapon_dog')
    grant(hero, 'weapon_dog')
    assert hero['weapon'] == 'axe' and hero['_bag'][0] == 'weapon_dog*2'
    grant(hero, 'armor')
    grant(hero, 'armor')
    assert game.stats(hero)['armor'] == pytest.approx(ZODIAC['rat']['armor'] + ITEMS['armor']['armor'] * 2)


def test_dropped_stack_keeps_its_tier_and_merges_on_pickup():
    game = RtsGame(['a', 'b'])
    hero, other = game.heroes['a'], game.heroes['b']
    hero.update(x=3200., y=3200.)
    grant(hero, 'axe')
    grant(hero, 'axe')
    game.input('a', dict(sequence=hero['sequence'] + 1, drop=0))
    game.tick(.05)
    assert game.ground_public(m.OUTDOOR)[0]['name'] == '도끼 x2'
    grant(other, 'axe')
    other.update(x=3200., y=3200., floor=m.OUTDOOR)
    game.tick(.05)
    assert other['weapon'] == 'axe*3'


def test_axe_sits_between_own_and_foreign_zodiac_weapon_and_stacks():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    attack = lambda weapon: (hero.update(weapon=weapon), game.stats(hero)['attack'])[1]
    assert attack('weapon_ox') < attack('axe') < attack('weapon_rat')
    assert attack('axe*3') - attack('') == pytest.approx(3 * (attack('axe') - attack('')))

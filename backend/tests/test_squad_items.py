import math

import pytest

from app import rts_map as m
from app.rts_game import RtsGame
from app.squad_items import BAG_SIZE, CURSE_TIME, ITEMS, SLOTS, TOP, WEAPON_ATTACK, WEAPON_TIER_ATTACK, get_slot, grant, tier
from app.zodiac_rules import ZODIAC

EMPTY = [''] * BAG_SIZE


def test_gear_equips_and_armor_raises_defense():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    base = ZODIAC['rat']['armor']
    assert grant(hero, 'weapon_pig') == '' and hero['weapon'] == 'weapon_pig'
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


def test_chest_fitted_armor_and_weapons_are_random_zodiac():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero['character'] = 'dog'
    picks = iter(['fitted_armor', 'snake'])  # not cut for the opener: any of the 12
    game.rng.choice = lambda options: next(picks)
    assert game.chest_reward(hero) == 'fitted_armor_snake'
    picks = iter(['zodiac_weapon', 'monkey'])
    game.rng.choice = lambda options: next(picks)
    assert game.chest_reward(hero) == 'weapon_monkey'


def test_new_gear_goes_to_bag_and_full_inventory_drops_slot_ten():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    grant(hero, 'weapon_pig')
    assert grant(hero, 'weapon_ox') == '' and hero['weapon'] == 'weapon_pig' and hero['_bag'][0] == 'weapon_ox'
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
    grant(hero, 'weapon_pig')
    grant(hero, 'weapon_rat')
    use(game, 'a', 2)
    assert hero['weapon'] == 'weapon_rat' and hero['_bag'][0] == 'weapon_pig'
    use(game, 'a', 0)  # equipped slots do nothing when pressed
    assert hero['weapon'] == 'weapon_rat'


def test_ctrl_drop_puts_item_on_ground_for_others():
    game = RtsGame(['a', 'b'])
    hero, other = game.heroes['a'], game.heroes['b']
    hero.update(x=3200., y=3200.)
    grant(hero, 'weapon_pig')
    game.input('a', dict(sequence=hero['sequence'] + 1, drop=0))
    game.tick(.05)
    assert hero['weapon'] == '' and game.ground_public(m.OUTDOOR)[0]['name'] == '돼지꼬리'
    game.tick(.05)
    assert hero['weapon'] == ''  # the dropper standing on it does not re-pick it
    seen = game.snapshot('b', 'R', 0)['ground_items']
    assert [g['item'] for g in seen] == ['weapon_pig']
    other.update(x=3200., y=3200., floor=m.OUTDOOR)
    game.tick(.05)
    assert other['weapon'] == 'weapon_pig' and game.ground == []


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


def test_bouncy_ball_bounces_thirty_times_then_vanishes():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    door = next(d for d in m.DOORS if d['floor'] == m.OUTDOOR)
    hero.update(floor=door['to_floor'], x=door['to_x'], y=door['to_y'], fx=.6, fy=-.8)
    grant(hero, 'bouncy_ball')
    use(game, 'a', 2)
    ball = game.items[0]
    seen = 0
    for _ in range(4000):
        seen = max(seen, ball['bounces'])
        game.tick(.05)
        if not game.items: break
        x0, y0, x1, y1 = m.bounds(ball['floor'])
        assert x0 <= ball['x'] <= x1 and y0 <= ball['y'] <= y1
    assert game.items == [] and ball['bounces'] == 30 and seen >= 29


def test_bouncy_ball_outdoors_is_not_consumed():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    assert hero['floor'] == m.OUTDOOR
    grant(hero, 'bouncy_ball')
    use(game, 'a', 2)
    assert get_slot(hero, 2) == 'bouncy_ball'
    assert game.items == []
    assert '실내' in hero.get('_notice', '')


@pytest.mark.parametrize('dx,dy', [(1, 0), (-1, 0), (0, 1), (0, -1),
                                  (1, 1), (-1, 1), (1, -1), (-1, -1), (.3, .8)])
def test_bouncy_ball_uses_aim_in_every_direction_even_while_facing_elsewhere(dx, dy):
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    door = next(d for d in m.DOORS if d['floor'] == m.OUTDOOR)
    hero.update(floor=door['to_floor'], x=door['to_x'], y=door['to_y'], fx=-1., fy=0.)
    grant(hero, 'bouncy_ball')
    game.use_item(hero, dict(item=2, aim_x=hero['x']+dx*100, aim_y=hero['y']+dy*100))
    ball = game.items[0]
    norm = math.hypot(dx, dy)
    assert ball['vx'] == pytest.approx(dx/norm*700)
    assert ball['vy'] == pytest.approx(dy/norm*700)


def test_bouncy_ball_lifetime_allows_thirty_bounces_in_largest_room():
    from app.squad_items import BALL
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    floor = max(m.INTERIORS, key=lambda f: math.hypot(m.bounds(f)[2]-m.bounds(f)[0], m.bounds(f)[3]-m.bounds(f)[1]))
    x0, y0, x1, y1 = m.bounds(floor)
    hero.update(floor=floor, x=(x0+x1)/2, y=(y0+y1)/2)
    grant(hero, 'bouncy_ball')
    game.use_item(hero, dict(item=2))
    assert game.items[0]['left'] > 30*math.hypot(x1-x0, y1-y0)/BALL['speed']


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


def test_broken_stone_wall_leaves_a_coin_that_becomes_the_pickers_own_weapon():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero.update(x=600., y=1240., fx=0., fy=1., character='tiger')
    grant(hero, 'long_whip')
    use(game, 'a', 2)
    coin = next(g for g in game.ground if g['item'] == 'coin')
    assert (coin['x'], coin['y']) == (600., 1500.)  # centre of the 8..15 x 26..33 block
    assert game.ground_public(1)[0]['name'] == '동전'
    hero.update(x=coin['x'], y=coin['y'])
    game.pickup(hero)
    assert hero['weapon'] == 'weapon_tiger' and coin not in game.ground


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
    bronze, silver, gold = WEAPON_TIER_ATTACK
    grant(hero, 'weapon_tiger')
    grant(hero, 'weapon_tiger')
    assert hero['weapon'] == 'weapon_tiger*2' and hero['_bag'] == EMPTY and tier(hero['weapon']) == 1
    assert game.stats(hero)['attack'] == pytest.approx(base_attack + bronze)
    grant(hero, 'weapon_tiger')  # 3 bronze -> silver
    assert hero['weapon'] == 'weapon_tiger*3' and tier(hero['weapon']) == 2
    assert game.stats(hero)['attack'] == pytest.approx(base_attack + silver)
    for _ in range(6): grant(hero, 'weapon_tiger')  # 3 silvers (9 weapons) -> gold
    assert hero['weapon'] == 'weapon_tiger*9' and tier(hero['weapon']) == 3
    assert game.stats(hero)['attack'] == pytest.approx(base_attack + gold)
    assert bronze < silver < gold and gold - silver > silver - bronze  # each grade is a bigger jump
    grant(hero, 'weapon_tiger')  # gold is the cap; a tenth starts a new stack
    assert hero['weapon'] == 'weapon_tiger*9' and hero['_bag'][0] == 'weapon_tiger'
    hero['character'] = 'rat'  # someone else's gold weapon: still halved
    assert game.stats(hero)['attack'] == pytest.approx(ZODIAC['rat']['attack'] + gold * .5)


def test_armor_keeps_two_for_silver_three_for_gold():
    assert (tier('armor*2'), tier('armor*3')) == (2, 3)
    hero = RtsGame(['a', 'b']).heroes['a']
    for _ in range(4): grant(hero, 'armor')
    assert hero['armor'] == 'armor*3' and hero['_bag'][0] == 'armor'


def test_bag_gear_stacks_too_and_armor_scales():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    grant(hero, 'weapon_pig')
    grant(hero, 'weapon_dog')
    grant(hero, 'weapon_dog')
    assert hero['weapon'] == 'weapon_pig' and hero['_bag'][0] == 'weapon_dog*2'
    grant(hero, 'armor')
    grant(hero, 'armor')
    assert game.stats(hero)['armor'] == pytest.approx(ZODIAC['rat']['armor'] + ITEMS['armor']['armor'] * 2)


def test_dropped_stack_keeps_its_tier_and_merges_on_pickup():
    game = RtsGame(['a', 'b'])
    hero, other = game.heroes['a'], game.heroes['b']
    hero.update(x=3200., y=3200.)
    grant(hero, 'weapon_pig')
    grant(hero, 'weapon_pig')
    game.input('a', dict(sequence=hero['sequence'] + 1, drop=0))
    game.tick(.05)
    assert game.ground_public(m.OUTDOOR)[0]['name'] == '돼지꼬리 x2'
    grant(other, 'weapon_pig')
    other.update(x=3200., y=3200., floor=m.OUTDOOR)
    game.tick(.05)
    assert other['weapon'] == 'weapon_pig*3'


def land(game, pid):
    for _ in range(30): game.tick(.05)
    return game.heroes[pid]


def super_jump(game, pid, **extra):
    hero = game.heroes[pid]
    game.input(pid, dict(sequence=hero['sequence'] + 1, super_jump=True, **extra))
    game.tick(.05)


@pytest.mark.parametrize('start,obstacle', [
    ((600., 1240.), (600., 1500.)),     # over the stone wall block (8..15, 26..33)
    ((600., 2650.), (600., 2800.)),     # over the river (rows 54..57)
    ((1500., 380.), (1500., 550.)),     # over the house (26..33, 8..15)
])
def test_super_jump_leaps_the_way_the_hero_runs(start, obstacle):
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero.update(x=start[0], y=start[1], super_jump=True)
    assert game.closed(hero, *obstacle)
    # running down (+y) while the mouse points the other way: the keys decide
    super_jump(game, 'a', move_x=0, move_y=1, aim_x=start[0], aim_y=0.)
    assert hero['super_jump_left'] > 0
    assert 'super_jump_left' in game.public(hero) and '_leap' not in game.public(hero)
    hero = land(game, 'a')
    assert hero['_leap'] is None and hero['super_jump_left'] == 0
    assert (hero['y'] - obstacle[1]) * (obstacle[1] - start[1]) > 0  # landed past the obstacle
    assert not game.closed(hero, hero['x'], hero['y']) and not m.is_door(1, *m.cell(hero['x'], hero['y']))


def test_super_jump_ignores_movement_mid_air_and_lands_short_of_the_board_edge():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero.update(x=100., y=600., fx=-1., fy=0., super_jump=True)  # standing still: jumps the way it faces
    super_jump(game, 'a')
    game.input('a', dict(sequence=hero['sequence'] + 1, move_x=0, move_y=1))
    game.tick(.05)
    assert hero['y'] == pytest.approx(600.)  # keys do nothing in flight
    hero = land(game, 'a')
    assert hero['x'] == pytest.approx(35.) and hero['y'] == pytest.approx(600.)


def test_super_jump_is_locked_until_a_chest_then_reusable_right_after_landing():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    super_jump(game, 'a')
    assert hero['super_jump_left'] == 0  # not unlocked yet
    open_chest(game, 'a', 'super_jump')
    assert hero['super_jump'] and hero['_bag'] == EMPTY and '슈퍼점프' in game.battle_snapshot('a')['notice']
    assert game.public(hero)['super_jump']
    hero.update(x=1500., y=1500.)
    super_jump(game, 'a', move_x=1)
    hero = land(game, 'a')
    super_jump(game, 'a', move_x=1)  # no cooldown: leaps again as soon as it lands
    assert hero['super_jump_left'] > 0 and hero['super_jump']


def test_owned_super_jump_is_not_rolled_again_and_never_lies_on_the_ground():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    hero['super_jump'] = True
    picks = iter(['super_jump', 'heal'])
    game.rng.choice = lambda options: next(picks)
    assert game.chest_reward(hero) == 'heal'
    assert 'super_jump' not in ITEMS


def test_top_aimed_past_an_interior_wall_lands_inside_the_room():
    from app import rts_map as m
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    floor = next(f for f, room in m.INTERIORS.items() if room[3] == 'passage')
    door = next(d for d in m.DOORS if d['to_floor'] == floor)
    hero.update(floor=floor, x=door['to_x'], y=door['to_y'])
    grant(hero, 'top')
    slot = hero['_bag'].index('top') + 2  # slots 0-1 are weapon and armor
    game.input('a', dict(sequence=hero['sequence'] + 1, item=slot, aim_x=hero['x'], aim_y=hero['y'] - 2000))  # far past the north wall
    game.tick(.05)
    top = next(i for i in game.items if i['kind'] == 'top')
    assert top['floor'] == floor and not m.blocked(floor, *m.cell(top['cx'], top['cy']))


def test_bouncy_ball_rebounds_in_all_eight_directions_not_one_line():
    game = RtsGame(['a', 'b'], seed=5)
    hero = game.heroes['a']
    door = next(d for d in m.DOORS if d['floor'] == m.OUTDOOR)
    hero.update(floor=door['to_floor'], x=door['to_x'], y=door['to_y'])
    grant(hero, 'bouncy_ball')
    game.use_item(hero, dict(item=2, aim_x=hero['x'] + 100, aim_y=hero['y']))  # thrown straight sideways
    ball = game.items[0]
    headings, last = set(), 0
    for _ in range(4000):
        game.tick(.05)
        if not game.items: break
        if ball['bounces'] != last:
            last = ball['bounces']
            assert math.hypot(ball['vx'], ball['vy']) == pytest.approx(700)
            angle = math.degrees(math.atan2(ball['vy'], ball['vx'])) % 360
            assert min(angle % 45, 45 - angle % 45) < 1e-6  # one of the 8 screen directions
            headings.add(round(angle) % 360)
    assert ball['bounces'] == 30
    assert len(headings) >= 5 and headings & {45, 135, 225, 315} and headings & {90, 270}

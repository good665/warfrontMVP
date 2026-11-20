import pytest
from app.rts_game import RtsGame
from app.zodiac_rules import ZODIAC


def advance(game, seconds):
    for _ in range(round(seconds / .05)):
        game.tick(.05)


@pytest.mark.parametrize('animal', list(ZODIAC))
def test_each_animal_can_use_q_and_e_with_server_cooldowns(animal):
    game = RtsGame(['a', 'b'], seed=7)
    h = game.heroes['a']
    game.input('a', dict(sequence=1, character=animal))
    assert h['character'] == animal
    game.input('a', dict(sequence=2, skill1=True, aim_x=2000, aim_y=1200))
    game.tick(.05)
    assert h['skill1_cooldown'] > 0
    game.input('a', dict(sequence=3, skill2=True, aim_x=2000, aim_y=1200))
    advance(game, .6)
    assert h['skill2_cooldown'] > 0


def test_running_hero_faces_the_key_direction_and_turns_to_the_mouse_to_attack():
    game = RtsGame(['a', 'b'], seed=7)
    h = game.heroes['a']
    mouse = dict(aim_x=h['x'] - 500, aim_y=h['y'])   # mouse to the left
    game.input('a', dict(sequence=1, move_x=1, **mouse))   # D key: run right
    game.tick(.05)
    assert h['fx'] > .99
    game.input('a', dict(sequence=2, **mouse))   # standing still: face the mouse
    game.tick(.05)
    assert h['fx'] < -.99
    game.input('a', dict(sequence=3, move_x=1, attack=True, **mouse))   # attacking while running
    game.tick(.05)
    assert h['fx'] < -.99


def test_jump_is_visual_and_cannot_prevent_damage():
    game = RtsGame(['a', 'b'], seed=7)
    a, b = game.heroes.values()
    b.update(floor=a['floor'], protected=0)
    a['protected'] = 0
    position = a['x'], a['y'], a['floor']
    game.input('a', dict(sequence=1, jump=True))
    game.tick(.05)
    assert a['jump_left'] > 0
    assert position == (a['x'], a['y'], a['floor'])
    game.damage(a, 10, b)
    assert a['hp'] < a['max_hp']


def test_poison_tick_damage_is_independent_of_simulation_tick_size():
    game = RtsGame(['a', 'b'], seed=7)
    a, b = game.heroes.values()
    a.update(floor=1, x=100, y=100)
    b.update(floor=1, x=1500, y=100, protected=0, poison_left=1., poison_damage=8., poison_owner=a['id'])
    advance(game, 1.)
    assert b['hp'] == pytest.approx(b['max_hp'] - 8.)


def test_tiger_roar_roots_the_hero_until_the_animation_ends():
    game = RtsGame(['a', 'b'], seed=7)
    h = game.heroes['a']
    game.input('a', dict(sequence=1, character='tiger'))
    game.input('a', dict(sequence=2, skill2=True, aim_x=h['x'] + 300, aim_y=h['y']))
    game.tick(.05)
    start = (h['x'], h['y'])
    for i in range(50):  # 2.5s of holding D and clicking attack
        game.input('a', dict(sequence=3 + i, move_x=1, attack=True))
        game.tick(.05)
        assert h['attack_cooldown'] == 0
    assert (h['x'], h['y']) == start
    for i in range(10):
        game.input('a', dict(sequence=60 + i, move_x=1))
        game.tick(.05)
    assert h['x'] > start[0]


def test_other_ultimates_do_not_root():
    game = RtsGame(['a', 'b'], seed=7)
    h = game.heroes['a']
    game.input('a', dict(sequence=1, character='rat'))
    game.input('a', dict(sequence=2, skill2=True, aim_x=h['x'] + 300, aim_y=h['y']))
    game.tick(.05)
    assert h['cast_left'] == 0


def test_tiger_slash_roots_and_holds_fire_for_its_animation():
    game = RtsGame(['a', 'b'], seed=7)
    h = game.heroes['a']
    game.input('a', dict(sequence=1, character='tiger'))
    game.input('a', dict(sequence=2, skill1=True, aim_x=h['x'] + 300, aim_y=h['y']))
    game.tick(.05)
    start = (h['x'], h['y'])
    for i in range(22):  # 1.1s of holding D and clicking attack
        game.input('a', dict(sequence=3 + i, move_x=1, attack=True))
        game.tick(.05)
        assert h['attack_cooldown'] == 0
    assert (h['x'], h['y']) == start
    for i in range(6):
        game.input('a', dict(sequence=30 + i, move_x=1))
        game.tick(.05)
    assert h['x'] > start[0]

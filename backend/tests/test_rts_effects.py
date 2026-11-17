import pytest
from app.rts_game import RtsGame
from app.zodiac_rules import ZODIAC


@pytest.mark.parametrize('character', ZODIAC)
@pytest.mark.parametrize('action,slot', [('skill1', 'q'), ('skill2', 'e')])
def test_skill_visual_identity_direction_and_age(character, action, slot):
    game = RtsGame(['a', 'b'], seed=7)
    hero = game.heroes['a']
    hero.update(character=character, x=1200., y=1800., floor=1, fx=0., fy=1.)
    game.use_skill(hero, action, dict(aim_x=1700., aim_y=1800.))
    effect = game.snapshot('a', 'TEST', 0)['effects'][-1]
    assert (effect['character'], effect['skill']) == (character, slot)
    assert effect['fx'] == pytest.approx(1.)
    assert effect['fy'] == pytest.approx(0.)
    assert effect['age'] == pytest.approx(0.)
    game.elapsed += .2
    aged = game.snapshot('a', 'TEST', 0)['effects'][-1]
    assert aged['age'] == pytest.approx(.2)
    if character == 'dragon' and slot == 'e':
        assert effect['x'] == pytest.approx(1700.)
    assert effect['radius'] > 0



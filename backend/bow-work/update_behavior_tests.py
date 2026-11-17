from pathlib import Path
p=Path('tests/test_squad_actions.py');s=p.read_text(encoding='utf-8-sig')
s=s.replace("@pytest.mark.parametrize('offset,expected', [(175., 140.), (175.01, 160.), (-100., 160.)])\ndef test_melee_body_contact_boundary_outside_and_behind(offset, expected):", "@pytest.mark.parametrize('offset,expected', [(37.9, 140.), (38.1, 160.), (100., 160.)])\ndef test_bow_body_contact_lateral_boundary(offset, expected):")
s=s.replace("enemy['x'] = hero['x']+offset\n    control(game, attack=True)", "enemy['y'] = hero['y']+offset\n    control(game, attack=True)",1)
s=s.replace('def test_melee_windup_single_hit_frozen_facing_and_public_action():', 'def test_bow_windup_single_hit_frozen_facing_and_public_action():')
s=s.replace("actor['action_kind'] == 'attack'", "actor['action_kind'] == 'hero_bow'")
s=s.replace("actor['action_duration'] == .55", "actor['action_duration'] == .40")
start=s.index('def test_heavy_damage_and_action_id_increase():');end=s.index('\n\ndef test_dodge_',start)
s=s[:start]+'''def test_charge_release_damage_and_action_id_increase():
    game, hero, enemy = arena()
    enemy['x'] = 1232.
    control(game, skill1=True, charge_held=True)
    game.tick(.05)
    for _ in range(24):
        control(game, charge_held=True)
        game.tick(.05)
    assert enemy['hp'] == 160.
    control(game, charge_release=True)
    game.tick(.05)
    assert hero['action_id'] == 2
    advance(game, .35)
    assert enemy['hp'] == 116.
    control(game, attack=True)
    game.tick(.01)
    assert hero['action_id'] == 3
''' +s[end:]
s=s.replace("advance(game, .20)\n    assert hero['hp'] == enemy['hp'] == 0.", "advance(game, .35)\n    assert hero['hp'] == enemy['hp'] == 0.")
p.write_text(s,encoding='utf-8')
p=Path('tests/test_squad_input_buffer.py');s=p.read_text(encoding='utf-8-sig').replace("('skill1', 'heavy')", "('skill1', 'charge_bow')").replace("hero['action_kind'] == 'attack'", "hero['action_kind'] == 'hero_bow'")
s=s.replace('send(game, attack=True, **{button: True})', "send(game, attack=True, charge_held=button=='skill1', **{button: True})")
s=s.replace('test_dodge_can_cancel_heavy_', 'test_dodge_can_cancel_charge_')
s=s.replace('send(game, skill1=True)', 'send(game, skill1=True, charge_held=True)')
p.write_text(s,encoding='utf-8')

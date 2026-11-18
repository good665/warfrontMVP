import math
import pytest
from app.rts_game import RtsGame
from app.squad_routes import SquadInput


@pytest.mark.parametrize('before_wave', [True, False])
def test_gather_moves_existing_and_future_minions_only_for_owner(before_wave):
    game = RtsGame(['a', 'b', 'c', 'd'], team_size=2)
    if not before_wave:
        game.tick(30)
    # Like Unity's G key, gather works without selecting any units.
    game.input('a', SquadInput(sequence=1, command='gather', order_x=1800, order_y=600).model_dump())
    if before_wave:
        game.tick(30)
    units = [u for u in game.minions.values() if u['owner_id'] == 'a']
    assert len(units) == 5
    assert all(u['command'] == 'attack_move' and (u['order_x'], u['order_y']) == (1800, 600) for u in units)
    assert all(u['command'] == 'wave' for u in game.minions.values() if u['owner_id'] != 'a')
    distances = {u['id']: math.hypot(1800-u['x'], 600-u['y']) for u in units}
    for _ in range(20):
        game.tick(.05)
    world = game.snapshot('a', 'ROOM', 0)
    for actor in world['players']:
        if actor['id'] in distances:
            # Nearby bodies can slow a unit, but every minion must make progress.
            assert math.hypot(1800-actor['x'], 600-actor['y']) < distances[actor['id']]


def test_latest_gather_controls_later_waves_and_replays_cannot_replace_it():
    game = RtsGame(['a', 'b'])
    game.input('a', dict(sequence=1, command='gather', order_x=1800, order_y=600))
    game.input('a', dict(sequence=2, command='gather', order_x=1800, order_y=1600))
    game.input('a', dict(sequence=1, command='gather', order_x=3000, order_y=3000))
    game.tick(30)
    for unit in game.minions.values():
        if unit['owner_id'] == 'a':
            assert (unit['order_x'], unit['order_y']) == (1800, 1600)
    first_ids = set(game.minions)
    for _ in range(600):
        game.tick(.05)
    later = [u for uid, u in game.minions.items() if uid not in first_ids and u['owner_id'] == 'a']
    assert len(later) == 5
    assert all(u['command'] == 'attack_move' and (u['order_x'], u['order_y']) == (1800, 1600) for u in later)


@pytest.mark.parametrize('before_wave', [True, False])
@pytest.mark.parametrize('kind', ['guard', 'archer'])
@pytest.mark.parametrize('arrived', [True, False])
def test_rally_minions_attack_enemies_and_keep_rally_goal(before_wave, kind, arrived):
    game = RtsGame(['a', 'b'])
    if not before_wave:
        game.tick(30)
    game.input('a', SquadInput(sequence=1, command='gather', order_x=2000, order_y=1450).model_dump())
    if before_wave:
        game.tick(30)
    unit = next(u for u in game.minions.values() if u['owner_id'] == 'a' and u['kind'] == kind)
    unit.update(x=2000 if arrived else 1450, y=1450)
    enemy = game.heroes['b']
    enemy.update(x=unit['x']+50, y=1450, protected=0)
    game.command_tick(unit, .05)
    assert enemy['hp'] < enemy['max_hp']
    assert (unit['order_x'], unit['order_y']) == (2000, 1450)
    enemy['hp'] = 0
    before = math.hypot(2000-unit['x'], 1450-unit['y'])
    game.command_tick(unit, .05)
    after = math.hypot(2000-unit['x'], 1450-unit['y'])
    if arrived:
        assert after == 0
    else:
        assert after < before

import pytest
from app.rts_game import RtsGame


def waves(game):
    return [a for a in game.minions.values() if a.get('wave')]


@pytest.mark.parametrize('ids,size', [(['a', 'b'], 1), (['a', 'b', 'c', 'd'], 2)])
def test_cadence_and_ownership(ids, size):
    game = RtsGame(ids, team_size=size)
    game.tick(29.9)
    assert not waves(game)
    game.tick(.1)
    for pid in ids:
        units = [a for a in waves(game) if a['owner_id'] == pid]
        assert sorted(a['kind'] for a in units) == ['archer', 'archer', 'guard', 'guard', 'guard']
        assert all(a['team'] == game.heroes[pid]['team'] for a in units)
    assert game.battle_snapshot('a')['next_wave'] == pytest.approx(30)
    game.tick(60)
    assert game.next_wave == 120
    assert len(waves(game)) == len(ids) * 15


def test_waypoints_are_visited_in_order_before_enemy_base():
    game = RtsGame(['a', 'b'])
    game.tick(30)
    unit = next(a for a in waves(game) if a['owner_id'] == 'a')
    # Isolate movement from combat without substituting the movement implementation.
    for enemy in list(game.units.values()):
        if enemy is not unit:
            game.units.pop(enemy['id'])
            game.minions.pop(enemy['id'], None)
    visited = []
    for _ in range(1100):
        game.wave_tick(unit, .05)
        for point in [(800., 800.), (3200., 3200.), (5600., 5600.)]:
            if (unit['x']-point[0])**2 + (unit['y']-point[1])**2 <= 82**2 and point not in visited:
                visited.append(point)
    assert visited == [(800., 800.), (3200., 3200.), (5600., 5600.)]
    assert unit['x'] > 5600 and unit['y'] > 5600


def test_combat_then_route_resume_and_manual_override():
    game = RtsGame(['a', 'b'])
    game.tick(30)
    unit = next(a for a in waves(game) if a['owner_id'] == 'a')
    enemy = game.heroes['b']
    enemy.update(x=unit['x'] + 50, y=unit['y'], protected=0)
    before = unit['x'], unit['y']
    game.wave_tick(unit, .05)
    assert enemy['hp'] < enemy['max_hp']
    assert (unit['x'], unit['y']) == before
    enemy.update(x=6000, y=6000)
    game.wave_tick(unit, .05)
    assert (unit['x'], unit['y']) != before
    game.input('a', dict(sequence=1, command='hold', unit_ids=[unit['id']]))
    before = unit['x'], unit['y']
    game.command_tick(unit, .05)
    assert (unit['x'], unit['y']) == before


def test_destroyed_source_and_target_and_finished_match():
    game = RtsGame(['a', 'b', 'c', 'd'], team_size=2)
    game.bases[0]['hp'] = 0
    game.tick(30)
    assert not any(a['owner_id'] == 'a' for a in waves(game))
    unit = next(a for a in waves(game) if a['owner_id'] == 'c')
    destination = next(b for b in game.bases if b['id'] == unit['_wave_destination'])
    destination['hp'] = 0
    game.wave_tick(unit, .05)
    assert unit['_wave_destination'] != destination['id']
    count = len(waves(game))
    game.reason = 'forfeit'
    game.tick(90)
    assert len(waves(game)) == count


def test_bot_does_not_override_automatic_routes():
    game = RtsGame(['a', 'b'])
    game.tick(30)
    game.bot_input('b')
    assert all(a['command'] == 'wave' for a in waves(game))


def test_wave_does_not_walk_back_to_a_waypoint_it_chased_past():
    game = RtsGame(['a', 'b'])
    game.tick(30)
    archer = next(a for a in waves(game) if a['owner_id'] == 'a' and a['kind'] == 'archer')
    for other in list(game.units.values()):
        if other is not archer and other['kind'] != 'hero':
            game.units.pop(other['id']); game.minions.pop(other['id'], None)
    centre = archer['_waypoints'][1]
    archer.update(_waypoint=1, x=centre['x'] + 300, y=centre['y'])  # fought its way past the nave entrance
    enemy = game.heroes['b']
    enemy.update(x=archer['x'] + 200, y=archer['y'], protected=0)
    game.wave_tick(archer, .05)
    enemy.update(x=100, y=6300)  # fight over
    before = (archer['x'] - centre['x'])**2 + (archer['y'] - centre['y'])**2
    for _ in range(10): game.wave_tick(archer, .05)
    assert archer['_waypoint'] == 2
    assert (archer['x'] - centre['x'])**2 + (archer['y'] - centre['y'])**2 > before  # kept going forward


@pytest.mark.parametrize('ids,size', [(['a', 'b'], 1), (['a', 'b', 'c', 'd'], 2)])
def test_waves_walk_through_the_cathedral_nave(ids, size):
    from app.rts_map import NAVE, RECTS, SOLID_CELLS, cell
    x0, y0, x1, y1 = NAVE
    _, _, top, _, bottom, _ = next(r for r in RECTS if r[0] == 'cathedral')
    game = RtsGame(ids, team_size=size)
    game.tick(30)
    for pid in ids:
        unit = next(a for a in waves(game) if a['owner_id'] == pid)
        for other in list(game.units.values()):
            if other is not unit:
                game.units.pop(other['id']); game.minions.pop(other['id'], None)
        west_start = unit['x'] < 3200
        ends = []
        for _ in range(1400):
            game.wave_tick(unit, .05)
            c = cell(unit['x'], unit['y'])
            assert c not in SOLID_CELLS
            if x0 <= c[0] <= x1 and top <= c[1] <= bottom:  # inside the cathedral footprint: only the nave is walkable
                assert y0 <= c[1] <= y1
                end = 'west' if c[0] == x0 else 'east' if c[0] == x1 else None
                if end and end not in ends: ends.append(end)
        assert ends == (['west', 'east'] if west_start else ['east', 'west'])
        game = RtsGame(ids, team_size=size); game.tick(30)

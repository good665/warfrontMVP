import pytest
from app.rts_game import RtsGame


@pytest.mark.parametrize('ids,size', [(['a', 'b'], 1), (['a', 'b', 'c', 'd'], 2)])
def test_match_starts_with_only_heroes_and_bases(ids, size):
    game = RtsGame(ids, team_size=size)
    assert [h['team'] for h in game.heroes.values()] == [i % 2 for i in range(len(ids))]
    assert len(game.bases) == len(ids)
    assert set(game.units) == set(ids)
    assert not game.minions
    world = game.snapshot('a', 'ROOM', 0)
    assert all(a['kind'] == 'hero' for a in world['players'])
    assert all(a['kind'] in ('hero', 'base', 'bell') for a in world['enemies'])


def test_automatic_waves_start_after_thirty_seconds():
    game = RtsGame(['a', 'b'])
    initial = set(game.units)
    for _ in range(599):
        game.tick(.05)
    assert set(game.units) == initial
    game.tick(.05)
    assert len(set(game.units) - initial) == 10


def test_commands_only_control_owned_units():
    game = RtsGame(['a', 'b', 'c', 'd'], team_size=2)
    game.tick(30)
    own = next(u for u in game.minions.values() if u['owner_id'] == 'a')
    allied = next(u for u in game.minions.values() if u['owner_id'] == 'c')
    game.input('a', dict(sequence=1, command='move', unit_ids=[own['id'], allied['id']], order_x=3000, order_y=3000))
    assert own['order_x'] == 3000
    assert allied.get('order_x') != 3000


def test_team_loses_only_when_all_its_bells_break():
    game = RtsGame(['a', 'b', 'c', 'd'], team_size=2)
    for base in game.bases: base['hp'] = 0  # fallen gates only open the keeps
    game.tick(.05)
    assert not game.reason
    bells = [b for b in game.bells if b['team'] == 0]
    bells[0]['hp'] = 0
    game.tick(.05)
    assert not game.reason
    bells[1]['hp'] = 0
    game.tick(.05)
    assert game.winner == 1 and game.reason == 'bell_destroyed'


def test_map_bounds_and_dead_owner_base_prevent_respawn():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    game.move(hero, 9000, 9000, 10000, 1)
    assert 35 <= hero['x'] <= 6365 and 35 <= hero['y'] <= 6365
    game.bases[0]['hp'] = 0
    hero.update(hp=0, respawn_left=0)
    game.tick(.05)
    assert hero['hp'] == 0


def test_rts_hero_move_locks_character_choice():
    game=RtsGame(['a','b'])
    game.input('a',dict(sequence=1,command='move',unit_ids=['a'],order_x=1200,order_y=1200))
    game.tick(.05)
    game.input('a',dict(sequence=2,character='dragon'))
    assert game.heroes['a']['character']=='rat'

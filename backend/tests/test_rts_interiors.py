from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import rts_map as m, squad_routes
from app.rts_game import RtsGame
from app.squad_routes import SquadInput
from app.zodiac_rules import ZODIAC
import pytest

m_attack = ZODIAC['rat']['attack']

C = m.CELL


def c(cx, cy):
    return (cx + .5) * C, (cy + .5) * C


HOUSE_DOOR = next(d for d in m.DOORS if d['floor'] == m.OUTDOOR and (d['cx'], d['cy']) == (29, 15))


def step_on(hero, floor, cx, cy):
    hero['floor'] = floor
    hero['x'], hero['y'] = c(cx, cy)


def test_hero_enters_and_exits_door():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    step_on(hero, m.OUTDOOR, 29, 15)
    game.tick(.05)
    assert hero['floor'] == HOUSE_DOOR['to_floor']
    assert (hero['x'], hero['y']) == (HOUSE_DOOR['to_x'], HOUSE_DOOR['to_y'])
    inner = next(d for d in m.DOORS if d['floor'] == hero['floor'])
    step_on(hero, inner['floor'], inner['cx'], inner['cy'])
    game.tick(.05)
    assert hero['floor'] != m.OUTDOOR  # re-entry cooldown
    game.tick(1.)
    assert hero['floor'] == m.OUTDOOR
    assert m.cell(hero['x'], hero['y']) == (29, 17)


def test_minion_cannot_enter_door():
    game = RtsGame(['a', 'b'])
    unit = game.actor('g1', 'guard', 0, *c(29, 17), 180, 1)
    unit.update(owner_id='a', command='hold')
    game.units['g1'] = game.minions['g1'] = unit
    for _ in range(40):
        game.move(unit, *c(29, 15), 180, .05)
    assert unit['floor'] == m.OUTDOOR and m.cell(unit['x'], unit['y']) != (29, 15)


def test_passage_connects_two_sides():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    west = next(d for d in m.DOORS if d['floor'] == m.OUTDOOR and (d['cx'], d['cy']) == (58, 22))
    step_on(hero, m.OUTDOOR, 58, 22)
    game.tick(.05)
    floor = west['to_floor']
    east_inner = max((d for d in m.DOORS if d['floor'] == floor), key=lambda d: d['cx'])
    game.tick(1.)
    step_on(hero, floor, east_inner['cx'], east_inner['cy'])
    game.tick(.05)
    assert hero['floor'] == m.OUTDOOR and m.cell(hero['x'], hero['y']) == (71, 22)


def test_chest_reward_and_respawn():
    game = RtsGame(['a', 'b'], seed=1)
    hero = game.heroes['a']
    chest = m.CHESTS[0]
    hero.update(floor=chest['floor'], x=chest['x'], y=chest['y'], hp=10)
    game.tick(.05)
    state = game.chests[chest['id']]
    assert state['ready_at'] > game.elapsed
    assert (hero['hp'] == hero['max_hp'] or hero['speed_left'] > 0 or hero['attack_left'] > 0
            or hero['weapon'] or hero['armor'] or hero['_bag'])
    hero.update(attack_left=5)
    assert game.stats(hero)['attack'] == pytest.approx(m_attack * 1.3)
    hero['x'] += 200
    game.tick(60.)
    assert state['ready_at'] > game.elapsed  # still closed after one minute
    game.tick(120.)
    assert state['ready_at'] <= game.elapsed
    world = game.snapshot('a', 'ROOM', 0)
    assert any(x['id'] == chest['id'] and x['ready'] for x in world['chests'])
    assert all(x['floor'] == hero['floor'] for x in world['chests'])


def test_walls_block_hero_attack():
    game = RtsGame(['a', 'b'])
    hero, enemy = game.heroes['a'], game.heroes['b']
    hero['x'], hero['y'] = c(34, 34)
    enemy['x'], enemy['y'] = c(46, 34)
    enemy['protected'] = 0
    game.input('a', dict(sequence=1, attack=True, aim_x=enemy['x'], aim_y=enemy['y']))
    game.tick(.05)
    assert enemy['hp'] == enemy['max_hp']


def test_dead_hero_respawns_outdoor():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    step_on(hero, 2, *m.cell(m.DOORS[1]['to_x'], m.DOORS[1]['to_y']))
    hero.update(floor=HOUSE_DOOR['to_floor'], hp=0, respawn_left=0)
    game.tick(.05)
    assert hero['hp'] > 0 and hero['floor'] == m.OUTDOOR


def test_snapshot_floor_follows_hero():
    game = RtsGame(['a', 'b'])
    game.heroes['a']['floor'] = 3
    assert game.snapshot('a', 'ROOM', 0)['floor'] == 3
    assert game.battle_snapshot('a')['floor'] == 3


def test_map_endpoint():
    app = FastAPI()
    app.include_router(squad_routes.router)
    with TestClient(app) as client:
        response = client.get('/v1/squad/map')
        duo = client.get('/v1/squad/map', params=dict(team_size=2))
    assert response.status_code == 200 and duo.status_code == 200
    assert len(response.json()['interiors']) == 8
    assert len(duo.json()['interiors']) == 6


def test_manor_door_only_exists_in_one_vs_one():
    solo, duo = RtsGame(['a', 'b']), RtsGame(['a', 'b', 'c', 'd'], team_size=2)
    for game in (solo, duo):
        step_on(game.heroes['a'], m.OUTDOOR, 123, 11)  # NE manor door
        game.tick(.05)
    assert solo.heroes['a']['floor'] in m.MANOR_FLOORS
    assert duo.heroes['a']['floor'] == m.OUTDOOR
    # In 2:2 the NE corner is a base, and its footprint is walkable ground.
    duo_base = next(b for b in duo.bases if m.cell(b['x'], b['y']) == m.cell(*m.STARTS[3]))
    assert not duo.closed(duo.heroes['a'], *c(110, 2)) and duo_base['hp'] > 0


def test_input_accepts_interior_aim():
    assert SquadInput(sequence=1, aim_x=8000, aim_y=900).aim_x == 8000


def test_hero_order_onto_house_does_not_enter_by_accident():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    step_on(hero, m.OUTDOOR, 29, 17)
    target = c(29, 13)  # inside the house footprint, right behind its door
    game.input('a', dict(sequence=1, command='move', unit_ids=['a'], order_x=target[0], order_y=target[1]))
    for _ in range(100):
        game.tick(.05)
    assert hero['floor'] == m.OUTDOOR

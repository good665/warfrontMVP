from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import rts_map as m, squad_routes
from app.config import Settings
from app.database import get_db
from app.rts_game import RtsGame
from app.security import create_access_token
from app.squad_rooms import SquadRooms


def test_dev_teleport_into_every_interior_and_outdoors():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    for floor in m.INTERIORS:
        game.dev_command('a', 'teleport', floor=floor)
        assert hero['floor'] == floor and not m.blocked(floor, *m.cell(hero['x'], hero['y']))
    game.dev_command('a', 'teleport', floor=m.OUTDOOR, x=3200, y=3200)
    assert hero['floor'] == m.OUTDOOR and m.cell(hero['x'], hero['y']) == (64, 64)
    game.dev_command('a', 'teleport', floor=m.OUTDOOR, x=1475, y=575)  # inside the NW house: lands on open ground
    assert not m.blocked(m.OUTDOOR, *m.cell(hero['x'], hero['y']))


def test_dev_teleport_rejects_manors_in_two_vs_two_and_unknown_floors():
    game = RtsGame(['a', 'b', 'c', 'd'], team_size=2)
    for floor in (*m.MANOR_FLOORS, 99):
        with pytest.raises(ValueError):
            game.dev_command('a', 'teleport', floor=floor)


def test_dev_give_any_item():
    game = RtsGame(['a', 'b'])
    hero = game.heroes['a']
    game.dev_command('a', 'give', item='axe')
    game.dev_command('a', 'give', item='long_whip')
    assert 'axe' in hero['_bag'] and 'long_whip' in hero['_bag']
    with pytest.raises(ValueError):
        game.dev_command('a', 'give', item='nuke')


def test_dev_tools_cannot_be_enabled_in_prod():
    with pytest.raises(ValueError):
        Settings(environment='prod', jwt_secret='x' * 40, squad_dev_tools=True)


@pytest.mark.parametrize('enabled', [False, True])
def test_dev_route_only_exists_when_enabled(monkeypatch, enabled):
    rooms = SquadRooms(clock=lambda: 0.)
    monkeypatch.setattr(squad_routes, 'squad_rooms', rooms)
    monkeypatch.setattr(squad_routes.settings, 'squad_dev_tools', enabled)
    app = FastAPI()
    app.include_router(squad_routes.router)
    app.dependency_overrides[get_db] = lambda: SimpleNamespace(get=lambda model, pid: SimpleNamespace(display_name=pid))
    headers = {'Authorization': 'Bearer ' + create_access_token('a')}
    with TestClient(app) as client:
        code = client.post('/v1/squad/computer', json={}, headers=headers).json()['code']
        response = client.post(f'/v1/squad/{code}/dev', json={'action': 'give', 'item': 'top'}, headers=headers)
        bad = client.post(f'/v1/squad/{code}/dev', json={'action': 'give', 'item': 'nuke'}, headers=headers)
    hero = rooms.rooms[code]['game'].heroes['a']
    if enabled:
        assert response.status_code == 200 and 'top' in hero['_bag'] and bad.status_code == 422
    else:
        assert response.status_code == 404 and 'top' not in hero['_bag']

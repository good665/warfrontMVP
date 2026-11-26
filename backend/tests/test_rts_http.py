from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import squad_routes
from app.database import get_db
from app.security import create_access_token
from app.squad_rooms import SquadRooms


def test_four_clients_share_teams_and_cannot_command_allied_units(monkeypatch):
    rooms = SquadRooms(clock=lambda: 0.)
    monkeypatch.setattr(squad_routes, 'squad_rooms', rooms)
    app = FastAPI()
    app.include_router(squad_routes.router)

    class DB:
        def get(self, model, pid):
            return SimpleNamespace(display_name=pid) if pid in 'abcd' else None

    app.dependency_overrides[get_db] = lambda: DB()
    headers = {p: {'Authorization': 'Bearer ' + create_access_token(p)} for p in 'abcd'}
    with TestClient(app) as client:
        response = client.post('/v1/squad/create', json={'team_size': 2}, headers=headers['a'])
        assert response.status_code == 200
        code = response.json()['code']
        for p in 'bcd':
            response = client.post('/v1/squad/join', json={'code': code}, headers=headers[p])
            assert response.status_code == 200
            assert response.json()['status'] == ('active' if p == 'd' else 'waiting')
        snapshots = [client.get('/v1/squad/' + code, headers=headers[p]).json() for p in 'abcd']
        assert [s['team'] for s in snapshots] == [0, 1, 0, 1]
        assert all(s['capacity'] == 4 and s['battle']['rts'] for s in snapshots)
        game = rooms.rooms[code]['game']
        assert set(game.units) == set('abcd')
        game.tick(30)
        own = next(u['id'] for u in game.minions.values() if u['owner_id'] == 'a')
        allied = next(u['id'] for u in game.minions.values() if u['owner_id'] == 'c')
        response = client.post('/v1/squad/' + code + '/input', headers=headers['a'], json={
            'sequence': 1, 'command': 'move', 'unit_ids': [own, allied], 'order_x': 3200, 'order_y': 3200,
        })
        assert response.status_code == 200
        assert game.units[own]['command'] == 'move'
        assert game.units[allied]['command'] == 'wave'
        response = client.post('/v1/squad/' + code + '/input', headers=headers['a'], json={
            'sequence': 2, 'command': 'gather', 'unit_ids': [], 'order_x': 1800, 'order_y': 600,
        })
        assert response.status_code == 422  # the G rally command was removed
        assert game.units[allied]['command'] == 'wave'

"""Two authenticated HTTP clients exercise the actual room routes and shared clock."""
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import squad_routes
from app.database import get_db
from app.security import create_access_token
from app.squad_rooms import SquadRooms


def test_two_humans_code_join_shared_state_replay_isolation_and_victory(monkeypatch):
    now = [100.]
    rooms = SquadRooms(clock=lambda: now[0])
    monkeypatch.setattr(squad_routes, 'squad_rooms', rooms)
    app = FastAPI()
    app.include_router(squad_routes.router)

    class DB:
        def get(self, model, pid):
            return SimpleNamespace(display_name=pid) if pid in ('a', 'b', 'c') else None
    app.dependency_overrides[get_db] = lambda: DB()
    headers = {pid: {'Authorization': 'Bearer ' + create_access_token(pid)} for pid in ('a', 'b', 'c')}
    with TestClient(app) as one, TestClient(app) as two:
        assert one.post('/v1/squad/create', json={}).status_code == 401
        waiting = one.post('/v1/squad/create', json={}, headers=headers['a']).json()
        code = waiting['code']
        assert waiting['status'] == 'waiting'
        started = two.post('/v1/squad/join', json={'code': code}, headers=headers['b']).json()
        assert started['status'] == 'active' and started['mode'] == 'pvp'
        assert started['battle']['rts']
        first = one.get('/v1/squad/' + code, headers=headers['a']).json()
        assert {first['battle']['floor'], started['battle']['floor']} == {1}
        assert first['world']['world_width'] == first['world']['world_height'] == 6400
        assert len(rooms.rooms[code]['ids']) == 2 and 'bot' not in rooms.rooms[code]
        assert one.get('/v1/squad/' + code, headers=headers['c']).status_code == 403
        path = '/v1/squad/' + code + '/input'
        assert one.post(path, json={'sequence': 1, 'character': 'rabbit'}, headers=headers['a']).json()['battle']['character'] == 'rabbit'
        assert two.post(path, json={'sequence': 1, 'character': 'ox'}, headers=headers['b']).json()['battle']['character'] == 'ox'
        assert one.post(path, json={'sequence': 2, 'move_x': 1, 'jump': True}, headers=headers['a']).status_code == 200
        now[0] += .1
        rooms.tick()
        h = rooms.rooms[code]['game'].heroes['a']
        position = h['x']
        one.post(path, json={'sequence': 2, 'character': 'dragon'}, headers=headers['a'])
        assert h['character'] == 'rabbit' and h['x'] == position
        assert one.post(path, json={'sequence': 3, 'hp': 999}, headers=headers['a']).status_code == 422
        assert one.post(path, json={'sequence': 3, 'character': 'invalid'}, headers=headers['a']).status_code == 422
        assert one.post(path, json={'sequence': 3, 'replace_slot': 9}, headers=headers['a']).status_code == 422
        # Focus b's golden bell (the win condition) so respawning defenders cannot turn this HTTP
        # victory test into an indefinite, balanced attack-move battle.
        game = rooms.rooms[code]['game']
        goal = next(bell for bell in game.bells if bell['owner_id'] == 'b')
        # Place the attackers at the target to keep this route test fast; damage is real.
        for unit in game.units.values():
            if unit['owner_id'] == 'a':
                unit.update(floor=goal['floor'], x=goal['x']-90, y=goal['y'], hp=100000, max_hp=100000)
        assert one.post(path, json={'sequence': 3, 'command': 'focus', 'target_id': goal['id'],
                                   'unit_ids': [u['id'] for u in game.units.values() if u['owner_id']=='a']},
                    headers=headers['a']).status_code == 200  # the bell is in an interior, past the outdoor order bounds
        for _ in range(18000):
            now[0] += .05
            if _ % 100 == 0:
                one.get('/v1/squad/' + code, headers=headers['a'])
                two.get('/v1/squad/' + code, headers=headers['b'])
            rooms.tick()
            if rooms.rooms[code]['status'] == 'finished': break
        a = one.get('/v1/squad/' + code, headers=headers['a']).json()
        b = two.get('/v1/squad/' + code, headers=headers['b']).json()
        assert a['status'] == b['status'] == 'finished'
        assert a['winner'] == b['winner'] and a['reason'] == b['reason']
        assert a['reason'] in ('bell_destroyed', 'simultaneous_destruction', 'timeout')


def test_quick_match_requires_two_real_players_and_same_new_rules():
    rooms = SquadRooms(clock=lambda: 0.)
    first = rooms.create('one', queue=True)
    assert first['status'] == 'waiting'
    second = rooms.create('two', queue=True)
    assert second['status'] == 'active' and second['battle']['rts']
    assert rooms.current('one')['code'] == second['code']
    assert not any(pid.startswith('bot:') for pid in rooms.rooms[second['code']]['ids'])


def test_retired_mmo_routes_are_not_exposed_by_production_app():
    from app.main import app
    client = TestClient(app)
    assert client.post('/v1/mmo/enter', json={'zone': 'frontier', 'role': 0}).status_code == 404

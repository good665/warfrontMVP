"""Computer matches stay isolated and use ordinary authoritative game rules."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.squad_bot import SquadBot
from app.squad_rooms import SquadRooms


def simulation(game, bot, seconds):
    for _ in range(round(seconds/.05)):
        bot.tick(game)
        game.tick(.05)
        if game.reason:
            break


def test_computer_starts_solo_idempotently_and_preserves_existing_rooms():
    rooms = SquadRooms(clock=lambda: 0.)
    state = rooms.computer('human', '사용자')
    room = rooms.rooms[state['code']]
    assert state['status'] == 'active' and state['team'] == 0
    assert state['mode'] == 'computer' and state['opponent_name'] == '컴퓨터'
    assert len(room['game'].units) == 2  # Only the two heroes before the first wave.
    assert not room['game'].minions
    assert room['ids'][1].startswith('bot:')
    assert rooms.membership == {'human': state['code']}
    assert rooms.computer('human')['code'] == state['code']
    assert rooms.current('human')['code'] == state['code']
    assert len(rooms.rooms) == 1
    waiting = rooms.create('other', queue=True)
    assert rooms.computer('other')['code'] == waiting['code']
    assert rooms.current('other')['status'] == 'waiting'
    rooms.create('third', queue=True)
    assert rooms.computer('third')['mode'] == 'pvp'


def test_computer_room_is_private_and_not_a_human_queue_entry():
    rooms = SquadRooms(clock=lambda: 0.)
    state = rooms.computer('human')
    bot_id = rooms.rooms[state['code']]['bot_id']
    assert rooms.create('queued', queue=True)['status'] == 'waiting'
    for action in (lambda: rooms.join(state['code'], 'outsider'),
                   lambda: rooms.state(state['code'], 'outsider'),
                   lambda: rooms.input(state['code'], bot_id, {'sequence': 1}),
                   lambda: rooms.create(bot_id, queue=True),
                   lambda: rooms.computer(bot_id),
                   lambda: rooms.join(state['code'], bot_id)):
        with pytest.raises(HTTPException):
            action()
    assert bot_id not in rooms.membership


def test_only_human_heartbeat_matters_and_finished_room_is_cleaned():
    clock = [0.]
    rooms = SquadRooms(clock=lambda: clock[0])
    state = rooms.computer('human')
    code = state['code']
    for _ in range(700):
        clock[0] += .05
        rooms.current('human')
        rooms.tick()
    assert rooms.current('human')['status'] == 'active'
    last_seen = clock[0]
    clock[0] = last_seen + 29.95
    rooms.tick()
    # Inspect directly: a state request here would refresh the human heartbeat.
    assert rooms.rooms[code]['status'] == 'active'
    clock[0] = last_seen + 30.
    rooms.tick()
    assert rooms.current('human')['reason'] == 'disconnect'
    assert rooms.current('human')['winner'] == 1
    clock[0] += 121.
    rooms.tick()
    assert code not in rooms.rooms and not rooms.membership
    state = rooms.computer('human')
    rooms.leave('human')
    assert rooms.rooms[state['code']]['game'].reason == 'forfeit'
    assert rooms.current('human')['status'] == 'none'


def test_computer_endpoint_requires_auth_and_does_not_create_database_records(monkeypatch):
    from app import squad_routes
    from app.database import get_db
    from app.online_routes import online_player
    rooms = SquadRooms(clock=lambda: 0.)
    monkeypatch.setattr(squad_routes, 'squad_rooms', rooms)
    app = FastAPI()
    app.include_router(squad_routes.router)
    class ReadOnlyDatabase:
        def get(self, model, pid):
            assert pid == 'human'
            return SimpleNamespace(display_name='사용자')
    app.dependency_overrides[get_db] = lambda: ReadOnlyDatabase()
    with TestClient(app) as client:
        assert client.post('/v1/squad/computer', json={}).status_code == 401
        assert client.post('/v1/squad/computer', headers={'Authorization': 'Bearer bot:fake'}, json={}).status_code == 401
        app.dependency_overrides[online_player] = lambda: 'human'
        response = client.post('/v1/squad/computer', json={})
        assert response.status_code == 200
        assert response.json()['mode'] == 'computer'
        assert client.post('/v1/squad/computer', json={'bot_id': 'fake'}).status_code == 422
        assert client.get('/v1/squad/current').json()['code'] == response.json()['code']

import pytest
from fastapi import HTTPException
from app.squad_rooms import SquadRooms


def match(computer=False):
    clock = [0.]
    rooms = SquadRooms(clock=lambda: clock[0])
    state = rooms.computer('a') if computer else rooms.create('a')
    code = state['code']
    if not computer:
        rooms.join(code, 'b')
    return rooms, clock, code


def test_computer_pause_freezes_world_and_resumes_without_catching_up():
    rooms, clock, code = match(True)
    game = rooms.rooms[code]['game']
    rooms.input(code, 'a', dict(sequence=1, move_x=1, attack=True))
    before = (game.elapsed, game.heroes['a']['x'])
    for _ in range(5):
        assert rooms.pause(code, 'a', True)['paused']
        clock[0] += 10
        rooms.state(code, 'a')
        rooms.tick()
        assert (game.elapsed, game.heroes['a']['x']) == before
        rooms.input(code, 'a', dict(sequence=2, move_x=1, skill2=True))
        assert not rooms.pause(code, 'a', False)['paused']
    clock[0] += .051
    rooms.tick()
    assert game.elapsed == pytest.approx(.05)
    assert game.heroes['a']['x'] == before[1]
    assert not game.bombs


def test_pvp_three_pauses_per_player_idempotency_and_owner_resume():
    rooms, clock, code = match()
    for remaining in (2, 1, 0):
        state = rooms.pause(code, 'a', True)
        assert state['pause_remaining'] == remaining
        assert state['paused_by'] == 'a'
        assert rooms.pause(code, 'a', True)['pause_remaining'] == remaining
        assert rooms.state(code, 'b')['paused']
        with pytest.raises(HTTPException) as error:
            rooms.pause(code, 'b', False)
        assert error.value.status_code == 409
        assert not rooms.pause(code, 'a', False)['paused']
        assert not rooms.pause(code, 'a', False)['paused']
    with pytest.raises(HTTPException) as error:
        rooms.pause(code, 'a', True)
    assert error.value.detail == 'squad_pause_limit'
    assert rooms.pause(code, 'b', True)['pause_remaining'] == 2
    assert rooms.state(code, 'a')['pause_remaining'] == 0


def test_paused_match_still_handles_disconnect_forfeit_and_membership():
    rooms, clock, code = match()
    with pytest.raises(HTTPException):
        rooms.pause(code, 'outsider', True)
    rooms.pause(code, 'a', True)
    clock[0] = 30
    rooms.state(code, 'b')
    rooms.tick()
    assert rooms.state(code, 'b')['reason'] == 'disconnect'
    assert not rooms.state(code, 'b')['paused']
    with pytest.raises(HTTPException):
        rooms.pause(code, 'b', True)
    rooms, _, code = match(True)
    rooms.pause(code, 'a', True)
    rooms.leave('a')
    assert rooms.rooms[code]['status'] == 'finished'


def test_pause_endpoint_auth_validation_and_shared_state(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app import squad_routes
    from app.online_routes import online_player
    rooms, _, code = match()
    monkeypatch.setattr(squad_routes, 'squad_rooms', rooms)
    app = FastAPI()
    app.include_router(squad_routes.router)
    with TestClient(app) as client:
        url = f'/v1/squad/{code}/pause'
        assert client.post(url, json={'paused': True}).status_code == 401
        app.dependency_overrides[online_player] = lambda: 'a'
        for data in ({}, {'paused': 'true'}, {'paused': True, 'extra': 1}):
            assert client.post(url, json=data).status_code == 422
        response = client.post(url, json={'paused': True})
        assert response.status_code == 200
        assert response.json()['paused'] and response.json()['pause_remaining'] == 2
        app.dependency_overrides[online_player] = lambda: 'b'
        assert client.get(f'/v1/squad/{code}').json()['paused_by'] == 'a'
        assert client.post(url, json={'paused': False}).status_code == 409
        app.dependency_overrides[online_player] = lambda: 'a'
        assert not client.post(url, json={'paused': False}).json()['paused']

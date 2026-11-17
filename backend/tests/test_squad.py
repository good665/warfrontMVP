"""Isolated squad rules: no live database, rewards or global MMO state."""
import pytest
from fastapi import HTTPException
from app.squad_rooms import SquadRooms
from app.squad_routes import SquadInput


def controls(sequence=1, **kwargs):
    return SquadInput(sequence=sequence, **kwargs).model_dump()


def advance(game, seconds):
    for _ in range(round(seconds/.05)):
        game.tick(.05)


def test_rooms_queue_isolation_reconnect_and_leave():
    clock = [10.]
    rooms = SquadRooms(clock=lambda: clock[0])
    code = rooms.create('a', queue=True)['code']
    assert rooms.current('a')['status'] == 'waiting'
    assert rooms.create('b', queue=True)['code'] == code
    other = rooms.create('c')['code']
    assert other != code
    with pytest.raises(HTTPException) as error:
        rooms.state(code, 'c')
    assert error.value.status_code == 403
    for _ in range(20):
        rooms.state(code, 'a')
    assert rooms.current('a')['elapsed'] == 0
    assert rooms.join(code, 'a')['status'] == 'active'
    rooms.leave('a')
    assert rooms.current('a')['status'] == 'none'
    assert rooms.current('b')['winner'] == 1
    assert rooms.current('b')['reason'] == 'forfeit'
    rooms.leave('c')
    assert other not in rooms.rooms


def test_disconnect_requires_thirty_seconds():
    clock = [0.]
    rooms = SquadRooms(clock=lambda: clock[0])
    code = rooms.create('a')['code']
    rooms.join(code, 'b')
    clock[0] = 29
    rooms.state(code, 'b')
    rooms.tick()
    assert rooms.current('b')['status'] == 'active'
    clock[0] = 30
    rooms.tick()
    assert rooms.current('b')['reason'] == 'disconnect'
    assert rooms.current('b')['winner'] == 1


def test_input_validation_rejects_nonfinite_and_invalid_commands():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        controls(move_x=float('nan'))
    with pytest.raises(ValidationError):
        controls(command='kill')


def test_squad_endpoints_require_authentication():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.squad_routes import router
    from app.database import get_db
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: None
    with TestClient(app) as client:
        assert client.get('/v1/squad/current').status_code == 401
        assert client.post('/v1/squad/create', json={}).status_code == 401



import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_test_dir = tempfile.TemporaryDirectory(prefix="warfront-online-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(_test_dir.name) / "test.db").as_posix()
os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-only-secret-with-at-least-32-bytes"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Match, Player
from app.online_arena import OnlineArena, line_clear
from app.online_rooms import rooms


@pytest.fixture
def online():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    clock = [1000.0]
    original_clock = rooms.clock
    rooms.clock = lambda: clock[0]
    try:
        with TestClient(app) as client:
            yield client, clock
    finally:
        rooms.clock = original_clock
        engine.dispose()


def login(client, name):
    response = client.post("/v1/auth/guest", json={"device_id": uuid.uuid4().hex, "display_name": name})
    assert response.status_code == 200
    auth = response.json()
    return {"Authorization": "Bearer " + auth["access_token"]}, auth["player"]["id"]


def paired(client):
    first, first_id = login(client, "online-first")
    second, second_id = login(client, "online-second")
    created = client.post("/v1/rooms", json={"role": 0}, headers=first)
    assert created.status_code == 200
    code = created.json()["code"]
    joined = client.post(f"/v1/rooms/{code}/join", json={"role": 2}, headers=second)
    assert joined.status_code == 200
    return code, first, second, first_id, second_id


def start(client, code, first, second):
    assert client.post(f"/v1/rooms/{code}/ready", json={"ready": True, "role": 0}, headers=first).json()["status"] == "waiting"
    response = client.post(f"/v1/rooms/{code}/ready", json={"ready": True, "role": 2}, headers=second)
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    return response.json()


def test_room_requires_authentication_and_membership(online):
    client, _ = online
    assert client.post("/v1/rooms", json={"role": 0}).status_code == 401
    code, first, second, *_ = paired(client)
    outsider, _ = login(client, "outsider")
    assert client.get(f"/v1/rooms/{code}", headers=outsider).status_code == 403
    assert client.post(f"/v1/rooms/{code}/join", json={"role": 0}, headers=outsider).status_code == 409
    assert client.get("/v1/rooms/current", headers=first).json()["code"] == code
    assert client.post(f"/v1/rooms/{code.lower()}/join", json={"role": 2}, headers=second).json()["slot"] == 1
    assert len(client.get(f"/v1/rooms/{code}", headers=first).json()["members"]) == 2


def test_two_humans_start_once_and_share_server_owned_movement(online):
    client, clock = online
    code, first, second, *_ = paired(client)
    assert client.get("/v1/me", headers=first).json()["stamina"] == 100
    started = start(client, code, first, second)
    assert len(started["actors"]) == 2
    assert {a["name"] for a in started["actors"]} == {"online-first", "online-second"}
    for headers in (first, second):
        assert client.get("/v1/me", headers=headers).json()["stamina"] == 90
    assert client.post(f"/v1/rooms/{code}/ready", json={"ready": True}, headers=second).json()["status"] == "active"
    assert client.get("/v1/me", headers=second).json()["stamina"] == 90
    client.post(f"/v1/rooms/{code}/input", json={"sequence": 1, "move_x": 1}, headers=first)
    clock[0] += .2
    other = client.get(f"/v1/rooms/{code}", headers=second).json()
    own = client.get(f"/v1/rooms/{code}", headers=first).json()
    assert own["actors"] == other["actors"]
    assert 105 < own["actors"][0]["x"] <= 141.01
    assert own["elapsed"] == pytest.approx(.2)
    assert own["stage_seconds"] == 60


def test_client_cannot_submit_damage_wins_or_position(online):
    client, _ = online
    code, first, second, *_ = paired(client)
    snap = start(client, code, first, second)
    url = f"/v1/rooms/{code}/input"
    for extra in ({"x": 640}, {"hp": 9999}, {"won": True}, {"elapsed": 900}, {"move_x": 999}):
        assert client.post(url, json={"sequence": 1, **extra}, headers=first).status_code == 422
    assert client.post(f"/v1/matches/{snap['match_id']}/finish", json={"won": True}, headers=second).status_code == 403
    assert client.post("/v1/matches", json={"mode": "arena1"}, headers=second).json()["detail"] == "online_match_active"


def test_insufficient_stamina_rolls_back_both_players(online):
    client, _ = online
    code, first, second, first_id, second_id = paired(client)
    with SessionLocal() as db:
        db.get(Player, second_id).stamina = 0
        db.commit()
    client.post(f"/v1/rooms/{code}/ready", json={"ready": True}, headers=first)
    response = client.post(f"/v1/rooms/{code}/ready", json={"ready": True}, headers=second)
    assert response.status_code == 400
    assert response.json()["detail"] == "participant_stamina_low"
    with SessionLocal() as db:
        assert db.get(Player, first_id).stamina == 100
        assert db.query(Match).count() == 0
    snap = client.get(f"/v1/rooms/{code}", headers=first).json()
    assert snap["status"] == "waiting" and not any(m["ready"] for m in snap["members"])


def test_forfeit_awards_opponent_once_and_preserves_rank(online):
    client, _ = online
    code, first, second, *_ = paired(client)
    start(client, code, first, second)
    result = client.post(f"/v1/rooms/{code}/leave", headers=first).json()
    assert result["status"] == "finished" and result["winner"] == 1
    assert result["reward"] == 0 and result["settled"] is True
    for _ in range(3):
        state = client.get(f"/v1/rooms/{code}", headers=second).json()
        assert state["reward"] == 3 and state["reason"] == "forfeit"
    profile = client.get("/v1/me", headers=second).json()
    assert profile["diamonds"] == 3 and profile["rating"] == 1000
    assert profile["wins"] == 0 and profile["losses"] == 0
    assert client.get("/v1/me", headers=first).json()["stamina"] == 90


def test_waiting_room_leave_is_free(online):
    client, _ = online
    code, first, second, *_ = paired(client)
    assert client.post(f"/v1/rooms/{code}/leave", headers=first).json()["status"] == "closed"
    assert client.get("/v1/me", headers=first).json()["stamina"] == 100
    assert client.get("/v1/rooms/current", headers=second).json()["status"] == "none"


def test_disconnect_uses_server_clock_and_settles_once(online):
    client, clock = online
    code, first, second, *_ = paired(client)
    start(client, code, first, second)
    clock[0] += 10
    client.get(f"/v1/rooms/{code}", headers=second)
    clock[0] += 6
    result = client.get(f"/v1/rooms/{code}", headers=second).json()
    assert result["status"] == "finished" and result["winner"] == 1
    assert result["reason"] == "disconnect"
    assert client.get("/v1/me", headers=second).json()["diamonds"] == 3
    client.get(f"/v1/rooms/{code}", headers=second)
    assert client.get("/v1/me", headers=second).json()["diamonds"] == 3


def test_replayed_packet_does_not_retrigger_skill(online):
    client, clock = online
    code, first, second, *_ = paired(client)
    start(client, code, first, second)
    packet = {"sequence": 7, "skill1": True}
    client.post(f"/v1/rooms/{code}/input", json=packet, headers=first)
    clock[0] += .1
    snap = client.post(f"/v1/rooms/{code}/input", json=packet, headers=first).json()
    assert snap["actors"][0]["skill1_cooldown"] > 11
    clock[0] += 12.2
    snap = client.post(f"/v1/rooms/{code}/input", json=packet, headers=first).json()
    assert snap["actors"][0]["skill1_cooldown"] == 0
    assert snap["last_sequence"] == 7


def test_server_engine_minute_stage_and_cover():
    game = OnlineArena(["a", "b"], [0, 1])
    for _ in range(1199):
        game.step(.05, [{}, {}])
    assert game.stage == 1
    game.step(.05, [{}, {}])
    assert game.stage == 2 and game.dangers
    for _ in range(1200):
        game.step(.05, [{}, {}])
    assert game.stage == 3
    assert not line_clear(200, 280, 400, 280)
    assert line_clear(200, 370, 700, 370)
    with pytest.raises(ValueError):
        game.step(900, [{}, {}])


def test_server_engine_skills_damage_respawn_and_victory():
    game = OnlineArena(["a", "b"], [0, 2])
    a, b = game.actors
    a.x, a.y, a.protection = 200, 370, 0
    b.x, b.y, b.protection = 260, 370, 0
    game.step(.05, [{"attack": True, "aim_x": 260, "aim_y": 370}, {}])
    assert b.hp < b.max_hp and a.damage_done > 0
    b.hp = 10
    game.step(.05, [{}, {"skill1": True}])
    assert b.hp == 55 and b.healing_done == 45
    game.damage(b, 999, a)
    assert b.hp == 0 and a.kills == 1
    for _ in range(250):
        game.step(.05, [{}, {}])
    assert b.hp > 0
    game.blue_score = 420
    game.step(.05, [{}, {}])
    assert game.finished and game.winner == 0


def test_simultaneous_ready_creates_only_two_match_rows(online):
    client, _ = online
    code, first, second, *_ = paired(client)
    def ready(headers):
        return client.post(f"/v1/rooms/{code}/ready", json={"ready": True}, headers=headers)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(ready, (first, second)))
    assert all(r.status_code == 200 for r in results)
    assert client.get(f"/v1/rooms/{code}", headers=first).json()["status"] == "active"
    with SessionLocal() as db:
        assert db.query(Match).filter(Match.mode == "online1").count() == 2
        assert all(p.stamina == 90 for p in db.query(Player).all())


def test_failed_settlement_rolls_back_and_retries_once(online, monkeypatch):
    from sqlalchemy.orm import Session
    client, _ = online
    code, first, second, first_id, second_id = paired(client)
    start(client, code, first, second)
    def fail_commit(_):
        raise RuntimeError("simulated database outage")
    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        with pytest.raises(RuntimeError):
            rooms.leave(code, first_id)
    with SessionLocal() as db:
        assert db.get(Player, second_id).diamonds == 0
        assert all(m.status == "active" for m in db.query(Match).all())
    rooms.tick()
    assert client.get("/v1/me", headers=second).json()["diamonds"] == 3
    rooms.tick()
    assert client.get("/v1/me", headers=second).json()["diamonds"] == 3


def test_server_restart_recovers_orphaned_match_stamina(online):
    import asyncio
    from app.online_rooms import RoomManager
    client, _ = online
    headers, player_id = login(client, "restart-test")
    with SessionLocal() as db:
        db.get(Player, player_id).stamina = 90
        db.add(Match(player_id=player_id, mode="online1"))
        db.commit()
    async def restart():
        manager = RoomManager()
        manager.start()
        await manager.stop()
    asyncio.run(restart())
    assert client.get("/v1/me", headers=headers).json()["stamina"] == 100
    with SessionLocal() as db:
        assert db.query(Match).one().status == "abandoned"


def test_six_humans_ready_for_team_match_and_settle_by_team(online):
    client, _ = online
    players = [login(client, f"squad-person-{i}") for i in range(6)]
    code = client.post("/v1/rooms", json={"role": 0, "team_size": 3}, headers=players[0][0]).json()["code"]
    for i in range(1, 6):
        response = client.post(f"/v1/rooms/{code}/join", json={"role": i % 3}, headers=players[i][0])
        assert response.status_code == 200
        assert response.json()["slot"] == i and response.json()["team"] == i % 2
    for i in range(5):
        response = client.post(f"/v1/rooms/{code}/ready", json={"ready": True, "role": i % 3}, headers=players[i][0])
        assert response.json()["status"] == "waiting"
    assert all(client.get("/v1/me", headers=h).json()["stamina"] == 100 for h, _ in players)
    response = client.post(f"/v1/rooms/{code}/ready", json={"ready": True, "role": 2}, headers=players[5][0])
    snap = response.json()
    assert snap["status"] == "active" and snap["team_size"] == 3
    assert len(snap["actors"]) == 6
    assert {a["name"] for a in snap["actors"]} == {f"squad-person-{i}" for i in range(6)}
    assert [a["team"] for a in snap["actors"]].count(0) == 3
    assert snap["remaining"] == 1200
    assert all(client.get("/v1/me", headers=h).json()["stamina"] == 90 for h, _ in players)
    client.post(f"/v1/rooms/{code}/leave", headers=players[5][0])
    for i, (headers, _) in enumerate(players):
        state = client.get(f"/v1/rooms/{code}", headers=headers).json()
        assert state["status"] == "finished" and state["winner"] == 0
        assert state["reward"] == (5 if i % 2 == 0 else 0)
        assert client.get("/v1/me", headers=headers).json()["diamonds"] == state["reward"]
    with SessionLocal() as db:
        assert db.query(Match).filter(Match.mode == "online3").count() == 6


def test_team_support_heals_only_nearby_living_allies():
    game = OnlineArena([str(i) for i in range(6)], [2, 0, 0, 0, 1, 0])
    for actor in game.actors:
        actor.hp = 20
        actor.x, actor.y = 200, 370
    game.actors[4].x = 800
    game.actors[2].hp = 0
    game.skill(game.actors[0], False)
    assert game.actors[0].hp == 65
    assert game.actors[1].hp == 20
    assert game.actors[2].hp == 0
    assert game.actors[4].hp == 20


def test_invalid_room_size_rejected(online):
    client, _ = online
    headers, _ = login(client, "bad-size")
    assert client.post("/v1/rooms", json={"team_size": 2}, headers=headers).status_code == 422


@pytest.mark.parametrize("team_size", [1, 3])
def test_quick_match_waits_for_real_players_and_starts_automatically(online, team_size):
    client, _ = online
    players = [login(client, f"quick-{i}") for i in range(team_size * 2)]
    codes = []
    for i, (headers, _) in enumerate(players):
        response = client.post("/v1/rooms/quick-match", json={"role": i % 3, "team_size": team_size}, headers=headers)
        assert response.status_code == 200
        snap = response.json()
        codes.append(snap["code"])
        assert snap["matchmaking"] is True
        assert snap["status"] == ("active" if i == len(players) - 1 else "waiting")
    assert len(set(codes)) == 1
    state = client.get(f"/v1/rooms/{codes[0]}", headers=players[0][0]).json()
    assert len(state["actors"]) == team_size * 2
    assert all(client.get("/v1/me", headers=h).json()["stamina"] == 90 for h, _ in players)


def test_quick_match_cancel_preserves_other_waiting_members(online):
    client, _ = online
    first, first_id = login(client, "queue-cancel")
    second, _ = login(client, "queue-stay")
    code = client.post("/v1/rooms/quick-match", json={"team_size": 3}, headers=first).json()["code"]
    assert client.post("/v1/rooms/quick-match", json={"team_size": 3}, headers=second).json()["code"] == code
    assert client.post(f"/v1/rooms/{code}/leave", headers=first).json()["status"] == "none"
    state = client.get("/v1/rooms/current", headers=second).json()
    assert state["code"] == code and state["status"] == "waiting" and len(state["members"]) == 1
    assert client.get("/v1/me", headers=first).json()["stamina"] == 100
    assert first_id not in rooms.membership


def test_quick_match_does_not_use_private_rooms_or_other_team_sizes(online):
    client, _ = online
    private, _ = login(client, "private-host")
    solo, _ = login(client, "quick-solo")
    squad, _ = login(client, "quick-squad")
    private_code = client.post("/v1/rooms", json={"team_size": 1}, headers=private).json()["code"]
    solo_code = client.post("/v1/rooms/quick-match", json={"team_size": 1}, headers=solo).json()["code"]
    squad_code = client.post("/v1/rooms/quick-match", json={"team_size": 3}, headers=squad).json()["code"]
    assert len({private_code, solo_code, squad_code}) == 3
    assert client.post(f"/v1/rooms/{solo_code}/join", json={}, headers=private).json()["detail"] == "use_quick_match"


def test_disconnected_queue_member_is_removed_without_charging(online):
    client, clock = online
    first, _ = login(client, "stale-queue")
    second, _ = login(client, "fresh-queue")
    code = client.post("/v1/rooms/quick-match", json={"team_size": 3}, headers=first).json()["code"]
    clock[0] += 16
    state = client.post("/v1/rooms/quick-match", json={"team_size": 3}, headers=second).json()
    assert state["status"] == "waiting" and len(state["members"]) == 1
    assert code not in rooms.rooms
    assert client.get("/v1/me", headers=first).json()["stamina"] == 100


def test_queue_cancel_racing_match_start_does_not_forfeit(online):
    client, _ = online
    first, _ = login(client, "cancel-race-first")
    second, _ = login(client, "cancel-race-second")
    code = client.post("/v1/rooms/quick-match", json={"team_size": 1}, headers=first).json()["code"]
    assert client.post("/v1/rooms/quick-match", json={"team_size": 1}, headers=second).json()["status"] == "active"
    result = client.post(f"/v1/rooms/{code}/leave", json={"waiting_only": True}, headers=first).json()
    assert result["status"] == "active" and result["winner"] == -1
    assert client.get("/v1/me", headers=second).json()["diamonds"] == 0


def test_private_ready_waits_for_connected_participants(online):
    client, clock = online
    code, first, second, *_ = paired(client)
    client.post(f"/v1/rooms/{code}/ready", json={"ready": True}, headers=first)
    clock[0] += 16
    response = client.post(f"/v1/rooms/{code}/ready", json={"ready": True}, headers=second)
    assert response.status_code == 409 and response.json()["detail"] == "participant_offline"
    assert client.get("/v1/me", headers=first).json()["stamina"] == 100
    assert client.get("/v1/me", headers=second).json()["stamina"] == 100

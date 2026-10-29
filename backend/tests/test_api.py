import os
import uuid
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

_test_dir = tempfile.TemporaryDirectory(prefix="warfront-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(_test_dir.name) / "test.db").as_posix()
os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-only-secret-with-at-least-32-bytes"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Match, Player

client = None


@pytest.fixture(autouse=True)
def fresh_db():
    global client
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        client = test_client
        yield
    engine.dispose()


def login(name="tester"):
    res = client.post("/v1/auth/guest", json={"device_id": uuid.uuid4().hex, "display_name": name})
    assert res.status_code == 200, res.text
    body = res.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["player"]


def age_match(match_id: str, seconds: float):
    with SessionLocal() as db:
        m = db.get(Match, match_id)
        m.started_at = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        db.commit()


def test_guest_login_is_idempotent_per_device():
    device = uuid.uuid4().hex
    a = client.post("/v1/auth/guest", json={"device_id": device, "display_name": "alpha"}).json()
    b = client.post("/v1/auth/guest", json={"device_id": device, "display_name": "ignored"}).json()
    assert a["player"]["id"] == b["player"]["id"]


def test_duplicate_display_name_conflicts():
    login("same-name")
    res = client.post("/v1/auth/guest", json={"device_id": uuid.uuid4().hex, "display_name": "same-name"})
    assert res.status_code == 409 and res.json()["detail"] == "display_name_taken"


def test_guest_session_refresh_returns_persisted_server_state():
    device = uuid.uuid4().hex
    payload = {"device_id": device, "display_name": "지휘관_123456789abc"}
    first = client.post("/v1/auth/guest", json=payload)
    assert first.status_code == 200
    account = first.json()
    player_id = account["player"]["id"]
    with SessionLocal() as db:
        player = db.get(Player, player_id)
        player.diamonds = 42
        player.stamina = 70
        player.rating = 1200
        player.wins = 2
        player.power = 3
        player.pve_best_stage = 4
        db.commit()

    headers = {"Authorization": f"Bearer {account['access_token']}"}
    refreshed = client.get("/v1/me", headers=headers)
    assert refreshed.status_code == 200
    state = refreshed.json()
    assert state["id"] == player_id
    assert state["diamonds"] == 42 and state["stamina"] == 70
    assert state["rating"] == 1200 and state["wins"] == 2
    assert state["power"] == 3 and state["pve_best_stage"] == 4
    assert 0 < state["next_stamina_in_seconds"] <= 3600
    assert state["daily_ad_views"] == 0
    assert state["daily_reward_claimed"] is False

    # A fresh Unity session logs in again with its persisted guest identifier.
    resumed = client.post("/v1/auth/guest", json={**payload, "display_name": "다른이름"})
    assert resumed.status_code == 200
    for field in ("id", "display_name", "diamonds", "stamina", "rating", "wins", "power", "pve_best_stage"):
        assert resumed.json()["player"][field] == state[field]
    headers = {"Authorization": f"Bearer {resumed.json()['access_token']}"}
    assert client.get("/v1/me", headers=headers).json()["id"] == player_id


def test_endpoints_require_auth():
    assert client.get("/v1/me").status_code == 401
    assert client.post("/v1/matches", json={"mode": "pvp"}).status_code == 401


def test_pvp_win_flow_and_single_settlement():
    h, _ = login()
    start = client.post("/v1/matches", json={"mode": "pvp"}, headers=h).json()
    assert start["player"]["stamina"] == 90
    age_match(start["match_id"], 10)
    done = client.post(f"/v1/matches/{start['match_id']}/finish", json={"won": True}, headers=h).json()
    assert done["rating_delta"] == 100 and done["diamonds_gained"] == 3
    assert done["player"]["rating"] == 1100 and done["player"]["wins"] == 1
    again = client.post(f"/v1/matches/{start['match_id']}/finish", json={"won": True}, headers=h)
    assert again.status_code == 409  # 이중 정산 방지


def test_instant_win_rejected():
    h, _ = login()
    start = client.post("/v1/matches", json={"mode": "pvp"}, headers=h).json()
    res = client.post(f"/v1/matches/{start['match_id']}/finish", json={"won": True}, headers=h)
    assert res.status_code == 400 and res.json()["detail"] == "finish_too_early"


def test_settlement_retry_after_lost_response_keeps_reward_once():
    device = uuid.uuid4().hex
    payload = {"device_id": device, "display_name": "retry-player"}
    auth = client.post("/v1/auth/guest", json=payload).json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    match = client.post("/v1/matches", json={"mode": "pvp"}, headers=headers).json()
    age_match(match["match_id"], 10)
    url = f"/v1/matches/{match['match_id']}/finish"
    # The server commits, but the client may never receive this response.
    assert client.post(url, json={"won": True}, headers=headers).status_code == 200

    # A restarted client authenticates with its existing guest identity.
    resumed = client.post("/v1/auth/guest", json=payload).json()
    headers = {"Authorization": f"Bearer {resumed['access_token']}"}
    repeated = client.post(url, json={"won": True}, headers=headers)
    assert repeated.status_code == 409
    assert repeated.json()["detail"] == "match_already_finished"
    state = client.get("/v1/me", headers=headers).json()
    assert state["diamonds"] == 3 and state["wins"] == 1
    assert state["rating"] == 1100 and state["stamina"] == 90


def test_rejected_early_result_can_be_retried_for_same_match():
    headers, _ = login()
    match = client.post("/v1/matches", json={"mode": "pve"}, headers=headers).json()
    url = f"/v1/matches/{match['match_id']}/finish"
    assert client.post(url, json={"won": True}, headers=headers).status_code == 400
    age_match(match["match_id"], 10)
    result = client.post(url, json={"won": True}, headers=headers)
    assert result.status_code == 200
    assert result.json()["diamonds_gained"] == 3
    assert result.json()["player"]["stamina"] == 90


def test_survival_reward_capped_by_server_time():
    h, _ = login()
    start = client.post("/v1/matches", json={"mode": "rush"}, headers=h).json()
    age_match(start["match_id"], 31)
    done = client.post(f"/v1/matches/{start['match_id']}/finish", json={"survival_seconds": 3000}, headers=h).json()
    assert done["survival_seconds"] <= 32.0
    assert done["diamonds_gained"] == 2


@pytest.mark.parametrize("mode", ["pvp", "pve", "rush", "bomb"])
def test_retreat_settles_once_without_refunding_stamina(mode):
    headers, _ = login()
    start = client.post("/v1/matches", json={"mode": mode}, headers=headers).json()
    age_match(start["match_id"], 360)
    url = f"/v1/matches/{start['match_id']}/finish"
    # Survival time excludes time spent paused, even when more wall time elapsed.
    result = client.post(url, json={"won": False, "survival_seconds": 31}, headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["player"]["stamina"] == 90
    assert body["won"] is False
    if mode == "pvp":
        assert body["player"]["losses"] == 1
        assert body["rating_delta"] == -100
        assert body["diamonds_gained"] == 0
    elif mode == "pve":
        assert body["player"]["pve_best_stage"] == 0
        assert body["diamonds_gained"] == 0
    else:
        assert body["survival_seconds"] == 31
        assert body["diamonds_gained"] == 2
    assert client.post(url, json={"won": False}, headers=headers).status_code == 409
    state = client.get("/v1/me", headers=headers).json()
    assert state["diamonds"] == body["player"]["diamonds"]
    assert state["losses"] == body["player"]["losses"]


@pytest.mark.parametrize("mode,reward", [("arena1", 3), ("arena3", 5)])
def test_ai_arena_win_rewards_without_changing_ranked_results(mode, reward):
    headers, _ = login()
    start = client.post("/v1/matches", json={"mode": mode}, headers=headers)
    assert start.status_code == 201
    match_id = start.json()["match_id"]
    url = f"/v1/matches/{match_id}/finish"
    assert client.post(url, json={"won": True}, headers=headers).json()["detail"] == "finish_too_early"
    age_match(match_id, 700)
    result = client.post(url, json={"won": True}, headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["mode"] == mode and body["won"] is True
    assert body["diamonds_gained"] == reward and body["player"]["diamonds"] == reward
    assert body["rating_delta"] == 0 and body["player"]["rating"] == 1000
    assert body["player"]["wins"] == 0 and body["player"]["losses"] == 0
    assert body["player"]["stamina"] == 90
    with SessionLocal() as db:
        assert db.get(Match, match_id).won is True
    assert client.post(url, json={"won": True}, headers=headers).status_code == 409
    assert client.get("/v1/me", headers=headers).json()["diamonds"] == reward


@pytest.mark.parametrize("mode", ["arena1", "arena3"])
def test_ai_arena_retreat_has_no_reward_or_rank_penalty(mode):
    headers, _ = login()
    start = client.post("/v1/matches", json={"mode": mode}, headers=headers).json()
    result = client.post(f"/v1/matches/{start['match_id']}/finish", json={"won": False}, headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["diamonds_gained"] == 0 and body["rating_delta"] == 0
    assert body["player"]["stamina"] == 90 and body["player"]["losses"] == 0


def test_ai_arena_expiration_does_not_grant_rewards():
    headers, _ = login()
    start = client.post("/v1/matches", json={"mode": "arena3"}, headers=headers).json()
    age_match(start["match_id"], 1801)
    result = client.post(f"/v1/matches/{start['match_id']}/finish", json={"won": True}, headers=headers)
    assert result.status_code == 409 and result.json()["detail"] == "match_expired"
    assert client.get("/v1/me", headers=headers).json()["diamonds"] == 0


def test_stamina_runs_out():
    h, _ = login()
    for _ in range(10):
        assert client.post("/v1/matches", json={"mode": "bomb"}, headers=h).status_code == 201
    res = client.post("/v1/matches", json={"mode": "bomb"}, headers=h)
    assert res.status_code == 400 and res.json()["detail"] == "not_enough_stamina"


def test_upgrade_requires_diamonds_then_succeeds():
    h, p = login()
    assert client.post("/v1/me/upgrade", headers=h).json()["detail"] == "not_enough_diamonds"
    with SessionLocal() as db:
        db.get(Player, p["id"]).diamonds = 10
        db.commit()
    res = client.post("/v1/me/upgrade", headers=h).json()
    assert res["power"] == 1 and res["diamonds"] == 0


def test_ad_stamina_limits():
    h, _ = login()
    assert client.post("/v1/me/ad-stamina", headers=h).json()["detail"] == "stamina_full"
    client.post("/v1/matches", json={"mode": "pvp"}, headers=h)  # 90
    res = client.post("/v1/me/ad-stamina", headers=h).json()
    assert res["recovered"] == 10 and res["player"]["daily_ad_views"] == 1


def test_leaderboard_and_daily_reward_once():
    h, _ = login("first")
    board = client.get("/v1/leaderboard", headers=h).json()
    assert board["my_rank"] == 1 and board["entries"][0]["is_me"] is True
    res = client.post("/v1/me/daily-reward", headers=h).json()
    assert res["reward"] == 100
    assert client.post("/v1/me/daily-reward", headers=h).json()["detail"] == "reward_already_claimed"


def test_me_and_invalid_token():
    h, p = login()
    assert client.get("/v1/me", headers=h).json()["id"] == p["id"]
    assert client.get("/v1/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_foreign_and_abandoned_match():
    h, _ = login("owner")
    other, _ = login("other")
    match = client.post("/v1/matches", json={"mode": "pvp"}, headers=h).json()["match_id"]
    url = f"/v1/matches/{match}/finish"
    assert client.post(url, json={}, headers=other).status_code == 404
    client.post("/v1/matches", json={"mode": "pvp"}, headers=h)
    assert client.post(url, json={}, headers=h).status_code == 409


def test_pve_and_expiration():
    h, _ = login()
    match = client.post("/v1/matches", json={"mode": "pve"}, headers=h).json()["match_id"]
    age_match(match, 10)
    done = client.post(f"/v1/matches/{match}/finish", json={"won": True}, headers=h)
    assert done.status_code == 200
    assert done.json()["player"]["pve_best_stage"] == 1
    assert done.json()["diamonds_gained"] == 3
    match = client.post("/v1/matches", json={"mode": "pvp"}, headers=h).json()["match_id"]
    age_match(match, 1801)
    assert client.post(f"/v1/matches/{match}/finish", json={}, headers=h).json()["detail"] == "match_expired"


def test_invalid_game_inputs():
    h, _ = login()
    assert client.post("/v1/matches", json={"mode": "unknown"}, headers=h).status_code == 422
    match = client.post("/v1/matches", json={"mode": "rush"}, headers=h).json()["match_id"]
    assert client.post(f"/v1/matches/{match}/finish", json={"survival_seconds": -1}, headers=h).status_code == 422


def test_expired_token():
    import jwt
    from app.config import settings
    token = jwt.encode({"sub": "missing", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}, settings.jwt_secret, algorithm="HS256")
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_recovery_and_ad_daily_reset():
    from app import game_rules as rules
    h, p = login()
    with SessionLocal() as db:
        player = db.get(Player, p["id"])
        player.stamina = 50
        player.last_stamina_at = datetime.now(timezone.utc) - timedelta(seconds=3601)
        player.daily_ad_views = 5
        player.daily_ad_date = rules.today_key()
        db.commit()
    assert client.get("/v1/me", headers=h).json()["stamina"] == 55
    assert client.post("/v1/me/ad-stamina", headers=h).json()["detail"] == "ad_limit_reached"
    with SessionLocal() as db:
        db.get(Player, p["id"]).daily_ad_date = "2000-01-01"
        db.commit()
    assert client.post("/v1/me/ad-stamina", headers=h).json()["player"]["daily_ad_views"] == 1
    assert rules.today_key(datetime(2026, 1, 1, 15, tzinfo=timezone.utc)) == "2026-01-02"


def test_tied_ranks_match_board():
    h, p = login("alpha")
    login("bravo")
    with SessionLocal() as db:
        stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for player in db.query(Player).all():
            player.created_at = stamp
        db.commit()
    board = client.get("/v1/leaderboard", headers=h).json()
    assert board["my_rank"] == next(row["rank"] for row in board["entries"] if row["is_me"])

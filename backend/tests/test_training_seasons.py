from datetime import datetime, timedelta, timezone

import pytest

from tests import test_api
from tests.test_api import fresh_db
from app import training_seasons
from app import main
from app.security import create_access_token


def at(value):
    return training_seasons.season_at(datetime.fromisoformat(value))


def test_korean_monday_boundary_and_utc_window():
    before = at("2026-11-01T14:59:59+00:00")
    after = at("2026-11-01T15:00:00+00:00")
    assert before["active_game"] == "cipher"
    assert before["next_game"] == "range"
    assert after["season_id"] == "2026-W45"
    assert after["active_game"] == "range"
    assert after["next_game"] == "drone"
    assert datetime.fromisoformat(after["starts_at"]) == datetime(2026, 11, 1, 15, tzinfo=timezone.utc)
    assert datetime.fromisoformat(after["ends_at"]) == datetime(2026, 11, 8, 15, tzinfo=timezone.utc)
    assert at("2026-11-02T00:00:00+09:00") == after


@pytest.mark.parametrize("weeks,active,next_game", [(0, "range", "drone"), (1, "drone", "cipher"), (2, "cipher", "range"), (3, "range", "drone"), (-1, "cipher", "range")])
def test_three_week_rotation(weeks, active, next_game):
    now = datetime(2026, 11, 1, 15, tzinfo=timezone.utc) + timedelta(weeks=weeks)
    result = training_seasons.season_at(now)
    assert (result["active_game"], result["next_game"]) == (active, next_game)


def test_iso_year_uses_korean_calendar():
    result = at("2027-01-03T14:59:59+00:00")
    assert result["season_id"] == "2026-W53"
    assert result["active_game"] == "cipher"
    assert at("2027-01-03T15:00:00+00:00")["season_id"] == "2027-W01"


def test_naive_datetimes_follow_existing_utc_convention():
    assert at("2026-11-01T15:00:00") == at("2026-11-01T15:00:00+00:00")


def test_default_clock_is_current_utc():
    before = datetime.now(timezone.utc)
    result = training_seasons.season_at()
    after = datetime.now(timezone.utc)
    assert before <= datetime.fromisoformat(result["server_now"]) <= after


def test_endpoint_requires_existing_authenticated_player():
    assert test_api.client.get("/v1/training/season").status_code == 401
    assert test_api.client.get("/v1/training/season", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert test_api.client.get("/v1/training/season", headers={"Authorization": f"Bearer {create_access_token('missing-player')}"}).status_code == 401


def test_endpoint_contract_uses_server_calendar(monkeypatch):
    expected = at("2026-11-01T15:00:00+00:00")
    monkeypatch.setattr(main, "season_at", lambda: expected)
    headers, _ = test_api.login("season-player")
    response = test_api.client.get("/v1/training/season", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body == expected
    assert set(body) == {"season_id", "active_game", "active_games", "next_game", "starts_at", "ends_at", "server_now", "duration_seconds", "timezone", "rotation"}
    assert body["active_games"] == ["range", "drone", "cipher"]
    assert body["rotation"] == ["range", "drone", "cipher"]
    assert body["duration_seconds"] == 45
    assert body["timezone"] == "Asia/Seoul"
    for field in ("starts_at", "ends_at", "server_now"):
        assert datetime.fromisoformat(body[field]).utcoffset() == timedelta(0)

import os
from pathlib import Path
import tempfile

_dir = tempfile.TemporaryDirectory(prefix="warfront-public-config-")
os.environ.setdefault("DATABASE_URL", "sqlite:///" + (Path(_dir.name) / "test.db").as_posix())
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("JWT_SECRET", "test-only-secret-with-at-least-32-bytes")

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, settings
from app.database import Base, engine
from app.main import app
from app.online_rooms import rooms


@pytest.mark.parametrize("secret", ["", "short", "dev-only-change-me", "change-me-to-a-long-random-string"])
def test_prod_rejects_placeholder_and_short_secrets(secret):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="prod", jwt_secret=secret)


def test_public_profile_requires_prod_and_invite_key():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="dev", jwt_secret="a" * 48, public_test_mode=True, test_access_key="b" * 32)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="prod", jwt_secret="a" * 48, public_test_mode=True, test_access_key="short")
    value = Settings(_env_file=None, environment="prod", jwt_secret="a" * 48, public_test_mode=True, test_access_key="b" * 32)
    assert value.public_test_mode


def test_public_gateway_allows_readiness_but_requires_invite(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    key = "invite-test-key-" + "x" * 32
    with monkeypatch.context() as patch:
        patch.setattr(settings, "public_test_mode", True)
        patch.setattr(settings, "test_access_key", key)
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            ready = client.get("/ready")
            assert ready.status_code == 200 and ready.json()["stage_seconds"] == 60
            assert client.post("/v1/auth/guest", json={}).status_code == 403
            assert client.post("/v1/auth/guest", json={}, headers={"X-Warfront-Test-Key": "wrong"}).status_code == 403
            assert client.post("/v1/auth/guest", json={}, headers={"X-Warfront-Test-Key": key}).status_code == 422
            assert client.post("/v1/rooms/quick-match", json={}).status_code == 403
    engine.dispose()


def test_ready_fails_when_room_loop_is_missing(monkeypatch):
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        with monkeypatch.context() as patch:
            patch.setattr(rooms, "task", None)
            response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["detail"] == "room_loop_unavailable"
    engine.dispose()

"""Check this launcher's public URL using isolated, disposable friend rooms."""
import json
from pathlib import Path
import sqlite3
import time
import uuid

from friend_server import CONNECTION, DATA, STATE, control, probe, request_json, write_json


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    live = control(state, "status")
    info = json.loads(CONNECTION.read_text(encoding="utf-8"))
    address = info["api_base_url"]
    if live["status"] != "running" or live["url"] != address or not address.startswith("https://"):
        raise RuntimeError("This check requires the launcher's running public HTTPS server")
    key = info["test_access_key"]
    probe(address, key)
    headers = {"X-Warfront-Test-Key": key}
    owned = []
    created_rooms = []
    results = []

    def request(path, body=None, token=None):
        auth = {**headers, **({"Authorization": "Bearer " + token} if token else {})}
        return request_json(address + path, body, auth, timeout=12)

    try:
        for size in (1, 3):
            start = time.monotonic()
            prefix = "CHECK" + uuid.uuid4().hex[:8]
            users = []
            for i in range(size * 2):
                auth = request("/v1/auth/guest", {"device_id": uuid.uuid4().hex, "display_name": f"{prefix}_{i}"})
                owned.append((auth["player"]["id"], auth["player"]["display_name"]))
                users.append(auth["access_token"])
            code = request("/v1/rooms", {"team_size": size, "role": 0}, users[0])["code"]
            created_rooms.append((code, users))
            for i, token in enumerate(users[1:], 1):
                request(f"/v1/rooms/{code}/join", {"role": i % 3}, token)
            for i, token in enumerate(users):
                snapshot = request(f"/v1/rooms/{code}/ready", {"role": i % 3, "ready": True}, token)
            if snapshot["status"] != "active" or len(snapshot["actors"]) != size * 2:
                raise RuntimeError("Public friend room did not start with the expected humans")
            request(f"/v1/rooms/{code}/input", {"sequence": 1, "move_x": 1}, users[0])
            time.sleep(.15)
            observed = request(f"/v1/rooms/{code}", token=users[-1])
            if observed["actors"][0]["x"] <= 105 or observed["stage_seconds"] != 60:
                raise RuntimeError("Opponent did not receive server-owned movement")
            request(f"/v1/rooms/{code}/leave", {}, users[0])
            for i, token in enumerate(users):
                final = request(f"/v1/rooms/{code}", token=token)
                profile = request("/v1/me", token=token)
                expected = (3 if size == 1 else 5) if i % 2 else 0
                if final["winner"] != 1 or profile["diamonds"] != expected or profile["stamina"] != 90:
                    raise RuntimeError("Public settlement was not consistent")
            results.append({"mode": f"{size}v{size}", "humans": size * 2,
                            "movement": True, "server_settlement": True,
                            "elapsed_check_seconds": round(time.monotonic() - start, 2)})
            print(f"PASS: public HTTPS {size}v{size}, opponent movement and per-player settlement")
    finally:
        for code, tokens in created_rooms:
            for token in tokens:
                try:
                    request(f"/v1/rooms/{code}/leave", {}, token)
                except Exception:
                    pass
        database = (DATA / "warfront.db").resolve()
        if database.parent != DATA.resolve():
            raise RuntimeError("Unexpected test database location")
        with sqlite3.connect(database) as db:
            # Delete only records whose generated ID and display name both match.
            # Never remove players belonging to an active server-owned match.
            for player_id, name in owned:
                found = db.execute("SELECT id FROM players WHERE id=? AND display_name=?", (player_id, name)).fetchone()
                active = db.execute("SELECT id FROM matches WHERE player_id=? AND status='active'", (player_id,)).fetchone()
                if found and not active:
                    db.execute("DELETE FROM matches WHERE player_id=?", (player_id,))
                    db.execute("DELETE FROM players WHERE id=? AND display_name=?", (player_id, name))
        print("Checked cleanup of this run's generated test accounts")
    write_json(DATA / "public-check.json", {"url": address, "passed": results,
                                            "invitation_gate": True, "stage_seconds": 60})


if __name__ == "__main__":
    main()

"""Run 1v1 and 3v3 HTTP clients against an isolated temporary server.

From backend/: python tests/check_online_live.py
Uses no existing accounts or databases and shuts down its own server afterward.
"""
import json
import argparse
import os
from pathlib import Path
import socket
import site
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-test", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="warfront-live-check-") as directory:
        root = Path(directory).resolve()
        assert root.parent == Path(tempfile.gettempdir()).resolve()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        address = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        env.update(DATABASE_URL="sqlite:///" + (root / "test.db").as_posix(), ENVIRONMENT="dev",
                   JWT_SECRET=uuid.uuid4().hex + uuid.uuid4().hex, AUTO_CREATE_TABLES="true",
                   PUBLIC_TEST_MODE="false", TEST_ACCESS_KEY="")
        test_key = uuid.uuid4().hex + uuid.uuid4().hex
        if args.public_test:
            env.update(ENVIRONMENT="prod", PUBLIC_TEST_MODE="true", TEST_ACCESS_KEY=test_key)
        # Windows venv python.exe is a launcher: terminating it can leave its
        # interpreter child alive. Launch the interpreter directly with venv libs.
        env["PYTHONPATH"] = os.pathsep.join(site.getsitepackages())
        with (root / "server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [getattr(sys, "_base_executable", sys.executable), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=Path(__file__).resolve().parents[1], env=env, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                def request(path, body=None, token=None):
                    headers = {"Content-Type": "application/json"}
                    if args.public_test:
                        headers["X-Warfront-Test-Key"] = test_key
                    if token:
                        headers["Authorization"] = "Bearer " + token
                    req = urllib.request.Request(address + path, headers=headers,
                                                 data=json.dumps(body).encode() if body is not None else None)
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return json.load(response)

                deadline = time.monotonic() + 15
                while True:
                    try:
                        request("/health")
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if process.poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError("Isolated server failed to start: " + (root / "server.log").read_text())
                        time.sleep(.1)
                assert request("/ready")["status"] == "ready"
                if args.public_test:
                    try:
                        urllib.request.urlopen(urllib.request.Request(address + "/v1/auth/guest", data=b"{}", headers={"Content-Type": "application/json"}), timeout=5)
                    except urllib.error.HTTPError as error:
                        assert error.code == 403
                    else:
                        raise AssertionError("Public test gate was bypassed")
                    try:
                        request("/openapi.json")
                    except urllib.error.HTTPError as error:
                        assert error.code == 404
                    else:
                        raise AssertionError("Public test docs should be disabled")
                    print("PASS: public invitation gate and private API documentation")
                for team_size in (1, 3):
                    count = team_size * 2
                    players = [request("/v1/auth/guest", {"device_id": uuid.uuid4().hex, "display_name": f"live_{team_size}_{i}"})
                               for i in range(count)]
                    tokens = [p["access_token"] for p in players]
                    host, guest = tokens[0], tokens[-1]
                    code = request("/v1/rooms", {"role": 0, "team_size": team_size}, host)["code"]
                    for i in range(1, count):
                        request(f"/v1/rooms/{code}/join", {"role": i % 3}, tokens[i])
                    for i, token in enumerate(tokens):
                        started = request(f"/v1/rooms/{code}/ready", {"ready": True, "role": i % 3}, token)
                    assert started["status"] == "active" and len(started["actors"]) == count
                    print(f"PASS: {count} authenticated HTTP clients joined and started {team_size}v{team_size}")
                    request(f"/v1/rooms/{code}/input", {"sequence": 1, "move_x": 1, "aim_x": 800, "aim_y": 370}, host)
                    time.sleep(.2)
                    observed = request(f"/v1/rooms/{code}", token=guest)
                    assert observed["actors"][0]["x"] > started["actors"][0]["x"]
                    assert observed["elapsed"] > 0 and observed["stage_seconds"] == 60
                    print(f"PASS: {team_size}v{team_size} opponent received server-clock movement")
                    result = request(f"/v1/rooms/{code}/leave", {}, host)
                    assert result["winner"] == 1 and result["settled"]
                    for _ in range(3):
                        request(f"/v1/rooms/{code}", token=guest)
                    for i, token in enumerate(tokens):
                        profile = request("/v1/me", token=token)
                        assert profile["diamonds"] == ((3 if team_size == 1 else 5) if i % 2 else 0)
                        assert profile["stamina"] == 90
                    print(f"PASS: {team_size}v{team_size} forfeit paid each winning participant exactly once")
                    for i, token in enumerate(tokens):
                        queued = request("/v1/rooms/quick-match", {"role": i % 3, "team_size": team_size}, token)
                        assert queued["status"] == ("active" if i == count - 1 else "waiting")
                    quick_code = queued["code"]
                    assert queued["matchmaking"] and len(queued["actors"]) == count
                    request(f"/v1/rooms/{quick_code}/leave", {}, host)
                    for i, token in enumerate(tokens):
                        profile = request("/v1/me", token=token)
                        assert profile["stamina"] == 80
                        assert profile["diamonds"] == ((6 if team_size == 1 else 10) if i % 2 else 0)
                    print(f"PASS: {team_size}v{team_size} quick queue matched real clients and settled independently")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()

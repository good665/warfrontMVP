"""Supervise a private test API and optional temporary Cloudflare HTTPS tunnel.

python tools/friend_server.py start [--local-only]
python tools/friend_server.py status | probe | stop
All data/secrets stay in backend/.test-server/, never the development database.
"""
import argparse
import asyncio
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import site
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / ".test-server"
STATE = DATA / "state.json"
CONNECTION = DATA / "connection.json"


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def profile():
    DATA.mkdir(exist_ok=True)
    path = DATA / "profile.json"
    if not path.exists():
        write_json(path, {"jwt_secret": secrets.token_urlsafe(64), "test_access_key": secrets.token_urlsafe(32)})
    value = json.loads(path.read_text(encoding="utf-8"))
    if len(value["jwt_secret"]) < 32 or len(value["test_access_key"]) < 24:
        raise RuntimeError("Invalid private test profile")
    return value


def request_json(url, body=None, headers=None, timeout=5):
    supplied = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=supplied)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def control(state, action):
    return request_json(f"http://127.0.0.1:{state['control_port']}/{action}",
                        {} if action == "stop" else None,
                        {"X-Control-Token": state["control_token"]}, timeout=3)


def public_state(state):
    return {k: state.get(k) for k in ("status", "stage", "url", "api_port", "connection_file", "error")}


def probe(url, key):
    ready = request_json(url.rstrip("/") + "/ready", timeout=10)
    if ready.get("status") != "ready" or ready.get("stage_seconds") != 60 or ready.get("room_sizes") != [1, 3]:
        raise RuntimeError("Unexpected test-server readiness response")
    for supplied, expected in (({}, 403), ({"X-Warfront-Test-Key": key}, 422)):
        try:
            request_json(url.rstrip("/") + "/v1/auth/guest", {}, supplied, timeout=10)
        except urllib.error.HTTPError as error:
            if error.code != expected:
                raise RuntimeError(f"Access probe expected {expected}, received {error.code}") from error
        else:
            raise RuntimeError("Access probe unexpectedly bypassed the invitation gate")
    return {"ready": True, "invitation_gate": True, "stage_seconds": 60, "room_sizes": [1, 3]}


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def runtime_env():
    env = os.environ.copy()
    paths = [str(BACKEND), *site.getsitepackages(), env.get("PYTHONPATH", "")]
    env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(p for p in paths if p))
    return env


def verified_tunnel_client():
    binary = BACKEND / ".tools" / "cloudflared.exe"
    metadata = json.loads(binary.with_suffix(".json").read_text(encoding="utf-8"))
    if hashlib.sha256(binary.read_bytes()).hexdigest() != metadata["sha256"]:
        raise RuntimeError("Portable tunnel client verification failed")
    return binary


async def serve(local_only):
    private = profile()
    binary = None if local_only else verified_tunnel_client()
    stop = threading.Event()
    state = {"status": "starting", "stage": "starting_api", "server_id": secrets.token_hex(16),
             "control_token": secrets.token_urlsafe(32), "api_port": free_port(),
             "connection_file": str(CONNECTION), "url": None, "error": None}

    class Controller(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self):
            value = self.headers.get("X-Control-Token", "")
            if not secrets.compare_digest(value.encode(), state["control_token"].encode()):
                self.send_error(403)
                return
            if self.path == "/stop" and self.command == "POST":
                state.update(status="stopping", stage="stopping")
                stop.set()
            elif self.path != "/status" or self.command != "GET":
                self.send_error(404)
                return
            data = json.dumps(public_state(state)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = respond

    controller = ThreadingHTTPServer(("127.0.0.1", 0), Controller)
    state["control_port"] = controller.server_port
    threading.Thread(target=controller.serve_forever, daemon=True).start()
    write_json(STATE, state)
    os.environ.update(DATABASE_URL="sqlite:///" + (DATA / "warfront.db").as_posix(), ENVIRONMENT="prod",
                      JWT_SECRET=private["jwt_secret"], TEST_ACCESS_KEY=private["test_access_key"],
                      PUBLIC_TEST_MODE="true", AUTO_CREATE_TABLES="true", ALLOWED_ORIGINS="")
    import uvicorn
    server = uvicorn.Server(uvicorn.Config("app.main:app", host="127.0.0.1", port=state["api_port"],
                                         workers=1, access_log=False, log_level="warning",
                                         proxy_headers=True, forwarded_allow_ips="127.0.0.1"))
    server_task = asyncio.create_task(server.serve())
    tunnel = tunnel_log = None
    try:
        deadline = time.monotonic() + 20
        while not server.started:
            if server_task.done() or stop.is_set() or time.monotonic() > deadline:
                raise RuntimeError("Private test API did not start")
            await asyncio.sleep(.1)
        local_url = f"http://127.0.0.1:{state['api_port']}"
        await asyncio.to_thread(probe, local_url, private["test_access_key"])
        url = local_url
        if not local_only:
            state["stage"] = "connecting_https_tunnel"
            write_json(STATE, state)
            log_path = DATA / "tunnel.log"
            tunnel_log = log_path.open("w", encoding="utf-8")
            tunnel = subprocess.Popen([str(binary), "tunnel", "--no-autoupdate", "--url", local_url,
                                       "--protocol", "http2"], stdout=tunnel_log, stderr=tunnel_log,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            deadline = time.monotonic() + 90
            url = None
            while not url:
                if stop.is_set() or tunnel.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("HTTPS tunnel did not start; inspect backend/.test-server/tunnel.log")
                text = log_path.read_text(encoding="utf-8", errors="replace")[-65536:]
                urls = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", text)
                if urls:
                    candidate = urls[-1]
                    try:
                        await asyncio.to_thread(probe, candidate, private["test_access_key"])
                        url = candidate
                    except (urllib.error.URLError, TimeoutError, RuntimeError):
                        pass
                await asyncio.sleep(1)
        write_json(CONNECTION, {"api_base_url": url, "test_access_key": private["test_access_key"],
                                "notes": "Share only with invited testers. Keep this PC and test server running."})
        state.update(status="running", stage="ready", url=url)
        write_json(STATE, state)
        while not stop.is_set() and not server_task.done():
            if tunnel and tunnel.poll() is not None:
                raise RuntimeError("Temporary HTTPS tunnel stopped")
            await asyncio.sleep(.25)
    except Exception as error:
        state.update(status="failed", stage="failed", error=str(error))
        write_json(STATE, state)
    finally:
        if tunnel and tunnel.poll() is None:
            tunnel.terminate()
            try:
                tunnel.wait(timeout=5)
            except subprocess.TimeoutExpired:
                tunnel.kill()
                tunnel.wait(timeout=5)
        if tunnel_log:
            tunnel_log.close()
        server.should_exit = True
        try:
            await asyncio.wait_for(server_task, timeout=20)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            server_task.cancel()
        if state["status"] != "failed":
            state.update(status="stopped", stage="stopped")
        write_json(STATE, state)
        controller.shutdown()
        controller.server_close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("start", "serve", "status", "probe", "stop"))
    parser.add_argument("--local-only", action="store_true")
    args = parser.parse_args()
    if args.command == "serve":
        asyncio.run(serve(args.local_only))
        return
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None
    running = None
    if state:
        try:
            running = control(state, "status")
        except (urllib.error.URLError, TimeoutError):
            pass
    if args.command == "start":
        if running:
            print(json.dumps(running))
            return
        if state and state.get("api_port"):
            try:
                request_json(f"http://127.0.0.1:{state['api_port']}/ready", timeout=1)
            except (urllib.error.URLError, TimeoutError):
                pass
            else:
                raise RuntimeError("Previous API still answers; refusing to start a second writer")
        profile()
        if not args.local_only:
            verified_tunnel_client()
        with (DATA / "supervisor.log").open("a", encoding="utf-8") as log:
            command = [getattr(sys, "_base_executable", sys.executable), str(Path(__file__).resolve()), "serve"]
            if args.local_only:
                command.append("--local-only")
            process = subprocess.Popen(command, cwd=BACKEND, env=runtime_env(), stdout=log, stderr=log,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        print(json.dumps({"status": "starting", "supervisor_pid": process.pid, "state_file": str(STATE)}))
    elif args.command == "status":
        print(json.dumps(running or public_state(state or {"status": "not_started"})))
    elif args.command == "stop":
        print(json.dumps(control(state, "stop") if running else {"status": "already_stopped"}))
    else:
        if not running or running["status"] != "running":
            raise RuntimeError("Test server is not ready")
        info = json.loads(CONNECTION.read_text(encoding="utf-8"))
        print(json.dumps(probe(info["api_base_url"], info["test_access_key"])))


if __name__ == "__main__":
    main()

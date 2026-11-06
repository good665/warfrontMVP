"""Read-only probe. Exit nonzero on HTTP, database or game-loop failure."""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def check(url):
    started = time.monotonic()
    request = urllib.request.Request(url.rstrip("/") + "/ready")
    with urllib.request.urlopen(request, timeout=5) as response:
        value = json.load(response)
    if value.get("status") != "ready" or value.get("stage_seconds") != 60 or value.get("room_sizes") != [1, 3]:
        raise ValueError("Unexpected readiness response")
    return {"status": "ready", "round_trip_ms": round((time.monotonic() - started) * 1000)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.url)))
    except (OSError, ValueError, urllib.error.URLError) as error:
        # Avoid outputting URLs, headers or credentials in monitoring logs.
        print(json.dumps({"status": "unavailable", "error": type(error).__name__}))
        sys.exit(1)


if __name__ == "__main__":
    main()

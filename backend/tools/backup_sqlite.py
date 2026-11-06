"""Create consistent SQLite snapshots; restore only to a new database path."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid


def validate(connection):
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Database integrity check failed")
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"players", "matches"} <= tables:
        raise ValueError("Not a Warfront database")


def copy_database(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file():
        raise FileNotFoundError("Source database does not exist")
    if destination.exists():
        raise FileExistsError("Destination already exists; existing data will not be overwritten")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive file creation also protects against a competing restore process.
    with destination.open("xb"):
        pass
    destination.chmod(0o600)
    deadline = time.monotonic() + 30

    def progress(_status, _remaining, _total):
        if time.monotonic() > deadline:
            raise TimeoutError("SQLite snapshot exceeded 30 seconds")

    try:
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=5) as original:
            validate(original)
            with sqlite3.connect(destination, timeout=5) as snapshot:
                original.backup(snapshot, pages=256, progress=progress, sleep=.05)
                validate(snapshot)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def backup(source, output_dir):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = Path(output_dir).resolve()
    filename = "warfront-" + timestamp + "-" + uuid.uuid4().hex[:8] + ".db"
    partial = directory / (filename + ".partial")
    copy_database(source, partial)
    final = directory / filename
    partial.rename(final)
    metadata = {"file": filename, "created_utc": timestamp, "bytes": final.stat().st_size,
                "sha256": hashlib.sha256(final.read_bytes()).hexdigest(), "integrity": "ok"}
    final.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("backup")
    create.add_argument("source", type=Path)
    create.add_argument("--output-dir", required=True, type=Path)
    restore = commands.add_parser("restore")
    restore.add_argument("source", type=Path)
    restore.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "backup":
        result = backup(args.source, args.output_dir)
    else:
        result = copy_database(args.source, args.destination)
    print(json.dumps({"status": "ok", "file": str(result)}))


if __name__ == "__main__":
    main()

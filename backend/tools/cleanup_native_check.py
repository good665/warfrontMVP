"""Remove only accounts recorded by a completed Unity native test run."""
import argparse
import json
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    run_id = report["run_id"]
    if len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
        raise ValueError("Invalid native run ID")
    database = Path(__file__).resolve().parents[1] / ".test-server" / "warfront.db"
    if not database.is_file():
        raise RuntimeError("Dedicated test database is missing")
    removed = 0
    with sqlite3.connect(database) as db:
        for account in report["cleanup_accounts"]:
            player_id, name = account["id"], account["name"]
            if not name.startswith("NATIVE" + run_id[:8] + "_"):
                raise ValueError("Account does not belong to this native run")
            found = db.execute("SELECT id FROM players WHERE id=? AND display_name=?", (player_id, name)).fetchone()
            active = db.execute("SELECT id FROM matches WHERE player_id=? AND status='active'", (player_id,)).fetchone()
            if found and not active:
                db.execute("DELETE FROM matches WHERE player_id=?", (player_id,))
                removed += db.execute("DELETE FROM players WHERE id=? AND display_name=?", (player_id, name)).rowcount
    print(f"Removed {removed} completed native-check accounts")


if __name__ == "__main__":
    main()

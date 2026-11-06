import json
import sqlite3

import pytest

from tools.backup_sqlite import backup, copy_database


def test_live_wal_backup_includes_committed_data_and_restores(tmp_path):
    source = tmp_path / "live.db"
    with sqlite3.connect(source) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("CREATE TABLE players (id INTEGER PRIMARY KEY, diamonds INTEGER)")
        live.execute("CREATE TABLE matches (id INTEGER PRIMARY KEY, status TEXT)")
        live.execute("INSERT INTO players VALUES (1, 7)")
        live.execute("INSERT INTO matches VALUES (1, 'finished')")
        live.commit()
        saved = backup(source, tmp_path / "backups")
        live.execute("UPDATE players SET diamonds=9")
        live.commit()
        restored = copy_database(saved, tmp_path / "restored.db")
        with sqlite3.connect(restored) as recovered:
            assert recovered.execute("SELECT diamonds FROM players").fetchone()[0] == 7
            assert recovered.execute("SELECT status FROM matches").fetchone()[0] == "finished"
        assert live.execute("SELECT diamonds FROM players").fetchone()[0] == 9
    metadata = json.loads(saved.with_suffix(".json").read_text())
    assert metadata["integrity"] == "ok" and len(metadata["sha256"]) == 64
    with pytest.raises(FileExistsError):
        copy_database(saved, restored)


def test_backup_rejects_missing_or_unrelated_database(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        backup(missing, tmp_path / "backups")
    assert not missing.exists()
    unrelated = tmp_path / "unrelated.db"
    with sqlite3.connect(unrelated) as db:
        db.execute("CREATE TABLE unrelated (id INTEGER)")
    with pytest.raises(ValueError, match="Not a Warfront"):
        backup(unrelated, tmp_path / "backups")
    assert not list((tmp_path / "backups").glob("*.partial"))

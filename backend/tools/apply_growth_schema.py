"""Explicit additive growth schema migration, independent of AUTO_CREATE_TABLES."""
import argparse
import json
from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from app.config import settings
from app.database import Base
from app import models  # Register existing FK targets, never alter/create them here.
from app.experience_models import ExperienceEvent, ExperienceState
from app.training_models import TrainingBest, TrainingClaim, TrainingRun, TrainingSeason
from tools.backup_sqlite import backup


GROWTH_TABLES = [ExperienceState.__table__, ExperienceEvent.__table__, TrainingSeason.__table__,
                 TrainingRun.__table__, TrainingBest.__table__, TrainingClaim.__table__]


def apply_schema(engine):
    if engine.dialect.name not in ('sqlite', 'postgresql'):
        raise ValueError('Only SQLite and PostgreSQL are supported')
    with engine.begin() as connection:
        existing = set(inspect(connection).get_table_names())
        if not {'players', 'matches'} <= existing:
            raise ValueError('Expected an existing Warfront players/matches database')
        # No Player/Match DDL. checkfirst handles tables but not missing columns.
        Base.metadata.create_all(connection, tables=GROWTH_TABLES, checkfirst=True)
        # SQLite does not enforce VARCHAR lengths. PostgreSQL needs the parent
        # and all referencing season keys widened for week-game league IDs.
        if engine.dialect.name == 'postgresql':
            for table, column in (('training_seasons', 'id'), ('training_runs', 'season_id'),
                                  ('training_bests', 'season_id'), ('training_claims', 'season_id')):
                connection.exec_driver_sql(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR(16)')
        columns = {column['name'] for column in inspect(connection).get_columns('experience_states')}
        timestamp = 'TIMESTAMP WITH TIME ZONE' if engine.dialect.name == 'postgresql' else 'DATETIME'
        additions = {'first_session_at': timestamp, 'first_guide_exit_at': timestamp,
                     'first_session_censored': 'BOOLEAN NOT NULL DEFAULT FALSE',
                     'first_guide_exit_censored': 'BOOLEAN NOT NULL DEFAULT FALSE'}
        for name, definition in additions.items():
            if name not in columns:
                # Identifiers and SQL types are fixed constants, never CLI input.
                connection.exec_driver_sql(f'ALTER TABLE experience_states ADD COLUMN {name} {definition}')
        # Legacy live events without anchors have unknown cohort provenance.
        for anchor, flag, kinds in (
            ('first_session_at', 'first_session_censored', "'session_start'"),
            ('first_guide_exit_at', 'first_guide_exit_censored', "'tutorial_complete','tutorial_skip'"),
        ):
            connection.exec_driver_sql(
                f'UPDATE experience_states SET {flag} = TRUE WHERE {anchor} IS NULL AND {flag} = FALSE '
                'AND EXISTS (SELECT 1 FROM experience_events WHERE experience_events.player_id = experience_states.player_id '
                f"AND source = 'client' AND queued_ms = 0 AND kind IN ({kinds}))")
        # create_all(checkfirst=True) skips an existing table's missing indexes.
        for table in GROWTH_TABLES:
            for index in table.indexes:
                index.create(connection, checkfirst=True)
    return [table.name for table in GROWTH_TABLES]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database-url', default=settings.database_url)
    parser.add_argument('--backup-dir', type=Path, help='Create a verified SQLite snapshot before applying changes')
    args = parser.parse_args()
    url = make_url(args.database_url)
    snapshot = None
    if args.backup_dir:
        if url.get_backend_name() != 'sqlite' or not url.database or url.database == ':memory:':
            parser.error('--backup-dir requires a file-backed SQLite database; use pg_dump for PostgreSQL')
        snapshot = str(backup(Path(url.database), args.backup_dir))
    engine = create_engine(url)
    try:
        tables = apply_schema(engine)
    finally:
        engine.dispose()
    print(json.dumps(dict(status='ok', tables=tables, backup=snapshot)))


if __name__ == '__main__':
    main()

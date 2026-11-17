"""Explicit additive production migration: python -m app.mmo_schema.

Creates only the MMO tables; does not reset players or legacy balances.
"""
from sqlalchemy import inspect, text
from .database import Base, engine
from . import models  # Register the referenced players table.
from .mmo_models import Avatar


def main():
    Base.metadata.create_all(engine, tables=[Avatar.__table__])
    with engine.begin() as connection:
        columns = {column['name'] for column in inspect(connection).get_columns('mmo_avatars')}
        if 'quest_state' not in columns:
            connection.execute(text('ALTER TABLE mmo_avatars ADD COLUMN quest_state JSON NULL'))
        additions = {'helmet_rank': 'INTEGER NOT NULL DEFAULT 0',
                     'helmet': "VARCHAR(64) NOT NULL DEFAULT ''",
                     'active_loadout': 'INTEGER NOT NULL DEFAULT 0',
                     'loadouts': 'JSON NULL'}
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f'ALTER TABLE mmo_avatars ADD COLUMN {name} {definition}'))
    print('MMO additive schema ready: mmo_avatars')


if __name__ == '__main__':
    main()

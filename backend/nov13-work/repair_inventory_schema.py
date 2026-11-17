"""Back up the configured avatar table, then apply the additive equipment schema."""
import datetime
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect, text
from app.database import engine
from app import mmo_schema
from app.mmo_models import Avatar
from app.mmo_world import world

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--player-id', required=True, help='Existing avatar whose profile should be verified after repair')
player_id = parser.parse_args().player_id
with engine.connect() as connection:
    columns = [c['name'] for c in inspect(connection).get_columns('mmo_avatars')]
    before = [dict(row) for row in connection.execute(text('SELECT * FROM mmo_avatars ORDER BY player_id')).mappings()]
missing = sorted(set(Avatar.__table__.columns.keys())-set(columns))
print('Missing columns:', ', '.join(missing) or 'none')
if missing:
    if engine.dialect.name != 'postgresql':
        raise RuntimeError('This repair script expects the inspected PostgreSQL database')
    backup_dir = Path(tempfile.gettempdir())/'warfront-inventory-backups'
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir/('mmo-avatars-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.dump')
    url = engine.url
    env = os.environ.copy()
    for name, value in [('PGHOST',url.host),('PGPORT',url.port),('PGUSER',url.username),('PGPASSWORD',url.password),('PGDATABASE',url.database)]:
        if value is not None: env[name] = str(value)
    if 'sslmode' in url.query: env['PGSSLMODE'] = str(url.query['sslmode'])
    result = subprocess.run(['C:/Program Files/PostgreSQL/18/bin/pg_dump.exe','--format=custom','--table=mmo_avatars','--file',str(backup)],env=env,capture_output=True)
    if result.returncode or not backup.is_file() or backup.stat().st_size == 0:
        raise RuntimeError('Avatar backup failed; migration was not applied')
    print('Backup:', backup)
    print('Backup SHA256:',hashlib.sha256(backup.read_bytes()).hexdigest())
    mmo_schema.main()

with engine.connect() as connection:
    remaining = sorted(set(Avatar.__table__.columns.keys())-{c['name'] for c in inspect(connection).get_columns('mmo_avatars')})
    after = [dict(row) for row in connection.execute(text('SELECT * FROM mmo_avatars ORDER BY player_id')).mappings()]
    preserved = [{key:row[key] for key in columns} for row in after] == before
if remaining: raise RuntimeError('Schema columns still missing: '+','.join(remaining))
if not preserved: raise RuntimeError('Existing avatar columns changed during repair; inspect concurrent activity')
profile = world.profile(player_id)
assert len(profile['loadouts']) == 3
print(json.dumps(dict(status='ok', existing_rows_preserved=len(before),inventory_items=len(profile['inventory']),loadouts=len(profile['loadouts']),active_loadout=profile['active_loadout']),ensure_ascii=False))

"""Isolated localhost verification only; never uses .env database or live test server."""
import os
from pathlib import Path
import secrets
import sys
import uuid

work = Path(__file__).resolve().parent
sys.path.insert(0, str(work.parent))
os.environ.update(DATABASE_URL='sqlite:///'+(work/('e2e-'+uuid.uuid4().hex+'.db')).as_posix(),
                  ENVIRONMENT='dev', JWT_SECRET=secrets.token_urlsafe(40),
                  PUBLIC_TEST_MODE='false', AUTO_CREATE_TABLES='true')
from app.database import Base, engine, SessionLocal
from app import main
from app.models import Player
from app.mmo_models import Avatar

Base.metadata.create_all(engine)
with SessionLocal() as db:
    db.add(Player(id='november-e2e', device_id='november-unity-e2e', display_name='NovemberCheck'))
    db.flush()
    avatar=Avatar(player_id='november-e2e', gold=1500)
    db.add(avatar)
    db.flush()
    avatar.inventory=avatar.inventory+[
        dict(id='e2e-helm', name='검증용 룬 투구', slot='helmet', power=24, rarity=2),
        dict(id='e2e-sword', name='검증용 룬 검', slot='weapon', power=12, rarity=2)]
    db.commit()
import uvicorn
uvicorn.run(main.app, host='127.0.0.1', port=58741, log_level='warning')

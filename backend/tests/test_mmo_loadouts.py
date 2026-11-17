import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.mmo_models import Avatar
from app.mmo_world import World
from app import mmo_routes
from app.online_routes import online_player
from tests.test_mmo_world import world


def test_loadouts(world, monkeypatch):
    w, _, factory = world
    assert len(w.profile('a')['loadouts']) == 3
    with factory() as db:
        a = db.get(Avatar, 'a')
        a.inventory = a.inventory + [dict(id='hat', slot='helmet', power=25, rarity=1, name='Helmet')]
        a.gold = 1000
        db.commit()
    w.enter('a', 'frontier', 0)
    w.actors['a']['hp'] = 12
    assert w.equip('a', 'hat', 1)['max_hp'] == 100
    p = w.loadout('a', 1)
    assert p['equipped_helmet'] == 'hat' and p['max_hp'] == 125
    assert w.actors['a']['hp'] == 12 and w.actors['a']['max_hp'] == 125
    assert World(factory).profile('a')['loadouts'] == p['loadouts']
    w.actors['a'].update(hp=0, revive=3)
    w.loadout('a', 0)
    assert w.actors['a']['hp'] == 0 and w.actors['a']['revive'] == 3
    assert w.upgrade('a', 'helmet')['helmet_rank'] == 1
    before = w.profile('a')
    for index in [-1, 3, True, '1']:
        with pytest.raises(HTTPException): w.loadout('a', index)
        with pytest.raises(HTTPException): w.equip('a', 'hat', index)
    assert w.profile('a') == before
    monkeypatch.setattr(mmo_routes, 'world', w)
    app = FastAPI()
    app.include_router(mmo_routes.router)
    app.dependency_overrides[online_player] = lambda: 'a'
    with TestClient(app) as client:
        assert client.post('/v1/mmo/loadout', json={'index': 1}).status_code == 200
        assert client.post('/v1/mmo/upgrade', json={'slot': 'helmet'}).status_code == 200
        for index in [-1, 3, True, '1']:
            assert client.post('/v1/mmo/loadout', json={'index': index}).status_code == 422
        assert client.post('/v1/mmo/equip', json={'item_id': 'foreign'}).status_code == 404


def test_legacy_selection_and_invalid_slot_rollback(world):
    w, _, factory = world
    with factory() as db:
        a = w.avatar(db, 'a')
        a.inventory = a.inventory + [dict(id='legacy', slot='armor', power=40, name='Legacy'),
                                     dict(id='bad', slot='gold', power=99, name='Invalid')]
        a.armor = 'legacy'
        a.loadouts = None
        db.commit()
    p = World(factory).profile('a')
    assert all(s['armor'] == 'legacy' for s in p['loadouts'])
    for action in [lambda: w.equip('a', 'bad'), lambda: w.upgrade('a', 'gold')]:
        with pytest.raises(HTTPException): action()
        assert w.profile('a') == p
    w.enter('a', 'frontier', 0)
    w.actors['a']['hp'] = 135
    assert w.equip('a', 'starter-armor')['max_hp'] == 100
    assert w.actors['a']['hp'] == 100
    assert World(factory).profile('a')['loadouts'][0]['armor'] == 'starter-armor'


def test_additive_schema_migration_preserves_old_avatar(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.orm import sessionmaker
    from app import mmo_schema
    from app.database import Base
    from app.models import Player
    engine = create_engine('sqlite:///' + str(tmp_path / 'legacy.db'))
    Base.metadata.create_all(engine, tables=[Player.__table__])
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE mmo_avatars (player_id VARCHAR PRIMARY KEY, level INTEGER, xp INTEGER, gold INTEGER, role INTEGER, hp FLOAT, weapon_rank INTEGER, armor_rank INTEGER, weapon VARCHAR, armor VARCHAR, kills INTEGER, quest_stage INTEGER, inventory JSON)'))
        connection.execute(text("INSERT INTO mmo_avatars VALUES ('a',1,0,12,0,72,0,0,'old-gun','old-armor',0,1,'[]')"))
    monkeypatch.setattr(mmo_schema, 'engine', engine)
    mmo_schema.main()
    mmo_schema.main()
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(Player(id='a', device_id='a', display_name='a'))
        db.commit()
    p = World(factory).profile('a')
    assert p['gold'] == 12 and p['active_loadout'] == 0
    assert p['loadouts'] == [dict(weapon='old-gun', armor='old-armor', helmet='')] * 3
    assert 'helmet_rank' in {c['name'] for c in inspect(engine).get_columns('mmo_avatars')}


def test_third_kill_rewards_owned_helmet(world):
    w, now, factory = world
    w.enter('a', 'frontier', 0)
    with factory() as db:
        a = db.get(Avatar, 'a')
        a.kills = 2
        db.commit()
    enemy = w.zones['frontier']['enemies'][0]
    enemy.update(x=400., y=300., hp=18.)
    w.input('a', dict(sequence=0, aim_x=500., aim_y=300., attack=True))
    now[0] += .1
    w.state('a')
    helmet = next(i for i in w.profile('a')['inventory'] if i['slot'] == 'helmet')
    assert w.equip('a', helmet['id'])['equipped_helmet'] == helmet['id']

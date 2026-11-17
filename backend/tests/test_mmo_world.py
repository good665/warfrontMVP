import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import Player
from app.mmo_world import World


@pytest.fixture
def world():
    engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all([Player(id=p, device_id=p, display_name=p) for p in ['a', 'b']])
        db.commit()
    now = [100.0]
    return World(factory, lambda: now[0]), now, factory


def test_shared_time_ttl_replay_and_reentry(world):
    w, now, _ = world
    w.enter('a', 'frontier', 0)
    assert len(w.enter('b', 'frontier', 0)['players']) == 2
    w.input('a', dict(sequence=1, move_x=1, move_y=1, aim_x=2000, aim_y=300, attack=True))
    for _ in range(50):
        w.state('a')
    assert w.state('a')['players'][0]['x'] == 300
    now[0] += 1
    snap = w.state('a')
    assert 300 < snap['players'][0]['x'] < 360
    x = snap['players'][0]['x']
    now[0] += 1
    assert w.state('a')['players'][0]['x'] == x
    w.actors['a']['hp'] = 11
    assert w.enter('a', 'minefield', 2)['players'][0]['hp'] == 11
    assert w.input('a', dict(sequence=1, move_x=-1))['last_sequence'] == 1


def test_rewards_persist_and_quest_claim_once(world):
    w, _, factory = world
    w.enter('a', 'frontier', 0)
    with factory() as db:
        avatar = w.avatar(db, 'a')
        w.reward(avatar, 200, 90)
        avatar.kills = 5
        db.commit()
    first = w.claim('a')
    with pytest.raises(Exception):
        w.claim('a')
    restored = World(factory).profile('a')
    assert restored['gold'] == first['gold']
    assert restored['level'] == 2
    assert restored['quest']['id'] == 'hunt-2'


def test_party_instances(world):
    w, _, _ = world
    a = w.enter('a', 'ruins', 0)
    b = w.enter('b', 'ruins', 0)
    assert a['instance_id'] != b['instance_id']
    code = w.party('a', 'create', '')['code']
    w.party('b', 'join', code)
    assert w.enter('a', 'ruins', 0)['instance_id'] == w.enter('b', 'ruins', 0)['instance_id']


def test_authoritative_kill_shared_snapshot_and_loot_once(world):
    w, now, factory = world
    w.enter('a', 'frontier', 0)
    w.enter('b', 'frontier', 0)
    enemy = w.zones['frontier']['enemies'][0]
    enemy.update(x=400., y=300., hp=18.)
    w.input('a', dict(sequence=0, aim_x=500., aim_y=300., attack=True))
    now[0] += .1
    snap = w.state('b')
    assert snap['enemies'][0]['hp'] == 0
    assert w.profile('a')['gold'] == 15
    assert w.profile('b')['gold'] == 0
    assert len(w.profile('a')['inventory']) == 3
    for _ in range(10):
        w.input('a', dict(sequence=0, attack=True))
    assert w.profile('a')['gold'] == 15
    assert World(factory).profile('a')['gold'] == 15


def test_hp_death_cooldown_and_equipment_ownership(world):
    w, now, factory = world
    w.enter('a', 'frontier', 0)
    w.input('a', dict(sequence=1, dodge=True, skill2=True))
    now[0] += .05
    w.state('a')
    cooldown = w.actors['a']['skill2_cooldown']
    w.actors['a']['hp'] = 17
    w.leave('a')
    snap = w.enter('a', 'ruins', 1)
    actor = next(p for p in snap['players'] if p['id'] == 'a')
    assert actor['hp'] == 17
    assert actor['skill2_cooldown'] == cooldown
    with pytest.raises(Exception): w.equip('a', 'foreign-item')
    with pytest.raises(Exception): w.upgrade('a', 'weapon')
    now[0] += .05
    w.state('a')
    with factory() as db:
        assert w.avatar(db, 'a').hp == 17


def test_simultaneous_claim_is_serialized(world):
    from concurrent.futures import ThreadPoolExecutor
    w, _, factory = world
    with factory() as db:
        a = w.avatar(db, 'a')
        a.kills = 5
        db.commit()
    def claim():
        try: return w.claim('a')['gold']
        except Exception: return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda _: claim(), range(2)))
    assert sorted(v for v in values if v is not None) == [75]


def test_routes_auth_and_validation(world, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.database import get_db
    from app import mmo_routes
    from app.security import create_access_token
    w, _, factory = world
    monkeypatch.setattr(mmo_routes, 'world', w)
    app = FastAPI()
    app.include_router(mmo_routes.router)
    def db_override():
        with factory() as db: yield db
    app.dependency_overrides[get_db] = db_override
    headers = {'Authorization': 'Bearer '+create_access_token('a')}
    with TestClient(app) as client:
        assert client.get('/v1/mmo/profile').status_code == 401
        assert client.get('/v1/mmo/state', headers=headers).status_code == 409
        assert client.post('/v1/mmo/enter', json={'zone':'frontier','role':0}, headers=headers).status_code == 200
        assert client.post('/v1/mmo/input', json={'sequence':0,'aim_x':'NaN'}, headers=headers).status_code == 422
        assert client.post('/v1/mmo/input', json={'sequence':0,'gold':900}, headers=headers).status_code == 422
        assert client.post('/v1/mmo/equip', json={'item_id':'stolen'}, headers=headers).status_code == 404


def test_cover_blocks_players_and_enemies(world):
    w, now, _ = world
    snap = w.enter('a', 'frontier', 0)
    assert len(snap['obstacles']) == 3
    actor = w.actors['a']
    actor.update(x=880., y=400.)
    w.input('a', dict(sequence=1,move_x=1,dodge=True))
    now[0] += .3
    assert w.state('a')['players'][0]['x'] < 900
    enemy = w.zones['frontier']['enemies'][0]
    enemy.update(x=880., y=400.)
    w.move(enemy, 20, 0)
    assert enemy['x'] == 880


def test_capacity_party_revoke_even_when_frontier_full(world):
    w, _, factory = world
    with factory() as db:
        db.add_all([Player(id=f'p{i}', device_id=f'p{i}', display_name=f'p{i}') for i in range(33)])
        db.commit()
    code = w.party('a', 'create', '')['code']
    w.party('b', 'join', code)
    for i in range(2): w.party(f'p{i}', 'join', code)
    with pytest.raises(Exception): w.party('p2', 'join', code)
    w.enter('a', 'ruins', 0)
    for i in range(32): w.enter(f'p{i}', 'frontier', 0)
    with pytest.raises(Exception): w.enter('p32', 'frontier', 0)
    assert w.party('a', 'leave', '')['code'] == ''
    assert w.actors['a']['key'] == ''
    with pytest.raises(Exception): w.state('a')


def test_dead_reentry_and_disconnected_slot_release(world):
    w, now, _ = world
    w.enter('a','frontier',0)
    w.hurt(w.actors['a'], 1000)
    w.leave('a')
    assert w.enter('a','ruins',2)['players'][0]['hp'] == 0
    now[0] += 31
    with pytest.raises(Exception): w.state('a')
    assert w.actors['a']['key'] == ''


def test_failed_commit_restores_simulation_and_reports_unready(world, monkeypatch):
    import asyncio
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session
    from app import main
    w, now, _ = world
    w.enter('a', 'frontier', 0)
    enemy = w.zones['frontier']['enemies'][0]
    enemy.update(x=400., y=300., hp=18.)
    w.input('a', dict(sequence=1, attack=True, aim_x=500, aim_y=300))
    original = Session.commit
    def fail(_): raise SQLAlchemyError('do not log connection secrets')
    monkeypatch.setattr(Session, 'commit', fail)
    now[0] += .05
    with pytest.raises(SQLAlchemyError): w.state('a')
    assert w.zones['frontier']['enemies'][0]['hp'] == 18
    monkeypatch.setattr(main, 'mmo_world', w)
    monkeypatch.setattr(main.rooms, 'last_loop_tick', __import__('time').monotonic())
    class Task:
        def done(self): return False
    monkeypatch.setattr(main.rooms,'task',Task())
    class DB:
        def execute(self,*args): pass
    with pytest.raises(Exception) as exc: main.readiness(DB())
    assert exc.value.status_code == 503
    assert exc.value.detail == 'mmo_loop_unavailable'
    monkeypatch.setattr(Session,'commit',original)
    now[0] += .05
    w.state('a')
    assert w.profile('a')['gold'] == 15


def nearby_enemy(w):
    w.enter('a', 'frontier', 0)
    enemies = w.zones['frontier']['enemies']
    for enemy in enemies[1:]:
        enemy.update(hp=0., respawn_left=100.)
    enemies[0].update(x=330., y=300.)
    return enemies[0]


def tick_for(w, seconds):
    for i in range(round(seconds/.05)):
        w.tick(.05, 100. + i*.05)


def test_enemy_strike_telegraphs_fixed_center_and_can_be_escaped(world):
    w, _, _ = world
    enemy = nearby_enemy(w)
    tick_for(w, .05)
    assert w.actors['a']['hp'] == 100
    assert enemy['windup_left'] == .7
    assert (enemy['attack_x'], enemy['attack_y']) == (300., 300.)
    original = (enemy['x'], enemy['y'])
    tick_for(w, .3)
    assert w.actors['a']['hp'] == 100
    w.actors['a'].update(x=500.)
    tick_for(w, .4)
    assert w.actors['a']['hp'] == 100
    assert (enemy['x'], enemy['y']) == original
    assert any(e['kind'] == 'enemy_attack' for e in w.zones['frontier']['effects'])


@pytest.mark.parametrize('defense', ['none', 'dodge', 'death'])
def test_enemy_windup_damage_dodge_and_death(world, defense):
    w, _, factory = world
    enemy = nearby_enemy(w)
    tick_for(w, .05)
    if defense == 'dodge':
        w.actors['a']['dodge_left'] = 2.
    elif defense == 'death':
        enemy.update(hp=1.)
        w.actors['a'].update(input=dict(attack=True, aim_x=330., aim_y=300.), expires=200.)
    tick_for(w, .7)
    expected = 92 if defense == 'none' else 100
    assert w.actors['a']['hp'] == expected
    with factory() as db:
        assert w.avatar(db, 'a').hp == expected
    if defense == 'death':
        assert enemy['windup_left'] == 0
    if defense == 'none':
        assert any(e['kind'] == 'player_damage' for e in w.zones['frontier']['effects'])


def test_varied_quests_persist_and_claim_once(world):
    from fastapi import HTTPException
    w, _, factory = world
    with factory() as db:
        av = w.avatar(db, 'a')
        av.kills = 5
        db.commit()
    assert w.claim('a')['quest']['id'] == 'hunt-2'
    for kind, event, zone, x, y in [
        ('hunt', 'raider', 'frontier', 0., 0.),
        ('elite', 'guard', 'minefield', 0., 0.),
        ('explore', 'explore', 'frontier', 1200., 1800.),
        ('boss', 'boss', 'ruins', 0., 0.),
    ]:
        w = World(factory)
        q = w.profile('a')['quest']
        assert q['kind'] == kind
        with pytest.raises(HTTPException):
            w.claim('a')
        with factory() as db:
            av = w.avatar(db, 'a')
            w.progress_quest(av, 'explore', 'ruins', 0., 0.)
            assert w.quest(av)['progress'] == 0
            for _ in range(q['target']):
                w.progress_quest(av, event, zone, x, y)
            db.commit()
        w = World(factory)
        assert w.profile('a')['quest']['ready']
        before = w.profile('a')['gold']
        result = w.claim('a')
        assert result['gold'] == before + q['reward_gold']
        with pytest.raises(HTTPException):
            w.claim('a')
    assert w.profile('a')['quest']['kind'] == 'hunt'


def test_legacy_later_stage_keeps_progress_until_claim(world):
    w, _, factory = world
    with factory() as db:
        av = w.avatar(db, 'a')
        av.quest_stage = 7
        av.kills = 35
        db.commit()
    restored = World(factory)
    q = restored.profile('a')['quest']
    assert q['id'] == 'hunt-7'
    assert q['progress'] == 35 and q['ready']
    assert restored.claim('a')['gold'] == 525


def test_server_movement_completes_exploration_and_kill_completes_elite(world):
    w, _, factory = world
    enemy = nearby_enemy(w)
    with factory() as db:
        av = w.avatar(db, 'a')
        av.quest_stage = 4
        av.quest_state = w.next_quest(4)
        db.commit()
    # Being in the right zone alone does not count.
    tick_for(w, .05)
    assert w.profile('a')['quest']['progress'] == 0
    w.actors['a'].update(x=1200., y=1800.)
    tick_for(w, .05)
    assert World(factory).profile('a')['quest']['ready']
    with factory() as db:
        av = w.avatar(db, 'a')
        av.quest_stage = 3
        av.quest_state = w.next_quest(3)
        db.commit()
    enemy.update(hp=1., x=1230., y=1800., kind='guard')
    w.actors['a'].update(input=dict(attack=True, aim_x=1230., aim_y=1800.), expires=200.)
    tick_for(w, .05)
    assert World(factory).profile('a')['quest']['progress'] == 1


def test_boss_windup_duration_radius_and_damage(world):
    w, _, _ = world
    w.enter('a', 'ruins', 0)
    enemy = w.zones['ruins:a']['enemies'][0]
    enemy.update(x=330., y=300.)
    tick_for(w, .05)
    assert enemy['windup_left'] == 1.
    assert enemy['attack_radius'] == 150.
    tick_for(w, .95)
    assert w.actors['a']['hp'] == 100
    tick_for(w, .05)
    assert w.actors['a']['hp'] == 80


def test_additive_quest_migration_is_repeatable_and_preserves_legacy(monkeypatch):
    from sqlalchemy import text, inspect
    from app import mmo_schema
    engine = create_engine('sqlite://', poolclass=StaticPool)
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE mmo_avatars (player_id TEXT PRIMARY KEY, kills INTEGER, quest_stage INTEGER)'))
        connection.execute(text("INSERT INTO mmo_avatars VALUES ('legacy', 35, 7)"))
    monkeypatch.setattr(mmo_schema, 'engine', engine)
    mmo_schema.main()
    mmo_schema.main()
    assert 'quest_state' in {c['name'] for c in inspect(engine).get_columns('mmo_avatars')}
    with engine.connect() as connection:
        row = connection.execute(text('SELECT kills, quest_stage, quest_state FROM mmo_avatars')).one()
        assert tuple(row) == (35, 7, None)

"""League HTTP tests use only the isolated test database and a scoped clock."""
from datetime import datetime, timedelta, timezone
import pytest
from tests import test_api as api
from tests.test_api import fresh_db


def post(path, headers=None, payload=None):
    return api.client.post('/v1/training' + path, headers=headers, json={} if payload is None else payload)


def test_training_routes_require_auth_and_reject_client_owned_fields():
    assert post('/runs').status_code == 401
    assert api.client.get('/v1/training/leaderboard').status_code == 401
    assert api.client.get('/v1/training/rewards').status_code == 401
    a, _ = api.login('alpha')
    for body in ({'score': 100}, {'seed': 1}, {'game': 'unknown'}, {'player_id': 'other'}):
        assert post('/runs', a, body).status_code == 422
    run = post('/runs', a)
    assert run.status_code == 201, run.text
    assert run.json()['rules_version'] == 2
    assert type(run.json()['seed']) is int and 1 <= run.json()['seed'] <= 2147483647


@pytest.fixture
def clock(monkeypatch):
    from app import training_service as service
    now = [datetime(2026, 11, 2, 0, tzinfo=timezone.utc)]
    monkeypatch.setattr(service, 'utcnow', lambda: now[0])
    return now


def start(headers):
    response = post('/runs', headers)
    assert response.status_code == 201, response.text
    return response.json()


def finish(headers, run, events=None, total_ticks=4500):
    return post('/runs/' + run['run_id'] + '/finish', headers,
                {'total_ticks': total_ticks, 'events': events or []})


def first_hit(seed):
    # Independent xorshift hand arithmetic for the first spawned target.
    def next_uint(value):
        value ^= (value << 13) & 0xffffffff
        value ^= value >> 17
        return (value ^ ((value << 5) & 0xffffffff)) & 0xffffffff
    x = next_uint(seed)
    y = next_uint(x)
    return [{'tick': 0, 'action': 0, 'x': 7000 + x % 86000, 'y': 6000 + y % 28000, 'index': 0}]


@pytest.mark.parametrize('minutes,expected', [(5, 10), (15, 9)])
def test_rewards_full_weekly_window_preserves_claimable_entries(clock, minutes, expected):
    from app.database import SessionLocal
    from app.training_models import TrainingBest
    headers, player = api.login('weekly_regular')
    monday = datetime(2026, 11, 1, 15, tzinfo=timezone.utc)  # Monday midnight KST
    for weeks in reversed(range(10)):
        clock[0] = monday - timedelta(weeks=weeks) + timedelta(minutes=1)
        run = start(headers)
        with SessionLocal() as db:
            db.add(TrainingBest(player_id=player['id'], season_id=run['season_id'], score=100,
                                verified_at=clock[0], run_id=run['run_id']))
            db.commit()
    clock[0] = monday + timedelta(minutes=minutes)
    response = api.client.get('/v1/training/rewards', headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()['items']
    assert len(items) == expected
    assert len({item['season_id'] for item in items}) == expected
    assert sum(item['state'] == 'final' and not item['claimed'] for item in items) >= 3
    # Optional export feeds the exact HTTP payload to the pure C# client validator.
    import os
    from pathlib import Path
    if os.environ.get('TRAINING_REWARDS_FIXTURE_DIR'):
        destination = Path(os.environ['TRAINING_REWARDS_FIXTURE_DIR'])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / f'rewards-{expected}.json').write_text(response.text, encoding='utf-8')


def test_owned_run_single_active_cancel_expiry_and_start_rate(clock):
    a, _ = api.login('alpha')
    b, _ = api.login('beta')
    run = start(a)
    assert start(b)['seed'] == run['seed']
    assert post('/runs', a).json()['run_id'] == run['run_id']
    assert finish(b, run).status_code == 404
    assert post('/runs/' + run['run_id'] + '/cancel', b).status_code == 404
    for _ in range(2):
        assert post('/runs/' + run['run_id'] + '/cancel', a).json()['status'] == 'cancelled'
    assert finish(a, run).status_code == 409
    for _ in range(19):
        run = start(a)
        post('/runs/' + run['run_id'] + '/cancel', a)
    assert post('/runs', a).status_code == 429
    clock[0] += timedelta(minutes=1)
    run = start(a)
    clock[0] += timedelta(minutes=10)
    assert finish(a, run).status_code == 410
    assert start(a)['run_id'] != run['run_id']


def test_finish_server_replay_elapsed_validation_and_lost_response_retry(clock):
    a, _ = api.login('alpha')
    run = start(a)
    events = first_hit(run['seed'])
    assert finish(a, run, events).status_code == 409  # cannot fast-forward wall time
    clock[0] += timedelta(seconds=45)
    for body in ({'score': 100, 'total_ticks': 4500, 'events': events},
                 {'total_ticks': True, 'events': []}, {'total_ticks': 4500.0, 'events': []},
                 {'total_ticks': 4501, 'events': []}, {'total_ticks': 4500, 'events': events * 4502}):
        assert post('/runs/' + run['run_id'] + '/finish', a, body).status_code == 422
    for invalid in ([dict(events[0], x=100001)], events * 2, [dict(events[0], action=2)]):
        assert finish(a, run, invalid).status_code == 422
    assert finish(a, run, events, total_ticks=100).status_code == 422
    result = finish(a, run, events)
    assert result.status_code == 200, result.text
    assert result.json()['score'] == 100 and result.json()['verified'] is True
    clock[0] += timedelta(days=35)
    from app.database import engine
    engine.dispose()  # new DB connections, no process-local idempotency
    retry = finish(a, run, events)
    assert retry.status_code == 200 and retry.json()['duplicate'] is True
    assert {k:v for k,v in result.json().items() if k not in ('duplicate', 'player')} == {k:v for k,v in retry.json().items() if k not in ('duplicate', 'player')}
    assert finish(a, run, []).status_code == 409
    assert post('/runs/' + run['run_id'] + '/cancel', a).json()['status'] == 'finished'


def test_positive_best_ties_zero_and_lower_scores(clock):
    accounts = [api.login(name)[0] for name in ('alpha', 'beta', 'zero')]
    for headers in accounts:
        run = start(headers)
        clock[0] += timedelta(seconds=45)
        assert finish(headers, run, first_hit(run['seed']) if headers != accounts[-1] else []).status_code == 200
    run = start(accounts[0])
    clock[0] += timedelta(seconds=45)
    assert finish(accounts[0], run).json()['score'] == 0
    board = api.client.get('/v1/training/leaderboard', headers=accounts[0]).json()
    assert board['participants'] == 2 and board['my_rank'] == 1 and board['my_score'] == 100
    assert [e['rank'] for e in board['entries']] == [1, 1]
    assert all(set(e) == {'rank', 'display_name', 'score', 'is_me'} for e in board['entries'])
    assert board['expected_reward'] == 30 and board['state'] == 'open'
    zero = api.client.get('/v1/training/leaderboard', headers=accounts[-1]).json()
    assert zero['my_rank'] == 0 and zero['my_score'] == 0


def test_monday_grace_final_claim_deadline_and_atomic_reward(clock):
    a, original = api.login('alpha')
    clock[0] = datetime(2026, 11, 8, 14, 59, 59, tzinfo=timezone.utc)
    run = start(a)
    assert run['season_id'] == '2026-W45'
    clock[0] += timedelta(seconds=45)
    assert finish(a, run, first_hit(run['seed'])).status_code == 200
    sid = run['season_id']
    assert start(a)['season_id'] == '2026-W46'
    assert post('/rewards/' + sid + '/claim', a).status_code == 409
    board = api.client.get('/v1/training/leaderboard?season_id=' + sid, headers=a).json()
    assert board['state'] == 'settling'
    clock[0] = datetime(2026, 11, 8, 15, 10, tzinfo=timezone.utc)
    result = post('/rewards/' + sid + '/claim', a)
    assert result.status_code == 200, result.text
    assert result.json()['reward'] == 30
    for field in ('stamina', 'rating', 'wins', 'losses'):
        assert result.json()['player'][field] == original[field]
    assert result.json()['player']['diamonds'] == original['diamonds'] + 30
    assert post('/rewards/' + sid + '/claim', a).json()['already_claimed'] is True
    assert post('/rewards/' + sid + '/claim', a).json()['reward'] == 0
    items = api.client.get('/v1/training/rewards', headers=a).json()['items']
    assert items[0]['claimed'] is True
    clock[0] += timedelta(days=28)
    assert post('/rewards/' + sid + '/claim', a).json()['already_claimed'] is True
    assert api.client.get('/v1/training/leaderboard?season_id=' + sid, headers=a).json()['state'] == 'expired'


def test_stream_body_limit_and_strict_event_integer_fields(clock):
    a, _ = api.login('alpha')
    run = start(a)
    clock[0] += timedelta(seconds=45)
    for field, value in [('tick', True), ('x', 0.5), ('y', '1'), ('index', -1), ('unexpected', 1)]:
        event = dict(first_hit(run['seed'])[0], **{field:value})
        assert finish(a, run, [event]).status_code == 422
    oversized = b'{"padding":"' + b'x' * (512 * 1024) + b'"}'
    response = api.client.post('/v1/training/runs', headers={**a, 'Content-Type':'application/json'},
                               content=(oversized[i:i+4096] for i in range(0, len(oversized), 4096)))
    assert response.status_code == 413


def test_lost_start_recovers_same_run_and_remaining_lifetime_including_old_season(clock):
    from app.database import SessionLocal, engine
    from app.training_models import TrainingRun
    from sqlalchemy import select, func
    a, _ = api.login('alpha')
    clock[0] = datetime(2026, 11, 8, 14, 59, 59, tzinfo=timezone.utc)
    issued = start(a)
    engine.dispose()
    clock[0] += timedelta(seconds=50)
    for _ in range(25):
        recovered = start(a)
        assert recovered['run_id'] == issued['run_id']
        assert recovered['season_id'] == '2026-W45' and recovered['game'] == 'range'
        assert recovered['expires_at'] == issued['expires_at']
        assert recovered['server_now'] == '2026-11-08T15:00:49+00:00'
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(TrainingRun)) == 1
    post('/runs/' + issued['run_id'] + '/cancel', a)
    assert start(a)['season_id'] == '2026-W46'


def test_finished_retry_keeps_verified_metrics_but_returns_latest_player(clock):
    from app.database import SessionLocal
    from app.models import Player
    a, player = api.login('alpha')
    run = start(a)
    clock[0] += timedelta(seconds=45)
    first = finish(a, run, first_hit(run['seed'])).json()
    # A reward or purchase after a lost finish response must not be overwritten.
    with SessionLocal() as db:
        db.get(Player, player['id']).diamonds += 50
        db.commit()
    clock[0] += timedelta(days=40)
    duplicate = finish(a, run, first_hit(run['seed'])).json()
    assert duplicate['score'] == first['score'] and duplicate['metrics'] == first['metrics']
    assert duplicate['duplicate'] is True
    assert duplicate['player']['diamonds'] == first['player']['diamonds'] + 50


def test_exact_run_expiry_settlement_and_unclaimed_deadline(clock):
    a, _ = api.login('alpha')
    b, _ = api.login('beta')
    clock[0] = datetime(2026, 11, 8, 14, 59, 59, tzinfo=timezone.utc)
    early = start(a)
    late = start(b)
    clock[0] += timedelta(seconds=45)
    assert finish(a, early, first_hit(early['seed'])).status_code == 200
    # The individual ten-minute lifetime is earlier than seasonal grace here.
    clock[0] = datetime(2026, 11, 8, 15, 9, 59, tzinfo=timezone.utc)
    assert finish(b, late, first_hit(late['seed'])).status_code == 410
    assert post('/rewards/2026-W45/claim', a).status_code == 409
    clock[0] = datetime(2026, 12, 6, 15, 10, tzinfo=timezone.utc)
    assert post('/rewards/2026-W45/claim', a).status_code == 410
    assert post('/rewards/2026-W45/claim', b).status_code == 410


def test_concurrent_claims_credit_once_and_survive_reconnect(clock):
    from concurrent.futures import ThreadPoolExecutor
    from app.database import SessionLocal, engine
    from app.models import Player
    from app.training_models import TrainingClaim
    from sqlalchemy import select
    a, original = api.login('alpha')
    run = start(a)
    clock[0] += timedelta(seconds=45)
    assert finish(a, run, first_hit(run['seed'])).status_code == 200
    clock[0] = datetime(2026, 11, 8, 15, 10, tzinfo=timezone.utc)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: post('/rewards/2026-W45/claim', a), range(8)))
    assert all(result.status_code == 200 for result in results)
    assert sorted(result.json()['reward'] for result in results) == [0] * 7 + [30]
    engine.dispose()
    with SessionLocal() as db:
        assert len(db.scalars(select(TrainingClaim)).all()) == 1
        assert db.get(Player, original['id']).diamonds == original['diamonds'] + 30
    assert post('/rewards/2026-W45/claim', a).json()['reward'] == 0


def test_top50_shared_ranks_and_reward_tiers_include_my_rank_outside_page(clock):
    from app.database import SessionLocal
    from app.models import Player
    from app.training_models import TrainingBest, TrainingRun
    a, original = api.login('alpha')
    run = start(a)
    # Ranking is tested with persisted server-verified rows, independent of replay mechanics.
    with SessionLocal() as db:
        for i in range(55):
            player = Player(device_id='leader-' + str(i), display_name='leader-' + str(i))
            db.add(player)
            db.flush()
            row = TrainingRun(player_id=player.id, season_id=run['season_id'], status='finished',
                              starts_at=clock[0], expires_at=clock[0] + timedelta(minutes=10))
            db.add(row)
            db.flush()
            score = 1000 if i < 2 else 1000 - i
            db.add(TrainingBest(player_id=player.id, season_id=run['season_id'], score=score, verified_at=clock[0], run_id=row.id))
        db.add(TrainingBest(player_id=original['id'], season_id=run['season_id'], score=1, verified_at=clock[0], run_id=run['run_id']))
        db.commit()
    board = api.client.get('/v1/training/leaderboard', headers=a).json()
    assert len(board['entries']) == 50 and board['participants'] == 56
    assert [row['rank'] for row in board['entries'][:4]] == [1, 1, 3, 4]
    assert board['my_rank'] == 56 and board['my_score'] == 1 and board['expected_reward'] == 3
    clock[0] = datetime(2026, 11, 8, 15, 10, tzinfo=timezone.utc)
    assert post('/rewards/2026-W45/claim', a).json()['reward'] == 3


def test_canonical_telemetry_is_opt_in_and_deduplicated(clock):
    from app.database import SessionLocal
    from app.experience_models import ExperienceEvent
    from sqlalchemy import select
    a, _ = api.login('alpha')
    api.client.post('/v1/experience', headers=a, json={'action':'consent', 'analytics_consent':True})
    run = start(a)
    clock[0] += timedelta(seconds=45)
    for _ in range(2):
        assert finish(a, run).status_code == 200
    with SessionLocal() as db:
        rows = db.scalars(select(ExperienceEvent).where(ExperienceEvent.run_id == run['run_id'])).all()
        assert {(row.kind, row.source, row.mode) for row in rows} == {('match_start','server','range'), ('match_complete','server','range')}
        assert len(rows) == 2


@pytest.mark.parametrize('operation', ['finish', 'claim'])
def test_deadline_is_checked_after_waiting_for_database_lock(clock, monkeypatch, operation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from fastapi import HTTPException
    from sqlalchemy import text
    from app.database import SessionLocal
    from app import training_service as service
    a, player = api.login('alpha')
    run = start(a)
    if operation == 'claim':
        clock[0] += timedelta(seconds=45)
        assert finish(a, run, first_hit(run['seed'])).status_code == 200
        deadline = datetime(2026, 12, 6, 15, 10, tzinfo=timezone.utc)
    else:
        deadline = clock[0] + timedelta(minutes=10)
    clock[0] = deadline - timedelta(seconds=1)
    attempting_lock = Event()
    original_begin = service.begin_write

    def observed_begin(db):
        attempting_lock.set()
        original_begin(db)

    monkeypatch.setattr(service, 'begin_write', observed_begin)

    def request_waiting():
        with SessionLocal() as db:
            try:
                if operation == 'claim':
                    return service.claim_reward(db, player['id'], run['season_id'])
                return service.finish_run(db, player['id'], run['run_id'], {'total_ticks':4500, 'events':first_hit(run['seed'])})
            except HTTPException as exc:
                return exc.status_code, exc.detail

    with SessionLocal() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        blocker.execute(text('BEGIN IMMEDIATE'))
        future = pool.submit(request_waiting)
        assert attempting_lock.wait(2)
        clock[0] = deadline
        blocker.commit()
        assert future.result(timeout=5) == (410, 'reward_expired' if operation == 'claim' else 'run_expired')


def test_inflight_finish_is_visible_to_settlement_claim(clock, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from app.database import SessionLocal
    from app import training_service as service
    a, player = api.login('alpha')
    clock[0] = datetime(2026, 11, 8, 14, 59, 59, tzinfo=timezone.utc)
    run = start(a)
    clock[0] = datetime(2026, 11, 8, 15, 9, 58, tzinfo=timezone.utc)
    replay_entered, release_replay, claim_waiting = Event(), Event(), Event()
    original_replay, original_begin = service.replay, service.begin_write

    def paused_replay(*args):
        replay_entered.set()
        assert release_replay.wait(3)
        return original_replay(*args)

    def observed_begin(db):
        if replay_entered.is_set():
            claim_waiting.set()
        original_begin(db)

    monkeypatch.setattr(service, 'replay', paused_replay)
    monkeypatch.setattr(service, 'begin_write', observed_begin)

    def complete():
        with SessionLocal() as db:
            return service.finish_run(db, player['id'], run['run_id'], {'total_ticks':4500, 'events':first_hit(run['seed'])})

    def claim():
        with SessionLocal() as db:
            return service.claim_reward(db, player['id'], run['season_id'])

    with ThreadPoolExecutor(max_workers=2) as pool:
        finishing = pool.submit(complete)
        assert replay_entered.wait(2)
        clock[0] = datetime(2026, 11, 8, 15, 10, tzinfo=timezone.utc)
        claiming = pool.submit(claim)
        assert claim_waiting.wait(2)
        release_replay.set()
        assert finishing.result(timeout=5)['score'] == 100
        assert claiming.result(timeout=5)['reward'] == 30


def test_claim_credit_and_claim_marker_rollback_together(clock, monkeypatch):
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import Player
    from app.training_models import TrainingClaim
    from app import training_service as service
    a, player = api.login('alpha')
    run = start(a)
    clock[0] += timedelta(seconds=45)
    finish(a, run, first_hit(run['seed']))
    clock[0] = datetime(2026, 11, 8, 15, 10, tzinfo=timezone.utc)
    with SessionLocal() as db:
        def disconnected():
            raise RuntimeError('simulated transaction failure before commit')
        monkeypatch.setattr(db, 'commit', disconnected)
        with pytest.raises(RuntimeError):
            service.claim_reward(db, player['id'], run['season_id'])
    with SessionLocal() as db:
        assert db.get(Player, player['id']).diamonds == player['diamonds']
        assert db.scalar(select(TrainingClaim)) is None
    assert post('/rewards/' + run['season_id'] + '/claim', a).json()['reward'] == 30


def test_reward_tiers_are_shared_rank_server_owned_and_account_scoped(clock):
    from app.database import SessionLocal
    from app.models import Player
    from app.training_models import TrainingBest, TrainingRun
    from app.security import create_access_token
    a, _ = api.login('alpha')
    run = start(a)
    headers = []
    with SessionLocal() as db:
        for i, score in enumerate([100, 100, 90, 80, 70, 60, 50, 40, 30, 20, 10]):
            player = Player(device_id='tier-' + str(i), display_name='tier-' + str(i))
            db.add(player)
            db.flush()
            row = TrainingRun(player_id=player.id, season_id=run['season_id'], status='finished', starts_at=clock[0], expires_at=clock[0]+timedelta(minutes=10))
            db.add(row)
            db.flush()
            db.add(TrainingBest(player_id=player.id, season_id=run['season_id'], score=score, verified_at=clock[0], run_id=row.id))
            headers.append({'Authorization':'Bearer ' + create_access_token(player.id)})
        db.commit()
    clock[0] = datetime(2026, 11, 8, 15, 10, tzinfo=timezone.utc)
    for i, reward in [(0,30), (1,30), (2,20), (3,10), (9,10), (10,3)]:
        assert post('/rewards/' + run['season_id'] + '/claim', headers[i], {'reward':999}).status_code == 422
        result = post('/rewards/' + run['season_id'] + '/claim', headers[i])
        assert result.status_code == 200 and result.json()['reward'] == reward
    assert post('/rewards/' + run['season_id'] + '/claim', a).json()['detail'] == 'no_eligible_score'


@pytest.mark.parametrize('legacy_live', [False, True])
def test_schema_apply_on_populated_database_backup_restore_with_auto_create_off(tmp_path, legacy_live):
    import os
    import json
    import sqlite3
    import subprocess
    import sys
    from app.database import Base
    from app.models import Player, Match
    from sqlalchemy import create_engine
    from app.experience_models import ExperienceEvent
    from tools.backup_sqlite import copy_database
    source = tmp_path / 'populated.db'
    engine = create_engine('sqlite:///' + source.as_posix())
    Base.metadata.create_all(engine, tables=[Player.__table__, Match.__table__])
    with engine.begin() as db:
        db.execute(Player.__table__.insert().values(id='legacy', device_id='legacy', display_name='legacy', diamonds=77))
        db.execute(Match.__table__.insert().values(id='match', player_id='legacy', mode='pve'))
        # Simulate Stage1 schema before durable cohort-anchor fields were added.
        db.exec_driver_sql('CREATE TABLE experience_states (player_id VARCHAR(36) PRIMARY KEY, version INTEGER NOT NULL, tutorial_step INTEGER NOT NULL, tutorial_status VARCHAR(16) NOT NULL, analytics_consent BOOLEAN NOT NULL)')
        db.exec_driver_sql("INSERT INTO experience_states VALUES ('legacy',1,2,'in_progress',1)")
        ExperienceEvent.__table__.create(db)
        if legacy_live:
            db.execute(ExperienceEvent.__table__.insert().values(player_id='legacy', event_id='historical', kind='session_start', mode='lobby', source='client'))
        db.execute(ExperienceEvent.__table__.insert().values(player_id='legacy', event_id='delayed', kind='tutorial_skip', mode='tutorial', source='client', queued_ms=500))
    engine.dispose()
    env = dict(os.environ, AUTO_CREATE_TABLES='false')
    command = [sys.executable, '-m', 'tools.apply_growth_schema', '--database-url', 'sqlite:///' + source.as_posix(), '--backup-dir', str(tmp_path / 'backups')]
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['status'] == 'ok'
    # Idempotent rerun must preserve both legacy data and current schema.
    again = subprocess.run(command, capture_output=True, text=True, env=env)
    assert again.returncode == 0, again.stderr
    with sqlite3.connect(source) as db:
        assert db.execute('SELECT diamonds FROM players').fetchone() == (77,)
        assert db.execute('SELECT id FROM matches').fetchone() == ('match',)
        assert db.execute('SELECT tutorial_step, first_session_at, first_guide_exit_at, first_session_censored, first_guide_exit_censored FROM experience_states').fetchone() == (2, None, None, int(legacy_live), 0)
        assert {'training_seasons','training_runs','training_bests','training_claims'} <= {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    restored = copy_database(report['backup'], tmp_path / 'restored.db')
    with sqlite3.connect(restored) as db:
        assert db.execute('SELECT diamonds FROM players').fetchone() == (77,)
        assert db.execute('SELECT id FROM matches').fetchone() == ('match',)
        assert db.execute("SELECT name FROM sqlite_master WHERE name='training_runs'").fetchone() is None


def test_finished_result_and_claim_survive_new_python_process(clock):
    import json
    import os
    import subprocess
    import sys
    from app.database import engine
    a, player = api.login('alpha')
    run = start(a)
    clock[0] += timedelta(seconds=45)
    first = finish(a, run, first_hit(run['seed'])).json()
    clock[0] = datetime(2026, 11, 8, 15, 10, tzinfo=timezone.utc)
    assert post('/rewards/' + run['season_id'] + '/claim', a).json()['reward'] == 30
    script = '''
import json, sys
from datetime import datetime, timezone
from app.database import SessionLocal
from app import training_service as service
data = json.load(sys.stdin)
service.utcnow = lambda: datetime(2027, 1, 1, tzinfo=timezone.utc)
with SessionLocal() as db:
    finished = service.finish_run(db, data['pid'], data['run_id'], data['payload'])
with SessionLocal() as db:
    claim = service.claim_reward(db, data['pid'], data['sid'])
print(json.dumps(dict(finished=finished, claim=claim)))
'''
    body = dict(pid=player['id'], run_id=run['run_id'], sid=run['season_id'], payload=dict(total_ticks=4500, events=first_hit(run['seed'])))
    result = subprocess.run([sys.executable, '-c', script], input=json.dumps(body), capture_output=True, text=True,
                            env=dict(os.environ, DATABASE_URL=str(engine.url), AUTO_CREATE_TABLES='false'))
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data['finished']['metrics'] == first['metrics'] and data['finished']['duplicate'] is True
    assert data['finished']['player']['diamonds'] == 30
    assert data['claim']['reward'] == 0 and data['claim']['already_claimed'] is True


def test_deleted_account_token_cannot_create_runs_or_read_league(clock):
    from app.security import create_access_token
    headers = {'Authorization': 'Bearer ' + create_access_token('deleted-account')}
    assert post('/runs', headers).status_code == 401
    assert api.client.get('/v1/training/leaderboard', headers=headers).status_code == 401
    assert api.client.get('/v1/training/rewards', headers=headers).status_code == 401


def test_finish_refuses_rules_version_it_cannot_replay(clock):
    from app.database import SessionLocal
    from app.training_models import TrainingSeason, TrainingBest
    from sqlalchemy import select
    a, _ = api.login('alpha')
    run = start(a)
    clock[0] += timedelta(seconds=45)
    with SessionLocal() as db:
        db.get(TrainingSeason, run['season_id']).rules_version = 999
        db.commit()
    result = finish(a, run, first_hit(run['seed']))
    assert result.status_code == 409 and result.json()['detail'] == 'unsupported_rules_version'
    with SessionLocal() as db:
        assert db.scalar(select(TrainingBest)) is None


@pytest.mark.parametrize('first_request', ['upgrade', 'claim'])
def test_upgrade_and_weekly_claim_preserve_both_currency_changes(clock, monkeypatch, first_request):
    """Exercise the actual public mutations with both possible account-read orders."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from app import main, training_service as service
    from app.database import SessionLocal
    from app.models import Player
    from app.training_models import TrainingClaim
    from sqlalchemy import select
    headers, player = api.login('alpha')
    run = start(headers)
    clock[0] += timedelta(seconds=45)
    assert finish(headers, run, first_hit(run['seed'])).status_code == 200
    clock[0] = datetime(2026, 11, 8, 15, 10, tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.get(Player, player['id']).diamonds = 1000
        db.commit()

    upgrade_loaded, claim_loaded, claim_entered = Event(), Event(), Event()
    claim_completed, release_first = Event(), Event()
    original_load = main._load_player
    original_lock = service.lock_season_account
    original_begin = service.begin_write

    def observed_load(db, pid, lock):
        result = original_load(db, pid, lock)
        if lock:
            upgrade_loaded.set()
            if first_request == 'upgrade':
                assert release_first.wait(5)
        return result

    def observed_season_lock(*args, **kwargs):
        result = original_lock(*args, **kwargs)
        claim_loaded.set()
        if first_request == 'claim':
            assert release_first.wait(5)
        return result

    def observed_begin(db):
        claim_entered.set()
        return original_begin(db)

    monkeypatch.setattr(main, '_load_player', observed_load)
    monkeypatch.setattr(service, 'lock_season_account', observed_season_lock)
    monkeypatch.setattr(service, 'begin_write', observed_begin)

    def request_upgrade():
        return api.client.post('/v1/me/upgrade', headers=headers)

    def request_claim():
        try:
            return post('/rewards/' + run['season_id'] + '/claim', headers)
        finally:
            claim_completed.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        try:
            if first_request == 'upgrade':
                upgrade = pool.submit(request_upgrade)
                assert upgrade_loaded.wait(2)
                claim = pool.submit(request_claim)
                assert claim_entered.wait(2)
                # The unfixed path lets claim commit before the paused upgrade
                # saves its stale 1000-10 value. The fixed path blocks claim.
                claim_completed.wait(1)
            else:
                claim = pool.submit(request_claim)
                assert claim_loaded.wait(2)
                upgrade = pool.submit(request_upgrade)
                # The unfixed path reads 1000 before the held claim commits.
                # The fixed path cannot read Player until the claim releases.
                upgrade_loaded.wait(1)
        finally:
            release_first.set()
        upgraded = upgrade.result(timeout=5)
        claimed = claim.result(timeout=5)
    assert upgraded.status_code == 200, upgraded.text
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()['reward'] == 30 and claimed.json()['already_claimed'] is False
    with SessionLocal() as db:
        state = db.get(Player, player['id'])
        assert state.diamonds == 1020  # 1000 + weekly30 - upgrade10, never990.
        assert state.power == 1
        assert len(db.scalars(select(TrainingClaim)).all()) == 1
    duplicate = post('/rewards/' + run['season_id'] + '/claim', headers).json()
    assert duplicate['reward'] == 0 and duplicate['already_claimed'] is True
    assert duplicate['player']['diamonds'] == 1020

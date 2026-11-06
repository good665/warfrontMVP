"""Three concurrent weekly leagues, preserving the legacy league identity."""
from datetime import datetime, timedelta, timezone

import pytest

from tests import test_api as api
from tests.test_api import fresh_db
from tests.test_training_league import clock, first_hit, finish, post


def start_game(headers, game):
    response = post('/runs', headers, {'game': game})
    assert response.status_code == 201, response.text
    return response.json()


def test_every_week_exposes_all_three_games():
    from app.training_seasons import season_at
    for week in range(6):
        season = season_at(datetime(2026, 11, 2, tzinfo=timezone.utc) + timedelta(weeks=week))
        assert season['active_games'] == ['range', 'drone', 'cipher']


def test_game_selection_preserves_legacy_identity_and_isolates_boards(clock):
    headers, player = api.login('three_games')
    from app.database import SessionLocal
    from app.training_models import TrainingBest
    runs = []
    for i, game in enumerate(('range', 'drone', 'cipher')):
        run = start_game(headers, game)
        assert run['game'] == game
        runs.append(run)
        with SessionLocal() as db:
            db.add(TrainingBest(player_id=player['id'], season_id=run['season_id'], score=100+i,
                                verified_at=clock[0], run_id=run['run_id']))
            db.commit()
        assert post('/runs/' + run['run_id'] + '/cancel', headers).status_code == 200
    assert runs[0]['season_id'] == '2026-W45'
    assert len({r['season_id'] for r in runs}) == 3
    assert len({r['seed'] for r in runs}) == 3
    for i, game in enumerate(('range', 'drone', 'cipher')):
        response = api.client.get('/v1/training/leaderboard', headers=headers, params={'game':game})
        assert response.status_code == 200, response.text
        board = response.json()
        assert board['game'] == game
        assert board['my_score'] == 100+i
        assert board['participants'] == 1 and board['my_rank'] == 1
    clock[0] = datetime(2026, 11, 8, 15, 10, tzinfo=timezone.utc)
    rewards = api.client.get('/v1/training/rewards', headers=headers).json()['items']
    assert {item['game'] for item in rewards} == {'range', 'drone', 'cipher'}
    for run in runs:
        path = '/rewards/' + run['season_id'] + '/claim'
        result = post(path, headers)
        assert result.status_code == 200, result.text
        assert result.json()['reward'] == 30
        assert post(path, headers).json()['reward'] == 0
    assert api.client.get('/v1/me', headers=headers).json()['diamonds'] == player['diamonds'] + 90


def test_explicit_game_keeps_original_season_seed_and_claim_identity(clock):
    headers, _ = api.login('legacy_game')
    legacy = post('/runs', headers).json()
    assert start_game(headers, 'range') == legacy
    clock[0] += timedelta(seconds=45)
    assert finish(headers, legacy, first_hit(legacy['seed'])).status_code == 200
    alias = api.client.get('/v1/training/leaderboard', headers=headers,
                           params={'season_id':'2026-W45-range'}).json()
    assert alias['season_id'] == legacy['season_id']
    assert alias['my_score'] == 100
    clock[0] = datetime(2026, 11, 8, 15, 10, tzinfo=timezone.utc)
    assert post('/rewards/2026-W45-range/claim', headers).json()['reward'] == 30
    assert post('/rewards/2026-W45/claim', headers).json()['reward'] == 0


@pytest.mark.parametrize('game', ['invalid', '', 1, None])
def test_unknown_games_are_rejected(clock, game):
    headers, _ = api.login('invalid_game')
    assert post('/runs', headers, {'game':game}).status_code == 422


def test_different_game_recovers_existing_run_until_cancelled(clock):
    headers, _ = api.login('switch_game')
    first = start_game(headers, 'drone')
    recovered = start_game(headers, 'cipher')
    assert recovered['run_id'] == first['run_id'] and recovered['game'] == 'drone'
    assert post('/runs/' + first['run_id'] + '/cancel', headers).status_code == 200
    assert start_game(headers, 'cipher')['game'] == 'cipher'


@pytest.mark.parametrize('game,score', [('range',100), ('drone',250), ('cipher',200)])
def test_selected_game_replay_is_verified_and_ranked_in_its_own_league(clock, game, score):
    headers, _ = api.login('replay_' + game)
    run = start_game(headers, game)
    if game == 'range':
        events = first_hit(run['seed'])
    elif game == 'drone':
        # Fly above both walls, collect the initial supply, and return safely.
        waypoints = [(0,10000,7000), (50,88000,7000), (310,88000,20000),
                     (360,88000,7000), (410,10000,7000), (670,10000,20000)]
        events = [dict(tick=t,action=1,x=x,y=y,index=0) for t,x,y in waypoints]
    else:
        # Initial two xorshift signals; no client-provided score or seed.
        seed = run['seed']
        events = []
        for tick in (190,191):
            seed ^= (seed << 13) & 0xffffffff
            seed ^= seed >> 17
            seed = (seed ^ ((seed << 5) & 0xffffffff)) & 0xffffffff
            events.append(dict(tick=tick,action=2,x=0,y=0,index=seed%4))
    wrong_action = dict(events[0], action=(events[0]['action']+1)%3)
    clock[0] += timedelta(seconds=45)
    assert finish(headers, run, [wrong_action]).status_code == 422
    response = finish(headers, run, events)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['verified'] and result['game'] == game and result['score'] == score
    board = api.client.get('/v1/training/leaderboard', headers=headers, params={'game':game}).json()
    assert board['my_score'] == score and board['my_rank'] == 1
    other = next(g for g in ('range','drone','cipher') if g != game)
    board = api.client.get('/v1/training/leaderboard', headers=headers, params={'game':other}).json()
    assert board['my_score'] == 0 and board['participants'] == 0


def test_three_games_full_reward_window(clock):
    from app.database import SessionLocal
    from app.training_models import TrainingBest
    headers, player = api.login('thirty_rewards')
    monday = datetime(2026,11,1,15,tzinfo=timezone.utc)
    for weeks in reversed(range(10)):
        clock[0] = monday - timedelta(weeks=weeks) + timedelta(minutes=1)
        for game in ('range','drone','cipher'):
            run = start_game(headers,game)
            with SessionLocal() as db:
                db.add(TrainingBest(player_id=player['id'], season_id=run['season_id'],score=100,
                                    verified_at=clock[0],run_id=run['run_id']))
                db.commit()
            assert post('/runs/'+run['run_id']+'/cancel',headers).status_code == 200
    clock[0] = monday + timedelta(minutes=5)
    items = api.client.get('/v1/training/rewards',headers=headers).json()['items']
    assert len(items) == 30 and len({i['season_id'] for i in items}) == 30
    assert sum(i['state']=='final' for i in items) == 12

"""Weekly league transaction boundaries and server-owned settlement."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from fastapi import HTTPException
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from .game_rules import utcnow
from .models import Player
from .training_models import TrainingBest, TrainingClaim, TrainingRun, TrainingSeason
from .training_seasons import KST, ROTATION, season_at
from .training_replay import replay
from .experience import safe_record_event


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def iso(value):
    return aware(value).isoformat()


def begin_write(db):
    # Acquire SQLite's write reservation before ANY reads in this transaction.
    # PostgreSQL serializes all mutations in season -> account order below.
    if db.bind.dialect.name == 'sqlite':
        raw = db.connection().connection.driver_connection
        if not raw.in_transaction:
            db.execute(text('BEGIN IMMEDIATE'))


def season_values(season_id, game=None):
    match = re.fullmatch(r'(\d{4}-W\d{2})(?:-(range|drone|cipher))?', season_id)
    if not match or (game is not None and game not in ROTATION):
        raise HTTPException(422, 'invalid_season')
    week, suffix = match.groups()
    if suffix and game is not None and suffix != game:
        raise HTTPException(422, 'game_season_mismatch')
    try:
        start = datetime.fromisocalendar(int(week[:4]), int(week[6:]), 1).replace(tzinfo=KST)
        calendar = season_at(start)
        end = start + timedelta(weeks=1)
        settles = end + timedelta(minutes=10)
        deadline = settles + timedelta(days=28)
    except (ValueError, OverflowError):
        raise HTTPException(422, 'invalid_season')
    selected = suffix or game or calendar['active_game']
    # The old weekly game retains its exact ID, seed, bests and claim marker.
    # Its suffixed alias always resolves here, preventing duplicate rewards.
    sid = week if selected == calendar['active_game'] else week + '-' + selected
    seed = int.from_bytes(hashlib.sha256(('training:v2:' + sid).encode()).digest()[:4], 'big') & 0x7fffffff
    return dict(id=sid, game=selected, rules_version=2, seed=seed or 1,
                starts_at=aware(start), ends_at=aware(end), settles_at=aware(settles), claim_until=aware(deadline))


def lock_season_account(db, season_id, pid, *, create=False):
    if create:
        values = season_values(season_id)
        insert = sqlite_insert if db.bind.dialect.name == 'sqlite' else pg_insert
        db.execute(insert(TrainingSeason).values(**values).on_conflict_do_nothing(index_elements=['id']))
    season = db.scalar(select(TrainingSeason).where(TrainingSeason.id == season_id).with_for_update().execution_options(populate_existing=True))
    if season is None:
        raise HTTPException(404, 'season_not_found')
    player = db.scalar(select(Player).where(Player.id == pid).with_for_update().execution_options(populate_existing=True))
    if player is None:
        raise HTTPException(401, 'unauthorized')
    return season, player


def player_dto(player):
    # Reuse the established DTO without triggering stamina recovery or spending.
    from .main import serialize
    return serialize(player).model_dump(mode='json')


def run_dto(run, season, now):
    return dict(run_id=run.id, season_id=season.id, game=season.game, rules_version=season.rules_version,
                seed=season.seed, starts_at=iso(run.starts_at), expires_at=iso(run.expires_at), server_now=iso(now))


def start_run(db, pid, game=None):
    # A lock wait may cross Monday midnight. Re-select the week after locking.
    while True:
        begin_write(db)
        week = season_at(utcnow())['season_id']
        sid = season_values(week, game)['id']
        season, _ = lock_season_account(db, sid, pid, create=True)
        now = aware(utcnow())
        if season_at(now)['season_id'] == week:
            break
        db.rollback()
    active = db.scalar(select(TrainingRun).where(TrainingRun.active_player_id == pid))
    if active is not None:
        if aware(active.expires_at) > now:
            # Recover a lost start response without extending its lifetime or
            # adding a rate-limit entry. Season rules are immutable, so reading
            # an older active run's season requires no extra lock after account.
            active_season = db.get(TrainingSeason, active.season_id)
            result = run_dto(active, active_season, now)
            db.commit()
            return result
        active.status = 'expired'
        active.active_player_id = None
        db.flush()
    recent = db.scalar(select(func.count()).select_from(TrainingRun).where(
        TrainingRun.player_id == pid, TrainingRun.starts_at > now - timedelta(minutes=1)))
    if recent >= 20:
        raise HTTPException(429, 'training_start_rate_limited')
    run = TrainingRun(player_id=pid, active_player_id=pid, season_id=sid, starts_at=now,
                      expires_at=min(now + timedelta(minutes=10), aware(season.settles_at)))
    db.add(run)
    db.flush()
    result = run_dto(run, season, now)
    db.commit()
    safe_record_event(pid, 'match_start', result['run_id'], result['game'])
    return result


def owned_run(db, pid, run_id):
    run = db.get(TrainingRun, run_id)
    if run is None or run.player_id != pid:
        raise HTTPException(404, 'run_not_found')
    return run


def finish_run(db, pid, run_id, payload):
    begin_write(db)
    run = owned_run(db, pid, run_id)
    season, player = lock_season_account(db, run.season_id, pid)
    db.refresh(run)
    now = aware(utcnow())  # MUST be sampled after both locks, not before waiting.
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    if run.status == 'finished':
        if fingerprint != run.submission_hash:
            raise HTTPException(409, 'submission_conflict')
        # Only verification is immutable. Refresh the profile so a recovered
        # response cannot restore currency from before a later reward/purchase.
        result = dict(run.result, duplicate=True, player=player_dto(player))
        db.commit()
        return result
    if run.status != 'active':
        raise HTTPException(409, 'run_not_active')
    if now >= aware(run.expires_at) or now >= aware(season.settles_at):
        raise HTTPException(410, 'run_expired')
    if season.rules_version != 2:
        raise HTTPException(409, 'unsupported_rules_version')
    try:
        metrics = replay(season.game, season.seed, payload['total_ticks'], payload['events'])
    except ValueError:
        raise HTTPException(422, 'invalid_replay')
    if (now - aware(run.starts_at)).total_seconds() * 100 < metrics['played_ticks']:
        raise HTTPException(409, 'run_too_fast')
    score = metrics['score']
    best = db.get(TrainingBest, (pid, season.id))
    if score > 0 and (best is None or score > best.score):
        if best is None:
            db.add(TrainingBest(player_id=pid, season_id=season.id, score=score, verified_at=now, run_id=run.id))
        else:
            best.score, best.verified_at, best.run_id = score, now, run.id
    result = dict(run_id=run.id, season_id=season.id, game=season.game, rules_version=season.rules_version,
                  score=score, metrics=metrics, verified=True, duplicate=False, player=player_dto(player))
    run.status, run.active_player_id = 'finished', None
    run.finished_at, run.submission_hash, run.result = now, fingerprint, result
    db.commit()
    safe_record_event(pid, 'match_complete', run_id, result['game'], duration_ms=metrics['played_ticks'] * 10)
    return result


def cancel_run(db, pid, run_id):
    begin_write(db)
    run = owned_run(db, pid, run_id)
    lock_season_account(db, run.season_id, pid)
    db.refresh(run)
    if run.status == 'active':
        run.status, run.active_player_id = 'cancelled', None
    result = dict(run_id=run.id, status=run.status)
    db.commit()
    return result


def season_state(season, now):
    if now < aware(season.ends_at):
        return 'open'
    if now < aware(season.settles_at):
        return 'settling'
    return 'final' if now < aware(season.claim_until) else 'expired'


def reward_for(rank):
    return 0 if rank <= 0 else 30 if rank == 1 else 20 if rank <= 3 else 10 if rank <= 10 else 3


def my_standing(db, sid, pid):
    best = db.get(TrainingBest, (pid, sid))
    if best is None or best.score <= 0:
        return 0, 0
    higher = db.scalar(select(func.count()).select_from(TrainingBest).where(
        TrainingBest.season_id == sid, TrainingBest.score > best.score))
    return int(higher) + 1, best.score


def leaderboard(db, pid, season_id=None, game=None):
    begin_write(db)
    current = season_at(utcnow())['season_id']
    sid = season_values(season_id or current, game)['id']
    season, _ = lock_season_account(db, sid, pid, create=sid[:8] == current)
    now = aware(utcnow())
    rows = db.execute(select(TrainingBest, Player.display_name).join(Player, Player.id == TrainingBest.player_id).where(
        TrainingBest.season_id == sid, TrainingBest.score > 0).order_by(
        TrainingBest.score.desc(), TrainingBest.verified_at, TrainingBest.player_id).limit(50)).all()
    entries, previous, rank = [], None, 0
    for position, (best, name) in enumerate(rows, 1):
        if previous != best.score:
            rank = position
        entries.append(dict(rank=rank, display_name=name, score=best.score, is_me=best.player_id == pid))
        previous = best.score
    my_rank, my_score = my_standing(db, sid, pid)
    participants = db.scalar(select(func.count()).select_from(TrainingBest).where(TrainingBest.season_id == sid, TrainingBest.score > 0))
    result = dict(season_id=sid, game=season.game, rules_version=season.rules_version,
                  starts_at=iso(season.starts_at), ends_at=iso(season.ends_at), settles_at=iso(season.settles_at),
                  claim_until=iso(season.claim_until), state=season_state(season, now), entries=entries,
                  my_rank=my_rank, my_score=my_score, participants=participants, expected_reward=reward_for(my_rank))
    db.commit()
    return result


def rewards(db, pid):
    # Read-only previews need no account lock; final mutations use claim_reward.
    if db.get(Player, pid) is None:
        raise HTTPException(401, 'unauthorized')
    now = aware(utcnow())
    seasons = db.scalars(select(TrainingSeason).join(TrainingBest, TrainingBest.season_id == TrainingSeason.id).where(
        TrainingBest.player_id == pid, TrainingBest.score > 0,
        TrainingSeason.claim_until > now - timedelta(weeks=4)).order_by(TrainingSeason.starts_at.desc())).all()
    items = []
    for season in seasons:
        rank, score = my_standing(db, season.id, pid)
        claim = db.scalar(select(TrainingClaim).where(TrainingClaim.player_id == pid, TrainingClaim.season_id == season.id))
        items.append(dict(season_id=season.id, game=season.game, rank=rank, score=score,
                          reward=claim.reward if claim else reward_for(rank), state=season_state(season, now),
                          settles_at=iso(season.settles_at), claim_until=iso(season.claim_until), claimed=claim is not None))
    return dict(items=items)


def claim_reward(db, pid, season_id):
    season_id = season_values(season_id)['id']
    begin_write(db)
    season, player = lock_season_account(db, season_id, pid)
    now = aware(utcnow())
    claim = db.scalar(select(TrainingClaim).where(TrainingClaim.player_id == pid, TrainingClaim.season_id == season_id))
    if claim is not None:
        result = dict(reward=0, already_claimed=True, player=player_dto(player))
        db.commit()
        return result
    if now < aware(season.settles_at):
        raise HTTPException(409, 'season_not_settled')
    if now >= aware(season.claim_until):
        raise HTTPException(410, 'reward_expired')
    rank, score = my_standing(db, season_id, pid)
    reward = reward_for(rank)
    if reward == 0:
        raise HTTPException(409, 'no_eligible_score')
    db.add(TrainingClaim(player_id=pid, season_id=season_id, rank=rank, score=score, reward=reward, claimed_at=now))
    db.flush()  # SQL unique constraint and atomic credit share this transaction.
    db.execute(update(Player).where(Player.id == pid).values(diamonds=Player.diamonds + reward))
    db.refresh(player)
    result = dict(reward=reward, already_claimed=False, player=player_dto(player))
    db.commit()
    return result

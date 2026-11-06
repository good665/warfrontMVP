"""Optional telemetry must run after canonical commits and never affect gameplay."""
import logging
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from .experience_models import ExperienceEvent, ExperienceState
from .models import Player
from .database import SessionLocal
from .game_rules import utcnow

logger = logging.getLogger(__name__)
CLIENT_KINDS = {"session_start", "tutorial_start", "tutorial_step", "tutorial_complete", "tutorial_skip", "mode_select", "practice_start", "practice_complete", "practice_retry", "connection_failure", "connection_recovered"}
SERVER_KINDS = {"match_start", "match_complete", "matching_wait", "matching_cancel", "matching_success"}
MODES = {"lobby", "tutorial", "training", "practice", "pvp", "pve", "rush", "bomb", "arena1", "arena3", "online1", "online3", "target", "range", "drone", "cipher"}


def lock_account(db, player_id):
    # SQLite ignores FOR UPDATE. Acquire its write reservation before reading
    # consent/state so ingestion cannot overtake a concurrent revocation.
    if db.bind.dialect.name == "sqlite":
        raw = db.connection().connection.driver_connection
        if not raw.in_transaction:
            db.execute(text("BEGIN IMMEDIATE"))
    else:
        db.scalar(select(Player.id).where(Player.id == player_id).with_for_update())


def preserve_legacy_censoring(db, player_id=None):
    """Persist per-anchor unknown provenance before ingesting or deleting raw history.

    Deferred/client-clock history never establishes a live observation. Markers
    are permanent: later live events cannot turn an unknown first date into now.
    """
    for timestamp_name, flag_name, kinds in (
        ("first_session_at", "first_session_censored", ("session_start",)),
        ("first_guide_exit_at", "first_guide_exit_censored", ("tutorial_complete", "tutorial_skip")),
    ):
        prior_live = select(ExperienceEvent.id).where(
            ExperienceEvent.player_id == ExperienceState.player_id,
            ExperienceEvent.source == "client", ExperienceEvent.queued_ms == 0,
            ExperienceEvent.kind.in_(kinds)).exists()
        statement = update(ExperienceState).where(
            getattr(ExperienceState, timestamp_name).is_(None),
            getattr(ExperienceState, flag_name).is_(False), prior_live)
        if player_id is not None:
            statement = statement.where(ExperienceState.player_id == player_id)
        db.execute(statement.values(**{flag_name: True}).execution_options(synchronize_session="fetch"))


def record_event(db, player_id, kind, run_id, mode, *, event_id=None, source="server", app_session="", step=0, duration_ms=0, queued_ms=0, success=True):
    if source not in ("server", "client") or kind not in (SERVER_KINDS if source == "server" else CLIENT_KINDS) or mode not in MODES:
        raise ValueError("invalid_event")
    lock_account(db, player_id)
    state = db.get(ExperienceState, player_id)
    if state is None or not state.analytics_consent:
        return False
    event_id = event_id or f"server:{kind}:{run_id}"
    if db.scalar(select(ExperienceEvent.id).where(ExperienceEvent.player_id == player_id, ExperienceEvent.event_id == event_id)):
        return True
    received_at = utcnow()
    if source == "client" and queued_ms == 0 and kind in ("session_start", "tutorial_complete", "tutorial_skip"):
        preserve_legacy_censoring(db, player_id)
        # See markers persisted by concurrent cleanup before choosing an anchor.
        db.refresh(state, with_for_update=True)
        if kind == "session_start" and state.first_session_at is None and not state.first_session_censored:
            state.first_session_at = received_at
        if kind in ("tutorial_complete", "tutorial_skip") and state.first_guide_exit_at is None and not state.first_guide_exit_censored:
            state.first_guide_exit_at = received_at
    try:
        with db.begin_nested():
            db.add(ExperienceEvent(player_id=player_id, event_id=event_id, source=source, kind=kind, run_id=run_id, mode=mode, app_session=app_session, step=step, duration_ms=duration_ms, queued_ms=queued_ms, success=success, received_at=received_at))
            db.flush()
    except IntegrityError:
        # A concurrent retry may have inserted the same ID.
        if not db.scalar(select(ExperienceEvent.id).where(ExperienceEvent.player_id == player_id, ExperienceEvent.event_id == event_id)):
            raise
    return True


def safe_record_event(player_id, kind, run_id, mode, **fields):
    try:
        with SessionLocal() as db:
            record_event(db, player_id, kind, run_id, mode, **fields)
            db.commit()
    except Exception:
        logger.warning("Optional experience telemetry unavailable", exc_info=True)

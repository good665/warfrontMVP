"""Read-only cohort report. Raw retention cleanup requires --prune explicitly."""
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import delete, select
from app.database import SessionLocal
from app.models import Player
from app.experience_models import ExperienceEvent, ExperienceState
from app.game_rules import as_utc
from app.experience import preserve_legacy_censoring

KST = timezone(timedelta(hours=9))
COMPLETION_MINUTES = 30
FIRST_GAME_MINUTES = 30
RETRY_MINUTES = 10
RUN_KINDS = {"server": ("match_start", "match_complete"),
             "client": ("practice_start", "practice_complete")}


def ratio(eligible, converted, label="converted"):
    return {"eligible": eligible, label: converted,
            "rate": converted / eligible if eligible else None}


def date_key(at):
    return as_utc(at).astimezone(KST).date().isoformat()


def distinct_runs(events, source, kind):
    """A fresh event ID cannot turn one run into multiple observations."""
    runs = {}
    for event in events:
        if event.source == source and event.kind == kind and event.mode != "tutorial":
            runs.setdefault((event.player_id, event.mode, event.run_id), event)
    return list(runs.values())


def report(db, days=7, now=None):
    now = as_utc(now or datetime.now(timezone.utc))
    since = now - timedelta(days=days)
    states = db.scalars(select(ExperienceState).where(
        ExperienceState.analytics_consent.is_(True))).all()
    rows = db.scalars(select(ExperienceEvent).join(
        ExperienceState, ExperienceEvent.player_id == ExperienceState.player_id).where(
            ExperienceState.analytics_consent.is_(True),
            ExperienceEvent.received_at <= now).order_by(
                ExperienceEvent.received_at, ExperienceEvent.id)).all()
    timely = [r for r in rows if r.source == "server" or r.queued_ms == 0]
    visible = [r for r in timely if as_utc(r.received_at) >= since]
    by_player = defaultdict(list)
    for row in timely:
        by_player[row.player_id].append(row)

    # Each bucket stores denominators and numerators at the anchor day.
    def bucket():
        return {"first": [0, 0], "retry": [0, 0], "d1": [0, 0],
                "first_sources": {s: [0, 0] for s in RUN_KINDS},
                "retry_sources": {s: [0, 0] for s in RUN_KINDS}}

    totals = bucket()
    daily_cohorts = defaultdict(bucket)
    today = now.astimezone(KST).date()
    left_censored = {"session": 0, "guide_exit": 0}
    for state in states:
        events = by_player[state.player_id]
        # Only persisted first observations establish cohorts. Surviving raw
        # records without metadata are left-censored, never presumed new users.
        if state.first_guide_exit_at is not None and not state.first_guide_exit_censored:
            anchor = as_utc(state.first_guide_exit_at)
            if since <= anchor <= now - timedelta(minutes=FIRST_GAME_MINUTES):
                day = daily_cohorts[date_key(anchor)]
                hits = {}
                for source, (_, finish_kind) in RUN_KINDS.items():
                    hits[source] = any(
                        anchor <= as_utc(r.received_at) <= anchor + timedelta(minutes=FIRST_GAME_MINUTES)
                        for r in distinct_runs(events, source, finish_kind))
                    for target in (totals, day):
                        target["first_sources"][source][0] += 1
                        target["first_sources"][source][1] += hits[source]
                for target in (totals, day):
                    target["first"][0] += 1
                    target["first"][1] += any(hits.values())
        elif state.first_guide_exit_censored or any(r.kind in ("tutorial_complete", "tutorial_skip") and r.source == "client" for r in events):
            left_censored["guide_exit"] += 1

        for source, (start_kind, finish_kind) in RUN_KINDS.items():
            for finish in distinct_runs(events, source, finish_kind):
                end = as_utc(finish.received_at)
                if since <= end <= now - timedelta(minutes=RETRY_MINUTES):
                    did_retry = any(
                        r.kind == start_kind and r.source == source and r.mode == finish.mode
                        and r.run_id != finish.run_id
                        and end <= as_utc(r.received_at) <= end + timedelta(minutes=RETRY_MINUTES)
                        for r in events)
                    for target in (totals, daily_cohorts[date_key(end)]):
                        target["retry"][0] += 1
                        target["retry"][1] += did_retry
                        target["retry_sources"][source][0] += 1
                        target["retry_sources"][source][1] += did_retry
        sessions = [r for r in events if r.kind == "session_start" and r.source == "client"]
        if state.first_session_at is not None and not state.first_session_censored:
            first = as_utc(state.first_session_at)
            first_date = first.astimezone(KST).date()
            if first >= since and first_date + timedelta(days=1) < today:
                returned = any(as_utc(r.received_at).astimezone(KST).date()
                               == first_date + timedelta(days=1) for r in sessions)
                for target in (totals, daily_cohorts[date_key(first)]):
                    target["d1"][0] += 1
                    target["d1"][1] += returned
        elif state.first_session_censored or sessions:
            left_censored["session"] += 1

    def cohort_dto(values):
        return {"first_game_completion": ratio(*values["first"]),
                "first_game_by_source": {s: ratio(*v) for s, v in values["first_sources"].items()},
                "retry": ratio(*values["retry"]),
                "retry_by_source": {s: ratio(*v) for s, v in values["retry_sources"].items()},
                "d1": ratio(*values["d1"], label="returned")}

    modes = {}
    for mode in sorted({r.mode for r in visible if r.mode != "tutorial"}):
        mode_rows = [r for r in visible if r.mode == mode]
        waits = [r.duration_ms for r in mode_rows if r.source == "server"
                 and r.kind in ("matching_success", "matching_cancel")]
        queue_starts = sum(r.kind == "matching_wait" and r.source == "server" for r in mode_rows)
        cancels = sum(r.kind == "matching_cancel" and r.source == "server" for r in mode_rows)
        completion_rates = {}
        for source, (start_kind, finish_kind) in RUN_KINDS.items():
            starts = [r for r in distinct_runs(timely, source, start_kind)
                      if r.mode == mode and since <= as_utc(r.received_at)
                      <= now - timedelta(minutes=COMPLETION_MINUTES)]
            finishes = distinct_runs(timely, source, finish_kind)
            completed = sum(any(
                finish.player_id == start.player_id and finish.mode == mode
                and finish.run_id == start.run_id
                and as_utc(start.received_at) <= as_utc(finish.received_at)
                <= as_utc(start.received_at) + timedelta(minutes=COMPLETION_MINUTES)
                for finish in finishes) for start in starts)
            completion_rates[source] = ratio(len(starts), completed)
        modes[mode] = {
            "server_starts": sum(r.kind == "match_start" and r.source == "server" for r in mode_rows),
            "server_completions": sum(r.kind == "match_complete" and r.source == "server" for r in mode_rows),
            "client_practice_starts": sum(r.kind == "practice_start" and r.source == "client" for r in mode_rows),
            "client_practice_completions": sum(r.kind == "practice_complete" and r.source == "client" for r in mode_rows),
            "completion_by_source": completion_rates,
            "matching_wait_median_ms": statistics.median(waits) if waits else None,
            "matching_cancel_rate": cancels / queue_starts if queue_starts else None}

    tutorial_starters = {r.player_id for r in visible if r.source == "client" and r.kind == "tutorial_start"}
    tutorial_rates = {}
    for name, kind in (("skip", "tutorial_skip"), ("complete", "tutorial_complete")):
        accounts = {r.player_id for r in visible if r.source == "client" and r.kind == kind}
        tutorial_rates[name] = ratio(len(tutorial_starters), len(tutorial_starters & accounts))
    daily_events = defaultdict(lambda: defaultdict(int))
    for row in visible:
        daily_events[date_key(row.received_at)][f"{row.source}:{row.kind}"] += 1
    return {
        "days": days,
        "windows": {"first_game_minutes": FIRST_GAME_MINUTES,
                    "retry_minutes": RETRY_MINUTES,
                    "mode_completion_minutes": COMPLETION_MINUTES,
                    "maturity": "Full observation window must elapse; endpoints inclusive.",
                    "mode_completion_anchor": "Start received within reporting interval; same account/source/mode/run finish within 30 minutes.",
                    "daily_attribution": "First game: first guide exit; retry: completion; D1: first session; KST anchor date."},
        "observed_consented_accounts": len({r.player_id for r in visible}),
        "tutorial": {kind: sum(r.kind == kind and r.source == "client" for r in visible)
                     for kind in ("tutorial_start", "tutorial_complete", "tutorial_skip")},
        "tutorial_account_rates": tutorial_rates,
        **cohort_dto(totals),
        "daily_cohorts_kst": {day: cohort_dto(values) for day, values in sorted(daily_cohorts.items())},
        "left_censored_accounts": left_censored,
        "delayed_client_events": sum(r.source == "client" and r.queued_ms > 0
                                     and as_utc(r.received_at) >= since for r in rows),
        "modes": modes,
        "daily_kst": dict(daily_events),
        "limitations": ["Opt-in observed sample only; missing events and offline use are not measured.",
                        "Client practice is self-reported; server match completion is canonical settlement, not proof of every input.",
                        "Delayed client events excluded from conversion, cohorts and daily attribution.",
                        "Durable first-observation timestamps and legacy-censor markers preserve cohort identity after raw retention; missing anchors are left-censored."]}


def prune_raw_events(db, now=None):
    """Preserve legacy unknown provenance, then delete raw records older than30days."""
    now = as_utc(now or datetime.now(timezone.utc))
    preserve_legacy_censoring(db)
    return db.execute(delete(ExperienceEvent).where(
        ExperienceEvent.received_at < now - timedelta(days=30))).rowcount


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--prune", action="store_true", help="Delete raw records older than 30 days")
    args = parser.parse_args()
    if not 1 <= args.days <= 30:
        parser.error("--days must be 1..30")
    with SessionLocal() as db:
        if args.prune:
            prune_raw_events(db)
            db.commit()
        print(json.dumps(report(db, args.days), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from tests import test_api as api
from tests.test_api import fresh_db
from app.database import SessionLocal


def request(method, path="", headers=None, **body):
    return getattr(api.client, method)("/v1/experience" + path, headers=headers, **({"json": body} if body else {}))


def test_progress_is_authenticated_sequential_persistent_and_account_scoped():
    assert request("get").status_code == 401
    a, _ = api.login("alpha")
    b, _ = api.login("beta")
    assert request("get", headers=a).json() == dict(version=1, tutorial_step=0, tutorial_status="new", analytics_consent=False)
    assert request("post", headers=a, action="progress", tutorial_step=2).status_code == 409
    assert request("post", headers=a, action="start").json()["tutorial_status"] == "in_progress"
    assert request("post", headers=a, action="progress", tutorial_step=1).json()["tutorial_step"] == 1
    assert request("post", headers=a, action="skip").json()["tutorial_status"] == "skipped"
    assert request("get", headers=b).json()["tutorial_step"] == 0
    request("post", headers=a, action="progress", tutorial_step=2)
    assert request("post", headers=a, action="progress", tutorial_step=3).json()["tutorial_status"] == "completed"
    for body in [dict(action="skip"), dict(action="start"), dict(action="progress", tutorial_step=1)]:
        assert request("post", headers=a, **body).json()["tutorial_status"] == "completed"


def event(**changes):
    return dict(event_id=str(uuid.uuid4()), app_session=str(uuid.uuid4()), run_id=str(uuid.uuid4()), kind="session_start", mode="lobby", step=0, duration_ms=0, queued_ms=0, success=True, **changes)


def test_consent_dedup_validation_and_revocation():
    from app.experience_models import ExperienceEvent
    from sqlalchemy import select
    a, player = api.login("alpha")
    b, _ = api.login("beta")
    e = event()
    assert request("post", "/events", a, events=[e]).json() == {"accepted": [], "consent": False}
    request("post", headers=a, action="consent", analytics_consent=True)
    for _ in range(2):
        assert request("post", "/events", a, events=[e]).json() == {"accepted": [e["event_id"]], "consent": True}
    assert request("post", "/events", b, events=[e]).json()["accepted"] == []
    with SessionLocal() as db:
        rows = db.scalars(select(ExperienceEvent)).all()
        assert len(rows) == 1 and rows[0].player_id == player["id"] and rows[0].source == "client"
    for field, value in [("kind", "match_complete"), ("mode", "secret"), ("queued_ms", 604800001), ("duration_ms", -1), ("step", 4), ("event_id", "x"), ("player_id", "other"), ("source", "server")]:
        assert request("post", "/events", a, events=[dict(e, **{field:value})]).status_code == 422
    assert request("post", "/events", a, events=[event() for _ in range(51)]).status_code == 422
    request("post", headers=a, action="consent", analytics_consent=False)
    assert request("post", "/events", a, events=[event()]).json()["accepted"] == []


def test_canonical_match_hooks_and_optional_failure(monkeypatch):
    from app.experience_models import ExperienceEvent
    from sqlalchemy import select
    a, _ = api.login("alpha")
    request("post", headers=a, action="consent", analytics_consent=True)
    run = api.client.post("/v1/matches", headers=a, json={"mode":"pve"}).json()["match_id"]
    api.age_match(run, 60)
    assert api.client.post(f"/v1/matches/{run}/finish", headers=a, json={"won":True}).status_code == 200
    with SessionLocal() as db:
        rows = db.scalars(select(ExperienceEvent).where(ExperienceEvent.run_id == run)).all()
        assert {r.kind for r in rows} == {"match_start", "match_complete"}
        assert all(r.source == "server" for r in rows)
    import app.experience as experience
    monkeypatch.setattr(experience, "record_event", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("telemetry unavailable")))
    assert api.client.post("/v1/matches", headers=a, json={"mode":"pve"}).status_code == 201


def test_metrics_mature_windows_delayed_client_and_kst_d1():
    from tools.player_metrics import report
    from app.experience_models import ExperienceEvent, ExperienceState
    a, p = api.login("alpha")
    now = datetime(2026, 11, 2, 16, 0, tzinfo=timezone.utc)  # Nov3 01 KST
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"], analytics_consent=True,first_session_at=now-timedelta(minutes=3000),first_guide_exit_at=now-timedelta(minutes=60)))
        def add(kind, minutes, run="one", mode="pve", source="server", queued=0):
            db.add(ExperienceEvent(player_id=p["id"], event_id=str(uuid.uuid4()), kind=kind, run_id=run, mode=mode, source=source, queued_ms=queued, received_at=now-timedelta(minutes=minutes)))
        add("session_start", 3000, source="client")  # Oct31/Nov1 KST
        add("session_start", 1560, source="client")  # Nov2 KST, D1
        add("tutorial_complete", 60, source="client")
        add("match_start", 50)
        add("match_complete", 45)
        add("match_start", 40, run="two")
        add("match_complete", 5, run="two")  # immature retry
        add("tutorial_complete", 10, run="delayed", source="client", queued=1000)
        db.commit()
        result = report(db, days=7, now=now)
        assert result["first_game_completion"] == {"eligible":1,"converted":1,"rate":1.0}
        assert result["retry"] == {"eligible":1,"converted":1,"rate":1.0}
        assert result["d1"] == {"eligible":1,"returned":1,"rate":1.0}
        assert result["delayed_client_events"] == 1
        assert result["modes"]["pve"]["server_completions"] == 2


def test_online_matching_hooks_and_cancellation():
    from app.experience_models import ExperienceEvent
    from sqlalchemy import select
    a, _ = api.login("alpha")
    b, _ = api.login("beta")
    for headers in (a,b):
        request("post", headers=headers, action="consent", analytics_consent=True)
    first = api.client.post("/v1/rooms/quick-match", headers=a, json={"role":0,"team_size":1}).json()
    api.client.post(f"/v1/rooms/{first['code']}/leave", headers=a, json={"waiting_only":True})
    api.client.post("/v1/rooms/quick-match", headers=a, json={"role":0,"team_size":1})
    api.client.post("/v1/rooms/quick-match", headers=b, json={"role":0,"team_size":1})
    with SessionLocal() as db:
        kinds = [r.kind for r in db.scalars(select(ExperienceEvent)).all()]
        assert kinds.count("matching_wait") == 3
        assert kinds.count("matching_cancel") == 1
        assert kinds.count("matching_success") == 2
        assert kinds.count("match_start") == 2

def test_metrics_excludes_immature_and_delayed_anchors_and_missing_consent():
    from tools.player_metrics import report
    from app.experience_models import ExperienceEvent, ExperienceState
    now = datetime(2026, 11, 2, 16, 0, tzinfo=timezone.utc)
    with SessionLocal() as db:
        for name, minutes, queued, consent in [("young",29,0,True),("delayed",60,1,True),("revoked",60,0,False)]:
            _, player = api.login(name)
            db.add(ExperienceState(player_id=player["id"],analytics_consent=consent))
            db.add(ExperienceEvent(player_id=player["id"],event_id=str(uuid.uuid4()),kind="tutorial_skip",run_id="r",mode="tutorial",source="client",queued_ms=queued,received_at=now-timedelta(minutes=minutes)))
        db.commit()
        output = report(db,now=now)
        assert output["first_game_completion"] == {"eligible":0,"converted":0,"rate":None}
        assert output["observed_consented_accounts"] == 1
        assert output["delayed_client_events"] == 1


def test_metrics_reports_practice_and_server_retry_separately():
    from tools.player_metrics import report
    from app.experience_models import ExperienceEvent, ExperienceState
    _, p = api.login("alpha")
    now = datetime(2026,11,2,16,0,tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"],analytics_consent=True))
        for kind, source, minutes, run in [("practice_complete","client",20,"one"),("match_start","server",19,"two")]:
            db.add(ExperienceEvent(player_id=p["id"],event_id=str(uuid.uuid4()),kind=kind,source=source,mode="range",received_at=now-timedelta(minutes=minutes),run_id=run))
        db.commit()
        output=report(db,now=now)
        assert output["retry_by_source"]["client"] == {"eligible":1,"converted":0,"rate":0.0}
        assert output["retry_by_source"]["server"] == {"eligible":0,"converted":0,"rate":None}

def test_report_cli_is_read_only_unless_prune_explicitly_requested():
    import os
    import subprocess
    import sys
    from pathlib import Path
    from sqlalchemy import select, func
    from app.experience_models import ExperienceState, ExperienceEvent
    _, p = api.login("alpha")
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"],analytics_consent=True))
        db.add(ExperienceEvent(player_id=p["id"],event_id=str(uuid.uuid4()),source="client",kind="session_start",received_at=datetime.now(timezone.utc)-timedelta(days=31)))
        db.commit()
    script = str(Path(__file__).resolve().parents[1]/"tools"/"player_metrics.py")
    from app.database import engine
    child_env = dict(os.environ, DATABASE_URL=str(engine.url))
    run = subprocess.run([sys.executable,script,"--days","7"],capture_output=True,text=True,env=child_env)
    assert run.returncode == 0, run.stderr
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ExperienceEvent)) == 1
    run = subprocess.run([sys.executable,script,"--prune"],capture_output=True,text=True,env=child_env)
    assert run.returncode == 0, run.stderr
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ExperienceEvent)) == 0


def test_simultaneous_tutorial_completion_and_replay_cannot_regress():
    from concurrent.futures import ThreadPoolExecutor
    a,_ = api.login("alpha")
    request("post",headers=a,action="progress",tutorial_step=1)
    request("post",headers=a,action="progress",tutorial_step=2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(request,"post",headers=a,**body) for body in [dict(action="progress",tutorial_step=3),dict(action="skip")]]
        assert all(f.result().status_code == 200 for f in futures)
    assert request("get",headers=a).json()["tutorial_status"] == "completed"

def test_concurrent_first_get_creates_one_state_and_consent_isolated():
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import select, func
    from app.experience_models import ExperienceState
    a,_=api.login("alpha")
    with ThreadPoolExecutor(max_workers=6) as pool:
        replies=list(pool.map(lambda _: request("get",headers=a),range(6)))
    assert all(r.status_code == 200 for r in replies)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ExperienceState)) == 1

def test_first_game_source_split_and_tutorial_unique_account_ratios():
    from tools.player_metrics import report
    from app.experience_models import ExperienceState,ExperienceEvent
    now=datetime(2026,11,2,16,0,tzinfo=timezone.utc)
    _,p=api.login("alpha")
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"],analytics_consent=True,first_guide_exit_at=now-timedelta(minutes=60)))
        for kind,minutes,mode,run in [("tutorial_start",70,"tutorial","guide"),("tutorial_skip",60,"tutorial","guide"),("tutorial_start",55,"tutorial","replay"),("practice_complete",50,"range","one")]:
            db.add(ExperienceEvent(player_id=p["id"],event_id=str(uuid.uuid4()),source="client",kind=kind,mode=mode,run_id=run,received_at=now-timedelta(minutes=minutes)))
        db.commit()
        out=report(db,now=now)
        assert out["first_game_completion"] == {"eligible":1,"converted":1,"rate":1.0}
        assert out["first_game_by_source"]["client"] == {"eligible":1,"converted":1,"rate":1.0}
        assert out["first_game_by_source"]["server"] == {"eligible":1,"converted":0,"rate":0.0}
        assert out["tutorial_account_rates"]["skip"] == {"eligible":1,"converted":1,"rate":1.0}
        assert out["tutorial_account_rates"]["complete"] == {"eligible":1,"converted":0,"rate":0.0}

def test_mode_completion_rates_link_runs_sources_and_mature_start_windows():
    from tools.player_metrics import report
    from app.experience_models import ExperienceState, ExperienceEvent
    _,p=api.login("alpha")
    now=datetime(2026,11,2,16,0,tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"],analytics_consent=True))
        # Starts at the window edge count; orphan finishes, wrong source/mode,
        # and immature starts cannot inflate completed runs.
        entries=[("practice_start","client",50,"ok","range"),
                 ("practice_complete","client",40,"ok","range"),
                 ("practice_start","client",45,"missing","range"),
                 ("practice_complete","client",35,"orphan","range"),
                 ("practice_start","client",5,"young","range"),
                 ("match_start","server",50,"server","range"),
                 ("practice_complete","client",40,"server","range"),
                 ("match_complete","server",40,"server","drone"),
                 ("practice_start","client",50,"tutorial","tutorial"),
                 ("practice_complete","client",40,"tutorial","tutorial")]
        for kind,source,minutes,run,mode in entries:
            db.add(ExperienceEvent(player_id=p["id"],event_id=str(uuid.uuid4()),kind=kind,source=source,mode=mode,run_id=run,received_at=now-timedelta(minutes=minutes)))
        db.commit()
        out=report(db,now=now)
        assert out["modes"]["range"]["completion_by_source"]["client"] == {"eligible":2,"converted":1,"rate":0.5}
        assert out["modes"]["range"]["completion_by_source"]["server"] == {"eligible":1,"converted":0,"rate":0.0}
        assert out["modes"]["range"]["client_practice_starts"] == 3
        assert "tutorial" not in out["modes"]
        assert out["windows"]["mode_completion_minutes"] == 30


def test_daily_cohort_conversions_stay_on_kst_anchor_day_across_midnight():
    from tools.player_metrics import report
    from app.experience_models import ExperienceState, ExperienceEvent
    _,p=api.login("alpha")
    now=datetime(2026,11,3,16,0,tzinfo=timezone.utc) # Nov4 01 KST
    first=datetime(2026,11,1,14,55,tzinfo=timezone.utc) # Nov1 23:55 KST
    guide=datetime(2026,11,2,14,55,tzinfo=timezone.utc) # Nov2 23:55 KST
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"],analytics_consent=True,first_session_at=first,first_guide_exit_at=guide))
        for kind,source,at,run in [("session_start","client",first,"session1"),("session_start","client",guide,"session2"),("tutorial_skip","client",guide,"guide"),("match_start","server",guide+timedelta(minutes=1),"game1"),("match_complete","server",guide+timedelta(minutes=10),"game1"),("match_start","server",guide+timedelta(minutes=15),"game2")]:
            db.add(ExperienceEvent(player_id=p["id"],event_id=str(uuid.uuid4()),kind=kind,source=source,mode="pve",run_id=run,received_at=at))
        db.commit()
        out=report(db,now=now)
        day=out["daily_cohorts_kst"]
        assert day["2026-11-01"]["d1"] == {"eligible":1,"returned":1,"rate":1.0}
        assert day["2026-11-02"]["first_game_completion"] == {"eligible":1,"converted":1,"rate":1.0}
        assert day["2026-11-03"]["retry"] == {"eligible":1,"converted":1,"rate":1.0}
        assert day["2026-11-02"]["first_game_by_source"]["server"]["converted"] == 1


def test_retention_preserves_original_session_and_first_guide_exit_cohort(monkeypatch):
    from tools.player_metrics import report, prune_raw_events
    import app.experience as experience
    from app.experience_models import ExperienceState
    _,p=api.login("alpha")
    now=datetime(2026,11,3,16,0,tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"],analytics_consent=True))
        db.commit()
        for days in (40,2,1):
            monkeypatch.setattr(experience,"utcnow",lambda days=days: now-timedelta(days=days))
            for kind in ("session_start","tutorial_skip"):
                experience.record_event(db,p["id"],kind,str(uuid.uuid4()),"lobby",source="client",event_id=str(uuid.uuid4()))
            db.commit()
        before=report(db,now=now)
        assert before["d1"]["eligible"] == 0
        assert before["first_game_completion"]["eligible"] == 0
        prune_raw_events(db,now=now)
        db.commit()
        after=report(db,now=now)
        assert after["d1"] == before["d1"]
        assert after["first_game_completion"] == before["first_game_completion"]
        db.expire_all()
        state=db.get(ExperienceState,p["id"])
        assert state.first_session_at is not None and state.first_guide_exit_at is not None

def test_mode_start_cohort_boundaries_and_duplicate_run_events():
    from tools.player_metrics import report
    from app.experience_models import ExperienceState,ExperienceEvent
    _,p=api.login("alpha")
    now=datetime(2026,11,3,16,0,tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"],analytics_consent=True))
        for kind,minutes,run in [("practice_start",1441,"before"),("practice_complete",1435,"before"),("practice_start",1440,"edge"),("practice_complete",1430,"edge"),("practice_start",30,"exact"),("practice_start",30,"exact"),("practice_complete",0,"exact"),("practice_start",60,"late"),("practice_complete",29,"late")]:
            db.add(ExperienceEvent(player_id=p["id"],event_id=str(uuid.uuid4()),kind=kind,source="client",mode="range",run_id=run,received_at=now-timedelta(minutes=minutes)))
        db.commit()
        out=report(db,days=1,now=now)
        assert out["modes"]["range"]["completion_by_source"]["client"] == {"eligible":3,"converted":2,"rate":2/3}


def test_missing_durable_anchors_are_left_censored_before_and_after_prune():
    from tools.player_metrics import report,prune_raw_events
    from app.experience_models import ExperienceState,ExperienceEvent
    _,p=api.login("alpha")
    now=datetime(2026,11,3,16,0,tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"],analytics_consent=True))
        for days in (40,2,1):
            for kind in ("session_start","tutorial_skip"):
                db.add(ExperienceEvent(player_id=p["id"],event_id=str(uuid.uuid4()),kind=kind,source="client",mode="lobby",received_at=now-timedelta(days=days)))
        db.commit()
        for _ in range(2):
            out=report(db,now=now)
            assert out["left_censored_accounts"] == {"session":1,"guide_exit":1}
            assert out["d1"]["eligible"] == out["first_game_completion"]["eligible"] == 0
            prune_raw_events(db,now=now)
            db.commit()


def test_cohort_anchor_is_consent_gated_and_excludes_delayed_client_events(monkeypatch):
    from app.experience_models import ExperienceState
    import app.experience as experience
    a,p=api.login("alpha")
    now=datetime(2026,11,3,16,0,tzinfo=timezone.utc)
    monkeypatch.setattr(experience,"utcnow",lambda:now)
    e=dict(event(),kind="session_start")
    assert request("post","/events",a,events=[e]).json()["accepted"] == []
    request("post",headers=a,action="consent",analytics_consent=True)
    request("post","/events",a,events=[dict(e,queued_ms=1000),dict(event(),kind="tutorial_skip",queued_ms=1000)])
    with SessionLocal() as db:
        state=db.get(ExperienceState,p["id"])
        assert state.first_session_at is None and state.first_guide_exit_at is None
    request("post","/events",a,events=[dict(event(),kind="session_start"),dict(event(),kind="tutorial_complete")])
    request("post",headers=a,action="consent",analytics_consent=False)
    monkeypatch.setattr(experience,"utcnow",lambda:now+timedelta(days=1))
    request("post","/events",a,events=[dict(event(),kind="session_start")])
    with SessionLocal() as db:
        from app.game_rules import as_utc
        state=db.get(ExperienceState,p["id"])
        assert as_utc(state.first_session_at) == now
        assert as_utc(state.first_guide_exit_at) == now

@pytest.mark.parametrize("prune_before_live",[False,True])
def test_legacy_live_history_stays_censored_through_ingestion_and_prune(monkeypatch,prune_before_live):
    from tools.player_metrics import report,prune_raw_events
    from app.experience_models import ExperienceState,ExperienceEvent
    import app.experience as experience
    _,p=api.login("alpha")
    now=datetime(2026,11,3,16,0,tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"],analytics_consent=True))
        for kind in ("session_start","tutorial_skip"):
            db.add(ExperienceEvent(player_id=p["id"],event_id=str(uuid.uuid4()),kind=kind,source="client",mode="lobby",queued_ms=0,received_at=now-timedelta(days=40)))
        db.commit()
        if prune_before_live:
            prune_raw_events(db,now=now)
            db.commit()
        for days in (2,1):
            monkeypatch.setattr(experience,"utcnow",lambda days=days:now-timedelta(days=days))
            for kind in ("session_start","tutorial_complete"):
                experience.record_event(db,p["id"],kind,str(uuid.uuid4()),"lobby",source="client",event_id=str(uuid.uuid4()))
            db.commit()
            prune_raw_events(db,now=now)
            db.commit()
        out=report(db,now=now)
        assert out["d1"]["eligible"] == 0
        assert out["first_game_completion"]["eligible"] == 0
        assert out["left_censored_accounts"] == {"session":1,"guide_exit":1}


@pytest.mark.parametrize("legacy_live_session",[False,True])
def test_deferred_only_history_can_be_first_live_and_censoring_is_per_anchor(monkeypatch,legacy_live_session):
    from tools.player_metrics import report,prune_raw_events
    from app.experience_models import ExperienceState,ExperienceEvent
    import app.experience as experience
    _,p=api.login("alpha")
    now=datetime(2026,11,3,16,0,tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(ExperienceState(player_id=p["id"],analytics_consent=True))
        for kind in ("session_start","tutorial_skip"):
            db.add(ExperienceEvent(player_id=p["id"],event_id=str(uuid.uuid4()),kind=kind,source="client",mode="lobby",queued_ms=0 if legacy_live_session and kind=="session_start" else 1000,received_at=now-timedelta(days=40)))
        db.commit()
        prune_raw_events(db,now=now)
        db.commit()
        for days in (2,1):
            monkeypatch.setattr(experience,"utcnow",lambda days=days:now-timedelta(days=days))
            for kind in ("session_start","tutorial_complete"):
                experience.record_event(db,p["id"],kind,str(uuid.uuid4()),"lobby",source="client",event_id=str(uuid.uuid4()))
            db.commit()
        out=report(db,now=now)
        assert out["first_game_completion"]["eligible"] == 1
        assert out["d1"]["eligible"] == (0 if legacy_live_session else 1)
        assert out["left_censored_accounts"] == {"session":int(legacy_live_session),"guide_exit":0}

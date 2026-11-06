# Player Growth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Execute stages in order; use isolated file ownership for independent tasks inside each stage.

**Goal:** Ship approved first-play guidance/measurement followed by server-verified weekly training rankings/rewards and end-to-end verification.

**Architecture:** Existing Unity/FastAPI, account-scoped experience state and consent-gated first-party events. Deterministic versioned training replay computes authoritative scores; DB constraints and transactions settle weekly rewards once.

**Tech Stack:** Unity 6000.3.23f1 C#, FastAPI, SQLAlchemy, SQLite/PostgreSQL, pytest, Android ARM64 IL2CPP.

**Spec:** ../specs/2026-11-02-player-growth-design.md (approved by user).

## Global Constraints

- Active Unity source only `C:/Users/good6/WarfrontMVP/Assets`; preserve Editor/unsaved scene and existing API/game flows.
- Monday 00:00 KST rotation, 45-second free games; previous season final at 00:10, claim deadline 28 days later.
- Rewards rank 1:30, 2–3:20, 4–10:10, other positive-score participants:3 diamonds; no stamina/PvP rating changes.
- Analysis opt-in defaults false, 200 queued events/7 days, 50 per batch, raw retention 30 days; no external SDK.
- Do not publish/deploy, change real clocks or inject records into real reward DB. All questions/justifications Korean.

## Review Focus

1. Account/server switch and async callbacks cannot leak consent, queued events, tutorial state or training runs.
2. Offline tutorial progress and failed telemetry cannot block lobby or falsely mark skip as completion.
3. Integer replay and input at the last tick/penalty termination must agree across C#/Python.
4. Concurrent/retried reward claims and finishes must not duplicate credit or regress highest score.
5. Cross-week run/grace/claim boundaries and server restart must preserve the same rank and reward.

## Stage 1

### Task 1: Experience state, first-party events and reports

Files: create `backend/app/experience.py`, `backend/app/experience_models.py`, `backend/app/experience_routes.py`, `backend/tools/player_metrics.py`, `backend/tests/test_experience.py`; modify `backend/app/main.py`, `online_rooms.py` only for registration and canonical event hooks.

Interfaces: GET `/v1/experience` → `{version:1,tutorial_step:0..3,tutorial_status:new|in_progress|skipped|completed,analytics_consent:bool}`. POST same path with `{action:start|progress|skip|consent,tutorial_step?:int,analytics_consent?:bool}` → same DTO. Progress 1=move completed, 2=attack, 3=dodge/completed. Consent changes independent; never regress completed steps. POST `/v1/experience/events` `{events:[{event_id,app_session,run_id,kind,mode,step,duration_ms,queued_ms,success}]}` → `{accepted:[event_id],consent:bool}`. `record_event(db,player_id,kind,run_id,mode,...)` is the canonical server hook. Operator report is read-only by default; prune requires explicit flag.

- [x] RED tests for default-off/account isolation, skip vs complete, sequential progress, consent/dedup/bounds/queued events and metrics mature windows.
- [x] Implement API/models/report and canonical game/matching hooks with enum allowlists, server time and source labels.
- [x] GREEN `backend/.venv/Scripts/python.exe -m pytest` from backend; reviewer verifies task and privacy boundaries.

### Task 2: Unity guide, consent and resilient queue

Files: create active `Assets/script/ExperienceApiClient.cs`, `ExperienceView.cs`, `ExperienceQueue.cs`, `TutorialSimulation.cs`, `Assets/Editor/ExperienceChecks.cs`; modify active `GameBootstrap.cs`, `LobbyView.cs` and minimal start/finish/navigation hooks.

Consumes Task 1 DTOs. Produces actual movement/attack/dodge tutorial using shared ArenaControls geometry, resume/skip/repractice, welcome/complete navigation, consent settings and account/server queue. Queue adds UUID event IDs, flushes max50, drops only acknowledged IDs, max200/7 days, bounded exponential retry; consent revocation clears queue. Async results must check account/server generation. UI errors cannot block lobby.

- [x] RED pure checks for movement/attack/dodge order, resume/skip distinction, queue cap/ack/expiry/isolation and revoke.
- [x] Implement UI/integration, first-load guide, retry/resume, fresh session/mode/start/finish/retry hooks.
- [x] GREEN pure Unity checks and baseline Arena/Training checks; review task and combine Stage 1 full backend/Unity compile before Stage 2.

## Stage 2

### Task 3: Portable competitive rules and replay

Files: active `Assets/script/TrainingSimulation.cs`, `Assets/Editor/TrainingChecks.cs`, new portable fixture/check files; backend `app/training_replay.py`, `tests/test_training_replay.py`, shared JSON fixtures under `backend/tests/fixtures/`.

Interface: training rules `v2`, 100Hz (4,500 active ticks), coordinate scale100, xorshift32 explicit uint wrap; integer sqrt/truncating division for drone movement. Preserve UI-facing TrainingSession API, add `PlayedTicks`, `RulesVersion`, `Inputs`, `AdvanceTicks`. Inputs `{tick:int,action:0=tap|1=move|2=signal,x:int,y:int,index:int}`; max one per tick, monotonically increasing, max4,501. Actions apply to state after `tick` advances and before next tick; final cipher penalty can finish at `total_ticks` without another tick. `replay(game,seed,total_ticks,events)` returns authoritative metrics and rejects unfinished/extra actions. Seeds and rules pinned by server. Public positions remain world floats derived from integers for rendering only.

- [x] RED hand-derived PRNG/tick/score tests, positive/negative/terminal fixtures, all three game parity.
- [x] Implement matched integer engines; preserve legacy local record key for old scores and use v2 key for new play.
- [x] GREEN Python replay tests + Unity fixture generator/checker; compare complete fixture outcomes, not only score; task review.

### Task 4: Training sessions, leaderboard and transactional rewards

Files: new `backend/app/training_models.py`, `training_routes.py`, `training_service.py`, `backend/tools/apply_growth_schema.py`, `backend/tests/test_training_league.py`, schema deployment notes. Main app router registration after Task1 ownership finished.

Interfaces: POST `/v1/training/runs` `{}` → `{run_id,season_id,game,rules_version,seed,starts_at,expires_at}`; POST `/v1/training/runs/{id}/finish` `{total_ticks,events}` → server score/metrics/player DTO; POST `/v1/training/runs/{id}/cancel`. GET `/v1/training/leaderboard?season_id=` → season/times/status/entries(top50)/my_rank/my_score/participants/expected_reward. GET `/v1/training/rewards` → eligible/recent claims; POST `/v1/training/rewards/{season_id}/claim` → `{reward,already_claimed,player}`. No user-supplied score/rank/reward. Server owns shared seed and run lifetime. Score0 can be verified but does not enter positive participant rank. Duplicate finishes return stable result; changed submissions conflict. Reward credit SQL atomic increment + unique claim in transaction. Late writes prohibited after grace so lazy settlement is stable.

- [x] RED auth/ownership/tamper/time/expiry/low-score/ties and concurrency/idempotence tests.
- [x] Implement with DB persistence, one live run/account, bounded input/body/start limits, source-separated telemetry.
- [x] RED→GREEN Monday/grace/claim deadlines, restart persistence, migration on populated DB/backup/restore; full backend suite and task review.

### Task 5: Unity competitive flow and reward UI

Files: active `TrainingApiClient.cs`, `TrainingView.cs`, new `TrainingLeagueView.cs`; growth queue hooks, Editor checks.

- [x] RED checks for run/account binding, versioned key, single submission/cancel and stale callback guards.
- [x] Start server run before competitive play; personal practice fallback labelled. Use seed/version from server, submit input log with retry and canonical score display. Never allow retry state to overwrite new run.
- [x] Integrate leaderboard/top50/me, finished-season rewards and once-only claim, timeout/retry/back paths and local-vs-server record copy.
- [x] GREEN Unity complete checks + compile; task review then broad whole-change review and fix material findings with RED→GREEN.

## Stage 3

### Task 6: Build and verify full service flow

- [x] Run full backend and all Unity checks from isolated disk snapshot, verify source hashes, build Android APK with complete existing SDK.
- [x] Verify guide move/attack/dodge/skip/replay, consent off/on/queue retry, first game/finish/retry, profile unchanged by free play on connected phone where available.
- [x] Test server rankings/multiple accounts and past-season claims on isolated clock/DB. Test app result/retry/ranking/reward UI with verification server, clearly distinguish injected calendar and real current week.
- [x] Restore direct normal test server and actual current calendar; no test reward pollution. Preserve active Editor/scene. Capture only foreground game.
- [x] Save hashes/screenshots/test outcomes, update status/docs/plan/ledger. Record unavailable iOS/multiple real devices/production deployment explicitly. Do not claim unrun checks.

Completed 2026-11-04. Evidence and exact limits: `PLAYER_GROWTH_2026-11-04.md`, `validation/player-growth-2026-11-04/`. Dodge used Android keyboard D+SHIFT, not a physical two-finger touch test. Physical background-kill queue restoration was not separately fault-injected; pure queue persistence/isolation checks passed. Existing real-test stamina recovers normally on login; isolated free play itself spends no resources.

## Execution record

Implementation follows the user's approved sequential instruction without another plan approval. File scopes may run concurrently inside a stage; Stage 2 starts after Stage 1 integration passes. No commits/branch mutation until repository ownership and writable git metadata can be verified; preserve existing edits and use source backups/snapshot verification when git is unavailable.

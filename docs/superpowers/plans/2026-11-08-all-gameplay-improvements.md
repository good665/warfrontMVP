# All gameplay priorities implementation plan

> **For agentic workers:** Inline integration with parallel independent domains as allowed by dispatching-parallel-agents. User explicitly requires ALL implementation before final verification.

**Goal:** Complete priorities 2–6 while preserving manual target lock.

**Architecture:** Server-authoritative combat/quest progression, additive persisted schema, focused Unity presentation partials, integrated settings/navigation/equipment panels.

**Tech Stack:** FastAPI, SQLAlchemy, Unity 6000.3.23f1, C# Input System.

**Spec:** docs/superpowers/specs/2026-11-08-all-gameplay-improvements-design.md

## Global constraints

- Active Unity destination C:/Users/good6/WarfrontMVP/Assets; preserve existing meta/scenes and current server integration.
- Stage under Temp/WarfrontWidgetValidation/Assets; no legacy Unity copies.
- Implement everything before running tests/compilers/review checks, per explicit user request.
- Preserve existing users/progression; additive schema only; no remote deployment, commits or resets.

## Review focus

- Windup location is fixed and damage happens after the warning; dodge/death cancel inappropriate damage.
- New quest progress survives restart and repeated claim cannot grant duplicate rewards.
- UI treats old snapshots/missing optional fields safely; no spurious loot notifications on first profile.
- Touch input rectangles match their visible positions; cancel/default/save and invalid persisted values are safe.
- Navigation points to real targets/party members and header/target/control panels do not obscure input.

## Implementation (no checks until all complete)

- [x] Server: enemy telegraph/stagger and persistent varied quests, additive schema and final tests authored.
- [x] Unity combat: warning rings/progress, authoritative hit reaction/audio and cleanup.
- [x] Unity progression/navigation: quest detail, comparison/loot toast, minimap/objective bearing.
- [x] Unity settings: persisted sensitivity/inversion/camera/volume and per-control layout with safe preview/save.
- [x] Integrate models, snapshot hooks, field/header/lobby/menu routes and lifecycle.

## Final verification and application

- [x] Run full backend tests including new behavior and migration tests; fix any failures.
- [x] Run Unity compilation/native regression including target lock and new complete-flow checks.
- [x] Run local server API + Play Mode render and input settings persistence/cancel checks; inspect screenshots.
- [x] Independent review and any necessary fixes; recheck changed behavior.
- [x] Install backed-up/hash-guarded Assets; apply migration to named local validation server; inspect active Editor.
- [x] Save evidence and report limitations (mobile/new APK/remote deployment).

## Ledger

- Explicit user request overrides test-first and repeated design/plan approval gates. This document records concrete scope and the chosen existing-stack implementation; proceed without another approval round.

- Final evidence: 191 backend tests passed; native Unity checks and real Play Mode UI/Input System verification passed; real Unity ApiClient -> local FastAPI -> PostgreSQL -> MmoApply -> scene actor integration passed.
- Reviewer found one P2 overlay input interception; fixed, reviewed and Unity checks rerun. Warning/name overlap fixed after visual inspection.
- Local PostgreSQL backed up and additive quest_state applied; original progression retained. Both disposable HTTP/Unity validation accounts cleaned.
- Installed 10 Assets files with original-hash guards and backups; final installed bytes match verified sources.
- Active Editor is minimized and computer-use getApp/state/raise fails with minimized/stale-window errors; no active Play session restart was forced. Active compile/play reconfirmation is the remaining environment limitation, covered by identical-code isolated compilation and real Play Mode.
- No mobile hardware, new APK, remote deployment or Git commits.

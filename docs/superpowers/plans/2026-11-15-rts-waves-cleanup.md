# RTS Waves and Retired Mode Cleanup Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add authoritative RTS waves and remove retired battle implementations without losing shared hero combat.
**Architecture:** Extract shared actor/skill behavior to rts_combat.py, implement route scheduling in rts_waves.py, simplify Unity consumers to RTS only.
**Tech Stack:** Python/FastAPI/pytest; Unity 6000.3.23f1/C#.
**Spec:** docs/superpowers/specs/2026-11-15-rts-waves-cleanup-design.md

## Global Constraints
- Active Unity edits belong only under C:/Users/good6/WarfrontMVP/Assets; preserve .meta identities for retained scripts.
- Preserve multiplayer ownership, 1v1/2v2, hero selection and abilities.
- No automatic commits or changes to user secrets/generated build folders.

## Review Focus
Destroyed wave destination redirects; large elapsed ticks preserve cadence; finished games never spawn; direct and bot orders do not silently override automatic routes; shared skill visuals survive retired-mode cleanup.

### Task 1: Authoritative wave behavior
Files: backend/tests/test_rts_game.py, backend/tests/test_rts_waves.py, backend/app/rts_waves.py, backend/app/rts_game.py.
- [x] Replace obsolete no-wave assertion with exact 30-second generation assertions; add ownership, waypoint order, combat resume, manual override, destroyed source/destination and finished-game cases.
- [x] Run .venv/Scripts/python.exe -m pytest tests/test_rts_game.py tests/test_rts_waves.py; confirm missing behavior fails.
- [x] Implement RtsWaves.spawn_wave(), set_wave_route(unit, destination), wave_tick(unit, dt), update_waves(); integrate with tick and battle_snapshot next_wave.
- [x] Run focused tests; expect all pass.

### Task 2: Retired server code
Files: backend/app/rts_combat.py, rts_game.py, squad_bot.py; retired modules/tests after reference audit.
- [x] Extract actor/stats/input/damage/event/use_skill/public and action state from old classes; keep skill assertions using RtsGame.
- [x] Remove FiveFloorGame/SquadGame execution, exclusive strategy/bow/movement modules and exclusive tests only when runtime references are gone.
- [x] Simplify bot to RTS controller and ensure all routing/room tests target current behavior.
- [x] Run full python -m pytest, report each unresolved failure.

### Task 3: Unity cleanup and verification
Files: active Assets/script/FiveFloorBattle.cs, FiveFloorScene.cs, SquadView.cs, SquadModels.cs, RTS view/input files and audited legacy partial classes.
- [x] Preserve zodiac selection, actor prefabs, jump and skill effects under RTS names; remove portals, obsolete item inventory and legacy strategy HUD branches.
- [x] Remove exclusive files and matching .meta only after reference audit. Request filesystem approval for active-project writes.
- [x] Compile using available Unity editor/build tooling, verify RTS wave render/navigation if editor is available; record limitations if not.
- [x] Review final references, backend suite, and changes.

## Execution ledger
User approved design and requested execution. Work is in existing shared workspace to apply to the active external Unity project; preserve unrelated edits, do not create commits. Plan execution is inline.

Task 1: complete — failing wave tests observed before implementation; periodic spawns, ownership, path/combat/manual behavior, destroyed bases and bot preservation pass.
Task 2: complete — RTS common combat extracted; five_floor_game/squad_game and exclusive bow/strategy/movement modules removed; shared zodiac ability tests migrated. Retired API fields removed; room/API tests retained.
Task 3: complete — 31 active Unity scripts added/updated, 14 exclusive scripts and their .meta files removed after a reference audit. Shared renamed scripts retain GUIDs. Original backup: C:/Users/good6/AppData/Local/Temp/warfront-rts-wave-backup-20261115-194415.
Validation: backend `python -m pytest -q`: 266 passed in 33.40s. Unity runtime/editor C# compilation passed. In active Unity Editor, RtsWaveChecks passed 2v2 allied 10-wave actor ownership/movement/render and pause input reset; RtsChecks passed grid/raycast/selection; ZodiacEffectChecks passed all 24 effects. Evidence: docs/verification/rts-waves/.
Review: independent read-only reviewer ran 59 RTS tests and found no critical/important issues. Git status was unavailable due repository ownership protection; no git configuration or commits changed.
Ruling: Removed-mode behavior tests were deleted, while HTTP-room tests and shared hero/skill/visual regressions were migrated to RTS rather than discarded.
Ruling: UI settings previously controlling the removed angled camera now control RTS zoom with its valid 8–67 range; per-field .meta identity retained. No gameplay assets or scenes removed.

# Squad computer opponent implementation plan

> **For agentic workers:** Independent server implementation and inline Unity integration. Preserve implementation-first, final-checks-last order.

**Goal:** Add explicit computer-opponent squad matches without changing real-human matchmaking.

**Architecture:** Same authoritative SquadGame, per-room bot controller emits normal inputs, separate computer-create API, additive snapshot mode field and Unity lobby/HUD.

**Tech Stack:** FastAPI/Python, Unity 6000.3.23f1/C# and existing ApiClient.

**Spec:** docs/superpowers/specs/2026-11-08-squad-computer-design.md

## Constraints and review focus

- All bot recruitment/damage/cooldowns are ordinary game rules; no direct positions/HP advantages.
- Computer IDs are room-local, never authenticated players, queue entries or DB accounts.
- Human reconnect/leave and computer heartbeat handling cannot produce false wins or stuck sessions.
- Lobby clearly distinguishes computer from human modes; no settings click-through.
- Preserve active Assets, original meta and RPG progress. No remote deploy/new APK.

## Implementation

- [x] Server controller, computer room API, mode metadata and tests authored.
- [x] Unity mode field, API call, lobby button, HUD labels and native checks.

## Final checks

- [x] Full backend suite, controller recruitment/attack/retreat/respawn and room isolation/auth checks.
- [x] Unity new and existing native regressions.
- [x] Actual one Unity client vs server computer, rendered lobby/match screenshot, cleanup fixture accounts after exit.
- [x] Independent review; fix/recheck defects, backed-up install and hash comparison.

- Final full suite: 219 passed in 28.43s; computer-specific 8 passed. Fixed deterministic 30-second heartbeat subtraction roundoff via expiry-time comparison, with 29.95/30 boundary coverage.
- Unity computer/native existing regressions and real single-client computer match Play Mode passed; observed solo spawn, both natural recruitment, bot movement and restored room/leave. Screenshots inspected.
- Independent code review found no important defects. Temporary account cleaned after process exit.
- Applied four Unity files with backups/original-hash guards; final active files equal verified sources. Server implementation local; no DB schema/account/economy changes. No offline mode/new APK/mobile or external deployment.

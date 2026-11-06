# Three Weekly Games Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Open range, drone and cipher every week with independent rankings and once-only rewards per game, as approved by the user.

**Architecture:** Preserve legacy weekly season rows, runs, bests and claims. The legacy rotating game keeps the eight-character week ID; the other games use week-game IDs and the same existing transactional settlement code. Explicit game selection is added to start and leaderboard requests, while omitted game retains legacy behavior. Weekly calendar exposes all three available games.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite/PostgreSQL, Unity C# IMGUI.

## Global Constraints
- Active Unity sources only: C:/Users/good6/WarfrontMVP/Assets/script; preserve existing changes including both 30-second survival intervals.
- Weekly boundary Monday 00:00 KST; settlement Monday 00:10 KST; claim lifetime 28 days; existing reward tiers unchanged, applied independently to each game.
- Do not delete or reset existing player records, scores, runs, or claims.
- One active run per account, server replay validation, bounded submissions and atomic claims remain enforced.
- Stage and back up active Unity edits before requesting filesystem write access.

## Review Focus
- Switching games while an existing run is active must not accept the other game's replay.
- Legacy week IDs and received rewards must not produce duplicate entitlements under new suffixed IDs.
- Reward validator/window must allow three times the previous number of entries.
- Week rollover and in-flight settlement retain exclusive deadlines and original seeds.
- Async responses must not replace a newly selected game's leaderboard.

## Task 1: Independent server leagues
- [x] Add tests for selecting all three games, distinct seeds and league IDs, isolated ranks and rewards, invalid games and legacy aliases.
- [x] Run tests and confirm failures before implementation (four expected failures).
- [x] Extend calendar, season identity resolution, request game parameters and SQL column lengths. Add PostgreSQL widening migration while SQLite remains compatible.
- [x] Run targeted tests then the full backend suite (171 passed).

## Task 2: Unity selection and views
- [x] Stage current source files and preserve original backups.
- [x] Open all three cards with selected-game competition/practice, add leaderboard tabs and named reward entries.
- [x] Pass game selection to API; validate extended season IDs, matching game and expanded reward window.
- [x] Compile active runtime; pure C# checks 39 passed; actual Unity batch checks 189 passed. Interactive UI inspection remains unperformed.

## Task 3: Integration and delivery
- [x] Document behavior and schema update; independent reviewer found no blocking defects.
- [x] Apply schema with verified backup to the active test database, restart test server and probe actual game-specific API routes; three game starts/cancels and separate boards passed over HTTPS.
- [x] Updated Android development APK built successfully; 48,733,596 bytes, ZIP CRC passed, active source hashes match build snapshot. No phone installation or interactive screen verification. Findings and limitations recorded in THREE_WEEKLY_GAMES_2026-11-06.md and validation/three-weekly-games-2026-11-06/verification.json.

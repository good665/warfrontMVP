# Corner Command Grid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the four lower command buttons with a bottom-right 3×3 strategy grid and automatic enemy-base advance.

**Architecture:** Keep authoritative economy and movement on FastAPI. Keep existing Unity input intent and retry handling; change presentation and map numeric keys to visible grid cells. Retain all economy actions across two pages.

**Tech Stack:** Unity 6000.3 C# IMGUI / Input System; FastAPI Python / pytest.

**Spec:** User request in this conversation: remove gather/focus/hold/retreat strip, 3×3 corner strategy HUD, hover hotkeys, building-related automatic advance.

## Global Constraints

- Active Unity source is C:/Users/good6/WarfrontMVP/Assets/script; stage changes and preserve backups.
- Preserve combat keys Q/E/Space/Shift, current movement and allied no-push rule.
- User confirmed barracks automatically produces troops and sends them to enemy headquarters. Buttons use small image icons; tooltip contains text and hotkeys.

## Review Focus

- Hovering/clicking grid must suppress world mouse attacks.
- Numeric shortcuts fire once and follow the current page; affordability and readiness gates apply equally to mouse and keyboard.
- Dead/disconnected players cannot queue economy actions.
- Building placement remains captured until a minimap click; retries retain exact intent.
- Automatic orders must respect capacity, construction completion, destroyed buildings and manual orders.

### Task 1: Corner HUD

- [x] Add staged Unity checks for 9 cells, corner bounds, tooltips and both pages.
- [x] Observe failing checks against current source.
- [x] Replace DrawStrategyHud and key mapping, remove old strip and pointer region.
- [x] Compile and run Editor checks; inspect actual GUI.

### Task 2: Automatic advance

- [x] Confirm production interpretation; write regression cases for construction/production and both teams.
- [x] Observe failures, implement automatic behavior on server.
- [x] Run strategy, bot, movement/combat checks.

### Task 3: Verification

- [x] Review final change, resolve important findings.
- [x] Record Editor checks, backend results and visual verification.

## Results

- CornerCommandChecks PASS in Unity; preview visually shows nine small pixel icons in the bottom-right. Both pages, shortcut strings, disconnected input rejection and full tooltip pointer area verified.
- Barracks completes construction, spends 60 supplies per automatic three-guard squad, respects 9 population / 3 squads, and sends produced guards with attack_move toward enemy headquarters. Construction ownership is captured at placement. Manual orders remain authoritative.
- Destroying a barracks cancels and refunds its queued automatic job. Completed jobs wait if no clear exit exists. Safe exit placement checks terrain and all live body spacing before committing the entire group.
- Review found two issues, both fixed: obstacle-intersecting spawns and tooltip's left extension passing clicks through to combat. Follow-up review found no remaining important issue.
- Full backend run: 335 passed, 13 pre-existing failures (pathfinding actor fixtures, formation and companion coordinate expectations). A subsequent additional blocked-exit regression was run with the automatic production suite.
- Unity files backed up under `%TEMP%/warfront-corner-commands/backup`. Staged files under `%TEMP%/warfront-corner-commands`.

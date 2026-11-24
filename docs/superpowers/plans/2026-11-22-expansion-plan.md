# Game Expansion Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for independent backend and asset tasks; primary implements Unity integration. Preserve file ownership and execute feature stages in the approved order.

**Goal:** Implement all 17 requested expansion ideas on the existing server-authoritative Unity game.
**Architecture:** Extend existing RTS modules with focused expansion systems; add backwards-compatible snapshots. Import reproducible Blender assets under active Unity Assets and consume server state in scene partials.
**Tech Stack:** Python/FastAPI/pytest, Unity 6000.3.23f1 C#, Blender 4.5, PNG/FBX.
**Spec:** ../specs/2026-11-22-expansion-design.md

## Global Constraints
- Active Unity C:/Users/good6/WarfrontMVP/Assets only; preserve scenes, Character.fbx and newer script integration.
- All movement/hit/reward/progression decisions server-owned. No external deployment without requested scope.
- Use spec network contract; coordinate additions before integration.
- Work in current user-mandated active paths with backups; git currently reports unsafe ownership, no global configuration changes.

## Review Focus
- Invalid movement/target/slot/vehicle/portal requests must not consume items or escape bounds.
- Every team can reach the final bell after a base dies, including respawning heroes.
- Regions/floors isolate combat and visuals; duplicate snapshots never duplicate rewards.
- Inventory expansion never grants unavailable slot access to normal players.
- Long jump/vehicle sweeps cannot tunnel through players/obstacles; deaths clear action states.

### Task 1: Server gameplay stages
Owner: backend implementation agent. Files backend/app/{rts_game,rts_combat,rts_map,rts_waves,squad_items,squad_routes}.py and focused new expansion modules, backend/tests.
- [x] Write behavioral tests before changing each stage, observe RED then GREEN.
- [x] Stage1 chests180/3-perbuilding/coin reward/ball30 indoor/top2x/warp/G removal.
- [x] Stage2 server jump trajectory and weapon visual identity.
- [x] Stage3 3 lanes, cathedral traversal and vehicle server state/interact.
- [x] Stage4 final phase, reachable lobby/bell, team cumulative true damage victory and respawns.
- [x] Stage5 six regions, directed portals, 20% special chests, 11 slots, bounded10stage match progression and transition lock.
- [x] Publish exact added snapshot contract and run entire pytest suite.

### Task 2: 3D source and asset delivery
Owner: asset implementation agent. Files .tools/game-expansion/assets only; do not write active Assets directly.
- [x] Investigate both exact source models and retain attribution/license evidence or report concrete access blocker.
- [x] Generate FBX+editable blend+PNG UV materials: coin, improved normal/dimensional chest, warp relic, car/motorcycle/bus, golden bell, 6 regional environment props/ground and optional traversal/final fallback buildings.
- [x] Check mesh/UV/bounds/materials and render contact sheet, document exact names/orientations/scales.

### Task 3: Unity gameplay integration
Owner: primary. Stage under .tools/game-expansion/client; apply via audited installer/backups to active Assets.
- [x] Extend DTOs, F input and 11-slot HUD with clear descriptions; remove G.
- [x] Connect equipped weapon identity/tier, superjump pose and actor growth visuals.
- [x] Render authoritative coin/chests/vehicles/portals/objectives and transition VFX.
- [x] Build six themed areas and traversal/final interior visuals matching server coordinates and floors.
- [x] Add verification scripts for network schema, materials, visual state lifecycles, growth, slot input and all map captures.

### Task 4: Whole flow verification
- [x] Run backend full suite and Unity actual Play mode plus prior regression checks.
- [x] Independent review spec/quality; reproduce and correct important findings.
- [x] Inspect exported overview screenshots and report all delivered features plus external asset limitations.

## Ledger
Ruling: User's follow-up '추천 하는대로 진행해줘' adopts recommended final activation, pure bell damage and match-only progression defaults. Unspecified mechanics use explicit values in spec; balancing may need playtesting.

Backend: complete, 408 full tests passed (24 focused expansion tests). Independent review reproduced and corrected unsafe warp overlap, AI final routing, and offboard command bounds. Actual walking AI reaches bell and wins; actual center minion traverses cathedral floor18.
Assets: complete, 33 unique FBX incl original museum scan + optimized derivative, 8 transparent icons and 12 growth symbols. Exact Cathedral download disabled by author; separately labelled original fallback used. Original Upper Vestibule officially downloaded CC BY4.0, attribution retained; runtime derivative180k triangles.
Unity: first Editor and Play mode expansion + old skill/basic regressions passed. Independent review fixed old interior/offboard outside-view bounds and duplicate cathedral slab. Visual QA reduced growth ornaments, corrected mounted pose and vehicle heading. Added real Unity MeshCollider probe: imported museum yaw0 gave0/13 safe cells; yaw180 gave13/13. Prefab builder now applies180 correction; final reimport and rerun pending.

Final verification:409backend tests passed;25focused expansion tests. Unity final Editor and actualPlay mode expansion+old skill/basic regressions passed.20captures inspected; native museum floor13/13after180degree correction. Vehicle nearest-target RED/GREEN and deterministic normal-chest overflow fixture recorded. Evidence output/game-expansion/verification.txt. No deployment/devicebuild. Cathedraloriginal remains author-download blocker with disclosed fallback.

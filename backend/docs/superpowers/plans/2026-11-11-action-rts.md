# Action RTS Implementation Plan

> **For agentic workers:** Execute sequential server tasks with superpowers:executing-plans; use a fresh reviewer for the complete change.

**Goal:** Add the six approved RTS layers to the existing squad mode without replacing direct hero combat.
**Architecture:** Server-authoritative strategy mixin, room-local resources/queues/orders/vision. Unity consumes a `strategy` snapshot and sends strategy intents in the existing sequenced input, retaining retry idempotency.
**Tech Stack:** FastAPI/Python, Unity 6000.3 C#, existing Generic characters and native scene geometry.
**Spec:** User-approved six-item recommendation in conversation: capture/resources, production/cap, squad orders, counters/formations, fog/scouting, buildings/research.

## Global Constraints
- Active Unity assets only under C:/Users/good6/WarfrontMVP/Assets; preserve server integration, appearance, .meta and existing bow/hit/pooling.
- Keep camp starter companions; production adds up to three controllable squads, nine population. Scout is one unit, normal squads three units.
- All changes isolated to squad matches, no RPG gold/progression. No automatic base defense attacks.
- Enemy hidden data must be removed server-side; known headquarters and public capture ownership remain visible.
- Commands/spending require living authenticated owner, valid input sequence and match active.

## Interfaces
SquadSnapshot.strategy: supplies,income,population,population_cap,squad_cap (numeric); points[],squads[],queue[],buildings[],research[],vision[],explored[]; action_error string; tech_attack,tech_armor,tech_recon ints.
point: id,name,x,y,radius,owner(-1/0/1),capturing(-1/0/1),progress(0..1),contested.
squad: id,kind,command,formation,x,y,hp,max_hp,members,alive,target_id.
queue: id,kind,remaining,duration; building: id,kind,team,x,y,hp,max_hp,remaining; research: id,remaining,duration.
vision: x,y,radius; explored: grid cell IDs on 30x20 grid (120 world units/cell).
SquadInput: economy (none/train_guard/train_archer/train_healer/train_scout/build_barracks/build_outpost/build_tower/build_academy/research_attack/research_armor/research_recon), squad_id (empty=starter,all=all), formation(none/line/wedge/spread), command additionally move/attack_move. order_x/y world map coordinate.

## Review Focus
- Duplicate/retried inputs never double-spend or queue twice.
- Hidden enemy actors/projectiles/bombs/buildings are omitted; attacks cannot lock unseen targets.
- Contested capture stops; captured income time-step independent; match end freezes all activity.
- Dead hero, invalid faction ownership/placements/capacity reject intents without deducting resources.
- Exit/reconnect/rematch clears stale selection/visuals and restores the existing game.

## Tasks
- [x] 1. Capture three points over six seconds; contested freezes; base income 2/s plus 3/s per point; initial supplies 120. Tests capture/income/contest/reset.
- [x] 2. Production queues (max3), cost guard60/archer75/healer90/scout45, duration8/10/12/6, reserve population and squad cap at enqueue. Test no overbooking/idempotency/death/refund-free invalid inputs.
- [x] 3. Selected squad orders move/attack_move/hold/focus/retreat/gather, valid owner and coordinates, no attack chase for move/retreat. Test independent orders and ownership.
- [x] 4. Guard vs archer .75 incoming, archer vs healer 1.25, scout fragile; line/wedge/spread offsets, existing hero damage retained. Test counters/formations and projectile source attribution.
- [x] 5. 520 normal/760 scout vision with obstacle LOS, recon +120. Server-filter hidden entities and attacks, explored map30x20. Test LOS/fog/reappearance/minimap/reconnect.
- [x] 6. Buildings barracks100/12s faster training, outpost80/10s vision, tower100/12s passive cover, academy120/15s unlock research. Research costs100/100/80 and durations15/15/12; one each, requires completed academy. Test legal placement, enemy damage, bonuses, queues, bot same rules.
- [x] Unity: DTO + command panel + minimap order destination + resource/capture/queue/formation/research HUD + fog grid + world markers/buildings; existing models reused. Verify compile, native Editor checks and render representative HUD.
- [x] Final: full backend pytest; fresh code review; address findings; Unity native scene/input/lifecycle regression checks; report only verified outcomes.

## Verification ledger
- Backend baseline 300 passed; final full suite 316 passed in 52.68s.
- Unity StrategyIntegrationChecks PASS after final label cleanup, including retry, scene, bow, hurt, damage and pooling checks.
- Fresh backend/client reviews: important findings corrected and confirmed.
- Active Unity backup: TEMP/warfront-rts-backup-20261111; existing .meta preserved.


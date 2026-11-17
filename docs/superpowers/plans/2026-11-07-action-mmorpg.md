# Action MMORPG implementation plan

Goal: Replace game entry flows with a playable persistent shared-world action RPG while preserving main lobby.
Architecture: independent server-authoritative MMO service and SQL character tables; Unity partial views consume a fixed snapshot protocol and reuse existing pixel art/controls. Stage Unity changes outside active project until reviewed.
Tech Stack: FastAPI, SQLAlchemy, Python; Unity 6000.3.23f1 C#/IMGUI/Input System.
Spec: docs/superpowers/specs/2026-11-07-action-mmorpg-design.md
API contract: docs/superpowers/specs/2026-11-07-mmo-api.md

- [ ] Server: persistence, zones, authoritative combat, rewards, quests, inventory, parties and instance dungeon; API security/replay/idempotency and multi-client tests.
- [ ] Unity: protocol/client, scrolling field renderer, keyboard/touch action input, equipment/quest/party UI, reconnect safety.
- [ ] Integration: preserve lobby bytes, remap existing game entry methods, additive schema/local live setup, simulation/Unity/backend regressions.
- [ ] Review complete flow and fix blockers; validate two-client shared state, persistence and visible Unity flow, then install active Assets and record results/limits.

Global constraints: active Unity Assets only for runtime installation; preserve existing files/scenes/settings/secrets. No commits/push/deploy. No client-owned XP, gold or combat outcomes. Bound rates and simulation advances by server monotonic time, not input traffic. Duplicate actions cannot produce duplicate rewards. Existing players retain legacy balances.

Review focus: re-entry healing/respawn abuse, disconnected movement and stale attack input, concurrent once-only quest claims, unauthorized inventory/party access, scene/menu regression and camera coordinate conversion.

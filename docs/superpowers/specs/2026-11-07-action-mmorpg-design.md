# WARFRONT shared-world action RPG design

User approved the recommended MMORPG direction and direct movement, attack, skills and dodge. Preserve the main lobby visually and preserve LobbyView.cs byte-for-byte. Existing military pixel art remains the visual identity.

Playable loop: enter shared frontier → fight server-controlled enemies → earn persistent XP/gold/gear and complete quests → equip/upgrade → form a party by invite code → enter a party-isolated ruins boss dungeon → return to unchanged lobby. Existing bomb and rush entrances open frontier/minefield regions. Central training building opens frontier quests; workshop opens equipment; rankings opens character details; online entrance opens shared field/party controls. Legacy games stay in source but these entries launch RPG content.

Combat: WASD/arrows or left touch pad, pointer aiming, hold basic attack/Space, Shift dodge, Q/E two skills, existing touch attack/dodge/skill buttons. Camera follows player through a larger world. HUD shows own HP/XP, quests, gold, equipment and party. No client score/damage/loot authority. In online zones opening UI does not pause the shared simulation; movement inputs expire quickly after communication stops.

Regions: frontier shared hunting ground; minefield with growing explosive hazards; ruins solo or party-instance boss dungeon. 32-player field/channel and four-player party limits are initial engineering limits, not a claim of large-scale MMO deployment. One server process owns world simulation; character/inventory/quest progression survives reconnect/restart in SQL. Parties and world enemy state are session-local.

Alternatives considered: fully automatic idle progression vs direct action; user selected direct action. Replace menu artwork vs preserve main screen; user explicitly selected preservation. Existing short matches cannot serve as a persistent world, so add independent MMO APIs and tables while retaining legacy APIs.

No account migration/reset, production deployment, guild/trade/payment systems, or mobile build is implied. Additive schema and local end-to-end checks are part of this implementation. Online MMO scale/load testing remains a separate measured requirement.

# Spacious Hanok and passage interiors

Intent: redesign the cramped Hanok and passage rooms, deliver PNG design art and FBX, double both horizontal dimensions and make the additional area genuinely walkable.

Direction: 32x24-cell Hanok (was16x12), 48x18-cell passage (was24x9). Open central circulation, warm oak/dark timber/cream paper/muted sage palette matching the natural village; Hanok daecheong plus ondol rooms, passage gallery plus side lounges. Roof omitted and camera-facing walls cut down for gameplay visibility. Manor layouts and exterior footprints remain unchanged.

Architecture: server row grids are the collision authority and a reproducible layout input for Blender. Wider doorway groups map to one canonical portal per opening with aliases for all doorway cells. Interior origins use 40-cell spacing so expanded floors do not overlap. Update aim limits to include the new coordinate range. Furniture uses existing breakable prop cells and maps the new FBX furniture nodes to server prop records. Unity rejects incompatible old room dimensions and retains the old renderer as fallback.

Tasks:
1. Add failing backend tests for dimensions, room separation, door connectivity/aliases and full aim range.
2. Generate two PNG concept images; implement authoritative room layouts, coordinate spacing and input validation; run backend tests.
3. Export layout fixtures, build UV-mapped FBX/blend sources and materials from those layouts.
4. Import Unity prefabs, connect rooms and breakable furniture, verify markers/bounds/walkability, capture actual enlarged rooms.
5. Review and deliver files plus verification and server-restart instructions.

Implementation stays under the active Unity Assets for art/runtime changes and this workspace's backend for server changes. Back up edited Unity scripts; preserve existing scenes and character assets.

Completed: all five tasks. Backend suite: 390 passed. Unity actual FBX checks passed 2026-11-21T23:36:22, including doorway aperture raycasts, furniture alignment/destruction, URP materials and old-layout fallback. Review found east doorway window/post overlap; generator now excludes overlapping decorations. FBX axis correction verified against authoritative doorway coordinates. Actual Unity overview/gameplay captures inspected. Delivery archive includes PNG/FBX/blend/textures/prefabs/scripts. Backend restart and new match required; no live server deployment performed.


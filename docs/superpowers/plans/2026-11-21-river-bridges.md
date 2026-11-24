# Flowing river and bridge assets

Intent: replace the existing blue water rectangles with river PNG/FBX art, visibly flowing water and bridges across existing crossing gaps. Match the newly balanced natural map and character materials.

Approach: generate a muted slate-teal seamless water PNG; model a UV-mapped subdivided water segment, bank edges and a weathered timber/stone bridge in Blender. A URP shader scrolls two texture layers with subtle waves in continuous board coordinates. Place bridges only across small gaps between adjacent collinear water rectangles, also rendering water below those gaps. Keep server map and collision data unchanged; the existing gaps remain the walkable crossing corridors.

1. [x] Add river acceptance checks; observe missing Water prefab before implementing.
2. [x] Generate PNG, actual 3D FBX and editable blend sources; verify reimport/UVs/physical thickness.
3. [x] Build persistent Unity materials/prefabs, implement gap detection and board integration.
4. [x] Verify water continuity/flow across time, bridge count/placement and zero added gameplay colliders; inspect actual Unity river/crossing captures.
5. [x] Review and package source/output, retaining edited-script backups.

Results: 3 FBX round trips passed, each optimized into one mesh. Unity PASS at 2026-11-21T22:39:37: four existing crossing gaps bridged, 12 continuous water sections including bridge gaps, temporal image difference at 0 and 3 seconds, no added bridge colliders, 64 terrain chunks retained. Actual crossing/overview renders inspected. Water recessed 0.12m with visual terrain cutouts; low bridge deck remains near authoritative actor ground level. Missing-prefab fallback preserves old rendering. Independent review found no confirmed regressions.

ZIP integrity passed (14.04 MiB), output under active Assets/ArtSources~/River_v1. No server/map/collision changes. Validation used existing map fixture; no live online match or Android hardware performance test.

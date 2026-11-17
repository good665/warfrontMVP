# Mini Dungeon reskin and first person

User explicitly requests replacing all presentation with https://kenney.nl/assets/mini-dungeon and replacing all button/panel imagery, including cancel, save/connect and return. Subsequent steering adds first-person gameplay.

Use actual official CC0 Mini Dungeon FBX environments and its human/orc rigs and supplied clips. Reuse the existing isolated 3D renderer and server rules. Replace the town with a compact stone dungeon hub, and fields with dungeon floors/walls/props. Replace the global IMGUI skin atlas and custom lobby button surfaces; retain button routes and labels. First-person camera follows the authoritative local actor with view-relative WASD, mouse yaw/pitch, click/Space attack and Esc cursor release. Add perspective-projected enemy/hazard feedback; no 2D world-coordinate overlays in first person.

- [x] Inspect official source: 30 assets, native character rigs and 32 supplied animation clips; one shared color map.
- [ ] RED native prefab/import and first-person direction checks.
- [ ] Import models/materials and create human/orc animation prefabs; generate a new slate/violet/amber UI atlas.
- [ ] Compose dungeon hub and fields; connect first-person camera, cursor lifecycle, aim and movement; replace remaining custom UI surfaces.
- [ ] Run native checks and regression suite, review, install with backups, inspect main/settings/field/return in Unity Play.

Stage under `.tools/mini-dungeon`; validate in Temp/WarfrontWidgetValidation. Active destination is C:/Users/good6/WarfrontMVP/Assets. Preserve scenes, accounts, backend rules and existing assets for rollback. Desktop mouse-look plus existing touch movement/actions; dragging right half of field provides touch look. Do not commit/push.

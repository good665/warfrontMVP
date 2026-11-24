# Zodiac equipment and consumables implementation plan

**Goal:** Create twelve fitted armor FBX assets and shared top, long whip and bouncy ball FBX assets; replace placeholder visuals in the active Warfront Unity project.

**Approved scope:** Twelve character-specific armor sets and three shared consumables. Match the natural character palette and realistic fantasy materials from the existing ArtSources character references. Preserve existing server item effects and identifiers.

**Architecture:** Blender builds UV-mapped, material-separated meshes and editable sources. Armor chest and shoulder pieces attach to the existing rig independently. A weighted whip uses a bone chain driven by the existing authoritative whip effect. Unity creates persistent URP materials/prefabs under Resources/ZodiacItems. Runtime loads these for equipment, active consumables and ground loot.

**Tech stack:** Blender 4.5, Unity 6000.3.23f1 / URP 17.3, existing C# visual system.

## Tasks
- [x] Add an Editor acceptance check and observe missing-asset failure before implementation.
- [x] Generate and reimport 15 FBX files, UV textures, blend sources and preview renders under the active project's Assets.
- [x] Build URP materials and prefabs; connect rig armor, spinning top, bouncing ball, bending whip and dropped items.
- [x] Check imported meshes, all 12 equipment fits, whip deformation, item movement and removal, and shader compatibility in Unity.
- [x] Inspect rendered output, review changes, package source/output and report actual verification limits.

## Results
15 Blender FBX round trips passed; 15 Unity URP prefabs and 15 icons built. Unity Play-mode checks passed at 2026-11-21 20:30:34 local, including pose-independent armor attachment, actual weighted whip Pose deformation, authoritative snapshot item lifecycle, mid-whip field replacement and floor filtering. Twelve actual Unity character renders visually inspected. ZIP integrity passed (25.52 MiB).

Review found equip-pose dependence and stale sweep state on field replacement; both fixed with bind-pose transforms and pre-destruction cleanup. Visual QA found FBX part axis/unit transforms were discarded; preserved imported rotation/scale and adjusted armor clearance. Final breastplate changed to connected forged plate for a clearer armor silhouette.

No server gameplay changes. Live online match acquisition/use and Android-device checks were not run. Existing scenes/settings preserved; edited script baselines stored in active Assets/ArtSources~/ZodiacItems_v1/IntegrationBackup.

## Constraints
Work directly in C:/Users/good6/WarfrontMVP/Assets as explicitly requested. Preserve existing scripts/scenes/settings and back up edited scripts. No gameplay balance, collision or network schema changes. Unknown item IDs retain their existing fallback. No generated Library/Temp content in deliverables.

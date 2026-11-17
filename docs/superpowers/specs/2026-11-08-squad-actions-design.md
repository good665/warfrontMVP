# Squad action upgrade

User requests Blender modeling and readable swing/walk, hit distance, dodge and bombs during CPU squad battles. Prior instruction is to implement all changes and test last, so proceed without another approval cycle.

## Approach
Keep the existing Unity scene and server integration. Create an original low-poly armored commander with a weighted articulated rig, palette texture and six in-place actions in Blender 4.5. Export FBX and build a Unity legacy-animation prefab. Sprite-only presentation would not satisfy the requested modeling; purely procedural Unity meshes would not deliver Blender source. Preserve the existing dungeon enemies and replace squad combatants only.

## Behavior
Server owns attack windup/contact/recovery, facing, body radii, LOS, dodge movement and bomb damage. Client samples action phase from snapshots; no root motion or client damage. Normal attack has 145-unit reach, a .16s windup, 20 damage and .55s cooldown. Heavy attack uses Q (210,42,5s). Shift dodges for .22s at 580 units/s with existing immunity and 3s cooldown; standing dodge follows facing. E throws a bomb up to 600 units, .65s flight, 150-radius explosion for 30 damage, 8s cooldown. Walls block attacks and bomb targets; allies are safe. Draw sword arcs, ground reach, bomb landing warning and explosion. Walk persists between sparse network samples and stops when authoritative movement stops.

## Assets and constraints
Deliver editable .blend, reproducible Blender Python, FBX, palette PNG, Unity material/clips/prefab. Six animations Idle/Walk/Attack/Heavy/Dodge/Throw. Generic rig, normalized weights, no downloads or external paid assets. Preserve active scenes, existing metadata, RPG balance and human/CPU modes. Work in the isolated validation project first and install with hash guards/backups. Running match must not be used as a test account.

## Verification
Final backend suite; Unity compile, rig weights, baked posed meshes, phase sampling, input/UI integration, old regression suite; rendered idle/walk/swing/dodge/bomb and a real isolated computer match. No APK or mobile hardware claim.

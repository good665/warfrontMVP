# Blender skill visuals
Preserve the MiniDungeon Human mesh, material and named transform hierarchy.
Author Heavy (.55s, contact .20-.43), Throw (.30s), Dodge (.22s) on that rig in Blender.
Export editable blend, baked FBX and sampled Unity-local animation tracks; import the latter into native legacy clips without replacing the character.
Model a low-poly iron bomb and an explosion made of a shockwave, core and radial fragments; deliver FBX meshes, palette and URP materials.
Use server bomb state for launch/flight/explosion and damage radius. Pool the new blast effect and preserve existing pools. No physics or animation root motion changes authoritative movement/damage.
Verify baked skin motion, unchanged character meshes, clip duration and endpoints, bomb flight and explosion radius, pooling and scene cleanup. Inspect actual Unity preview; report limits.

# Archery motion refinement
Use the existing MiniDungeon Generic/legacy rig and bow/arrow assets; preserve the character mesh and authoritative server combat.
Phases in the .65-second Bow clip: prepare/raise 0-.07, draw .07-.22, fixed cheek anchor .22-.25, release .25, hand/bow follow-through .25-.36, recover .36-.65. Existing hero/charge/companion server-to-clip time mapping remains unchanged.
Bake torso/head/arm rotations and matching grip positions in the Editor. The simple rig has one bone per arm, so use restrained local translations rather than changing to Humanoid or replacing its skin.
Add ArcheryBowVisual with late visual synchronization after hit reactions. Center string point tracks the actual draw-hand grip while held; limb segments flex; nocked arrow tail stays on string. Release snaps the string to rest with decaying vibration and a brief reused wind streak. No damage from animation events.
Cache visual arrow launch positions from the bow and retain server endpoint/timing. Clear caches on projectile return and field transition. Add tiny camera follow-through without changing input yaw/pitch.
Validate exact string/hand/arrow-tail alignment, flex, fixed anchor, release recoil, idempotent refresh, projectile launch and hit-pose compatibility; render preparation/draw/anchor/release/recovery in Unity. Re-run existing bow, companion, hurt and pooling checks.

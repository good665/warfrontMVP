# Squad actions implementation plan

**Goal:** Make squad combat readable with Blender characters and authoritative melee, dodge and bombs.
**Architecture:** Blender FBX + Unity prefab, phase-driven presentation, isolated server squad rules.
**Spec:** docs/superpowers/specs/2026-11-08-squad-actions-design.md
**Constraints:** Preserve active Unity Assets, scenes and newer server integration; implement first and test last per user; no commits or publishing.

- [x] Create Blender generator, palette, weighted rig, six actions and FBX/source.
- [x] Implement server action phases, reach/body/LOS, dodge and bomb simulation; add behavior tests.
- [x] Build Unity imported prefab, consume server phases, smooth visual walk and add sword/reach/dodge/bomb presentation and control labels.
- [x] Run backend suite and Unity action/rig/regression checks; render poses and real computer gameplay.
- [x] Review, fix, install with backups/hash guards and report tested behavior.

Review focus: duplicate/retried inputs, missed sparse action snapshots, stationary dodge, walls/friendly fire, no root motion/state mutation, actor/effect cleanup and existing dungeon compatibility.

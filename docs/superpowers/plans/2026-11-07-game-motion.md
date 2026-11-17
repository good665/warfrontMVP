# Game motion and bomb presentation plan

Goal: Apply growing bomb imagery, moving rush trails and character motion across existing game modes.
Spec: User requests bomb growth/image, rush charging effect and moving character animations in all games.

Design: Keep existing pixel soldiers and deform their torso/leg regions for alternating steps, body bob and movement-facing. Track poses per actor, once per rendered frame. Freeze pose on game pause. Rush trails appear only when moving. Bomb art is a new transparent 2x2 sheet (normal/hot/fire/smoke) inside the existing visible danger circle; collision radius and all game rules remain unchanged. Drone rotors and hover animate; stationary training modes and duel/PvE show a breathing commander avatar.

- [x] Add portable motion/bomb frame tests and observe failure before implementation.
- [x] Generate bomb sheet; add presentation classes and integrate survival, arena, tutorial, stationary training and drone screens. Stage from current active code, not legacy copies.
- [x] Validate motion freezes, duplicate GUI sampling, idle/rush gating, direction and teleport behavior, bomb phase progression and original simulation invariants.
- [x] Unity compile/import/regressions and source parity; review and install under active Assets with backups. Preserve user scenes/configuration.

Review correction: use preserved WalkingPose for Lean, not active Moving; failing pause-position test confirmed the issue before correction. Final review has no blockers. Editor preview visually inspected across time; restarted Play after source installation and verified normal connected lobby. No gameplay match or mobile device test.

Constraints: No movement speed, collision, input, score, server or replay changes. Read-only scene preview for visual inspection when Editor accessible. No commit/push or APK build requested.

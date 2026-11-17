# Player hit reaction verification
- Root cause: Actor applied a small root recoil, then SquadAction overwrote the root rotation and sampled the bow/charge animation; original hurt check omitted this final sampling stage.
- RED: SquadHurtPoseChecks failed Final action sampling erased hit recoil: hero_bow.
- New HeroHitReaction applies additive torso/head/arm/root pose in LateUpdate. Actor restores the previous additive pose before sampling; expiry/disable/reset restore it. Bow remains attached to the animated hand. Duration .32 seconds, visual only; no server movement, damage, input or charge state changes.
- GREEN: SquadHurtPoseChecks, PlayerHurtChecks, HeroBowChecks passed in Unity. Checks include bow/charge/release/bomb/idle, pose decay/reset/no accumulation, weapon attachment, own-HP feedback duplicate/healing/identity suppression and camera behavior.
- Rendered and visually inspected neutral/hit pose PNGs in Unity URP. Game restarted successfully and town rendered.
- Independent read-only review found no significant issues.
- Limit: regression tests invoke Sample directly to model LateUpdate; a real combat frame timing trace was not captured.
- Backup: C:/Users/good6/AppData/Local/Temp/warfront-hurt-backup-20261111-131931.
- No backend changes or backend test rerun required.

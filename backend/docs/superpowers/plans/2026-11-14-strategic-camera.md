# Warcraft-style headquarters battle view

User approved replacing the game view with the elevated fixed view shown in the demo. Apply to computer and human headquarters battles; do not promote the prototype tiger rig or change server rules.

- [ ] Add and observe failing Unity checks for orthographic 55° pitch / 45° yaw, stable portal zoom, pointer/ground projection round trips, and visible unlocked cursor.
- [ ] Add strategic camera and inverse ground projection. Follow the player at fixed angle; wheel zoom 7.5–14 with default 11. Update screen-relative movement and pointer aiming/attack without mouse-look or cursor locking. Retain WASD, Q/E, Shift and visual Space jump.
- [ ] Update battle guidance and preview to show actual game camera; hide obsolete look settings in strategic mode.
- [ ] Install guarded active Assets edits with backups. Run Unity checks, inspect actual battle renderer and verify UI/world input separation; review implementation and record limitations. No backend changes or prototype rig integration.

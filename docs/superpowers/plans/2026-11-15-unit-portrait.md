# Unit portrait implementation plan

Goal: Display the selected unit bust in a live RawImage with an isolated studio and idle motion.
Architecture: Keep existing RetroFantasyScene portrait RenderTexture ownership. Copy visual hierarchy only into UnitPortraitStudio; bind the current hero or selected squad representative from GameBootstrap.
Tech: Unity 6000.3.23f1, URP 17, uGUI.
Approved approach: User selected immediate implementation of separate studio + RawImage.

- [x] Create visual-only studio with private layer 29, key/fill/rim lights, frontal bust framing, sampled Idle and additive breathing/head motion.
- [x] Preserve existing equipment portrait; connect selection and layout/lifecycle to a noninteractive RawImage at design coordinates (926,594,86,112).
- [x] Validate compile, source isolation, selection changes, no-source clearing, motion, rendering and cleanup with an Editor validation entry point and capture.

Constraints: Active Unity files belong under C:/Users/good6/WarfrontMVP/Assets. Preserve original files and meta files. Stage changes here before permission to install outside workspace.
Review focus: no gameplay scripts copied; no world/portrait light spill; dead/missing selected units clear; viewport resize and menu hiding; owned meshes/materials/RT are released.


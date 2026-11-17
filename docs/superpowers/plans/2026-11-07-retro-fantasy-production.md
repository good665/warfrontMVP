# Retro fantasy asset production

User direction: create a reusable skill using Kenney Retro Fantasy Kit as reference, produce 3D model, texture and rig, continue the previously recommended 3D town main screen. User explicitly requests proceeding rather than another design discussion.

Architecture: import official CC0 modular environment FBX and original pixel textures. Generate an original stylized adventurer as editable Unity mesh assets, UV texture PNG, weighted Generic skeleton, animation clips and prefab using an Editor builder. This does not produce a Blender file or an FBX character. Display actual meshes using a dedicated camera/render texture both in the town lobby and MMO field; preserve authoritative server coordinates/input and existing UI routes.

- [x] Inspect official kit, native model formats and DCC availability. Retro kit contains environment modules and textures, not a supplied character rig. Blender not found in PATH or standard install location.
- [x] Skill behavioral baseline: independent agent correctly distinguishes rig from bones-only and checks live Unity integration. No baseline discipline failure; author a concise reference/tool skill rather than invented prohibitions.
- [x] Create and validate reusable `unity-retro-fantasy` skill with asset builder and import/rig QA reference; install in the personal skills directory.
- [x] RED: Editor checks reject missing hero prefab; test skin weights/bind poses, animated deformations and model material references.
- [x] GREEN: native kit import, original textured and weighted hero + idle/walk/attack/dodge clips; retain reproducible sources.
- [x] Add actual 3D town lobby and model-based MMO rendering while retaining screen-coordinate aim and all server state.
- [x] Compile, run native Unity asset checks, review with fresh agent, verify visuals and routes in the active project; record actual results and limitations.

Isolation: stage files under `.tools/fantasy-town/staged`, validate in the existing temporary Unity project, back up changed active files before approved installation. Do not modify user scenes/settings/packages or legacy workspace Assets. Do not auto-commit or push.

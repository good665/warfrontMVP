# Fantasy town 3D lobby plan

Goal: Replace the military-image main screen with a real 3D town using the user's selected Kenney Fantasy Town Kit reference, while retaining MMORPG entry/profile/inventory/party functionality.
Architecture: native imported models arranged into a runtime town, isolated layer/camera/light and render texture integrated into the existing safe-area IMGUI screen. Separate 3D presentation from all server/gameplay rules. Existing scenes and project rendering settings stay intact.
Tech Stack: Unity 6000.3.23f1, C#/IMGUI, FBX/OBJ models from Kenney Fantasy Town Kit 2.0.
Spec: user explicitly supersedes the previous preserve-main-screen requirement and selects https://kenney.nl/assets/fantasy-town-kit as the new main-screen direction.

- [x] Retrieve official kit, inspect included model formats, scale, palette and license.
- [x] Validate native model import/materials and town renderer lifecycle with failing checks before implementation.
- [x] Build a composed 3D town with plaza/roads, distinct functional buildings, trees and warm lighting. Add projected building labels and readable fantasy UI; map to existing MMO zones/equipment/profile/party.
- [x] Verify import, route mapping, camera/hit rectangles and resource cleanup; compile and inspect Unity screen, fix visual issues, install with backups and record evidence.

Constraints: actual 3D mesh assets rather than a replacement background PNG; no account reset, server balance change or paid purchase; maintain source CC0 license/provenance with imported assets. Preserve user scenes/packages/settings and avoid hot reload while Play is running.

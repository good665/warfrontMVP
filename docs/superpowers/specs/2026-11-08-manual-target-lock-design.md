# Manual enemy target lock

Approved in conversation: manual lock rather than automatic attack-time selection. Tab and a touch-friendly Target button toggle the closest-to-screen-centre visible living enemy. Camera yaw smoothly follows the target; existing aim coordinates point at the target. Movement and dodge remain camera-relative. Selected enemy receives an amber bracket and target status. Pressing the control again unlocks, with no automatic switching.

Implementation choices: acquire within 600 server units (12 Unity units); retain within 800 units (16 Unity units). Only on-screen enemies without a server-obstacle line-of-sight obstruction may be acquired. Death, disappearance, obstruction, range exit, player death, region/instance changes, connection loss/staleness, menus, focus loss and leaving the field clear the lock. While locked, horizontal manual look yields to target tracking; vertical look and zoom remain available. Esc releases lock and cursor.

Alternatives: automatic selection on attack reduces input but can select an unintended enemy; manual selection preserves player intent and was chosen. No damage, range, cooldown, reward or backend rules change. Client sends ordinary aim coordinates to the authoritative server.

Preserve active Unity Assets, existing scene/meta files, accounts, and lobby. Verify with native Unity checks and Play Mode rendering in the existing isolated temporary validation project, then install only changed files with backups and original-hash guards. Mobile hardware checks must be reported separately.

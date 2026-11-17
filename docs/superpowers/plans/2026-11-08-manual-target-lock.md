# Manual target lock implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline. Steps use checkbox syntax for tracking.

**Goal:** Add the approved manual enemy lock to third-person combat.

**Architecture:** A focused GameBootstrap partial owns target selection/lifecycle and camera/aim assistance. Existing input and presentation call it; the server remains authoritative.

**Tech Stack:** Unity 6000.3.23f1, C#, Input System, native editor verification.

**Spec:** docs/superpowers/specs/2026-11-08-manual-target-lock-design.md

## Global constraints

- Active destination C:/Users/good6/WarfrontMVP/Assets; never use legacy workspace Unity code.
- Preserve scene/meta files and server rules. No commit/push.
- Stage and verify in isolated Temp/WarfrontWidgetValidation before installation.

## Review focus

- Centrality wins over distance; enemies behind camera/walls cannot be selected.
- Tab/GUI button toggles once and never triggers an attack.
- Death, range, region, connection/focus/menu transitions cannot retain stale locks.
- Aim follows live authoritative target coordinates and ordinary movement remains unchanged.
- Camera smoothing handles 0/360 wrapping and maintains existing wall/floor avoidance.

### Task 1: Target selection and lifecycle

Files: new Assets/script/MmoTargetLock.cs; new Assets/Editor/TargetLockChecks.cs.

- [x] Add native behavior checks using real GameBootstrap/RetroFantasyScene, reflection only for existing private gameplay state. Verify missing feature fails before implementation.
- [x] Implement selection, toggle, validity, line of sight, clear and target aim methods. Use 600 acquire / 800 retain range.
- [x] Check centre priority, behind camera, dead/absent enemies, wall obstruction, stale connection, menus and instance changes.

### Task 2: Input, camera and visual integration

Files: Assets/script/MmoView.cs, DungeonFirstPersonView.cs; new partial from Task 1.

- [x] Wire Tab and a dedicated 120x80 target button; run tracking before network-send throttling.
- [x] Smooth yaw toward target while retaining pitch/zoom; use exact target position for input aim.
- [x] Draw target brackets/status and update field and guide instructions.
- [x] Run TargetLockChecks.Run and existing ThirdPersonChecks.Run in Unity batch mode; run Play Mode render and inspect screenshot.
- [x] Review changes; install changed files with backups/hash guard under required filesystem approval; confirm active Editor imports cleanly.

## Execution ledger

- User approved displayed manual-lock design. Implementation details above are builder choices.
- Existing temporary Unity project supplies isolation without a backend Git worktree; active Unity project is outside backend repository.
- No further design approval requested: existing explicit authorization covers implementation.

- Task 1 complete: implementation initially absent (RED), then native lifecycle/selection checks PASS.
- Task 2 complete: native regression, real Play Mode HUD and Input System Tab integration PASS; independent review had no must-fix issues. Active Editor button lock/unlock and lobby return observed.
- Installed with hash guards/backups; final active files match validated isolated files byte-for-byte.
- Ruling: no merge/commit menu because Unity Assets are outside the backend Git repository; requested result is applied locally.
- Known verification limits: OS-injected Tab events were inconclusive; native Input System events passed. Mobile hardware/new APK not run.

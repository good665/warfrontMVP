# Vertical battlefield and opposite-end portals

Spec: user confirmed vertical maps and crossing to the opposite portal before advancing again. Prior 5-floor match rules remain.

- [x] Add regressions: taller-than-wide dimensions; upward gate only at top wall, downward only at bottom; upward arrival at bottom and downward arrival at top; waiting/repeated fresh input cannot advance at arrival gate; minions/bot route across the floor.
- [x] Set map 2400×3600. Top gate (1200,35) leads up one floor to (1200,3565), bottom gate leads down to top. Preserve delayed fade, floor bounds, bidirectional return and replay rejection. Move HQ/spawns/camps/dragon into the vertical map, update input bounds and snapshots.
- [x] Make Unity ground/walls/camera bounds derive from snapshot dimensions. Render portals from server metadata flush with end walls; retain inactive end walls at floors 1/5. Update guidance, Editor geometry checks and live HTTP navigation to cross each complete floor.
- [x] Install hash-guarded active Assets changes with backups. Run full backend suite, real HTTP route traversal and Unity compile/render checks, independent review, document actual results.

Execution: inline. Existing workspace and active Assets retained; no unrelated branch/data changes. User explicitly confirmed the concrete movement design.

Verification: failing new regressions observed before implementation; final full pytest 393 passed in 64.78s. Isolated real HTTP server completed 5→4→3→2→1 by ordinary movement across each map and returned matching participant snapshots/result. First center-line traversal failed after meeting fighting minion waves; the successful route uses the eastern flank with ordinary healing skill inputs, without modifying server positions, HP or time. Unity compile and extended integration checks passed: vertical ground, directional end-wall portals, top/bottom arrival camera boom >=3.5, prior character/input checks. Editor overview and third-person screenshots inspected; solid wall pieces behind gates were replaced with framed openings and camera bounds split beside them to prevent portal occlusion and arrival clipping. Independent reviewer found no Important server/navigation issue and flagged the subsequently fixed camera geometry concern.

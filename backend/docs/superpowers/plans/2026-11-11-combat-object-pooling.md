# Combat object pooling implementation plan
Goal: Implement the approved projectile/effect pooling design.
Spec: ../specs/2026-11-11-combat-object-pooling.md
1. Add Unity editor regression checks: object identity reuse, arrow transform reset, bomb/ring reuse and team color reset, field transition reuse and bounded retention. Run against existing code and observe failure.
2. Add scene-owned bounded pools for arrows, bombs and rings; return live items before field deletion; reuse snapshot scratch buffers. Preserve authoritative gameplay.
3. Run new checks and existing CompanionAttackChecks using Unity 6000.3.23f1. Inspect compilation logs and changes. Record limitations.
Execution: inline; stage changes in backend/pooling-work, preserve originals and install only selected files into the active Unity project with filesystem approval. No commits requested.

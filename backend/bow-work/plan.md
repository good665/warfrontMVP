# Bow and charge-shot implementation
Scope: squad PvP and computer mode; preserve character mesh, bombs, dodge and existing pooling.
Normal shot: free-aim projectile, 700 range, 20 damage, .12 windup, .40 action, .55 repeat cooldown.
Q: server-timed charge capped at 1.2s; explicit press/held/release; release aims freely and launches 20..44 damage, 5s cooldown after release. Never autofire when capped.
Cancel on dodge, bomb, death, lost input or unavailable controls. Preserve short taps and release while a request is in flight.
Swept projectile collision hits first hostile body or wall, prevents tunnelling/friendly fire, respects invulnerability and map bounds. Same rules for bot.
Client: hero bow equipment/animation, Q hold control and gauge, model fields and clear labels. Test inputs, damage scaling, release exactly once, lifecycle and pooling. Verify actual Unity renderer.

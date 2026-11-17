# Companion attack visibility and timing fix

User reports idle allies in computer squad battles and requests actual bow/arrow and guard sword attacks. Investigation: companions currently apply damage directly without setting action state or facing, while client only animates action fields. Archery has no projectile and every ally holds the same sword/shield. Preserve restored original Human model, scenes and the removed ground attack range.

Guard: .55s original Attack animation, .16s windup and single target contact using range95+body radius and LOS. Archer: .65s draw/release/recovery, .25s windup, 320-range aimed arrow. Server projectile flies at900units/s (flight .12-.45s) to launch-time target position; apply15 damage once on arrival only if target is still within body+16 radius and visible/alive/not dodging/protected. Friendly fire disabled. Retain resolved projectile event .25s for sparse snapshots, then remove. Healer displays heal action and faces healed ally. Acquiring an attack target prefers a reachable visible target when no valid explicit focus target exists. Retreat remains nonattacking.

Client: role equipment only on squad companions. Original guard sword/shield stay, archer receives original-style curved wood bow/string and draw clip for the existing bones. Arrow mesh shaft/head/fletching follows authoritative flight; never applies damage. Both teams use same animation handling. No character replacement, no ground attack radius. Clean role/effect caches on actor removal/zone change.

Implement first, final backend+Unity native regression and actual computer-match rendering last per user preference. Stage all Unity edits in isolated validation project; install under active Assets only with backup and hash guards.

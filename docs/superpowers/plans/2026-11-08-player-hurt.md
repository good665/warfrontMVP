# Player hurt feedback plan

> **For agentic workers:** Inline implementation; user preference remains implementation first, final checks last.

**Goal:** Make receiving authoritative damage clearly visible and audible.

**Architecture:** Extend MmoCombatFeedback self pulses and RetroFantasyScene local presentation-only impact timer. Reuse existing audio settings and snapshot lifecycle.

**Tech Stack:** Unity 6000.3.23f1, C#, generated local AudioClip, existing Mini Dungeon models.

**Spec:** docs/superpowers/specs/2026-11-08-player-hurt-design.md

- [x] Implement damage amount, red vignette/streaks and dedicated rate-limited hurt sound.
- [x] Implement visual flinch/tint and bounded camera displacement/roll; clear on reset/region change.
- [x] Author and run final native checks for own damage versus initial/heal/other/same snapshots and camera/pose reset.
- [x] Render actual normal/hurt/recovered gameplay frames; inspect, review and fix defects.
- [x] Run existing Unity regressions; install with backups/hash guards and document results/limitations.

- Final native checks, dedicated audio PCM and existing Unity regressions passed. Real isolated MMO monster reduced HP100->80 and normal/impact/recovered frames were inspected.
- Independent code review found no important defects. Fixture account cleaned after process exit.
- Applied 3 files with backups/hash guards; final active bytes match tested sources. No backend rule change; no new APK/mobile or audio-device listening evaluation.

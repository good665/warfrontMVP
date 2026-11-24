# Zodiac Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Execute inline in the existing active Unity project, preserving assets.

**Goal:** Deliver 24 character-specific Q/E motions and server-driven PNG/FBX VFX.
**Architecture:** New SkillMotions FBX assets override only Skill/Ultimate. A runtime component owns the monkey staff; a scene partial consumes authoritative effect events and manages bounded visual instances.
**Tech Stack:** Unity 6000.3.23f1, C#, Blender 4.5, transparent PNG atlas.
**Spec:** ../specs/2026-11-22-zodiac-skills-design.md

## Global Constraints
- Active assets only under C:/Users/good6/WarfrontMVP/Assets; back up edited files.
- Preserve server damage, scenes, character skins and basic attacks.
- No visual root motion or colliders on effects.

## Review Focus
- Duplicate snapshots must not replay effects.
- Other floors and old fields must not retain effects.
- Character swaps and deaths must hide staff and stop stale poses.
- Model import scales and animation binding paths must match original rigs.
- Missing optional assets must not cause gameplay exceptions.

### Task 1: Generate inspectable PNG/FBX assets
- [x] Write validation for two distinct clips per character and weapon UV/mesh.
- [x] Produce SkillMotions.fbx per existing rig, staff and effect geometry FBX, source blend files and atlas.
- [x] Verify import, sampled skin deformation, stationary actor roots and visible motion phases in Unity.

### Task 2: Integrate motions and effects
- [x] Validate server action facing matches aimed effect facing.
- [x] Apply SkillMotions after existing Motions without replacing Attack; use explicit authored duration.
- [x] Add staff attachment and event-driven directional/radial/defensive effects with bounded cache and cleanup.
- [x] Verify all 24 effects, deduplication, floor/field cleanup and no actor movement.

### Task 3: Verify and render
- [x] Run related Unity checks and backend tests for changed behavior.
- [x] Render 24 Unity skill captures and a monkey phase strip; inspect and fix visible defects.
- [x] Report delivered paths and observed limits.

Validation: backend 391 passed; Unity Editor and actual Play mode checks passed. Independent review corrected event age and owner cleanup. Evidence: output/zodiac-skills-v2/verification.txt.

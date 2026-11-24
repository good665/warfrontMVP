# Natural environment consistency

Approved intent: make the existing map blend naturally with the detailed zodiac characters, following the diagnosed mismatch. Preserve characters, gameplay, collisions and map layout.

Approach: retain the existing PBR ground set; warm and compress the gravel contrast in the terrain shader, reduce repetition with coherent multi-scale sampling, use the supplied dirt roughness/AO, soften normals and grade grass to the same palette. Replace harsh 32px point-filtered fallback appearance with smooth mipmapped detail and align plaza stone tint/normal strength. No new online assets or generated-image dependencies.

1. [x] Capture an unchanged map/character baseline in Unity; observe missing roughness-input check fail.
2. [x] Back up and edit GroundSplat.shader and RetroRuneEnvironment.cs; import roughness/AO as linear repeat textures.
3. [x] Verify actual terrain material inputs, import flags, shader compilation and continuity; capture identical Unity views after changes.
4. [x] Visually compare character/ground and map views, review code, record evidence and limitations.

Additional root cause found in visual QA: QuarterCamera's fixed 150m distance exceeded active URP shadowDistance=50m. Added a failing close-view shadow-range check and changed camera distance to Max(22, size*1.8+12), preserving orthographic framing. Projection/picking round-trip passed. Actual final Unity capture shows character/building shadows.

Final evidence: PASS after 2026-11-21T22:13:35, six before/after captures under active Assets/ArtSources~/NaturalGround_v1/Verification. Independent shader/resource review and focused camera review found no material issues. No Android device performance measurement; screenshot verification used the existing squad-map JSON fixture. Existing source images, character assets, map layout and collision rules preserved.

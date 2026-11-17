# Unit portrait integration

Runtime code is installed in C:/Users/good6/WarfrontMVP/Assets/script.

- UnitPortraitStudio.cs copies only transform/mesh/material data. Portrait layer 29 is reserved by the studio; existing world visuals stay on layer 30. Key/fill/rim lights affect only the portrait layer. Existing main lighting is unchanged.
- UnitPortraitHud.cs adds an automatic noninteractive ScreenSpaceOverlay RawImage. It follows the existing UiOrigin/UiScale safe-area layout. Design rect: (926,594,86,112); camera output: 384x512.
- Selected strategy squads use the first living member. Default/all selections and five-floor combat use the current player. Dead/missing targets clear the studio.
- The equipment panel shares the same RenderTexture and refreshes changed helmet geometry/materials while open.
- Idle clips are sampled independently from combat state. Additive breathing and head motion use unscaled time, with a reset every sample to prevent cumulative deformation.
- Runtime lights, display hierarchy, copied materials/static meshes and RenderTextures are owned by the presentation hierarchy and released on destruction.

Verification: Warfront > Validate Unit Portrait. Creates a temporary PreviewScene, checks four representative prefabs, 600 repeated Idle samples, selection resolution, HUD texture/raycast properties, equipment refresh, no-target clearing and initialization/teardown. PNG captures and result.txt go to %TEMP%/WarfrontPortraitValidation.

Visual tuning: UnitPortraitStudio.Initialize contains light colors/intensities; FrameBust controls upper-chest crop and head-width margin; SampleIdle controls motion amplitudes. No extra Inspector setup is required on existing GameBootstrap scenes.

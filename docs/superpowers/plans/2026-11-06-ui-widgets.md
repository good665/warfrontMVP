# WARFRONT UI widgets implementation plan

Goal: Apply the approved generated military pixel widgets to the active Unity UI.
Architecture: Preserve IMGUI input and layout; cache atlas slices and a cloned GUISkin. Restore GUI state after rendering. Existing sprites and scenes remain intact.
Spec: User requested applying the generated button, panel, status bar and icon sheet to WarfrontMVP.

- [x] Add widget asset/import and runtime slice checks; confirm missing implementation fails.
- [x] Add WidgetArtView.cs; apply common buttons/panels, lobby resource icons and training icons. Preserve fallback rendering and disabled controls.
- [x] Compile active runtime and run Unity import/regression checks. Record limitations.
- [ ] Visually inspect rendered UI: preview opens, but computer-use capture does not expose its contents.

Constraints: Active Assets only; preserve .meta, scenes, packages, networking and simulation. Back up edited files before install. No automatic commit or push.

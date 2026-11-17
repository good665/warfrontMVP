# Blender Skill Visuals

Authored for the existing MiniDungeon Human rig with Blender 4.5.10.
The original Human prefab, meshes, textures and source FBX are preserved.

- SkillVisuals.blend: editable source with existing character rig, authored Heavy/Throw/Dodge actions, Bomb and Blast meshes.
- SkillActions.fbx: baked animated rig export.
- build_skill_visuals.py: reproducible authoring/export script; run Blender --background --python <script> -- <output-directory>.
- Resources/SkillVisuals/Source/SkillActions.json: Blender-sampled local transforms on the original Unity transform paths. BlenderSkillImport builds legacy .anim clips from these samples.
- Bomb.fbx / Blast.fbx: original low-poly iron grenade, shockwave, core and fragments.

Animation times match authoritative squad states: Heavy .55 s (contact .20-.43), Throw .30 s (release .12), Dodge .22 s.
Root offsets animate the visual skeleton only. Server actor movement, damage, cooldowns and invulnerability remain authoritative.
The original character is an existing project asset; retain its existing license/provenance. Newly authored skill tracks and bomb/effect geometry were created for this project.

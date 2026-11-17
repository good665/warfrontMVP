import bpy
import sys
from pathlib import Path
source,target=[Path(x).resolve() for x in sys.argv[sys.argv.index('--')+1:]]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
strip=scene.sequence_editor_create().strips.new_movie('Encoded comparison',str(source),channel=1,frame_start=1)
assert strip.frame_duration==240,strip.frame_duration
scene.view_settings.view_transform='Standard';scene.render.use_sequencer=True
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(target);scene.frame_set(109)
bpy.ops.render.render(write_still=True)
print('PASS: decoded encoded MP4 frame109; duration240frames')

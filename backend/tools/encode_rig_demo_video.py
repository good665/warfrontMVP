"""Encode rendered Unity comparison frames using Blender's bundled FFmpeg."""
import bpy
import sys
from pathlib import Path

frames,output=[Path(x).resolve() for x in sys.argv[sys.argv.index('--')+1:]]
files=sorted(frames.glob('frame-*.png'))
if len(files)!=240:raise RuntimeError('Expected all 240 rendered frames')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.fps=24;scene.frame_start=1;scene.frame_end=len(files)
editor=scene.sequence_editor_create()
strip=editor.strips.new_image('Warcraft-style rig comparison',str(files[0]),channel=1,frame_start=1)
for file in files[1:]:strip.elements.append(file.name)
strip.frame_final_duration=len(files)
scene.render.use_sequencer=True
scene.view_settings.view_transform='Standard'
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='HIGH';scene.render.ffmpeg.ffmpeg_preset='GOOD'
scene.render.filepath=str(output)
bpy.ops.render.render(animation=True)
print('VIDEO_READY',output,flush=True)

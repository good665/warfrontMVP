"""Inspect the prototype's imported-source poses, without editing game assets."""
import bpy
import math
import sys
from pathlib import Path
from mathutils import Vector

source, output = [Path(x).resolve() for x in sys.argv[sys.argv.index('--')+1:]]
bpy.ops.wm.open_mainfile(filepath=str(source))
output.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.world.color=(.16,.16,.16)
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='Standard'
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.005))
floor=bpy.context.object
mat=bpy.data.materials.new('Stage');mat.diffuse_color=(.10,.16,.13,1);floor.data.materials.append(mat)
for location,power,size in [((2,-3,6),650,5),((-3,-1,4),350,4)]:
    data=bpy.data.lights.new('Softbox','AREA');data.energy=power;data.shape='DISK';data.size=size
    light=bpy.data.objects.new('Softbox',data);scene.collection.objects.link(light);light.location=location
    light.rotation_euler=(Vector((0,0,.5))-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Isometric study');camera=bpy.data.objects.new('Isometric study',data);scene.collection.objects.link(camera)
camera.location=(3,-4,4);camera.rotation_euler=(Vector((0,0,.55))-camera.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=2.8;scene.camera=camera
rig=bpy.data.objects['TigerRig']
for name,phase in [('Walk',.25),('QSkill',.45),('EUltimate',.45)]:
    action=bpy.data.actions[name];rig.animation_data.action=action
    scene.frame_set(round(action.frame_range[0]+phase*(action.frame_range[1]-action.frame_range[0])))
    scene.render.filepath=str(output/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('POSE_RENDERED',name,flush=True)

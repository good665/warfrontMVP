"""Blender-authored skill actions for the existing MiniDungeon rig (not a replacement character)."""
import bpy, math, json, sys, re
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
project=Path(r'C:/Users/good6/WarfrontMVP/Assets')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(project/'Resources/MiniDungeon/Models/character-human.fbx'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
rig.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
# The source FBX's Blender coordinates map from Unity by (-x,-z,y).
C=Matrix(((-1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
Ci=C.inverted()
rest={'root':(None,(0,0,0)), 'torso':('root',(0,.17625,-.02375)),
      'arm-left':('torso',(-.09989677,.1115,.0115)), 'arm-right':('torso',(.09989677,.1115,.0115)),
      'head':('torso',(0,.16699998,.026388776)),
      'leg-left':('root',(-.083570965,.17625,-.02375)), 'leg-right':('root',(.083570965,.17625,-.02375))}
order=['root','torso','leg-left','leg-right','arm-left','arm-right','head']
def path(name):
 parent=rest[name][0]
 return path(parent)+'/'+name if parent else name

def unity_q(e):
 x,y,z=[math.radians(a) for a in e]
 return Quaternion((0,1,0),y)@Quaternion((1,0,0),x)@Quaternion((0,0,1),z)

def world_matrices(poses):
 matrices={}
 for name in order:
  e,offset=poses.get(name,((0,0,0),(0,0,0)))
  local=Matrix.Translation(Vector(rest[name][1])+Vector(offset))@unity_q(e).to_matrix().to_4x4()
  parent=rest[name][0];matrices[name]=matrices[parent]@local if parent else local
 return matrices
rest_world=world_matrices({})
for name in rig.data.bones.keys():
 expected=C@rest_world[name].translation
 actual=rig.matrix_world@rig.data.bones[name].head_local
 assert (expected-actual).length<.0001,(name,expected,actual)

def smooth(t):return t*t*(3-2*t)
def mix(a,b,t):return tuple(x+(y-x)*t for x,y in zip(a,b))
# Key poses are authored in the active rig's Unity-local axes; sampled in Blender at 100 Hz.
heavy=[(0,{}),(.12,{'torso':((0,-28,-8),(0,-.025,0)), 'arm-right':((-138,-65,-25),(0,.015,0)), 'arm-left':((-45,20,15),(0,0,0)), 'leg-left':((20,0,0),(0,0,0))}),
 (.20,{'torso':((8,-38,-10),(0,-.035,0)), 'arm-right':((-125,-75,-20),(0,.02,0)), 'arm-left':((-55,20,15),(0,0,0)), 'leg-left':((25,0,0),(0,0,0))}),
 (.34,{'torso':((22,48,8),(0,-.02,.015)), 'arm-right':((-82,85,25),(-.025,0,.035)), 'arm-left':((-35,-15,20),(0,0,0)), 'leg-right':((-18,0,0),(0,0,0))}),
 (.43,{'torso':((12,30,4),(0,-.01,0)), 'arm-right':((-55,75,32),(0,0,0)), 'arm-left':((-20,0,10),(0,0,0))}),(.55,{})]
throw=[(0,{}),(.08,{'torso':((0,-24,-8),(0,-.01,0)), 'arm-right':((-155,-20,-10),(0,.02,0)), 'arm-left':((-35,0,15),(0,0,0))}),
 (.12,{'torso':((15,18,0),(0,0,.015)), 'arm-right':((-95,8,5),(0,0,.03)), 'arm-left':((-20,0,12),(0,0,0))}),
 (.20,{'torso':((12,25,4),(0,0,.01)), 'arm-right':((-55,12,10),(0,0,0))}),(.30,{})]
dodge=[(0,{}),(.045,{'root':((0,0,0),(0,-.065,0)), 'torso':((62,0,0),(0,-.025,0)), 'head':((-28,0,0),(0,0,0)), 'arm-right':((-70,12,-22),(0,0,0)), 'arm-left':((-70,-12,22),(0,0,0)), 'leg-left':((-48,0,-8),(0,0,0)), 'leg-right':((48,0,8),(0,0,0))}),
 (.13,{'root':((0,0,-14),(0,-.055,0)), 'torso':((48,0,0),(0,-.015,0)), 'head':((-20,0,0),(0,0,0)), 'arm-right':((-55,10,-15),(0,0,0)), 'arm-left':((-55,-10,15),(0,0,0)), 'leg-left':((42,0,-6),(0,0,0)), 'leg-right':((-42,0,6),(0,0,0))}),(.22,{})]

def sample(keys,t):
 for i in range(len(keys)-1):
  if t<=keys[i+1][0]+1e-8:
   ta,a=keys[i];tb,b=keys[i+1];u=smooth(max(0,min(1,(t-ta)/(tb-ta))))
   return {n:(mix(a.get(n,((0,0,0),(0,0,0)))[0],b.get(n,((0,0,0),(0,0,0)))[0],u),mix(a.get(n,((0,0,0),(0,0,0)))[1],b.get(n,((0,0,0),(0,0,0)))[1],u)) for n in order}
 return {}
scene=bpy.context.scene;scene.render.fps=100
result={'provenance':'Authored and sampled in Blender 4.5 on original MiniDungeon Human hierarchy','clips':[]}
rig.animation_data_create()
for name,keys in [('Heavy',heavy),('Throw',throw),('Dodge',dodge)]:
 duration=keys[-1][0];act=bpy.data.actions.new(name);rig.animation_data.action=act;tracks={n:[] for n in order}
 for f in range(round(duration*100)+1):
  t=f/100;poses=sample(keys,t);world=world_matrices(poses)
  for n in order:
   e,offset=poses.get(n,((0,0,0),(0,0,0)));q=unity_q(e);p=Vector(rest[n][1])+Vector(offset)
   tracks[n].append([t,*p,q.x,q.y,q.z,q.w])
  for n in ['torso','leg-left','leg-right','arm-left','arm-right','head']:
   bone=rig.pose.bones[n];delta=C@world[n]@rest_world[n].inverted()@Ci
   bone.matrix=rig.matrix_world.inverted()@delta@rig.matrix_world@rig.data.bones[n].matrix_local
   bone.rotation_mode='QUATERNION';bone.keyframe_insert('location',frame=f+1);bone.keyframe_insert('rotation_quaternion',frame=f+1);bone.keyframe_insert('scale',frame=f+1)
  bpy.context.view_layer.update()
 act.use_fake_user=True
 result['clips'].append({'name':name,'duration':duration,'tracks':[{'path':path(n),'keys':[{'time':row[0],'position':row[1:4],'rotation':row[4:]} for row in tracks[n]]} for n in order]})
(out/'SkillActions.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
# Real FBX export accompanies the exact-path sampled animation for reproducibility.
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
 if o.type in {'ARMATURE','MESH'}:o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(out/'SkillActions.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,axis_forward='-Z',axis_up='Y',bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
# Palette and static skill meshes, with no changes to the original character.
colors=[(.09,.13,.20,1),(.27,.34,.44,1),(.70,.52,.20,1),(1,.34,.035,1),(1,.82,.20,1),(.35,.20,.09,1)]
image=bpy.data.images.new('SkillPalette',width=6,height=6,alpha=True);image.pixels=[v for y in range(6) for c in colors for v in c];image.filepath_raw=str(out/'SkillPalette.png');image.file_format='PNG';image.save()
mat=bpy.data.materials.new('SkillPalette');mat.use_nodes=True;tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest';mat.node_tree.links.new(tex.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
def color_mesh(o,index):
 o.data.materials.clear();o.data.materials.append(mat)
 if not o.data.uv_layers:o.data.uv_layers.new()
 for uv in o.data.uv_layers.active.data:uv.uv=((index+.5)/6,.5)
 return o
parts=[]
bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.21,location=(0,0,0));parts.append(color_mesh(bpy.context.object,0))
for z,r,depth,ci in [(.175,.13,.065,2),(.24,.035,.09,5),(.30,.045,.035,4)]:
 bpy.ops.mesh.primitive_cylinder_add(vertices=10,radius=r,depth=depth,location=(0,0,z));parts.append(color_mesh(bpy.context.object,ci))
# Forged band around the grenade body.
bpy.ops.mesh.primitive_torus_add(major_radius=.20,minor_radius=.018,major_segments=12,minor_segments=4);parts.append(color_mesh(bpy.context.object,1))
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();bomb=bpy.context.object;bomb.name='BlenderBomb';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.ops.export_scene.fbx(filepath=str(out/'Bomb.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',bake_anim=False)
bomb.location.x=2
# Blast mesh components retain names so Unity can animate expansion and fade.
bpy.ops.mesh.primitive_torus_add(major_radius=.965,minor_radius=.035,major_segments=48,minor_segments=4,location=(0,0,.035));wave=color_mesh(bpy.context.object,3);wave.name='Shockwave'
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.36,location=(0,0,.25));core=color_mesh(bpy.context.object,4);core.name='Core'
shards=[]
for i in range(12):
 angle=i*2*math.pi/12
 bpy.ops.mesh.primitive_cone_add(vertices=4,radius1=.07,radius2=0,depth=.30,location=(math.cos(angle)*.65,math.sin(angle)*.65,.18+(i%3)*.08));o=color_mesh(bpy.context.object,3 if i%2 else 4);o.rotation_euler=(math.sin(angle)*.8,-math.cos(angle)*.8,angle);shards.append(o)
bpy.ops.object.select_all(action='DESELECT')
for o in shards:o.select_set(True)
bpy.context.view_layer.objects.active=shards[0];bpy.ops.object.join();sparks=bpy.context.object;sparks.name='Sparks';scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
bpy.ops.object.select_all(action='DESELECT')
for o in [wave,core,sparks]:o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(out/'Blast.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',bake_anim=False)
for o in [wave,core,sparks]:o.location.x+=3.3
rig.animation_data.action=bpy.data.actions['Heavy'];scene.frame_start=1;scene.frame_end=56;scene.frame_set(35)
for im in bpy.data.images:
 if 'colormap' in (im.name+' '+im.filepath).lower():im.filepath=str(project/'Resources/MiniDungeon/Textures/colormap.png');im.reload()
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'SkillVisuals.blend'))
print('SKILL_VISUALS_CREATED: Heavy .55, Throw .30, Dodge .22; Bomb and Blast FBX; original character preserved',flush=True)



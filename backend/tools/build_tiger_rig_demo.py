"""Blender-only, isolated preview asset. Does not change the game's Zodiac assets."""
import bpy
import math
import sys
import struct
from pathlib import Path
from mathutils import Vector, Matrix, Euler

OUT = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

palette = [(1., .48, .07, 1), (.98, .85, .61, 1), (.055, .035, .035, 1),
           (1, .98, .91, 1), (.80, .27, .26, 1), (.95, .67, .12, 1), (.66, .25, .045, 1), (.08, .15, .19, 1)]
texture = bpy.data.images.new('Tiger palette', width=64, height=8)
texture.pixels[:] = [v for y in range(8) for x in range(64) for v in palette[x//8]]
texture.filepath_raw = str(OUT/'TigerPalette.png')
texture.file_format = 'PNG'
texture.save()
material = bpy.data.materials.new('Tiger preview palette')
material.use_nodes = True
node = material.node_tree.nodes.new('ShaderNodeTexImage')
node.image = texture
node.interpolation = 'Closest'
shader = material.node_tree.nodes.get('Principled BSDF')
material.node_tree.links.new(node.outputs['Color'], shader.inputs['Base Color'])
shader.inputs['Roughness'].default_value = .8

rest = {'Root': (0,0,0), 'Hips': (0,.24,.67), 'Spine': (0,0,.72),
        'Chest': (0,-.28,.74), 'Neck': (0,-.48,.88), 'Head': (0,-.67,.98), 'Jaw': (0,-.80,.88)}
parents = {'Hips':'Root', 'Spine':'Hips', 'Chest':'Spine', 'Neck':'Chest', 'Head':'Neck', 'Jaw':'Head'}
limbs = {}
for label, x, y in [('FrontL',-.245,-.33), ('FrontR',.245,-.33), ('HindL',-.25,.32), ('HindR',.25,.32)]:
    front = label.startswith('Front')
    upper, lower, paw = label+'Upper', label+'Lower', label+'Paw'
    rest[upper] = (x,y,.71 if front else .65)
    rest[lower] = (x,-.28 if front else .47,.39)
    rest[paw] = (x,-.40 if front else .34,.105)
    parents[upper] = 'Chest' if front else 'Hips'
    parents[lower], parents[paw] = upper, lower
    limbs[label] = upper,lower,paw
for i, p in enumerate([(0,.53,.74), (0,.78,.79), (0,1.0,.96), (0,1.12,1.12)]):
    rest['Tail'+str(i)] = p
    parents['Tail'+str(i)] = 'Hips' if i == 0 else 'Tail'+str(i-1)
rest = {k:Vector(v) for k,v in rest.items()}

armature = bpy.data.armatures.new('Tiger articulated preview skeleton')
rig = bpy.data.objects.new('TigerRig', armature)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name, point in rest.items():
    bone = armature.edit_bones.new(name)
    bone.head, bone.tail = point, point+Vector((0,0,.12))
for name,parent in parents.items(): armature.edit_bones[name].parent = armature.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front = True

vertices, faces, colors, weights = [], [], [], []
def body_weight(point):
    t = max(0., min(1., (.30-point.y)/.65))
    return {'Hips':1-t, 'Chest':t}

def oval(center, size, weight, color, sides=10, rings=6):
    center, size = Vector(center), Vector(size)
    start = len(vertices)
    for r in range(rings+1):
        latitude = math.pi*r/rings
        for s in range(sides+1):
            angle = math.tau*s/sides
            point = center+Vector((math.sin(latitude)*math.cos(angle)*size.x*.5,
                                  math.sin(latitude)*math.sin(angle)*size.y*.5,
                                  math.cos(latitude)*size.z*.5))
            vertices.append(tuple(point))
            colors.append(color)
            weights.append(weight(point) if callable(weight) else weight)
            if r<rings and s<sides:
                a = start+r*(sides+1)+s
                b = a+sides+1
                faces.extend(((a,b,a+1),(a+1,b,b+1)))

def segment(a, b, radius_a, radius_b, bone_a, bone_b, color):
    a,b = Vector(a),Vector(b)
    axis = (b-a).normalized()
    right = axis.cross(Vector((0,1,0)))
    if right.length < .01: right = axis.cross(Vector((1,0,0)))
    right.normalize()
    up = axis.cross(right).normalized()
    start = len(vertices)
    for ring in range(5):
        t = ring/4
        for i in range(11):
            angle = math.tau*i/10
            point = a.lerp(b,t)+(right*math.cos(angle)+up*math.sin(angle))*(radius_a*(1-t)+radius_b*t)
            vertices.append(tuple(point)); colors.append(color)
            # A broad blend around each elbow/knee, rather than a single rigid stick.
            mix = max(0.,min(1.,(t-.45)/.5))
            weights.append({bone_a:1-mix,bone_b:mix})
            if ring<4 and i<10:
                j = start+ring*11+i
                faces.extend(((j,j+1,j+11),(j+1,j+12,j+11)))

oval((0,.05,.71),(.66,1.04,.59),body_weight,0)
oval((0,-.30,.71),(.62,.46,.66),{'Chest':1},0)
oval((0,-.28,.55),(.44,.49,.32),{'Chest':1},1)
oval((0,.32,.66),(.66,.42,.53),{'Hips':1},0)
oval((0,-.49,.87),(.42,.36,.38),{'Neck':.7,'Chest':.3},0)
oval((0,-.69,1.0),(.56,.52,.48),{'Head':1},0)
oval((0,-.89,.91),(.44,.28,.27),{'Head':1},1)
oval((0,-1.045,.94),(.15,.08,.09),{'Head':1},2)
oval((0,-.94,.845),(.35,.20,.065),{'Head':.5,'Jaw':.5},2)
oval((0,-.91,.815),(.36,.26,.11),{'Jaw':1},1)
for side in (-1,1):
    oval((side*.23,-.61,1.205),(.18,.12,.19),{'Head':1},2)
    oval((side*.23,-.677,1.21),(.115,.025,.11),{'Head':1},1)
    oval((side*.235,-.85,1.055),(.11,.055,.085),{'Head':1},3)
    oval((side*.24,-.883,1.055),(.045,.025,.064),{'Head':1},2)
    oval((side*.23,-.844,1.105),(.17,.07,.045),{'Head':1},2)
    oval((side*.29,-.77,.93),(.14,.24,.19),{'Head':1},1)
    for i,y in enumerate((-.28,-.07,.14,.34)):
        stripe_start=len(vertices)
        oval((side*.313,y,.77),(.032,.085,.30 if i%2 else .37),body_weight,2,6,4)
        # Keep markings on the curved coat instead of rigid black fins above it.
        for v in range(stripe_start,len(vertices)):
            x,vy,vz=vertices[v]
            surface=.33*math.sqrt(max(.025,1-((vy-.05)/.52)**2-((vz-.71)/.295)**2))
            vertices[v]=(side*(surface+.012+(abs(x)-.313)*.15),vy,vz)
    for y,z in [(-.69,1.19),(-.55,1.13)]: oval((side*.13,y,z),(.09,.07,.04),{'Head':1},2,6,3)
for label,(upper,lower,paw) in limbs.items():
    segment(rest[upper],rest[lower],.125,.095,upper,lower,0)
    oval(rest[lower],(.21,.21,.21),{upper:.4,lower:.6},0)
    segment(rest[lower],rest[paw],.09,.08,lower,paw,0)
    oval(rest[paw]+Vector((0,-.045,-.015)),(.25,.33,.16),{paw:1},1)
    for toe in (-.065,0,.065):
        oval(rest[paw]+Vector((toe,-.18,-.01)),(.065,.055,.06),{paw:1},2,6,3)
for i in range(3):
    a,b = rest['Tail'+str(i)],rest['Tail'+str(i+1)]
    segment(a,b,.07-i*.012,.058-i*.012,'Tail'+str(i),'Tail'+str(i+1),0)
    oval(a.lerp(b,.55),(.12-i*.02,.065,.12-i*.02),{'Tail'+str(i):.5,'Tail'+str(i+1):.5},2,8,4)
oval(rest['Tail3'],(.09,.10,.13),{'Tail3':1},2)

mesh = bpy.data.meshes.new('Tiger continuous weighted volumes')
mesh.from_pydata(vertices,[],faces);mesh.update()
obj = bpy.data.objects.new('TigerPreviewMesh',mesh)
bpy.context.collection.objects.link(obj)
obj.data.materials.append(material)
uv = mesh.uv_layers.new(name='PaletteUV')
for polygon in mesh.polygons:
    for loop in polygon.loop_indices:
        uv.data[loop].uv = ((colors[mesh.loops[loop].vertex_index]+.5)/8,.5)
for name in rest: obj.vertex_groups.new(name=name)
for index, assignments in enumerate(weights):
    total = sum(assignments.values())
    for name,value in assignments.items():
        if value>0: obj.vertex_groups[name].add([index],value/total,'REPLACE')
modifier = obj.modifiers.new('Articulated deformation','ARMATURE');modifier.object=rig
obj.parent=rig

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)
def matrix_at(point, rotation=(0,0,0)):
    # Blender bones use local Y along the bone, even when authored along world Z.
    base=armature.bones['Root'].matrix_local.to_3x3().to_4x4()
    return Matrix.Translation(point) @ Euler(rotation).to_matrix().to_4x4() @ base
def solve_leg(hip,target,l1,l2,knee_forward):
    v=target-hip; d=min(l1+l2-.002,max(.01,v.length)); axis=v.normalized()
    bend=Vector((0,knee_forward,0));bend=(bend-axis*bend.dot(axis)).normalized()
    along=(l1*l1-l2*l2+d*d)/(2*d)
    return hip+axis*along+bend*math.sqrt(max(.0001,l1*l1-along*along))

scene=bpy.context.scene;scene.render.fps=30
rig.animation_data_create()
for action_name,frames in [('Idle',60),('Walk',30),('QSkill',36),('EUltimate',54)]:
    rig.animation_data.action=bpy.data.actions.new(action_name)
    for frame in range(1,frames+1):
        t=(frame-1)/(frames-1);scene.frame_set(frame)
        for p in rig.pose.bones: p.rotation_mode='QUATERNION';p.matrix_basis=Matrix.Identity(4)
        prep=smooth(t/.22)*(1-smooth((t-.35)/.55)) if action_name in ('QSkill','EUltimate') else 0
        motion=math.sin(math.tau*t)
        offset=Vector((0,.065*prep, -.045*prep))
        if action_name=='Walk':offset=Vector((0,0,.012*math.cos(math.tau*t*2)))
        if action_name=='Idle':offset=Vector((0,0,.006*motion))
        twist=math.radians((-16*prep+32*smooth((t-.25)/.22)*(1-smooth((t-.50)/.5))) if action_name=='QSkill' else 0)
        chest_raise=.085*smooth((t-.2)/.23)*(1-smooth((t-.72)/.28)) if action_name=='EUltimate' else 0
        for name in ('Root','Hips','Spine','Chest','Neck','Head','Jaw'):
            point=rest[name]+(Vector((0,0,0)) if name=='Root' else offset)
            if name in ('Chest','Neck','Head','Jaw'):point.z+=chest_raise
            pitch=math.radians(-20*prep) if action_name=='EUltimate' and name in ('Neck','Head','Jaw') else 0
            if action_name=='EUltimate' and name=='Jaw':pitch+=math.radians(25*prep)
            rig.pose.bones[name].matrix=matrix_at(point,(pitch,0,twist if name in ('Chest','Neck','Head','Jaw') else twist*.3))
            bpy.context.view_layer.update()
        for label,(upper,lower,paw) in limbs.items():
            hip=rest[upper]+offset+Vector((0,0,chest_raise if label.startswith('Front') else 0))
            foot=rest[paw].copy()
            if action_name=='Walk':
                phase=(t+(0 if label in ('FrontL','HindR') else .5))%1
                if phase<.6: foot.y+=.14*(1-2*phase/.6)
                else:
                    u=(phase-.6)/.4;foot.y+=-.14+.28*smooth(u);foot.z+=.10*math.sin(math.pi*u)
            if action_name=='QSkill' and label=='FrontR':
                keys=[(0,rest[paw]),(.24,Vector((.40,-.3,.53))),(.48,Vector((-.18,-.97,.54))),(1,rest[paw])]
                for (ta,pa),(tb,pb) in zip(keys,keys[1:]):
                    if ta<=t<=tb:foot=pa.lerp(pb,smooth((t-ta)/(tb-ta)));break
            if action_name=='EUltimate' and label.startswith('Front'):foot.x+=(-1 if label.endswith('L') else 1)*.025*prep
            l1=(rest[lower]-rest[upper]).length;l2=(rest[paw]-rest[lower]).length
            knee=solve_leg(hip,foot,l1,l2,1)
            q1=(rest[lower]-rest[upper]).rotation_difference(knee-hip)
            q2=(rest[paw]-rest[lower]).rotation_difference(foot-knee)
            base=armature.bones['Root'].matrix_local.to_3x3().to_4x4()
            rig.pose.bones[upper].matrix=Matrix.Translation(hip)@q1.to_matrix().to_4x4()@base
            bpy.context.view_layer.update()
            rig.pose.bones[lower].matrix=Matrix.Translation(knee)@q2.to_matrix().to_4x4()@base
            bpy.context.view_layer.update()
            rig.pose.bones[paw].matrix=matrix_at(foot)
            bpy.context.view_layer.update()
        for i in range(4):
            p=rest['Tail'+str(i)]+offset
            p.x+=.035*math.sin(math.tau*t+i*.45)
            rig.pose.bones['Tail'+str(i)].matrix=matrix_at(p,(0,math.radians(5*motion),-twist*.5))
            bpy.context.view_layer.update()
        bpy.context.view_layer.update()
        for bone in rig.pose.bones:
            bone.keyframe_insert('location',frame=frame)
            bone.keyframe_insert('rotation_quaternion',frame=frame)
            bone.keyframe_insert('scale',frame=frame)
    action=rig.animation_data.action
    action.use_fake_user=True

scene.frame_start=1;scene.frame_end=60;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TigerRigDemo.blend'))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'TigerRigDemo.fbx'),use_selection=True,
                         object_types={'MESH','ARMATURE'},add_leaf_bones=False,
                         bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,
                         axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL')
print('RIG_DEMO_READY',len(rest),'bones',len(vertices),'vertices',list(a.name for a in bpy.data.actions))

# A deterministic deformed-mesh cache makes the preview independent of FBX unit
# conversion. The editable .blend and weighted .fbx remain the source assets.
bone_names=list(rest)
with (OUT/'TigerPreview.bytes').open('wb') as cache:
    cache.write(b'TRD1')
    indices=[i for face in faces for i in face]
    cache.write(struct.pack('<iiiif',len(vertices),len(indices),len(bone_names),240,24.))
    for color in colors:cache.write(struct.pack('<ff',(color+.5)/8,.5))
    cache.write(struct.pack('<'+'i'*len(indices),*indices))
    for name in bone_names:
        cache.write(name.encode().ljust(64,b'\0'))
        cache.write(struct.pack('<i',bone_names.index(parents[name]) if name in parents else -1))
    for frame in range(240):
        time=frame/24
        action_name='Walk' if time<3 else 'QSkill' if time<6 else 'EUltimate'
        phase=(time/1.15)%1 if time<3 else max(0,min(1,(time-3.35)/2.15)) if time<6 else max(0,min(1,(time-6.35)/3.05))
        action=bpy.data.actions[action_name];rig.animation_data.action=action
        position=action.frame_range[0]+phase*(action.frame_range[1]-action.frame_range[0])
        scene.frame_set(int(position),subframe=position%1);bpy.context.view_layer.update()
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());deformed=evaluated.to_mesh()
        for vertex in deformed.vertices:
            p=vertex.co;cache.write(struct.pack('<fff',p.x,p.z,-p.y))
        for vertex in deformed.vertices:
            n=vertex.normal;cache.write(struct.pack('<fff',n.x,n.z,-n.y))
        for name in bone_names:
            p=rig.pose.bones[name].head;cache.write(struct.pack('<fff',p.x,p.z,-p.y))
        evaluated.to_mesh_clear()
print('PREVIEW_CACHE_READY',OUT/'TigerPreview.bytes',flush=True)

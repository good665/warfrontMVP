import bpy, bmesh, math, sys
from mathutils import Vector
T=r"C:/Users/good6/WarfrontMVP/Assets/Resources/SpaciousInteriors/Textures/"
OUT=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
mats={}
def mat(name, metal=0, rough=.6):
    m=bpy.data.materials.new(name); m.use_nodes=True
    b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    t=m.node_tree.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(T+name+'.png')
    m.node_tree.links.new(t.outputs[0], b.inputs['Base Color'])
    b.inputs['Metallic'].default_value=metal; b.inputs['Roughness'].default_value=rough
    mats[name]=m; return m
for n,mt,r in (('HI_Oak',0,.6),('HI_DarkTimber',0,.6),('HI_Iron',.8,.4)): mat(n,mt,r)
parts=[]
def box(name, m, cx,cy,cz, sx,sy,sz):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx,cy,cz)); o=bpy.context.object
    o.scale=(sx,sy,sz); o.name=name; o.data.materials.append(mats[m]); parts.append(o); return o
def disc(name, m, cx,cy,cz, r, d, verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=(cx,cy,cz), rotation=(math.pi/2,0,0))
    o=bpy.context.object; o.name=name; o.data.materials.append(mats[m]); parts.append(o); return o
W,D=1.0,.62   # classic domed treasure chest; front faces +Y (into the room, like the hanok furniture)
F=D/2; H=.5; R=D/2
def half_cyl(name, m, length, r, z, verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=length, location=(0,0,z), rotation=(0,math.pi/2,0))
    o=bpy.context.object; o.name=name; o.data.materials.append(mats[m])
    bm=bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(0,0,0), plane_no=(1,0,0), clear_outer=True)  # local X = world -Z
    bm.to_mesh(o.data); bm.free(); parts.append(o); return o
box('Body','HI_Oak',0,0,H/2+.03,W,D,H)
box('Base','HI_DarkTimber',0,0,.03,W+.04,D+.04,.06)
box('Rim','HI_DarkTimber',0,0,H+.02,W+.03,D+.03,.04)
half_cyl('Lid','HI_Oak',W,R,H+.04)
for x in (-W/2+.005, W/2-.005):
    o=half_cyl('LidCap','HI_DarkTimber',.03,R+.01,H+.04); o.location.x=x
# iron straps over the lid and down the body, corner plates, a big lock
for x in (-.3,.3):
    o=half_cyl('LidBand','HI_Iron',.07,R+.015,H+.04); o.location.x=x
    box('Band','HI_Iron',x,F+.008,H/2+.03,.07,.016,H)
    box('BandBack','HI_Iron',x,-F-.008,H/2+.03,.07,.016,H)
for x in (-W/2+.04, W/2-.04):
    for z in (.1,H-.04): box('Corner','HI_Iron',x,F+.01,z,.09,.02,.09)
box('LockPlate','HI_Iron',0,F+.015,H-.02,.16,.03,.2)
box('Hasp','HI_Iron',0,F+.012,H+.1,.08,.025,.14)
disc('Keyhole','HI_DarkTimber',0,F+.032,H-.04,.022,.01,12)
for x in (-1,1): disc('Handle','HI_Iron',x*(W/2+.006),0,H*.6,.06,.012,16).rotation_euler=(math.pi/2,0,math.pi/2)
bpy.ops.object.select_all(action='DESELECT')
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.join(); chest=bpy.context.object; chest.name='Chest'
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.cube_project(cube_size=1.0); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, apply_unit_scale=True, bake_space_transform=False,
    object_types={'MESH'}, mesh_smooth_type='FACE', path_mode='STRIP')
# preview render
sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE_NEXT'; sc.render.resolution_x=sc.render.resolution_y=640
w=bpy.data.worlds.new('w'); w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(.32,.28,.24,1); sc.world=w
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(50),0,math.radians(30))); bpy.context.object.data.energy=3
bpy.ops.mesh.primitive_plane_add(size=4); fl=bpy.context.object; fl.data.materials.append(mat('HI_Ondol'))
bpy.ops.object.camera_add(location=(1.6,2.7,1.8)); cam=bpy.context.object; sc.camera=cam
d=Vector((0,0,.42))-cam.location; cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
sc.render.filepath=OUT.replace('.fbx','_preview.png'); bpy.ops.render.render(write_still=True)
print("DIM", [round(v,3) for v in chest.dimensions], "MATS", [m.name for m in chest.data.materials])

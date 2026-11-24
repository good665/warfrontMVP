"""Low-poly 1:1 manor vehicles (Car, Bike, Bus) and the bus Portal in the hanok HI_* materials; 1 m = 1 cell, front = Blender +Y.
Portal.fbx: a frameless 'Glow' disc (material PortalGlow, origin at its centre) that Unity tints, spins and scales.

blender -b --factory-startup --python build_vehicles.py -- <out_dir> [preview.png]
Unity remaps the HI_* slots to Resources/SpaciousInteriors/Materials at runtime (VehicleModel).
"""
import bpy, math, sys
from mathutils import Vector
args = sys.argv[sys.argv.index('--')+1:]
OUT, PREVIEW = args[0], (args[1] if len(args) > 1 else '')
T = r"C:/Users/good6/WarfrontMVP/Assets/Resources/SpaciousInteriors/Textures/"
bpy.ops.wm.read_factory_settings(use_empty=True)
mats = {}
def mat(name, metal=0., rough=.6, emit=0.):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(T+name+'.png')
    m.node_tree.links.new(t.outputs[0], b.inputs['Base Color'])
    b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
    if emit: m.node_tree.links.new(t.outputs[0], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = emit
    mats[name] = m
for n, mt, r, e in (('HI_Oak', 0, .6, 0), ('HI_DarkTimber', 0, .6, 0), ('HI_Iron', .8, .4, 0), ('HI_Sage', 0, .6, 0),
                    ('HI_Paper', 0, .6, 0), ('HI_Ondol', 0, .6, 0), ('HI_Lantern', 0, .5, 2.)):
    mat(n, mt, r, e)
mats['PortalGlow'] = bpy.data.materials.new('PortalGlow')

def box(parts, m, c, s, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c, rotation=rot); o = bpy.context.object
    o.scale = s; o.data.materials.append(mats[m]); parts.append(o); return o
def cyl(parts, m, c, r, d, axis='X', verts=16):
    rot = dict(X=(0, math.pi/2, 0), Y=(math.pi/2, 0, 0), Z=(0, 0, 0))[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=c, rotation=rot)
    o = bpy.context.object; o.data.materials.append(mats[m]); parts.append(o); return o
def torus(parts, m, c, R, r, rot):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=c, rotation=rot, major_segments=24, minor_segments=8)
    o = bpy.context.object; o.data.materials.append(mats[m]); parts.append(o); return o
def wheel(parts, x, y, r, w):
    cyl(parts, 'HI_Iron', (x, y, r), r, w, 'X', 20); cyl(parts, 'HI_Oak', (x, y, r), r*.55, w+.02, 'X', 12)

def car():  # open-top wooden jeep, 2.0 x 1.0: the driver's upper body shows above the 0.8 m sides
    p = []
    box(p, 'HI_DarkTimber', (0, 0, .3), (.96, 1.9, .16))                  # chassis
    for x in (-.45, .45): box(p, 'HI_Oak', (x, -.05, .55), (.08, 1.5, .5))  # side boards
    box(p, 'HI_Oak', (0, -.78, .55), (.98, .08, .5))                       # tailgate
    box(p, 'HI_Sage', (0, .62, .55), (.9, .66, .4))                        # bonnet
    box(p, 'HI_Iron', (0, .97, .5), (.8, .04, .26))                        # grille
    for x in (-.3, .3): cyl(p, 'HI_Lantern', (x, .99, .62), .07, .04, 'Y', 12)  # headlights
    box(p, 'HI_Paper', (0, .27, .95), (.86, .03, .34))                     # windscreen
    box(p, 'HI_Ondol', (0, -.35, .5), (.8, .4, .14))                       # seat
    cyl(p, 'HI_DarkTimber', (0, .05, .8), .14, .04, 'Y', 16)               # steering wheel
    for x in (-.5, .5):
        for y in (-.6, .62): wheel(p, x, y, .25, .16)
    return p

def bike():  # 1.2 x 0.35 steam bike: thin from above, the rider sits on top
    p = []
    wheel(p, 0, .45, .3, .1); wheel(p, 0, -.45, .3, .1)
    box(p, 'HI_Iron', (0, 0, .42), (.08, .9, .08), (math.radians(-8), 0, 0))  # frame
    box(p, 'HI_Oak', (0, .12, .58), (.22, .4, .18))                        # tank
    box(p, 'HI_Ondol', (0, -.22, .56), (.2, .34, .08))                     # saddle
    cyl(p, 'HI_Iron', (0, .42, .62), .03, .4, 'Z')                         # fork
    cyl(p, 'HI_DarkTimber', (0, .38, .82), .025, .56, 'X')                 # handlebar
    cyl(p, 'HI_Lantern', (0, .52, .7), .06, .04, 'Y', 12)                  # lamp
    cyl(p, 'HI_Iron', (.14, -.3, .36), .05, .5, 'Y')                       # exhaust
    return p

def bus():  # 4.0 x 1.5 carriage bus with a glowing portal ring on its door (it only teleports)
    p = []
    box(p, 'HI_DarkTimber', (0, 0, .35), (1.5, 4.0, .2))
    box(p, 'HI_Sage', (0, 0, 1.05), (1.44, 3.9, 1.2))
    for y in (-1.3, -.6, .1, .8):
        for x in (-.73, .73): box(p, 'HI_Paper', (x, y, 1.3), (.02, .5, .45))  # windows
    box(p, 'HI_Paper', (0, 1.96, 1.3), (1.2, .02, .5))                     # windscreen
    box(p, 'HI_DarkTimber', (0, 0, 1.72), (1.56, 4.06, .14))               # roof
    box(p, 'HI_Oak', (0, 0, 1.86), (1.2, 3.4, .14))                        # roof rack
    box(p, 'HI_DarkTimber', (.73, 1.35, .95), (.04, .7, 1.0))              # door (east side, front)
    torus(p, 'HI_Lantern', (.78, 1.35, 1.0), .52, .06, (0, math.pi/2, 0))   # portal ring
    for x in (-.3, .3): cyl(p, 'HI_Lantern', (x, 2.01, .7), .08, .04, 'Y', 12)
    for y in (-1.3, 1.3):
        for x in (-.7, .7): wheel(p, x, y, .32, .2)
    return p

bpy.ops.object.select_all(action='DESELECT')
built = {}
for name, make, at in (('Car', car, -3.), ('Bike', bike, -.6), ('Bus', bus, 2.6)):
    parts = make()
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.join(); o = bpy.context.object; o.name = name
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.cube_project(cube_size=1.); bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.export_scene.fbx(filepath=f'{OUT}/{name}.fbx', use_selection=True, object_types={'MESH'}, apply_unit_scale=True, path_mode='STRIP', mesh_smooth_type='FACE')
    print('VEHICLE', name, [round(v, 2) for v in o.dimensions])
    o.select_set(False); o.location.x = at; built[name] = o
def portal():  # frameless: one 1 m glowing disc facing +Y, its rim just off the ground (Unity draws it 2x)
    bpy.ops.mesh.primitive_circle_add(vertices=40, radius=1., fill_type='TRIFAN', location=(0, 0, 1.03), rotation=(math.pi/2, 0, 0))
    g = bpy.context.object; g.name = 'Glow'; g.data.materials.append(mats['PortalGlow'])
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)  # origin stays at the disc centre
    uv = g.data.uv_layers.new(name='UVMap')  # centred planar UVs so Unity's swirl texture spins about the middle
    for loop in g.data.loops:
        co = g.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co.x / 2 + .5, co.z / 2 + .5)
    bpy.ops.object.select_all(action='DESELECT'); g.select_set(True)
    bpy.ops.export_scene.fbx(filepath=f'{OUT}/Portal.fbx', use_selection=True, object_types={'MESH'}, apply_unit_scale=True, path_mode='STRIP', mesh_smooth_type='FACE')
    print('PORTAL', [round(v, 2) for v in g.dimensions])
    g.select_set(False); g.location.x = 6.
portal()
if PREVIEW:
    sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE_NEXT'; sc.render.resolution_x, sc.render.resolution_y = 960, 540
    w = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.35, .32, .28, 1); sc.world = w
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(50), 0, math.radians(35))); bpy.context.object.data.energy = 3
    bpy.ops.mesh.primitive_plane_add(size=20); bpy.context.object.data.materials.append(mats['HI_Ondol'])
    bpy.ops.object.camera_add(location=(7.5, 9.5, 6.5)); cam = bpy.context.object; sc.camera = cam
    cam.rotation_euler = (Vector((0, 0, .5)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = PREVIEW; bpy.ops.render.render(write_still=True)

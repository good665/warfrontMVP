"""Central cathedral (CC-BY-4.0 "Low Poly Medieval Gothic Church" by lexferreira89, Sketchfab) for the squad plaza.

blender -b --factory-startup --python build_cathedral.py -- <scene.gltf> <out.fbx>
Cuts an arched opening the width of the nave through both end walls (the server nave runs end to end),
splits the roof tiles into their own 'Roof' object (Unity hides it while the hero is inside) and turns the
front (glTF +X) to Blender -Y like the manor, keeping real-world metres (1 m = 1 cell).
"""
import bpy, math, sys
from mathutils import Vector, Matrix
src, out = sys.argv[sys.argv.index('--')+1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in meshes:  # bake the glTF empties' transforms into the meshes
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
for o in [o for o in bpy.context.scene.objects if o.type == 'EMPTY']: bpy.data.objects.remove(o)
walls = next(o for o in meshes if o.data.materials[0].name == 'pedra'); walls.name = 'Walls'
roof = next(o for o in meshes if o.data.materials[0].name == 'telha'); roof.name = 'Roof'
for o in meshes:
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True); o.select_set(False)

HALF, SPRING = 2.05, 4.0   # nave half width (interior measured from the model) and arch springing height
def cutter(x0, x1):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0+x1)/2, 0, (SPRING-.5)/2)); b = bpy.context.object
    b.scale = (x1-x0, HALF*2, SPRING+.5)
    bpy.ops.mesh.primitive_cylinder_add(radius=HALF, depth=x1-x0, location=((x0+x1)/2, 0, SPRING), rotation=(0, math.pi/2, 0), vertices=32)
    return [b, bpy.context.object]
cutters = cutter(-19, -15.2) + cutter(7.0, 11)
for c in cutters:
    m = walls.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.solver = 'EXACT'; m.use_hole_tolerant = True; m.use_self = True; m.object = c
bpy.context.view_layer.objects.active = walls
for m in list(walls.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)
for c in cutters: bpy.data.objects.remove(c)

def clear_through():
    dg = bpy.context.evaluated_depsgraph_get(); blocked = []
    for y in (-1.6, 0, 1.6):
        for z in (.3, 1.5, 3.0):
            hit = bpy.context.scene.ray_cast(dg, Vector((-30, y, z)), Vector((1, 0, 0)), distance=60)
            if hit[0]: blocked.append((y, z, round(hit[1].x, 2)))
    return blocked
assert not clear_through(), clear_through()  # walkable end to end along the nave

rot = Matrix.Rotation(-math.pi/2, 4, 'Z')  # front (+X) to -Y, then centred on the footprint
for o in (walls, roof): o.data.transform(rot)
pts = [v.co for o in (walls, roof) for v in o.data.vertices]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
for o in (walls, roof): o.data.transform(Matrix.Translation((-(lo.x+hi.x)/2, -(lo.y+hi.y)/2, -lo.z)))
print('CATHEDRAL_SIZE', [round(v, 2) for v in hi-lo], 'FRONT_Y', round(min(v.co.y for v in walls.data.vertices), 2))
for o in (walls, roof): o.select_set(True)
bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={'MESH'}, apply_unit_scale=True, path_mode='STRIP', mesh_smooth_type='FACE')

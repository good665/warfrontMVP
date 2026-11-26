"""Preview-only: 5 alternative Car/Bike/Bus concept sets in the hanok HI_* materials (same footprints as build_vehicles.py).
Writes <out_dir>/concept_<n>.png per set; exports nothing into Unity.

blender -b --factory-startup --python preview_vehicle_concepts.py -- <out_dir>
"""
import bpy, math, sys
from mathutils import Vector
OUT = sys.argv[sys.argv.index('--')+1:][0]
T = r"C:/Users/good6/WarfrontMVP/Assets/Resources/SpaciousInteriors/Textures/"
mats = {}

def setup_mats():
    for n, mt, r, e in (('HI_Oak', 0, .6, 0), ('HI_DarkTimber', 0, .6, 0), ('HI_Iron', .8, .4, 0), ('HI_Sage', 0, .6, 0),
                        ('HI_Paper', 0, .3, 0), ('HI_Ondol', 0, .6, 0), ('HI_Lantern', 0, .5, 2.), ('HI_Ceramic', 0, .3, 0), ('HI_Stone', 0, .7, 0)):
        m = bpy.data.materials.new(n); m.use_nodes = True
        b = next(x for x in m.node_tree.nodes if x.type == 'BSDF_PRINCIPLED')
        t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(T+n+'.png')
        m.node_tree.links.new(t.outputs[0], b.inputs['Base Color'])
        b.inputs['Metallic'].default_value = mt; b.inputs['Roughness'].default_value = r
        if e: m.node_tree.links.new(t.outputs[0], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = e
        mats[n] = m

def _fin(p, m, bev=0., seg=2):
    o = bpy.context.object; o.data.materials.append(mats[m])
    if bev:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        md = o.modifiers.new('b', 'BEVEL'); md.width = bev; md.segments = seg; md.limit_method = 'ANGLE'
        bpy.ops.object.modifier_apply(modifier='b')
    p.append(o); return o
def box(p, m, c, s, rot=(0, 0, 0), bev=.03, seg=2):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c, rotation=rot); bpy.context.object.scale = s; return _fin(p, m, bev, seg)
def cyl(p, m, c, r, d, axis='X', verts=16, bev=0.):
    rot = dict(X=(0, math.pi/2, 0), Y=(math.pi/2, 0, 0), Z=(0, 0, 0))[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=c, rotation=rot); return _fin(p, m, bev)
def ball(p, m, c, s):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1, location=c); bpy.context.object.scale = s
    bpy.ops.object.shade_smooth(); return _fin(p, m)
def torus(p, m, c, R, r, rot=(0, math.pi/2, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=c, rotation=rot, major_segments=24, minor_segments=8); return _fin(p, m)
def wheel(p, x, y, r, w, rim='HI_Oak', hub=True):
    cyl(p, 'HI_Iron', (x, y, r), r, w, 'X', 24, bev=.03); cyl(p, rim, (x, y, r), r*.6, w+.02, 'X', 16)
    if hub: cyl(p, 'HI_Lantern' if rim == 'HI_Ceramic' else 'HI_Iron', (x, y, r), r*.18, w+.05, 'X', 8)
def lights(p, xs, y, z, r=.07):
    for x in xs: cyl(p, 'HI_Lantern', (x, y, z), r, .04, 'Y', 14)
def car_wheels(p, xw=.5, ys=(-.62, .62), r=.25, w=.16):
    for x in (-xw, xw):
        for y in ys: wheel(p, x, y, r, w)
def bike_wheels(p, r=.3, w=.1):
    wheel(p, 0, .45, r, w, hub=False); wheel(p, 0, -.45, r, w, hub=False)

# 1. 클래식 도시형: 지붕 달린 세단, 스쿠터, 대형 앞유리 시내버스
def car1():
    p = []; box(p, 'HI_Sage', (0, 0, .5), (.94, 1.96, .42), bev=.12, seg=3)
    box(p, 'HI_Paper', (0, -.12, .9), (.82, 1.0, .4), bev=.1, seg=3)             # glass cabin
    box(p, 'HI_Sage', (0, -.12, 1.12), (.84, .9, .06), bev=.03)                  # roof
    box(p, 'HI_Iron', (0, .99, .42), (.9, .05, .12)); box(p, 'HI_Iron', (0, -.99, .42), (.9, .05, .12))  # bumpers
    lights(p, (-.32, .32), .98, .58); car_wheels(p); return p
def bike1():
    p = []; bike_wheels(p, .22, .1)
    box(p, 'HI_Ceramic', (0, -.18, .42), (.3, .6, .3), bev=.12, seg=3)          # rear cowl
    box(p, 'HI_Ceramic', (0, .38, .55), (.3, .1, .6), bev=.04)                    # leg shield
    box(p, 'HI_Iron', (0, .1, .26), (.18, .5, .05))                               # floorboard
    box(p, 'HI_Ondol', (0, -.2, .62), (.22, .42, .08), bev=.03)                   # seat
    cyl(p, 'HI_DarkTimber', (0, .4, .9), .02, .5, 'X'); lights(p, (0,), .45, .85, .06); return p
def bus1():
    p = []; box(p, 'HI_Ceramic', (0, 0, 1.05), (1.46, 3.96, 1.5), bev=.15, seg=3)
    box(p, 'HI_Sage', (0, 0, .55), (1.48, 3.98, .4), bev=.1)                     # lower band
    for x in (-.74, .74): box(p, 'HI_Paper', (x, -.2, 1.35), (.02, 3.0, .55), bev=0)  # window strip
    box(p, 'HI_Paper', (0, 1.98, 1.25), (1.3, .02, .85), bev=0)                   # big windscreen
    box(p, 'HI_DarkTimber', (.745, 1.45, 1.0), (.02, .7, 1.2), bev=0)             # door
    torus(p, 'HI_Lantern', (.8, 1.45, 1.0), .52, .05)
    box(p, 'HI_Lantern', (0, 1.99, 1.72), (.9, .03, .16), bev=0)                  # route sign
    lights(p, (-.5, .5), 2.0, .55, .09)
    for y in (-1.3, 1.3):
        for x in (-.7, .7): wheel(p, x, y, .32, .2)
    return p

# 2. 레트로 둥근형: 딱정벌레 차, 카페레이서, 보닛 달린 스쿨버스
def car2():
    p = []; ball(p, 'HI_Lantern', (0, 0, .62), (.47, .95, .42))                  # round body (warm yellow)
    ball(p, 'HI_Paper', (0, -.1, .88), (.36, .5, .3))                             # glass dome
    for x in (-.42, .42):
        for y in (-.6, .6): ball(p, 'HI_DarkTimber', (x, y, .4), (.12, .28, .18))  # fenders
    lights(p, (-.25, .25), .9, .6, .08); car_wheels(p, .44); return p
def bike2():
    p = []; bike_wheels(p, .3, .12)
    ball(p, 'HI_Sage', (0, .1, .66), (.13, .28, .12))                             # teardrop tank
    box(p, 'HI_Ondol', (0, -.25, .62), (.18, .38, .07), bev=.03)
    box(p, 'HI_Sage', (0, -.48, .64), (.18, .1, .12), bev=.05)                    # tail hump
    box(p, 'HI_Iron', (0, 0, .42), (.08, .8, .2), bev=.02)                        # engine block
    cyl(p, 'HI_Iron', (0, .42, .62), .03, .44, 'Z'); cyl(p, 'HI_DarkTimber', (0, .36, .78), .02, .4, 'X')
    ball(p, 'HI_Lantern', (0, .5, .74), (.08, .06, .08))
    cyl(p, 'HI_Iron', (.12, -.25, .32), .04, .6, 'Y'); return p
def bus2():
    p = []; box(p, 'HI_Lantern', (0, -.35, 1.1), (1.44, 3.2, 1.4), bev=.2, seg=4)   # yellow box
    box(p, 'HI_Lantern', (0, 1.55, .72), (1.1, .9, .6), bev=.15, seg=3)           # hood
    box(p, 'HI_Iron', (0, 2.0, .6), (.9, .04, .4)); box(p, 'HI_DarkTimber', (0, 0, .5), (1.5, 4.0, .16))
    for y in (-1.5, -.8, -.1, .6):
        for x in (-.72, .72): box(p, 'HI_Paper', (x, y, 1.35), (.02, .55, .45), bev=0)
    box(p, 'HI_Paper', (0, 1.26, 1.4), (1.25, .02, .55), bev=0)
    box(p, 'HI_DarkTimber', (.72, .95, 1.0), (.03, .5, 1.1), bev=0); torus(p, 'HI_Lantern', (.78, .95, 1.0), .45, .05)
    lights(p, (-.4, .4), 2.02, .78, .09)
    for y in (-1.3, 1.3):
        for x in (-.7, .7): wheel(p, x, y, .32, .2)
    return p

# 3. 오프로드 탐험형: 롤바 픽업, 오프로드 바이크, 루프랙 사파리 버스
def car3():
    p = []; box(p, 'HI_Stone', (0, .25, .58), (.96, 1.4, .46), bev=.06)          # body
    box(p, 'HI_DarkTimber', (0, -.6, .5), (.96, .78, .3), bev=.03)                # open bed
    box(p, 'HI_Paper', (0, .1, .98), (.86, .5, .34), bev=.06)                     # cab glass
    box(p, 'HI_Stone', (0, .1, 1.18), (.88, .55, .06))
    for x in (-.4, .4): cyl(p, 'HI_Iron', (x, -.55, .95), .03, .6, 'Z')          # roll bar
    cyl(p, 'HI_Iron', (0, -.55, 1.25), .03, .82, 'X')
    box(p, 'HI_Iron', (0, .98, .45), (.98, .08, .2)); lights(p, (-.3, .3), .96, .68)
    for x in (-.25, .25): cyl(p, 'HI_Lantern', (x, .2, 1.24), .05, .05, 'Y', 12)  # roof lamps
    car_wheels(p, .5, r=.3, w=.22); return p
def bike3():
    p = []; bike_wheels(p, .32, .12)
    box(p, 'HI_Lantern', (0, .45, .72), (.14, .3, .04), (math.radians(10), 0, 0))  # high front fender
    box(p, 'HI_Lantern', (0, -.15, .72), (.16, .62, .1), (math.radians(-6), 0, 0), bev=.04)  # tank+seat line
    box(p, 'HI_Ondol', (0, -.2, .79), (.14, .45, .05))
    box(p, 'HI_Iron', (0, 0, .45), (.1, .5, .22), bev=.02)
    for x in (-.05, .05): cyl(p, 'HI_Iron', (x, .44, .62), .025, .55, 'Z')
    cyl(p, 'HI_DarkTimber', (0, .4, .95), .02, .6, 'X'); lights(p, (0,), .52, .82, .06); return p
def bus3():
    p = []; box(p, 'HI_Stone', (0, 0, 1.05), (1.46, 3.96, 1.3), bev=.08)
    box(p, 'HI_DarkTimber', (0, 0, .42), (1.5, 4.0, .22))
    for y in (-1.3, -.5, .3):
        for x in (-.74, .74): box(p, 'HI_Paper', (x, y, 1.3), (.02, .65, .5), bev=0)
    box(p, 'HI_Paper', (0, 1.98, 1.3), (1.25, .02, .5), bev=0)
    for x in (-.7, .7): cyl(p, 'HI_Iron', (x, 0, 1.95), .025, 3.6, 'Y')           # roof rack rails
    for y in (-1.2, -.3, .6): box(p, 'HI_Oak', (y * .3, y, 1.92), (.6, .5, .3))   # luggage crates
    box(p, 'HI_Iron', (0, 2.03, .55), (1.4, .08, .25)); lights(p, (-.5, .5), 2.0, .75, .09)
    box(p, 'HI_DarkTimber', (.745, 1.3, 1.0), (.02, .7, 1.1), bev=0); torus(p, 'HI_Lantern', (.8, 1.3, 1.0), .5, .05)
    cyl(p, 'HI_Iron', (0, -2.05, 1.0), .3, .2, 'Y', 20)                           # spare wheel
    for y in (-1.3, 1.3):
        for x in (-.7, .7): wheel(p, x, y, .36, .24)
    return p

# 4. 한옥 판타지: 기와지붕 가마차, 나무 자전거형 바이크, 단청 누각 버스
def roof(p, c, w, l, h=.18):
    box(p, 'HI_Stone', c, (w, l, h), bev=.05)
    for s in (-1, 1):
        box(p, 'HI_Stone', (c[0] + s*w*.48, c[1], c[2] - h*.4), (w*.15, l*1.02, h*.6), (0, -s*math.radians(25), 0), bev=.03)  # eaves
    cyl(p, 'HI_DarkTimber', (c[0], c[1], c[2] + h*.55), .04, l*1.05, 'Y', 10)     # ridge
def car4():
    p = []; box(p, 'HI_DarkTimber', (0, 0, .35), (.96, 1.9, .14))
    box(p, 'HI_Oak', (0, -.15, .75), (.8, 1.2, .7), bev=.03)                      # palanquin cabin
    for x in (-.405, .405): box(p, 'HI_Paper', (x, -.15, .82), (.02, .8, .4), bev=0)  # hanji windows
    roof(p, (0, -.15, 1.2), 1.0, 1.45)
    box(p, 'HI_Sage', (0, .7, .5), (.86, .5, .2), bev=.05)                        # front step
    for x in (-.45, .45): cyl(p, 'HI_Lantern', (x, .85, .9), .06, .14, 'Z', 10)    # hanging lanterns
    for x in (-.5, .5):
        for y in (-.6, .62): wheel(p, x, y, .28, .1, rim='HI_DarkTimber')
    return p
def bike4():
    p = []; wheel(p, 0, .45, .3, .06, rim='HI_DarkTimber', hub=False); wheel(p, 0, -.45, .3, .06, rim='HI_DarkTimber', hub=False)
    box(p, 'HI_Oak', (0, 0, .5), (.08, .95, .07), (math.radians(-10), 0, 0))
    box(p, 'HI_Oak', (0, -.05, .38), (.08, .5, .06), (math.radians(20), 0, 0))
    box(p, 'HI_Sage', (0, -.22, .7), (.2, .3, .08), bev=.03)
    box(p, 'HI_Oak', (0, .1, .6), (.18, .26, .12), bev=.03)                       # wooden box
    cyl(p, 'HI_DarkTimber', (0, .42, .64), .03, .5, 'Z'); cyl(p, 'HI_DarkTimber', (0, .4, .9), .02, .55, 'X')
    cyl(p, 'HI_Lantern', (0, .55, .76), .06, .16, 'Z', 10); return p
def bus4():
    p = []; box(p, 'HI_DarkTimber', (0, 0, .4), (1.5, 4.0, .2))
    box(p, 'HI_Oak', (0, 0, 1.0), (1.4, 3.8, 1.0), bev=.03)
    for y in (-1.4, -.7, 0, .7):
        for x in (-.705, .705): box(p, 'HI_Paper', (x, y, 1.1), (.02, .55, .55), bev=0)
    for y in (-1.85, -1.05, -.35, .35, 1.05, 1.85):
        for x in (-.7, .7): cyl(p, 'HI_Sage', (x, y, 1.0), .05, 1.05, 'Z', 8)       # columns (dancheong green)
    box(p, 'HI_Sage', (0, 0, 1.55), (1.5, 3.9, .1), bev=.02)
    roof(p, (0, 0, 1.75), 1.75, 4.2, .25)
    box(p, 'HI_Paper', (0, 1.91, 1.1), (1.1, .02, .5), bev=0)
    torus(p, 'HI_Lantern', (.78, 1.35, 1.0), .48, .05)
    for y in (-1.9, 1.9):
        for x in (-.7, .7): cyl(p, 'HI_Lantern', (x, y, 1.35), .07, .18, 'Z', 10)
    for y in (-1.3, 1.3):
        for x in (-.72, .72): wheel(p, x, y, .34, .12, rim='HI_DarkTimber')
    return p

# 5. 스팀펑크: 굴뚝 증기차, 놋쇠 파이프 바이크, 노면전차 버스
def car5():
    p = []; box(p, 'HI_DarkTimber', (0, 0, .35), (.96, 1.9, .14))
    cyl(p, 'HI_Lantern', (0, .45, .62), .34, .9, 'Y', 20, bev=.03)                 # brass boiler (lies along Y)
    cyl(p, 'HI_Iron', (0, .92, .62), .3, .06, 'Y', 20)
    cyl(p, 'HI_Iron', (0, .7, 1.15), .07, .55, 'Z', 12); cyl(p, 'HI_Iron', (0, .7, 1.45), .11, .08, 'Z', 12)  # chimney
    box(p, 'HI_Oak', (0, -.45, .6), (.9, .9, .4), bev=.03)
    box(p, 'HI_Ondol', (0, -.5, .85), (.75, .5, .12), bev=.03)
    for x in (-.4, .4): cyl(p, 'HI_Iron', (x, -.5, 1.05), .02, .5, 'Z')
    box(p, 'HI_DarkTimber', (0, -.5, 1.3), (.9, .7, .04))                          # canopy
    lights(p, (-.38, .38), .96, .55)
    for x in (-.5, .5):
        wheel(p, x, -.6, .32, .12, rim='HI_Lantern'); wheel(p, x, .62, .25, .12, rim='HI_Lantern')
    return p
def bike5():
    p = []; wheel(p, 0, .45, .3, .08, rim='HI_Lantern', hub=False); wheel(p, 0, -.45, .3, .08, rim='HI_Lantern', hub=False)
    cyl(p, 'HI_Lantern', (0, .05, .55), .13, .4, 'Y', 16)                          # boiler tank
    box(p, 'HI_Iron', (0, 0, .4), (.06, .9, .06), (math.radians(-6), 0, 0))
    box(p, 'HI_Ondol', (0, -.28, .66), (.2, .3, .08), bev=.03)
    for x in (-.12, .12): cyl(p, 'HI_Lantern', (x, -.25, .4), .03, .6, 'Y', 8)     # twin pipes
    cyl(p, 'HI_Iron', (0, .15, .78), .03, .22, 'Z', 8)
    cyl(p, 'HI_Iron', (0, .42, .62), .03, .44, 'Z'); cyl(p, 'HI_DarkTimber', (0, .38, .86), .02, .55, 'X')
    lights(p, (0,), .52, .72, .07); return p
def bus5():
    p = []; box(p, 'HI_Iron', (0, 0, .38), (1.5, 4.0, .22))
    box(p, 'HI_Sage', (0, 0, 1.05), (1.44, 3.7, 1.2), bev=.04)
    for s in (-1, 1): box(p, 'HI_Paper', (0, s*1.9, 1.15), (1.3, .25, 1.0), bev=.1)  # glazed rounded ends
    for y in (-1.2, -.4, .4, 1.2):
        for x in (-.73, .73): box(p, 'HI_Paper', (x, y, 1.3), (.02, .6, .5), bev=0)
    box(p, 'HI_Lantern', (0, 0, .95), (1.47, 3.72, .06), bev=0)                    # brass trim
    box(p, 'HI_DarkTimber', (0, 0, 1.72), (1.3, 4.1, .12), bev=.04)
    for y in (-.4, .4): box(p, 'HI_Iron', (0, y, 2.05), (.04, .9, .04), (math.copysign(math.radians(40), y), 0, 0), bev=0)  # pantograph
    box(p, 'HI_Iron', (0, 0, 2.35), (.8, .08, .03), bev=0)
    torus(p, 'HI_Lantern', (.78, 1.0, 1.0), .48, .05); lights(p, (0,), 2.06, .75, .1)
    for y in (-1.4, -.9, .9, 1.4):
        for x in (-.66, .66): wheel(p, x, y, .25, .1, rim='HI_Lantern', hub=False)
    return p

SETS = ((car1, bike1, bus1), (car2, bike2, bus2), (car3, bike3, bus3), (car4, bike4, bus4), (car5, bike5, bus5))
for i, (car, bike, bus) in enumerate(SETS, 1):
    bpy.ops.wm.read_factory_settings(use_empty=True); mats.clear(); setup_mats()
    for make, at in ((car, -3.), (bike, -.6), (bus, 2.6)):
        for o in make(): o.location.x += at
    sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE_NEXT'; sc.render.resolution_x, sc.render.resolution_y = 960, 540
    w = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.35, .32, .28, 1); sc.world = w
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(50), 0, math.radians(35))); bpy.context.object.data.energy = 3
    bpy.ops.mesh.primitive_plane_add(size=30); bpy.context.object.data.materials.append(mats['HI_Ondol'])
    bpy.ops.object.camera_add(location=(6.5, 9.5, 6.)); cam = bpy.context.object; sc.camera = cam
    cam.rotation_euler = (Vector((0, 0, .7)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f'{OUT}/concept_{i}.png'; bpy.ops.render.render(write_still=True)
    print('CONCEPT', i)

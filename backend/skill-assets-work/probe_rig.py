import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:/Users/good6/WarfrontMVP/Assets/Resources/MiniDungeon/Models/character-human.fbx')
for o in bpy.context.scene.objects:
 print('OBJECT',o.name,o.type,tuple(o.location),tuple(o.scale))
 if o.type=='ARMATURE':
  for b in o.data.bones: print('BONE',b.name,'parent',b.parent.name if b.parent else None,'head',tuple(o.matrix_world@b.head_local))

from pathlib import Path
p=Path('skill-assets-work/BlenderBlastVisual.cs')
s=p.read_text(encoding='utf-8-sig').replace('private MaterialPropertyBlock block;', 'private MaterialPropertyBlock block;\n        private Vector3 waveScale,coreScale,sparksScale;')
s=s.replace('''{if(child.name=="Shockwave")wave=child;else if(child.name=="Core")core=child;else if(child.name=="Sparks")sparks=child;}''','''{if(child.name=="Shockwave")wave=child;else if(child.name=="Core")core=child;else if(child.name=="Sparks")sparks=child;}
            if(wave!=null)waveScale=wave.localScale;if(core!=null)coreScale=core.localScale;if(sparks!=null)sparksScale=sparks.localScale;''')
s=s.replace('wave.localScale=Vector3.one*', 'wave.localScale=waveScale*').replace('core.localScale=Vector3.one*', 'core.localScale=coreScale*').replace('sparks.localScale=Vector3.one*', 'sparks.localScale=sparksScale*')
p.write_text(s,encoding='utf-8-sig')
p=Path('skill-assets-work/BlenderSkillImport.cs')
s=p.read_text(encoding='utf-8-sig').replace('var model=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path));model.name=name;', '''var model=new GameObject(name);
                UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path),model.transform,false);''')
p.write_text(s,encoding='utf-8-sig')
p=Path('skill-assets-work/BlenderSkillChecks.cs')
s=p.read_text(encoding='utf-8-sig').replace('EditorApplication.delayCall+=()=>{var path=', 'EditorApplication.delayCall+=()=>{if(EditorApplication.isPlayingOrWillChangePlaymode){AutoRun();return;}var path=')
s=s.replace('var camera=root.GetComponentsInChildren<Camera>(true).First(c=>c.name=="Fantasy Camera");', 'actor.transform.localRotation=Quaternion.identity;\n            var camera=root.GetComponentsInChildren<Camera>(true).First(c=>c.name=="Fantasy Camera");')
s=s.replace('Check(bomb.localPosition.y>1.5f,"Bomb does not fly through an arc");', '''Check(bomb.localPosition.y>1.5f,"Bomb does not fly through an arc");
                Check(bomb.GetComponentsInChildren<Renderer>().Max(r=>r.bounds.size.magnitude)>.2f,"Bomb FBX scale lost during pooling/rental");''')
s=s.replace('Check(blast.GetComponentsInChildren<MeshRenderer>(true).Length>=3,"Blast lacks shockwave/core/fragments");', '''Check(blast.GetComponentsInChildren<MeshRenderer>(true).Length>=3,"Blast lacks shockwave/core/fragments");
                Check(blast.GetComponentsInChildren<Renderer>().Max(r=>r.bounds.size.magnitude)>1f,"Explosion lost imported FBX scale");''')
p.write_text(s,encoding='utf-8-sig')

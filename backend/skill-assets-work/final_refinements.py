from pathlib import Path
p=Path('skill-assets-work/RetroSquadCombat.cs')
s=p.read_text(encoding='utf-8-sig').replace('private readonly Dictionary<int,float> squadBlastReplayStart=', 'private readonly Dictionary<int,Vector3> bombLaunchPoints=new Dictionary<int,Vector3>();\n        private readonly Dictionary<int,float> squadBlastReplayStart=')
s=s.replace('if(animation==null)return;EnsureBlenderSkillClips(animation);', 'if(animation==null)return;EnsureBlenderSkillClips(animation);')
s=s.replace('float remaining=Mathf.Max(0,left-age);bool active=remaining>0&&duration>0;', '''float remaining=Mathf.Max(0,left-age);bool active=remaining>0&&duration>0;
            var sword=actor.transform.Find("root/torso/arm-right/weapon-sword(Clone)");
            if(sword!=null)sword.gameObject.SetActive(!(active&&kind=="bomb")&&(!companionRoles.TryGetValue(key,out var role)||role!="archer"));''')
s=s.replace('''                // Never invent explosion damage; await the server's exploded flag.''', '''                if(!bombLaunchPoints.ContainsKey(b.id)||elapsed<release)bombLaunchPoints[b.id]=HeldBombPosition(b);
                // Never invent explosion damage; await the server's exploded flag.''')
s=s.replace('elapsed<release?HeldBombPosition(b):WorldPoint(Mathf.Lerp(b.start_x,b.target_x,t),Mathf.Lerp(b.start_y,b.target_y,t))+Vector3.up*(.35f+4*1.8f*t*(1-t))', 'elapsed<release?bombLaunchPoints[b.id]:Vector3.Lerp(bombLaunchPoints[b.id],WorldPoint(b.target_x,b.target_y)+Vector3.up*.18f,t)+Vector3.up*(4*1.8f*t*(1-t))')
s=s.replace('squadBlastEffects.Remove(id);squadBlastReplayStart.Remove(id);', 'squadBlastEffects.Remove(id);squadBlastReplayStart.Remove(id);bombLaunchPoints.Remove(id);')
p.write_text(s,encoding='utf-8-sig')
p=Path('skill-assets-work/RetroCombatPooling.cs')
s=p.read_text(encoding='utf-8-sig').replace('squadBlastEffects.Clear();squadBlastReplayStart.Clear();', 'squadBlastEffects.Clear();squadBlastReplayStart.Clear();bombLaunchPoints.Clear();')
p.write_text(s,encoding='utf-8-sig')
p=Path('skill-assets-work/BlenderSkillChecks.cs')
s=p.read_text(encoding='utf-8-sig')
s=s.replace('Check(actor.GetComponentInChildren<SkinnedMeshRenderer>().sharedMesh==original,"Existing character art was replaced");', '''Check(actor.GetComponentInChildren<SkinnedMeshRenderer>().sharedMesh==original,"Existing character art was replaced");
                scene.SquadAction("player:self",2,"bomb",.20f,.30f,1,0,0,0,true,145,.35f);
                Check(!actor.Find("root/torso/arm-right/weapon-sword(Clone)").gameObject.activeSelf,"Throw still holds sword in bomb hand");
                scene.SquadBombs(new[]{new MmoBomb{id=50,owner_id="self",flight=.65f,radius=150,start_x=1000,start_y=1200,target_x=1300,target_y=1200,age=.119f}},0,0);
                var held=root.transform.Find("Encounter squad/Server bomb 50").localPosition;
                scene.SquadBombs(new[]{new MmoBomb{id=50,owner_id="self",flight=.65f,radius=150,start_x=1000,start_y=1200,target_x=1300,target_y=1200,age=.121f}},0,0);
                Check(Vector3.Distance(held,root.transform.Find("Encounter squad/Server bomb 50").localPosition)<.08f,"Bomb snaps away from hand at release");
                scene.SquadAction("player:self",3,"heavy",.27f,.55f,1,0,0,0,true,210,.35f);
                Check(actor.Find("root/torso/arm-right/weapon-sword(Clone)").gameObject.activeSelf,"Sword not restored after throw");''')
s=s.replace('''                var clip=Resources.Load<AnimationClip>("SkillVisuals/"+item[0]);clip.SampleAnimation''', '''                var sword=actor.transform.Find("root/torso/arm-right/weapon-sword(Clone)");sword.gameObject.SetActive(item[0]!="Throw");
                var clip=Resources.Load<AnimationClip>("SkillVisuals/"+item[0]);clip.SampleAnimation''')
p.write_text(s,encoding='utf-8-sig')
p=Path('skill-assets-work/build_skill_visuals.py')
s=p.read_text(encoding='utf-8-sig').replace("bpy.ops.wm.save_as_mainfile(filepath=str(out/'SkillVisuals.blend'))", "bpy.ops.file.pack_all()\nbpy.ops.wm.save_as_mainfile(filepath=str(out/'SkillVisuals.blend'))")
p.write_text(s,encoding='utf-8')

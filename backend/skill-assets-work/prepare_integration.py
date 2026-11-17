from pathlib import Path
p=Path('skill-assets-work/RetroBlenderSkills.cs')
s=p.read_text(encoding='utf-8-sig').replace('''                foreach(var child in owner.GetComponentsInChildren<Transform>(true))
                    if(child.name=="arm-right")return field.transform.InverseTransformPoint(child.TransformPoint(new Vector3(0,-.12f,.06f)));''','''                var hand=owner.transform.Find("root/torso/arm-right");
                if(hand!=null)return field.transform.InverseTransformPoint(hand.TransformPoint(new Vector3(0,-.12f,.06f)));''')
p.write_text(s,encoding='utf-8-sig')
base=Path(r'C:/Users/good6/WarfrontMVP/Assets/script')
for name in ['RetroSquadCombat.cs','RetroCombatPooling.cs']:
 Path('skill-assets-work',name).write_text((base/name).read_text(encoding='utf-8-sig'),encoding='utf-8-sig')
p=Path('skill-assets-work/RetroSquadCombat.cs')
s=p.read_text(encoding='utf-8-sig').replace('private GameObject squadGrenade;', '''private GameObject squadGrenade,squadBlastPrefab;
        private readonly Dictionary<int,GameObject> squadBlastEffects=new Dictionary<int,GameObject>();
        private readonly Dictionary<int,float> squadBlastReplayStart=new Dictionary<int,float>();''')
s=s.replace('var animation=actor.GetComponent<Animation>();if(animation==null)return;', 'var animation=actor.GetComponent<Animation>();if(animation==null)return;EnsureBlenderSkillClips(animation);')
s=s.replace('squadGrenade=Resources.Load<GameObject>("WarfrontCombat/Bomb")', 'squadGrenade=Resources.Load<GameObject>("SkillVisuals/Bomb")??Resources.Load<GameObject>("WarfrontCombat/Bomb")')
s=s.replace('squadBlastRings[b.id]=ring;', '''squadBlastRings[b.id]=ring;
                    if(squadBlastPrefab==null)squadBlastPrefab=Resources.Load<GameObject>("SkillVisuals/Blast");
                    if(squadBlastPrefab!=null)squadBlastEffects[b.id]=RentCombatVisual(blastEffectPool,squadBlastPrefab,"Blender blast "+b.id);''')
s=s.replace('float t=Mathf.Clamp01(elapsed/flight);', 'float release=Mathf.Min(.12f,flight*.25f);float t=Mathf.Clamp01((elapsed-release)/Mathf.Max(.01f,flight-release));')
s=s.replace('node.transform.localPosition=WorldPoint(Mathf.Lerp(b.start_x,b.target_x,t),Mathf.Lerp(b.start_y,b.target_y,t))+Vector3.up*(.5f+4*1.8f*t*(1-t));', 'node.transform.localPosition=elapsed<release?HeldBombPosition(b):WorldPoint(Mathf.Lerp(b.start_x,b.target_x,t),Mathf.Lerp(b.start_y,b.target_y,t))+Vector3.up*(.35f+4*1.8f*t*(1-t));')
s=s.replace('float blast=b.exploded?Mathf.Clamp01((elapsed-flight)/.35f):0;', '''if(b.exploded&&!squadBlastReplayStart.ContainsKey(b.id))squadBlastReplayStart[b.id]=Time.unscaledTime-Mathf.Clamp(elapsed-flight,0,.2f);
                float blast=b.exploded?Mathf.Clamp01((Time.unscaledTime-squadBlastReplayStart[b.id])/.35f):0;
                if(squadBlastEffects.TryGetValue(b.id,out var effect))
                {
                    effect.SetActive(b.exploded&&blast<1);effect.transform.localPosition=WorldPoint(b.target_x,b.target_y)+Vector3.up*.04f;
                    if(b.exploded)effect.GetComponent<BlenderBlastVisual>().Show(b.radius/50f,blast,b.team==ownTeam);
                }''')
s=s.replace('squadBombs.Remove(id);squadBlastRings.Remove(id);', '''if(squadBlastEffects.TryGetValue(id,out var effect))ReturnCombatVisual(blastEffectPool,effect);
                squadBlastEffects.Remove(id);squadBlastReplayStart.Remove(id);squadBombs.Remove(id);squadBlastRings.Remove(id);''')
p.write_text(s,encoding='utf-8-sig')
p=Path('skill-assets-work/RetroCombatPooling.cs')
s=p.read_text(encoding='utf-8-sig').replace('private readonly Stack<GameObject> bombPool=', 'private readonly Stack<GameObject> blastEffectPool=new Stack<GameObject>(CombatPoolCapacity);\n        private readonly Stack<GameObject> bombPool=')
s=s.replace('flyingArrows.Clear();arrowReplayStart.Clear();', '''foreach(var item in squadBlastEffects.Values)ReturnCombatVisual(blastEffectPool,item);
            squadBlastEffects.Clear();squadBlastReplayStart.Clear();
            flyingArrows.Clear();arrowReplayStart.Clear();''')
p.write_text(s,encoding='utf-8-sig')
p=Path('skill-assets-work/SquadCharacterRestoreChecks.cs')
s=(Path(r'C:/Users/good6/WarfrontMVP/Assets/Editor/SquadCharacterRestoreChecks.cs')).read_text(encoding='utf-8-sig')
s=s.replace('string clip=kind=="dodge"?"Dodge":"Attack";', 'string clip=kind=="dodge"?"Dodge":kind=="heavy"&&animation.GetClip("Heavy")!=null?"Heavy":kind=="bomb"&&animation.GetClip("Throw")!=null?"Throw":"Attack";')
p.write_text(s,encoding='utf-8-sig')

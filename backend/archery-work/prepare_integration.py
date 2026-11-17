from pathlib import Path
p=Path('archery-work/CompanionEquipmentBuilder.cs');s=p.read_text(encoding='utf-8-sig')
a=s.index('                var idle=instance.GetComponent<Animation>().GetClip("Idle");')
b=s.index('string path=Root+"/BowDraw.anim";',a)
s=s[:a]+'                var clip=BowMotionClipBuilder.Build(instance);'+s[b:]
a=s.index('        static void Arm(');s=s[:a]+'    }\n}\n';p.write_text(s,encoding='utf-8-sig')
p=Path('archery-work/RetroSquadCompanions.cs');s=p.read_text(encoding='utf-8-sig')
s=s.replace('private readonly Dictionary<int,float> arrowReplayStart=', 'private readonly Dictionary<int,Vector3> arrowVisualStarts=new Dictionary<int,Vector3>();\n        private readonly Dictionary<int,float> arrowReplayStart=')
s=s.replace('flyingArrows.Clear();arrowReplayStart.Clear();', 'flyingArrows.Clear();arrowReplayStart.Clear();arrowVisualStarts.Clear();')
s=s.replace('nockedArrows[key]=nock;', 'nockedArrows[key]=nock;\n            bow.AddComponent<ArcheryBowVisual>().Initialize(actor.transform,hand,actor.transform.Find("root/torso/arm-right"),nock.transform);')
a=s.index('            bow.transform.position=hand.TransformPoint(');b=s.index('\n        public void SquadProjectiles',a)
s=s[:a]+'''            var visual=bow.GetComponent<ArcheryBowVisual>();if(visual!=null)visual.SetPhase(drawing,elapsed);
        }
        private Vector3 ArrowVisualStart(MmoProjectile projectile)
        {
            var fallback=WorldPoint(projectile.start_x,projectile.start_y)+Vector3.up*.85f;
            GameObject bow;
            if(companionBows.TryGetValue("player:"+projectile.owner_id,out bow)||companionBows.TryGetValue("enemy:"+projectile.owner_id,out bow))
            {
                var visual=bow.GetComponent<ArcheryBowVisual>();if(visual==null)return fallback;
                var point=field.transform.InverseTransformPoint(visual.ReleasePosition);
                if(new Vector2(point.x-fallback.x,point.z-fallback.z).sqrMagnitude>.75f*.75f)return fallback;
                return point;
            }
            return fallback;
        }
''' +s[b:]
s=s.replace('flyingArrows[p.id]=arrow;', 'flyingArrows[p.id]=arrow;arrowVisualStarts[p.id]=ArrowVisualStart(p);')
s=s.replace('arrow.transform.localPosition=WorldPoint(Mathf.Lerp(p.start_x,p.end_x,t),Mathf.Lerp(p.start_y,p.end_y,t))+Vector3.up*.85f;', 'var visualStart=arrowVisualStarts[p.id];arrow.transform.localPosition=Vector3.Lerp(visualStart,WorldPoint(p.end_x,p.end_y)+Vector3.up*visualStart.y,t);')
s=s.replace('arrowReplayStart.Remove(id);', 'arrowReplayStart.Remove(id);arrowVisualStarts.Remove(id);')
p.write_text(s,encoding='utf-8-sig')
p=Path('archery-work/RetroCombatPooling.cs');s=p.read_text(encoding='utf-8-sig').replace('flyingArrows.Clear();arrowReplayStart.Clear();', 'flyingArrows.Clear();arrowReplayStart.Clear();arrowVisualStarts.Clear();');p.write_text(s,encoding='utf-8-sig')
p=Path('archery-work/HeroHitReaction.cs');s=p.read_text(encoding='utf-8-sig').replace('if(bow!=null&&leftArm!=null){bow.position=', 'if(bow!=null&&leftArm!=null){var visual=bow.GetComponent<ArcheryBowVisual>();if(visual!=null){visual.Refresh();return;}bow.position=');p.write_text(s,encoding='utf-8-sig')
p=Path('archery-work/RetroSquadCombat.cs');s=p.read_text(encoding='utf-8-sig').replace('private Material squadEffectMaterial;', 'private Material squadEffectMaterial;\n        private int ownBowImpulseAction=-1;\n        private float ownBowImpulseAt=-100,ownBowImpulseStrength;')
s=s.replace('ClearCompanionVisuals();walkUntil.Clear();', 'ownBowImpulseAction=-1;ownBowImpulseAt=-100;ClearCompanionVisuals();walkUntil.Clear();')
s=s.replace('            if(!squadArcs.TryGetValue(key,out var arc))', '''            if(own&&active&&heroBow&&bowTime>=.25f&&ownBowImpulseAction!=id)
            {ownBowImpulseAction=id;ownBowImpulseAt=Time.unscaledTime;ownBowImpulseStrength=kind=="charged_bow"?.25f:.12f;}
            if(!squadArcs.TryGetValue(key,out var arc))''')
p.write_text(s,encoding='utf-8-sig')
p=Path('archery-work/RetroFantasyScene.cs');s=p.read_text(encoding='utf-8-sig')
a=s.index('        public void ThirdPerson(');b=s.index('        public bool Project(',a)
part=s[a:b];i=part.rfind('        }');part=part[:i]+'''            float shotAge=Time.unscaledTime-ownBowImpulseAt;
            if(shotAge>=0&&shotAge<.12f)
            {
                float kick=Mathf.Sin(shotAge/.12f*Mathf.PI)*(1-shotAge/.12f);
                view.transform.rotation*=Quaternion.Euler(-ownBowImpulseStrength*kick,0,0);
                var position=view.transform.position-view.transform.forward*(.018f*kick);position.y=Mathf.Max(origin.y+.3f,position.y);view.transform.position=position;
            }
''' +part[i:];s=s[:a]+part+s[b:];p.write_text(s,encoding='utf-8-sig')

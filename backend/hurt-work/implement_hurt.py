from pathlib import Path
p=Path('hurt-work/RetroFantasyScene.cs');s=p.read_text(encoding='utf-8-sig')
s=s.replace('            bool moving=lastPositions.TryGetValue(key,out var previous)', '''            var reaction=actor.GetComponent<HeroHitReaction>();
            if(reaction!=null)reaction.RestorePose();
            float expiry=playerImpactUntil.TryGetValue(key,out var hitUntil)?hitUntil:0;
            if(expiry>Time.unscaledTime&&reaction==null)reaction=actor.AddComponent<HeroHitReaction>();
            if(reaction!=null)reaction.PlayUntil(expiry);
            bool moving=lastPositions.TryGetValue(key,out var previous)''')
start=s.index('            float hurt=PlayerImpactWeight(key);\n            if(hurt>0)')
end=s.index('\n        }\n        public void EndField()',start)
s=s[:start]+s[end:]
s=s.replace('if(!string.IsNullOrEmpty(id))playerImpactUntil["player:"+id]=Time.unscaledTime+.24f;', '''if(string.IsNullOrEmpty(id))return;
            string key="player:"+id;float expiry=Time.unscaledTime+HeroHitReaction.Duration;playerImpactUntil[key]=expiry;
            if(actors.TryGetValue(key,out var actor))
            {
                var reaction=actor.GetComponent<HeroHitReaction>()??actor.AddComponent<HeroHitReaction>();reaction.PlayUntil(expiry);
            }''')
s=s.replace('public void ClearPlayerImpacts(){playerImpactUntil.Clear();}', '''public void ClearPlayerImpacts()
        {
            playerImpactUntil.Clear();foreach(var actor in actors.Values)if(actor!=null){var reaction=actor.GetComponent<HeroHitReaction>();if(reaction!=null)reaction.Clear();}
        }''')
s=s.replace('(until-Time.unscaledTime)/.24f', '(until-Time.unscaledTime)/HeroHitReaction.Duration')
p.write_text(s,encoding='utf-8-sig')
p=Path('hurt-work/PlayerHurtChecks.cs');s=p.read_text(encoding='utf-8-sig')
s=s.replace('scene.Actor("player:self",1000,1000,0,0,false,false,false,false);scene.ThirdPerson', 'scene.Actor("player:self",1000,1000,0,0,false,false,false,false);stage.transform.Find("Encounter frontier/player:self").GetComponent<HeroHitReaction>().Sample(Time.unscaledTime);scene.ThirdPerson')
p.write_text(s,encoding='utf-8-sig')
p=Path('hurt-work/SquadHurtPoseChecks.cs');s=p.read_text(encoding='utf-8-sig').replace('var pose=torso.localRotation;', '''var bow=actor.Find("Archer Bow");var hand=actor.Find("root/torso/arm-left");Check(Vector3.Distance(bow.position,hand.TransformPoint(new Vector3(0,-.12f,.035f)))<.005f,"Bow detached during hurt");
                    var pose=torso.localRotation;''')
p.write_text(s,encoding='utf-8-sig')

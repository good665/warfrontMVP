from pathlib import Path
p=Path(__file__).parent
f=p/'FantasyTownView.cs'
s=f.read_text(encoding='utf-8-sig').replace('if(mmoWorld.players!=null)foreach(var a in mmoWorld.players)\n','if(mmoWorld.players!=null)foreach(var a in mmoWorld.players)if(!SquadModeActive||a.hp>0)\n')
f.write_text(s,encoding='utf-8')
f=p/'MmoCombatFeedback.cs';s=f.read_text(encoding='utf-8-sig')
s=s.replace('if(own&&retroScene!=null)retroScene.PlayerImpact(actor.id);','if(retroScene!=null)retroScene.PlayerImpact(actor.id,actor.hp<=0);\n                        death|=actor.hp<=0;')
f.write_text(s,encoding='utf-8')
f=p/'RetroFantasyScene.cs';s=f.read_text(encoding='utf-8-sig')
s=s.replace('SetLayer(actor);actors.Add(key,actor);','SetLayer(actor);actors.Add(key,actor);\n                if(fieldKey.StartsWith("squad:"))actor.AddComponent<CharacterScaleStability>().Capture();')
s=s.replace('            var reaction=actor.GetComponent<HeroHitReaction>();','''            // A live snapshot for the same id cancels every transient corpse/action state.
            if(deathUntil.Remove(key))
            {
                impactUntil.Remove(key);playerImpactUntil.Remove(key);previousWindups.Remove(key);
                actionUntil.Remove(key);actionState.Remove(key);walkUntil.Remove(key);lastPositions.Remove(key);
                var oldReaction=actor.GetComponent<HeroHitReaction>();if(oldReaction!=null)oldReaction.Clear();
                var oldAnimation=actor.GetComponent<Animation>();if(oldAnimation!=null){oldAnimation.Stop();foreach(AnimationState state in oldAnimation)state.speed=1;}
            }
            var reaction=actor.GetComponent<HeroHitReaction>();''',1)
s=s.replace('if(dead)deathUntil[key]=Time.unscaledTime+.55f;','''if(dead)deathUntil[key]=Time.unscaledTime+.55f;
            else if(fieldKey.StartsWith("squad:")&&actors.TryGetValue(key,out var actor))
            {var reaction=actor.GetComponent<HeroHitReaction>()??actor.AddComponent<HeroHitReaction>();reaction.PlayUntil(Time.unscaledTime+HeroHitReaction.Duration);}''')
s=s.replace('public void PlayerImpact(string id)','public void PlayerImpact(string id,bool dead=false)')
s=s.replace('string key="player:"+id;float expiry=', 'string key="player:"+id;if(dead)deathUntil[key]=Time.unscaledTime+.55f;float expiry=')
s=s.replace('if(enemy.hp>0&&actors.TryGetValue(key,out var actor))','if(!fieldKey.StartsWith("squad:")&&enemy.hp>0&&actors.TryGetValue(key,out var actor))')
f.write_text(s,encoding='utf-8')

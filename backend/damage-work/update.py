from pathlib import Path
p=Path('damage-work/MmoCombatFeedback.cs')
s=p.read_text(encoding='utf-8-sig')
s=s.replace('public float x,y,started,damage;', 'public float x,y,started,damage,height=1.7f; public string target;')
s=s.replace('AddMmoCombatPulse(enemy.x,enemy.y,killed,false);', 'AddMmoCombatPulse(enemy.x,enemy.y,killed,false,Mathf.Min(old.hp,enemy.max_hp>0?enemy.max_hp:old.hp)-enemy.hp,"enemy:"+enemy.id,enemy.kind=="base"?3.6f:enemy.kind=="boss"?2.55f:1.8f);')
s=s.replace('if(old.hp>enemy.hp&&old.hp>0)', 'if(Mathf.Min(old.hp,enemy.max_hp>0?enemy.max_hp:old.hp)>enemy.hp&&old.hp>0)')
s=s.replace('if(actor.id==current.you_id)foreach', 'foreach')
s=s.replace('AddMmoCombatPulse(actor.x,actor.y,actor.hp<=0,true,damage);\n                        if(retroScene!=null)retroScene.PlayerImpact(actor.id);\n                        impact=true;hurt=true;', 'bool own=actor.id==current.you_id;\n                        AddMmoCombatPulse(actor.x,actor.y,actor.hp<=0,own,damage,"player:"+actor.id);\n                        if(own&&retroScene!=null)retroScene.PlayerImpact(actor.id);\n                        impact=true;hurt|=own;')
s=s.replace('bool self,float damage=0)', 'bool self,float damage=0,string target=null,float height=1.7f)')
s=s.replace('self=self,damage=damage,started=', 'self=self,damage=damage,target=target,height=height,started=')
s=s.replace('float alpha=1-age/duration;', '''float alpha=1-age/duration;
                if(pulse.damage>0&&retroScene.Project(pulse.x,pulse.y,pulse.height,out var numberPoint))
                {
                    var tint=pulse.self?new Color(1,.48f,.32f,alpha):new Color(1,.9f,.5f,alpha);
                    var rect=new Rect(numberPoint.x-90,numberPoint.y-56-age*45,180,34);
                    BaseText(new Rect(rect.x+1,rect.y+2,rect.width,rect.height),"-"+pulse.damage.ToString("0.#"),22,new Color(0,0,0,alpha),TextAnchor.MiddleCenter);
                    BaseText(rect,"-"+pulse.damage.ToString("0.#"),22,tint,TextAnchor.MiddleCenter);
                }''')
# Numbers have their own readable lifetime; retain existing local hurt fade separately.
s=s.replace('float duration=pulse.self?.4f:pulse.death?.7f:.3f;', 'float duration=.8f;')
s='\n'.join(line for line in s.split('\n') if not ('pulse.damage.ToString' in line and 'hitPoint.x' in line))
p.write_text(s,encoding='utf-8-sig')
p=Path('damage-work/DungeonFirstPersonView.cs');s=p.read_text(encoding='utf-8-sig');s=s.replace('if(retroScene.Project(effect.effect.x', 'if(effect.effect.kind=="damage"||effect.effect.kind=="player_damage")continue;\n                if(retroScene.Project(effect.effect.x');p.write_text(s,encoding='utf-8-sig')
p=Path('damage-work/PlayerHurtChecks.cs');s=p.read_text(encoding='utf-8-sig');s=s.replace('Check(pulses.Count==1,"Other player\'s damage triggered local hurt");', 'Check(pulses.Count==2&&timers["player:self"]==expiry,"Other player damage missing number or triggered local hurt");');p.write_text(s,encoding='utf-8-sig')

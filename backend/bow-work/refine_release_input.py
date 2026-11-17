from pathlib import Path
p=Path('bow-work/SquadChargeInput.cs');s=p.read_text(encoding='utf-8-sig').replace('private float squadChargeStarted=-1;', 'private float squadChargeStarted=-1;\n        private Vector2 squadChargeReleaseAim;')
s=s.replace('if((!held&&squadChargeHeld)||(!held&&pressed))squadChargeRelease=true;', '''if((!held&&squadChargeHeld)||(!held&&pressed))
            {
                squadChargeRelease=true;var self=MmoSelf;
                squadChargeReleaseAim=new Vector2(self?.x??0,self?.y??0)+DungeonFirstPersonMath.Forward(dungeonYaw)*800;
            }''')
s=s.replace('float seconds=mmoWorld?', 'if(!self.charge_active&&self.skill1_cooldown>0)return;\n            float seconds=mmoWorld?')
p.write_text(s,encoding='utf-8-sig')
p=Path('bow-work/SquadView.cs');s=p.read_text(encoding='utf-8-sig').replace('var input=new SquadInput {sequence=', 'if(squadChargeRelease)aim=squadChargeReleaseAim;\n            var input=new SquadInput {sequence=')
p.write_text(s,encoding='utf-8-sig')
p=Path('bow-work/HeroBowChecks.cs');s=p.read_text(encoding='utf-8-sig').replace('var ready=typeof(GameBootstrap)', '''var releaseAim=(Vector2)Get(game,"squadChargeReleaseAim");Set(game,"dungeonYaw",0f);Check(((Vector2)Get(game,"squadChargeReleaseAim"))==releaseAim,"Release aim follows later camera motion");
                var ready=typeof(GameBootstrap)''')
p.write_text(s,encoding='utf-8-sig')

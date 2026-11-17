from pathlib import Path
p=Path('pooling-work/SquadView.cs')
s=p.read_text(encoding='utf-8-sig')
s=s.replace('        private void UpdateSquad()', '''        // A tapped action bypasses movement polling, but never overtakes an in-flight request.
        private bool SquadSendReady(float now)=>!squadRequest&&(now>=squadNext||mmoDodge||mmoSkill1||mmoSkill2);
        private void UpdateSquad()''')
s=s.replace('if(squadRequest||Time.realtimeSinceStartup<squadNext)return;', 'if(!SquadSendReady(Time.realtimeSinceStartup))return;')
s=s.replace('squadNext=Time.realtimeSinceStartup+.15f;', 'squadNext=Time.realtimeSinceStartup+.05f;')
p.write_text(s,encoding='utf-8-sig')

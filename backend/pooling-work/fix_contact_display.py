from pathlib import Path
p=Path('pooling-work/MmoModels.cs')
s=p.read_text(encoding='utf-8-sig').replace('bomb_radius=150; }', 'bomb_radius=150,attack_windup=.16f,heavy_windup=.20f,melee_active_end=.43f; }')
p.write_text(s,encoding='utf-8-sig')
p=Path('pooling-work/RetroSquadCombat.cs')
s=p.read_text(encoding='utf-8-sig').replace('bool own,float reach,float dot)', 'bool own,float reach,float dot,MmoCombatRules rules=null)')
start=s.index('            float progress=duration>0?1-remaining/duration:0;')
end=s.index('\n\n        }',start)
s=s[:start]+'''            float elapsed=duration-remaining;
            float windup=kind=="heavy"?(rules!=null&&rules.heavy_windup>0?rules.heavy_windup:.20f):(rules!=null&&rules.attack_windup>0?rules.attack_windup:.16f);
            float activeEnd=kind=="guard_attack"?.21f:(rules!=null&&rules.melee_active_end>0?rules.melee_active_end:.43f);
            // Render contact feedback only inside the server's damage window/sector.
            bool swing=active&&(kind=="attack"||kind=="heavy"||kind=="guard_attack")&&elapsed>=windup&&elapsed<activeEnd;
            arc.enabled=swing;
            if(swing)
            {
                float halfAngle=Mathf.Acos(Mathf.Clamp(dot,-1,1))*Mathf.Rad2Deg;
                float angle=Mathf.Lerp(-halfAngle,halfAngle,Mathf.Clamp01((elapsed-windup)/Mathf.Max(.01f,activeEnd-windup)));
                Arc(arc,(kind=="guard_attack"?95:reach)/50f/actor.transform.localScale.x,Mathf.Max(-halfAngle,angle-38),angle,.65f);
            }''' + s[end:]
p.write_text(s,encoding='utf-8-sig')
p=Path('pooling-work/FantasyTownView.cs')
s=p.read_text(encoding='utf-8-sig').replace('false,145,.35f);', 'false,e.action_kind=="heavy"?(mmoWorld.combat_rules?.heavy_reach??210):(mmoWorld.combat_rules?.attack_reach??145),mmoWorld.combat_rules?.attack_dot??.35f,mmoWorld.combat_rules);')
s=s.replace('mmoWorld.combat_rules?.attack_dot??.35f);', 'mmoWorld.combat_rules?.attack_dot??.35f,mmoWorld.combat_rules);')
p.write_text(s,encoding='utf-8-sig')

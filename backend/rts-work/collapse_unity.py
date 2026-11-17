from pathlib import Path
p=Path('rts-work/unity/SquadStrategyView.cs');s=p.read_text(encoding='utf-8-sig')
a=s.index('            if(st.points!=null)for(int i=0;i<st.points.Length;i++)')
b=s.index('\n        private void DrawStrategyFog()',a)
block=s[a:b]
# Block includes the closing brace for DrawStrategyHud.
s=s[:a]+'        }\n        private void DrawStrategyPublicMarkers(SquadStrategy st)\n        {\n'+block+s[b:]
s=s.replace('BaseText(new Rect(255,14,695,23)', 'BaseText(new Rect(255,14,510,23)')
needle='            bool old=GUI.enabled;GUI.enabled=old&&StrategyReady;'
s=s.replace(needle,needle+'\n            if(MmoButton(new Rect(775,14,175,23),"지휘 접기 [Tab]"))ToggleStrategyPanel();',1)
p.write_text(s,encoding='utf-8-sig')

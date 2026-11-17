from pathlib import Path
root=Path(__file__).parent/'unity'/'script'
p=root/'MmoView.cs';s=p.read_text(encoding='utf-8-sig')
start=s.index('            BaseText(new Rect(30,12,550,38),"WARFRONT')
end=s.index('            if(mmoWorld!=null)DrawMmoField();',start)
s=s[:start]+s[end:]
start=s.index('            bool controlsEnabled=GUI.enabled;')
end=s.index('            DrawMmoLootToast();',start)
s=s[:start]+'            DrawCombatRuneBar(false);\n'+s[end:]
p.write_text(s,encoding='utf-8-sig')
p=root/'SquadStrategyView.cs';s=p.read_text(encoding='utf-8-sig').replace('(index%3)*80','(index%3)*72').replace(',76,48)',',68,46)')
s=s.replace('if(GUI.Button(cell,new GUIContent(StrategyCommandIcons.Get(action),"")))ActivateStrategyCell(i);','RuneFrame(cell,true);GUI.DrawTexture(new Rect(cell.x+13,cell.y+5,36,36),StrategyCommandIcons.Get(action),ScaleMode.ScaleToFit,true);\n                if(GUI.Button(cell,GUIContent.none,GUIStyle.none))ActivateStrategyCell(i);')
p.write_text(s,encoding='utf-8-sig')
# Render navigation in the larger field group, but never draw the extended grid there.
p=root/'DungeonFirstPersonView.cs';s=p.read_text(encoding='utf-8-sig')
s=s.replace('!MmoNavigationPointer', '!DungeonPointerBlocked')
p.write_text(s,encoding='utf-8-sig')
# Block the lower settings/menu strip too, even if custom touch settings move a button.
p=root/'DungeonFirstPersonView.cs';s=p.read_text(encoding='utf-8-sig').replace('=>MmoNavigationPointer(point)||','=>point.y>=594||MmoNavigationPointer(point)||')
p.write_text(s,encoding='utf-8-sig')
# Gear details helper now understands the real helmet slot.
source=Path('C:/Users/good6/WarfrontMVP/Assets/script/MmoAdventureUi.cs')
p=root/source.name;s=source.read_text(encoding='utf-8-sig')
s=s.replace('item.slot=="weapon"?mmoProfile.equipped_weapon:mmoProfile.equipped_armor','item.slot=="weapon"?mmoProfile.equipped_weapon:item.slot=="helmet"?mmoProfile.equipped_helmet:mmoProfile.equipped_armor')
p.write_text(s,encoding='utf-8-sig')

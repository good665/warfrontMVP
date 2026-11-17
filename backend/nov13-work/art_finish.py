from pathlib import Path
root=Path(__file__).parent/'unity'/'script'
p=root/'RetroFantasyScene.cs';s=p.read_text(encoding='utf-8-sig')
s=s.replace('model.transform.localRotation=Quaternion.Euler(0,-20,0);SetLayer(model);','model.transform.localRotation=Quaternion.Euler(0,-20,0);model.AddComponent<RuneKnightVisual>().Configure(false,new Color(.72f,.4f,1));SetLayer(model);')
s=s.replace('SetLayer(actor);actors.Add(key,actor);spawned=true;','if(!enemy)actor.AddComponent<RuneKnightVisual>().Configure(true,new Color(.72f,.4f,1));SetLayer(actor);actors.Add(key,actor);spawned=true;')
# Fog has its own material ownership. Restore it to opaque before death starts; keep it
# disabled until rebirth so it cannot replace the death materials in LateUpdate.
p.write_text(s,encoding='utf-8-sig')
p=root/'RetroActorLife.cs';s=p.read_text(encoding='utf-8-sig').replace('if(death!=null)death.SetAlive(living);','var fog=actor.GetComponent<FogActorVisibility>();\n            if(!living&&fog!=null&&fog.enabled){fog.Show(Time.unscaledTime-1);fog.Sample(Time.unscaledTime);fog.enabled=false;}\n            if(death!=null)death.SetAlive(living);\n            if(living&&fog!=null)fog.enabled=true;')
s=s.replace('public void ActorLife','public void EquipmentAppearance(string key,bool helmetEquipped)\n        {\n            if(actors.TryGetValue(key,out var actor)){var art=actor.GetComponent<RuneKnightVisual>();if(art!=null)art.Configure(helmetEquipped,new Color(.72f,.4f,1));}\n            if(portrait!=null){var art=portrait.GetComponentInChildren<RuneKnightVisual>(true);if(art!=null)art.Configure(helmetEquipped,new Color(.72f,.4f,1));}\n        }\n        public void ActorLife')
p.write_text(s,encoding='utf-8-sig')
p=root/'FantasyTownView.cs';s=p.read_text(encoding='utf-8-sig')
s=s.replace('if(lobby){if(!retroShowingTown)retroScene.ShowTown();retroShowingTown=true;return;}','if(lobby){if(!retroShowingTown)retroScene.ShowTown();retroScene.EquipmentAppearance("",!string.IsNullOrEmpty(mmoProfile?.equipped_helmet));retroShowingTown=true;return;}')
s=s.replace('retroScene.EndField();','if(!SquadModeActive&&MmoSelf!=null)retroScene.EquipmentAppearance("player:"+MmoSelf.id,!string.IsNullOrEmpty(mmoProfile?.equipped_helmet));\n            retroScene.EndField();')
s=s.replace('DrawWidgetFrame(new Rect(22,624,1234,74),true);','RuneFrame(new Rect(22,624,1234,74),true);')
s=s.replace('return GUI.Button(rect,title);','return RuneButton(rect,title);')
s=s.replace('DrawWidgetFrame(rect,true,hover);','RuneFrame(rect,true,hover);')
s=s.replace('Fill(new Rect(22,104,210,502),new Color(.20f,.18f,.29f));','RuneFrame(new Rect(22,104,210,502),true);')
s=s.replace('new Color(.10f,.09f,.16f)','new Color(.09f,.065f,.11f)')
s=s.replace('new Color(1,.66f,.31f)','new Color(.78f,.57f,.92f)')
p.write_text(s,encoding='utf-8-sig')
source=Path('C:/Users/good6/WarfrontMVP/Assets/script/WidgetArtView.cs');p=root/source.name;s=source.read_text(encoding='utf-8-sig')
s=s.replace('widgetPanel = WidgetSlice(36, 194, 716, 254, 2);','widgetPanel = RuneSurface(true);\n            widgetButtons = new[]{RuneSurface(false),RuneSurface(false),RuneSurface(false)};')
p.write_text(s,encoding='utf-8-sig')
# Helmet comparison nullable profile form.
p=root/'MmoAdventureUi.cs';s=p.read_text(encoding='utf-8-sig').replace('item.slot=="weapon"?mmoProfile?.equipped_weapon:mmoProfile?.equipped_armor','item.slot=="weapon"?mmoProfile?.equipped_weapon:item.slot=="helmet"?mmoProfile?.equipped_helmet:mmoProfile?.equipped_armor');p.write_text(s,encoding='utf-8-sig')

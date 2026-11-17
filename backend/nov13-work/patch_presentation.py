from pathlib import Path

ROOT = Path(__file__).parent / 'unity' / 'script'
def change(name, old, new):
    p=ROOT/name
    text=p.read_text(encoding='utf-8-sig')
    if old not in text: raise RuntimeError(f'Missing replacement in {name}: {old[:100]}')
    p.write_text(text.replace(old,new),encoding='utf-8-sig')

change('MmoModels.cs','public sealed class MmoProfile { public int level,xp,xp_next,gold,role,weapon_rank,armor_rank; public float attack,max_hp; public string equipped_weapon,equipped_armor;',
       'public sealed class MmoLoadout { public string weapon,armor,helmet; }\n    [Serializable] public sealed class MmoProfile { public int level,xp,xp_next,gold,role,weapon_rank,armor_rank,helmet_rank,active_loadout; public MmoLoadout[] loadouts; public float attack,max_hp; public string equipped_weapon,equipped_armor,equipped_helmet;')
change('MmoModels.cs','public sealed class MmoUpgradeRequest','public sealed class MmoLoadoutRequest { public int index; }\n    [Serializable] public sealed class MmoUpgradeRequest')
change('MmoApiClient.cs','public Task<MmoProfile> MmoUpgradeAsync', 'public Task<MmoProfile> MmoLoadoutAsync(int index) => SendAsync<MmoProfile>("POST", "/v1/mmo/loadout", JsonUtility.ToJson(new MmoLoadoutRequest {index=index}));\n        public Task<MmoProfile> MmoUpgradeAsync')
change('DungeonFirstPersonView.cs','MmoSelf.hp>0));','MmoSelf!=null));')
change('DungeonFirstPersonView.cs','MmoSelf!=null&&MmoSelf!=null','MmoSelf!=null')
change('DungeonFirstPersonView.cs','!MmoNavigationPointer(MmoUiPoint(mouse.position.ReadValue()))','!DungeonPointerBlocked(MmoUiPoint(mouse.position.ReadValue()))')
change('DungeonFirstPersonView.cs','private bool DungeonMouseAttack', 'private bool DungeonPointerBlocked(Vector2 point)=>MmoNavigationPointer(point)||mmoPad.Contains(point)||mmoAttackButton.Contains(point)||mmoDodgeButton.Contains(point)||mmoSkill1Button.Contains(point)||mmoSkill2Button.Contains(point);\n        private bool DungeonMouseAttack')
change('DungeonFirstPersonView.cs','if(actor.id!=mmoWorld.you_id&&retroScene.Project','if(actor.hp>0&&actor.id!=mmoWorld.you_id&&retroScene.Project')
change('FantasyTownView.cs','if(mmoWorld.enemies!=null)foreach(var e in mmoWorld.enemies)if(e.hp>0&&e.kind!="base"&&(!SquadModeActive||!StrategyBuildingKind(e.kind)))\n            {',
       'if(mmoWorld.enemies!=null)foreach(var e in mmoWorld.enemies){if(e.kind=="base"||(SquadModeActive&&StrategyBuildingKind(e.kind)))continue;if(e.hp<=0){retroScene.ActorLife("enemy:"+e.id,false);continue;}\n            retroScene.ActorLife("enemy:"+e.id,true);')
change('FantasyTownView.cs','{var p=MmoRenderPosition("mmo-player:"+a.id,a.x,a.y);bool attack=',
       '{if(a.hp<=0){retroScene.ActorLife("player:"+a.id,false);continue;}retroScene.ActorLife("player:"+a.id,true);var p=MmoRenderPosition("mmo-player:"+a.id,a.x,a.y);bool attack=')
# The portrait camera must remain enabled while equipment is open in the field.
change('RetroFantasyScene.cs','townMode=false;town.SetActive(false);portrait.SetActive(false);','townMode=false;town.SetActive(false);portrait.SetActive(true);')
# Remove old .55s roll logic: one lifecycle now owns all corpse presentation.
change('RetroFantasyScene.cs','float phase=1-(expires-Time.unscaledTime)/.55f;\n                    var corpse=actors[key];corpse.transform.localRotation=Quaternion.Euler(0,corpse.transform.localEulerAngles.y,phase*85);\n                    corpse.transform.localPosition+=Vector3.down*Time.unscaledDeltaTime*.4f;\n                    var dyingAnimation=corpse.GetComponent<Animation>();if(dyingAnimation!=null)dyingAnimation.Stop();continue;',
       'var corpse=actors[key];var death=corpse.GetComponent<ActorDeathVisual>()??corpse.AddComponent<ActorDeathVisual>();death.SetAlive(false);continue;')
change('RetroFantasyScene.cs','Time.unscaledTime+.55f','Time.unscaledTime+ActorDeathVisual.Duration')
# Prevent ThirdPerson from reactivating fully faded bodies (we use renderer hiding, retaining orbit anchor).
change('RetroFantasyScene.cs','actor.name=key;','actor.name=key;')
change('MmoView.cs','private readonly Rect mmoField = new Rect(20, 126, 1240, 460);','private readonly Rect mmoField = new Rect(20, 14, 1240, 572);')
change('MmoView.cs','if(mmoPanel=="controls"){DrawMmoControlSettings();return;}','if(mmoPanel=="controls"){DrawMmoControlSettings();return;}\n            if(mmoPanel=="equipment"){DrawMmoEquipmentPanel();return;}')
# Field projection and camera render ratio must agree after removing the header band.
change('RetroFantasyScene.cs','target.width=1240;target.height=460','target.width=1240;target.height=572')
change('RetroFantasyScene.cs','view.aspect=1240f/460;view.orthographicSize=460f/100;','view.aspect=1240f/572;view.orthographicSize=572f/100;')
change('RetroFantasyScene.cs','scroll.y+230','scroll.y+286')
change('RetroFantasyScene.cs','(1-projected.y)*460','(1-projected.y)*572')
# Compact center skill bar; settings key v2 avoids inheriting the old right-aligned defaults.
change('MmoControlSettings.cs','warfront.playSettings.v1','warfront.playSettings.v2')
change('MmoControlSettings.cs','new Rect(690,604,140,80)','new Rect(374,608,126,80)')
change('MmoControlSettings.cs','new Rect(840,604,120,80)','new Rect(506,608,126,80)')
change('MmoControlSettings.cs','new Rect(970,604,120,80)','new Rect(638,608,126,80)')
change('MmoControlSettings.cs','new Rect(1100,604,140,80)','new Rect(770,608,126,80)')
change('MmoControlSettings.cs','MmoNavigationPointer(point))continue','DungeonPointerBlocked(point))continue')
# IMGUI navigation is drawn in field-local coordinates, so panel extends into the lower HUD.
change('SquadStrategyView.cs','new Rect(mmoField.width-264,mmoField.height-224,252,212)','new Rect(mmoField.width-244,720-mmoField.y-218,232,206)')
change('SquadStrategyView.cs','BaseText(new Rect(255,14,510,28),','BaseText(new Rect(245,14,510,28),')
change('SquadStrategyView.cs','var panel=strategyPanel;Fill(panel,new Color(.025f,.04f,.075f,.95f));','var panel=strategyPanel;RuneFrame(panel,true);')
change('SquadStrategyView.cs','panel.y+3,236','panel.y+3,216')
change('SquadStrategyView.cs','panel.y+187,236','panel.y+180,216')
# Cells are expressed relative to the panel; fit 3 columns within the narrower frame.
change('SquadStrategyView.cs','var cell=StrategyCellRect(i);string action=', 'var cell=StrategyCellRect(i);string action=')
change('SquadView.cs','Fill(new Rect(0,0,1280,720),new Color(.08f,.10f,.15f));','Fill(new Rect(0,0,1280,720),new Color(.055f,.05f,.075f));\n            if(mmoWorld!=null){DrawSquadBattle();return;}')
# Keep the grid at the actual screen edge without clipping at the field viewport.
change('SquadView.cs','DrawStrategyHud();','')
change('MmoView.cs','GUI.EndGroup();\n        }\n        private void MmoHealth','GUI.EndGroup();\n        }\n        private void MmoHealth')

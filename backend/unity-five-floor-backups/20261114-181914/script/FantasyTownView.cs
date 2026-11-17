using UnityEngine;

namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private RetroFantasyScene retroScene;
        private bool retroShowingTown;
        private readonly Color parchment=new Color(.91f,.89f,1);
        private readonly Color townInk=new Color(.13f,.12f,.20f);
        private readonly Color townGold=new Color(.78f,.57f,.92f);
        private readonly Rect townViewRect=new Rect(250,104,1006,502);

        private void UpdateRetroPresentation()
        {
            EnsureMmoSettings();UpdateDungeonLook();
            bool lobby=ready&&!busy&&(screen==Screen.Lobby||(screen==Screen.Mmo&&mmoPanel=="equipment"&&mmoWorld==null));
            bool encounter=ready&&!busy&&screen==Screen.Mmo&&mmoWorld!=null;
            if(!lobby&&!encounter){if(retroScene!=null)retroScene.gameObject.SetActive(false);return;}
            if(retroScene==null)
            {
                var root=new GameObject("Warfront Retro Fantasy Presentation");
                retroScene=root.AddComponent<RetroFantasyScene>();retroScene.Initialize();retroShowingTown=true;
            }
            retroScene.gameObject.SetActive(true);
            if(lobby){if(!retroShowingTown)retroScene.ShowTown();retroScene.EquipmentAppearance("",!string.IsNullOrEmpty(mmoProfile?.equipped_helmet));retroShowingTown=true;return;}
            if(!retroScene.Available)return;
            retroShowingTown=false;retroScene.BeginField(mmoWorld,MmoCamera);
            if(mmoWorld.enemies!=null)foreach(var e in mmoWorld.enemies){if(e.kind=="base"||(SquadModeActive&&StrategyBuildingKind(e.kind)))continue;if(e.hp<=0){retroScene.ActorLife("enemy:"+e.id,false);continue;}
            retroScene.PrepareFiveFloorActor("enemy:"+e.id,e.kind,e.character);retroScene.ActorLife("enemy:"+e.id,true);var p=MmoRenderPosition("mmo-enemy:"+e.id,e.x,e.y);var self=MmoSelf;retroScene.Actor("enemy:"+e.id,p.x,p.y,SquadModeActive?e.fx:(self?.x??e.x+1)-e.x,SquadModeActive?e.fy:(self?.y??e.y)-e.y,false,false,!SquadModeActive||e.kind=="grunt"||e.kind=="elite",e.kind=="boss"||e.kind=="elite");retroScene.SetActorAppearance("enemy:"+e.id,SquadModeActive?0:-1,e.hit_flash>0);retroScene.FiveFloorPose("enemy:"+e.id,e.jump_left,e.transition_left);if(SquadModeActive){retroScene.SquadSide("enemy:"+e.id,false,e.hit_flash>0);retroScene.SquadRole("enemy:"+e.id,e.kind=="scout"?"archer":e.kind);retroScene.SquadAction("enemy:"+e.id,e.action_id,e.action_kind,e.action_left,e.action_duration,e.action_fx,e.action_fy,e.dodge_left,Time.realtimeSinceStartup-mmoLastResponse,false,e.action_kind=="heavy"?(mmoWorld.combat_rules?.heavy_reach??210):(mmoWorld.combat_rules?.attack_reach??145),mmoWorld.combat_rules?.attack_dot??.35f,mmoWorld.combat_rules,e.charge_ratio);}}
            if(mmoWorld.players!=null)foreach(var a in mmoWorld.players)
            {if(a.hp<=0){retroScene.ActorLife("player:"+a.id,false);continue;}retroScene.PrepareFiveFloorActor("player:"+a.id,a.kind,a.character);retroScene.ActorLife("player:"+a.id,true);var p=MmoRenderPosition("mmo-player:"+a.id,a.x,a.y);bool attack=mmoMuzzleUntil.TryGetValue(a.id,out float until)&&until>Time.realtimeSinceStartup;retroScene.Actor("player:"+a.id,p.x,p.y,a.fx,a.fy,!SquadModeActive&&attack,!SquadModeActive&&a.dodge_left>0,false,false);retroScene.SetActorAppearance("player:"+a.id,a.role,a.hit_flash>0);retroScene.FiveFloorPose("player:"+a.id,a.jump_left,a.transition_left);if(SquadModeActive){retroScene.SquadSide("player:"+a.id,true,a.hit_flash>0);retroScene.SquadRole("player:"+a.id,a.kind=="scout"?"archer":a.kind);retroScene.SquadAction("player:"+a.id,a.action_id,a.action_kind,a.action_left,a.action_duration,a.action_fx,a.action_fy,a.dodge_left,Time.realtimeSinceStartup-mmoLastResponse,a.id==mmoWorld.you_id,a.action_kind=="heavy"?(mmoWorld.combat_rules?.heavy_reach??210):(mmoWorld.combat_rules?.attack_reach??145),mmoWorld.combat_rules?.attack_dot??.35f,mmoWorld.combat_rules,a.charge_ratio);}}
            if(!SquadModeActive&&MmoSelf!=null)retroScene.EquipmentAppearance("player:"+MmoSelf.id,!string.IsNullOrEmpty(mmoProfile?.equipped_helmet));
            if(FiveFloorActive)retroScene.FiveFloorEnvironment(squadSnapshot);retroScene.EndField();
            var ownActor=MmoSelf;if(ownActor!=null){var p=MmoRenderPosition("mmo-player:"+ownActor.id,ownActor.x,ownActor.y);if(StrategicViewActive)retroScene.StrategicView(p.x,p.y,strategicZoom,mmoWorld.world_width,mmoWorld.world_height);else retroScene.ThirdPerson("player:"+ownActor.id,p.x,p.y,dungeonYaw,dungeonPitch,dungeonDistance);}
            retroScene.Hazards(mmoWorld.hazards);retroScene.EnemyTelegraphs(mmoWorld.enemies);if(SquadModeActive){retroScene.SquadObjectives(squadSnapshot);retroScene.StrategyObjectives(squadSnapshot);retroScene.SquadBombs(mmoWorld.bombs,Time.realtimeSinceStartup-mmoLastResponse,squadSnapshot.team);retroScene.SquadProjectiles(mmoWorld.projectiles,Time.realtimeSinceStartup-mmoLastResponse);}
        }
        private void DisposeRetroPresentation(){DisposeSquadConnection();DisposeMmoCombatFeedback();ReleaseDungeonCursor();if(retroScene!=null)Destroy(retroScene.gameObject);retroScene=null;}
        private bool HasRetroField=>retroScene!=null&&retroScene.gameObject.activeSelf&&retroScene.Available&&!retroShowingTown;

        private void DrawFantasyTownLobby()
        {
            Fill(new Rect(0,0,1280,720),townInk);
            Fill(new Rect(0,0,1280,87),new Color(.09f,.065f,.11f));
            Fill(new Rect(0,86,1280,2),townGold);
            BaseText(new Rect(27,12,300,39),"WARFRONT",30,parchment);
            BaseText(new Rect(29,53,360,20),"MINI DUNGEON · 모험가의 거점",12,townGold);
            BaseText(new Rect(462,17,420,28),data.DisplayName+" 님, 던전 거점에 오신 걸 환영합니다",18,parchment);
            BaseText(new Rect(462,48,500,22),mmoProfile==null?"장비를 준비하고 동료와 함께 모험을 시작하세요":$"LV {mmoProfile.level}  ·  골드 {mmoProfile.gold}  ·  다음 모험을 준비하세요",13,townGold);
            if(TownButton(new Rect(902,23,155,40),"조작 · 소리 설정"))OpenMmoControlSettings();
            if(TownButton(new Rect(1073,23,175,40),"접속 · 환경 설정"))OpenConnectionSettings();
            RuneFrame(new Rect(22,104,210,502),true);
            BaseText(new Rect(36,117,182,28),"12간지 영웅",20,parchment);
            DrawFiveFloorSelection(new Rect(29,148,196,245));
            BaseText(new Rect(36,399,182,22),"나의 동물 영웅",17,townGold);
            BaseText(new Rect(36,429,182,20),"Q 스킬 · E 필살기 · Space 점프",11,parchment);



            if(retroScene!=null&&retroScene.View!=null)GUI.DrawTexture(townViewRect,retroScene.View,ScaleMode.StretchToFill,false);
            BaseText(new Rect(270,116,240,32),"5층 본진 전장",24,parchment);
            BaseText(new Rect(272,149,240,23),"사람 대전 · 컴퓨터 대전",13,parchment);



            TownLandmark(new Vector3(-6,1.5f,-3.5f),"분대 지휘소","1대1 · 본진 파괴",OpenSquadLobby);

            RuneFrame(new Rect(22,624,1234,74),true);
            BaseText(new Rect(39,635,205,25),"오늘은 어디로 떠날까요?",17,parchment);
            BaseText(new Rect(39,667,210,18),"WASD 이동 · 좌클릭 공격 · Space 점프",10,parchment);

            if(TownButton(new Rect(514,639,230,45),"분대 PvP · 본진 공략",true))OpenSquadLobby();


        }
        private bool TownButton(Rect rect,string title,bool light=false)
        {
            return RuneButton(rect,title);
        }

        private void TownLandmark(Vector3 anchor,string title,string detail,System.Action action)
        {
            if(retroScene==null)return;
            Vector2 uv=retroScene.TownLabel(anchor);Vector2 point=townViewRect.position+Vector2.Scale(uv,townViewRect.size);
            var rect=new Rect(point.x-91,point.y-57,182,55);
            bool hover=rect.Contains(Event.current.mousePosition);
            Fill(new Rect(rect.x+3,rect.y+4,rect.width,rect.height),new Color(0,0,0,.30f));
            RuneFrame(rect,true,hover);Fill(new Rect(rect.x+12,rect.y+4,rect.width-24,2),townGold);
            BaseText(new Rect(rect.x+8,rect.y+4,166,26),title,17,parchment,TextAnchor.MiddleCenter);
            BaseText(new Rect(rect.x+8,rect.y+32,166,17),detail,11,townGold,TextAnchor.MiddleCenter);
            if(GUI.Button(rect,GUIContent.none,GUIStyle.none))action();
        }
    }
}

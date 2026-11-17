using UnityEngine;

namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private RetroFantasyScene retroScene;
        private bool retroShowingTown;
        private readonly Color parchment=new Color(.91f,.89f,1);
        private readonly Color townInk=new Color(.13f,.12f,.20f);
        private readonly Color townGold=new Color(1,.66f,.31f);
        private readonly Rect townViewRect=new Rect(250,104,1006,502);

        private void UpdateRetroPresentation()
        {
            EnsureMmoSettings();UpdateDungeonLook();
            bool lobby=ready&&!busy&&screen==Screen.Lobby;
            bool encounter=ready&&!busy&&screen==Screen.Mmo&&mmoWorld!=null;
            if(!lobby&&!encounter){if(retroScene!=null)retroScene.gameObject.SetActive(false);return;}
            if(retroScene==null)
            {
                var root=new GameObject("Warfront Retro Fantasy Presentation");
                retroScene=root.AddComponent<RetroFantasyScene>();retroScene.Initialize();retroShowingTown=true;
            }
            retroScene.gameObject.SetActive(true);
            if(lobby){if(!retroShowingTown)retroScene.ShowTown();retroShowingTown=true;return;}
            if(!retroScene.Available)return;
            retroShowingTown=false;retroScene.BeginField(mmoWorld,MmoCamera);
            if(mmoWorld.enemies!=null)foreach(var e in mmoWorld.enemies)if(e.hp>0&&e.kind!="base"&&(!SquadModeActive||!StrategyBuildingKind(e.kind)))
            {var p=MmoRenderPosition("mmo-enemy:"+e.id,e.x,e.y);var self=MmoSelf;retroScene.Actor("enemy:"+e.id,p.x,p.y,SquadModeActive?e.fx:(self?.x??e.x+1)-e.x,SquadModeActive?e.fy:(self?.y??e.y)-e.y,false,false,!SquadModeActive,e.kind=="boss");retroScene.SetActorAppearance("enemy:"+e.id,SquadModeActive?0:-1,e.hit_flash>0);if(SquadModeActive){retroScene.SquadSide("enemy:"+e.id,false,e.hit_flash>0);retroScene.SquadRole("enemy:"+e.id,e.kind=="scout"?"archer":e.kind);retroScene.SquadAction("enemy:"+e.id,e.action_id,e.action_kind,e.action_left,e.action_duration,e.action_fx,e.action_fy,e.dodge_left,Time.realtimeSinceStartup-mmoLastResponse,false,e.action_kind=="heavy"?(mmoWorld.combat_rules?.heavy_reach??210):(mmoWorld.combat_rules?.attack_reach??145),mmoWorld.combat_rules?.attack_dot??.35f,mmoWorld.combat_rules,e.charge_ratio);}}
            if(mmoWorld.players!=null)foreach(var a in mmoWorld.players)if(!SquadModeActive||a.hp>0)
            {var p=MmoRenderPosition("mmo-player:"+a.id,a.x,a.y);bool attack=mmoMuzzleUntil.TryGetValue(a.id,out float until)&&until>Time.realtimeSinceStartup;retroScene.Actor("player:"+a.id,p.x,p.y,a.fx,a.fy,!SquadModeActive&&attack,!SquadModeActive&&a.dodge_left>0,false,false);retroScene.SetActorAppearance("player:"+a.id,a.role,a.hit_flash>0);if(SquadModeActive){retroScene.SquadSide("player:"+a.id,true,a.hit_flash>0);retroScene.SquadRole("player:"+a.id,a.kind=="scout"?"archer":a.kind);retroScene.SquadAction("player:"+a.id,a.action_id,a.action_kind,a.action_left,a.action_duration,a.action_fx,a.action_fy,a.dodge_left,Time.realtimeSinceStartup-mmoLastResponse,a.id==mmoWorld.you_id,a.action_kind=="heavy"?(mmoWorld.combat_rules?.heavy_reach??210):(mmoWorld.combat_rules?.attack_reach??145),mmoWorld.combat_rules?.attack_dot??.35f,mmoWorld.combat_rules,a.charge_ratio);}}
            retroScene.EndField();
            var ownActor=MmoSelf;if(ownActor!=null){var p=MmoRenderPosition("mmo-player:"+ownActor.id,ownActor.x,ownActor.y);retroScene.ThirdPerson("player:"+ownActor.id,p.x,p.y,dungeonYaw,dungeonPitch,dungeonDistance);}
            retroScene.Hazards(mmoWorld.hazards);retroScene.EnemyTelegraphs(mmoWorld.enemies);if(SquadModeActive){retroScene.SquadObjectives(squadSnapshot);retroScene.StrategyObjectives(squadSnapshot);retroScene.SquadBombs(mmoWorld.bombs,Time.realtimeSinceStartup-mmoLastResponse,squadSnapshot.team);retroScene.SquadProjectiles(mmoWorld.projectiles,Time.realtimeSinceStartup-mmoLastResponse);}
        }
        private void DisposeRetroPresentation(){DisposeSquadConnection();DisposeMmoCombatFeedback();ReleaseDungeonCursor();if(retroScene!=null)Destroy(retroScene.gameObject);retroScene=null;}
        private bool HasRetroField=>retroScene!=null&&retroScene.gameObject.activeSelf&&retroScene.Available&&!retroShowingTown;

        private void DrawFantasyTownLobby()
        {
            Fill(new Rect(0,0,1280,720),townInk);
            Fill(new Rect(0,0,1280,87),new Color(.10f,.09f,.16f));
            Fill(new Rect(0,86,1280,2),townGold);
            BaseText(new Rect(27,12,300,39),"WARFRONT",30,parchment);
            BaseText(new Rect(29,53,360,20),"MINI DUNGEON · 모험가의 거점",12,townGold);
            BaseText(new Rect(462,17,420,28),data.DisplayName+" 님, 던전 거점에 오신 걸 환영합니다",18,parchment);
            BaseText(new Rect(462,48,500,22),mmoProfile==null?"장비를 준비하고 동료와 함께 모험을 시작하세요":$"LV {mmoProfile.level}  ·  골드 {mmoProfile.gold}  ·  다음 모험을 준비하세요",13,townGold);
            if(TownButton(new Rect(902,23,155,40),"조작 · 소리 설정"))OpenMmoControlSettings();
            if(TownButton(new Rect(1073,23,175,40),"접속 · 환경 설정"))OpenConnectionSettings();
            Fill(new Rect(22,104,210,502),new Color(.20f,.18f,.29f));
            BaseText(new Rect(36,117,182,28),"나의 모험가",20,parchment);
            if(retroScene!=null&&retroScene.Portrait!=null)GUI.DrawTexture(new Rect(29,148,196,245),retroScene.Portrait,ScaleMode.StretchToFill,false);
            BaseText(new Rect(36,399,182,22),"꼬마 던전 기사",17,townGold);
            BaseText(new Rect(36,429,182,20),"검 · 방패 · 3인칭 액션 전투",11,parchment);
            if(TownButton(new Rect(36,467,182,41),"장비와 소지품"))OpenMmoEquipment();
            if(TownButton(new Rect(36,518,182,35),"캐릭터 · 퀘스트"))OpenMmoProfile();
            if(TownButton(new Rect(36,564,182,28),"3인칭 조작 안내"))MmoOpenPanel("guide");
            if(retroScene!=null&&retroScene.View!=null)GUI.DrawTexture(townViewRect,retroScene.View,ScaleMode.StretchToFill,false);
            BaseText(new Rect(270,116,240,32),"미니 던전 거점",24,parchment);
            BaseText(new Rect(272,149,240,23),"구역 이름표를 눌러 이동하세요",13,parchment);
            TownLandmark(new Vector3(-6,1.7f,3),"탐험 관문","공동 사냥터",()=>OpenMmoWorld("frontier"));
            TownLandmark(new Vector3(0,1.7f,5),"고대 유적 관문","파티 · 보스 원정",()=>OpenMmoWorld("ruins"));
            TownLandmark(new Vector3(6,1.7f,3),"장비 보관실","장비 · 강화",OpenMmoEquipment);
            TownLandmark(new Vector3(-6,1.5f,-3.5f),"분대 지휘소","1대1 · 본진 파괴",OpenSquadLobby);
            TownLandmark(new Vector3(6,1.5f,-3.5f),"퀘스트 기록실","캐릭터 · 퀘스트",OpenMmoProfile);
            DrawWidgetFrame(new Rect(22,624,1234,74),true);
            BaseText(new Rect(39,635,205,25),"오늘은 어디로 떠날까요?",17,parchment);
            BaseText(new Rect(39,667,210,18),"이동 WASD · 공격 Space · 회피 Shift",10,parchment);
            if(TownButton(new Rect(270,639,230,45),"공동 사냥터",true))OpenMmoWorld("frontier");
            if(TownButton(new Rect(514,639,230,45),"분대 PvP · 본진 공략",true))OpenSquadLobby();
            if(TownButton(new Rect(758,639,230,45),"고대 유적 원정",true))OpenMmoWorld("ruins");
            if(TownButton(new Rect(1002,639,235,45),"파티 모집",true))MmoOpenPanel("party");
        }
        private bool TownButton(Rect rect,string title,bool light=false)
        {
            return GUI.Button(rect,title);
        }

        private void TownLandmark(Vector3 anchor,string title,string detail,System.Action action)
        {
            if(retroScene==null)return;
            Vector2 uv=retroScene.TownLabel(anchor);Vector2 point=townViewRect.position+Vector2.Scale(uv,townViewRect.size);
            var rect=new Rect(point.x-91,point.y-57,182,55);
            bool hover=rect.Contains(Event.current.mousePosition);
            Fill(new Rect(rect.x+3,rect.y+4,rect.width,rect.height),new Color(0,0,0,.30f));
            DrawWidgetFrame(rect,true,hover);Fill(new Rect(rect.x+12,rect.y+4,rect.width-24,2),townGold);
            BaseText(new Rect(rect.x+8,rect.y+4,166,26),title,17,parchment,TextAnchor.MiddleCenter);
            BaseText(new Rect(rect.x+8,rect.y+32,166,17),detail,11,townGold,TextAnchor.MiddleCenter);
            if(GUI.Button(rect,GUIContent.none,GUIStyle.none))action();
        }
    }
}

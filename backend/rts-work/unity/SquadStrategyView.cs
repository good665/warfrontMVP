using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private string strategySquad="",strategyEconomy="none",strategyFormation="none",strategyPlacement="",strategyMapCommand="move";
        private Vector2 strategyBuildPoint;
        private bool strategyExpanded;
        private readonly Rect strategyPanel=new Rect(245,10,715,235);
        private void ResetStrategy(){strategyExpanded=false;strategySquad="";strategyEconomy="none";strategyFormation="none";strategyPlacement="";strategyMapCommand="move";}
        private bool StrategyPointer(Vector2 p)=>new Rect(245,10,715,strategyExpanded?312:38).Contains(p)||new Rect(14,256,225,98).Contains(p);
        private void ToggleStrategyPanel(){strategyExpanded=!strategyExpanded;ReleaseDungeonCursor();}
        private bool StrategySelectionLocked=>squadOrder!="none"||strategyFormation!="none"||strategyPlacement.Length>0||strategyEconomy.StartsWith("build_");
        private void SelectStrategySquad(string id){if(!StrategySelectionLocked)strategySquad=id;}
        private static bool StrategyBuildingKind(string kind)=>kind=="barracks"||kind=="outpost"||kind=="tower"||kind=="academy";
        private void ConsumeStrategyIntent(SquadInput input,bool controls)
        {
            input.squad_id=strategySquad;input.economy=controls?strategyEconomy:"none";input.formation=controls?strategyFormation:"none";
            if(controls&&strategyEconomy.StartsWith("build_")){input.order_x=strategyBuildPoint.x;input.order_y=strategyBuildPoint.y;input.command="none";}
            if(controls){strategyEconomy="none";strategyFormation="none";}
        }
        private SquadInput PrepareSquadRetry(SquadInput original,bool controls)
        {
            if(controls)return original;
            bool strategy=(!string.IsNullOrEmpty(original.economy)&&original.economy!="none")||(!string.IsNullOrEmpty(original.formation)&&original.formation!="none")||(!string.IsNullOrEmpty(original.command)&&original.command!="none");
            if(strategy)return new SquadInput{sequence=original.sequence,squad_id=original.squad_id,economy=original.economy,formation=original.formation,command=original.command,order_x=original.order_x,order_y=original.order_y,target_id=original.target_id,aim_x=original.aim_x,aim_y=original.aim_y};
            return new SquadInput{sequence=++squadSequence,aim_x=MmoSelf?.x??0,aim_y=MmoSelf?.y??0};
        }
        private void ValidateStrategySelection()
        {
            if(strategySquad==""||strategySquad=="all")return;
            if(squadSnapshot?.strategy?.squads!=null)foreach(var s in squadSnapshot.strategy.squads)if(s.id==strategySquad)return;
            strategySquad="";
        }
        private bool StrategyReady=>SquadInBattle&&mmoConnected&&!mmoSuspended&&mmoPanel.Length==0&&MmoSelf!=null&&MmoSelf.hp>0&&!squadExit&&Time.realtimeSinceStartup-mmoLastResponse<1.2f;
        private void UpdateStrategyPointer()
        {
            if(!StrategyReady){strategyPlacement="";strategyEconomy="none";strategyFormation="none";return;}
            if(Keyboard.current!=null&&Keyboard.current.tabKey.wasPressedThisFrame)ToggleStrategyPanel();
            if(Keyboard.current!=null&&Keyboard.current.escapeKey.wasPressedThisFrame)strategyPlacement="";
            var mouse=Mouse.current;Vector2 screenPoint=Vector2.zero;bool pressed=false;
            if(mouse!=null&&mouse.leftButton.wasPressedThisFrame&&Cursor.lockState!=CursorLockMode.Locked){screenPoint=mouse.position.ReadValue();pressed=true;}
            if(Touchscreen.current!=null)foreach(var touch in Touchscreen.current.touches)if(touch.press.wasPressedThisFrame){screenPoint=touch.position.ReadValue();pressed=true;break;}
            if(!pressed)return;
            var local=MmoUiPoint(screenPoint)-mmoField.position;
            if(!squadMap.Contains(local))return;
            var inner=new Rect(squadMap.x+8,squadMap.y+8,squadMap.width-16,squadMap.height-16);
            squadOrderPoint=new Vector2(Mathf.Clamp01((local.x-inner.x)/inner.width)*mmoWorld.world_width,Mathf.Clamp01((local.y-inner.y)/inner.height)*mmoWorld.world_height);
            squadOrderTarget="";
            if(strategyPlacement.Length>0){strategyEconomy=strategyPlacement;strategyBuildPoint=squadOrderPoint;strategyPlacement="";squadOrder="none";}
            else squadOrder=strategyMapCommand;
        }
        private bool StrategyBuy(Rect rect,string label,string action,int cost,bool allowed=true)
        {
            bool old=GUI.enabled;GUI.enabled=old&&allowed&&strategyEconomy=="none"&&(squadSnapshot.strategy.supplies>=cost);
            bool clicked=MmoButton(rect,label+" "+cost);GUI.enabled=old;
            if(clicked){ReleaseDungeonCursor();if(action.StartsWith("build_"))strategyPlacement=action;else strategyEconomy=action;}
            return clicked;
        }
        private static string StrategyKind(string kind)=>kind=="guard"?"수호병":kind=="archer"?"궁수":kind=="healer"?"치유사":kind=="scout"?"정찰병":kind=="barracks"?"병영":kind=="outpost"?"전초기지":kind=="tower"?"방어탑":kind=="academy"?"연구소":kind;
        private static string StrategyErrorLabel(string code)
        {
            switch(code){case "insufficient_supplies":return "보급이 부족합니다";case "population_limit":return "인구 또는 분대 한도에 도달했습니다";case "hero_dead":return "영웅 부활 후 명령할 수 있습니다";case "invalid_action":return "사용할 수 없는 명령입니다";case "building_exists":return "이미 건설한 건물입니다";case "invalid_build_location":return "건설할 수 없는 위치입니다";case "academy_required":return "완성된 연구소가 필요합니다";case "already_researched":return "이미 완료한 연구입니다";case "research_busy":return "연구가 진행 중입니다";default:return "명령을 실행할 수 없습니다 ("+code+")";}
        }
        private string StrategySelectionLabel(SquadStrategy st)
        {
            if(strategySquad=="all")return "전체 분대 · 각 분대 대형 유지";
            if(strategySquad=="")return "기본 동료 · 대형 "+(strategyFormation=="none"?"기본":StrategyFormationLabel(strategyFormation));
            if(st.squads!=null)foreach(var s in st.squads)if(s.id==strategySquad)return StrategyKind(s.kind)+" · 대형 "+StrategyFormationLabel(strategyFormation=="none"?s.formation:strategyFormation);
            return "기본 동료";
        }
        private static string StrategyFormationLabel(string formation)=>formation=="wedge"?"쐐기":formation=="spread"?"산개":"횡대";
        private void DrawStrategyHud()
        {
            var st=squadSnapshot.strategy;if(st==null)return;
            DrawStrategyBuildingLabels();
            DrawStrategyPublicMarkers(st);
            if(!strategyExpanded)
            {
                Fill(new Rect(245,10,715,38),new Color(.025f,.04f,.075f,.94f));
                BaseText(new Rect(255,14,510,28),$"보급 {st.supplies:0} (+{st.income:0}/초) · 인구 {st.population}/{st.population_cap} · "+StrategySelectionLabel(st),12,baseGold);
                bool enabled=GUI.enabled;GUI.enabled=enabled&&StrategyReady;
                if(MmoButton(new Rect(775,14,175,28),"전략 지휘 [Tab]"))ToggleStrategyPanel();GUI.enabled=enabled;
                if(strategyPlacement.Length>0)BaseText(new Rect(255,49,690,22),"미니맵 클릭: "+StrategyKind(strategyPlacement.Substring(6))+" 배치 · Esc 취소",12,baseGold);
                else if(!string.IsNullOrEmpty(st.action_error))BaseText(new Rect(255,49,690,22),StrategyErrorLabel(st.action_error),12,baseGold);
                return;
            }
            Fill(strategyPanel,new Color(.025f,.04f,.075f,.95f));
            BaseText(new Rect(255,14,510,23),$"보급 {st.supplies:0} (+{st.income:0}/초)  ·  인구 {st.population}/{st.population_cap}  ·  생산 분대 최대 {st.squad_cap}  ·  기술 {st.tech_attack}/{st.tech_armor}/{st.tech_recon}",13,baseGold);
            bool old=GUI.enabled;GUI.enabled=old&&StrategyReady;
            if(MmoButton(new Rect(775,14,175,23),"지휘 접기 [Tab]"))ToggleStrategyPanel();
            string[] units={"guard","archer","healer","scout"};int[] costs={60,75,90,45};
            for(int i=0;i<4;i++)StrategyBuy(new Rect(255+i*174,40,168,26),StrategyKind(units[i]),"train_"+units[i],costs[i],(st.queue?.Length??0)<3&&st.population+(i==3?1:3)<=st.population_cap&&(st.squads?.Length??0)+(st.queue?.Length??0)<st.squad_cap);
            string[] buildings={"barracks","outpost","tower","academy"};int[] prices={100,80,100,120};
            for(int i=0;i<4;i++)StrategyBuy(new Rect(255+i*174,70,168,26),StrategyKind(buildings[i])+" 건설","build_"+buildings[i],prices[i]);
            bool academy=false;if(st.buildings!=null)foreach(var b in st.buildings)if(b.team==squadSnapshot.team&&b.kind=="academy"&&b.hp>0&&b.remaining<=0)academy=true;
            string[] techs={"attack","armor","recon"};string[] labels={"공격 연구","방어 연구","정찰 연구"};int[] levels={st.tech_attack,st.tech_armor,st.tech_recon};
            for(int i=0;i<3;i++){bool pending=false;if(st.research!=null)foreach(var r in st.research)if(r.id==techs[i]||r.id=="research_"+techs[i])pending=true;StrategyBuy(new Rect(255+i*174,100,168,26),labels[i],"research_"+techs[i],i==2?80:100,academy&&levels[i]==0&&!pending&&(st.research?.Length??0)==0);}
            if(MmoButton(new Rect(777,100,168,26),strategyMapCommand=="move"?"지도: 이동":"지도: 공격 이동")){strategyMapCommand=strategyMapCommand=="move"?"attack_move":"move";ReleaseDungeonCursor();}
            if(MmoButton(new Rect(255,130,112,26),(strategySquad==""?"● ":"")+"기본 동료"))SelectStrategySquad("");
            if(MmoButton(new Rect(372,130,90,26),(strategySquad=="all"?"● ":"")+"전체"))SelectStrategySquad("all");
            if(st.squads!=null)for(int i=0;i<Mathf.Min(3,st.squads.Length);i++){var s=st.squads[i];if(MmoButton(new Rect(467+i*160,130,155,26),(strategySquad==s.id?"● ":"")+StrategyKind(s.kind)+$" {s.alive}/{s.members}"))SelectStrategySquad(s.id);}
            string[] forms={"line","wedge","spread"};string[] names={"횡대","쐐기","산개"};
            for(int i=0;i<3;i++)if(MmoButton(new Rect(255+i*116,160,110,26),names[i]))strategyFormation=forms[i];
            if(MmoButton(new Rect(603,160,168,26),"이동 지점 지정")){strategyMapCommand="move";strategyPlacement="";ReleaseDungeonCursor();}
            if(MmoButton(new Rect(777,160,168,26),"공격 이동 지정")){strategyMapCommand="attack_move";strategyPlacement="";ReleaseDungeonCursor();}
            GUI.enabled=old;
            string queue=$"생산 {st.queue?.Length??0}/3 (차례대로): ";if(st.queue!=null)for(int i=0;i<st.queue.Length;i++){var q=st.queue[i];queue+=StrategyKind(q.kind)+(i==0?$" {q.remaining:0}s  ":$" 대기 {q.duration:0}s  ");}
            if(st.research!=null)foreach(var r in st.research)queue+="연구 "+r.id+$" {r.remaining:0}s  ";
            BaseText(new Rect(255,189,690,20),queue,12,baseCyan);
            BaseText(new Rect(255,211,690,28),strategyPlacement.Length>0?StrategyKind(strategyPlacement.Substring(6))+" 배치: 미니맵을 클릭하세요 · Esc 취소":!string.IsNullOrEmpty(st.action_error)?"명령 거절: "+StrategyErrorLabel(st.action_error):"Esc로 시점 해제 → 미니맵 클릭: 선택 분대 목적지 / 건설 위치 지정",12,baseGold);
            Fill(new Rect(245,246,715,76),new Color(.025f,.04f,.075f,.92f));
            BaseText(new Rect(255,248,695,22),"선택: "+StrategySelectionLabel(st)+(StrategySelectionLocked?" · 명령 전송 대기":""),12,baseCyan);
            BaseText(new Rect(255,270,695,22),"병영: 생산 가속 · 전초기지: 시야 · 방어탑: 주변 받는 피해 감소 (자동 공격 없음)",12,baseMuted);
            BaseText(new Rect(255,292,695,22),"정찰 연구: 시야 +120 · 수호병: 궁수 피해 감소 · 궁수: 치유사에 추가 피해 · 정찰병: 낮은 체력",11,baseMuted);
            if(Keyboard.current!=null&&Keyboard.current.escapeKey.wasPressedThisFrame)strategyPlacement="";
        }
        private void DrawStrategyPublicMarkers(SquadStrategy st)
        {
            if(st.points!=null)for(int i=0;i<st.points.Length;i++){var p=st.points[i];var c=p.owner==squadSnapshot.team?baseCyan:p.owner<0?baseMuted:new Color(1,.4f,.3f);BaseText(new Rect(20,260+i*28,220,25),p.name+" · "+(p.contested?"교전 중":p.owner<0?"중립":p.owner==squadSnapshot.team?"아군":"적군")+$" {p.progress*100:0}%",12,c);var map=SquadMapPoint(p.x,p.y);Fill(new Rect(map.x-3,map.y-3,6,6),c);}
            if(st.buildings!=null)foreach(var b in st.buildings){var p=SquadMapPoint(b.x,b.y);Fill(new Rect(p.x-3,p.y-3,6,6),b.team==squadSnapshot.team?baseGold:new Color(1,.4f,.3f));}
        }
        private void DrawStrategyFog()
        {
            var st=squadSnapshot.strategy;if(st==null)return;
            var explored=new System.Collections.Generic.HashSet<int>(st.explored??new int[0]);
            for(int y=0;y<20;y++)for(int x=0;x<30;x++)
            {
                bool visible=false;float wx=x*120+60,wy=y*120+60;
                if(st.vision!=null)foreach(var v in st.vision)if((new Vector2(wx-v.x,wy-v.y)).sqrMagnitude<=v.radius*v.radius){visible=true;break;}
                var p=SquadMapPoint(x*120,y*120);var q=SquadMapPoint((x+1)*120,(y+1)*120);
                Fill(new Rect(p.x,p.y,q.x-p.x+1,q.y-p.y+1),visible?new Color(.18f,.28f,.3f):explored.Contains(y*30+x)?new Color(.09f,.12f,.16f):new Color(.015f,.02f,.035f));
            }
        }
        private void DrawStrategyBuildingLabels()
        {
            if(retroScene==null||squadSnapshot.strategy.buildings==null)return;
            foreach(var b in squadSnapshot.strategy.buildings)
            {
                if(b.team!=squadSnapshot.team||b.hp<=0||!retroScene.Project(b.x,b.y,2.5f,out var p))continue;
                if(p.x<0||p.x>mmoField.width||p.y<0||p.y>mmoField.height)continue;
                Fill(new Rect(p.x-40,p.y-7,80,6),new Color(.1f,.12f,.18f,.9f));
                Fill(new Rect(p.x-40,p.y-7,80*Mathf.Clamp01(b.hp/Mathf.Max(1,b.max_hp)),6),baseCyan);
                BaseText(new Rect(p.x-125,p.y-29,250,20),StrategyKind(b.kind)+(b.remaining>0?$" · 건설 {b.remaining:0}s":" · 완성")+$" {b.hp:0}/{b.max_hp:0}",12,baseCyan,TextAnchor.MiddleCenter);
            }
        }
    }
}

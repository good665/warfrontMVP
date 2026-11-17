using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private string strategySquad="",strategyEconomy="none",strategyFormation="none",strategyPlacement="",strategyMapCommand="move";
        private Vector2 strategyBuildPoint;
        private bool strategyExpanded;
        private Rect strategyPanel=>new Rect(mmoField.width-264,mmoField.height-224,252,212);
        private int strategyHotkey=-1;
        private void ResetStrategy(){strategyExpanded=false;strategyHotkey=-1;strategySquad="";strategyEconomy="none";strategyFormation="none";strategyPlacement="";strategyMapCommand="move";}
        private bool StrategyPointer(Vector2 p)=>(strategyPanel.Contains(p)||new Rect(strategyPanel.x-90,strategyPanel.y-54,strategyPanel.width+90,54).Contains(p))||new Rect(14,256,225,98).Contains(p);
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
            var keyboard=Keyboard.current;
            if(keyboard!=null&&keyboard.tabKey.wasPressedThisFrame)ToggleStrategyPanel();
            if(keyboard!=null){UnityEngine.InputSystem.Controls.KeyControl[] keys={keyboard.digit1Key,keyboard.digit2Key,keyboard.digit3Key,keyboard.digit4Key,keyboard.digit5Key,keyboard.digit6Key,keyboard.digit7Key,keyboard.digit8Key,keyboard.digit9Key};for(int i=0;i<keys.Length;i++)if(keys[i].wasPressedThisFrame)strategyHotkey=i;}
            if(strategyHotkey>=0){int cell=strategyHotkey;strategyHotkey=-1;ActivateStrategyCell(cell);}
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
        private Rect StrategyCellRect(int index)
        {
            var panel=strategyPanel;return new Rect(panel.x+8+(index%3)*80,panel.y+28+(index/3)*52,76,48);
        }
        private string StrategyCellAction(int index)
        {
            string[] primary={"build_barracks","build_outpost","build_tower","build_academy","train_guard","train_archer","train_healer","train_scout","page"};
            string[] secondary={"research_attack","research_armor","research_recon","formation_line","formation_wedge","formation_spread","selection","map","page"};
            return (strategyExpanded?secondary:primary)[index];
        }
        private int StrategyCellCost(string action)
        {
            switch(action){case "build_barracks":case "build_tower":case "research_attack":case "research_armor":return 100;case "build_outpost":case "research_recon":return 80;case "build_academy":return 120;case "train_guard":return 60;case "train_archer":return 75;case "train_healer":return 90;case "train_scout":return 45;default:return 0;}
        }
        private string StrategyCellName(string action)
        {
            if(action.StartsWith("build_"))return StrategyKind(action.Substring(6))+" 건설";
            if(action.StartsWith("train_"))return StrategyKind(action.Substring(6))+" 생산";
            switch(action){case "research_attack":return "공격 연구";case "research_armor":return "방어 연구";case "research_recon":return "정찰 연구";case "formation_line":return "횡대";case "formation_wedge":return "쐐기";case "formation_spread":return "산개";case "selection":return "분대 선택: "+StrategySelectionLabel(squadSnapshot.strategy);case "map":return strategyMapCommand=="move"?"지도: 이동":"지도: 공격 이동";default:return strategyExpanded?"건설·생산 페이지":"연구·명령 페이지";}
        }
        private bool StrategyCellAllowed(string action)
        {
            var st=squadSnapshot?.strategy;if(st==null||!StrategyReady)return false;
            if(action=="page")return true;
            if(action=="selection")return !StrategySelectionLocked;
            if(action=="map"||action.StartsWith("formation_"))return true;
            if(strategyEconomy!="none"||st.supplies<StrategyCellCost(action))return false;
            if(action.StartsWith("train_"))return (st.queue?.Length??0)<3&&st.population+(action=="train_scout"?1:3)<=st.population_cap&&(st.squads?.Length??0)+(st.queue?.Length??0)<st.squad_cap;
            if(action.StartsWith("build_")){if(st.buildings!=null)foreach(var b in st.buildings)if(b.team==squadSnapshot.team&&b.kind==action.Substring(6)&&b.hp>0)return false;return true;}
            bool academy=false;if(st.buildings!=null)foreach(var b in st.buildings)if(b.team==squadSnapshot.team&&b.kind=="academy"&&b.hp>0&&b.remaining<=0)academy=true;
            int level=action=="research_attack"?st.tech_attack:action=="research_armor"?st.tech_armor:st.tech_recon;
            return academy&&level==0&&(st.research?.Length??0)==0;
        }
        private string StrategyCellTooltip(int index)
        {
            string action=StrategyCellAction(index);int cost=StrategyCellCost(action);
            return StrategyCellName(action)+(cost>0?" · 보급 "+cost:"")+"\n단축키: "+(index+1)+(action=="page"?" / Tab":"")+(action=="build_barracks"?" · 완성 후 자동 수호병 생산 / 적 본진 전진":"");
        }
        private void ActivateStrategyCell(int index)
        {
            if(index<0||index>8)return;string action=StrategyCellAction(index);if(!StrategyCellAllowed(action))return;
            ReleaseDungeonCursor();
            if(action=="page"){ToggleStrategyPanel();return;}
            if(action=="selection")
            {
                var squads=squadSnapshot.strategy.squads;
                if(strategySquad=="")SelectStrategySquad("all");
                else if(strategySquad=="all")SelectStrategySquad(squads!=null&&squads.Length>0?squads[0].id:"");
                else{int next=-1;if(squads!=null)for(int i=0;i<squads.Length;i++)if(squads[i].id==strategySquad)next=i+1;SelectStrategySquad(next>=0&&next<squads.Length?squads[next].id:"");}return;
            }
            if(action=="map"){strategyMapCommand=strategyMapCommand=="move"?"attack_move":"move";strategyPlacement="";return;}
            if(action.StartsWith("formation_")){strategyFormation=action.Substring(10);return;}
            if(action.StartsWith("build_"))strategyPlacement=action;else strategyEconomy=action;
        }
        private void DrawStrategyHud()
        {
            var st=squadSnapshot.strategy;if(st==null)return;
            DrawStrategyBuildingLabels();DrawStrategyPublicMarkers(st);
            BaseText(new Rect(255,14,510,28),$"보급 {st.supplies:0} (+{st.income:0}/초) · 인구 {st.population}/{st.population_cap} · 생산 {st.queue?.Length??0}",12,baseGold);
            var panel=strategyPanel;Fill(panel,new Color(.025f,.04f,.075f,.95f));
            BaseText(new Rect(panel.x+8,panel.y+3,236,22),strategyExpanded?"연구 · 명령":"건설 · 생산",12,baseGold,TextAnchor.MiddleCenter);
            string tooltip="";bool old=GUI.enabled;
            for(int i=0;i<9;i++)
            {
                var cell=StrategyCellRect(i);string action=StrategyCellAction(i);bool allowed=StrategyCellAllowed(action);
                GUI.enabled=old&&allowed;
                if(GUI.Button(cell,new GUIContent(StrategyCommandIcons.Get(action),"")))ActivateStrategyCell(i);
                GUI.enabled=old;
                if(Cursor.lockState!=CursorLockMode.Locked&&cell.Contains(Event.current.mousePosition))tooltip=StrategyCellTooltip(i)+(allowed?"":"\n현재 사용할 수 없습니다");
            }
            BaseText(new Rect(panel.x+8,panel.y+187,236,20),$"생산 대기 {st.queue?.Length??0} · "+(strategyExpanded?"2 / 2":"1 / 2"),11,baseMuted,TextAnchor.MiddleCenter);
            string hint=tooltip.Length>0?tooltip:strategyPlacement.Length>0?StrategyKind(strategyPlacement.Substring(6))+" 배치: 미니맵 클릭 · Esc 취소":!string.IsNullOrEmpty(st.action_error)?StrategyErrorLabel(st.action_error):tooltip;
            if(hint.Length>0){var box=new Rect(panel.x-90,panel.y-54,panel.width+90,50);Fill(box,new Color(.025f,.04f,.075f,.98f));BaseText(new Rect(box.x+8,box.y+3,box.width-16,44),hint,11,baseGold);}
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

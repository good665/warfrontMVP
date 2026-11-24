using System;
using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    [Serializable] public sealed class SquadDevRequest { public string action,item=""; public int floor=1; public float x,y; }

    public sealed partial class ApiClient
    {
        public System.Threading.Tasks.Task<SquadSnapshot> SquadDevAsync(string code,SquadDevRequest request)=>SendAsync<SquadSnapshot>("POST","/v1/squad/"+Uri.EscapeDataString(code)+"/dev",JsonUtility.ToJson(request));
    }

    // Developer panel (F9, editor / development builds only) for RTS matches: jump into any building or outdoor spot
    // and grant any item through POST /v1/squad/{code}/dev. The server answers 404 unless SQUAD_DEV_TOOLS=true.
    public sealed partial class GameBootstrap
    {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private bool devPanelOpen,devItemsTab;private string devStatus="";private Vector2 devScroll;private float devContentHeight=600;
        private static readonly Rect DevPanelRect=new Rect(880,40,390,540);
        private static readonly string[] DevItems={"axe","armor","portal","portal_plus","top","bouncy_ball","long_whip","curse_attack","curse_skill","curse_ultimate"};
        private static readonly string[] DevItemNames={"도끼","갑옷","포탈","업그레이드 포탈","팽이","탱탱볼","긴 채찍","일반공격 금지 저주","스킬 금지 저주","필살기 금지 저주"};
        private static string DevKind(string kind)=>kind=="manor"?"저택":kind=="passage"?"통로":kind=="house"?"한옥":kind;

        private void UpdateDevPanel(Keyboard k)
        {
            if(k==null||!k.f9Key.wasPressedThisFrame)return;
            devPanelOpen=!devPanelOpen;if(devPanelOpen)ReleaseDungeonCursor();
        }
        private bool DevPanelBlocks(Vector2 point)=>devPanelOpen&&DevPanelRect.Contains(point);

        private void DrawDevPanel()
        {
            if(!devPanelOpen||squadSnapshot==null)return;
            GUI.Box(DevPanelRect,"");GUI.Box(DevPanelRect,"");
            BaseText(new Rect(DevPanelRect.x+12,DevPanelRect.y+6,360,24),"개발자 패널 (F9 닫기)",16,Color.yellow);
            // Two tabs, each a one-per-row list, so items are as quick to reach as teleport spots.
            if(GUI.Toggle(new Rect(DevPanelRect.x+8,DevPanelRect.y+34,184,28),!devItemsTab,"순간이동","Button")&&devItemsTab){devItemsTab=false;devScroll=Vector2.zero;}
            if(GUI.Toggle(new Rect(DevPanelRect.x+198,DevPanelRect.y+34,184,28),devItemsTab,"아이템 지급","Button")&&!devItemsTab){devItemsTab=true;devScroll=Vector2.zero;}
            devScroll=GUI.BeginScrollView(new Rect(DevPanelRect.x+8,DevPanelRect.y+70,DevPanelRect.width-16,DevPanelRect.height-106),devScroll,new Rect(0,0,350,devContentHeight));
            float y=devItemsTab?DrawDevItems():DrawDevTeleports();
            devContentHeight=Mathf.Max(y,10);
            GUI.EndScrollView();
            BaseText(new Rect(DevPanelRect.x+12,DevPanelRect.yMax-32,366,24),devStatus,13,Color.white);
        }

        private float DrawDevItems()
        {
            float y=0;
            for(int i=0;i<DevItems.Length;i++)
            {
                if(GUI.Button(new Rect(0,y,340,26),DevItemNames[i]))DevCommand(new SquadDevRequest{action="give",item=DevItems[i]},DevItemNames[i]);
                y+=30;
            }
            string character=MmoSelf?.character;
            if(!string.IsNullOrEmpty(character))
            {
                if(GUI.Button(new Rect(0,y,340,26),"전용 무기 ("+character+")"))DevCommand(new SquadDevRequest{action="give",item="weapon_"+character},"전용 무기");
                y+=30;
                if(GUI.Button(new Rect(0,y,340,26),"전용 갑옷 ("+character+")"))DevCommand(new SquadDevRequest{action="give",item="fitted_armor_"+character},"전용 갑옷");
                y+=30;
            }
            return y;
        }

        private float DrawDevTeleports()
        {
            float y=0;
            GUI.Label(new Rect(0,y,340,22),"건물 안");y+=24;
            if(squadMap?.interiors!=null)foreach(var room in squadMap.interiors)
            {
                if(GUI.Button(new Rect(0,y,340,26),DevKind(room.kind)+" 실내 (층 "+room.floor+")"))
                    DevCommand(new SquadDevRequest{action="teleport",floor=room.floor},DevKind(room.kind)+" 실내");
                y+=30;
            }
            GUI.Label(new Rect(0,y,340,22),"바깥");y+=24;
            var home=RtsOutsideFocus;
            if(GUI.Button(new Rect(0,y,168,26),"내 본진"))DevCommand(new SquadDevRequest{action="teleport",x=home.x,y=home.y},"내 본진");
            if(GUI.Button(new Rect(172,y,168,26),"광장 중앙"))DevCommand(new SquadDevRequest{action="teleport",x=3200,y=3200},"광장 중앙");
            y+=30;
            int column=0;
            if(squadMap?.doors!=null)foreach(var door in squadMap.doors)
            {
                if(door.floor!=1)continue;
                string kind="건물";foreach(var room in squadMap.interiors)if(room.floor==door.to_floor)kind=DevKind(room.kind);
                string label=kind+" 문 앞 ("+door.cx+","+door.cy+")";
                // Doors stay closed for the landing search, so the hero stands next to the door instead of walking in.
                if(GUI.Button(new Rect(column*172,y,168,26),label))DevCommand(new SquadDevRequest{action="teleport",x=(door.cx+.5f)*50,y=(door.cy+.5f)*50},label);
                if(++column==2){column=0;y+=30;}
            }
            if(column!=0)y+=30;
            return y;
        }

        private async void DevCommand(SquadDevRequest request,string label)
        {
            if(api==null||string.IsNullOrEmpty(squadSnapshot?.code))return;
            devStatus=label+" 요청 중...";
            try{await api.SquadDevAsync(squadSnapshot.code,request);devStatus=label+" 완료";}
            catch(ApiException error){devStatus=error.Status==404?"서버 .env 에 SQUAD_DEV_TOOLS=true 를 넣고 재시작하세요":"실패: "+error.Code;}
        }
#else
        private void UpdateDevPanel(Keyboard k){}
        private bool DevPanelBlocks(Vector2 point)=>false;
        private void DrawDevPanel(){}
#endif
    }
}

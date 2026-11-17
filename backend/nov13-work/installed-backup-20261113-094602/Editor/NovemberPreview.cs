using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public sealed class NovemberPreview : EditorWindow
    {
        private GameObject root,sceneRoot;
        private GameBootstrap game;
        private RetroFantasyScene scene;
        private bool battle;
        private bool dead;
        private float lastTime;
        private const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
        private void Set(string name,object value)=>typeof(GameBootstrap).GetField(name,Flags).SetValue(game,value);
        private object Call(string name,params object[] args)=>typeof(GameBootstrap).GetMethod(name,Flags).Invoke(game,args);
        [InitializeOnLoadMethod] static void AutoOpen(){EditorApplication.delayCall+=()=>{
            if(File.Exists(Path.Combine(Path.GetTempPath(),"warfront-november-preview.request"))&&!EditorApplication.isPlayingOrWillChangePlaymode){File.Delete(Path.Combine(Path.GetTempPath(),"warfront-november-preview.request"));Open();}
        };}
        [MenuItem("Warfront/November/Preview Equipment And Battle")]
        public static void Open(){var window=GetWindow<NovemberPreview>();window.titleContent=new GUIContent("November Preview");window.minSize=new Vector2(1280,760);window.Show();}
        private void OnEnable()
        {
            root=new GameObject("November offline preview"){hideFlags=HideFlags.HideAndDontSave};root.SetActive(false);game=root.AddComponent<GameBootstrap>();
            sceneRoot=new GameObject("November preview render"){hideFlags=HideFlags.HideAndDontSave};scene=sceneRoot.AddComponent<RetroFantasyScene>();scene.Initialize();Set("retroScene",scene);
            Set("mmoProfile",new MmoProfile{level=12,gold=1250,attack=62,max_hp=280,weapon_rank=3,armor_rank=2,helmet_rank=1,active_loadout=0,equipped_weapon="blade",equipped_armor="plate",equipped_helmet="helm",loadouts=new[]{new MmoLoadout{weapon="blade",armor="plate",helmet="helm"},new MmoLoadout(),new MmoLoadout()},inventory=new[]{
                new MmoItem{id="helm",name="자수정 수호 투구",slot="helmet",power=18,rarity=2,equipped=true},new MmoItem{id="plate",name="룬 각인 흉갑",slot="armor",power=32,rarity=2,equipped=true},new MmoItem{id="blade",name="황혼의 장검",slot="weapon",power=26,rarity=2,equipped=true},
                new MmoItem{id="helm2",name="정예병의 투구",slot="helmet",power=24,rarity=3},new MmoItem{id="bow",name="전장 회수 무기",slot="weapon",power=16,rarity=1},new MmoItem{id="mail",name="견습 기사의 갑옷",slot="armor",power=12,rarity=1}}});
            Set("equipmentSelected","helm2");Set("mmoPanel","equipment");scene.EquipmentAppearance("",true);
            lastTime=(float)EditorApplication.timeSinceStartup;
        }
        private void OnGUI()
        {
            if(game==null)return;var skin=GUI.skin;
            GUI.skin=(GUISkin)Call("WidgetSkin",skin);
            if(GUI.Button(new Rect(20,4,200,28),battle?"장비 화면 보기":"전투 화면 보기")){battle=!battle;Set("mmoPanel",battle?"":"equipment");}
            if(battle&&GUI.Button(new Rect(230,4,200,28),dead?"부활":"영웅과 동료 쓰러짐"))dead=!dead;
            GUI.BeginGroup(new Rect(0,38,1280,720));
            try{
                if(battle){DrawBattle();Call("DrawSquadBattle");}
                else{RenderPortrait();Call("DrawMmoEquipmentPanel");}
            }finally{GUI.EndGroup();GUI.skin=skin;}
            Repaint();
        }
        private void RenderPortrait(){foreach(var camera in sceneRoot.GetComponentsInChildren<Camera>())if(camera.targetTexture!=null)camera.Render();}
        private void DrawBattle()
        {
            var self=new MmoActor{id="self",name="룬의 수호자",kind="hero",x=1100,y=1200,fx=1,hp=dead?0:160,max_hp=160};
            var companion=new MmoActor{id="guard",name="수호병",kind="guard",x=1150,y=1260,fx=1,hp=dead?0:180,max_hp=180};
            var snap=new MmoSnapshot{zone="squad",instance_id="preview",you_id="self",world_width=3600,world_height=2400,players=new[]{self,companion},enemies=Array.Empty<MmoEnemy>(),profile=new MmoProfile(),combat_rules=new MmoCombatRules()};
            Set("squadMode",true);Set("mmoWorld",snap);Set("mmoConnected",true);Set("mmoLastResponse",Time.realtimeSinceStartup);Set("retroShowingTown",false);
            Set("squadSnapshot",new SquadSnapshot{status="active",team=0,world=snap,respawn_left=dead?6:0,strategy=new SquadStrategy{supplies=300,population=3,population_cap=18,squad_cap=6}});
            scene.BeginField(snap,new Vector2(480,900));
            foreach(var actor in snap.players){string key="player:"+actor.id;scene.ActorLife(key,actor.hp>0);if(actor.hp>0){scene.Actor(key,actor.x,actor.y,1,0,false,false,false,false);scene.SquadRole(key,actor.kind);} }
            scene.EndField();scene.ThirdPerson("player:self",1100,1200,125,18,5.6f);
            foreach(var actor in sceneRoot.GetComponentsInChildren<ActorDeathVisual>())actor.Sample(Time.unscaledTime);
            RenderPortrait();lastTime=(float)EditorApplication.timeSinceStartup;
        }
        private void OnDisable(){if(root!=null)DestroyImmediate(root);if(sceneRoot!=null)DestroyImmediate(sceneRoot);}
    }
}

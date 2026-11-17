using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.EditorTools
{
    public sealed class FiveFloorPreview : EditorWindow
    {
        GameObject root,sceneRoot; GameBootstrap game; RetroFantasyScene scene; SquadSnapshot snapshot;
        bool overview;
        const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
        void Set(string name,object value)=>typeof(GameBootstrap).GetField(name,Flags).SetValue(game,value);
        object Call(string name,params object[] args)=>typeof(GameBootstrap).GetMethod(name,Flags).Invoke(game,args);
        [MenuItem("Warfront/Five Floor/Preview Battle")]
        public static void Open(){var w=GetWindow<FiveFloorPreview>();w.titleContent=new GUIContent("Five Floor Preview");w.minSize=new Vector2(1280,760);w.Show();}
        void OnEnable()
        {
            try
            {
                string path=Path.Combine(Path.GetTempPath(),"warfront-five-floor-preview.json");
                if(!File.Exists(path))return;snapshot=JsonUtility.FromJson<SquadSnapshot>(File.ReadAllText(path));
                root=new GameObject("Five floor offline preview"){hideFlags=HideFlags.HideAndDontSave};root.SetActive(false);game=root.AddComponent<GameBootstrap>();
                sceneRoot=new GameObject("Five floor render preview"){hideFlags=HideFlags.HideAndDontSave};scene=sceneRoot.AddComponent<RetroFantasyScene>();scene.Initialize();
                Set("retroScene",scene);Set("ready",true);Set("screen",Enum.Parse(typeof(GameBootstrap).GetField("screen",Flags).FieldType,"Mmo"));
                Set("squadMode",true);Set("squadSnapshot",snapshot);Set("mmoWorld",snapshot.world);Set("mmoProfile",snapshot.world.profile);Set("mmoConnected",true);Set("mmoPanel","");
                Set("dungeonYaw",0f);Set("dungeonPitch",22f);Set("dungeonDistance",7f);
            }
            catch(Exception e){Debug.LogException(e);}
        }
        void OnGUI()
        {
            if(game==null){GUILayout.Label("Generate a server snapshot fixture before opening the preview.");return;}
            GUI.Label(new Rect(16,4,1100,26),"서버 스냅샷 기반 오프라인 시각 검증 · 실제 사람 대전은 별도 HTTP 검사로 검증");
            if(GUI.Button(new Rect(1100,3,160,27),overview?"게임 시점 보기":"세로 맵 전체 보기"))overview=!overview;
            var previous=GUI.skin;GUI.skin=(GUISkin)Call("WidgetSkin",previous);
            GUI.BeginGroup(new Rect(0,34,1280,720));
            try
            {
                Set("mmoLastResponse",Time.realtimeSinceStartup);Call("UpdateRetroPresentation");
                if(overview)scene.FiveFloorOverview(snapshot.world);
                foreach(var camera in sceneRoot.GetComponentsInChildren<Camera>())if(camera.targetTexture!=null)camera.Render();
                Call("DrawSquadBattle");
            }
            catch(Exception e){GUI.Label(new Rect(20,60,1220,500),e.ToString());}
            finally{GUI.EndGroup();GUI.skin=previous;}
            Repaint();
        }
        void OnDisable(){if(root!=null)DestroyImmediate(root);if(sceneRoot!=null)DestroyImmediate(sceneRoot);}
    }
}

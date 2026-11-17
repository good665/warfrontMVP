using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public static class CornerCommandChecks
    {
        static object Call(GameBootstrap game,string method,params object[] args)=>typeof(GameBootstrap).GetMethod(method,BindingFlags.Instance|BindingFlags.NonPublic).Invoke(game,args);
        static void Set(GameBootstrap game,string name,object value)=>typeof(GameBootstrap).GetField(name,BindingFlags.Instance|BindingFlags.NonPublic).SetValue(game,value);
        static void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        [InitializeOnLoadMethod]
        static void AutoRun(){EditorApplication.delayCall+=()=>{
            if(EditorApplication.isPlayingOrWillChangePlaymode)return;
            var path=Path.Combine(Path.GetTempPath(),"warfront-corner-commands.request");if(!File.Exists(path))return;File.Delete(path);
            try{Run();CornerCommandPreview.Open();File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-corner-commands.result"),"PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-corner-commands.result"),e.ToString());}
        };}
        [MenuItem("Warfront/Squad/Check Corner Commands")]
        public static void Run()
        {
            var root=new GameObject("Corner command checks");root.SetActive(false);
            try{
                var game=root.AddComponent<GameBootstrap>();Call(game,"ResetStrategy");
                for(int page=0;page<2;page++){
                    Set(game,"strategyExpanded",page==1);
                    for(int i=0;i<9;i++){
                        var rect=(Rect)Call(game,"StrategyCellRect",i);
                        Check(rect.x>=976&&rect.y>=236&&rect.xMax<=1240&&rect.yMax<=460,"Cell not in bottom-right corner");
                        Check((bool)Call(game,"StrategyPointer",rect.center),"Grid pointer not blocked");
                        string action=(string)Call(game,"StrategyCellAction",i);
                        var icon=StrategyCommandIcons.Get(action);Check(icon!=null&&icon.width==32,"Missing command image");
                        if(action=="selection")Set(game,"squadSnapshot",new SquadSnapshot{strategy=new SquadStrategy()});
                        Check(((string)Call(game,"StrategyCellTooltip",i)).Contains("단축키: "+(i+1)),"Missing hover hotkey");
                        for(int j=0;j<i;j++)Check(!rect.Overlaps((Rect)Call(game,"StrategyCellRect",j)),"Overlapping grid cells");
                    }
                }
                Check((bool)Call(game,"StrategyPointer",new Vector2(900,210)),"Tooltip must block world clicks");
                Check(!(bool)Call(game,"StrategyPointer",new Vector2(300,385)),"Removed command strip still blocks the battlefield");
                Check(!(bool)Call(game,"StrategyPointer",new Vector2(300,100)),"Old expanded panel still blocks the battlefield");
                Set(game,"mmoConnected",false);Call(game,"ActivateStrategyCell",0);
                Check((string)typeof(GameBootstrap).GetField("strategyEconomy",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(game)=="none","Disconnected hotkey queued economy");
            }finally{UnityEngine.Object.DestroyImmediate(root);}
            Debug.Log("CORNER_COMMAND_CHECKS PASS");
        }
    }
    public sealed class CornerCommandPreview : EditorWindow
    {
        private GameObject root;
        private GameBootstrap game;
        [MenuItem("Warfront/Squad/Preview Corner Commands")]
        public static void Open(){var window=GetWindow<CornerCommandPreview>();window.titleContent=new GUIContent("Command Grid Preview");window.minSize=new Vector2(1280,510);window.Show();}
        private void OnEnable()
        {
            root=new GameObject("Command grid preview data"){hideFlags=HideFlags.HideAndDontSave};root.SetActive(false);game=root.AddComponent<GameBootstrap>();
            Set("squadMode",true);Set("mmoConnected",true);
            var world=new MmoSnapshot{you_id="preview",players=new[]{new MmoActor{id="preview",hp=160}}};
            Set("mmoWorld",world);Set("squadSnapshot",new SquadSnapshot{status="active",world=world,strategy=new SquadStrategy{supplies=300,income=2,population_cap=9,squad_cap=3}});
        }
        private void Set(string name,object value)=>typeof(GameBootstrap).GetField(name,BindingFlags.NonPublic|BindingFlags.Instance).SetValue(game,value);
        private void OnGUI()
        {
            if(game==null)return;Set("mmoLastResponse",Time.realtimeSinceStartup);
            EditorGUI.DrawRect(new Rect(20,20,1240,460),new Color(.16f,.18f,.22f));
            GUI.Label(new Rect(35,62,500,28),"3×3 아이콘 지휘 패널 · 마우스를 올려 단축키 확인");
            if(GUI.Button(new Rect(35,100,140,28),"페이지 전환 (Tab)"))typeof(GameBootstrap).GetMethod("ToggleStrategyPanel",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(game,null);
            GUI.BeginGroup(new Rect(20,20,1240,460));
            typeof(GameBootstrap).GetMethod("DrawStrategyHud",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(game,null);
            GUI.EndGroup();Repaint();
        }
        private void OnDisable(){if(root!=null)DestroyImmediate(root);}
    }
}

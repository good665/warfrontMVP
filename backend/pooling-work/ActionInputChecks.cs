using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public static class ActionInputChecks
    {
        const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
        static void Set(GameBootstrap game,string field,object value)=>typeof(GameBootstrap).GetField(field,Flags).SetValue(game,value);
        static void Check(bool value,string message){if(!value)throw new Exception(message);}
        [InitializeOnLoadMethod]
        static void AutoRun(){EditorApplication.delayCall+=()=>{var path=Path.Combine(Path.GetTempPath(),"warfront-action-input-check.request");if(!File.Exists(path))return;File.Delete(path);try{Run();File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-action-input-check.result"),"PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-action-input-check.result"),e.ToString());}};}
        [MenuItem("Warfront/Squad/Check Immediate Action Input")]
        public static void Run()
        {
            var root=new GameObject("Immediate action input checks");root.SetActive(false);
            try
            {
                var game=root.AddComponent<GameBootstrap>();
                var method=typeof(GameBootstrap).GetMethod("SquadSendReady",Flags);
                Check(method!=null,"No action-aware send gate; key presses wait for movement throttle");
                Func<float,bool> ready=now=>(bool)method.Invoke(game,new object[]{now});
                Set(game,"squadNext",10f);Set(game,"squadRequest",false);
                Check(!ready(9f)&&ready(10f),"Movement throttle changed unexpectedly");
                foreach(var action in new[]{"mmoDodge","mmoSkill1","mmoSkill2"})
                {
                    Set(game,action,true);Check(ready(9f),"Action press did not bypass throttle: "+action);
                    Set(game,"squadRequest",true);Check(!ready(9f),"Action created concurrent/reordered requests");
                    Check((bool)typeof(GameBootstrap).GetField(action,Flags).GetValue(game),"Pending action was cleared before send");
                    Set(game,"squadRequest",false);Set(game,action,false);
                }
                Check(!ready(9f),"Action bypass stayed latched");
                Debug.Log("ACTION_INPUT_CHECKS PASS: Q/E/Shift bypass, request ordering, retained pending press");
            }
            finally{UnityEngine.Object.DestroyImmediate(root);}
            SquadChecks.Run();TargetLockChecks.Run();
        }
    }
}

using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public static class TownPanelReturnChecks
    {
        const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
        static object Get(object target,string name)=>target.GetType().GetField(name,Flags).GetValue(target);
        static void Set(object target,string name,object value)=>target.GetType().GetField(name,Flags).SetValue(target,value);
        static void Call(object target,string name,params object[] values){var method=target.GetType().GetMethod(name,Flags);if(method==null)throw new Exception("Missing method: "+name);method.Invoke(target,values);}
        static void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        static void Screen(object target,string name){var field=target.GetType().GetField("screen",Flags);field.SetValue(target,Enum.Parse(field.FieldType,name));}
        [InitializeOnLoadMethod] static void AutoRun(){EditorApplication.delayCall+=()=>{
            var request=Path.Combine(Path.GetTempPath(),"warfront-town-panel-return.request");if(!File.Exists(request))return;
            if(EditorApplication.isPlayingOrWillChangePlaymode){AutoRun();return;}
            File.Delete(request);try{Run();File.WriteAllText(request+".result","PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(request+".result",e.ToString());}
        };}
        [MenuItem("Warfront/November/Check Panel Return To Town")]
        public static void Run()
        {
            var root=new GameObject("Town panel return checks");root.SetActive(false);
            try{
                var game=root.AddComponent<GameBootstrap>();var profile=new MmoProfile{gold=210,active_loadout=2};Set(game,"mmoProfile",profile);
                foreach(var panel in new[]{"equipment","profile","guide"}){
                    Screen(game,"Mmo");Set(game,"mmoPanel",panel);Set(game,"mmoDodge",true);Set(game,"mmoSkill1",true);
                    Call(game,"CloseMmoPanel");
                    Check(Get(game,"screen").ToString()=="Lobby",panel+" did not return to town");
                    Check((string)Get(game,"mmoPanel")=="","Panel remained open");Check(ReferenceEquals(profile,Get(game,"mmoProfile")),"Closing lost loaded equipment");
                    Check(!(bool)Get(game,"mmoDodge")&&!(bool)Get(game,"mmoSkill1"),"Combat input leaked through close");
                    Call(game,"CloseMmoPanel");Check(Get(game,"screen").ToString()=="Lobby","Repeated close changed destination");
                }
                Screen(game,"Mmo");Set(game,"mmoPanel","equipment");Set(game,"mmoRequest",true);
                Call(game,"CloseMmoPanel");var pending=(Action)Get(game,"mmoPendingAction");
                Check(pending!=null&&Get(game,"screen").ToString()=="Mmo","Active save was abandoned");
                Set(game,"mmoRequest",false);pending();Check(Get(game,"screen").ToString()=="Lobby","Deferred close did not return to town");
                Check(Get(game,"mmoPendingAction")==null,"Pending action survived town return");
                Screen(game,"Mmo");Set(game,"mmoWorld",null);Call(game,"OpenMmoControlSettings");Call(game,"CloseMmoControlSettings");
                Check(Get(game,"screen").ToString()=="Lobby","Cancel from town controls did not return to town");
                Screen(game,"Mmo");Set(game,"mmoWorld",new MmoSnapshot());Call(game,"OpenMmoControlSettings");Call(game,"CloseMmoControlSettings");
                Check(Get(game,"screen").ToString()=="Mmo","Battle settings unexpectedly left battle");
            }finally{UnityEngine.Object.DestroyImmediate(root);}
            Debug.Log("TOWN_PANEL_RETURN_CHECKS PASS: three panels, preserved profile, queued save, settings cancel");
        }
    }
}

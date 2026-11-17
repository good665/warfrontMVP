using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public static class NovemberCombatChecks
    {
        const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
        static void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        static void Set(object target,string name,object value)=>target.GetType().GetField(name,Flags).SetValue(target,value);
        static object Call(object target,string name,params object[] values)=>target.GetType().GetMethod(name,Flags).Invoke(target,values);
        [InitializeOnLoadMethod] static void AutoRun(){EditorApplication.delayCall+=()=>{
            string request=Path.Combine(Path.GetTempPath(),"warfront-november.request");if(!File.Exists(request))return;
            if(EditorApplication.isPlayingOrWillChangePlaymode){AutoRun();return;}
            File.Delete(request);try{Run();File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-november.result"),"PASS");}
            catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-november.result"),e.ToString());}
        };}
        [MenuItem("Warfront/November/Check Combat And Equipment")]
        public static void Run()
        {
            var go=new GameObject("November checks");go.SetActive(false);
            try{
                var game=go.AddComponent<GameBootstrap>();
                Check(typeof(GameBootstrap).GetMethod("DrawMmoEquipmentPanel",Flags)!=null,"Missing equipment grid and loadouts panel");
                Check(typeof(MmoProfile).GetField("loadouts")!=null&&typeof(MmoProfile).GetField("equipped_helmet")!=null,"Missing loadout model");
                var world=new MmoSnapshot{zone="squad",instance_id="checks",you_id="self",players=new[]{new MmoActor{id="self",hp=0}}};
                Set(game,"ready",true);Set(game,"screen",Enum.Parse(typeof(GameBootstrap).GetField("screen",Flags).FieldType,"Mmo"));
                Set(game,"mmoPanel","equipment");Call(game,"UpdateRetroPresentation");
                var equipmentScene=(RetroFantasyScene)typeof(GameBootstrap).GetField("retroScene",Flags).GetValue(game);
                try{Check(equipmentScene!=null&&equipmentScene.gameObject.activeSelf,"Town equipment panel disabled the live portrait");}
                finally{if(equipmentScene!=null)UnityEngine.Object.DestroyImmediate(equipmentScene.gameObject);Set(game,"retroScene",null);}
                Set(game,"mmoPanel","");
                Set(game,"squadMode",true);Set(game,"mmoConnected",true);Set(game,"mmoWorld",world);Set(game,"squadSnapshot",new SquadSnapshot{status="active",world=world});
                Check((bool)typeof(GameBootstrap).GetProperty("DungeonLookAllowed",Flags).GetValue(game),"Dead hero cannot orbit");
                var field=(Rect)typeof(GameBootstrap).GetField("mmoField",Flags).GetValue(game);
                var panel=(Rect)typeof(GameBootstrap).GetProperty("strategyPanel",Flags).GetValue(game);
                Check(Mathf.Abs(panel.xMax-field.width)<21&&Mathf.Abs(panel.yMax-(720-field.y))<21,"Command grid not at screen bottom-right");
                Rect combined=Rect.zero;
                foreach(int index in new[]{2,3,4,5}){
                    var r=(Rect)Call(game,"MmoControlRect",index);
                    Check(!r.Overlaps(new Rect(field.x+panel.x,field.y+panel.y,panel.width,panel.height)),"Skills overlap command panel");
                    if(index==2)combined=r;else combined=Rect.MinMaxRect(Mathf.Min(combined.xMin,r.xMin),Mathf.Min(combined.yMin,r.yMin),Mathf.Max(combined.xMax,r.xMax),Mathf.Max(combined.yMax,r.yMax));
                }
                Check(Mathf.Abs(combined.center.x-640)<95,"Skills not centered");
                Check((bool)Call(game,"DungeonPointerBlocked",combined.center),"HUD must block camera clicks");
                var defaults=(MmoPlaySettings)typeof(GameBootstrap).GetMethod("MmoDefaultSettings",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);
                defaults.controls[0].x=280;defaults.controls[0].y=652;
                Check(!(bool)typeof(GameBootstrap).GetMethod("MmoLayoutValid",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{defaults}),"Custom movement pad can cover menu/surrender buttons");
            }finally{UnityEngine.Object.DestroyImmediate(go);}
            var root=new GameObject("Death checks");var scene=root.AddComponent<RetroFantasyScene>();
            try{
                scene.Initialize();scene.BeginField(new MmoSnapshot{zone="squad",instance_id="death"},Vector2.zero);
                scene.Actor("player:self",1000,1200,1,0,false,false,false,false);
                var method=typeof(RetroFantasyScene).GetMethod("ActorLife");Check(method!=null,"Missing actor death lifecycle");
                method.Invoke(scene,new object[]{"player:self",false});
                var actor=root.transform.Find("Encounter squad/player:self");Check(actor!=null,"Missing rendered actor");
                var death=actor.GetComponent("ActorDeathVisual");Check(death!=null,"Missing death component");
                var sample=death.GetType().GetMethod("Sample");var start=(float)death.GetType().GetProperty("StartedAt").GetValue(death);
                sample.Invoke(death,new object[]{start+.35f});Check(Quaternion.Angle(actor.localRotation,Quaternion.LookRotation(Vector3.right))>10,"Corpse did not fall");
                method.Invoke(scene,new object[]{"player:self",false});Check((float)death.GetType().GetProperty("StartedAt").GetValue(death)==start,"Repeated snapshot restarts death");
                sample.Invoke(death,new object[]{start+1.5f});
                foreach(var renderer in actor.GetComponentsInChildren<Renderer>(true))Check(!renderer.enabled,"Dead actor remains visible");
                method.Invoke(scene,new object[]{"player:self",true});
                foreach(var renderer in actor.GetComponentsInChildren<SkinnedMeshRenderer>())Check(renderer.enabled,"Respawn did not restore body");
                Check(actor.GetComponent<Animation>().enabled,"Respawn animation disabled");
                scene.BeginField(new MmoSnapshot{zone="squad",instance_id="death"},Vector2.zero);scene.EndField();
                Check(actor!=null,"Removed allied squad skipped corpse animation");
                Check((bool)death.GetType().GetProperty("IsDead").GetValue(death),"Removed allied squad did not start dying");
            }finally{UnityEngine.Object.DestroyImmediate(root);}
            Debug.Log("NOVEMBER_COMBAT_CHECKS PASS");
        }
    }
}


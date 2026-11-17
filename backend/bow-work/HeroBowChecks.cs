using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public static class HeroBowChecks
    {
        const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
        static void Check(bool value,string message){if(!value)throw new Exception(message);}
        static object Get(GameBootstrap game,string name)=>typeof(GameBootstrap).GetField(name,Flags).GetValue(game);
        static void Set(GameBootstrap game,string name,object value)=>typeof(GameBootstrap).GetField(name,Flags).SetValue(game,value);
        [InitializeOnLoadMethod]
        static void AutoRun(){EditorApplication.delayCall+=()=>{if(EditorApplication.isPlayingOrWillChangePlaymode){AutoRun();return;}var path=Path.Combine(Path.GetTempPath(),"warfront-hero-bow.request");if(!File.Exists(path))return;File.Delete(path);try{Run();ActionInputChecks.Run();CombatPoolingChecks.Run();BlenderSkillChecks.Run();File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-hero-bow.result"),"PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-hero-bow.result"),e.ToString());}};}
        [MenuItem("Warfront/Squad/Check Hero Bow and Charge")]
        public static void Run()
        {
            var root=new GameObject("Hero bow checks");var scene=root.AddComponent<RetroFantasyScene>();
            try
            {
                scene.Initialize();scene.BeginField(new MmoSnapshot{zone="squad",instance_id="bow-checks"},Vector2.zero);
                scene.Actor("player:hero",1000,1200,1,0,false,false,false,false);scene.SquadRole("player:hero","hero");
                var actor=root.transform.Find("Encounter squad/player:hero");
                Check(actor.Find("Archer Bow")!=null,"Hero has no bow equipment");
                var sword=actor.Find("root/torso/arm-right/weapon-sword(Clone)");Check(!sword.gameObject.activeSelf,"Hero still holds sword");
                scene.SquadAction("player:hero",1,"charge_bow",.1f,1.2f,1,0,0,0,true,700,.35f);
                var nock=actor.Find("Archer Bow/Nocked Arrow");Check(nock.gameObject.activeSelf,"Charging released arrow before key-up");
                Check(actor.Find("Archer Bow").GetComponentInChildren<LineRenderer>().GetPosition(1).z<-.15f,"Charge does not draw bowstring");
                scene.SquadAction("player:hero",2,"charged_bow",.25f,.30f,1,0,0,0,true,700,.35f);
                Check(!nock.gameObject.activeSelf&&!sword.gameObject.activeSelf,"Released shot keeps nocked arrow or restores sword");
                scene.SquadAction("player:hero",3,"hero_bow",.35f,.40f,1,0,0,0,true,700,.35f);
                Check(nock.gameObject.activeSelf,"Normal arrow missing before release");
                scene.SquadAction("player:hero",3,"hero_bow",.20f,.40f,1,0,0,0,true,700,.35f);Check(!nock.gameObject.activeSelf,"Normal arrow not released");
            }
            finally{UnityEngine.Object.DestroyImmediate(root);}
            root=new GameObject("Charge input checks");root.SetActive(false);
            try
            {
                var game=root.AddComponent<GameBootstrap>();var capture=typeof(GameBootstrap).GetMethod("CaptureSquadCharge",Flags);Check(capture!=null,"No held/release capture path");
                capture.Invoke(game,new object[]{true,true,true});Check((bool)Get(game,"squadChargeHeld")&&(bool)Get(game,"mmoSkill1"),"Q down not captured");
                Set(game,"mmoSkill1",false);Set(game,"squadRequest",true);Set(game,"squadNext",float.MaxValue);
                capture.Invoke(game,new object[]{false,false,true});Check((bool)Get(game,"squadChargeRelease"),"Release lost while request in flight");
                var releaseAim=(Vector2)Get(game,"squadChargeReleaseAim");Set(game,"dungeonYaw",0f);Check(((Vector2)Get(game,"squadChargeReleaseAim"))==releaseAim,"Release aim follows later camera motion");
                var ready=typeof(GameBootstrap).GetMethod("SquadSendReady",Flags);Check(!(bool)ready.Invoke(game,new object[]{0f}),"Release overtakes request");Set(game,"squadRequest",false);Check((bool)ready.Invoke(game,new object[]{0f}),"Release waits behind movement throttle");
                capture.Invoke(game,new object[]{false,false,false});Check(!(bool)Get(game,"squadChargeHeld")&&!(bool)Get(game,"squadChargeRelease"),"Suspension keeps charge/release pending");
                capture.Invoke(game,new object[]{false,true,true});Check((bool)Get(game,"mmoSkill1")&&(bool)Get(game,"squadChargeRelease"),"Sub-frame short tap lost");
                Debug.Log("HERO_BOW_CHECKS PASS: hero bow gear, draw/hold/release, held input, release ordering, short tap, suspension");
            }
            finally{UnityEngine.Object.DestroyImmediate(root);}
        }
    }
}

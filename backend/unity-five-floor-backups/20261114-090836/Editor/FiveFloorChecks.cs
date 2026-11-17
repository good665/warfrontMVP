using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.EditorTools
{
    public static class FiveFloorChecks
    {
        const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
        [InitializeOnLoadMethod] static void Auto(){EditorApplication.delayCall+=()=>{string p=Path.Combine(Path.GetTempPath(),"warfront-five-floor-checks.request");if(File.Exists(p)&&!EditorApplication.isPlayingOrWillChangePlaymode){File.Delete(p);Run();}};}
        static void Require(bool value,string message){if(!value)throw new Exception(message);}
        [MenuItem("Warfront/Five Floor/Verify Gameplay Integration")]
        public static void Run()
        {
            GameObject go=null,host=null;
            try
            {
                ZodiacAssetBuilder.Verify();
                go=new GameObject("Zodiac integration checks");var scene=go.AddComponent<RetroFantasyScene>();scene.Initialize();
                var snap=new MmoSnapshot{zone="squad",instance_id="integration",world_width=3600,world_height=2400,obstacles=Array.Empty<MmoObstacle>()};
                scene.BeginField(snap,Vector2.zero);
                var actors=(Dictionary<string,GameObject>)typeof(RetroFantasyScene).GetField("actors",Flags).GetValue(scene);
                foreach(string animal in new[]{"rat","ox","tiger","rabbit","dragon","snake","horse","goat","monkey","rooster","dog","pig"})
                {
                    string key="player:"+animal;scene.PrepareFiveFloorActor(key,"hero",animal);scene.Actor(key,1600,1200,1,0,false,false,false,false);
                    var animation=actors[key].GetComponent<Animation>();var heavy=animation.GetClip("Heavy");
                    scene.SquadAction(key,1,"heavy",.3f,.6f,1,0,0,0,true,210,.35f);
                    Require(animation.GetClip("Heavy")==heavy,"Animal clip overwritten by human skill: "+animal);
                    scene.FiveFloorPose(key,.325f,0);Require(actors[key].transform.localPosition.y>.6f,"Jump pose absent: "+animal);
                }
                host=new GameObject("Input lifecycle checks");host.SetActive(false);var game=host.AddComponent<GameBootstrap>();
                typeof(GameBootstrap).GetField("fivePortal",Flags).SetValue(game,1);
                typeof(GameBootstrap).GetField("fiveJump",Flags).SetValue(game,true);
                typeof(GameBootstrap).GetField("fiveReplace",Flags).SetValue(game,4);
                typeof(GameBootstrap).GetMethod("ClearSquadPauseInput",Flags).Invoke(game,null);
                Require((int)typeof(GameBootstrap).GetField("fivePortal",Flags).GetValue(game)==0,"Pause replayed a portal intent");
                Require(!(bool)typeof(GameBootstrap).GetField("fiveJump",Flags).GetValue(game),"Pause replayed a jump intent");
                Require((int)typeof(GameBootstrap).GetField("fiveReplace",Flags).GetValue(game)==-1,"Pause replayed an inventory intent");
                File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-five-floor-checks.result"),"PASS: 12 animal skill clips preserved; native rig deformation; visual jump; pause clears one-shot inputs.");
            }
            catch(Exception e){File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-five-floor-checks.result"),"FAIL: "+e);Debug.LogException(e);}
            finally{if(go!=null)UnityEngine.Object.DestroyImmediate(go);if(host!=null)UnityEngine.Object.DestroyImmediate(host);}
        }
    }
}

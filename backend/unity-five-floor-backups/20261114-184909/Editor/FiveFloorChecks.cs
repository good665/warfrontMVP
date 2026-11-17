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
                var snap=new MmoSnapshot{zone="squad",instance_id="integration",five_floor=true,floor=3,world_width=2400,world_height=3600,obstacles=Array.Empty<MmoObstacle>()};
                scene.BeginField(snap,Vector2.zero);
                var ground=(Mesh)typeof(RetroFantasyScene).GetField("fieldGroundMesh",Flags).GetValue(scene);
                Require(ground.bounds.size.z>ground.bounds.size.x,"Battlefield ground is still horizontal");
                scene.FiveFloorEnvironment(new SquadSnapshot{world=snap,battle=new FiveFloorBattle{floor=3,portals=new[]{new BattlePortal{x=1200,y=35,up=true},new BattlePortal{x=1200,y=3565,down=true}}}});
                var gates=(GameObject)typeof(RetroFantasyScene).GetField("fiveEnvironment",Flags).GetValue(scene);
                Require(gates.transform.childCount==2,"Expected two end-wall portals");
                Require(Vector3.Distance(gates.transform.GetChild(0).localPosition,RetroFantasyScene.WorldPoint(1200,35))<.001f,"Top portal is not on the end wall");
                Require(Vector3.Distance(gates.transform.GetChild(1).localPosition,RetroFantasyScene.WorldPoint(1200,3565))<.001f,"Bottom portal is not on the end wall");
                scene.ThirdPerson("",1200,35,0,18,5.6f);
                Require((float)typeof(RetroFantasyScene).GetField("followDistance",Flags).GetValue(scene)>=3.5f,"Top arrival camera is inside the end wall");
                scene.ThirdPerson("",1200,3565,180,18,5.6f);
                Require((float)typeof(RetroFantasyScene).GetField("followDistance",Flags).GetValue(scene)>=3.5f,"Bottom arrival camera is inside the end wall");
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
                typeof(GameBootstrap).GetField("squadMode",Flags).SetValue(game,true);
                typeof(GameBootstrap).GetField("squadSnapshot",Flags).SetValue(game,new SquadSnapshot{status="active",battle=new FiveFloorBattle{five_floor=true,portals=new[]{new BattlePortal{x=1200,y=35,up=true}}},world=snap});
                snap.players=new[]{new MmoActor{id="rat",x=1200,y=35,hp=160}};snap.you_id="rat";typeof(GameBootstrap).GetField("mmoWorld",Flags).SetValue(game,snap);
                Require((bool)typeof(GameBootstrap).GetMethod("SquadOverlayPointer",Flags).Invoke(game,new object[]{new Vector2(530,494)}),"Portal UI click starts camera look instead of activating button");
                File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-five-floor-checks.result"),"PASS: vertical ground geometry; two server-defined end-wall portals; 12 animal clips/rigs; visual jump; pause and overlay input.");
            }
            catch(Exception e){File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-five-floor-checks.result"),"FAIL: "+e);Debug.LogException(e);}
            finally{if(go!=null)UnityEngine.Object.DestroyImmediate(go);if(host!=null)UnityEngine.Object.DestroyImmediate(host);}
        }
    }
}

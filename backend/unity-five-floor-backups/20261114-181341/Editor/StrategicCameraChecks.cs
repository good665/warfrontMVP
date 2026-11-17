using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.EditorTools
{
    public static class StrategicCameraChecks
    {
        const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
        [InitializeOnLoadMethod]static void Auto(){EditorApplication.delayCall+=()=>{string path=Path.Combine(Path.GetTempPath(),"warfront-strategic-camera.request");if(File.Exists(path)&&!EditorApplication.isPlayingOrWillChangePlaymode){File.Delete(path);Run();}};}
        static void Require(bool value,string message){if(!value)throw new Exception(message);}
        [MenuItem("Warfront/Five Floor/Verify Strategic Camera")]
        public static void Run()
        {
            GameObject root=null,host=null;
            try
            {
                var set=typeof(RetroFantasyScene).GetMethod("StrategicView");
                var pick=typeof(RetroFantasyScene).GetMethod("TryStrategicGround");
                Require(set!=null&&pick!=null,"Strategic camera and ground projection are missing");
                root=new GameObject("Strategic camera verification");var scene=root.AddComponent<RetroFantasyScene>();scene.Initialize();
                scene.BeginField(new MmoSnapshot{zone="squad",instance_id="strategic-check",five_floor=true,floor=3,world_width=2400,world_height=3600,obstacles=Array.Empty<MmoObstacle>()},Vector2.zero);
                var camera=(Camera)typeof(RetroFantasyScene).GetField("view",Flags).GetValue(scene);
                set.Invoke(scene,new object[]{1200f,1800f,11f,2400f,3600f});
                Require(camera.orthographic,"Battle camera is still perspective");
                Require(Mathf.Abs(Mathf.DeltaAngle(camera.transform.eulerAngles.x,55))<.01f,"Pitch must stay at 55 degrees");
                Require(Mathf.Abs(Mathf.DeltaAngle(camera.transform.eulerAngles.y,45))<.01f,"Yaw must stay at 45 degrees");
                foreach(var point in new[]{new Vector2(1200,1800),new Vector2(950,1500),new Vector2(1500,2050)})
                {
                    Require(scene.Project(point.x,point.y,0,out var screen),"Ground point was behind camera");
                    object[] args={screen,Vector2.zero};Require((bool)pick.Invoke(scene,args),"Pointer ray missed ground");
                    Require(Vector2.Distance((Vector2)args[1],point)<.15f,"Pointer aim disagrees with rendered ground");
                }
                foreach(float y in new[]{35f,3565f})
                {set.Invoke(scene,new object[]{1200f,y,11f,2400f,3600f});Require(Mathf.Abs(camera.orthographicSize-11)<.001f,"Portal wall changed strategic zoom");}
                set.Invoke(scene,new object[]{1200f,1800f,999f,2400f,3600f});Require(camera.orthographicSize<=14,"Zoom exceeded maximum");
                set.Invoke(scene,new object[]{1200f,1800f,0f,2400f,3600f});Require(camera.orthographicSize>=7.5f,"Zoom exceeded minimum");
                host=new GameObject("Strategic input verification");host.SetActive(false);var game=host.AddComponent<GameBootstrap>();
                typeof(GameBootstrap).GetField("squadMode",Flags).SetValue(game,true);
                typeof(GameBootstrap).GetField("squadSnapshot",Flags).SetValue(game,new SquadSnapshot{status="active",battle=new FiveFloorBattle{five_floor=true},world=new MmoSnapshot{you_id="self"}});
                typeof(GameBootstrap).GetField("dungeonLooking",Flags).SetValue(game,true);
                typeof(GameBootstrap).GetField("squadAutoLookPending",Flags).SetValue(game,true);
                typeof(GameBootstrap).GetMethod("UpdateDungeonLook",Flags).Invoke(game,null);
                Require(!(bool)typeof(GameBootstrap).GetField("dungeonLooking",Flags).GetValue(game),"Mouse-look remains active");
                Require(Cursor.lockState==CursorLockMode.None&&Cursor.visible,"Strategic cursor must remain visible and unlocked");
                File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-strategic-camera.result"),"PASS: fixed orthographic 55/45 camera; ground aiming round trips; portal zoom; zoom limits; cursor unlocked.");
            }
            catch(Exception e){File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-strategic-camera.result"),"FAIL: "+e);Debug.LogException(e);}
            finally{if(root!=null)UnityEngine.Object.DestroyImmediate(root);if(host!=null)UnityEngine.Object.DestroyImmediate(host);}
        }
    }
}

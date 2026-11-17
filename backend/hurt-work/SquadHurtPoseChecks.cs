using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using System.Linq;
namespace Warfront.Verification
{
    public static class SquadHurtPoseChecks
    {
        const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
        static void Check(bool value,string message){if(!value)throw new Exception(message);}
        [InitializeOnLoadMethod]
        static void AutoRun(){EditorApplication.delayCall+=()=>{if(EditorApplication.isPlayingOrWillChangePlaymode){AutoRun();return;}var path=Path.Combine(Path.GetTempPath(),"warfront-hurt-pose.request");if(!File.Exists(path))return;File.Delete(path);try{Run();PlayerHurtChecks.Run();HeroBowChecks.Run();File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-hurt-pose.result"),"PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-hurt-pose.result"),e.ToString());}};}
        static void FinishPose(Transform actor,float now)
        {
            var reaction=actor.GetComponent("HeroHitReaction");if(reaction!=null)reaction.GetType().GetMethod("Sample").Invoke(reaction,new object[]{now});
        }
        [MenuItem("Warfront/Player Hurt/Check Squad Final Pose")]
        public static void Run()
        {
            foreach(var kind in new[]{"hero_bow","charge_bow","charged_bow","bomb",""})
            {
                var root=new GameObject("Squad hurt final pose checks");var scene=root.AddComponent<RetroFantasyScene>();
                try
                {
                    scene.Initialize();scene.BeginField(new MmoSnapshot{zone="squad",instance_id="hurt-pose"},Vector2.zero);
                    scene.Actor("player:self",1000,1200,1,0,false,false,false,false);scene.SquadRole("player:self","hero");
                    var actor=root.transform.Find("Encounter squad/player:self");var torso=actor.Find("root/torso");
                    actor.GetComponent<Animation>().GetClip("Idle").SampleAnimation(actor.gameObject,0);
                    float duration=kind=="charge_bow"?1.2f:.4f;
                    scene.SquadAction("player:self",1,kind,duration*.5f,duration,1,0,0,0,true,700,.35f);
                    var neutralTorso=torso.localRotation;var neutralPosition=actor.localPosition;
                    if(kind=="charge_bow")Capture(root,actor,"neutral",true);
                    scene.PlayerImpact("self");var timers=(Dictionary<string,float>)typeof(RetroFantasyScene).GetField("playerImpactUntil",Flags).GetValue(scene);timers["player:self"]=Time.unscaledTime+.18f;
                    scene.Actor("player:self",1000,1200,1,0,false,false,false,false);scene.SquadAction("player:self",1,kind,duration*.5f,duration,1,0,0,0,true,700,.35f);FinishPose(actor,Time.unscaledTime);
                    Check(Quaternion.Angle(actor.localRotation,Quaternion.LookRotation(Vector3.right))>2,"Final action sampling erased hit recoil: "+kind);
                    Check(Quaternion.Angle(torso.localRotation,neutralTorso)>8,"No visible torso hurt motion: "+kind);
                    var bow=actor.Find("Archer Bow");var hand=actor.Find("root/torso/arm-left");Check(Vector3.Distance(bow.position,hand.TransformPoint(new Vector3(0,-.12f,.035f)))<.005f,"Bow detached during hurt");
                    var pose=torso.localRotation;var position=actor.localPosition;
                    for(int i=0;i<8;i++){scene.Actor("player:self",1000,1200,1,0,false,false,false,false);scene.SquadAction("player:self",1,kind,duration*.5f,duration,1,0,0,0,true,700,.35f);FinishPose(actor,Time.unscaledTime);}
                    Check(Quaternion.Angle(pose,torso.localRotation)<.1f&&Vector3.Distance(position,actor.localPosition)<.001f,"Hit pose accumulates across frames: "+kind);
                    Check(Vector3.Distance(neutralPosition,actor.localPosition)<.15f,"Visual recoil moved too far");
                    if(kind=="charge_bow")Capture(root,actor,"hit",false);
                    timers["player:self"]=Time.unscaledTime-1;
                    scene.Actor("player:self",1000,1200,1,0,false,false,false,false);scene.SquadAction("player:self",1,kind,duration*.5f,duration,1,0,0,0,true,700,.35f);FinishPose(actor,Time.unscaledTime);
                    Check(Quaternion.Angle(torso.localRotation,neutralTorso)<.1f&&Vector3.Distance(actor.localPosition,neutralPosition)<.001f,"Hit pose fails to restore: "+kind);
                    Check(actor.GetComponent<Animation>().GetClip("Bow")!=null,"Hurt removed bow state");
                }
                finally{UnityEngine.Object.DestroyImmediate(root);}
            }
            Debug.Log("SQUAD_HURT_POSE_CHECKS PASS: final bow/charge/release/bomb/idle hit pose, visible torso, no accumulation, restore");
        }
        static void Capture(GameObject root,Transform actor,string name,bool setCamera)
        {
            if(SystemInfo.graphicsDeviceType==GraphicsDeviceType.Null)return;
            var camera=root.GetComponentsInChildren<Camera>(true).First(c=>c.name=="Fantasy Camera");
            if(setCamera){camera.orthographic=true;camera.orthographicSize=.95f;camera.aspect=camera.targetTexture.width/(float)camera.targetTexture.height;var facing=Quaternion.LookRotation(Vector3.right);camera.transform.position=actor.position+facing*new Vector3(2.2f,1.5f,3);camera.transform.LookAt(actor.position+Vector3.up*.45f);}
            var request=new UniversalRenderPipeline.SingleCameraRequest{destination=camera.targetTexture};if(!RenderPipeline.SupportsRenderRequest(camera,request))return;
            RenderPipeline.SubmitRenderRequest(camera,request);var previous=RenderTexture.active;
            try{RenderTexture.active=camera.targetTexture;var image=new Texture2D(camera.targetTexture.width,camera.targetTexture.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,image.width,image.height),0,0);image.Apply();File.WriteAllBytes(Path.Combine(Path.GetTempPath(),"warfront-hurt-"+name+".png"),image.EncodeToPNG());UnityEngine.Object.DestroyImmediate(image);}
            finally{RenderTexture.active=previous;}
        }
    }
}

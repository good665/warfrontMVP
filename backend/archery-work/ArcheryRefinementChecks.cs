using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
namespace Warfront.Verification
{
    public static class ArcheryRefinementChecks
    {
        static void Check(bool value,string message){if(!value)throw new Exception(message);}
        [InitializeOnLoadMethod]
        static void AutoRun(){EditorApplication.delayCall+=()=>{if(EditorApplication.isPlayingOrWillChangePlaymode){AutoRun();return;}var path=Path.Combine(Path.GetTempPath(),"warfront-archery-refinement.request");if(!File.Exists(path))return;File.Delete(path);try{Warfront.Assets.CompanionEquipmentBuilder.Build();Run();HeroBowChecks.Run();SquadHurtPoseChecks.Run();CombatPoolingChecks.Run();CompanionAttackChecks.Run();File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-archery-refinement.result"),"PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-archery-refinement.result"),e.ToString());}};}
        [MenuItem("Warfront/Squad/Check Archery Motion Refinement")]
        public static void Run()
        {
            var root=new GameObject("Archery refinement checks");var scene=root.AddComponent<RetroFantasyScene>();
            try
            {
                scene.Initialize();scene.BeginField(new MmoSnapshot{zone="squad",instance_id="archery-motion"},Vector2.zero);
                scene.Actor("player:self",1000,1200,0,-1,false,false,false,false);scene.SquadRole("player:self","hero");
                var actor=root.transform.Find("Encounter squad/player:self");var hand=actor.Find("root/torso/arm-right");var bow=actor.Find("Archer Bow");var line=bow.GetComponentInChildren<LineRenderer>();var nock=bow.Find("Nocked Arrow");
                var restTip=line.GetPosition(0);
                scene.SquadAction("player:self",1,"charge_bow",.10f,1.2f,0,-1,0,0,true,700,.35f);
                var pullPoint=line.transform.TransformPoint(line.GetPosition(1));var grip=hand.TransformPoint(new Vector3(0,-.12f,.035f));
                Check(Vector3.Distance(pullPoint,grip)<.005f,"Bow string does not follow actual draw hand");
                Check(Vector3.Distance(nock.TransformPoint(new Vector3(0,0,-.32f)),pullPoint)<.005f,"Arrow nock is not seated on string");
                Check(Vector3.Distance(restTip,line.GetPosition(0))>.01f,"Bow limbs do not flex under draw");
                var lower=bow.Find("Curved wood limb 0");var upper=bow.Find("Curved wood limb 3");
                Check(Vector3.Distance(lower.TransformPoint(new Vector3(0,0,-.5f)),line.transform.TransformPoint(line.GetPosition(0)))<.005f,"Lower string tip is detached");
                Check(Vector3.Distance(upper.TransformPoint(new Vector3(0,0,.5f)),line.transform.TransformPoint(line.GetPosition(2)))<.005f,"Upper string tip is detached");
                var clip=actor.GetComponent<Animation>().GetClip("Bow");clip.SampleAnimation(actor.gameObject,.22f);var anchor=hand.TransformPoint(new Vector3(0,-.12f,.035f));clip.SampleAnimation(actor.gameObject,.249f);
                Check(Vector3.Distance(anchor,hand.TransformPoint(new Vector3(0,-.12f,.035f)))<.002f,"Draw hand drifts during anchor hold");
                clip.SampleAnimation(actor.gameObject,.28f);var follow=hand.TransformPoint(new Vector3(0,-.12f,.035f));
                Check(Vector3.Dot(follow-anchor,actor.forward)<-.015f,"Release hand has no backward follow-through");
                scene.SquadAction("player:self",2,"charge_bow",.10f,1.2f,0,-1,0,0,true,700,.35f);
                scene.SquadAction("player:self",3,"charged_bow",.30f,.30f,0,-1,0,0,true,700,.35f);
                Check(!nock.gameObject.activeSelf&&line.GetPosition(1).z>-.10f,"Release does not snap string/reset nocked arrow");
                var visual=bow.GetComponent("ArcheryBowVisual");Check(visual!=null,"Missing linked bow visual controller");
                var launch=(Vector3)visual.GetType().GetProperty("ReleasePosition").GetValue(visual);
                scene.SquadProjectiles(new[]{new MmoProjectile{id=91,owner_id="self",start_x=1000,start_y=1200,end_x=1000,end_y=500,flight=.6f,age=0}},0);
                Check(Vector3.Distance(root.transform.Find("Encounter squad/Authoritative arrow 91").position,launch)<.01f,"Flying arrow does not originate at drawn arrow");
                foreach(float time in new[]{.04f,.14f,.249f,.28f,.65f})
                {
                    clip.SampleAnimation(actor.gameObject,time);scene.SquadAction("player:self",4,"bow",.65f-time,.65f,0,-1,0,0,true,700,.35f);Capture(root,actor,time);
                }
                Debug.Log("ARCHERY_REFINEMENT_CHECKS PASS: phased pose, fixed anchor, string/hand/nock/tips, limb flex, follow-through, release, launch socket");
            }
            finally{UnityEngine.Object.DestroyImmediate(root);}
        }
        static void Capture(GameObject root,Transform actor,float time)
        {
            if(SystemInfo.graphicsDeviceType==GraphicsDeviceType.Null)return;
            var camera=root.GetComponentsInChildren<Camera>(true).First(c=>c.name=="Fantasy Camera");camera.orthographic=true;camera.orthographicSize=.95f;camera.aspect=camera.targetTexture.width/(float)camera.targetTexture.height;camera.transform.position=actor.position+new Vector3(2.2f,1.25f,3);camera.transform.LookAt(actor.position+Vector3.up*.45f);
            foreach(var skin in actor.GetComponentsInChildren<SkinnedMeshRenderer>())skin.forceMatrixRecalculationPerRender=true; var request=new UniversalRenderPipeline.SingleCameraRequest{destination=camera.targetTexture};if(!RenderPipeline.SupportsRenderRequest(camera,request))return;RenderPipeline.SubmitRenderRequest(camera,request);var previous=RenderTexture.active;
            try{RenderTexture.active=camera.targetTexture;var image=new Texture2D(camera.targetTexture.width,camera.targetTexture.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,image.width,image.height),0,0);image.Apply();File.WriteAllBytes(Path.Combine(Path.GetTempPath(),"warfront-archery-"+time.ToString("0.000",System.Globalization.CultureInfo.InvariantCulture)+".png"),image.EncodeToPNG());UnityEngine.Object.DestroyImmediate(image);}
            finally{RenderTexture.active=previous;}
        }
    }
}


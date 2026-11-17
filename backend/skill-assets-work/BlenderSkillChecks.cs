using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
namespace Warfront.Verification
{
    public static class BlenderSkillChecks
    {
        static void Check(bool value,string message){if(!value)throw new Exception(message);}
        [InitializeOnLoadMethod]
        static void AutoRun(){EditorApplication.delayCall+=()=>{if(EditorApplication.isPlayingOrWillChangePlaymode){AutoRun();return;}var path=Path.Combine(Path.GetTempPath(),"warfront-blender-skills.request");if(!File.Exists(path))return;var mode=File.ReadAllText(path);File.Delete(path);try{if(mode.Contains("build"))Warfront.Assets.BlenderSkillImport.Build();Run();CombatPoolingChecks.Run();CombatContactChecks.Run();File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-blender-skills.result"),"PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-blender-skills.result"),e.ToString());}};}
        [MenuItem("Warfront/Squad/Check Blender Skill Visuals")]
        public static void Run()
        {
            var source=Resources.Load<GameObject>("MiniDungeon/Characters/Human");
            var root=new GameObject("Blender skill checks");var scene=root.AddComponent<RetroFantasyScene>();
            try
            {
                scene.Initialize();scene.BeginField(new MmoSnapshot{zone="squad",instance_id="skill-checks"},Vector2.zero);
                scene.Actor("player:self",1000,1200,1,0,false,false,false,false);
                var actor=root.transform.Find("Encounter squad/player:self");var original=source.GetComponentInChildren<SkinnedMeshRenderer>().sharedMesh;
                foreach(var spec in new[]{new[]{"Heavy",".55",".28"},new[]{"Throw",".30",".10"},new[]{"Dodge",".22",".08"}})
                {
                    var clip=Resources.Load<AnimationClip>("SkillVisuals/"+spec[0]);Check(clip!=null,"Missing Blender-authored "+spec[0]+" clip");
                    float duration=float.Parse(spec[1],System.Globalization.CultureInfo.InvariantCulture),time=float.Parse(spec[2],System.Globalization.CultureInfo.InvariantCulture);
                    Check(clip.legacy&&Mathf.Abs(clip.length-duration)<.005f,"Clip duration/legacy mismatch: "+spec[0]);
                    var arm=actor.Find("root/torso/arm-right");clip.SampleAnimation(actor.gameObject,0);var before=arm.localRotation;
                    var skin=actor.GetComponentInChildren<SkinnedMeshRenderer>();var baked=new Mesh();skin.BakeMesh(baked);var restVertices=baked.vertices;
                    clip.SampleAnimation(actor.gameObject,time);skin.BakeMesh(baked);var posed=baked.vertices;bool deformed=false;
                    for(int i=0;i<posed.Length;i++)if(Vector3.Distance(posed[i],restVertices[i])>.015f){deformed=true;break;}
                    UnityEngine.Object.DestroyImmediate(baked);Check(deformed,"Original weighted skin does not deform: "+spec[0]);
                    Check(Quaternion.Angle(before,arm.localRotation)>25,"Blender clip does not move original arm: "+spec[0]);
                    clip.SampleAnimation(actor.gameObject,duration);Check(Quaternion.Angle(before,arm.localRotation)<.1f,"Skill end does not restore original rig");
                }
                scene.SquadAction("player:self",1,"heavy",.27f,.55f,1,0,0,0,true,210,.35f);
                Check(actor.GetComponent<Animation>().GetClip("Heavy")==Resources.Load<AnimationClip>("SkillVisuals/Heavy"),"Heavy still uses normal Attack fallback");
                Check(actor.GetComponentInChildren<SkinnedMeshRenderer>().sharedMesh==original,"Existing character art was replaced");
                scene.SquadAction("player:self",2,"bomb",.20f,.30f,1,0,0,0,true,145,.35f);
                Check(!actor.Find("root/torso/arm-right/weapon-sword(Clone)").gameObject.activeSelf,"Throw still holds sword in bomb hand");
                scene.SquadBombs(new[]{new MmoBomb{id=50,owner_id="self",flight=.65f,radius=150,start_x=1000,start_y=1200,target_x=1300,target_y=1200,age=.119f}},0,0);
                var held=root.transform.Find("Encounter squad/Server bomb 50").localPosition;
                scene.SquadBombs(new[]{new MmoBomb{id=50,owner_id="self",flight=.65f,radius=150,start_x=1000,start_y=1200,target_x=1300,target_y=1200,age=.121f}},0,0);
                Check(Vector3.Distance(held,root.transform.Find("Encounter squad/Server bomb 50").localPosition)<.08f,"Bomb snaps away from hand at release");
                scene.SquadAction("player:self",3,"heavy",.27f,.55f,1,0,0,0,true,210,.35f);
                Check(actor.Find("root/torso/arm-right/weapon-sword(Clone)").gameObject.activeSelf,"Sword not restored after throw");
                scene.SquadBombs(new[]{new MmoBomb{id=51,owner_id="self",flight=.65f,radius=150,start_x=1000,start_y=1200,target_x=1300,target_y=1200,age=.3f}},0,0);
                var bomb=root.transform.Find("Encounter squad/Server bomb 51");Check(bomb!=null&&bomb.gameObject.activeSelf,"Flying bomb missing");
                Check(bomb.localPosition.y>1.5f,"Bomb does not fly through an arc");
                Check(bomb.GetComponentsInChildren<Renderer>().Max(r=>r.bounds.size.magnitude)>.2f,"Bomb FBX scale lost during pooling/rental");
                scene.SquadBombs(new[]{new MmoBomb{id=51,owner_id="self",flight=.65f,radius=150,target_x=1300,target_y=1200,age=.7f,exploded=true}},0,0);
                Check(!bomb.gameObject.activeSelf,"Bomb stays visible after authoritative explosion");
                var blast=root.transform.Find("Encounter squad/Blender blast 51");Check(blast!=null&&blast.gameObject.activeSelf,"Blender explosion geometry not connected");int blastId=blast.gameObject.GetInstanceID();
                Check(Mathf.Abs(blast.localScale.x-3)<.01f,"Blender blast does not match server radius");
                Check(blast.GetComponentsInChildren<MeshRenderer>(true).Length>=3,"Blast lacks shockwave/core/fragments");
                Check(blast.GetComponentsInChildren<Renderer>().Max(r=>r.bounds.size.magnitude)>1f,"Explosion lost imported FBX scale");
                scene.SquadBombs(null,0,0);Check(!blast.gameObject.activeSelf,"Expired blast not returned to pool");
                scene.SquadBombs(new[]{new MmoBomb{id=52,flight=.65f,radius=150,age=.7f,exploded=true}},0,1);
                Check(root.transform.Find("Encounter squad/Blender blast 52").gameObject.GetInstanceID()==blastId,"Blender explosion bypasses pooling");
                RenderPreviews(scene,root,actor.gameObject);
                scene.BeginField(new MmoSnapshot{zone="squad",instance_id="skill-rematch"},Vector2.zero);
                Check(root.transform.Find("Combat visual pool")!=null,"Field transition lost skill effect pool");
                Debug.Log("BLENDER_SKILL_CHECKS PASS: original rig, distinct Heavy/Throw/Dodge, durations, bomb arc, server explosion, radius, pooling");
            }
            finally{UnityEngine.Object.DestroyImmediate(root);}
        }
        static void RenderPreviews(RetroFantasyScene scene,GameObject root,GameObject actor)
        {
            actor.transform.localRotation=Quaternion.identity;
            var camera=root.GetComponentsInChildren<Camera>(true).First(c=>c.name=="Fantasy Camera");
            camera.orthographic=true;camera.orthographicSize=1.15f;camera.aspect=1.4f;
            camera.transform.position=actor.transform.position+new Vector3(2.4f,1.8f,3);camera.transform.LookAt(actor.transform.position+Vector3.up*.5f);
            foreach(var item in new[]{new[]{"Heavy",".28"},new[]{"Throw",".10"},new[]{"Dodge",".08"}})
            {
                var sword=actor.transform.Find("root/torso/arm-right/weapon-sword(Clone)");sword.gameObject.SetActive(item[0]!="Throw");
                var clip=Resources.Load<AnimationClip>("SkillVisuals/"+item[0]);clip.SampleAnimation(actor,float.Parse(item[1],System.Globalization.CultureInfo.InvariantCulture));
                Capture(camera,"warfront-skill-"+item[0]+".png");
            }
            actor.SetActive(false);scene.SquadBombs(new[]{new MmoBomb{id=99,flight=.65f,radius=150,target_x=1000,target_y=1200,age=.78f,exploded=true}},0,0);
            camera.orthographicSize=4f;camera.transform.position=actor.transform.position+new Vector3(5,6,7);camera.transform.LookAt(actor.transform.position+Vector3.up*.4f);Capture(camera,"warfront-skill-Blast.png");
        }
        static void Capture(Camera camera,string name)
        {
            if(SystemInfo.graphicsDeviceType==GraphicsDeviceType.Null)return;
            var request=new UniversalRenderPipeline.SingleCameraRequest{destination=camera.targetTexture};
            if(!RenderPipeline.SupportsRenderRequest(camera,request))return;
            RenderPipeline.SubmitRenderRequest(camera,request);var previous=RenderTexture.active;
            try{RenderTexture.active=camera.targetTexture;var image=new Texture2D(camera.targetTexture.width,camera.targetTexture.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,image.width,image.height),0,0);image.Apply();File.WriteAllBytes(Path.Combine(Path.GetTempPath(),name),image.EncodeToPNG());UnityEngine.Object.DestroyImmediate(image);}
            finally{RenderTexture.active=previous;}
        }
    }
}

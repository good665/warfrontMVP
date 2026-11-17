using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.EditorTools
{
    public static class ZodiacEffectChecks
    {
        const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
        static readonly string[] Animals={"rat","ox","tiger","rabbit","dragon","snake","horse","goat","monkey","rooster","dog","pig"};
        [InitializeOnLoadMethod]static void Auto(){EditorApplication.delayCall+=()=>{var path=Path.Combine(Path.GetTempPath(),"warfront-zodiac-effects.request");if(File.Exists(path)&&!EditorApplication.isPlayingOrWillChangePlaymode){File.Delete(path);Run();}};}
        static void Require(bool value,string text){if(!value)throw new Exception(text);}
        [MenuItem("Warfront/Five Floor/Verify Zodiac Effects")]
        public static void Run()
        {
            GameObject root=null;Texture2D sheet=null;RenderTexture previous=RenderTexture.active;
            try
            {
                root=new GameObject("24 zodiac effect checks");var scene=root.AddComponent<RetroFantasyScene>();scene.Initialize();
                var world=new MmoSnapshot{zone="squad",instance_id="effect-check",five_floor=true,floor=3,world_width=2400,world_height=3600,obstacles=Array.Empty<MmoObstacle>()};
                scene.BeginField(world,Vector2.zero);
                var snapshot=new SquadSnapshot{world=world,battle=new FiveFloorBattle{five_floor=true,floor=3,portals=Array.Empty<BattlePortal>()}};
                scene.FiveFloorEnvironment(snapshot);scene.StrategicView(1200,1750,9,2400,3600);
                var camera=(Camera)typeof(RetroFantasyScene).GetField("view",Flags).GetValue(scene);
                var target=new RenderTexture(320,220,24);camera.targetTexture=target;camera.aspect=320f/220;
                sheet=new Texture2D(1920,880,TextureFormat.RGB24,false);
                for(int i=0;i<24;i++)
                {
                    string animal=Animals[i/2],slot=i%2==0?"q":"e";
                    scene.BeginField(world,Vector2.zero);scene.PrepareFiveFloorActor("player:preview","hero",animal);
                    scene.Actor("player:preview",1200,1800,0,-1,false,false,false,false);scene.EndField();
                    var effect=new MmoEffect{id=i.ToString(),character=animal,skill=slot,kind="skill",x=1200,y=1800,fx=0,fy=-1,radius=260,age=.28f};
                    scene.UpdateZodiacEffects(new[]{effect});
                    var env=(GameObject)typeof(RetroFantasyScene).GetField("fiveEnvironment",Flags).GetValue(scene);
                    Require(env.transform.childCount==1,"Expired effect survived or basic ring present");
                    var visual=env.transform.GetChild(0);Require(visual.childCount==(slot=="q"?12:24),"Missing skill fragments");
                    Require(visual.GetComponentsInChildren<Collider>().Length==0,"Visual effect has gameplay colliders");
                    Require(visual.GetComponentsInChildren<LineRenderer>().Length==0,"Generic skill circle survived");
                    var piece=visual.GetChild(0);Vector3 first=piece.localPosition;
                    effect.age=.53f;scene.UpdateZodiacEffects(new[]{effect});
                    Require(env.transform.childCount==1,"Snapshot replay duplicated effect");
                    Require(Vector3.Distance(first,piece.localPosition)>.001f||piece.localScale.sqrMagnitude>.001f,"Effect invalid");
                    foreach(var node in visual.GetComponentsInChildren<Transform>())Require(float.IsFinite(node.localPosition.x)&&float.IsFinite(node.localScale.x),"Non-finite VFX transform");
                    effect.age=.28f;scene.UpdateZodiacEffects(new[]{effect});camera.Render();RenderTexture.active=target;
                    sheet.ReadPixels(new Rect(0,0,320,220),(i%6)*320,(3-i/6)*220);
                }
                sheet.Apply();File.WriteAllBytes(Path.Combine(Path.GetTempPath(),"warfront-zodiac-effects.png"),sheet.EncodeToPNG());
                scene.UpdateZodiacEffects(new[]{new MmoEffect{id="basic",kind="shot",radius=650}});
                var environment=(GameObject)typeof(RetroFantasyScene).GetField("fiveEnvironment",Flags).GetValue(scene);
                Require(environment.transform.childCount==0,"Basic attack created circular effect");
                camera.targetTexture=null;target.Release();UnityEngine.Object.DestroyImmediate(target);
                File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-zodiac-effects.result"),"PASS: 24 character/slot effects; geometry and render; replay deduplication; no colliders; no generic attack circles; cleanup.");
            }
            catch(Exception e){File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-zodiac-effects.result"),"FAIL: "+e);Debug.LogException(e);}
            finally{RenderTexture.active=previous;if(sheet!=null)UnityEngine.Object.DestroyImmediate(sheet);if(root!=null)UnityEngine.Object.DestroyImmediate(root);}
        }
    }
}

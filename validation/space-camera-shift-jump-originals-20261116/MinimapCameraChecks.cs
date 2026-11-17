using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace Warfront.Verification
{
    public static class MinimapCameraChecks
    {
        const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
        static void Set(object o,string key,object value)=>o.GetType().GetField(key,Flags).SetValue(o,value);
        static object Get(object o,string key)=>o.GetType().GetField(key,Flags).GetValue(o);
        static object Call(object o,string key,params object[] args)=>o.GetType().GetMethod(key,Flags).Invoke(o,args);
        static void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        [InitializeOnLoadMethod]
        static void Init(){EditorApplication.update+=Poll;}
        static void Poll()
        {
            var request=Path.Combine(Path.GetTempPath(),"warfront-minimap-camera.request");
            if(EditorApplication.isPlayingOrWillChangePlaymode||EditorApplication.isCompiling||!File.Exists(request))return;
            File.Delete(request);Run();
        }
        [MenuItem("Warfront/Characters/Check Minimap Camera")]
        public static void Run()
        {
            var holder=new GameObject("Minimap input checks");holder.SetActive(false);
            var root=new GameObject("Minimap camera checks");
            try
            {
                var bootstrap=holder.AddComponent<GameBootstrap>();
                var self=new MmoActor{id="self",kind="hero",hp=100,x=700,y=1100};
                var world=new MmoSnapshot{zone="squad",instance_id="map-check",world_width=6400,world_height=6400,you_id="self",players=new[]{self}};
                Set(bootstrap,"mmoWorld",world);
                Call(bootstrap,"MmoCameraFocus",new Vector2(self.x,self.y));
                var map=(Rect)typeof(GameBootstrap).GetProperty("MmoMinimapInput",Flags).GetValue(bootstrap);
                Call(bootstrap,"ApplyMinimapCameraPoint",map.center,true);
                var focus=(Vector2)Call(bootstrap,"MmoCameraFocus",Vector2.zero);
                Check(Vector2.Distance(focus,new Vector2(3200,3200))<.01f,"Click does not move camera to map center");
                Call(bootstrap,"ApplyMinimapCameraPoint",map.position+new Vector2(-100,1000),false);
                focus=(Vector2)Call(bootstrap,"MmoCameraFocus",Vector2.zero);
                Check(Vector2.Distance(focus,new Vector2(0,6400))<.01f,"Drag outside minimap does not clamp at world boundary");
                Check((bool)Get(bootstrap,"mmoMapDragging"),"Drag capture was lost outside minimap");
                var selfPoint=map.position+new Vector2(self.x/world.world_width*map.width,self.y/world.world_height*map.height);
                Call(bootstrap,"ApplyMinimapCameraPoint",selfPoint,true);
                Check((bool)Get(bootstrap,"mmoMapDragging"),"Own-marker press must keep pointer captured until release");
                Call(bootstrap,"ApplyMinimapCameraPoint",selfPoint,false);
                Check(!(bool)Get(bootstrap,"mmoMapCameraOverride"),"Holding own-marker press cancels follow restoration");
                Check(!(bool)Call(bootstrap,"MmoHeld",new Rect(-100000,-100000,200000,200000)),"Own-marker drag can activate gameplay controls");
                Check((bool)Call(bootstrap,"DungeonPointerBlocked",new Vector2(500,200)),"Own-marker drag can attack in gameplay field");
                Call(bootstrap,"ReleaseMinimapDrag");
                focus=(Vector2)Call(bootstrap,"MmoCameraFocus",new Vector2(self.x,self.y));
                Check(!((bool)Get(bootstrap,"mmoMapCameraOverride"))&&Vector2.Distance(focus,new Vector2(self.x,self.y))<.01f,"Own dot does not restore follow view");
                Call(bootstrap,"ApplyMinimapCameraPoint",map.center,true);world.instance_id="next-battle";
                Call(bootstrap,"MmoCameraFocus",new Vector2(self.x,self.y));
                Check(!((bool)Get(bootstrap,"mmoMapCameraOverride")),"New battle retains manual camera position");
                var scene=root.AddComponent<RetroFantasyScene>();scene.Initialize();
                scene.BeginField(world,Vector2.zero);scene.Actor("player:self",self.x,self.y,0,-1,false,false,false,false);scene.EndField();
                var camera=Array.Find(root.GetComponentsInChildren<Camera>(true),c=>c.name=="Fantasy Camera");
                var corners=new Vector2[4];float previousArea=0;
                foreach(float zoom in new[]{3.5f,5.6f,8f})
                {
                    scene.RtsCamera(true,"player:self",3200,3200,45,35.264f,new Vector2(3200,3200),zoom);
                    Check(scene.CameraGroundFootprint(corners),"Camera footprint projection failed");
                    float area=0;
                    for(int i=0;i<4;i++)
                    {
                        var actual=camera.WorldToViewportPoint(root.transform.position+RetroFantasyScene.WorldPoint(corners[i].x,corners[i].y));
                        var expected=new Vector2(i==1||i==2?1:0,i>=2?1:0);
                        Check(Vector2.Distance(new Vector2(actual.x,actual.y),expected)<.002f,"White border does not match rendered viewport corner");
                        var next=corners[(i+1)%4];area+=corners[i].x*next.y-next.x*corners[i].y;
                    }
                    area=Mathf.Abs(area);Check(area>previousArea,"Zoom out does not enlarge viewport border");previousArea=area;
                }
                scene.MinimapCamera(new Vector2(1200,4400),5.6f);
                Check(scene.CameraGroundFootprint(corners),"Panned camera footprint missing");
                var center=(corners[0]+corners[1]+corners[2]+corners[3])*.25f;
                Check(Vector2.Distance(center,new Vector2(1200,4400))<.2f,"Panned viewport is not aligned with chosen world point");
                File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-minimap-camera.result"),"PASS: click mapping, edge drag clamping/capture, own-marker follow, new-battle reset, actual viewport corner alignment at 3 zoom levels, panned viewport alignment.");
                Debug.Log("MINIMAP_CAMERA_CHECKS PASS");
            }
            catch(Exception error){File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-minimap-camera.result"),"FAIL: "+error);Debug.LogException(error);}
            finally{UnityEngine.Object.DestroyImmediate(root);UnityEngine.Object.DestroyImmediate(holder);}
        }
    }
}

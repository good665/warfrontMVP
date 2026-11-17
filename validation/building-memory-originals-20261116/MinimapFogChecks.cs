using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace Warfront.Verification
{
    public static class MinimapFogChecks
    {
        const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
        static void Set(object o,string key,object value)=>o.GetType().GetField(key,Flags).SetValue(o,value);
        static object Get(object o,string key)=>o.GetType().GetField(key,Flags).GetValue(o);
        static object Call(object o,string key,params object[] args)
        {
            var method=o.GetType().GetMethod(key,Flags);if(method==null)throw new Exception("Missing minimap fog behavior: "+key);
            return method.Invoke(o,args);
        }
        static void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        static bool Visible(object o,float x,float y)=>(bool)Call(o,"MinimapPointVisible",x,y);
        [InitializeOnLoadMethod]static void Init(){EditorApplication.update+=Poll;}
        static void Poll()
        {
            string request=Path.Combine(Path.GetTempPath(),"warfront-minimap-fog.request");
            if(EditorApplication.isPlayingOrWillChangePlaymode||EditorApplication.isCompiling||!File.Exists(request))return;
            File.Delete(request);Run();
        }
        [MenuItem("Warfront/Characters/Check Minimap Fog")]
        public static void Run()
        {
            var root=new GameObject("Minimap fog checks");root.SetActive(false);GameBootstrap game=null;
            try
            {
                game=root.AddComponent<GameBootstrap>();
                var self=new MmoActor{id="self",team=0,floor=1,x=500,y=600,hp=100};
                var ally=new MmoActor{id="ally",team=0,floor=1,x=2800,y=3000,hp=100};
                var enemy=new MmoActor{id="enemy",team=1,floor=1,x=5600,y=5600,hp=100};
                var dead=new MmoActor{id="dead",team=0,floor=1,x=5000,y=700,hp=0};
                var otherFloor=new MmoActor{id="upstairs",team=0,floor=2,x=500,y=5000,hp=100};
                var world=new MmoSnapshot{zone="squad",instance_id="fog-test",floor=1,world_width=6400,world_height=6400,you_id="self",players=new[]{self,ally,enemy,dead,otherFloor}};
                var squad=new SquadSnapshot{team=0,status="playing",world=world,bases=new[]{new SquadBase{team=0,floor=1,hp=2000,x=5000,y=3000}}};
                Set(game,"mmoWorld",world);Set(game,"squadMode",true);Set(game,"squadSnapshot",squad);
                Call(game,"UpdateMinimapFog",true);
                Check(Visible(game,self.x,self.y),"Own unit does not reveal terrain");
                Check(Visible(game,ally.x,ally.y),"Living ally does not share vision");
                Check(Visible(game,5000f,3000f),"Friendly base does not reveal terrain");
                Check(!Visible(game,enemy.x,enemy.y),"Enemy reveals unexplored terrain");
                Check(!Visible(game,dead.x,dead.y),"Dead ally reveals terrain");
                Check(!Visible(game,otherFloor.x,otherFloor.y),"Another floor reveals terrain");
                Check(!Visible(game,-1,600)&&!Visible(game,6401,600)&&!Visible(game,500,6401),"Outside zone boundary is revealed");
                Set(game,"mmoMapCameraOverride",true);Set(game,"mmoMapCameraCenter",new Vector2(enemy.x,enemy.y));Call(game,"UpdateMinimapFog",true);
                Check(!Visible(game,enemy.x,enemy.y),"Moving camera into unknown region reveals enemies");
                var texture=(Texture2D)Get(game,"mmoMinimapFog");
                var bright=texture.GetPixel((int)(self.x/6400*texture.width),texture.height-1-(int)(self.y/6400*texture.height));
                var grey=texture.GetPixel((int)(enemy.x/6400*texture.width),texture.height-1-(int)(enemy.y/6400*texture.height));
                Check(bright.a==0,"Visible terrain is covered or mask is vertically flipped");
                Check(grey.a==1&&Mathf.Abs(grey.r-grey.g)<.001f&&Mathf.Abs(grey.g-grey.b)<.001f,"Hidden region is not fully opaque grey");
                ally.hp=0;Call(game,"UpdateMinimapFog",true);Check(!Visible(game,2800f,3000f),"Lost vision stays bright");
                var remembered=texture.GetPixel((int)(2800f/6400*texture.width),texture.height-1-(int)(3000f/6400*texture.height));
                Check(remembered.a==1&&remembered.r>grey.r+.15f&&Mathf.Abs(remembered.r-remembered.g)<.001f,"Explored area does not persist as opaque light grey");
                Call(game,"UpdateMinimapFog",true);
                Check(texture.GetPixel((int)(2800f/6400*texture.width),texture.height-1-(int)(3000f/6400*texture.height))==remembered,"Exploration fades without current vision");
                Check(!(bool)Call(game,"WorldUnitVisible",1,1,2800f,3000f),"Enemy visible in remembered terrain");
                Check((bool)Call(game,"WorldUnitVisible",1,1,self.x,self.y),"Enemy in current allied vision is hidden");
                var presentation=new GameObject("World fog visibility check");
                try
                {
                    world.enemies=new[]{new MmoEnemy{id="hidden",team=1,floor=1,x=5600,y=5600,hp=100},new MmoEnemy{id="seen",team=1,floor=1,x=self.x,y=self.y,hp=100}};
                    var scene=presentation.AddComponent<RetroFantasyScene>();scene.Initialize();
                    scene.BeginField(world,Vector2.zero);scene.Actor("enemy:hidden",5600,5600,0,-1,false,false,true,false);scene.Actor("enemy:seen",self.x,self.y,0,-1,false,false,true,false);scene.EndField();
                    var hidden=presentation.transform.Find("Encounter squad/enemy:hidden");var seen=presentation.transform.Find("Encounter squad/enemy:seen");
                    var predicate=new Func<float,float,bool>((x,y)=>Visible(game,x,y));
                    scene.ApplyWorldVision(world,squad,predicate);
                    Check(!hidden.gameObject.activeSelf&&seen.gameObject.activeSelf,"Main screen leaks enemy model outside shared vision");
                    scene.MinimapCamera(new Vector2(5600,5600),5.6f);scene.ApplyWorldVision(world,squad,predicate);
                    Check(!hidden.gameObject.activeSelf,"Moving camera reveals hidden enemy model");
                    world.enemies[1].floor=2;scene.ApplyWorldVision(world,squad,predicate);
                    Check(!seen.gameObject.activeSelf,"Other-floor enemy is visible in the main world");world.enemies[1].floor=1;
                    var effect=new GameObject("Fog effect lifecycle test");effect.transform.SetParent(presentation.transform,false);effect.transform.localPosition=RetroFantasyScene.WorldPoint(5600,5600);
                    typeof(RetroFantasyScene).GetMethod("HideOutsideVision",Flags).Invoke(scene,new object[]{effect,predicate});
                    Check(!effect.activeSelf,"Effect outside vision is not hidden");scene.RestoreFogVisuals();
                    Check(effect.activeSelf,"Fog-hidden effect does not restore before normal effect update");
                    self.x=5600;self.y=5600;Call(game,"UpdateMinimapFog",true);scene.ApplyWorldVision(world,squad,predicate);
                    Check(hidden.gameObject.activeSelf&&!seen.gameObject.activeSelf,"Enemy visibility does not switch when allied vision moves");
                }
                finally{UnityEngine.Object.DestroyImmediate(presentation);}
                self.x=5500;self.y=5500;world.instance_id="new-zone";Call(game,"UpdateMinimapFog",true);
                Check(!Visible(game,500f,600f)&&Visible(game,5500f,5500f),"Zone transition leaks old vision");
                File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-minimap-fog.result"),"PASS: allied/base vision, enemy/dead/other-floor exclusion, opaque grayscale unknown area, map boundaries, texture Y orientation, camera-independent fog, persistent light-grey exploration, main-world enemy hiding/reveal, loss of vision and new-zone reset.");Debug.Log("MINIMAP_FOG_CHECKS PASS");
            }
            catch(Exception error){File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-minimap-fog.result"),"FAIL: "+error);Debug.LogException(error);}
            finally{if(game!=null&&typeof(GameBootstrap).GetMethod("DisposeMinimapFog",Flags)!=null)Call(game,"DisposeMinimapFog");UnityEngine.Object.DestroyImmediate(root);}
        }
    }
}

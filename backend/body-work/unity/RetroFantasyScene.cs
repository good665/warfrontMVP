using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Warfront
{
    // All models are real meshes on an isolated layer. No scene or global lighting edits.
    public sealed partial class RetroFantasyScene : MonoBehaviour
    {
        public const int ModelLayer = 30;
        private readonly Dictionary<string, Material> materials = new Dictionary<string, Material>();
        private readonly Dictionary<string, GameObject> actors = new Dictionary<string, GameObject>();
        private readonly Dictionary<string, Vector3> lastPositions = new Dictionary<string, Vector3>();
        private readonly Dictionary<string,Quaternion> actorFacing=new Dictionary<string,Quaternion>();
        private readonly Dictionary<string,float> actionUntil=new Dictionary<string,float>();
        private readonly Dictionary<string,string> actionState=new Dictionary<string,string>();
        private readonly HashSet<string> alive = new HashSet<string>();
        private MaterialPropertyBlock appearanceBlock;
        private readonly List<Mesh> ownedMeshes = new List<Mesh>();
        private Mesh fieldGroundMesh;
        private GameObject town, field, portrait;
        private Camera view, portraitCamera;
        private RenderTexture target, portraitTarget;
        private GameObject hero,orc,viewWeapon,viewShield;
        private Mesh dangerMesh;
        private float firstPersonAttackUntil;
        private Vector3 previousEye;
        private readonly List<Bounds> cameraWalls=new List<Bounds>();
        private float followDistance;
        private Material dungeonMaterial;
        private readonly List<GameObject> dangerMarkers=new List<GameObject>();
        private readonly List<GameObject> enemyWarnings=new List<GameObject>();
        private readonly Dictionary<string,float> impactUntil=new Dictionary<string,float>();
        private readonly Dictionary<string,float> deathUntil=new Dictionary<string,float>();
        private readonly Dictionary<string,float> previousWindups=new Dictionary<string,float>();
        private readonly Dictionary<string,float> playerImpactUntil=new Dictionary<string,float>();
        private string fieldKey = "";
        private bool townMode;
        private GameObject squadObjectiveRoot;
        private readonly Dictionary<string,GameObject> squadBuildings=new Dictionary<string,GameObject>();
        private readonly Vector3 origin = new Vector3(10000,0,10000);
        private static readonly Dictionary<string,string> textureNames = new Dictionary<string,string> {
            {"stones","cobblestone"},{"bricks","cobblestoneAlternative"},{"stonesPainted","cobblestonePainted"},
            {"planks","planks"},{"roof","roof"},{"details","details"},{"barrel","barrel"},{"fence","fence"},{"tree","tree"},{"water","water"},{"grass","grass"} };

        public Texture View => target;
        public Texture Portrait => portraitTarget;
        public bool Available => hero != null;

        public void Initialize()
        {
            appearanceBlock=new MaterialPropertyBlock();
            transform.position=origin;
            hero=Resources.Load<GameObject>("MiniDungeon/Characters/Human");
            orc=Resources.Load<GameObject>("MiniDungeon/Characters/Orc");
            dungeonMaterial=Resources.Load<Material>("MiniDungeon/Materials/Colormap");
            foreach(var entry in textureNames)materials[entry.Key]=Resources.Load<Material>("MiniDungeon/Materials/Floor");
            view=CameraNode("Fantasy Camera",transform,1280,640,out target);
            var lightObject=new GameObject("Town sunlight");lightObject.transform.SetParent(transform,false);lightObject.transform.localRotation=Quaternion.Euler(48,-32,0);
            var sunlight=lightObject.AddComponent<Light>();sunlight.type=LightType.Directional;sunlight.color=new Color(1,.88f,.69f);sunlight.intensity=1.7f;sunlight.cullingMask=1<<ModelLayer;sunlight.shadows=LightShadows.Soft;
            var fillObject=new GameObject("Cool fill light");fillObject.transform.SetParent(transform,false);fillObject.transform.localRotation=Quaternion.Euler(35,145,0);
            var fill=fillObject.AddComponent<Light>();fill.type=LightType.Directional;fill.color=new Color(.65f,.78f,1);fill.intensity=.65f;fill.cullingMask=1<<ModelLayer;
            town=new GameObject("Stonehaven Town");town.transform.SetParent(transform,false);BuildTown();
            portrait=new GameObject("Adventurer Portrait");portrait.transform.SetParent(transform,false);portrait.transform.localPosition=new Vector3(-35,0,0);
            if(hero!=null){var model=Instantiate(hero,portrait.transform);model.transform.localScale=Vector3.one*2f;model.transform.localRotation=Quaternion.Euler(0,-20,0);SetLayer(model);}
            portraitCamera=CameraNode("Portrait Camera",portrait.transform,320,400,out portraitTarget);
            portraitCamera.transform.localPosition=new Vector3(1.8f,1.45f,3.2f);portraitCamera.transform.LookAt(portrait.transform.position+Vector3.up*.85f);portraitCamera.orthographicSize=1.02f;portraitCamera.backgroundColor=new Color(.16f,.15f,.23f);
            SetLayer(gameObject);
            ShowTown();
        }
        private Camera CameraNode(string name,Transform parent,int width,int height,out RenderTexture texture)
        {
            texture=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32){name=name+" Output",antiAliasing=1};texture.Create();
            var go=new GameObject(name);go.transform.SetParent(parent,false);var camera=go.AddComponent<Camera>();
            camera.orthographic=true;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.13f,.13f,.19f);
            camera.cullingMask=1<<ModelLayer;camera.targetTexture=texture;camera.nearClipPlane=.1f;camera.farClipPlane=150;camera.depth=-20;camera.allowHDR=false;
            var config=Resources.Load<RetroRenderConfig>("RetroFantasy/RenderConfig");
            if(config!=null)camera.GetUniversalAdditionalCameraData().SetRenderer(config.rendererIndex);
            return camera;
        }
        public void ShowTown()
        {
            ClearPlayerImpacts();
            townMode=true;view.orthographic=true;if(viewWeapon!=null)viewWeapon.SetActive(false);if(viewShield!=null)viewShield.SetActive(false);town.SetActive(true);if(field!=null)field.SetActive(false);portrait.SetActive(true);
            target.Release();target.width=1280;target.height=640;target.Create();view.aspect=2;view.orthographicSize=7.4f;
            view.transform.localPosition=new Vector3(11,15,-19);view.transform.LookAt(origin+new Vector3(0,.5f,.6f));
        }
        public Vector2 TownLabel(Vector3 local)
        {
            Vector3 point=view.WorldToViewportPoint(origin+local);
            return new Vector2(point.x,1-point.y);
        }
        public static Vector3 WorldPoint(float x,float y)=>new Vector3(x/50f,0,-y/50f);
        public void BeginField(MmoSnapshot snapshot,Vector2 scroll)
        {
            string key=snapshot.zone+":"+snapshot.instance_id;
            if(townMode || field==null || fieldKey!=key)
            {
                townMode=false;town.SetActive(false);portrait.SetActive(false);fieldKey=key;
                ReturnFieldCombatVisuals();
                if(field!=null)RemoveOwned(field);
                if(fieldGroundMesh!=null){ownedMeshes.Remove(fieldGroundMesh);RemoveOwned(fieldGroundMesh);fieldGroundMesh=null;}
                cameraWalls.Clear();followDistance=0;
                cameraWalls.Add(new Bounds(new Vector3(36,1,1.5f),new Vector3(76,2,2)));
                cameraWalls.Add(new Bounds(new Vector3(36,1,-49.5f),new Vector3(76,2,2)));
                cameraWalls.Add(new Bounds(new Vector3(-1.5f,1,-24),new Vector3(2,2,52)));
                cameraWalls.Add(new Bounds(new Vector3(73.5f,1,-24),new Vector3(2,2,52)));
                enemyWarnings.Clear();impactUntil.Clear();deathUntil.Clear();previousWindups.Clear();dangerMarkers.Clear();actors.Clear();lastPositions.Clear();actionUntil.Clear();actionState.Clear();
                ClearPlayerImpacts();actorFacing.Clear();
                squadObjectiveRoot=null;squadBuildings.Clear();ClearSquadVisuals();
                field=new GameObject("Encounter "+snapshot.zone);field.transform.SetParent(transform,false);
                fieldGroundMesh=Ground(field.transform,new Vector3(36,-.025f,-24),new Vector2(76,52),snapshot.zone=="ruins"?"stones":"grass",snapshot.zone=="minefield"?new Color(.88f,.76f,.68f):Color.white);
                if(snapshot.obstacles!=null)foreach(var obstacle in snapshot.obstacles)
                {
                    var center=WorldPoint(obstacle.x+obstacle.width*.5f,obstacle.y+obstacle.height*.5f);
                    cameraWalls.Add(new Bounds(center+Vector3.up,new Vector3(obstacle.width/50f,2,obstacle.height/50f)));
                    var model=Model("wall",center,Vector3.zero,new Vector3(obstacle.width/50f,2,obstacle.height/50f),field.transform);
                    if(model==null)continue;
                    // Decorative items remain within server-authoritative obstacle footprints.
                    Model("chest",center+new Vector3(0,.78f,0),Vector3.zero,Vector3.one*.55f,field.transform);
                }
                for(int i=0;i<30;i++)
                {float x=i*2.5f;Model("wall",new Vector3(x,0,1.5f),Vector3.zero,new Vector3(2.5f,2,2),field.transform);Model("wall",new Vector3(x,0,-49.5f),Vector3.zero,new Vector3(2.5f,2,2),field.transform);}
                for(int i=0;i<20;i++){float z=-i*2.5f;Model("wall",new Vector3(-1.5f,0,z),Vector3.zero,new Vector3(2,2,2.5f),field.transform);Model("wall",new Vector3(73.5f,0,z),Vector3.zero,new Vector3(2,2,2.5f),field.transform);}
                for(int i=0;i<18;i++)Model(i%3==0?"banner":i%3==1?"column":"barrel",new Vector3(2+i*4,0,.4f),Vector3.zero,Vector3.one*1.5f,field.transform);
                SetLayer(field);
                target.Release();target.width=1240;target.height=460;target.Create();
            }
            view.aspect=1240f/460;view.orthographicSize=460f/100;
            Vector3 centerPoint=WorldPoint(scroll.x+620,scroll.y+230);
            var rotation=Quaternion.Euler(55,0,0);view.transform.rotation=rotation;view.transform.position=origin+centerPoint-rotation*Vector3.forward*35;
            alive.Clear();
        }
        public void Actor(string key,float x,float y,float fx,float fy,bool attack,bool dodge,bool enemy,bool boss)
        {
            alive.Add(key);Vector3 point=WorldPoint(x,y);
            if(!actors.TryGetValue(key,out var actor))
            {
                actor=Instantiate(enemy?orc:hero,field.transform);actor.name=key;actor.transform.localScale=Vector3.one*(boss?2.9f:1.7f);
                SetLayer(actor);actors.Add(key,actor);
                if(fieldKey.StartsWith("squad:"))actor.AddComponent<CharacterScaleStability>().Capture();
                if(enemy){var block=new MaterialPropertyBlock();block.SetColor("_BaseColor",boss?new Color(.65f,.3f,.21f):new Color(.8f,.53f,.45f));foreach(var skin in actor.GetComponentsInChildren<SkinnedMeshRenderer>())skin.SetPropertyBlock(block);}
            }
            // A live snapshot for the same id cancels every transient corpse/action state.
            if(deathUntil.Remove(key))
            {
                impactUntil.Remove(key);playerImpactUntil.Remove(key);previousWindups.Remove(key);
                actionUntil.Remove(key);actionState.Remove(key);walkUntil.Remove(key);lastPositions.Remove(key);
                var oldReaction=actor.GetComponent<HeroHitReaction>();if(oldReaction!=null)oldReaction.Clear();
                var oldAnimation=actor.GetComponent<Animation>();if(oldAnimation!=null){oldAnimation.Stop();foreach(AnimationState state in oldAnimation)state.speed=1;}
            }
            var reaction=actor.GetComponent<HeroHitReaction>();
            if(fieldKey.StartsWith("squad:")&&key.StartsWith("enemy:"))
            {
                var visibility=actor.GetComponent<FogActorVisibility>();
                if(visibility==null)visibility=actor.AddComponent<FogActorVisibility>();
                if(visibility.IsHidden){var paused=actor.GetComponent<Animation>();if(paused!=null)foreach(AnimationState state in paused)state.speed=1;}
                visibility.Show(Time.unscaledTime);
            }
            if(reaction!=null)reaction.RestorePose();
            float expiry=playerImpactUntil.TryGetValue(key,out var hitUntil)?hitUntil:0;
            if(expiry>Time.unscaledTime&&reaction==null)reaction=actor.AddComponent<HeroHitReaction>();
            if(reaction!=null)reaction.PlayUntil(expiry);
            bool moving=lastPositions.TryGetValue(key,out var previous)&&Vector3.Distance(previous,point)>.005f;
            if(moving)walkUntil[key]=Time.unscaledTime+.14f;
            moving=walkUntil.TryGetValue(key,out float walkEnd)&&Time.unscaledTime<walkEnd;
            actor.transform.localPosition=point;lastPositions[key]=point;
            if(Mathf.Abs(fx)+Mathf.Abs(fy)>.01f)actorFacing[key]=Quaternion.LookRotation(new Vector3(fx,0,-fy));
            if(!actorFacing.TryGetValue(key,out var facing)){facing=actor.transform.localRotation;actorFacing[key]=facing;}
            actor.transform.localRotation=facing;
            if(!actor.activeSelf)return;
            var animation=actor.GetComponent<Animation>();
            actionUntil.TryGetValue(key,out float until);
            if(dodge&&(!actionState.TryGetValue(key,out string active)||active!="Dodge"||Time.time>=until))
            {actionState[key]="Dodge";actionUntil[key]=Time.time+.42f;}
            else if(attack&&Time.time>=until){actionState[key]="Attack";actionUntil[key]=Time.time+.43f;}
            string clip=actionUntil.TryGetValue(key,out until)&&Time.time<until?actionState[key]:moving?"Walk":"Idle";
            if(!animation.IsPlaying(clip))animation.CrossFade(clip,.1f);

        }
        public void EndField()
        {
            var remove=new List<string>();foreach(var pair in actors)if(!alive.Contains(pair.Key))remove.Add(pair.Key);
            foreach(string key in remove){
                if(deathUntil.TryGetValue(key,out float expires)&&Time.unscaledTime<expires)
                {
                    float phase=1-(expires-Time.unscaledTime)/.55f;
                    var corpse=actors[key];var hitReaction=corpse.GetComponent<HeroHitReaction>();if(hitReaction!=null)hitReaction.Clear();
                    corpse.transform.localRotation=Quaternion.Euler(0,corpse.transform.localEulerAngles.y,phase*85);
                    corpse.transform.localPosition+=Vector3.down*Time.unscaledDeltaTime*.4f;
                    var dyingAnimation=corpse.GetComponent<Animation>();if(dyingAnimation!=null)dyingAnimation.Stop();continue;
                }
                if(fieldKey.StartsWith("squad:")&&key.StartsWith("enemy:")&&!deathUntil.ContainsKey(key))
                {
                    var visibility=actors[key].GetComponent<FogActorVisibility>();
                    if(visibility!=null)
                    {
                        visibility.Hide(Time.unscaledTime);
                        if(visibility.Keep(Time.unscaledTime))
                        {
                            var animation=actors[key].GetComponent<Animation>();if(animation!=null)foreach(AnimationState state in animation)state.speed=0;
                            if(squadArcs.TryGetValue(key,out var arc))arc.enabled=false;
                            continue;
                        }
                    }
                }
                impactUntil.Remove(key);deathUntil.Remove(key);previousWindups.Remove(key);
                playerImpactUntil.Remove(key);
                RemoveCompanionVisuals(key);actorFacing.Remove(key);walkUntil.Remove(key);squadArcs.Remove(key);
                RemoveOwned(actors[key]);actors.Remove(key);lastPositions.Remove(key);actionUntil.Remove(key);actionState.Remove(key);}
        }
        public void SetActorAppearance(string key,int role,bool hit)
        {
            if(!actors.TryGetValue(key,out var actor))return;
            Color color=role<0?Color.white:role==1?new Color(.64f,.83f,1):role==2?new Color(.67f,1,.71f):Color.white;
            if(hit)color=new Color(2,1.1f,.8f);
            color=Color.Lerp(color,new Color(2,.48f,.25f),PlayerImpactWeight(key));
            appearanceBlock.Clear();appearanceBlock.SetColor("_BaseColor",color);
            foreach(var skin in actor.GetComponentsInChildren<SkinnedMeshRenderer>())skin.SetPropertyBlock(appearanceBlock);
        }
        public void FirstPerson(string self,float x,float y,float yaw,float pitch,bool attack,bool dodge)
        {
            view.orthographic=false;view.fieldOfView=70;view.nearClipPlane=.04f;
            Vector3 foot=WorldPoint(x,y);bool moving=(foot-previousEye).sqrMagnitude>.00001f;previousEye=foot;
            float bob=moving?Mathf.Sin(Time.time*11)*.018f:0;
            view.transform.position=origin+foot+Vector3.up*(1.10f+bob-(dodge?.16f:0));
            view.transform.rotation=Quaternion.Euler(pitch,yaw,0);
            if(actors.TryGetValue(self,out var body))body.SetActive(false);
            if(viewWeapon==null)
            {
                viewWeapon=Model("weapon-sword",Vector3.zero,Vector3.zero,Vector3.one*1.15f,view.transform);
                viewShield=Model("shield-round",new Vector3(-.32f,-.28f,.55f),new Vector3(0,180,0),Vector3.one*.85f,view.transform);
            }
            if(attack&&Time.time>=firstPersonAttackUntil)firstPersonAttackUntil=Time.time+.36f;
            float phase=Mathf.Clamp01(1-(firstPersonAttackUntil-Time.time)/.36f);
            float swing=Time.time<firstPersonAttackUntil?Mathf.Sin(phase*Mathf.PI):0;
            if(viewWeapon!=null)
            {viewWeapon.SetActive(true);viewWeapon.transform.localPosition=new Vector3(.32f-swing*.3f,-.32f+bob,.55f);viewWeapon.transform.localRotation=Quaternion.Euler(-15+swing*65,-15-swing*35,-20-swing*65);}
            if(viewShield!=null)viewShield.SetActive(true);
        }
        public void ThirdPerson(string self,float x,float y,float yaw,float pitch,float distance)
        {
            view.orthographic=false;view.fieldOfView=60;view.nearClipPlane=.08f;
            if(viewWeapon!=null)viewWeapon.SetActive(false);
            if(viewShield!=null)viewShield.SetActive(false);
            if(actors.TryGetValue(self,out var body))body.SetActive(true);
            var rotation=Quaternion.Euler(Mathf.Clamp(pitch,-35,48),yaw,0);
            Vector3 anchor=WorldPoint(x,y)+Vector3.up*1.2f;
            Vector3 back=rotation*Vector3.back;
            float allowed=Mathf.Clamp(distance,3.5f,8);
            // Use server obstacle footprints: imported decoration has no physics colliders.
            var ray=new Ray(anchor,back);
            foreach(var wall in cameraWalls)
            {
                var padded=wall;padded.Expand(.4f);
                if(padded.Contains(anchor)){allowed=.15f;break;}
                if(padded.IntersectRay(ray,out float hit))allowed=Mathf.Min(allowed,Mathf.Max(.15f,hit-.08f));
            }
            // Looking up lowers the orbit camera: shorten the boom before it crosses the floor.
            if(back.y<0)allowed=Mathf.Min(allowed,(anchor.y-.3f)/-back.y);
            // Pull in immediately to avoid walls; ease back out after leaving cover.
            followDistance=followDistance<=0||allowed<followDistance?allowed:Mathf.MoveTowards(followDistance,allowed,Time.deltaTime*5);
            view.transform.SetPositionAndRotation(origin+anchor+back*followDistance,rotation);
            float hurt=PlayerImpactWeight(self);
            if(hurt>0)
            {
                float phase=(1-hurt)*32;
                var impulse=(view.transform.right*Mathf.Sin(phase)+view.transform.up*Mathf.Sin(phase*1.3f))*(.035f*hurt);
                var position=view.transform.position+impulse;position.y=Mathf.Max(origin.y+.3f,position.y);view.transform.position=position;
                view.transform.rotation=rotation*Quaternion.Euler(0,0,Mathf.Sin(phase*.9f)*.65f*hurt);
            }
            float shotAge=Time.unscaledTime-ownBowImpulseAt;
            if(shotAge>=0&&shotAge<.12f)
            {
                float kick=Mathf.Sin(shotAge/.12f*Mathf.PI)*(1-shotAge/.12f);
                view.transform.rotation*=Quaternion.Euler(-ownBowImpulseStrength*kick,0,0);
                var position=view.transform.position-view.transform.forward*(.018f*kick);position.y=Mathf.Max(origin.y+.3f,position.y);view.transform.position=position;
            }
        }
        public bool Project(float x,float y,float height,out Vector2 point)
        {
            var projected=view.WorldToViewportPoint(origin+WorldPoint(x,y)+Vector3.up*height);
            point=new Vector2(projected.x*1240,(1-projected.y)*460);return projected.z>view.nearClipPlane;
        }
        public void Hazards(MmoHazard[] hazards)
        {
            int count=Mathf.Min(64,hazards?.Length??0);
            EnsureDangerMesh();
            for(int i=dangerMarkers.Count;i<count;i++)
            {
                var marker=new GameObject("Growing danger ring");marker.transform.SetParent(field.transform,false);marker.AddComponent<MeshFilter>().sharedMesh=dangerMesh;
                marker.AddComponent<MeshRenderer>().sharedMaterial=Resources.Load<Material>("MiniDungeon/Materials/Danger");SetLayer(marker);dangerMarkers.Add(marker);
                Model("trap",new Vector3(0,.01f,0),Vector3.zero,Vector3.one*.28f,marker.transform);
            }
            for(int i=0;i<dangerMarkers.Count;i++)
            {
                dangerMarkers[i].SetActive(i<count);if(i>=count)continue;
                dangerMarkers[i].transform.localPosition=WorldPoint(hazards[i].x,hazards[i].y)+Vector3.up*.025f;
                float radius=Mathf.Max(.02f,hazards[i].radius/50f);dangerMarkers[i].transform.localScale=new Vector3(radius,1,radius);
            }
        }
        private void EnsureDangerMesh()
        {
            if(dangerMesh==null)
            {
                dangerMesh=new Mesh {name="Authoritative hazard ring"};var points=new List<Vector3>();var indices=new List<int>();
                for(int i=0;i<=48;i++){float angle=i*Mathf.PI*2/48;var p=new Vector3(Mathf.Sin(angle),0,Mathf.Cos(angle));points.Add(p);points.Add(p*.88f);if(i<48){int n=i*2;indices.AddRange(new[]{n,n+2,n+1,n+1,n+2,n+3});}}
                dangerMesh.SetVertices(points);dangerMesh.SetTriangles(indices,0);dangerMesh.RecalculateNormals();dangerMesh.RecalculateBounds();ownedMeshes.Add(dangerMesh);
            }
        }
        public void EnemyImpact(string id,bool dead)
        {
            string key="enemy:"+id;
            impactUntil[key]=Time.unscaledTime+.2f;
            if(dead)deathUntil[key]=Time.unscaledTime+.55f;
            else if(fieldKey.StartsWith("squad:")&&actors.TryGetValue(key,out var actor))
            {float expiry=Time.unscaledTime+HeroHitReaction.Duration;playerImpactUntil[key]=expiry;var reaction=actor.GetComponent<HeroHitReaction>()??actor.AddComponent<HeroHitReaction>();reaction.PlayUntil(expiry);}
        }
        public void PlayerImpact(string id,bool dead=false)
        {
            if(string.IsNullOrEmpty(id))return;
            string key="player:"+id;if(dead)deathUntil[key]=Time.unscaledTime+.55f;float expiry=Time.unscaledTime+HeroHitReaction.Duration;playerImpactUntil[key]=expiry;
            if(actors.TryGetValue(key,out var actor))
            {
                var reaction=actor.GetComponent<HeroHitReaction>()??actor.AddComponent<HeroHitReaction>();reaction.PlayUntil(expiry);
            }
        }
        public void ClearPlayerImpacts()
        {
            playerImpactUntil.Clear();foreach(var actor in actors.Values)if(actor!=null){var reaction=actor.GetComponent<HeroHitReaction>();if(reaction!=null)reaction.Clear();}
        }
        private float PlayerImpactWeight(string key)=>playerImpactUntil.TryGetValue(key,out float until)?Mathf.Clamp01((until-Time.unscaledTime)/HeroHitReaction.Duration):0;
        public void SquadObjectives(SquadSnapshot snapshot)
        {
            if(field==null||snapshot==null||snapshot.world==null)return;
            if(squadObjectiveRoot==null)
            {
                squadObjectiveRoot=new GameObject("Squad headquarters and camps");squadObjectiveRoot.transform.SetParent(field.transform,false);
                if(snapshot.bases!=null)foreach(var headquarters in snapshot.bases)
                {
                    var node=new GameObject(headquarters.id);node.transform.SetParent(squadObjectiveRoot.transform,false);
                    node.transform.localPosition=WorldPoint(headquarters.x,headquarters.y);squadBuildings[headquarters.id]=node;
                    Model("gate",Vector3.zero,new Vector3(0,headquarters.team==0?90:-90,0),Vector3.one*2.2f,node.transform);
                    foreach(float x in new[]{-1.4f,1.4f})
                    {
                        Model("column",new Vector3(x,0,-.7f),Vector3.zero,new Vector3(1.2f,2.2f,1.2f),node.transform);
                        Model("column",new Vector3(x,0,.7f),Vector3.zero,new Vector3(1.2f,2.2f,1.2f),node.transform);
                    }
                    Model("banner",new Vector3(0,2.1f,0),Vector3.zero,Vector3.one*1.4f,node.transform);
                    foreach(var renderer in node.GetComponentsInChildren<Renderer>())
                    {
                        var block=new MaterialPropertyBlock();block.SetColor("_BaseColor",headquarters.team==snapshot.team?new Color(.62f,.82f,1):new Color(1,.55f,.4f));renderer.SetPropertyBlock(block);
                    }
                    // Camera avoidance matches the visible fort footprint, without changing gameplay collision.
                    if(headquarters.team!=snapshot.team)cameraWalls.Add(new Bounds(node.transform.localPosition+Vector3.up*1.5f,new Vector3(3.7f,3,3.2f)));
                }
                if(snapshot.camps!=null)foreach(var camp in snapshot.camps)
                {
                    var node=new GameObject("Recruitment camp "+camp.team);node.transform.SetParent(squadObjectiveRoot.transform,false);node.transform.localPosition=WorldPoint(camp.x,camp.y);
                    Model("floor-detail",new Vector3(0,.015f,0),Vector3.zero,Vector3.one*3.5f,node.transform);
                    Model("chest",new Vector3(-1.1f,0,.7f),Vector3.zero,Vector3.one,node.transform);
                    Model("banner",new Vector3(1.25f,0,.7f),Vector3.zero,Vector3.one*1.5f,node.transform);
                    Model("barrel",new Vector3(1.4f,0,-.6f),Vector3.zero,Vector3.one,node.transform);
                }
                SetLayer(squadObjectiveRoot);
            }
            if(snapshot.bases!=null)foreach(var headquarters in snapshot.bases)
                if(squadBuildings.TryGetValue(headquarters.id,out var building))
                {
                    bool obscures=false;
                    if(headquarters.team==snapshot.team&&snapshot.world.players!=null)
                    {
                        foreach(var self in snapshot.world.players)if(self.id==snapshot.world.you_id)
                        {
                            var anchor=WorldPoint(self.x,self.y)+Vector3.up*1.2f;
                            var cameraPoint=view.transform.position-origin;var delta=cameraPoint-anchor;
                            var bounds=new Bounds(building.transform.localPosition+Vector3.up*1.5f,new Vector3(3.7f,3,3.2f));
                            obscures=bounds.IntersectRay(new Ray(anchor,delta.normalized),out float hit)&&hit<delta.magnitude;
                            break;
                        }
                    }
                    building.SetActive(!obscures);
                    bool destroyed=headquarters.hp<=0;building.transform.localRotation=Quaternion.Euler(0,0,destroyed?18:0);
                    building.transform.localScale=destroyed?new Vector3(1,.5f,1):Vector3.one;
                }
        }
        public void SquadSide(string key,bool ally,bool hit)
        {
            if(!actors.TryGetValue(key,out var actor))return;
            var tint=ally?new Color(.68f,.86f,1):new Color(1,.48f,.38f);
            if(ally&&key.EndsWith(":healer"))tint=new Color(.55f,1,.7f);
            if(ally&&key.EndsWith(":archer"))tint=new Color(1,.9f,.55f);
            if(hit)tint=new Color(2,1.1f,.8f);
            tint=Color.Lerp(tint,new Color(2,.48f,.25f),PlayerImpactWeight(key));
            appearanceBlock.Clear();appearanceBlock.SetColor("_BaseColor",tint);
            foreach(var skin in actor.GetComponentsInChildren<SkinnedMeshRenderer>())skin.SetPropertyBlock(appearanceBlock);
        }
        // Authoritative windup geometry only; these meshes never apply damage or collisions.
        public void EnemyTelegraphs(MmoEnemy[] enemies)
        {
            if(field==null)return;
            EnsureDangerMesh();int used=0;
            if(enemies!=null)foreach(var enemy in enemies)
            {
                string key="enemy:"+enemy.id;
                if(!fieldKey.StartsWith("squad:")&&enemy.hp>0&&actors.TryGetValue(key,out var actor))
                {
                    if(deathUntil.ContainsKey(key))deathUntil.Remove(key);
                    float prior=0;previousWindups.TryGetValue(key,out prior);
                    if(enemy.windup_left<=0&&prior>0&&enemy.stagger_left<=0)
                    {actionState[key]="Attack";actionUntil[key]=Time.time+.43f;}
                    previousWindups[key]=enemy.windup_left;
                    var animation=actor.GetComponent<Animation>();
                    if(enemy.stagger_left>0||(impactUntil.TryGetValue(key,out float until)&&until>Time.unscaledTime))
                    {
                        // Actor() restores facing/position on the next presentation frame.
                        actor.transform.localRotation*=Quaternion.Euler(-12,0,Mathf.Sin(Time.unscaledTime*50)*5);
                        if(animation!=null&&!animation.IsPlaying("Idle"))animation.CrossFade("Idle",.03f);
                    }
                    else if(enemy.windup_left>0)
                    {
                        var direction=WorldPoint(enemy.attack_x-enemy.x,enemy.attack_y-enemy.y);
                        if(direction.sqrMagnitude>.001f)actor.transform.localRotation=Quaternion.LookRotation(direction);
                        actor.transform.localRotation*=Quaternion.Euler(-10,0,0);
                    }
                }
                if(enemy.hp<=0||enemy.windup_left<=0||enemy.attack_radius<=0||used>=64)continue;
                if(used>=enemyWarnings.Count)
                {
                    var marker=new GameObject("Enemy authoritative attack warning");marker.transform.SetParent(field.transform,false);
                    marker.AddComponent<MeshFilter>().sharedMesh=dangerMesh;
                    marker.AddComponent<MeshRenderer>().sharedMaterial=Resources.Load<Material>("MiniDungeon/Materials/Danger");
                    var progress=new GameObject("Windup progress");progress.transform.SetParent(marker.transform,false);
                    progress.AddComponent<MeshFilter>().sharedMesh=dangerMesh;
                    progress.AddComponent<MeshRenderer>().sharedMaterial=Resources.Load<Material>("MiniDungeon/Materials/Danger");
                    SetLayer(marker);enemyWarnings.Add(marker);
                }
                var warning=enemyWarnings[used++];warning.SetActive(true);
                warning.transform.localPosition=WorldPoint(enemy.attack_x,enemy.attack_y)+Vector3.up*.035f;
                float radius=Mathf.Max(.02f,enemy.attack_radius/50f);
                warning.transform.localScale=new Vector3(radius,1,radius);
                float fill=Mathf.Clamp01(1-enemy.windup_left/Mathf.Max(.01f,enemy.windup_duration));
                warning.transform.GetChild(0).localScale=new Vector3(Mathf.Max(.03f,fill),1,Mathf.Max(.03f,fill));
                warning.transform.GetChild(0).localPosition=Vector3.up*.008f;
            }
            for(int i=used;i<enemyWarnings.Count;i++)enemyWarnings[i].SetActive(false);
        }
        private void BuildTown()
        {
            Ground(town.transform,new Vector3(0,-.04f,0),new Vector2(23,19),"stones",Color.white);
            Building(new Vector3(-6,0,3),"Expedition Gate",3);
            Building(new Vector3(0,0,5),"Ancient Gate",4);
            Building(new Vector3(6,0,3),"Equipment Vault",2);
            Building(new Vector3(-6,0,-3.5f),"Party Camp",2);
            Building(new Vector3(6,0,-3.5f),"Quest Archive",2);
            for(int i=-4;i<=4;i++)Model("wall",new Vector3(i*2.5f,0,8.6f),Vector3.zero,new Vector3(2.5f,1.2f,1.3f),town.transform);
            for(int i=0;i<4;i++)Model("column",new Vector3(i%2==0?-10:10,0,i<2?6:-6),Vector3.zero,Vector3.one*2,town.transform);
            Model("floor-detail",new Vector3(0,.01f,0),Vector3.zero,Vector3.one*3,town.transform);
            Model("barrel",new Vector3(-3.5f,0,-2),Vector3.zero,Vector3.one*1.5f,town.transform);
            if(hero!=null){var guide=Instantiate(hero,town.transform);guide.transform.localPosition=new Vector3(0,0,-1);guide.transform.localScale=Vector3.one*2;guide.transform.localRotation=Quaternion.Euler(0,160,0);}
        }
        private void Building(Vector3 center,string name,int height)
        {
            var building=new GameObject(name);building.transform.SetParent(town.transform,false);building.transform.localPosition=center;
            for(int x=-1;x<=1;x++)Model("wall",new Vector3(x*1.1f,0,1.1f),Vector3.zero,new Vector3(1.1f,1.4f,1),building.transform);
            for(int z=-1;z<=0;z++)foreach(int x in new[]{-1,1})Model("wall-half",new Vector3(x*1.65f,0,z*1.1f),new Vector3(0,90,0),new Vector3(1.1f,1.3f,1.1f),building.transform);
            foreach(float x in new[]{-1.6f,1.6f})Model("column",new Vector3(x,0,-1.5f),Vector3.zero,Vector3.one*1.6f,building.transform);
            Model("wood-structure",new Vector3(0,0,-1.5f),Vector3.zero,new Vector3(1.5f,1.5f,1),building.transform);
            Model(name.Contains("Vault")?"chest":name.Contains("Archive")?"table":name.Contains("Camp")?"barrel":"gate",new Vector3(0,0,0),Vector3.zero,Vector3.one*1.5f,building.transform);
            Model("banner",new Vector3(-1,1.3f,.55f),Vector3.zero,Vector3.one,building.transform);
        }
        private GameObject Model(string name,Vector3 position,Vector3 angles,Vector3 scale,Transform parent)
        {
            var source=Resources.Load<GameObject>("MiniDungeon/Models/"+name);if(source==null)return null;
            var instance=Instantiate(source,parent);instance.transform.localPosition=position;instance.transform.localEulerAngles=angles;instance.transform.localScale=scale;
            foreach(var renderer in instance.GetComponentsInChildren<Renderer>())
            {
                var assigned=renderer.sharedMaterials;
                for(int i=0;i<assigned.Length;i++)assigned[i]=dungeonMaterial;
                renderer.sharedMaterials=assigned;
            }
            SetLayer(instance);return instance;
        }
        private Mesh Ground(Transform parent,Vector3 center,Vector2 size,string materialName,Color tint)
        {
            var go=new GameObject("Textured ground");go.transform.SetParent(parent,false);go.transform.localPosition=center;
            var mesh=new Mesh {name="Tiled ground"};float x=size.x*.5f,z=size.y*.5f;
            mesh.vertices=new[]{new Vector3(-x,0,-z),new Vector3(-x,0,z),new Vector3(x,0,z),new Vector3(x,0,-z)};
            mesh.triangles=new[]{0,1,2,0,2,3};mesh.uv=new[]{Vector2.zero,new Vector2(0,size.y),size,new Vector2(size.x,0)};mesh.RecalculateNormals();mesh.RecalculateBounds();ownedMeshes.Add(mesh);
            go.AddComponent<MeshFilter>().sharedMesh=mesh;var renderer=go.AddComponent<MeshRenderer>();
            renderer.sharedMaterial=materials[materialName];var block=new MaterialPropertyBlock();block.SetColor("_BaseColor",tint);renderer.SetPropertyBlock(block);SetLayer(go);
            return mesh;
        }
        public static void SetLayer(GameObject root){foreach(var child in root.GetComponentsInChildren<Transform>(true))child.gameObject.layer=ModelLayer;}
        private void OnDestroy()
        {
            if(view!=null)view.targetTexture=null;if(portraitCamera!=null)portraitCamera.targetTexture=null;
            if(target!=null){target.Release();RemoveOwned(target);}if(portraitTarget!=null){portraitTarget.Release();RemoveOwned(portraitTarget);}
            if(squadEffectMaterial!=null)RemoveOwned(squadEffectMaterial);
            foreach(var mesh in ownedMeshes)if(mesh!=null)RemoveOwned(mesh);
        }
        private static void RemoveOwned(Object value){if(Application.isPlaying)Destroy(value);else DestroyImmediate(value);}
    }
}

using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;
namespace Warfront
{
    [Serializable] public sealed class RtsMatchRequest {public int team_size=1;}
    [Serializable] public sealed class RtsMember {public string owner_id,base_id,name;public int team;}
    [Serializable] public sealed class RtsPing {public string owner_id;public int team;public float x,y;}
    public sealed class RtsUnitIdentity:MonoBehaviour {public string id,owner,kind;public int team;public LineRenderer ring;}
    public sealed partial class RetroFantasyScene
    {
        public void RtsBoard()
        {
            if(field==null||field.transform.Find("RTS Grid")!=null)return;
            var board=new GameObject("RTS Grid",typeof(Grid));board.transform.SetParent(field.transform,false);
            board.GetComponent<Grid>().cellSwizzle=GridLayout.CellSwizzle.XZY;
            // 64 meshes, 256 cells each. No per-cell GameObjects.
            for(int cy=0;cy<8;cy++)for(int cx=0;cx<8;cx++){
                var vertices=new List<Vector3>();var triangles=new List<int>();var uv=new List<Vector2>();
                for(int y=0;y<16;y++)for(int x=0;x<16;x++){
                    int n=vertices.Count;float px=cx*16+x,pz=-(cy*16+y);
                    vertices.Add(new Vector3(px,.015f,pz));vertices.Add(new Vector3(px+1,.015f,pz));vertices.Add(new Vector3(px+1,.015f,pz-1));vertices.Add(new Vector3(px,.015f,pz-1));
                    triangles.AddRange(new[]{n,n+1,n+2,n,n+2,n+3});uv.AddRange(new[]{Vector2.zero,Vector2.right,Vector2.one,Vector2.up});
                }
                var mesh=new Mesh{name="RTS 16x16 cells"};mesh.SetVertices(vertices);mesh.SetTriangles(triangles,0);mesh.SetUVs(0,uv);mesh.RecalculateNormals();ownedMeshes.Add(mesh);
                var chunk=new GameObject("Chunk "+cx+","+cy,typeof(MeshFilter),typeof(MeshRenderer));chunk.transform.SetParent(board.transform,false);chunk.GetComponent<MeshFilter>().sharedMesh=mesh;chunk.GetComponent<MeshRenderer>().sharedMaterial=materials["grass"];
            }
            for(int corner=0;corner<4;corner++){
                float x=corner==0||corner==2?12:116,z=corner==0||corner==3?-12:-116;
                float sx=x<64?1:-1,sz=z>-64?-1:1;
                for(int i=0;i<5;i++)Model("chest",new Vector3(x+sx*(3.6f+i*1.4f),0,z+sz*4),Vector3.zero,Vector3.one,board.transform);
            }
            SetLayer(board);
        }
        public void RtsBuildings(SquadSnapshot snapshot)
        {
            if(snapshot.bases==null)return;
            foreach(var b in snapshot.bases)if(squadBuildings.TryGetValue(b.id,out var node)&&node!=null){
                var tag=node.GetComponent<RtsUnitIdentity>()??node.AddComponent<RtsUnitIdentity>();tag.id=b.id;tag.kind="base";tag.team=b.team;tag.owner="";
                if(node.GetComponent<Collider>()==null){var box=node.AddComponent<BoxCollider>();box.center=Vector3.up*1.5f;box.size=new Vector3(4,3,4);}
            }
        }
        public void RtsCamera(bool first,string self,float x,float y,float yaw,float pitch,Vector2 center,float zoom)
        {
            foreach(var a in actors.Values)if(a!=null)a.SetActive(true);
            if(first){ThirdPerson(self,x,y,QuarterYaw,35.264f,Mathf.Clamp(zoom,3.5f,8));return;}
            if(viewWeapon!=null)viewWeapon.SetActive(false);if(viewShield!=null)viewShield.SetActive(false);
            view.orthographic=true;view.aspect=1240f/572;view.orthographicSize=zoom;view.farClipPlane=400;
            QuarterCamera(WorldPoint(center.x,center.y),zoom);
        }
        public void RtsSync(MmoSnapshot world,HashSet<string> selected)
        {
            if(world.players!=null)foreach(var a in world.players)RtsIdentity("player:"+a.id,a.id,a.owner_id,a.kind,a.team,a.hp>0&&selected.Contains(a.id));
            if(world.enemies!=null)foreach(var a in world.enemies)RtsIdentity("enemy:"+a.id,a.id,a.owner_id,a.kind,a.team,false);
            UpdateZodiacEffects(world.effects);
        }
        private void RtsIdentity(string key,string id,string owner,string kind,int team,bool selected)
        {
            if(!actors.TryGetValue(key,out var actor)||actor==null)return;
            var tag=actor.GetComponent<RtsUnitIdentity>()??actor.AddComponent<RtsUnitIdentity>();tag.id=id;tag.owner=owner;tag.kind=kind;tag.team=team;
            if(actor.GetComponent<Collider>()==null){var box=actor.AddComponent<BoxCollider>();box.center=new Vector3(0,.6f,0);box.size=new Vector3(.8f,1.4f,.8f);}
            if(tag.ring==null){tag.ring=CombatLine("Selection",actor.transform,49,Color.green,.045f);Arc(tag.ring,.65f,0,360,.04f);}
            tag.ring.enabled=selected;
        }
        public RtsUnitIdentity RtsPick(Vector2 point)
        {
            var ray=view.ViewportPointToRay(new Vector3(point.x/1240,1-point.y/572,0));
            RtsUnitIdentity nearest=null;float distance=float.MaxValue;foreach(var hit in Physics.RaycastAll(ray,400,1<<ModelLayer)){var unit=hit.collider.GetComponentInParent<RtsUnitIdentity>();if(unit!=null&&hit.distance<distance){nearest=unit;distance=hit.distance;}}if(nearest!=null)return nearest;
            return null;
        }
        public bool RtsGround(Vector2 point,out Vector2 goal)
        {
            goal=Vector2.zero;var ray=view.ViewportPointToRay(new Vector3(point.x/1240,1-point.y/572,0));
            if(!new Plane(Vector3.up,origin).Raycast(ray,out float d))return false;
            var p=ray.GetPoint(d)-origin;goal=new Vector2(Mathf.Clamp(p.x*50,35,6365),Mathf.Clamp(-p.z*50,35,6365));return true;
        }
    }
    public sealed partial class GameBootstrap
    {
        private bool RtsActive=>SquadModeActive&&squadSnapshot?.battle?.rts==true;
        private int rtsTeamSize=1,rtsLastGroup=-1;
        private bool rtsFirstPerson,rtsDragging;
        private float rtsZoom=67,rtsLastClick=-1,rtsGroupAt;
        private Vector2 rtsCenter=new Vector2(3200,3200),rtsDown;
        private string rtsInstance="",rtsLastUnit="",rtsInspect="",rtsOrder="none",rtsTarget="";
        private Vector2 rtsGoal;
        private readonly HashSet<string> rtsSelected=new HashSet<string>();
        private readonly List<string>[] rtsGroups=new List<string>[9];
        private GameObject rtsCanvas;
        private void UpdateRtsCanvasVisibility(){if(rtsCanvas!=null&&(!RtsActive||screen!=Screen.Mmo||mmoPanel.Length>0||SquadPauseBlocked))rtsCanvas.SetActive(false);}
        private RectTransform rtsBox;
        private MmoActor RtsActor(string id){if(mmoWorld?.players!=null)foreach(var a in mmoWorld.players)if(a.id==id)return a;return null;}
        private void UpdateRtsInput()
        {
            if(rtsFirstPerson){rtsFirstPerson=false;ReleaseDungeonCursor();rtsDragging=false;}
            if(rtsInstance!=mmoWorld.instance_id){rtsInstance=mmoWorld.instance_id;rtsSelected.Clear();Array.Clear(rtsGroups,0,9);rtsCenter=new Vector2(3200,3200);rtsZoom=67;rtsFirstPerson=false;rtsOrder="none";}
            rtsSelected.RemoveWhere(id=>{var a=RtsActor(id);return a==null||a.hp<=0||a.owner_id!=mmoWorld.you_id;});
            var k=Keyboard.current;var m=Mouse.current;
            if(k==null||m==null||!Application.isFocused||SquadPauseBlocked||mmoPanel.Length>0){rtsDragging=false;if(rtsCanvas!=null)rtsCanvas.SetActive(false);return;}

            Vector2 p=MmoUiPoint(m.position.ReadValue());bool inside=mmoField.Contains(p)&&!DungeonPointerBlocked(p);
            if(k.gKey.wasPressedThisFrame&&retroScene!=null&&retroScene.RtsGround(rtsFirstPerson?new Vector2(620,286):p-mmoField.position,out var rally)){rtsOrder="gather";rtsGoal=rally;}
            if(rtsFirstPerson){if(rtsCanvas!=null)rtsCanvas.SetActive(false);return;}
            ReleaseDungeonCursor();
            if(inside)rtsZoom=Mathf.Clamp(rtsZoom-m.scroll.ReadValue().y*.03f,8,67);
            float speed=Time.unscaledDeltaTime*rtsZoom*25;
            rtsCenter+=DungeonFirstPersonMath.Move(new Vector2((k.rightArrowKey.isPressed?1:0)-(k.leftArrowKey.isPressed?1:0),(k.downArrowKey.isPressed?1:0)-(k.upArrowKey.isPressed?1:0)),RetroFantasyScene.QuarterYaw)*speed;
            rtsCenter=new Vector2(Mathf.Clamp(rtsCenter.x,0,6400),Mathf.Clamp(rtsCenter.y,0,6400));
            bool shift=k.leftShiftKey.isPressed||k.rightShiftKey.isPressed;
            if(inside&&m.leftButton.wasPressedThisFrame){rtsDown=p;rtsDragging=true;}
            if(rtsDragging&&m.leftButton.wasReleasedThisFrame)
            {
                var rect=Rect.MinMaxRect(Mathf.Min(rtsDown.x,p.x),Mathf.Min(rtsDown.y,p.y),Mathf.Max(rtsDown.x,p.x),Mathf.Max(rtsDown.y,p.y));
                if(!shift)rtsSelected.Clear();
                if(rect.size.magnitude>8){foreach(var a in mmoWorld.players)if(a.hp>0&&a.owner_id==mmoWorld.you_id&&retroScene.Project(a.x,a.y,.5f,out var at)&&rect.Contains(at+mmoField.position))rtsSelected.Add(a.id);}
                else if(inside){var hit=retroScene.RtsPick(p-mmoField.position);if(hit!=null){rtsInspect=hit.kind+" · "+hit.id;if(hit.owner==mmoWorld.you_id){if(rtsLastUnit==hit.id&&Time.unscaledTime-rtsLastClick<.35f){foreach(var a in mmoWorld.players)if(a.hp>0&&a.owner_id==hit.owner&&a.kind==hit.kind&&retroScene.Project(a.x,a.y,.5f,out var at)&&new Rect(0,0,1240,572).Contains(at))rtsSelected.Add(a.id);}else if(shift&&rtsSelected.Contains(hit.id))rtsSelected.Remove(hit.id);else rtsSelected.Add(hit.id);rtsLastUnit=hit.id;rtsLastClick=Time.unscaledTime;}}}
                rtsDragging=false;
            }
            if(inside&&m.rightButton.wasPressedThisFrame&&retroScene.RtsGround(p-mmoField.position,out var goal)){
                var hit=retroScene.RtsPick(p-mmoField.position);rtsTarget=hit!=null&&hit.team!=squadSnapshot.team?hit.id:"";rtsOrder=rtsTarget.Length>0?"focus":"move";rtsGoal=goal;}
            var keys=new[]{k.digit1Key,k.digit2Key,k.digit3Key,k.digit4Key,k.digit5Key,k.digit6Key,k.digit7Key,k.digit8Key,k.digit9Key};
            for(int i=0;i<9;i++)if(keys[i].wasPressedThisFrame){if(k.leftCtrlKey.isPressed||k.rightCtrlKey.isPressed)rtsGroups[i]=new List<string>(rtsSelected);else if(rtsGroups[i]!=null){rtsSelected.Clear();Vector2 center=Vector2.zero;foreach(var id in rtsGroups[i]){var a=RtsActor(id);if(a!=null&&a.hp>0&&a.owner_id==mmoWorld.you_id){rtsSelected.Add(id);center+=new Vector2(a.x,a.y);}}if(rtsLastGroup==i&&Time.unscaledTime-rtsGroupAt<.35f&&rtsSelected.Count>0)rtsCenter=center/rtsSelected.Count;rtsLastGroup=i;rtsGroupAt=Time.unscaledTime;}}
            UpdateRtsBox(p);
        }
        private void UpdateRtsBox(Vector2 p)
        {
            if(rtsCanvas==null){rtsCanvas=new GameObject("RTS selection canvas",typeof(Canvas));rtsCanvas.transform.SetParent(transform);rtsCanvas.GetComponent<Canvas>().renderMode=RenderMode.ScreenSpaceOverlay;var box=new GameObject("Selection rectangle",typeof(RectTransform),typeof(Image));box.transform.SetParent(rtsCanvas.transform,false);rtsBox=box.GetComponent<RectTransform>();rtsBox.anchorMin=rtsBox.anchorMax=Vector2.zero;box.GetComponent<Image>().color=new Color(0,1,0,.18f);box.GetComponent<Image>().raycastTarget=false;}
            rtsCanvas.SetActive(rtsDragging);
            var lo=Vector2.Min(rtsDown,p);var hi=Vector2.Max(rtsDown,p);rtsBox.pivot=Vector2.zero;rtsBox.anchoredPosition=new Vector2(UiOrigin.x+lo.x*UiScale,UnityEngine.Screen.height-UiOrigin.y-hi.y*UiScale);rtsBox.sizeDelta=(hi-lo)*UiScale;
        }
        private void ApplyRtsInput(SquadInput input,bool controls)
        {
            if(!rtsFirstPerson){input.attack=false;input.dodge=false;}
            input.unit_ids=new List<string>(rtsSelected).ToArray();input.command=controls?rtsOrder:"none";input.order_x=rtsGoal.x;input.order_y=rtsGoal.y;input.target_id=rtsTarget;
            if(controls)rtsOrder="none";
        }
        private Vector2 RtsAim(Vector2 fallback)
        {
            if(Mouse.current!=null&&retroScene!=null){var p=MmoUiPoint(Mouse.current.position.ReadValue());if(mmoField.Contains(p)&&!DungeonPointerBlocked(p)&&retroScene.RtsGround(p-mmoField.position,out var goal))return goal;}
            return fallback;
        }
        private void DrawRtsHud()
        {
            if(squadSnapshot.battle.pings!=null)foreach(var ping in squadSnapshot.battle.pings)if(retroScene.Project(ping.x,ping.y,.3f,out var at))BaseText(new Rect(at.x-35,at.y-20,70,25),"집결 ▼",14,Color.green,TextAnchor.MiddleCenter);
        }
    }
}

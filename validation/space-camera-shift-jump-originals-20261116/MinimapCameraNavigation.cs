using UnityEngine;
using UnityEngine.InputSystem;

namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        public void MinimapCamera(Vector2 center,float zoom)
        {
            QuarterCamera(WorldPoint(center.x,center.y),Mathf.Clamp(zoom,3.5f,8));
        }
        // Server coordinates of the actual rendered camera's ground-plane footprint.
        public bool CameraGroundFootprint(Vector2[] corners)
        {
            if(view==null||corners==null||corners.Length<4)return false;
            for(int i=0;i<4;i++)
            {
                var uv=new Vector2(i==1||i==2?1:0,i>=2?1:0);
                var ray=view.ViewportPointToRay(uv);
                if(!new Plane(Vector3.up,origin).Raycast(ray,out float distance))return false;
                var point=ray.GetPoint(distance)-origin;
                corners[i]=new Vector2(point.x*50,-point.z*50);
            }
            return true;
        }
    }

    public sealed partial class GameBootstrap
    {
        private bool mmoMapCameraOverride,mmoMapDragging,mmoMapFollowPress;
        private int mmoMapTouchId=-1;
        private string mmoMapCameraWorld="";
        private Vector2 mmoMapCameraCenter;
        private Vector2 mmoMapDragStart;
        private readonly Vector2[] mmoMapFootprint=new Vector2[4];
        private Rect MmoMinimapInner=>new Rect(16,39,180,120);
        private Rect MmoMinimapInput=>new Rect(MmoMinimapRect.position+MmoMinimapInner.position,MmoMinimapInner.size);
        private Vector2 MmoMapWorldSize=>new Vector2(mmoWorld!=null&&mmoWorld.world_width>0?mmoWorld.world_width:3600,mmoWorld!=null&&mmoWorld.world_height>0?mmoWorld.world_height:2400);

        private Vector2 MmoCameraFocus(Vector2 follow)
        {
            string world=mmoWorld==null?"":mmoWorld.zone+":"+mmoWorld.instance_id;
            if(world!=mmoMapCameraWorld)
            {
                mmoMapCameraWorld=world;mmoMapCameraOverride=false;ReleaseMinimapDrag();
            }
            return mmoMapCameraOverride?mmoMapCameraCenter:follow;
        }
        private void ReleaseMinimapDrag(){mmoMapDragging=false;mmoMapFollowPress=false;mmoMapTouchId=-1;}
        private void ApplyMinimapCameraPoint(Vector2 point,bool begin)
        {
            var area=MmoMinimapInput;var size=MmoMapWorldSize;
            if(!begin&&mmoMapFollowPress&&(point-mmoMapDragStart).sqrMagnitude<16)return;
            var self=MmoSelf;
            if(begin&&self!=null)
            {
                var selfPoint=new Vector2(area.x+self.x/size.x*area.width,area.y+self.y/size.y*area.height);
                if((selfPoint-point).sqrMagnitude<=64)
                {
                    mmoMapCameraOverride=false;mmoMapDragging=true;mmoMapFollowPress=true;mmoMapDragStart=point;return;
                }
            }
            mmoMapCameraCenter=new Vector2(Mathf.Clamp01((point.x-area.x)/area.width)*size.x,Mathf.Clamp01((point.y-area.y)/area.height)*size.y);
            mmoMapCameraOverride=true;mmoMapDragging=true;mmoMapFollowPress=false;rtsCenter=mmoMapCameraCenter;
        }
        private void UpdateMinimapCameraInput()
        {
            var self=MmoSelf;MmoCameraFocus(self==null?Vector2.zero:new Vector2(self.x,self.y));
            if(mmoWorld==null||!DungeonLookAllowed||!Application.isFocused){ReleaseMinimapDrag();return;}
            // Capture the initiating pointer until release, including outside the map.
            if(Touchscreen.current!=null)
            {
                foreach(var touch in Touchscreen.current.touches)
                {
                    if(!touch.press.isPressed)continue;
                    int id=touch.touchId.ReadValue();var point=MmoUiPoint(touch.position.ReadValue());
                    if(mmoMapTouchId==id){ApplyMinimapCameraPoint(point,false);return;}
                    if(mmoMapTouchId<0&&!mmoMapDragging&&touch.press.wasPressedThisFrame&&MmoMinimapInput.Contains(point))
                    {
                        ApplyMinimapCameraPoint(point,true);if(mmoMapDragging)mmoMapTouchId=id;return;
                    }
                }
                if(mmoMapTouchId>=0){ReleaseMinimapDrag();return;}
            }
            var mouse=Mouse.current;
            if(mouse==null){ReleaseMinimapDrag();return;}
            var pointer=MmoUiPoint(mouse.position.ReadValue());
            if(mouse.leftButton.wasPressedThisFrame&&MmoMinimapInput.Contains(pointer))ApplyMinimapCameraPoint(pointer,true);
            else if(mmoMapDragging&&mouse.leftButton.isPressed)ApplyMinimapCameraPoint(pointer,false);
            if(!mouse.leftButton.isPressed)ReleaseMinimapDrag();
        }
        private void DrawMinimapCameraFootprint(Rect map)
        {
            if(retroScene==null||!retroScene.CameraGroundFootprint(mmoMapFootprint))return;
            var size=MmoMapWorldSize;
            GUI.BeginGroup(map);
            var matrix=GUI.matrix;
            try
            {
                for(int i=0;i<4;i++)
                {
                    var p=mmoMapFootprint[i];var q=mmoMapFootprint[(i+1)%4];
                    // Do not clamp individual corners: GUI clipping preserves the real shape at map edges.
                    var start=new Vector2(p.x/size.x*map.width,p.y/size.y*map.height);
                    var end=new Vector2(q.x/size.x*map.width,q.y/size.y*map.height);var delta=end-start;
                    GUI.matrix=matrix;GUIUtility.RotateAroundPivot(Mathf.Atan2(delta.y,delta.x)*Mathf.Rad2Deg,start);
                    Fill(new Rect(start.x,start.y-.75f,delta.magnitude,1.5f),new Color(1,1,1,.85f));
                }
            }
            finally{GUI.matrix=matrix;GUI.EndGroup();}
        }
    }
}

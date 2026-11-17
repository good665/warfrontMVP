using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        private float strategicWidth=2400,strategicHeight=3600;
        public void StrategicView(float x,float y,float zoom,float width,float height)
        {
            strategicWidth=width;strategicHeight=height;
            view.orthographic=true;view.orthographicSize=Mathf.Clamp(zoom,7.5f,14);view.aspect=1240f/572;
            view.nearClipPlane=.1f;view.farClipPlane=250;
            if(viewWeapon!=null)viewWeapon.SetActive(false);if(viewShield!=null)viewShield.SetActive(false);
            var rotation=Quaternion.Euler(55,45,0);
            var anchor=WorldPoint(Mathf.Clamp(x,35,width-35),Mathf.Clamp(y,35,height-35));
            view.transform.SetPositionAndRotation(origin+anchor-rotation*Vector3.forward*80,rotation);
        }
        public bool TryStrategicGround(Vector2 fieldPoint,out Vector2 point)
        {
            point=Vector2.zero;
            if(view==null||!view.orthographic||fieldPoint.x<0||fieldPoint.y<0||fieldPoint.x>1240||fieldPoint.y>572)return false;
            var ray=view.ViewportPointToRay(new Vector3(fieldPoint.x/1240,1-fieldPoint.y/572,0));
            var ground=new Plane(Vector3.up,new Vector3(0,origin.y,0));
            if(!ground.Raycast(ray,out float distance))return false;
            var hit=ray.GetPoint(distance)-origin;
            point=new Vector2(Mathf.Clamp(hit.x*50,35,strategicWidth-35),Mathf.Clamp(-hit.z*50,35,strategicHeight-35));
            return true;
        }
    }
    public sealed partial class GameBootstrap
    {
        private bool StrategicViewActive=>FiveFloorActive;
        private float strategicZoom=11;
        private Vector2 strategicLastAim;
        private bool strategicHasAim;
        private string strategicAimInstance="";
        private bool StrategicWorldPointer(Vector2 uiPoint)=>mmoField.Contains(uiPoint)&&!DungeonPointerBlocked(uiPoint);
        private void UpdateStrategicInput()
        {
            // A fixed RTS view never captures the cursor or rotates from pointer movement.
            ReleaseDungeonCursor();
            if(!Application.isFocused||!DungeonLookAllowed||Mouse.current==null)return;
            var point=MmoUiPoint(Mouse.current.position.ReadValue());
            if(StrategicWorldPointer(point))
            {
                strategicZoom=Mathf.Clamp(strategicZoom-Mouse.current.scroll.ReadValue().y*.006f,7.5f,14);
                if(mmoSettings!=null)mmoSettings.strategicZoom=strategicZoom;
            }
        }
        private Vector2 StrategicAim(Vector2 fallback)
        {
            string instance=mmoWorld?.instance_id??"";
            if(strategicAimInstance!=instance){strategicHasAim=false;strategicAimInstance=instance;}
            var self=MmoSelf;
            if(!strategicHasAim&&self!=null)
                fallback=new Vector2(self.x,self.y)+new Vector2(self.fx,self.fy)*800;
            Vector2 pointer=Vector2.zero;bool valid=false;
            if(Touchscreen.current!=null)foreach(var touch in Touchscreen.current.touches)
            {var p=MmoUiPoint(touch.position.ReadValue());if(touch.press.isPressed&&StrategicWorldPointer(p)){pointer=p;valid=true;break;}}
            if(!valid&&Mouse.current!=null){pointer=MmoUiPoint(Mouse.current.position.ReadValue());valid=StrategicWorldPointer(pointer);}
            if(valid&&retroScene!=null&&retroScene.TryStrategicGround(pointer-mmoField.position,out var aim))
            {strategicLastAim=aim;strategicHasAim=true;}
            return strategicHasAim?strategicLastAim:fallback;
        }
        private bool StrategicMouseAttack=>Mouse.current!=null&&Mouse.current.leftButton.isPressed&&StrategicWorldPointer(MmoUiPoint(Mouse.current.position.ReadValue()));
    }
}

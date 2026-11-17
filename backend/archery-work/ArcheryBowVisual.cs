using UnityEngine;
namespace Warfront
{
    [DefaultExecutionOrder(250)]
    public sealed class ArcheryBowVisual : MonoBehaviour
    {
        public static readonly Vector3 Grip=new Vector3(0,-.12f,.035f);
        private Transform actor,leftHand,rightHand,nock,stringGrip;
        private LineRenderer bowstring;
        private readonly Transform[] limbs=new Transform[4];
        private readonly Vector2[] widths=new Vector2[4];
        private readonly Vector3[] points=new Vector3[5];
        private readonly LineRenderer[] wind=new LineRenderer[3];
        private MaterialPropertyBlock windBlock;
        private bool active,released,hasDrawn;
        private float clipTime,releasedAt=-100;
        private Vector3 lastDrawn;
        public Vector3 ReleasePosition { get; private set; }
        public void Initialize(Transform owner,Transform left,Transform right,Transform loadedArrow)
        {
            actor=owner;leftHand=left;rightHand=right;nock=loadedArrow;bowstring=GetComponentInChildren<LineRenderer>();
            for(int i=0;i<4;i++){limbs[i]=transform.Find("Curved wood limb "+i);if(limbs[i]!=null)widths[i]=new Vector2(limbs[i].localScale.x,limbs[i].localScale.y);}
            stringGrip=transform.Find("StringGrip");if(stringGrip==null){stringGrip=new GameObject("StringGrip").transform;stringGrip.SetParent(transform,false);}
            windBlock=new MaterialPropertyBlock();
            for(int i=0;i<3;i++)
            {
                var go=new GameObject("Arrow release wind "+i);go.transform.SetParent(transform,false);go.layer=gameObject.layer;
                wind[i]=go.AddComponent<LineRenderer>();wind[i].sharedMaterial=bowstring.sharedMaterial;wind[i].useWorldSpace=false;wind[i].positionCount=2;wind[i].numCapVertices=2;wind[i].enabled=false;
            }
            Refresh();ReleasePosition=nock.position;
        }
        public void SetPhase(bool drawing,float elapsed)
        {
            if(drawing&&(!active||elapsed<clipTime-.02f)){released=false;hasDrawn=false;}
            if(drawing&&elapsed>=.25f&&!released)
            {
                var direction=actor!=null?actor.forward:transform.forward;
                ReleasePosition=hasDrawn?lastDrawn:rightHand.TransformPoint(Grip)+direction*(.32f*nock.lossyScale.z);
                releasedAt=Time.unscaledTime;released=true;
            }
            active=drawing;clipTime=elapsed;Refresh();
        }
        private void LateUpdate(){Refresh();}
        public void Refresh()
        {
            if(actor==null||leftHand==null||rightHand==null||nock==null||bowstring==null)return;
            float draw=active&&clipTime<.25f?Mathf.SmoothStep(0,1,Mathf.InverseLerp(.07f,.22f,clipTime)):0;
            float age=Time.unscaledTime-releasedAt;
            float vibration=age>=0&&age<.12f?Mathf.Exp(-age*35)*Mathf.Sin(age*100):0;
            float flex=draw+vibration*.10f;
            transform.position=leftHand.TransformPoint(Grip);transform.rotation=actor.rotation*Quaternion.AngleAxis(-5+2*draw,Vector3.forward);
            points[0]=new Vector3(0,-.24f+.018f*flex,-.055f-.045f*flex);points[1]=new Vector3(0,-.16f+.007f*flex,.02f-.018f*flex);points[2]=new Vector3(0,0,.065f);points[3]=new Vector3(0,.16f-.007f*flex,.02f-.018f*flex);points[4]=new Vector3(0,.24f-.018f*flex,-.055f-.045f*flex);
            for(int i=0;i<4;i++)if(limbs[i]!=null){var delta=points[i+1]-points[i];limbs[i].localPosition=(points[i]+points[i+1])*.5f;limbs[i].localRotation=Quaternion.LookRotation(delta);limbs[i].localScale=new Vector3(widths[i].x,widths[i].y,delta.magnitude);}
            var middle=active&&clipTime>=.07f&&clipTime<.25f?transform.InverseTransformPoint(rightHand.TransformPoint(Grip)):new Vector3(0,0,-.055f+vibration*.025f);
            bowstring.SetPosition(0,points[0]);bowstring.SetPosition(1,middle);bowstring.SetPosition(2,points[4]);stringGrip.localPosition=middle;
            nock.gameObject.SetActive(!active||clipTime<.25f);
            var stringWorld=transform.TransformPoint(middle);var rest=transform.TransformPoint(new Vector3(0,0,.065f));var directionToRest=(rest-stringWorld).normalized;
            nock.rotation=Quaternion.LookRotation(directionToRest,actor.up);nock.position=stringWorld+directionToRest*(.32f*nock.lossyScale.z);
            if(active&&clipTime>=.07f&&clipTime<.25f){lastDrawn=nock.position;hasDrawn=true;}
            for(int i=0;i<3;i++)if(wind[i]!=null)
            {
                bool show=age>=0&&age<.09f;wind[i].enabled=show;if(!show)continue;float t=age/.09f;float angle=i*120*Mathf.Deg2Rad;
                var radial=new Vector3(Mathf.Cos(angle),Mathf.Sin(angle),0);wind[i].SetPosition(0,radial*(.018f+t*.035f)+Vector3.forward*(.10f+t*.15f));wind[i].SetPosition(1,radial*(.035f+t*.055f)+Vector3.forward*(.22f+t*.20f));wind[i].widthMultiplier=.006f*(1-t);
                windBlock.Clear();windBlock.SetColor("_BaseColor",new Color(1,.93f,.72f));wind[i].SetPropertyBlock(windBlock);
            }
        }
    }
}

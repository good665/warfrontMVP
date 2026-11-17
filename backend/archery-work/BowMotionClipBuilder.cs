using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
namespace Warfront.Assets
{
    public static class BowMotionClipBuilder
    {
        static float Smooth(float a,float b,float t)=>Mathf.SmoothStep(0,1,Mathf.InverseLerp(a,b,t));
        static AnimationCurve Curve(params float[] values){var curve=new AnimationCurve();for(int i=0;i<values.Length;i+=2)curve.AddKey(values[i],values[i+1]);return curve;}
        public static AnimationClip Build(GameObject instance)
        {
            var idle=instance.GetComponent<Animation>().GetClip("Idle");var clip=UnityEngine.Object.Instantiate(idle);clip.name="Bow";clip.legacy=true;clip.wrapMode=WrapMode.ClampForever;
            foreach(var binding in AnimationUtility.GetCurveBindings(clip))
            {
                var source=AnimationUtility.GetEditorCurve(clip,binding);var curve=new AnimationCurve(source.keys.Where(k=>k.time<.65f).ToArray());curve.AddKey(.65f,source.Evaluate(.65f));AnimationUtility.SetEditorCurve(clip,binding,curve);
            }
            var torso=instance.transform.Find("root/torso");var head=torso.Find("head");var left=torso.Find("arm-left");var right=torso.Find("arm-right");var nodes=new[]{torso,head,left,right};
            var rest=nodes.Select(t=>t.localPosition).ToArray();var rotations=nodes.Select(t=>t.localRotation).ToArray();
            var leftRest=left.TransformPoint(ArcheryBowVisual.Grip);var rightRest=right.TransformPoint(ArcheryBowVisual.Grip);
            var yaw=Curve(0,0,.07f,15,.14f,35,.22f,45,.25f,45,.28f,49,.34f,42,.48f,14,.65f,0);
            var curves=nodes.Select(t=>new[]{new AnimationCurve(),new AnimationCurve(),new AnimationCurve(),new AnimationCurve(),new AnimationCurve(),new AnimationCurve(),new AnimationCurve()}).ToArray();
            for(int frame=0;frame<=65;frame++)
            {
                float t=frame*.01f,raise=Smooth(0,.07f,t),draw=Smooth(.07f,.22f,t),recover=1-Smooth(.36f,.65f,t);
                float snap=t>=.25f?Mathf.Sin(Mathf.Clamp01((t-.25f)/.10f)*Mathf.PI):0;
                for(int i=0;i<nodes.Length;i++){nodes[i].localPosition=rest[i];nodes[i].localRotation=rotations[i];}
                torso.localRotation=rotations[0]*Quaternion.Euler((4*raise-7*snap)*recover,yaw.Evaluate(t),-2*snap);
                head.localRotation=rotations[1]*Quaternion.Euler(-2*raise*recover,-yaw.Evaluate(t)*.78f,0);
                left.localRotation=rotations[2]*Quaternion.Euler((-86*raise-5*snap)*recover,0,-8*raise*recover);
                right.localRotation=rotations[3]*Quaternion.Euler((-75*raise-5*draw)*recover,Mathf.Lerp(-25,-55,draw)*raise*recover,Mathf.Lerp(15,28,draw)*raise*recover);
                var anchor=head.TransformPoint(new Vector3(.08f,-.06f,.045f));var forward=instance.transform.forward;var bowTarget=anchor+forward*(.20f+.012f*snap);
                var leftGoal=Vector3.Lerp(leftRest,bowTarget,raise*recover);
                left.localPosition+=left.parent.InverseTransformVector(leftGoal-left.TransformPoint(ArcheryBowVisual.Grip));
                var rightTarget=t<.25f?bowTarget-forward*Mathf.Lerp(.055f,.20f,draw):anchor-forward*(.055f*snap)+instance.transform.right*(.025f*snap);
                var rightGoal=Vector3.Lerp(rightRest,rightTarget,raise*recover);
                right.localPosition+=right.parent.InverseTransformVector(rightGoal-right.TransformPoint(ArcheryBowVisual.Grip));
                for(int i=0;i<nodes.Length;i++)
                {
                    var p=nodes[i].localPosition;var q=nodes[i].localRotation;float[] values={p.x,p.y,p.z,q.x,q.y,q.z,q.w};for(int a=0;a<7;a++)curves[i][a].AddKey(t,values[a]);
                }
            }
            for(int i=0;i<nodes.Length;i++)
            {
                string path=AnimationUtility.CalculateTransformPath(nodes[i],instance.transform);
                foreach(var binding in AnimationUtility.GetCurveBindings(clip).Where(b=>b.path==path&&(b.propertyName.Contains("Rotation")||b.propertyName.Contains("Euler")||b.propertyName.Contains("Position"))))AnimationUtility.SetEditorCurve(clip,binding,null);
                for(int a=0;a<7;a++){var curve=curves[i][a];for(int k=0;k<curve.length;k++){AnimationUtility.SetKeyLeftTangentMode(curve,k,AnimationUtility.TangentMode.Linear);AnimationUtility.SetKeyRightTangentMode(curve,k,AnimationUtility.TangentMode.Linear);}clip.SetCurve(path,typeof(Transform),(a<3?"localPosition.":"localRotation.")+"xyzw"[a<3?a:a-3],curve);}
            }
            clip.EnsureQuaternionContinuity();return clip;
        }
    }
}


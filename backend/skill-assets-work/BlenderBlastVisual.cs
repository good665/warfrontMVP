using UnityEngine;
namespace Warfront
{
    // Blender-authored geometry; visual expansion never applies damage or moves actors.
    public sealed class BlenderBlastVisual : MonoBehaviour
    {
        private Renderer[] renderers;
        private Transform wave,core,sparks;
        private MaterialPropertyBlock block;
        private Vector3 waveScale,coreScale,sparksScale;
        private void Awake()
        {
            renderers=GetComponentsInChildren<Renderer>(true);block=new MaterialPropertyBlock();
            foreach(var child in GetComponentsInChildren<Transform>(true))
            {if(child.name=="Shockwave")wave=child;else if(child.name=="Core")core=child;else if(child.name=="Sparks")sparks=child;}
            if(wave!=null)waveScale=wave.localScale;if(core!=null)coreScale=core.localScale;if(sparks!=null)sparksScale=sparks.localScale;
        }
        public void Show(float radius,float progress,bool friendly)
        {
            if(renderers==null)Awake();
            float t=Mathf.Clamp01(progress);transform.localScale=Vector3.one*Mathf.Max(.01f,radius);
            if(wave!=null)wave.localScale=waveScale*Mathf.Lerp(.25f,1,t);
            if(core!=null)core.localScale=coreScale*(.25f+.7f*Mathf.Sin(t*Mathf.PI));
            if(sparks!=null)sparks.localScale=sparksScale*Mathf.Lerp(.3f,1,t);
            foreach(var renderer in renderers)
            {
                var tint=renderer.transform==core?new Color(1,.82f,.20f):friendly?new Color(1,.58f,.10f):new Color(1,.27f,.06f);
                tint.a=(1-t)*.9f;block.Clear();block.SetColor("_BaseColor",tint);renderer.SetPropertyBlock(block);
            }
        }
    }
}

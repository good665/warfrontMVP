using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
namespace Warfront
{
    // A missing snapshot freezes the last known pose; it never predicts hidden movement.
    [DefaultExecutionOrder(350)]
    public sealed class FogActorVisibility : MonoBehaviour
    {
        private const float Grace=.12f,FadeOut=.20f,FadeIn=.15f,Retention=.60f;
        private static readonly int BaseColor=Shader.PropertyToID("_BaseColor");
        private sealed class Surface
        {
            public Renderer renderer;
            public Material[] originals,transparent;
            public ShadowCastingMode shadows;
            public bool faded;
        }
        private readonly List<Surface> surfaces=new List<Surface>();
        private MaterialPropertyBlock block;
        private bool visible=true,cached;
        private float changed,from;
        public float Alpha {get;private set;}=1;
        public bool IsHidden=>!visible;
        private void Awake(){changed=Time.unscaledTime;from=0;Alpha=0;}
        public void Show(float now)
        {
            if(visible)return;
            from=Opacity(now);changed=now;visible=true;
        }
        public void Hide(float now)
        {
            if(!visible)return;
            from=Opacity(now);changed=now;visible=false;
        }
        public bool Keep(float now)=>!visible&&now-changed<Retention;
        private float Opacity(float now)=>visible?Mathf.Lerp(from,1,Mathf.SmoothStep(0,1,(now-changed)/FadeIn)):
            from*(1-Mathf.SmoothStep(0,1,(now-changed-Grace)/FadeOut));
        private void Cache()
        {
            if(block==null)block=new MaterialPropertyBlock();
            if(cached)return;cached=true;
            foreach(var renderer in GetComponentsInChildren<Renderer>(true))
            {
                var originals=renderer.sharedMaterials;
                var copies=new Material[originals.Length];
                for(int i=0;i<copies.Length;i++)
                {
                    if(originals[i]==null)continue;
                    var material=new Material(originals[i]){name=originals[i].name+" (fog transition)"};
                    material.SetOverrideTag("RenderType","Transparent");
                    if(material.HasProperty("_Surface"))material.SetFloat("_Surface",1);
                    if(material.HasProperty("_Blend"))material.SetFloat("_Blend",0);
                    if(material.HasProperty("_SrcBlend"))material.SetFloat("_SrcBlend",(float)BlendMode.SrcAlpha);
                    if(material.HasProperty("_DstBlend"))material.SetFloat("_DstBlend",(float)BlendMode.OneMinusSrcAlpha);
                    if(material.HasProperty("_ZWrite"))material.SetFloat("_ZWrite",0);
                    material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
                    material.renderQueue=(int)RenderQueue.Transparent;copies[i]=material;
                }
                surfaces.Add(new Surface{renderer=renderer,originals=originals,transparent=copies,shadows=renderer.shadowCastingMode});
            }
        }
        public void Sample(float now)
        {
            Cache();Alpha=Opacity(now);bool fade=Alpha<.999f;
            foreach(var surface in surfaces)
            {
                var renderer=surface.renderer;if(renderer==null)continue;
                if(surface.faded!=fade){renderer.sharedMaterials=fade?surface.transparent:surface.originals;surface.faded=fade;}
                renderer.shadowCastingMode=fade?ShadowCastingMode.Off:surface.shadows;
                renderer.GetPropertyBlock(block);
                Color tint=block.HasColor(BaseColor)?block.GetColor(BaseColor):
                    renderer.sharedMaterial!=null&&renderer.sharedMaterial.HasProperty(BaseColor)?renderer.sharedMaterial.GetColor(BaseColor):Color.white;
                tint.a=Alpha;block.SetColor(BaseColor,tint);renderer.SetPropertyBlock(block);block.Clear();
            }
        }
        private void LateUpdate(){Sample(Time.unscaledTime);}
        private void OnDestroy()
        {
            foreach(var surface in surfaces)
            {
                if(surface.renderer!=null&&surface.faded)surface.renderer.sharedMaterials=surface.originals;
                foreach(var material in surface.transparent)if(material!=null){if(Application.isPlaying)Destroy(material);else DestroyImmediate(material);}
            }
        }
    }
}

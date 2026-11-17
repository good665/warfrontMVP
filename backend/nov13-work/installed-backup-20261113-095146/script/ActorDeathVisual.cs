using UnityEngine;
using UnityEngine.Rendering;
namespace Warfront
{
    // Pure presentation: never changes the server position, HP, or respawn clock.
    [DefaultExecutionOrder(500)]
    public sealed class ActorDeathVisual : MonoBehaviour
    {
        public const float FallDuration=.65f, FadeDelay=.45f, Duration=1.25f;
        public bool IsDead {get;private set;}
        public float StartedAt {get;private set;}
        private Vector3 standingPosition;
        private Quaternion standingRotation;
        private Renderer[] skins;
        private Material[][] originals, fading;
        private bool[] visible;
        private Animation animationPlayer;
        private bool animationEnabled;
        private HeroHitReaction reaction;
        public void SetAlive(bool living)
        {
            if(living){if(IsDead)Restore();return;}
            if(IsDead)return;
            reaction=GetComponent<HeroHitReaction>();if(reaction!=null){reaction.Clear();reaction.enabled=false;}
            standingPosition=transform.localPosition;standingRotation=transform.localRotation;
            animationPlayer=GetComponent<Animation>();
            if(animationPlayer!=null){animationEnabled=animationPlayer.enabled;animationPlayer.Stop();animationPlayer.enabled=false;}
            skins=GetComponentsInChildren<Renderer>(true);originals=new Material[skins.Length][];fading=new Material[skins.Length][];visible=new bool[skins.Length];
            for(int i=0;i<skins.Length;i++){
                visible[i]=skins[i].enabled;originals[i]=skins[i].sharedMaterials;fading[i]=new Material[originals[i].Length];
                for(int j=0;j<originals[i].Length;j++){
                    var source=originals[i][j];if(source==null)continue;
                    var material=new Material(source){name=source.name+" Death fade",hideFlags=HideFlags.HideAndDontSave};
                    material.SetFloat("_Surface",1);material.SetFloat("_Blend",0);material.SetFloat("_SrcBlend",(float)BlendMode.SrcAlpha);material.SetFloat("_DstBlend",(float)BlendMode.OneMinusSrcAlpha);
                    material.SetFloat("_ZWrite",0);material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
                    material.SetOverrideTag("RenderType","Transparent");material.renderQueue=(int)RenderQueue.Transparent;fading[i][j]=material;
                }
                skins[i].sharedMaterials=fading[i];
            }
            StartedAt=Time.unscaledTime;IsDead=true;Sample(StartedAt);
        }
        public void Sample(float now)
        {
            if(!IsDead)return;
            float age=Mathf.Max(0,now-StartedAt),fall=Mathf.SmoothStep(0,1,Mathf.Clamp01(age/FallDuration));
            float alpha=1-Mathf.SmoothStep(0,1,Mathf.Clamp01((age-FadeDelay)/(Duration-FadeDelay)));
            transform.localRotation=standingRotation*Quaternion.Euler(0,0,-88*fall);
            transform.localPosition=standingPosition+Vector3.down*(.08f*fall);
            for(int i=0;i<skins.Length;i++){
                if(skins[i]==null)continue;skins[i].enabled=visible[i]&&alpha>0;
                var block=new MaterialPropertyBlock();skins[i].GetPropertyBlock(block);
                Color tint=block.HasColor("_BaseColor")?block.GetColor("_BaseColor"):Color.white;tint.a=alpha;block.SetColor("_BaseColor",tint);block.SetColor("_Color",tint);skins[i].SetPropertyBlock(block);
                foreach(var material in fading[i])if(material!=null){
                    if(material.HasProperty("_BaseColor")){var color=material.GetColor("_BaseColor");color.a=alpha;material.SetColor("_BaseColor",color);}
                    if(material.HasProperty("_Color")){var color=material.GetColor("_Color");color.a=alpha;material.SetColor("_Color",color);}
                }
            }
        }
        private void LateUpdate(){Sample(Time.unscaledTime);}
        private void Restore()
        {
            IsDead=false;transform.localPosition=standingPosition;transform.localRotation=standingRotation;
            for(int i=0;i<skins.Length;i++)if(skins[i]!=null){skins[i].sharedMaterials=originals[i];skins[i].enabled=visible[i];skins[i].SetPropertyBlock(null);}
            DisposeFadeMaterials();
            if(animationPlayer!=null){animationPlayer.enabled=animationEnabled;if(animationEnabled&&animationPlayer.GetClip("Idle")!=null)animationPlayer.Play("Idle");}
            if(reaction!=null)reaction.enabled=true;
        }
        private void DisposeFadeMaterials(){if(fading==null)return;foreach(var group in fading)if(group!=null)foreach(var material in group)if(material!=null){if(Application.isPlaying)Destroy(material);else DestroyImmediate(material);}fading=null;}
        private void OnDestroy(){DisposeFadeMaterials();}
    }
}

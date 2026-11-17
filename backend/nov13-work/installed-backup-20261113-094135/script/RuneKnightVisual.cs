using UnityEngine;
namespace Warfront
{
    // Low-poly armor ornaments follow the imported rig; no new physics or root motion.
    public sealed class RuneKnightVisual : MonoBehaviour
    {
        private Material metal,rune;
        private GameObject helmet;
        private bool built;
        public void Configure(bool helmetEquipped,Color accent)
        {
            if(!built)Build();if(rune!=null){rune.SetColor("_BaseColor",accent);if(rune.HasProperty("_EmissionColor"))rune.SetColor("_EmissionColor",accent*.65f);}
            if(helmet!=null)helmet.SetActive(helmetEquipped);
        }
        private void Build()
        {
            built=true;var source=Resources.Load<Material>("MiniDungeon/Materials/Colormap");if(source==null)return;
            metal=new Material(source){name="Obsidian rune steel"};metal.SetTexture("_BaseMap",null);metal.SetColor("_BaseColor",new Color(.19f,.17f,.24f));
            if(metal.HasProperty("_Metallic"))metal.SetFloat("_Metallic",.55f);if(metal.HasProperty("_Smoothness"))metal.SetFloat("_Smoothness",.25f);
            rune=new Material(metal){name="Amethyst rune inlay"};rune.EnableKeyword("_EMISSION");
            var torso=transform.Find("root/torso");var head=transform.Find("root/torso/head");
            if(torso!=null){
                Part("Chest rune horizontal",torso,new Vector3(0,.085f,.065f),new Vector3(.10f,.015f,.012f),rune);
                Part("Chest rune vertical",torso,new Vector3(0,.085f,.068f),new Vector3(.015f,.085f,.012f),rune);
            }
            foreach(string side in new[]{"left","right"}){
                var arm=transform.Find("root/torso/arm-"+side);if(arm==null)continue;
                Part("Faceted pauldron",arm,new Vector3(0,.01f,0),new Vector3(.105f,.065f,.105f),metal);
                Part("Shoulder rune",arm,new Vector3(0,.045f,0),new Vector3(.055f,.012f,.06f),rune);
            }
            if(head!=null){
                helmet=new GameObject("Equipped rune helmet");helmet.transform.SetParent(head,false);
                Part("Helmet crown",helmet.transform,new Vector3(0,.045f,0),new Vector3(.16f,.12f,.145f),metal);
                Part("Rune visor",helmet.transform,new Vector3(0,.035f,.076f),new Vector3(.12f,.015f,.008f),rune);
                Part("Helmet ridge",helmet.transform,new Vector3(0,.11f,-.005f),new Vector3(.024f,.035f,.13f),metal);
            }
            RetroFantasyScene.SetLayer(gameObject);
        }
        private static void Part(string name,Transform parent,Vector3 position,Vector3 scale,Material material)
        {
            var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=name;go.transform.SetParent(parent,false);go.transform.localPosition=position;go.transform.localScale=scale;
            var collider=go.GetComponent<Collider>();if(collider!=null){collider.enabled=false;if(Application.isPlaying)Destroy(collider);else DestroyImmediate(collider);}
            go.GetComponent<Renderer>().sharedMaterial=material;
        }
        private void OnDestroy(){foreach(var material in new[]{metal,rune})if(material!=null){if(Application.isPlaying)Destroy(material);else DestroyImmediate(material);}}
    }
}

using UnityEngine;
namespace Warfront
{
    // Low-poly armor ornaments follow the imported rig; no new physics or root motion.
    public sealed class RuneKnightVisual : MonoBehaviour
    {
        private Material metal,rune;
        private Texture2D steelPalette;
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
            steelPalette=new Texture2D(8,8,TextureFormat.RGBA32,false){name="Obsidian pixel steel",filterMode=FilterMode.Point,hideFlags=HideFlags.HideAndDontSave};
            var pixels=new Color[64];for(int i=0;i<64;i++){float value=((i*17)%7)*.008f;pixels[i]=new Color(.20f+value,.17f+value,.25f+value);}steelPalette.SetPixels(pixels);steelPalette.Apply(false,true);
            metal=new Material(source){name="Obsidian rune steel"};metal.SetTexture("_BaseMap",steelPalette);metal.SetColor("_BaseColor",Color.white);
            if(metal.HasProperty("_Metallic"))metal.SetFloat("_Metallic",.55f);if(metal.HasProperty("_Smoothness"))metal.SetFloat("_Smoothness",.25f);
            rune=new Material(metal){name="Amethyst rune inlay"};rune.SetTexture("_BaseMap",null);rune.EnableKeyword("_EMISSION");
            foreach(var skin in GetComponentsInChildren<SkinnedMeshRenderer>())if(skin.name.StartsWith("body"))skin.sharedMaterial=metal;
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
                Vector3 center=new Vector3(0,.07f,0),size=new Vector3(.28f,.28f,.25f);
                foreach(var skin in GetComponentsInChildren<SkinnedMeshRenderer>())if(skin.name.StartsWith("head")){
                    // Imported renderer bounds cover the entire animated skeleton.
                    // Fit the helmet to the actual deformed head vertices instead.
                    var baked=new Mesh();skin.BakeMesh(baked);var points=baked.vertices;
                    if(points.Length>0){var bounds=new Bounds(head.InverseTransformPoint(skin.transform.TransformPoint(points[0])),Vector3.zero);
                        foreach(var point in points)bounds.Encapsulate(head.InverseTransformPoint(skin.transform.TransformPoint(point)));
                        center=bounds.center;size=bounds.size*1.04f;
                    }
                    if(Application.isPlaying)Destroy(baked);else DestroyImmediate(baked);break;
                }
                Part("Helmet crown",helmet.transform,center,size,metal);
                Part("Rune visor",helmet.transform,center+new Vector3(0,size.y*.04f,size.z*.505f),new Vector3(size.x*.80f,size.y*.10f,.008f),rune);
                Part("Helmet ridge",helmet.transform,center+new Vector3(0,size.y*.55f,0),new Vector3(size.x*.12f,size.y*.18f,size.z*.9f),metal);
            }
            RetroFantasyScene.SetLayer(gameObject);
        }
        private static void Part(string name,Transform parent,Vector3 position,Vector3 scale,Material material)
        {
            var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=name;go.transform.SetParent(parent,false);go.transform.localPosition=position;go.transform.localScale=scale;
            var collider=go.GetComponent<Collider>();if(collider!=null){collider.enabled=false;if(Application.isPlaying)Destroy(collider);else DestroyImmediate(collider);}
            go.GetComponent<Renderer>().sharedMaterial=material;
        }
        private void OnDestroy(){foreach(var material in new[]{metal,rune})if(material!=null){if(Application.isPlaying)Destroy(material);else DestroyImmediate(material);}if(steelPalette!=null){if(Application.isPlaying)Destroy(steelPalette);else DestroyImmediate(steelPalette);}}
    }
}

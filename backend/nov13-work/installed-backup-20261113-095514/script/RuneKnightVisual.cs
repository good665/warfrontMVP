using UnityEngine;
namespace Warfront
{
    // Low-poly armor ornaments follow the imported rig; no new physics or root motion.
    [DefaultExecutionOrder(0)]
    public sealed class RuneKnightVisual : MonoBehaviour
    {
        private Material metal,rune;
        private Texture2D steelPalette;
        private GameObject helmet;
        private bool built;
        private Transform headBone;
        private Vector3 headScale;
        private SkinnedMeshRenderer headSkin;
        private Material[] headMaterials;
        private bool? displayedHelmet;
        private readonly System.Collections.Generic.List<Mesh> armorMeshes=new System.Collections.Generic.List<Mesh>();
        public void Configure(bool helmetEquipped,Color accent)
        {
            if(!built)Build();if(rune!=null){rune.SetColor("_BaseColor",accent);if(rune.HasProperty("_EmissionColor"))rune.SetColor("_EmissionColor",accent*.65f);}
            var death=GetComponent<ActorDeathVisual>();
            if((death==null||!death.IsDead)&&displayedHelmet!=helmetEquipped){
                if(helmet!=null)helmet.SetActive(helmetEquipped);
                if(headSkin!=null)headSkin.sharedMaterials=helmetEquipped?new[]{metal}:headMaterials;
                displayedHelmet=helmetEquipped;
            }
            if(headBone!=null)headBone.localScale=headScale*.72f;
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
                headBone=head;headScale=head.localScale;
                helmet=new GameObject("Equipped rune helmet");helmet.transform.SetParent(head,false);
                foreach(var skin in GetComponentsInChildren<SkinnedMeshRenderer>())if(skin.name.StartsWith("head")){
                    headSkin=skin;headMaterials=skin.sharedMaterials;break;
                }
                // Use the imported weighted head mesh as the fitted steel shell.
                // It follows every animation exactly without a second bounding box.
                Part("Rune visor",helmet.transform,new Vector3(0,.055f,.125f),new Vector3(.16f,.018f,.008f),rune);
            }
            RetroFantasyScene.SetLayer(gameObject);
        }
        private void Part(string name,Transform parent,Vector3 position,Vector3 scale,Material material)
        {
            var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=name;go.transform.SetParent(parent,false);go.transform.localPosition=position;go.transform.localScale=scale;
            if(name=="Helmet crown"||name=="Faceted pauldron"){
                var mesh=new Mesh{name="Beveled rune armor"};var vertices=new Vector3[26];
                var outline=new[]{new Vector2(-.35f,-.5f),new Vector2(.35f,-.5f),new Vector2(.5f,-.35f),new Vector2(.5f,.35f),new Vector2(.35f,.5f),new Vector2(-.35f,.5f),new Vector2(-.5f,.35f),new Vector2(-.5f,-.35f)};
                for(int ring=0;ring<3;ring++)for(int i=0;i<8;i++){float inset=ring==2?.85f:1;vertices[ring*8+i]=new Vector3(outline[i].x*inset,ring==0?-.5f:ring==1?.35f:.5f,outline[i].y*inset);}
                vertices[24]=Vector3.down*.5f;vertices[25]=Vector3.up*.5f;
                var triangles=new System.Collections.Generic.List<int>();
                for(int i=0;i<8;i++){int next=(i+1)%8;for(int ring=0;ring<2;ring++){int a=ring*8+i,b=ring*8+next;triangles.AddRange(new[]{a,a+8,b,b,a+8,b+8});}triangles.AddRange(new[]{24,i,next,25,16+next,16+i});}
                mesh.vertices=vertices;mesh.triangles=triangles.ToArray();mesh.RecalculateNormals();mesh.RecalculateBounds();go.GetComponent<MeshFilter>().sharedMesh=mesh;armorMeshes.Add(mesh);
            }
            var collider=go.GetComponent<Collider>();if(collider!=null){collider.enabled=false;if(Application.isPlaying)Destroy(collider);else DestroyImmediate(collider);}
            go.GetComponent<Renderer>().sharedMaterial=material;
        }
        private void LateUpdate(){if(headBone!=null)headBone.localScale=headScale*.72f;}
        private void OnDestroy(){foreach(var mesh in armorMeshes)if(mesh!=null){if(Application.isPlaying)Destroy(mesh);else DestroyImmediate(mesh);}foreach(var material in new[]{metal,rune})if(material!=null){if(Application.isPlaying)Destroy(material);else DestroyImmediate(material);}if(steelPalette!=null){if(Application.isPlaying)Destroy(steelPalette);else DestroyImmediate(steelPalette);}}
    }
}

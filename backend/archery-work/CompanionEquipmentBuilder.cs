using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
namespace Warfront.Assets
{
    public static class CompanionEquipmentBuilder
    {
        const string Root="Assets/Resources/SquadEquipment";
        static Material Material(string name,Color color)
        {
            var path=Root+"/"+name+".mat";var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(m==null){m=new Material(Shader.Find("Universal Render Pipeline/Lit"));AssetDatabase.CreateAsset(m,path);}
            m.color=color;m.SetFloat("_Smoothness",.1f);EditorUtility.SetDirty(m);return m;
        }
        static GameObject Cube(string name,Transform parent,Vector3 position,Vector3 scale,Material material,Quaternion rotation)
        {
            var p=GameObject.CreatePrimitive(PrimitiveType.Cube);p.name=name;UnityEngine.Object.DestroyImmediate(p.GetComponent<Collider>());p.transform.SetParent(parent,false);p.transform.localPosition=position;p.transform.localScale=scale;p.transform.localRotation=rotation;p.GetComponent<Renderer>().sharedMaterial=material;return p;
        }
        [MenuItem("Warfront/Squad/Build Companion Equipment")]
        public static void Build()
        {
            Directory.CreateDirectory(Root);AssetDatabase.Refresh();
            var wood=Material("BowWood",new Color(.40f,.20f,.08f));var stringMat=Material("BowString",new Color(.85f,.79f,.58f));var steel=Material("ArrowSteel",new Color(.65f,.73f,.78f));var feather=Material("ArrowFeather",new Color(.92f,.80f,.45f));
            var bow=new GameObject("Wooden Bow");
            try
            {
                var points=new[]{new Vector3(0,-.24f,-.055f),new Vector3(0,-.16f,.02f),new Vector3(0,0,.065f),new Vector3(0,.16f,.02f),new Vector3(0,.24f,-.055f)};
                for(int i=0;i<points.Length-1;i++){var d=points[i+1]-points[i];Cube("Curved wood limb "+i,bow.transform,(points[i]+points[i+1])*.5f,new Vector3(.026f,.026f,d.magnitude),wood,Quaternion.LookRotation(d));}
                Cube("Leather grip",bow.transform,new Vector3(0,0,.065f),new Vector3(.035f,.09f,.035f),wood,Quaternion.identity);
                var line=new GameObject("Bowstring").AddComponent<LineRenderer>();line.transform.SetParent(bow.transform,false);line.sharedMaterial=stringMat;line.useWorldSpace=false;line.positionCount=3;line.widthMultiplier=.006f;line.SetPositions(new[]{points[0],new Vector3(0,0,-.055f),points[4]});
                PrefabUtility.SaveAsPrefabAsset(bow,Root+"/Bow.prefab");
            }
            finally{UnityEngine.Object.DestroyImmediate(bow);}
            var arrow=new GameObject("Arrow");
            try
            {
                Cube("Wooden shaft",arrow.transform,new Vector3(0,0,-.02f),new Vector3(.014f,.014f,.60f),wood,Quaternion.identity);
                Cube("Steel point",arrow.transform,new Vector3(0,0,.30f),new Vector3(.035f,.035f,.10f),steel,Quaternion.Euler(0,0,45));
                Cube("Feather horizontal",arrow.transform,new Vector3(0,0,-.25f),new Vector3(.10f,.009f,.11f),feather,Quaternion.identity);
                Cube("Feather vertical",arrow.transform,new Vector3(0,0,-.25f),new Vector3(.009f,.10f,.11f),feather,Quaternion.identity);
                PrefabUtility.SaveAsPrefabAsset(arrow,Root+"/Arrow.prefab");
            }
            finally{UnityEngine.Object.DestroyImmediate(arrow);}
            var human=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Resources/MiniDungeon/Characters/Human.prefab");var instance=UnityEngine.Object.Instantiate(human);
            try
            {
                var clip=BowMotionClipBuilder.Build(instance);string path=Root+"/BowDraw.anim";var saved=AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
                if(saved==null)AssetDatabase.CreateAsset(clip,path);else{EditorUtility.CopySerialized(clip,saved);UnityEngine.Object.DestroyImmediate(clip);EditorUtility.SetDirty(saved);}
                AssetDatabase.SaveAssets();Debug.Log("COMPANION_EQUIPMENT_BUILD PASS: original rig Bow clip and native bow/arrow prefabs");
            }
            finally{UnityEngine.Object.DestroyImmediate(instance);}
        }
    }
}

using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
namespace Warfront.Assets
{
    public static class BlenderSkillImport
    {
        const string Root="Assets/Resources/SkillVisuals";
        [Serializable] class TracksFile { public ClipData[] clips; }
        [Serializable] class ClipData { public string name;public float duration;public Track[] tracks; }
        [Serializable] class Track { public string path;public PoseKey[] keys; }
        [Serializable] class PoseKey { public float time;public float[] position,rotation; }
        static Material Material(string name,Shader shader,bool transparent)
        {
            var path=Root+"/"+name+".mat";var material=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(material==null){material=new Material(shader){name=name};AssetDatabase.CreateAsset(material,path);}
            material.shader=shader;
            if(transparent){material.SetFloat("_Surface",1);material.SetFloat("_Blend",0);material.SetInt("_SrcBlend",(int)BlendMode.SrcAlpha);material.SetInt("_DstBlend",(int)BlendMode.OneMinusSrcAlpha);material.SetInt("_ZWrite",0);material.SetInt("_Cull",0);material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");material.SetOverrideTag("RenderType","Transparent");material.renderQueue=3000;}
            EditorUtility.SetDirty(material);return material;
        }
        [MenuItem("Warfront/Squad/Import Blender Skill Visuals")]
        public static void Build()
        {
            AssetDatabase.Refresh();
            var texture=(TextureImporter)AssetImporter.GetAtPath(Root+"/Source/SkillPalette.png");texture.filterMode=FilterMode.Point;texture.mipmapEnabled=false;texture.textureCompression=TextureImporterCompression.Uncompressed;texture.SaveAndReimport();
            var metal=Material("BombMetal",Shader.Find("Universal Render Pipeline/Lit"),false);metal.mainTexture=AssetDatabase.LoadAssetAtPath<Texture2D>(Root+"/Source/SkillPalette.png");metal.SetFloat("_Smoothness",.25f);
            var blast=Material("BlastGlow",Shader.Find("Universal Render Pipeline/Unlit"),true);blast.color=new Color(1,.5f,.1f,.9f);
            var file=JsonUtility.FromJson<TracksFile>(File.ReadAllText(Root+"/Source/SkillActions.json"));
            var human=Resources.Load<GameObject>("MiniDungeon/Characters/Human");var instance=UnityEngine.Object.Instantiate(human);
            try
            {
                foreach(var data in file.clips)
                {
                    var clip=new AnimationClip{name=data.name,legacy=true,wrapMode=WrapMode.ClampForever,frameRate=100};
                    foreach(var track in data.tracks)
                    {
                        if(instance.transform.Find(track.path)==null)throw new Exception("Blender track misses original rig: "+track.path);
                        for(int axis=0;axis<7;axis++)
                        {
                            var curve=new AnimationCurve();foreach(var key in track.keys)curve.AddKey(key.time,axis<3?key.position[axis]:key.rotation[axis-3]);
                            for(int i=0;i<curve.length;i++){AnimationUtility.SetKeyLeftTangentMode(curve,i,AnimationUtility.TangentMode.Linear);AnimationUtility.SetKeyRightTangentMode(curve,i,AnimationUtility.TangentMode.Linear);}
                            clip.SetCurve(track.path,typeof(Transform),(axis<3?"localPosition.":"localRotation.")+"xyzw"[axis<3?axis:axis-3],curve);
                        }
                    }
                    clip.EnsureQuaternionContinuity();var path=Root+"/"+data.name+".anim";var saved=AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
                    if(saved==null)AssetDatabase.CreateAsset(clip,path);else{EditorUtility.CopySerialized(clip,saved);UnityEngine.Object.DestroyImmediate(clip);EditorUtility.SetDirty(saved);}
                }
            }
            finally{UnityEngine.Object.DestroyImmediate(instance);}
            foreach(var name in new[]{"Bomb","Blast"})
            {
                string path=Root+"/Source/"+name+".fbx";var importer=(ModelImporter)AssetImporter.GetAtPath(path);importer.importAnimation=false;importer.isReadable=true;importer.materialImportMode=ModelImporterMaterialImportMode.None;importer.SaveAndReimport();
                var model=new GameObject(name);
                UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path),model.transform,false);
                try
                {
                    foreach(var renderer in model.GetComponentsInChildren<Renderer>(true))renderer.sharedMaterial=name=="Bomb"?metal:blast;
                    if(name=="Blast")model.AddComponent<BlenderBlastVisual>();
                    PrefabUtility.SaveAsPrefabAsset(model,Root+"/"+name+".prefab");
                }
                finally{UnityEngine.Object.DestroyImmediate(model);}
            }
            AssetDatabase.SaveAssets();Debug.Log("BLENDER_SKILL_IMPORT PASS: original-rig Heavy/Throw/Dodge, Blender Bomb/Blast meshes and URP materials");
        }
    }
}

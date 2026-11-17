using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace Warfront.EditorTools
{
    // Native mesh variants leave imported originals and animation curves intact.
    public static class FootProportionAdjustment
    {
        const string Folder="Assets/Resources/FittedFeet";
        static string Temp(string name)=>Path.Combine(Path.GetTempPath(),name);
        [InitializeOnLoadMethod]
        static void AutoRun()
        {
            EditorApplication.update+=Poll;
        }
        static void Poll()
        {
            if(EditorApplication.isPlayingOrWillChangePlaymode||EditorApplication.isCompiling||!File.Exists(Temp("warfront-feet.request")))return;
            File.Delete(Temp("warfront-feet.request"));Run();
        }
        [MenuItem("Warfront/Characters/Fit Feet To Models")]
        public static void Run()
        {
            try
            {
                Directory.CreateDirectory(Folder);AssetDatabase.Refresh();
                string backup=File.ReadAllText(Temp("warfront-feet-backup.txt")).Trim();Directory.CreateDirectory(backup);
                var paths=new List<string>{"Assets/Resources/MiniDungeon/Characters/Human.prefab","Assets/Resources/MiniDungeon/Characters/Orc.prefab"};
                paths.AddRange(Directory.GetFiles("Assets/Resources/SidelineZodiac","Character.prefab",SearchOption.AllDirectories).Select(p=>p.Replace('\\','/')));
                var report=new List<string>();var previews=new List<GameObject>();
                foreach(string path in paths)
                {
                    string id=path.Contains("MiniDungeon")?Path.GetFileNameWithoutExtension(path):new DirectoryInfo(Path.GetDirectoryName(path)).Name;
                    var root=PrefabUtility.LoadPrefabContents(path);
                    bool preview=id=="Human"||id=="tiger"||id=="rabbit"||id=="ox";
                    if(preview)
                    {
                        var before=UnityEngine.Object.Instantiate(root);
                        string savedPrefab=Path.Combine(backup,id+"-Character.prefab");
                        if(File.Exists(savedPrefab))
                        {
                            var refs=System.Text.RegularExpressions.Regex.Matches(File.ReadAllText(savedPrefab),@"m_Mesh: \{fileID: (-?\d+), guid: ([a-f0-9]+), type: \d+\}");
                            var skins=before.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                            for(int i=0;i<Math.Min(refs.Count,skins.Length);i++)
                            {
                                long wanted=long.Parse(refs[i].Groups[1].Value);
                                foreach(var asset in AssetDatabase.LoadAllAssetsAtPath(AssetDatabase.GUIDToAssetPath(refs[i].Groups[2].Value)))
                                    if(asset is Mesh mesh&&AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh,out string guid,out long localId)&&localId==wanted){skins[i].sharedMesh=mesh;break;}
                            }
                        }
                        previews.Add(before);
                    }
                    try
                    {
                        int changed=0;
                        foreach(var skin in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                        {
                            var original=skin.sharedMesh;if(original==null||AssetDatabase.GetAssetPath(original).StartsWith(Folder))continue;
                            var vertices=original.vertices;var output=(Vector3[])vertices.Clone();var weights=original.boneWeights;var binds=original.bindposes;
                            if(weights.Length!=vertices.Length)continue;
                            for(int bone=0;bone<skin.bones.Length;bone++)
                            {
                                if(skin.bones[bone]==null||!skin.bones[bone].name.StartsWith("leg",StringComparison.OrdinalIgnoreCase))continue;
                                var points=new List<Vector3>();
                                for(int i=0;i<vertices.Length;i++)if(Weight(weights[i],bone)>.5f)points.Add(binds[bone].MultiplyPoint3x4(vertices[i]));
                                if(points.Count==0)continue;
                                float bottom=points.Min(v=>v.y),height=points.Max(v=>v.y)-bottom;if(height<.0001f)continue;
                                float ankle=bottom+height*.40f;
                                var feet=points.Where(v=>v.y<=ankle).ToArray();
                                float centerX=(feet.Min(v=>v.x)+feet.Max(v=>v.x))*.5f;
                                float centerZ=(feet.Min(v=>v.z)+feet.Max(v=>v.z))*.5f;
                                for(int i=0;i<vertices.Length;i++)
                                {
                                    float weight=Weight(weights[i],bone);if(weight<=0)continue;
                                    var local=binds[bone].MultiplyPoint3x4(vertices[i]);
                                    float fit=1-Mathf.SmoothStep(0,1,Mathf.InverseLerp(bottom+height*.16f,ankle,local.y));
                                    if(fit<=0)continue;
                                    var fitted=local;fitted.x=centerX+(local.x-centerX)*(1+.30f*fit);fitted.z=centerZ+(local.z-centerZ)*(1+.35f*fit);
                                    output[i]+=binds[bone].inverse.MultiplyVector(fitted-local)*weight;
                                }
                            }
                            int count=0;
                            for(int i=0;i<output.Length;i++)
                            {
                                if(!float.IsFinite(output[i].x)||!float.IsFinite(output[i].y)||!float.IsFinite(output[i].z))throw new Exception(id+": non-finite vertex");
                                if(Mathf.Abs(output[i].y-vertices[i].y)>.00001f)throw new Exception(id+": foot height changed");
                                if((output[i]-vertices[i]).sqrMagnitude>1e-12f)count++;
                            }
                            if(count==0)continue;
                            var mesh=UnityEngine.Object.Instantiate(original);mesh.name=original.name+" fitted feet";mesh.vertices=output;mesh.RecalculateNormals();mesh.RecalculateBounds();
                            if(mesh.vertexCount!=original.vertexCount||mesh.triangles.Length!=original.triangles.Length||mesh.bindposes.Length!=original.bindposes.Length)throw new Exception(id+": rig/topology changed");
                            string meshPath=Folder+"/"+id+"-"+skin.name+".asset";
                            var saved=AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
                            if(saved==null){AssetDatabase.CreateAsset(mesh,meshPath);saved=mesh;}else{EditorUtility.CopySerialized(mesh,saved);EditorUtility.SetDirty(saved);UnityEngine.Object.DestroyImmediate(mesh);}
                            skin.sharedMesh=saved;var bounds=skin.localBounds;bounds.Encapsulate(saved.bounds.min);bounds.Encapsulate(saved.bounds.max);skin.localBounds=bounds;changed+=count;
                        }
                        if(changed>0)
                        {
                            string copy=Path.Combine(backup,id+"-Character.prefab");if(!File.Exists(copy))File.Copy(path,copy);
                            PrefabUtility.SaveAsPrefabAsset(root,path);
                        }
                        // Sample real clips after fitting: the rig must still produce finite geometry.
                        var animation=root.GetComponent<Animation>();
                        if(animation!=null)foreach(AnimationState state in animation)foreach(float phase in new[]{0f,.28f,.65f})
                        {
                            state.clip.SampleAnimation(root,state.length*phase);
                            foreach(var skin in root.GetComponentsInChildren<SkinnedMeshRenderer>())
                            {
                                var baked=new Mesh();try{skin.BakeMesh(baked);foreach(var vertex in baked.vertices)if(!float.IsFinite(vertex.x)||!float.IsFinite(vertex.y)||!float.IsFinite(vertex.z))throw new Exception(id+": bad animated vertex");}finally{UnityEngine.Object.DestroyImmediate(baked);}
                            }
                        }
                        report.Add(id+": "+changed+" foot vertices fitted; height/topology/rig preserved; animation samples valid");
                        if(preview)previews.Add(UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path)));
                    }
                    finally{PrefabUtility.UnloadPrefabContents(root);}
                }
                AssetDatabase.SaveAssets();Render(previews);
                File.WriteAllLines(Temp("warfront-feet.result"),report);Debug.Log("FOOT FIT PASS: "+string.Join("; ",report));
            }
            catch(Exception error){File.WriteAllText(Temp("warfront-feet.result"),"FAIL: "+error);Debug.LogException(error);}
        }
        static float Weight(BoneWeight w,int bone)=>(w.boneIndex0==bone?w.weight0:0)+(w.boneIndex1==bone?w.weight1:0)+(w.boneIndex2==bone?w.weight2:0)+(w.boneIndex3==bone?w.weight3:0);
        static void Render(List<GameObject> previews)
        {
            var root=new GameObject("Feet comparison preview");var target=new RenderTexture(1600,900,24);var previous=RenderTexture.active;
            try
            {
                root.transform.position=new Vector3(20000,0,20000);
                for(int i=0;i<previews.Count;i++)
                {
                    var actor=previews[i];actor.transform.SetParent(root.transform,false);actor.transform.localPosition=new Vector3((i%4)*1.3f,0,-(i/4)*2f);actor.transform.localRotation=Quaternion.Euler(0,180,0);
                    var animation=actor.GetComponent<Animation>();if(animation!=null){animation.Stop();var idle=animation.GetClip("Idle");if(idle!=null)idle.SampleAnimation(actor,0);animation.enabled=false;}
                    foreach(var node in actor.GetComponentsInChildren<Transform>(true))node.gameObject.layer=31;
                    if(i<2)actor.transform.localScale=Vector3.one*2;
                    foreach(var skin in actor.GetComponentsInChildren<SkinnedMeshRenderer>())skin.forceMatrixRecalculationPerRender=true;
                }
                var cameraObject=new GameObject("Foot preview camera");cameraObject.transform.SetParent(root.transform,false);var camera=cameraObject.AddComponent<Camera>();camera.orthographic=true;camera.orthographicSize=2.3f;camera.aspect=1600f/900;camera.cullingMask=1<<31;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.17f,.18f,.23f);camera.targetTexture=target;
                camera.transform.localPosition=new Vector3(5,4,7);camera.transform.LookAt(root.transform.position+new Vector3(2,.35f,-.8f));
                var lightObject=new GameObject("Preview light");lightObject.transform.SetParent(root.transform,false);var light=lightObject.AddComponent<Light>();light.type=LightType.Directional;light.intensity=2;light.cullingMask=1<<31;light.transform.rotation=Quaternion.Euler(45,-30,0);
                var config=Resources.Load<RetroRenderConfig>("RetroFantasy/RenderConfig");if(config!=null)camera.GetUniversalAdditionalCameraData().SetRenderer(config.rendererIndex);
                var request=new UniversalRenderPipeline.SingleCameraRequest{destination=target};if(!RenderPipeline.SupportsRenderRequest(camera,request))throw new Exception("Preview render unavailable");RenderPipeline.SubmitRenderRequest(camera,request);
                RenderTexture.active=target;var image=new Texture2D(1600,900,TextureFormat.RGB24,false);try{image.ReadPixels(new Rect(0,0,1600,900),0,0);image.Apply();File.WriteAllBytes(Temp("warfront-feet-comparison.png"),image.EncodeToPNG());}finally{UnityEngine.Object.DestroyImmediate(image);}
            }
            finally{RenderTexture.active=previous;UnityEngine.Object.DestroyImmediate(root);target.Release();UnityEngine.Object.DestroyImmediate(target);}
        }
    }
}

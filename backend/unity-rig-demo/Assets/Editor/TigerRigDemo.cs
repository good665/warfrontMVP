using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using UnityEngine.UI;

namespace Warfront.EditorTools
{
    public sealed class TigerRigDemoImporter : AssetPostprocessor
    {
        void OnPreprocessModel()
        {
            if(!assetPath.Contains("/RigDemo/")||!assetPath.EndsWith(".fbx"))return;
            var importer=(ModelImporter)assetImporter;importer.animationType=ModelImporterAnimationType.Legacy;
            importer.importAnimation=true;importer.materialImportMode=ModelImporterMaterialImportMode.None;
            importer.animationCompression=ModelImporterAnimationCompression.Off;
        }
        void OnPreprocessTexture()
        {if(assetPath.Contains("/RigDemo/")){var importer=(TextureImporter)assetImporter;importer.filterMode=FilterMode.Point;importer.mipmapEnabled=false;}}
    }

    // An isolated animation study. No GameBootstrap/server/production prefab mutation.
    public sealed class TigerRigDemo : EditorWindow
    {
        const string Fbx="Assets/RigDemo/Tiger/TigerRigDemo.fbx";
        const int Width=640,Height=720,Fps=24,FrameCount=240;
        GameObject stage;GameObject[] models=new GameObject[2];Camera[] cameras=new Camera[2];RenderTexture[] targets=new RenderTexture[2];
        readonly Dictionary<string,AnimationClip> clips=new Dictionary<string,AnimationClip>();
        readonly List<UnityEngine.Object> owned=new List<UnityEngine.Object>();
        Mesh previewMesh;Vector3[][] cachedVertices,cachedNormals,cachedBones;Vector2[] cachedUV;int[] cachedIndices,cachedParents;string[] cachedNames;
        Transform[] sourceBones;
        Text[] phaseLabels=new Text[2],details=new Text[2];LineRenderer[] indicators=new LineRenderer[2];
        float started;bool paused,showRig;float frozen;int exportFrame=-1;string output;
        List<LineRenderer>[] rigLines={new List<LineRenderer>(),new List<LineRenderer>()};
        List<Transform>[] rigBones={new List<Transform>(),new List<Transform>()};
        static string Request=>Path.Combine(Path.GetTempPath(),"warfront-rig-demo-v8.request");
        [InitializeOnLoadMethod]static void Auto(){EditorApplication.update-=Poll;EditorApplication.update+=Poll;}
        static void Poll()
        {
            if(!File.Exists(Request)||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.isPlayingOrWillChangePlaymode)return;
            if(AssetDatabase.LoadAssetAtPath<GameObject>(Fbx)==null)return;
            AssetDatabase.ImportAsset("Assets/RigDemo/Tiger/TigerPreview.bytes",ImportAssetOptions.ForceSynchronousImport|ImportAssetOptions.ForceUpdate);
            string folder=File.ReadAllText(Request).Trim();File.Delete(Request);
            foreach(var previous in Resources.FindObjectsOfTypeAll<TigerRigDemo>())previous.Close();
            var window=GetWindow<TigerRigDemo>();window.titleContent=new GUIContent("Tiger Rig Demo · 시연");window.minSize=new Vector2(1280,770);window.Show();
            window.output=folder;Directory.CreateDirectory(folder);window.exportFrame=0;
        }
        [MenuItem("Warfront/Rig Demo/Compare Tiger Animations")]
        public static void Open(){var w=GetWindow<TigerRigDemo>();w.titleContent=new GUIContent("Tiger Rig Demo · 시연");w.minSize=new Vector2(1280,770);w.Show();}
        Material Mat(Color color)
        {var m=new Material(Shader.Find("Universal Render Pipeline/Lit"));m.color=color;m.SetFloat("_Smoothness",.05f);owned.Add(m);return m;}
        void Layer(GameObject node){foreach(var t in node.GetComponentsInChildren<Transform>(true))t.gameObject.layer=29;}
        Text Label(Transform parent,string text,Vector2 position,Vector2 size,int fontSize,Color color,Font font)
        {
            var node=new GameObject(text,typeof(RectTransform));node.transform.SetParent(parent,false);
            var r=node.GetComponent<RectTransform>();r.anchorMin=r.anchorMax=new Vector2(.5f,1);r.pivot=new Vector2(.5f,1);r.anchoredPosition=position;r.sizeDelta=size;
            var label=node.AddComponent<Text>();label.font=font;label.fontSize=fontSize;label.fontStyle=FontStyle.Bold;label.alignment=TextAnchor.MiddleCenter;
            label.text=text;label.color=color;label.horizontalOverflow=HorizontalWrapMode.Wrap;label.verticalOverflow=VerticalWrapMode.Overflow;node.layer=29;return label;
        }
        void OnEnable()
        {
            try{Build();started=(float)EditorApplication.timeSinceStartup;EditorApplication.update+=Tick;}
            catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-rig-demo.result"),"FAIL: "+e);}
        }
        void Build()
        {
            if(stage!=null)return;
            var old=Resources.Load<GameObject>("Zodiac/tiger/Character");var next=AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
            if(old==null||next==null)throw new Exception("Missing baseline or demo asset");
            foreach(var asset in AssetDatabase.LoadAllAssetsAtPath(Fbx))if(asset is AnimationClip clip&&!clip.name.StartsWith("__preview__"))
                foreach(string name in new[]{"Idle","Walk","QSkill","EUltimate"})if(clip.name.EndsWith(name,StringComparison.OrdinalIgnoreCase))clips[name]=clip;
            foreach(string name in new[]{"Idle","Walk","QSkill","EUltimate"})if(!clips.ContainsKey(name))throw new Exception("Missing imported clip "+name);
            LoadSourceCache();
            stage=new GameObject("Isolated tiger rigging study"){hideFlags=HideFlags.HideAndDontSave};stage.transform.position=new Vector3(500,0,500);
            var lightNode=new GameObject("Study key light");lightNode.transform.SetParent(stage.transform,false);lightNode.transform.localRotation=Quaternion.Euler(48,-35,0);
            var key=lightNode.AddComponent<Light>();key.type=LightType.Directional;key.intensity=1.7f;key.color=new Color(1,.92f,.75f);key.cullingMask=1<<29;key.shadows=LightShadows.Soft;
            var font=Font.CreateDynamicFontFromOSFont("Malgun Gothic",24);owned.Add(font);
            var palette=AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/RigDemo/Tiger/TigerPalette.png");
            var animal=Mat(Color.white);animal.mainTexture=palette;animal.SetFloat("_Cull",0);
            for(int i=0;i<2;i++)
            {
                var platform=new GameObject(i==0?"Current animation":"Improved preview");platform.transform.SetParent(stage.transform,false);platform.transform.localPosition=new Vector3(i*10,0,0);
                var floor=GameObject.CreatePrimitive(PrimitiveType.Cube);floor.transform.SetParent(platform.transform,false);floor.transform.localPosition=new Vector3(0,-.09f,0);floor.transform.localScale=new Vector3(6,.15f,6);floor.GetComponent<Renderer>().sharedMaterial=Mat(i==0?new Color(.19f,.24f,.20f):new Color(.17f,.26f,.22f));
                // Small repeating stones establish foot contact at the isometric game angle.
                for(int n=0;n<9;n++)
                {var tile=GameObject.CreatePrimitive(PrimitiveType.Cube);tile.transform.SetParent(platform.transform,false);tile.transform.localPosition=new Vector3((n%3-1)*.9f,-.008f,(n/3-1)*.9f);tile.transform.localScale=new Vector3(.88f,.018f,.88f);tile.GetComponent<Renderer>().sharedMaterial=floor.GetComponent<Renderer>().sharedMaterial;}
                var visualRoot=new GameObject("Scale normalization (outside animation bindings)");visualRoot.transform.SetParent(platform.transform,false);
                if(i==0)models[i]=UnityEngine.Object.Instantiate(old,visualRoot.transform);
                else
                {
                    models[i]=new GameObject("Blender weighted-source preview");models[i].transform.SetParent(visualRoot.transform,false);
                    previewMesh=new Mesh{name="23-bone source deformation cache"};owned.Add(previewMesh);previewMesh.vertices=cachedVertices[0];previewMesh.normals=cachedNormals[0];previewMesh.uv=cachedUV;previewMesh.triangles=cachedIndices;previewMesh.RecalculateBounds();
                    models[i].AddComponent<MeshFilter>().sharedMesh=previewMesh;models[i].AddComponent<MeshRenderer>().sharedMaterial=animal;
                    sourceBones=new Transform[cachedNames.Length];
                    for(int b=0;b<sourceBones.Length;b++){var node=new GameObject(cachedNames[b]);sourceBones[b]=node.transform;sourceBones[b].SetParent(cachedParents[b]<0?models[i].transform:sourceBones[cachedParents[b]],false);sourceBones[b].position=models[i].transform.TransformPoint(cachedBones[0][b]);}
                }
                models[i].name=i==0?"Current tiger (unchanged)":"Demo tiger (23 source bones)";
                if(i==1)foreach(var renderer in models[i].GetComponentsInChildren<Renderer>())renderer.sharedMaterial=animal;
                foreach(var animation in models[i].GetComponentsInChildren<Animation>())animation.enabled=false;
                foreach(var animator in models[i].GetComponentsInChildren<Animator>())animator.enabled=false;
                foreach(var bodySkin in models[i].GetComponentsInChildren<SkinnedMeshRenderer>())bodySkin.updateWhenOffscreen=true;
                var bounds=new Bounds(models[i].transform.position,Vector3.zero);bool first=true;
                foreach(var renderer in models[i].GetComponentsInChildren<Renderer>())
                {
                    var actual=renderer.bounds;
                    if(renderer is SkinnedMeshRenderer skinned)
                    {
                        var baked=new Mesh();skinned.BakeMesh(baked);actual=new Bounds(skinned.transform.TransformPoint(baked.bounds.center),Vector3.zero);
                        foreach(var vertex in baked.vertices)actual.Encapsulate(skinned.transform.TransformPoint(vertex));UnityEngine.Object.DestroyImmediate(baked);
                    }
                    if(first){bounds=actual;first=false;}else bounds.Encapsulate(actual);
                }
                float scale=1.35f/Mathf.Max(.1f,bounds.size.y);visualRoot.transform.localScale=Vector3.one*scale;
                // The model's feet stay on the same ground plane in both columns.
                visualRoot.transform.localPosition=new Vector3(platform.transform.position.x-bounds.center.x,platform.transform.position.y-bounds.min.y,platform.transform.position.z-bounds.center.z)*scale;
                var cameraNode=new GameObject("Warcraft-style isometric preview camera");cameraNode.transform.SetParent(platform.transform,false);
                cameras[i]=cameraNode.AddComponent<Camera>();var camera=cameras[i];camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.075f,.10f,.12f);camera.cullingMask=1<<29;camera.orthographic=true;camera.orthographicSize=1.8f;camera.nearClipPlane=.05f;camera.farClipPlane=100;
                camera.transform.localPosition=new Vector3(3.3f,6.8f,3.3f);camera.transform.LookAt(platform.transform.position+Vector3.up*.65f);camera.aspect=Width/(float)Height;
                var config=Resources.Load<RetroRenderConfig>("RetroFantasy/RenderConfig");if(config!=null)camera.GetUniversalAdditionalCameraData().SetRenderer(config.rendererIndex);
                targets[i]=new RenderTexture(Width,Height,24){antiAliasing=2};targets[i].Create();camera.targetTexture=targets[i];
                var canvasNode=new GameObject("Demo annotations");canvasNode.transform.SetParent(platform.transform,false);var canvas=canvasNode.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;
                var scaler=canvasNode.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;scaler.referenceResolution=new Vector2(Width,Height);
                Label(canvas.transform,i==0?"현재 모델 · 현재 클립":"개선안 · 시연 전용",new Vector2(0,-18),new Vector2(600,48),30,i==0?new Color(.8f,.83f,.87f):new Color(1,.77f,.35f),font);
                Label(canvas.transform,i==0?"8개 관절 · 한 덩어리 다리 회전":"23개 관절 · 팔꿈치 / 무릎 / 발 지지",new Vector2(0,-70),new Vector2(610,35),19,Color.white,font);
                phaseLabels[i]=Label(canvas.transform,"",new Vector2(0,-560),new Vector2(610,42),27,Color.white,font);
                details[i]=Label(canvas.transform,"",new Vector2(0,-610),new Vector2(600,65),19,new Color(.8f,.86f,.9f),font);
                Label(canvas.transform,"워크래프트 3식 시점 · 동작을 천천히 비교",new Vector2(0,-685),new Vector2(620,25),15,new Color(.7f,.76f,.8f),font);
                var ringNode=new GameObject("Skill timing cue");ringNode.transform.SetParent(platform.transform,false);indicators[i]=ringNode.AddComponent<LineRenderer>();indicators[i].useWorldSpace=false;indicators[i].loop=true;indicators[i].positionCount=48;indicators[i].widthMultiplier=.035f;
                var fx=new Material(Shader.Find("Universal Render Pipeline/Unlit"));fx.color=i==0?new Color(.5f,.65f,.8f):new Color(1,.65f,.16f);owned.Add(fx);indicators[i].sharedMaterial=fx;
                var skin=models[i].GetComponentInChildren<SkinnedMeshRenderer>();
                foreach(var bone in i==0?skin.bones:sourceBones)if(bone!=null&&bone.parent!=null)
                {
                    var lineNode=new GameObject("Rig line "+bone.name);lineNode.transform.SetParent(platform.transform,false);var line=lineNode.AddComponent<LineRenderer>();line.sharedMaterial=fx;line.widthMultiplier=.013f;line.positionCount=2;line.useWorldSpace=true;rigLines[i].Add(line);rigBones[i].Add(bone);
                }
                Layer(platform);
            }
            Validate();
        }
        void Validate()
        {
            if(sourceBones.Length!=23)throw new Exception("Expected articulated 23-bone source rig");
            bool changed=false;for(int n=0;n<cachedVertices[0].Length;n++)if((cachedVertices[0][n]-cachedVertices[108][n]).sqrMagnitude>.00001f){changed=true;break;}
            if(!changed)throw new Exception("Q skill does not deform source mesh");
        }
        void LoadSourceCache()
        {
            string path=Path.Combine(Application.dataPath,"RigDemo/Tiger/TigerPreview.bytes");
            using(var stream=new MemoryStream(File.ReadAllBytes(path)))using(var reader=new BinaryReader(stream))
            {
                if(System.Text.Encoding.ASCII.GetString(reader.ReadBytes(4))!="TRD1")throw new Exception("Invalid source cache");
                int v=reader.ReadInt32(),indices=reader.ReadInt32(),bones=reader.ReadInt32(),frames=reader.ReadInt32();reader.ReadSingle();
                cachedUV=new Vector2[v];for(int n=0;n<v;n++)cachedUV[n]=new Vector2(reader.ReadSingle(),reader.ReadSingle());
                cachedIndices=new int[indices];for(int n=0;n<indices;n++)cachedIndices[n]=reader.ReadInt32();
                cachedNames=new string[bones];cachedParents=new int[bones];for(int n=0;n<bones;n++){cachedNames[n]=System.Text.Encoding.UTF8.GetString(reader.ReadBytes(64)).TrimEnd('\0');cachedParents[n]=reader.ReadInt32();}
                cachedVertices=new Vector3[frames][];cachedNormals=new Vector3[frames][];cachedBones=new Vector3[frames][];
                for(int f=0;f<frames;f++)
                {
                    cachedVertices[f]=new Vector3[v];cachedNormals[f]=new Vector3[v];cachedBones[f]=new Vector3[bones];
                    for(int n=0;n<v;n++)cachedVertices[f][n]=new Vector3(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());
                    for(int n=0;n<v;n++)cachedNormals[f][n]=new Vector3(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());
                    for(int n=0;n<bones;n++)cachedBones[f][n]=new Vector3(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());
                }
            }
        }
        void Sample(float time)
        {
            float t=Mathf.Repeat(time,10);string action=t<3?"Walk":t<6?"QSkill":"EUltimate";
            float phase=t<3?Mathf.Repeat(t/1.15f,1):t<6?Mathf.Clamp01((t-3.35f)/2.15f):Mathf.Clamp01((t-6.35f)/3.05f);
            var oldAnimation=models[0].GetComponent<Animation>();var baseline=oldAnimation.GetClip(action=="QSkill"?"Attack":action=="EUltimate"?"Heavy":"Walk");
            baseline.SampleAnimation(models[0],baseline.length*phase);
            int sourceFrame=Mathf.Clamp(Mathf.RoundToInt(t*Fps),0,cachedVertices.Length-1);
            previewMesh.vertices=cachedVertices[sourceFrame];previewMesh.normals=cachedNormals[sourceFrame];previewMesh.RecalculateBounds();
            for(int b=0;b<sourceBones.Length;b++)sourceBones[b].position=models[1].transform.TransformPoint(cachedBones[sourceFrame][b]);
            for(int i=0;i<2;i++)
            {
                phaseLabels[i].text=action=="Walk"?"걷기 · 접지와 관절 비교":action=="QSkill"?"Q · 맹호의 발톱":"E · 호랑이 포효";
                details[i].text=i==0?(action=="Walk"?"다리가 한 축에서 흔들리는 동작": "다리와 머리에 같은 회전 패턴 반복"):
                    action=="Walk"?"발→무릎→몸통 순서로 체중을 받음":action=="QSkill"?"준비 → 체중 이동 → 할퀴기 → 복귀":"발을 벌려 지지 → 가슴·머리 상승 → 턱 열기";
                float radius=action=="EUltimate"?Mathf.Lerp(.5f,1.6f,Mathf.Clamp01((phase-.25f)/.35f)):.8f;
                indicators[i].enabled=action!="Walk"&&phase>.24f&&phase<.7f;
                for(int n=0;n<48;n++){float angle=n/48f*Mathf.PI*2;indicators[i].SetPosition(n,new Vector3(Mathf.Sin(angle)*radius,.025f,Mathf.Cos(angle)*radius));}
                for(int n=0;n<rigLines[i].Count;n++){var bone=rigBones[i][n];var line=rigLines[i][n];line.enabled=showRig;line.SetPosition(0,bone.position);line.SetPosition(1,bone.parent.position);}
            }
            Canvas.ForceUpdateCanvases();foreach(var camera in cameras)camera.Render();
        }
        void Tick()
        {
            if(stage==null)return;
            try
            {
                if(exportFrame>=0)
                {
                    Sample(exportFrame/(float)Fps);var frame=new Texture2D(Width*2,Height,TextureFormat.RGB24,false);var previous=RenderTexture.active;
                    if(exportFrame==0||exportFrame==108)
                    {
                        string info="frame "+exportFrame+"\n";
                        for(int j=0;j<2;j++)foreach(var skin in models[j].GetComponentsInChildren<SkinnedMeshRenderer>())
                        {var baked=new Mesh();skin.BakeMesh(baked);info+=j+" root="+models[j].transform.position+" scale="+models[j].transform.lossyScale+" mesh="+baked.bounds+" center="+skin.transform.TransformPoint(baked.bounds.center)+" viewport="+cameras[j].WorldToViewportPoint(skin.transform.TransformPoint(baked.bounds.center))+"\n";UnityEngine.Object.DestroyImmediate(baked);}
                        File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-rig-demo-bounds-"+exportFrame+".txt"),info);
                    }
                    for(int i=0;i<2;i++){RenderTexture.active=targets[i];frame.ReadPixels(new Rect(0,0,Width,Height),i*Width,0);}
                    frame.Apply();RenderTexture.active=previous;File.WriteAllBytes(Path.Combine(output,$"frame-{exportFrame:0000}.png"),frame.EncodeToPNG());UnityEngine.Object.DestroyImmediate(frame);
                    exportFrame++;if(exportFrame>=FrameCount){exportFrame=-1;File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-rig-demo.result"),"PASS: Blender weighted 23-bone source cache, four source clips, Q deformation; 240 comparison frames exported to "+output);}
                }
                else Sample(paused?frozen:(float)EditorApplication.timeSinceStartup-started);
                Repaint();
            }
            catch(Exception e){exportFrame=-1;Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-rig-demo.result"),"FAIL: "+e);}
        }
        void OnGUI()
        {
            if(stage==null){GUILayout.Label("Preparing demo assets…");return;}
            if(GUI.Button(new Rect(16,8,130,28),paused?"재생":"일시정지")){frozen=(float)EditorApplication.timeSinceStartup-started;paused=!paused;if(!paused)started=(float)EditorApplication.timeSinceStartup-frozen;}
            if(GUI.Button(new Rect(158,8,150,28),showRig?"뼈대 숨기기":"뼈대 같이 보기"))showRig=!showRig;
            if(GUI.Button(new Rect(320,8,110,28),"걷기"))started=(float)EditorApplication.timeSinceStartup;
            if(GUI.Button(new Rect(442,8,110,28),"Q 시연"))started=(float)EditorApplication.timeSinceStartup-3.35f;
            if(GUI.Button(new Rect(564,8,110,28),"E 시연"))started=(float)EditorApplication.timeSinceStartup-6.35f;
            GUI.Label(new Rect(700,10,550,24),exportFrame>=0?$"영상 생성 {exportFrame}/{FrameCount}":"시연용 모델과 동작입니다 · 본 게임에는 미적용");
            GUI.DrawTexture(new Rect(0,48,Width,Height),targets[0]);GUI.DrawTexture(new Rect(Width,48,Width,Height),targets[1]);
        }
        void OnDisable()
        {
            EditorApplication.update-=Tick;if(stage!=null)UnityEngine.Object.DestroyImmediate(stage);
            for(int i=0;i<2;i++)if(targets[i]!=null){targets[i].Release();UnityEngine.Object.DestroyImmediate(targets[i]);}
            foreach(var item in owned)if(item!=null)UnityEngine.Object.DestroyImmediate(item);owned.Clear();
        }
    }
}

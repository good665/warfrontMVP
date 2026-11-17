from pathlib import Path
p=Path('hurt-work/SquadHurtPoseChecks.cs');s=p.read_text(encoding='utf-8-sig').replace('using UnityEngine;', 'using UnityEngine;\nusing UnityEngine.Rendering;\nusing UnityEngine.Rendering.Universal;\nusing System.Linq;')
s=s.replace('var neutralTorso=torso.localRotation;var neutralPosition=actor.localPosition;', '''var neutralTorso=torso.localRotation;var neutralPosition=actor.localPosition;
                    if(kind=="charge_bow")Capture(root,actor,"neutral",true);''')
s=s.replace('Check(Vector3.Distance(neutralPosition,actor.localPosition)<.15f,"Visual recoil moved too far");', '''Check(Vector3.Distance(neutralPosition,actor.localPosition)<.15f,"Visual recoil moved too far");
                    if(kind=="charge_bow")Capture(root,actor,"hit",false);''')
pos=s.rfind('    }\n}')
s=s[:pos]+'''        static void Capture(GameObject root,Transform actor,string name,bool setCamera)
        {
            if(SystemInfo.graphicsDeviceType==GraphicsDeviceType.Null)return;
            var camera=root.GetComponentsInChildren<Camera>(true).First(c=>c.name=="Fantasy Camera");
            if(setCamera){camera.orthographic=true;camera.orthographicSize=.95f;camera.aspect=camera.targetTexture.width/(float)camera.targetTexture.height;var facing=Quaternion.LookRotation(Vector3.right);camera.transform.position=actor.position+facing*new Vector3(2.2f,1.5f,3);camera.transform.LookAt(actor.position+Vector3.up*.45f);}
            var request=new UniversalRenderPipeline.SingleCameraRequest{destination=camera.targetTexture};if(!RenderPipeline.SupportsRenderRequest(camera,request))return;
            RenderPipeline.SubmitRenderRequest(camera,request);var previous=RenderTexture.active;
            try{RenderTexture.active=camera.targetTexture;var image=new Texture2D(camera.targetTexture.width,camera.targetTexture.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,image.width,image.height),0,0);image.Apply();File.WriteAllBytes(Path.Combine(Path.GetTempPath(),"warfront-hurt-"+name+".png"),image.EncodeToPNG());UnityEngine.Object.DestroyImmediate(image);}
            finally{RenderTexture.active=previous;}
        }
''' +s[pos:]
p.write_text(s,encoding='utf-8-sig')

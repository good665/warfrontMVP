from pathlib import Path
p=Path('skill-assets-work/BlenderSkillChecks.cs')
s=p.read_text(encoding='utf-8-sig').replace('using UnityEngine;', 'using UnityEngine;\nusing UnityEngine.Rendering;\nusing UnityEngine.Rendering.Universal;')
s=s.replace('var arm=actor.Find("root/torso/arm-right");clip.SampleAnimation(actor.gameObject,0);var before=arm.localRotation;clip.SampleAnimation(actor.gameObject,time);', '''var arm=actor.Find("root/torso/arm-right");clip.SampleAnimation(actor.gameObject,0);var before=arm.localRotation;
                    var skin=actor.GetComponentInChildren<SkinnedMeshRenderer>();var baked=new Mesh();skin.BakeMesh(baked);var restVertices=baked.vertices;
                    clip.SampleAnimation(actor.gameObject,time);skin.BakeMesh(baked);var posed=baked.vertices;bool deformed=false;
                    for(int i=0;i<posed.Length;i++)if(Vector3.Distance(posed[i],restVertices[i])>.015f){deformed=true;break;}
                    UnityEngine.Object.DestroyImmediate(baked);Check(deformed,"Original weighted skin does not deform: "+spec[0]);''')
s=s.replace('Debug.Log("BLENDER_SKILL_CHECKS PASS:', '''RenderPreviews(scene,root,actor.gameObject);
                Debug.Log("BLENDER_SKILL_CHECKS PASS:''')
s=s.replace('''        }
    }
}
''','''        }
        static void RenderPreviews(RetroFantasyScene scene,GameObject root,GameObject actor)
        {
            var camera=root.GetComponentsInChildren<Camera>(true).First(c=>c.name=="Fantasy Camera");
            camera.orthographic=true;camera.orthographicSize=1.15f;camera.aspect=1.4f;
            camera.transform.position=actor.transform.position+new Vector3(2.4f,1.8f,3);camera.transform.LookAt(actor.transform.position+Vector3.up*.5f);
            foreach(var item in new[]{new[]{"Heavy",".28"},new[]{"Throw",".10"},new[]{"Dodge",".08"}})
            {
                var clip=Resources.Load<AnimationClip>("SkillVisuals/"+item[0]);clip.SampleAnimation(actor,float.Parse(item[1],System.Globalization.CultureInfo.InvariantCulture));
                Capture(camera,"warfront-skill-"+item[0]+".png");
            }
            actor.SetActive(false);scene.SquadBombs(new[]{new MmoBomb{id=99,flight=.65f,radius=150,target_x=1000,target_y=1200,age=.78f,exploded=true}},0,0);
            camera.orthographicSize=4f;camera.transform.position=actor.transform.position+new Vector3(5,6,7);camera.transform.LookAt(actor.transform.position+Vector3.up*.4f);Capture(camera,"warfront-skill-Blast.png");
        }
        static void Capture(Camera camera,string name)
        {
            if(SystemInfo.graphicsDeviceType==GraphicsDeviceType.Null)return;
            var request=new UniversalRenderPipeline.SingleCameraRequest{destination=camera.targetTexture};
            if(!RenderPipeline.SupportsRenderRequest(camera,request))return;
            RenderPipeline.SubmitRenderRequest(camera,request);var previous=RenderTexture.active;
            try{RenderTexture.active=camera.targetTexture;var image=new Texture2D(camera.targetTexture.width,camera.targetTexture.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,image.width,image.height),0,0);image.Apply();File.WriteAllBytes(Path.Combine(Path.GetTempPath(),name),image.EncodeToPNG());UnityEngine.Object.DestroyImmediate(image);}
            finally{RenderTexture.active=previous;}
        }
    }
}
''')
p.write_text(s,encoding='utf-8-sig')

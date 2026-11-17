using System.Collections.Generic;
using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        private sealed class ZodiacEffect
        {
            public GameObject root; public Transform[] pieces; public string character,skill;
        }
        private readonly Dictionary<string,ZodiacEffect> zodiacEffects=new Dictionary<string,ZodiacEffect>();
        private readonly Dictionary<int,Material> zodiacMaterials=new Dictionary<int,Material>();
        private static readonly Color[] ZodiacColors={new Color(.45f,.8f,1),new Color(1,.65f,.2f),new Color(1,.36f,.07f),new Color(.65f,.85f,1),new Color(1,.24f,.025f),new Color(.35f,.9f,.12f),new Color(.25f,.85f,1),new Color(.5f,1,.65f),new Color(1,.73f,.12f),new Color(1,.45f,.15f),new Color(.3f,.55f,1),new Color(1,.45f,.65f)};
        private static readonly string[] EffectAnimals={"rat","ox","tiger","rabbit","dragon","snake","horse","goat","monkey","rooster","dog","pig"};
        private Material ZodiacMaterial(int index)
        {
            if(!zodiacMaterials.TryGetValue(index,out var mat))
            {
                mat=new Material(Shader.Find("Universal Render Pipeline/Unlit")){name="Zodiac energy "+index};
                mat.SetColor("_BaseColor",index==12?new Color(1,.94f,.7f):ZodiacColors[index]);zodiacMaterials[index]=mat;
            }
            return mat;
        }
        // Server event ID owns lifetime. Repeated snapshots advance phase without replaying casts.
        public void UpdateZodiacEffects(MmoEffect[] effects)
        {
            if(fiveEnvironment==null)return;
            var live=new HashSet<string>();
            if(effects!=null)foreach(var effect in effects)
            {
                int animal=System.Array.IndexOf(EffectAnimals,effect.character);
                if(animal<0||(effect.skill!="q"&&effect.skill!="e"))continue;
                live.Add(effect.id);
                if(!zodiacEffects.TryGetValue(effect.id,out var visual)||visual.root==null)
                {
                    visual=BuildZodiacEffect(effect,animal);zodiacEffects[effect.id]=visual;
                }
                // Pause stops server age; do not keep advancing client animation beyond snapshots.
                SampleZodiacEffect(visual,Mathf.Clamp01(effect.age/.8f));
            }
            var gone=new List<string>();
            foreach(var pair in zodiacEffects)if(!live.Contains(pair.Key)){if(pair.Value.root!=null)RemoveOwned(pair.Value.root);gone.Add(pair.Key);}
            foreach(string key in gone)zodiacEffects.Remove(key);
        }
        private ZodiacEffect BuildZodiacEffect(MmoEffect effect,int animal)
        {
            var root=new GameObject(effect.character+" "+effect.skill+" skill effect");root.transform.SetParent(fiveEnvironment.transform,false);
            root.transform.localPosition=WorldPoint(effect.x,effect.y);
            var direction=new Vector3(effect.fx,0,-effect.fy);root.transform.localRotation=direction.sqrMagnitude>.001f?Quaternion.LookRotation(direction):Quaternion.identity;
            int count=effect.skill=="e"?24:12;
            var visual=new ZodiacEffect{root=root,pieces=new Transform[count],character=effect.character,skill=effect.skill};
            for(int i=0;i<count;i++)
            {
                bool mote=effect.character=="rabbit"||effect.character=="snake"||effect.character=="dragon";
                var node=GameObject.CreatePrimitive(mote?PrimitiveType.Sphere:PrimitiveType.Cube);
                node.name=effect.character+" energy fragment "+i;node.transform.SetParent(root.transform,false);
                var collider=node.GetComponent<Collider>();if(collider!=null){collider.enabled=false;RemoveOwned(collider);}
                var renderer=node.GetComponent<Renderer>();renderer.sharedMaterial=ZodiacMaterial(i%4==0?12:animal);
                renderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;renderer.receiveShadows=false;
                visual.pieces[i]=node.transform;
            }
            SetLayer(root);return visual;
        }
        private static void Piece(Transform node,Vector3 position,Vector3 scale,Vector3 angles)
        {node.localPosition=position;node.localScale=scale;node.localRotation=Quaternion.Euler(angles);}
        private void SampleZodiacEffect(ZodiacEffect v,float t)
        {
            bool e=v.skill=="e";float fade=Mathf.Min(1,t*12+.15f)*Mathf.Pow(1-t,.65f);
            for(int i=0;i<v.pieces.Length;i++)
            {
                var node=v.pieces[i];float n=i/(float)v.pieces.Length,a=i*2.39996f;
                float s=Mathf.Sin(a),c=Mathf.Cos(a);Vector3 pos=Vector3.zero,size=Vector3.one*.2f,angles=Vector3.zero;
                switch(v.character)
                {
                    case "rat":
                        if(!e){pos=new Vector3((i%3-1)*.35f,.3f+(i%4)*.18f,-3.8f+t*3.2f+n*2);size=new Vector3(.07f,.07f,1.2f);}
                        else{float r=4.5f*(1-t)+.35f;pos=new Vector3(s*r,.35f,c*r);size=new Vector3(.24f,.25f,.6f);angles.y=-a*Mathf.Rad2Deg;}
                        break;
                    case "ox":
                        if(!e){pos=new Vector3((i%2==0?-1:1)*(.45f+n*.45f),.5f+n*.7f,t*2+n);size=new Vector3(.14f,.18f,.8f);angles=new Vector3(-30,0,i%2==0?-20:20);}
                        else{float r=.6f+t*5+n;pos=new Vector3(s*r,Mathf.Sin(t*Mathf.PI)*(1+n),c*r);size=new Vector3(.35f,.5f+n,.3f);angles=new Vector3(i*17,i*31,i*11);}
                        break;
                    case "tiger":
                        if(!e){int claw=i%3;float along=(i/3)/3f;pos=new Vector3((claw-1)*.42f,.5f+along*.8f,1+t*2+along*1.4f);size=new Vector3(.09f,.1f,.85f);angles.y=-18+t*36;}
                        else{float r=1+t*5;pos=new Vector3(s*r,.8f+(i%3)*.4f,c*r);size=new Vector3(.09f,.12f,1.2f);angles.y=a*Mathf.Rad2Deg;}
                        break;
                    case "rabbit":
                        if(!e){pos=new Vector3(s*(.6f+n),.3f+t*2.8f+n,c*(.6f+n));size=Vector3.one*(.12f+n*.12f);}
                        else{float angle=n*Mathf.PI*2;pos=new Vector3(Mathf.Cos(angle)*1.45f,1.6f+Mathf.Sin(angle)*1.45f,.2f);size=Vector3.one*(i%4==0?.32f:.15f);}
                        break;
                    case "dragon":
                        if(!e){float z=.6f+n*4.5f+t;pos=new Vector3(s*n*1.7f,.6f+c*.3f+n*.8f,z);size=new Vector3(.2f+n*.5f,.3f+n*.5f,.7f+n*.8f);}
                        else if(t<.42f){pos=new Vector3((n-.5f)*.8f,7*(1-t/.42f)+n*.7f,0);size=new Vector3(.6f,.7f+n, .6f);angles.z=-25;}
                        else{float r=(t-.42f)*8*(.5f+n);pos=new Vector3(s*r,.1f+Mathf.Sin((t-.42f)/.58f*Mathf.PI)*2*n,c*r);size=Vector3.one*(.3f+n*.65f);}
                        break;
                    case "snake":
                        if(!e){pos=new Vector3(i%2==0?-.38f:.38f,.7f+Mathf.Sin(n*Mathf.PI)*.6f,.5f+t*3+n);size=new Vector3(.13f,.35f,.16f);angles.x=40;}
                        else{pos=new Vector3(s*(1+n*3),.2f+Mathf.Sin(t*4+a)*.25f+n*.6f,c*(1+n*3));size=Vector3.one*(.4f+n*.9f)*(.7f+t*.5f);}
                        break;
                    case "horse":
                        if(!e){pos=new Vector3((i%2==0?-1:1)*(.5f+n),.25f+n*.7f,-1-n*3+t*1.5f);size=new Vector3(.06f,.08f,1.6f);angles.y=i%2==0?-10:10;}
                        else{int rider=i/4,part=i%4;pos=new Vector3((rider-2.5f)*.85f,part==0?.9f:part==1?1.45f:.3f,t*5+(rider%2)*.7f);size=part==0?new Vector3(.5f,.65f,1.1f):part==1?new Vector3(.3f,.5f,.45f):new Vector3(.12f,.65f,.14f);pos.z+=part>=2?(part==2?-.35f:.35f):0;}
                        break;
                    case "goat":
                        if(!e){pos=new Vector3(s*1.3f,.5f+n*1.5f,c*1.3f);size=new Vector3(.5f,.65f,.22f);angles=new Vector3(i*13,a*Mathf.Rad2Deg,15);}
                        else{pos=new Vector3(s*(.5f+n*3),t*3+n,c*(.5f+n*3));size=new Vector3(.12f,.55f,.12f);angles.z=35;}
                        break;
                    case "monkey":
                        if(!e){pos=new Vector3(0,.95f,1+n*6);size=new Vector3(.17f,.17f,.75f);angles.z=t*60;}
                        else{float turn=a+t*Mathf.PI*4;pos=new Vector3(Mathf.Sin(turn)*(1.5f+n),.6f+n*.7f,Mathf.Cos(turn)*(1.5f+n));size=new Vector3(.12f,.12f,1.5f);angles.y=turn*Mathf.Rad2Deg+90;}
                        break;
                    case "rooster":
                        if(!e){pos=new Vector3((i%3-1)*.25f,.7f+(i%2)*.3f,1+t*6+n);size=new Vector3(.13f,.035f,.75f);angles=new Vector3(0,(i%3-1)*8,45);}
                        else{pos=new Vector3(s*(1+t*3),.6f+t*3+n,c*(1+t*3));size=new Vector3(.09f,1+n*1.5f,.09f);angles.z=(i%2==0?-1:1)*25;}
                        break;
                    case "dog":
                        if(!e){pos=new Vector3((i%2==0?-1:1)*(.25f+n*.4f),1-n*.6f,.7f+t*2+n);size=new Vector3(.15f,.5f,.2f);angles.x=i%2==0?35:-35;}
                        else{pos=new Vector3(s*1.6f,.6f+(i%3)*.45f,c*1.6f);size=new Vector3(.6f,.65f,.12f);angles.y=a*Mathf.Rad2Deg;}
                        break;
                    case "pig":
                        if(!e){pos=new Vector3(s*(.4f+t*1.7f),.4f+c*.3f,1+t*2+n);size=new Vector3(.2f,.25f,.55f);angles=new Vector3(i*17,i*23,25);}
                        else{pos=new Vector3(s*1.2f,.45f+(i%4)*.4f,c*1.2f);size=new Vector3(.42f,.4f,.18f);angles.y=a*Mathf.Rad2Deg+t*45;}
                        break;
                }
                Piece(node,pos,size*fade,angles);
            }
        }
        private void DisposeZodiacMaterials()
        {foreach(var material in zodiacMaterials.Values)if(material!=null)RemoveOwned(material);zodiacMaterials.Clear();zodiacEffects.Clear();}
    }
}

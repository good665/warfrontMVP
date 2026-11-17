using System;
using System.IO;
using UnityEditor;
using UnityEngine;
namespace Warfront.EditorTools
{
    public sealed class ZodiacEffectPreview:EditorWindow
    {
        static readonly string[] Ids={"rat","ox","tiger","rabbit","dragon","snake","horse","goat","monkey","rooster","dog","pig"};
        static readonly string[] Names={"쥐","소","호랑이","토끼","용","뱀","말","양","원숭이","닭","개","돼지"};
        GameObject root;RetroFantasyScene scene;MmoSnapshot world;int animal;bool ultimate;string selection="";
        [MenuItem("Warfront/Five Floor/Preview Zodiac Effects")]
        public static void Open(){var w=GetWindow<ZodiacEffectPreview>();w.titleContent=new GUIContent("Q / E 이펙트");w.minSize=new Vector2(960,650);w.Show();}
        void OnEnable()
        {
            root=new GameObject("Isolated Zodiac VFX preview"){hideFlags=HideFlags.HideAndDontSave};scene=root.AddComponent<RetroFantasyScene>();scene.Initialize();
            world=new MmoSnapshot{zone="squad",instance_id="vfx-preview",five_floor=true,floor=3,world_width=2400,world_height=3600,obstacles=Array.Empty<MmoObstacle>()};
        }
        void OnGUI()
        {
            animal=GUILayout.SelectionGrid(animal,Names,12,GUILayout.Height(32));
            ultimate=GUILayout.Toolbar(ultimate?1:0,new[]{"Q 스킬","E 필살기"},GUILayout.Height(32))==1;
            if(scene==null)return;
            scene.BeginField(world,Vector2.zero);scene.PrepareFiveFloorActor("player:preview","hero",Ids[animal]);
            scene.Actor("player:preview",1200,1800,0,-1,false,false,false,false);scene.EndField();
            float age=(float)(EditorApplication.timeSinceStartup%1.5);
            world.effects=age<.8f?new[]{new MmoEffect{id="preview",character=Ids[animal],skill=ultimate?"e":"q",x=1200,y=1800,fx=0,fy=-1,age=age,radius=260}}:Array.Empty<MmoEffect>();
            // Clear on selection change so the preview uses the newly chosen geometry.
            string next=Ids[animal]+ultimate;
            if(next!=selection){scene.UpdateZodiacEffects(Array.Empty<MmoEffect>());selection=next;}
            scene.FiveFloorEnvironment(new SquadSnapshot{world=world,battle=new FiveFloorBattle{five_floor=true,portals=Array.Empty<BattlePortal>()}});
            scene.StrategicView(1200,1750,7.5f,2400,3600);
            foreach(var camera in root.GetComponentsInChildren<Camera>())if(camera.targetTexture!=null)camera.Render();
            GUI.DrawTexture(new Rect(0,72,position.width,position.height-72),scene.View,ScaleMode.ScaleToFit,false);Repaint();
        }
        void OnDisable(){if(root!=null)DestroyImmediate(root);}
    }
}

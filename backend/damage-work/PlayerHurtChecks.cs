using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using UnityEditor;
namespace Warfront.Verification
{
    public static class PlayerHurtChecks
    {
        const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
        static object Call(object o,string n,params object[] args)=>o.GetType().GetMethod(n,Flags).Invoke(o,args);
        static object Get(object o,string n)=>o.GetType().GetField(n,Flags).GetValue(o);
        static void Set(object o,string n,object v)=>o.GetType().GetField(n,Flags).SetValue(o,v);
        static void Check(bool value,string text){if(!value)throw new Exception(text);}
        static MmoSnapshot Snapshot(float hp,float maximum=100,string instance="hurt-check")=>new MmoSnapshot{zone="frontier",instance_id=instance,you_id="self",world_width=3600,world_height=2400,players=new[]{new MmoActor{id="self",x=1000,y=1000,hp=hp,max_hp=maximum,fx=1},new MmoActor{id="other",hp=100,max_hp=100}},enemies=new MmoEnemy[0],obstacles=new MmoObstacle[0]};
        [MenuItem("Warfront/Player Hurt/Run Checks")]
        public static void Run()
        {
            var inactive=new GameObject("Inactive hurt checks");inactive.SetActive(false);var stage=new GameObject("Player hurt scene checks");AudioClip clip=null;
            try
            {
                var game=inactive.AddComponent<GameBootstrap>();var scene=stage.AddComponent<RetroFantasyScene>();scene.Initialize();
                var full=Snapshot(100);scene.BeginField(full,Vector2.zero);scene.Actor("player:self",1000,1000,1,0,false,false,false,false);scene.EndField();
                Set(game,"retroScene",scene);Set(game,"mmoImpactAudio",false);
                var pulses=(IList)Get(game,"mmoCombatPulses");
                Call(game,"MmoApplyCombatFeedback",null,full);Check(pulses.Count==0,"Initial snapshot generated fake hurt");
                var hit=Snapshot(92);Call(game,"MmoApplyCombatFeedback",full,hit);
                Check(pulses.Count==1,"Authoritative self damage did not create feedback");
                var pulse=pulses[0];Check((bool)pulse.GetType().GetField("self").GetValue(pulse),"Self damage categorized as enemy hit");
                Check(Mathf.Abs((float)pulse.GetType().GetField("damage").GetValue(pulse)-8)<.001f,"Displayed damage not actual HP loss");
                var timers=(Dictionary<string,float>)Get(scene,"playerImpactUntil");Check(timers.ContainsKey("player:self"),"Player pose/camera impact not triggered");
                float expiry=timers["player:self"];Call(game,"MmoApplyCombatFeedback",hit,hit);Check(pulses.Count==1&&timers["player:self"]==expiry,"Repeated snapshot retriggered hurt");
                Call(game,"MmoApplyCombatFeedback",hit,full);Check(pulses.Count==1,"Healing triggered hurt");
                var ally=Snapshot(100);ally.players[1].hp=50;Call(game,"MmoApplyCombatFeedback",full,ally);Check(pulses.Count==2&&timers["player:self"]==expiry,"Other player damage missing number or triggered local hurt");
                Call(game,"ResetMmoCombatFeedback");Call(game,"MmoApplyCombatFeedback",Snapshot(120,120),Snapshot(100,100));
                Check(pulses.Count==0&&timers.Count==0,"Equipment max-HP reduction triggered fake damage");
                Call(game,"MmoApplyCombatFeedback",Snapshot(120,120),Snapshot(92,100));Check(pulses.Count==1,"Concurrent max HP change hid real damage");
                Check(Mathf.Abs((float)pulses[0].GetType().GetField("damage").GetValue(pulses[0])-8)<.001f,"Clamped max-HP damage wrong");
                Call(game,"MmoApplyCombatFeedback",hit,Snapshot(70,100,"new-instance"));Check(pulses.Count==0&&timers.Count==0,"Zone change retained hurt");
                Call(game,"MmoApplyCombatFeedback",full,hit);var switched=Snapshot(60);switched.you_id="other";Call(game,"MmoApplyCombatFeedback",hit,switched);Check(pulses.Count==0,"Player identity change retained hurt");

                scene.ThirdPerson("player:self",1000,1000,90,18,5.6f);
                var camera=Array.Find(stage.GetComponentsInChildren<Camera>(),c=>c.name=="Fantasy Camera");var before=camera.transform.position;var beforeRotation=camera.transform.rotation;
                scene.PlayerImpact("self");timers["player:self"]=Time.unscaledTime+.18f;
                scene.Actor("player:self",1000,1000,0,0,false,false,false,false);stage.transform.Find("Encounter frontier/player:self").GetComponent<HeroHitReaction>().Sample(Time.unscaledTime);scene.ThirdPerson("player:self",1000,1000,90,18,5.6f);
                var body=stage.transform.Find("Encounter frontier/player:self");
                Check(Quaternion.Angle(body.localRotation,Quaternion.LookRotation(Vector3.right))>1,"Character did not flinch");
                Check(Vector3.Distance(before,camera.transform.position)>.001f&&Vector3.Distance(before,camera.transform.position)<.06f,"Camera impulse absent or excessive");
                Check(Quaternion.Angle(beforeRotation,camera.transform.rotation)<1,"Camera impulse changed aim excessively");
                Check(hit.players[0].x==1000&&hit.players[0].y==1000&&hit.players[0].hp==92,"Visual impact changed authoritative state");
                timers["player:self"]=Time.unscaledTime-1;
                scene.Actor("player:self",1000,1000,0,0,false,false,false,false);stage.transform.Find("Encounter frontier/player:self").GetComponent<HeroHitReaction>().Sample(Time.unscaledTime);scene.ThirdPerson("player:self",1000,1000,90,18,5.6f);
                Check(Quaternion.Angle(body.localRotation,Quaternion.LookRotation(Vector3.right))<.01f,"Stationary actor retained flinch rotation");
                Check(Vector3.Distance(camera.transform.position,before)<.001f,"Camera impulse did not reset");
                scene.PlayerImpact("self");scene.ShowTown();Check(timers.Count==0,"Lobby retained player hit timer");
                clip=(AudioClip)typeof(GameBootstrap).GetMethod("CreateMmoHurtClip",BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,null);
                var samples=new float[clip.samples];clip.GetData(samples,0);float energy=0;
                foreach(float sample in samples){Check(!float.IsNaN(sample)&&Mathf.Abs(sample)<=1,"Invalid hurt audio sample");energy+=Mathf.Abs(sample);}
                Check(energy>10&&clip.length<.3f,"Dedicated hurt sound is silent or too long");
                Debug.Log("PLAYER_HURT_CHECKS PASS: authoritative own damage, displayed amount, duplicate/heal/other/maxHP/zone/identity suppression, flinch/camera decay, no state mutation and dedicated audio");
            }
            finally{if(clip!=null)UnityEngine.Object.DestroyImmediate(clip);UnityEngine.Object.DestroyImmediate(inactive);UnityEngine.Object.DestroyImmediate(stage);}
            SquadComputerChecks.Run();
        }
    }
}

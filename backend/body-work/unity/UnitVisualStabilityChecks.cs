using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public static class UnitVisualStabilityChecks
    {
        const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
        static void Check(bool value,string message){if(!value)throw new Exception(message);}
        [InitializeOnLoadMethod] static void Auto(){EditorApplication.delayCall+=()=>{
            string path=Path.Combine(Path.GetTempPath(),"warfront-unit-visual.request");if(!File.Exists(path))return;
            if(EditorApplication.isPlayingOrWillChangePlaymode){Auto();return;}File.Delete(path);
            try{Run();File.WriteAllText(path+".result","PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(path+".result",e.ToString());}
        };}
        [MenuItem("Warfront/Squad/Check Unit Visual Stability")]
        public static void Run()
        {
            var root=new GameObject("Unit visual stability checks");
            try
            {
                var scene=root.AddComponent<RetroFantasyScene>();scene.Initialize();var world=new MmoSnapshot{zone="squad",instance_id="unit-stability"};scene.BeginField(world,Vector2.zero);
                foreach(string key in new[]{"player:ally","enemy:bot"})
                {
                    scene.Actor(key,1000,900,1,0,false,false,false,false);scene.SquadRole(key,"archer");
                    var actor=root.transform.Find("Encounter squad/"+key);var stability=actor.GetComponent<CharacterScaleStability>();Check(stability!=null,"Missing scale contract: "+key);
                    var saved=new Dictionary<Transform,Vector3>{{actor,actor.localScale}};
                    foreach(var skin in actor.GetComponentsInChildren<SkinnedMeshRenderer>())foreach(var bone in skin.bones)if(bone!=null)saved[bone]=bone.localScale;
                    var animation=actor.GetComponent<Animation>();
                    foreach(string clip in new[]{"Idle","Walk","Bow"})
                    {
                        Check(animation.GetClip(clip)!=null,"Missing clip "+clip);
                        for(int sample=0;sample<6;sample++)
                        {
                            animation.GetClip(clip).SampleAnimation(actor.gameObject,sample*.09f);
                            foreach(var entry in saved)entry.Key.localScale=entry.Value*1.13f;
                            stability.RestoreScales();foreach(var entry in saved)Check((entry.Key.localScale-entry.Value).sqrMagnitude<.000001f,"Body scale drift: "+clip);
                        }
                    }
                    var bow=actor.Find("Archer Bow");Check(bow!=null,"No bow");var flex=bow.localScale=new Vector3(.7f,.8f,.9f);stability.RestoreScales();Check(bow.localScale==flex,"Weapon scale incorrectly locked");
                    scene.SquadAction(key,12,"bow",.2f,.4f,1,0,0,0,false,700,.35f);
                    if(key.StartsWith("enemy")){scene.EnemyImpact("bot",false);scene.EnemyTelegraphs(new[]{new MmoEnemy{id="bot",hp=20,hit_flash=1,stagger_left=.2f}});Check(animation["Bow"].enabled&&animation["Bow"].speed==0,"Legacy telegraph replaced authoritative bow");}
                    else scene.PlayerImpact("ally");
                    var reaction=actor.GetComponent<HeroHitReaction>();Check(reaction!=null,"Missing additive hurt");reaction.Sample(Time.unscaledTime+.08f);stability.RestoreScales();foreach(var entry in saved)Check(entry.Key.localScale==entry.Value,"Hurt changed body scale");
                }
                scene.PlayerImpact("ally",true);scene.BeginField(world,Vector2.zero);scene.EndField();var corpse=root.transform.Find("Encounter squad/player:ally");Check(corpse!=null,"No bounded death presentation");
                scene.Actor("player:ally",1000,900,1,0,false,false,false,false);scene.SquadAction("player:ally",12,"",0,.4f,1,0,0,0,false,700,.35f);
                var deaths=(Dictionary<string,float>)typeof(RetroFantasyScene).GetField("deathUntil",Flags).GetValue(scene);Check(!deaths.ContainsKey("player:ally"),"Revive retained death timer");Check(Quaternion.Angle(corpse.localRotation,Quaternion.LookRotation(Vector3.right))<.01f,"Revive retained corpse/hurt pose");
                scene.PlayerImpact("ally",true);deaths["player:ally"]=Time.unscaledTime-1;scene.BeginField(world,Vector2.zero);scene.EndField();Check(root.transform.Find("Encounter squad/player:ally")==null,"Dead ally retained indefinitely");
                Debug.Log("UNIT_VISUAL_STABILITY_CHECKS PASS: both teams body scale, weapon freedom, authoritative bow/hurt, bounded death and same-id revive");
            }
            finally{UnityEngine.Object.DestroyImmediate(root);}
        }
    }
}

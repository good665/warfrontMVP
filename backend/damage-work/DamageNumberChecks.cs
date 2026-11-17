using System;
using System.Collections;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification {
public static class DamageNumberChecks {
 [InitializeOnLoadMethod] static void Auto(){EditorApplication.delayCall+=()=>{var p=System.IO.Path.Combine(System.IO.Path.GetTempPath(),"warfront-damage.request");if(!System.IO.File.Exists(p))return;if(EditorApplication.isPlayingOrWillChangePlaymode){Auto();return;}System.IO.File.Delete(p);try{RunAll();System.IO.File.WriteAllText(p+".result","PASS");}catch(Exception e){Debug.LogException(e);System.IO.File.WriteAllText(p+".result",e.ToString());}};}
 const BindingFlags F=BindingFlags.NonPublic|BindingFlags.Instance;
 static MmoSnapshot State(float own,float ally,float enemy,float basis)=>new MmoSnapshot{zone="squad",instance_id="numbers",you_id="self",players=new[]{new MmoActor{id="self",hp=own,max_hp=100},new MmoActor{id="ally",hp=ally,max_hp=100}},enemies=new[]{new MmoEnemy{id="enemy",hp=enemy,max_hp=100},new MmoEnemy{id="base",kind="base",hp=basis,max_hp=100}}};
 static void Check(bool value,string message){if(!value)throw new Exception(message);}
 public static void Run(){var root=new GameObject("Damage checks");root.SetActive(false);try{var game=root.AddComponent<GameBootstrap>();typeof(GameBootstrap).GetField("mmoImpactAudio",F).SetValue(game,false);var method=typeof(GameBootstrap).GetMethod("MmoApplyCombatFeedback",F);var pulses=(IList)typeof(GameBootstrap).GetField("mmoCombatPulses",F).GetValue(game);var full=State(100,100,100,100);var hit=State(92,85,70,0);method.Invoke(game,new object[]{full,hit});Check(pulses.Count==4,"All damaged targets must generate a number");float sum=0;foreach(var pulse in pulses)sum+=(float)pulse.GetType().GetField("damage").GetValue(pulse);Check(Mathf.Abs(sum-153)<.001f,"Damage numbers must equal actual HP loss, including lethal damage");method.Invoke(game,new object[]{hit,hit});Check(pulses.Count==4,"Repeated snapshots duplicated numbers");method.Invoke(game,new object[]{hit,full});Check(pulses.Count==4,"Healing generated numbers");var other=State(50,100,100,100);other.instance_id="other";method.Invoke(game,new object[]{full,other});Check(pulses.Count==0,"New match retained damage numbers");Debug.Log("DAMAGE_NUMBER_CHECKS PASS: own/ally/enemy/base, actual damage, lethal, duplicate, healing and transition");}finally{UnityEngine.Object.DestroyImmediate(root);}}
 public static void RunAll(){Run();PlayerHurtChecks.Run();}
}}

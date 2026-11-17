using System;
using System.IO;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification {
public static class StrategyIntegrationChecks {
 [InitializeOnLoadMethod] static void Schedule(){EditorApplication.delayCall+=()=>{var p=Path.Combine(Path.GetTempPath(),"warfront-rts.request");if(!File.Exists(p))return;if(EditorApplication.isPlayingOrWillChangePlaymode){Schedule();return;}File.Delete(p);try{Run();File.WriteAllText(p+".result","PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(p+".result",e.ToString());}};}
 [MenuItem("Warfront/Squad/Run RTS Integration Checks")]
 public static void Run(){StrategyChecks.Run();HeroBowChecks.Run();SquadHurtPoseChecks.Run();DamageNumberChecks.Run();CombatPoolingChecks.Run();Debug.Log("RTS_INTEGRATION_CHECKS PASS");}
}}

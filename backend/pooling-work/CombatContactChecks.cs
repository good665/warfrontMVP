using System;
using System.IO;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public static class CombatContactChecks
    {
        static void Check(bool value,string message){if(!value)throw new Exception(message);}
        [InitializeOnLoadMethod]
        static void AutoRun(){EditorApplication.delayCall+=()=>{var path=Path.Combine(Path.GetTempPath(),"warfront-contact-check.request");if(!File.Exists(path))return;File.Delete(path);try{Run();File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-contact-check.result"),"PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-contact-check.result"),e.ToString());}};}
        [MenuItem("Warfront/Squad/Check Melee Contact Display")]
        public static void Run()
        {
            var root=new GameObject("Melee contact timing checks");var scene=root.AddComponent<RetroFantasyScene>();
            try
            {
                scene.Initialize();scene.BeginField(new MmoSnapshot{zone="squad",instance_id="contacts"},Vector2.zero);
                scene.Actor("player:self",1000,1200,1,0,false,false,false,false);
                scene.SquadAction("player:self",1,"attack",.40f,.55f,1,0,0,0,true,145,.35f);
                var line=root.transform.Find("Encounter squad/player:self/Server timed sword trail").GetComponent<LineRenderer>();
                Check(!line.enabled,"Attack trail appears before authoritative .16-second windup");
                scene.SquadAction("player:self",2,"heavy",.37f,.55f,1,0,0,0,true,210,.35f);
                Check(!line.enabled,"Heavy trail appears before authoritative .20-second windup");
                scene.SquadAction("player:self",3,"attack",.23f,.55f,1,0,0,0,true,145,.35f);
                Check(line.enabled,"Late active swing disappeared");
                for(int i=0;i<line.positionCount;i++){var point=line.GetPosition(i);Check(Mathf.Abs(Mathf.Atan2(point.x,point.z)*Mathf.Rad2Deg)<=69.52f,"Visible trail leaves server damage sector");}
                scene.SquadAction("player:self",4,"attack",.10f,.55f,1,0,0,0,true,145,.35f);
                Check(!line.enabled,"Recovery shows a damaging trail after active window");
                Debug.Log("COMBAT_CONTACT_CHECKS PASS: server windup, late active contact, sector geometry, recovery");
            }
            finally{UnityEngine.Object.DestroyImmediate(root);}
            CompanionAttackChecks.Run();
        }
    }
}

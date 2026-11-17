using System;
using System.IO;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public static class CombatPoolingChecks
    {
        static void Check(bool value,string message){if(!value)throw new Exception(message);}
        [InitializeOnLoadMethod]
        static void AutoRun(){EditorApplication.delayCall+=()=>{var request=Path.Combine(Path.GetTempPath(),"warfront-pooling-check.request");if(!File.Exists(request))return;File.Delete(request);try{Run();File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-pooling-check.result"),"PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-pooling-check.result"),e.ToString());}};}
        [MenuItem("Warfront/Run Combat Pooling Checks")]
        public static void Run()
        {
            var root=new GameObject("Pooling checks");var scene=root.AddComponent<RetroFantasyScene>();
            try
            {
                scene.Initialize();scene.BeginField(new MmoSnapshot{zone="squad",instance_id="pool-a"},Vector2.zero);
                scene.SquadProjectiles(new[]{new MmoProjectile{id=1,start_x=100,end_x=400,flight=1}},0);
                var arrow=root.transform.Find("Encounter squad/Authoritative arrow 1").gameObject;int arrowId=arrow.GetInstanceID();
                arrow.transform.localScale=Vector3.one*9;arrow.transform.localRotation=Quaternion.Euler(20,30,40);arrow.SetActive(false);
                scene.SquadProjectiles(null,0);
                Check(arrow!=null&&!arrow.activeSelf,"Returned arrow was destroyed instead of retained");
                scene.SquadProjectiles(new[]{new MmoProjectile{id=2,start_x=100,end_x=400,flight=1}},0);
                var reused=root.transform.Find("Encounter squad/Authoritative arrow 2").gameObject;
                Check(reused.GetInstanceID()==arrowId,"Arrow instance was not reused");Check(reused.activeSelf&&reused.transform.localScale==Vector3.one,"Arrow state leaked across rentals");
                scene.SquadBombs(new[]{new MmoBomb{id=1,team=0,flight=1,radius=150}},0,0);
                var bomb=root.transform.Find("Encounter squad/Server bomb 1").gameObject;int bombId=bomb.GetInstanceID();
                var ring=root.transform.Find("Encounter squad/Bomb landing and blast 1").GetComponent<LineRenderer>();int ringId=ring.GetInstanceID();
                scene.SquadBombs(null,0,0);Check(bomb!=null&&!bomb.activeSelf,"Bomb not returned");
                scene.SquadBombs(new[]{new MmoBomb{id=2,team=1,flight=1,radius=150,exploded=true,age=1.1f}},0,0);
                Check(root.transform.Find("Encounter squad/Server bomb 2").gameObject.GetInstanceID()==bombId,"Bomb not reused");
                ring=root.transform.Find("Encounter squad/Bomb landing and blast 2").GetComponent<LineRenderer>();
                Check(ring.GetInstanceID()==ringId&&Mathf.Abs(ring.startColor.g-.25f)<.005f&&Mathf.Abs(ring.startColor.b-.12f)<.005f&&ring.enabled,"Ring reused with stale team or visibility");
                scene.BeginField(new MmoSnapshot{zone="squad",instance_id="pool-b"},Vector2.zero);
                scene.SquadProjectiles(new[]{new MmoProjectile{id=3,end_x=400,flight=1}},0);
                Check(root.transform.Find("Encounter squad/Authoritative arrow 3").gameObject.GetInstanceID()==arrowId,"Field switch discarded pool");
                scene.SquadBombs(new[]{new MmoBomb{id=3,flight=1,radius=150}},0,0);
                Check(root.transform.Find("Encounter squad/Server bomb 3").gameObject.GetInstanceID()==bombId,"Field switch lost active bomb");
                scene.SquadProjectiles(null,0);scene.SquadBombs(null,0,0);
                var burst=new MmoProjectile[80];for(int i=0;i<burst.Length;i++)burst[i]=new MmoProjectile{id=100+i,end_x=400,flight=1};
                scene.SquadProjectiles(burst,0);scene.SquadProjectiles(null,0);
                var storage=root.transform.Find("Combat visual pool");Check(storage!=null&&storage.childCount<=192,"Idle pool retained unbounded burst objects");
                int arrows=0;foreach(Transform child in storage)if(child.name.StartsWith("Authoritative arrow"))arrows++;
                Check(arrows==64,"Arrow idle retention did not respect cap");
                Debug.Log("COMBAT_POOLING_CHECKS PASS: instance reuse, reset, ring team color, field transition");
            }
            finally{UnityEngine.Object.DestroyImmediate(root);}
            CompanionAttackChecks.Run();
        }
    }
}


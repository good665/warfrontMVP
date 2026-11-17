using System;
using System.Linq;
using UnityEngine;
using UnityEditor;
namespace Warfront.Verification
{
    public static class SquadCharacterRestoreChecks
    {
        static void Check(bool v,string m){if(!v)throw new Exception(m);}
        public static void Run()
        {
            var root=new GameObject("Restored squad character checks");var scene=root.AddComponent<RetroFantasyScene>();
            try
            {
                scene.Initialize();scene.BeginField(new MmoSnapshot{zone="squad",instance_id="restore",obstacles=new MmoObstacle[0]},Vector2.zero);
                scene.Actor("player:self",1000,1200,1,0,false,false,false,false);scene.Actor("enemy:other",1150,1200,-1,0,false,false,false,false);scene.EndField();
                var source=Resources.Load<GameObject>("MiniDungeon/Characters/Human").GetComponentInChildren<SkinnedMeshRenderer>().sharedMesh;
                foreach(string key in new[]{"player:self","enemy:other"})
                {
                    var actor=root.transform.Find("Encounter squad/"+key);Check(actor.GetComponentInChildren<SkinnedMeshRenderer>().sharedMesh==source,"Squad character not restored to original");
                    foreach(string kind in new[]{"attack","heavy","bomb","dodge"})
                    {
                        scene.SquadAction(key,1,kind,.3f,.55f,1,0,0,0,true,145,.35f);
                        var animation=actor.GetComponent<Animation>();string clip=kind=="dodge"?"Dodge":kind=="heavy"&&animation.GetClip("Heavy")!=null?"Heavy":kind=="bomb"&&animation.GetClip("Throw")!=null?"Throw":"Attack";
                        Check(Mathf.Abs(animation[clip].normalizedTime-(1-.3f/.55f))<.02f,"Restored rig action fallback failed: "+kind);
                    }
                    scene.SquadAction(key,1,"attack",.3f,.55f,1,0,0,.6f,true,145,.35f);
                    Check(actor.GetComponent<Animation>().IsPlaying("Idle"),"Old rig does not return to idle");
                }
                Check(!root.GetComponentsInChildren<Transform>(true).Any(t=>t.name=="Authoritative melee reach"),"Attack radius still visible");
                Debug.Log("SQUAD_CHARACTER_RESTORE PASS: original Human meshes for both teams, legacy attack/heavy/bomb/dodge compatibility, expiry, no ground attack radius");
            }
            finally{UnityEngine.Object.DestroyImmediate(root);}
            PlayerHurtChecks.Run();
        }
    }
}

using System.Collections.Generic;
using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        private readonly Dictionary<string,string> companionRoles=new Dictionary<string,string>();
        private readonly Dictionary<string,GameObject> companionBows=new Dictionary<string,GameObject>();
        private readonly Dictionary<string,GameObject> nockedArrows=new Dictionary<string,GameObject>();
        private readonly Dictionary<string,Transform> bowHands=new Dictionary<string,Transform>();
        private readonly Dictionary<int,GameObject> flyingArrows=new Dictionary<int,GameObject>();
        private readonly Dictionary<int,float> arrowReplayStart=new Dictionary<int,float>();
        private GameObject bowPrefab,arrowPrefab;
        private AnimationClip bowClip;
        private void ClearCompanionVisuals(){companionRoles.Clear();companionBows.Clear();nockedArrows.Clear();bowHands.Clear();flyingArrows.Clear();arrowReplayStart.Clear();}
        private void RemoveCompanionVisuals(string key){companionRoles.Remove(key);companionBows.Remove(key);nockedArrows.Remove(key);bowHands.Remove(key);}
        public void SquadRole(string key,string kind)
        {
            if(!actors.TryGetValue(key,out var actor))return;
            if(string.IsNullOrEmpty(kind)){kind=key.EndsWith(":archer")?"archer":key.EndsWith(":guard")?"guard":key.EndsWith(":healer")?"healer":"hero";}
            if(companionRoles.TryGetValue(key,out string previous)&&previous==kind)return;
            companionRoles[key]=kind;
            if(kind!="archer")return;
            if(bowPrefab==null)bowPrefab=Resources.Load<GameObject>("SquadEquipment/Bow");
            if(arrowPrefab==null)arrowPrefab=Resources.Load<GameObject>("SquadEquipment/Arrow");
            if(bowClip==null)bowClip=Resources.Load<AnimationClip>("SquadEquipment/BowDraw");
            Transform hand=null;
            foreach(var t in actor.GetComponentsInChildren<Transform>(true))
            {
                if(t.name.StartsWith("weapon-sword")||t.name.StartsWith("shield-round"))t.gameObject.SetActive(false);
                if(t.name=="arm-left")hand=t;
            }
            if(hand==null||bowPrefab==null||arrowPrefab==null||bowClip==null)return;
            var animation=actor.GetComponent<Animation>();if(animation.GetClip("Bow")==null)animation.AddClip(bowClip,"Bow");
            var bow=Instantiate(bowPrefab,actor.transform);bow.name="Archer Bow";SetLayer(bow);companionBows[key]=bow;bowHands[key]=hand;
            var nock=Instantiate(arrowPrefab,bow.transform);nock.name="Nocked Arrow";nock.transform.localScale=Vector3.one*.6f;SetLayer(nock);nockedArrows[key]=nock;
            UpdateBowPose(key,false,0);
        }
        private void UpdateBowPose(string key,bool drawing,float elapsed)
        {
            if(!companionBows.TryGetValue(key,out var bow)||!actors.TryGetValue(key,out var actor)||!bowHands.TryGetValue(key,out var hand))return;
            bow.transform.position=hand.TransformPoint(new Vector3(0,-.12f,.035f));bow.transform.rotation=actor.transform.rotation;
            // Pull the string back until the server's .25-second release.
            float draw=drawing?Mathf.Clamp01(elapsed/.25f):0;
            float pull=drawing&&elapsed<.25f?.055f+.15f*draw:.055f;
            var line=bow.GetComponentInChildren<LineRenderer>();if(line!=null)line.SetPosition(1,new Vector3(0,0,-pull));
            if(nockedArrows.TryGetValue(key,out var nock)){nock.SetActive(!drawing||elapsed<.25f);nock.transform.localPosition=new Vector3(0,0,-pull+.16f);nock.transform.localRotation=Quaternion.identity;}
        }
        public void SquadProjectiles(MmoProjectile[] projectiles,float snapshotAge)
        {
            if(arrowPrefab==null)arrowPrefab=Resources.Load<GameObject>("SquadEquipment/Arrow");
            var present=projectileIds;present.Clear();
            if(projectiles!=null)foreach(var p in projectiles)
            {
                present.Add(p.id);
                if(!flyingArrows.TryGetValue(p.id,out var arrow))
                {
                    if(arrowPrefab==null)continue;
                    arrow=RentCombatVisual(arrowPool,arrowPrefab,"Authoritative arrow "+p.id);flyingArrows[p.id]=arrow;
                    // A completed event can be our first snapshot of a short shot.
                    // Replay only its visual flight; server damage is already decided.
                    if(p.resolved||p.age+Mathf.Clamp(snapshotAge,0,.3f)>=p.flight*.85f)arrowReplayStart[p.id]=Time.unscaledTime;
                }
                bool replay=arrowReplayStart.TryGetValue(p.id,out float replayAt);
                arrow.SetActive(replay?Time.unscaledTime-replayAt<.12f:!p.resolved);
                float t=Mathf.Clamp01((p.age+Mathf.Clamp(snapshotAge,0,.3f))/Mathf.Max(.01f,p.flight));
                if(replay)t=Mathf.Clamp01((Time.unscaledTime-replayAt)/.12f);
                arrow.transform.localPosition=WorldPoint(Mathf.Lerp(p.start_x,p.end_x,t),Mathf.Lerp(p.start_y,p.end_y,t))+Vector3.up*.85f;
                var direction=WorldPoint(p.end_x-p.start_x,p.end_y-p.start_y);if(direction.sqrMagnitude>.000001f)arrow.transform.localRotation=Quaternion.LookRotation(direction);
            }
            var expired=expiredProjectileIds;expired.Clear();foreach(var id in flyingArrows.Keys)if(!present.Contains(id))expired.Add(id);
            foreach(int id in expired){ReturnCombatVisual(arrowPool,flyingArrows[id]);flyingArrows.Remove(id);arrowReplayStart.Remove(id);}
        }
    }
}

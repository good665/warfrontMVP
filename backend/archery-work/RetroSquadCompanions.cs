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
        private readonly Dictionary<int,Vector3> arrowVisualStarts=new Dictionary<int,Vector3>();
        private readonly Dictionary<int,float> arrowReplayStart=new Dictionary<int,float>();
        private GameObject bowPrefab,arrowPrefab;
        private AnimationClip bowClip;
        private void ClearCompanionVisuals(){companionRoles.Clear();companionBows.Clear();nockedArrows.Clear();bowHands.Clear();flyingArrows.Clear();arrowReplayStart.Clear();arrowVisualStarts.Clear();}
        private void RemoveCompanionVisuals(string key){companionRoles.Remove(key);companionBows.Remove(key);nockedArrows.Remove(key);bowHands.Remove(key);}
        public void SquadRole(string key,string kind)
        {
            if(!actors.TryGetValue(key,out var actor))return;
            if(string.IsNullOrEmpty(kind)){kind=key.EndsWith(":archer")?"archer":key.EndsWith(":guard")?"guard":key.EndsWith(":healer")?"healer":"hero";}
            if(companionRoles.TryGetValue(key,out string previous)&&previous==kind)return;
            companionRoles[key]=kind;
            if(kind!="archer"&&kind!="hero")return;
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
            bow.AddComponent<ArcheryBowVisual>().Initialize(actor.transform,hand,actor.transform.Find("root/torso/arm-right"),nock.transform);
            UpdateBowPose(key,false,0);
        }
        private void UpdateBowPose(string key,bool drawing,float elapsed)
        {
            if(!companionBows.TryGetValue(key,out var bow)||!actors.TryGetValue(key,out var actor)||!bowHands.TryGetValue(key,out var hand))return;
            var visual=bow.GetComponent<ArcheryBowVisual>();if(visual!=null)visual.SetPhase(drawing,elapsed);
        }
        private Vector3 ArrowVisualStart(MmoProjectile projectile)
        {
            var fallback=WorldPoint(projectile.start_x,projectile.start_y)+Vector3.up*.85f;
            GameObject bow;
            if(companionBows.TryGetValue("player:"+projectile.owner_id,out bow)||companionBows.TryGetValue("enemy:"+projectile.owner_id,out bow))
            {
                var visual=bow.GetComponent<ArcheryBowVisual>();if(visual==null)return fallback;
                var point=field.transform.InverseTransformPoint(visual.ReleasePosition);
                if(new Vector2(point.x-fallback.x,point.z-fallback.z).sqrMagnitude>.75f*.75f)return fallback;
                return point;
            }
            return fallback;
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
                    arrow=RentCombatVisual(arrowPool,arrowPrefab,"Authoritative arrow "+p.id);flyingArrows[p.id]=arrow;arrowVisualStarts[p.id]=ArrowVisualStart(p);
                    // A completed event can be our first snapshot of a short shot.
                    // Replay only its visual flight; server damage is already decided.
                    if(p.resolved||p.age+Mathf.Clamp(snapshotAge,0,.3f)>=p.flight*.85f)arrowReplayStart[p.id]=Time.unscaledTime;
                }
                arrow.transform.localScale=arrowPrefab.transform.localScale*(p.charged?1.35f:1f);
                bool replay=arrowReplayStart.TryGetValue(p.id,out float replayAt);
                arrow.SetActive(replay?Time.unscaledTime-replayAt<.12f:!p.resolved);
                float t=Mathf.Clamp01((p.age+Mathf.Clamp(snapshotAge,0,.3f))/Mathf.Max(.01f,p.flight));
                if(replay)t=Mathf.Clamp01((Time.unscaledTime-replayAt)/.12f);
                var visualStart=arrowVisualStarts[p.id];arrow.transform.localPosition=Vector3.Lerp(visualStart,WorldPoint(p.end_x,p.end_y)+Vector3.up*visualStart.y,t);
                var direction=WorldPoint(p.end_x-p.start_x,p.end_y-p.start_y);if(direction.sqrMagnitude>.000001f)arrow.transform.localRotation=Quaternion.LookRotation(direction);
            }
            var expired=expiredProjectileIds;expired.Clear();foreach(var id in flyingArrows.Keys)if(!present.Contains(id))expired.Add(id);
            foreach(int id in expired){ReturnCombatVisual(arrowPool,flyingArrows[id]);flyingArrows.Remove(id);arrowReplayStart.Remove(id);arrowVisualStarts.Remove(id);}
        }
    }
}

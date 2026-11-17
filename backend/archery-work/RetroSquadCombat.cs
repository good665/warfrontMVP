using System.Collections.Generic;
using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        private GameObject squadGrenade,squadBlastPrefab;
        private readonly Dictionary<int,GameObject> squadBlastEffects=new Dictionary<int,GameObject>();
        private readonly Dictionary<int,Vector3> bombLaunchPoints=new Dictionary<int,Vector3>();
        private readonly Dictionary<int,float> squadBlastReplayStart=new Dictionary<int,float>();
        private readonly Dictionary<string,float> walkUntil=new Dictionary<string,float>();
        private readonly Dictionary<string,LineRenderer> squadArcs=new Dictionary<string,LineRenderer>();
        private readonly Dictionary<int,GameObject> squadBombs=new Dictionary<int,GameObject>();
        private readonly Dictionary<int,LineRenderer> squadBlastRings=new Dictionary<int,LineRenderer>();
        private Material squadEffectMaterial;
        private int ownBowImpulseAction=-1;
        private float ownBowImpulseAt=-100,ownBowImpulseStrength;
        private void ClearSquadVisuals()
        {
            ownBowImpulseAction=-1;ownBowImpulseAt=-100;ClearCompanionVisuals();walkUntil.Clear();squadArcs.Clear();squadBombs.Clear();squadBlastRings.Clear();
        }
        private LineRenderer CombatLine(string label,Transform parent,int count,Color color,float width)
        {
            if(squadEffectMaterial==null)squadEffectMaterial=new Material(Shader.Find("Universal Render Pipeline/Unlit")){name="Squad combat lines"};
            var go=new GameObject(label);go.transform.SetParent(parent,false);SetLayer(go);
            var line=go.AddComponent<LineRenderer>();line.sharedMaterial=squadEffectMaterial;line.useWorldSpace=false;line.positionCount=count;line.widthMultiplier=width;line.startColor=line.endColor=color;line.numCapVertices=3;return line;
        }
        private static void Arc(LineRenderer line,float reach,float from,float to,float height)
        {
            for(int i=0;i<line.positionCount;i++){float angle=Mathf.Lerp(from,to,i/(float)(line.positionCount-1))*Mathf.Deg2Rad;line.SetPosition(i,new Vector3(Mathf.Sin(angle)*reach,height,Mathf.Cos(angle)*reach));}
        }
        // The clip is explicitly sampled from the authoritative action phase. No root motion.
        public void SquadAction(string key,int id,string kind,float left,float duration,float fx,float fy,float dodgeLeft,float age,bool own,float reach,float dot,MmoCombatRules rules=null,float chargeRatio=0)
        {
            if(!actors.TryGetValue(key,out var actor))return;
            var animation=actor.GetComponent<Animation>();if(animation==null)return;EnsureBlenderSkillClips(animation);
            float remaining=Mathf.Max(0,left-age);bool active=(remaining>0||(kind=="charge_bow"&&age<.35f))&&duration>0;
            var sword=actor.transform.Find("root/torso/arm-right/weapon-sword(Clone)");
            if(sword!=null)sword.gameObject.SetActive(!(active&&kind=="bomb")&&(!companionRoles.TryGetValue(key,out var role)||(role!="archer"&&role!="hero")));
            bool heroBow=kind=="hero_bow"||kind=="charge_bow"||kind=="charged_bow";
            float bowTime=kind=="charge_bow"?Mathf.Min(.249f,(duration-remaining)/.20f*.249f):kind=="charged_bow"?.25f+Mathf.Clamp01((duration-remaining)/.30f)*.40f:kind=="hero_bow"?(duration-remaining<.12f?(duration-remaining)/.12f*.25f:.25f+(duration-remaining-.12f)/.28f*.40f):duration-remaining;
            string clip=kind=="bow"||heroBow?"Bow":kind=="guard_attack"||kind=="heal"?"Attack":kind=="attack"?"Attack":kind=="heavy"?"Heavy":kind=="dodge"?"Dodge":kind=="bomb"?"Throw":"";
            if((kind=="heavy"||kind=="bomb")&&animation.GetClip(clip)==null)clip="Attack";
            if(active&&!string.IsNullOrEmpty(clip)&&animation.GetClip(clip)!=null)
            {
                animation.Stop();var state=animation[clip];state.enabled=true;state.weight=1;state.speed=0;state.normalizedTime=heroBow?Mathf.Clamp01(bowTime/.65f):Mathf.Clamp01(1-remaining/duration);animation.Sample();
                if(Mathf.Abs(fx)+Mathf.Abs(fy)>.001f)actor.transform.localRotation=Quaternion.LookRotation(new Vector3(fx,0,-fy));
            }
            else
            {
                foreach(AnimationState state in animation)state.speed=1;
                string locomotion=walkUntil.TryGetValue(key,out float until)&&Time.unscaledTime<until?"Walk":"Idle";
                if(!animation.IsPlaying(locomotion)){animation.Stop();animation.Play(locomotion);}
            }
            UpdateBowPose(key,active&&(kind=="bow"||heroBow),heroBow?bowTime:duration-remaining);
            if(own&&active&&heroBow&&bowTime>=.25f&&ownBowImpulseAction!=id)
            {ownBowImpulseAction=id;ownBowImpulseAt=Time.unscaledTime;ownBowImpulseStrength=kind=="charged_bow"?.25f:.12f;}
            if(!squadArcs.TryGetValue(key,out var arc)){arc=CombatLine("Server timed sword trail",actor.transform,20,new Color(1,.81f,.30f),.07f);squadArcs[key]=arc;}
            float elapsed=duration-remaining;
            float windup=kind=="heavy"?(rules!=null&&rules.heavy_windup>0?rules.heavy_windup:.20f):(rules!=null&&rules.attack_windup>0?rules.attack_windup:.16f);
            float activeEnd=kind=="guard_attack"?.26f:(rules!=null&&rules.melee_active_end>0?rules.melee_active_end:.43f);
            // Render contact feedback only inside the server's damage window/sector.
            bool swing=active&&(kind=="attack"||kind=="heavy"||kind=="guard_attack")&&elapsed>=windup&&elapsed<activeEnd;
            arc.enabled=swing;
            if(swing)
            {
                float halfAngle=Mathf.Acos(Mathf.Clamp(dot,-1,1))*Mathf.Rad2Deg;
                float angle=Mathf.Lerp(-halfAngle,halfAngle,Mathf.Clamp01((elapsed-windup)/Mathf.Max(.01f,activeEnd-windup)));
                Arc(arc,(kind=="guard_attack"?95:reach)/50f/actor.transform.localScale.x,Mathf.Max(-halfAngle,angle-38),angle,.65f);
            }

        }
        public void SquadBombs(MmoBomb[] bombs,float age,int ownTeam)
        {
            var present=bombIds;present.Clear();
            if(bombs!=null)foreach(var b in bombs)
            {
                present.Add(b.id);
                if(!squadBombs.TryGetValue(b.id,out var node))
                {
                    if(squadGrenade==null)squadGrenade=Resources.Load<GameObject>("SkillVisuals/Bomb")??Resources.Load<GameObject>("WarfrontCombat/Bomb");
                    if(squadGrenade==null)continue;
                    node=RentCombatVisual(bombPool,squadGrenade,"Server bomb "+b.id);squadBombs[b.id]=node;
                    var ring=RentBlastRing("Bomb landing and blast "+b.id,b.team==ownTeam?new Color(1,.75f,.2f):new Color(1,.25f,.12f));squadBlastRings[b.id]=ring;
                    if(squadBlastPrefab==null)squadBlastPrefab=Resources.Load<GameObject>("SkillVisuals/Blast");
                    if(squadBlastPrefab!=null)squadBlastEffects[b.id]=RentCombatVisual(blastEffectPool,squadBlastPrefab,"Blender blast "+b.id);
                }
                float elapsed=b.age+Mathf.Min(age,.3f);float flight=Mathf.Max(.01f,b.flight);float release=Mathf.Min(.12f,flight*.25f);float t=Mathf.Clamp01((elapsed-release)/Mathf.Max(.01f,flight-release));
                if(!bombLaunchPoints.ContainsKey(b.id)||elapsed<release)bombLaunchPoints[b.id]=HeldBombPosition(b);
                // Never invent explosion damage; await the server's exploded flag.
                node.SetActive(!b.exploded);node.transform.localPosition=elapsed<release?bombLaunchPoints[b.id]:Vector3.Lerp(bombLaunchPoints[b.id],WorldPoint(b.target_x,b.target_y)+Vector3.up*.18f,t)+Vector3.up*(4*1.8f*t*(1-t));node.transform.localScale=Vector3.one;node.transform.localRotation=Quaternion.Euler(t*480,t*240,0);
                var marker=squadBlastRings[b.id];marker.transform.localPosition=WorldPoint(b.target_x,b.target_y)+Vector3.up*.06f;
                if(b.exploded&&!squadBlastReplayStart.ContainsKey(b.id))squadBlastReplayStart[b.id]=Time.unscaledTime-Mathf.Clamp(elapsed-flight,0,.2f);
                float blast=b.exploded?Mathf.Clamp01((Time.unscaledTime-squadBlastReplayStart[b.id])/.35f):0;
                if(squadBlastEffects.TryGetValue(b.id,out var effect))
                {
                    effect.SetActive(b.exploded&&blast<1);effect.transform.localPosition=WorldPoint(b.target_x,b.target_y)+Vector3.up*.04f;
                    if(b.exploded)effect.GetComponent<BlenderBlastVisual>().Show(b.radius/50f,blast,b.team==ownTeam);
                }
                marker.enabled=b.exploded&&blast<1;marker.widthMultiplier=b.exploded?.16f*(1-blast)+.025f:.035f;Arc(marker,b.radius/50f*(b.exploded?.3f+.7f*blast:1),0,360,b.exploded?blast*.5f:0);
            }
            var gone=expiredBombIds;gone.Clear();foreach(var id in squadBombs.Keys)if(!present.Contains(id))gone.Add(id);
            foreach(int id in gone){ReturnCombatVisual(bombPool,squadBombs[id]);ReturnCombatVisual(blastRingPool,squadBlastRings[id].gameObject);if(squadBlastEffects.TryGetValue(id,out var effect))ReturnCombatVisual(blastEffectPool,effect);
                squadBlastEffects.Remove(id);squadBlastReplayStart.Remove(id);bombLaunchPoints.Remove(id);squadBombs.Remove(id);squadBlastRings.Remove(id);}
        }
    }
}


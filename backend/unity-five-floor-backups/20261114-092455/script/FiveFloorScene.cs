using System.Collections.Generic;
using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        private readonly Dictionary<string,string> fiveModels=new Dictionary<string,string>();
        private readonly Dictionary<string,GameObject> fivePrefabs=new Dictionary<string,GameObject>();
        private GameObject fiveEnvironment;
        private readonly Dictionary<string,LineRenderer> fiveSkillRings=new Dictionary<string,LineRenderer>();
        public void PrepareFiveFloorActor(string key,string kind,string character)
        {
            string resource=kind=="hero"&&!string.IsNullOrEmpty(character)?character:kind=="dragon_boss"?"boss":null;
            if(resource==null){fiveModels.Remove(key);return;}
            if(fiveModels.TryGetValue(key,out string old)&&old!=resource&&actors.TryGetValue(key,out var previous))
            {Destroy(previous);actors.Remove(key);lastPositions.Remove(key);RemoveCompanionVisuals(key);}
            fiveModels[key]=resource;
        }
        private GameObject FiveFloorPrefab(string key)
        {
            if(!fiveModels.TryGetValue(key,out string resource))return null;
            if(!fivePrefabs.TryGetValue(resource,out var prefab)){prefab=Resources.Load<GameObject>("Zodiac/"+resource+"/Character");fivePrefabs[resource]=prefab;}
            return prefab;
        }
        public void FiveFloorPose(string key,float jump,float transition)
        {
            if(!actors.TryGetValue(key,out var actor)||!fiveModels.ContainsKey(key))return;
            float j=Mathf.Clamp01((.65f-jump)/.65f);
            var position=actor.transform.localPosition;
            position.y=jump>0?Mathf.Sin(j*Mathf.PI)*.75f:0;
            actor.transform.localPosition=position;
            float fade=transition>.325f?Mathf.Clamp01((transition-.325f)/.325f):transition>0?Mathf.Clamp01(1-transition/.325f):1;
            // Native skinned meshes scale from a small silhouette into full size after relocation.
            actor.transform.localScale=Vector3.one*(fiveModels[key]=="boss"?3.4f:1.7f)*Mathf.Max(.02f,fade);
        }
        public void FiveFloorEnvironment(SquadSnapshot snapshot)
        {
            if(field==null||snapshot?.battle==null)return;
            if(fiveEnvironment==null||fiveEnvironment.transform.parent!=field.transform)
            {
                fiveEnvironment=new GameObject("Five floor portals and camp markers");fiveEnvironment.transform.SetParent(field.transform,false);
                fiveSkillRings.Clear();
                foreach(float x in new[]{140f,3460f})
                {
                    var portal=new GameObject("Bidirectional portal");portal.transform.SetParent(fiveEnvironment.transform,false);portal.transform.localPosition=WorldPoint(x,1200);
                    var ring=CombatLine("Violet portal",portal.transform,49,new Color(.7f,.35f,2f),.16f);
                    for(int i=0;i<49;i++){float angle=i/48f*Mathf.PI*2;ring.SetPosition(i,new Vector3(Mathf.Cos(angle)*1.15f,1.25f+Mathf.Sin(angle)*1.2f,0));}
                    Model("column",new Vector3(-1.5f,0,0),Vector3.zero,new Vector3(.8f,1.8f,.8f),portal.transform);
                    Model("column",new Vector3(1.5f,0,0),Vector3.zero,new Vector3(.8f,1.8f,.8f),portal.transform);
                }
                SetLayer(fiveEnvironment);
            }
            var live=new HashSet<string>();
            if(snapshot.world.effects!=null)foreach(var effect in snapshot.world.effects)
            {
                if(effect.kind=="shot")continue;live.Add(effect.id);
                if(!fiveSkillRings.TryGetValue(effect.id,out var ring))
                {
                    ring=CombatLine("Zodiac skill "+effect.kind,fiveEnvironment.transform,49,effect.kind=="heal"?new Color(.3f,1,.5f):new Color(1,.55f,.15f),.12f);fiveSkillRings[effect.id]=ring;
                }
                ring.transform.localPosition=WorldPoint(effect.x,effect.y)+Vector3.up*.12f;
                Arc(ring,effect.radius/50f,0,360,.06f);
            }
            var gone=new List<string>();foreach(var entry in fiveSkillRings)if(!live.Contains(entry.Key)){Destroy(entry.Value.gameObject);gone.Add(entry.Key);}
            foreach(string key in gone)fiveSkillRings.Remove(key);
        }
    }
}

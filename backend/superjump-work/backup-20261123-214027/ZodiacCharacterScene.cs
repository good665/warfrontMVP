using System.Collections.Generic;
using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        private readonly Dictionary<string,string> zodiacModels=new Dictionary<string,string>();
        private readonly Dictionary<string,GameObject> zodiacPrefabs=new Dictionary<string,GameObject>();


        private readonly Dictionary<string,GameObject> minionModels=new Dictionary<string,GameObject>();
        private readonly Dictionary<string,GameObject> minionPrefabs=new Dictionary<string,GameObject>();

        public void PrepareZodiacActor(string key,string kind,string character)
        {
            // Allied minions use the Blender soldier variants in Assets/Resources/SquadUnits/.
            string folder=!key.StartsWith("player:")?null:kind=="archer"?"Soldier":kind=="guard"?"Melee":null;
            if(folder!=null&&!minionPrefabs.ContainsKey(folder))minionPrefabs[folder]=Resources.Load<GameObject>("SquadUnits/"+folder+"/Character");
            if(folder!=null&&minionPrefabs[folder]!=null)minionModels[key]=minionPrefabs[folder];
            else minionModels.Remove(key);
            string resource=kind=="hero"&&!string.IsNullOrEmpty(character)?character:null;
            if(resource==null){zodiacModels.Remove(key);return;}
            if(zodiacModels.TryGetValue(key,out string old)&&old!=resource&&actors.TryGetValue(key,out var previous))
            {squadArcs.Remove(key);RemoveOwned(previous);actors.Remove(key);lastPositions.Remove(key);RemoveCompanionVisuals(key);}
            zodiacModels[key]=resource;
        }
        private GameObject ZodiacPrefab(string key)
        {
            if(!zodiacModels.TryGetValue(key,out string resource))return null;
            if(!zodiacPrefabs.TryGetValue(resource,out var prefab)){prefab=Resources.Load<GameObject>("ZodiacHumanoid/"+resource+"/Character")??Resources.Load<GameObject>("SidelineZodiac/"+resource+"/Character")??Resources.Load<GameObject>("Zodiac/"+resource+"/Character");zodiacPrefabs[resource]=prefab;}
            return prefab;
        }
        public void ZodiacPose(string key,float jump)
        {
            if(!actors.TryGetValue(key,out var actor)||!zodiacModels.ContainsKey(key))return;
            float j=Mathf.Clamp01((.65f-jump)/.65f);
            var position=actor.transform.localPosition;
            position.y=jump>0?Mathf.Sin(j*Mathf.PI)*.75f:0;
            actor.transform.localPosition=position;
            actor.transform.localScale=Vector3.one*1.7f;
        }


    }
}

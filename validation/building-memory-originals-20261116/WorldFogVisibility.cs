using System;
using System.Collections.Generic;
using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        private readonly HashSet<GameObject> fogSuppressedVisuals=new HashSet<GameObject>();
        private readonly HashSet<string> currentEnemySight=new HashSet<string>();
        public void RestoreFogVisuals()
        {
            foreach(var node in fogSuppressedVisuals)if(node!=null)node.SetActive(true);
            fogSuppressedVisuals.Clear();
        }
        private static bool SameVisionFloor(MmoSnapshot world,int floor)=>world.floor<=0||floor<=0||floor==world.floor;
        public void ApplyWorldVision(MmoSnapshot world,SquadSnapshot squad,Func<float,float,bool> canSee)
        {
            if(world==null||canSee==null)return;
            currentEnemySight.Clear();
            if(world.enemies!=null)foreach(var actor in world.enemies)
                if(SameVisionFloor(world,actor.floor)&&canSee(actor.x,actor.y))currentEnemySight.Add("enemy:"+actor.id);
            foreach(var pair in actors)
            {
                if(pair.Value==null||!pair.Key.StartsWith("enemy:"))continue;
                pair.Value.SetActive(currentEnemySight.Contains(pair.Key));
            }
            if(squad!=null)
            {
                if(world.players!=null)foreach(var actor in world.players)
                    if(actor.team!=squad.team&&actors.TryGetValue("player:"+actor.id,out var body))body.SetActive(SameVisionFloor(world,actor.floor)&&canSee(actor.x,actor.y));
                if(squad.bases!=null)foreach(var headquarters in squad.bases)
                    if(headquarters.team!=squad.team&&squadBuildings.TryGetValue(headquarters.id,out var building)&&(!SameVisionFloor(world,headquarters.floor)||!canSee(headquarters.x,headquarters.y)))building.SetActive(false);
            }
            foreach(var node in flyingArrows.Values)HideOutsideVision(node,canSee);
            foreach(var node in squadBombs.Values)HideOutsideVision(node,canSee);
            foreach(var node in squadBlastEffects.Values)HideOutsideVision(node,canSee);
            foreach(var line in squadBlastRings.Values)if(line!=null)HideOutsideVision(line.gameObject,canSee);
            foreach(var effect in zodiacEffects.Values)HideOutsideVision(effect.root,canSee);
            foreach(var node in dangerMarkers)HideOutsideVision(node,canSee);
            foreach(var node in enemyWarnings)HideOutsideVision(node,canSee);
        }
        private void HideOutsideVision(GameObject node,Func<float,float,bool> canSee)
        {
            if(node==null||!node.activeSelf)return;
            var p=node.transform.position-origin;
            if(!canSee(p.x*50,-p.z*50)){node.SetActive(false);fogSuppressedVisuals.Add(node);}
        }
    }
}

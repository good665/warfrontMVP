using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        public void EquipmentAppearance(string key,bool helmetEquipped)
        {
            if(actors.TryGetValue(key,out var actor)){var art=actor.GetComponent<RuneKnightVisual>();if(art!=null)art.Configure(helmetEquipped,new Color(.72f,.4f,1));}
            RefreshTownPortrait(helmetEquipped);
        }
        public void ActorLife(string key,bool living)
        {
            if(!actors.TryGetValue(key,out var actor))return;
            alive.Add(key);
            var death=actor.GetComponent<ActorDeathVisual>();
            if(!living&&death==null)death=actor.AddComponent<ActorDeathVisual>();
            var fog=actor.GetComponent<FogActorVisibility>();
            if(!living&&fog!=null&&fog.enabled){fog.Show(Time.unscaledTime-1);fog.Sample(Time.unscaledTime);fog.enabled=false;}
            if(death!=null)death.SetAlive(living);
            if(living&&fog!=null)fog.enabled=true;
            if(!living){
                if(squadArcs.TryGetValue(key,out var arc))arc.enabled=false;
                actionUntil.Remove(key);actionState.Remove(key);walkUntil.Remove(key);playerImpactUntil.Remove(key);
            }
        }
    }
}

using UnityEngine;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private bool squadAutoLookPending;
        private void ObserveSquadLookTransition(bool wasActive,bool wasAlive,string previousCode,string previousPlayer)
        {
            if(!SquadInBattle||MmoSelf==null||MmoSelf.hp<=0){squadAutoLookPending=false;return;}
            if(!wasActive||!wasAlive||previousCode!=squadSnapshot.code||previousPlayer!=mmoWorld.you_id)
                squadAutoLookPending=true;
        }
        private bool ConsumeSquadAutoLook(bool hasMouse,bool focused)
        {
            if(!squadAutoLookPending||!hasMouse||!focused||!SquadInBattle||!mmoConnected||MmoSelf==null||MmoSelf.hp<=0||
               mmoPanel.Length>0||strategyExpanded||strategyPlacement.Length>0)return false;
            squadAutoLookPending=false;
            return true;
        }
    }
}

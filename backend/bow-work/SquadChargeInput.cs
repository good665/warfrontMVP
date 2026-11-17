using UnityEngine;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private bool squadChargeHeld,squadChargeRelease;
        private float squadChargeStarted=-1;
        private Vector2 squadChargeReleaseAim;
        // Capture both edges before the network gate, including taps within one frame.
        private void CaptureSquadCharge(bool held,bool pressed,bool allowed)
        {
            if(!allowed){ResetSquadCharge();return;}
            if((held&&!squadChargeHeld)||pressed)
            {mmoSkill1=true;if(!squadChargeHeld)squadChargeStarted=Time.realtimeSinceStartup;}
            if((!held&&squadChargeHeld)||(!held&&pressed))
            {
                squadChargeRelease=true;var self=MmoSelf;
                squadChargeReleaseAim=new Vector2(self?.x??0,self?.y??0)+DungeonFirstPersonMath.Forward(dungeonYaw)*800;
            }
            squadChargeHeld=held;
        }
        private void ResetSquadCharge(){squadChargeHeld=squadChargeRelease=mmoSkill1=false;squadChargeStarted=-1;}
        private void DrawSquadChargeGauge()
        {
            var self=MmoSelf;if(!SquadInBattle||self==null||self.hp<=0||mmoPanel.Length>0||(!squadChargeHeld&&!self.charge_active))return;
            if(!self.charge_active&&self.skill1_cooldown>0)return;
            float seconds=mmoWorld?.combat_rules?.charge_seconds??1.2f;if(seconds<=0)seconds=1.2f;
            float ratio=self.charge_active?self.charge_ratio+Mathf.Max(0,Time.realtimeSinceStartup-mmoLastResponse)/seconds:(Time.realtimeSinceStartup-squadChargeStarted)/seconds;
            ratio=Mathf.Clamp01(ratio);
            Fill(new Rect(460,140,360,18),new Color(.08f,.09f,.15f,.9f));Fill(new Rect(462,142,356*ratio,14),ratio>=1?baseGold:baseCyan);
            BaseText(new Rect(460,161,360,24),ratio>=1?"최대 충전 · Q를 놓아 발사":$"차지샷 {ratio*100:0}% · 놓으면 발사",15,Color.white,TextAnchor.MiddleCenter);
        }
    }
}

using UnityEngine;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private void DrawSquadBattle()
        {
            bool pauseEnabled=GUI.enabled;GUI.enabled=pauseEnabled&&!SquadPauseBlocked;
            DrawMmoField();
            // Navigation projects in field-local coordinates; command grid can extend into the HUD.
            GUI.BeginGroup(new Rect(mmoField.x,mmoField.y,mmoField.width,720-mmoField.y));
            bool old=GUI.enabled;GUI.enabled=old&&mmoPanel.Length==0;
            if(FiveFloorActive)DrawFiveFloorInventory();else DrawStrategyHud();GUI.enabled=old;GUI.EndGroup();
            DrawCombatRuneBar(true);
            if(squadSnapshot?.status=="finished")DrawSquadResult();
            if(mmoPanel=="controls")DrawMmoControlSettings();
            GUI.enabled=pauseEnabled;
            DrawSquadPause();
        }
        private void DrawCombatRuneBar(bool squad)
        {
            RuneFrame(new Rect(20,594,900,112),true);
            bool previous=GUI.enabled;var self=MmoSelf;
            GUI.enabled=previous&&mmoPanel.Length==0&&mmoConnected&&self!=null&&self.hp>0;
            DrawRuneControl(mmoPad,"이동\nWASD",-1);
            DrawRuneControl(mmoAttackButton,FiveFloorActive?"기본 공격\n좌클릭":squad?"활 발사\nSPACE":"공격\nSPACE",0);
            DrawRuneControl(mmoDodgeButton,$"회피 Shift\n{self?.dodge_cooldown??0:0.0}s",3);
            if(GUI.Button(mmoDodgeButton,GUIContent.none,GUIStyle.none))mmoDodge=true;
            DrawRuneControl(mmoSkill1Button,FiveFloorActive?FiveSkillLabel(false):squad?(self?.skill1_cooldown>0?$"차지샷 Q\n{self.skill1_cooldown:0.0}s":"차지샷 Q\n길게 충전"):$"폭발 룬 Q\n{self?.skill1_cooldown??0:0.0}s",FiveFloorActive?-1:4);
            if((!squad||FiveFloorActive)&&GUI.Button(mmoSkill1Button,GUIContent.none,GUIStyle.none))mmoSkill1=true;
            DrawRuneControl(mmoSkill2Button,FiveFloorActive?FiveSkillLabel(true):$"{(squad?"폭탄 E":"회복 E")}\n{self?.skill2_cooldown??0:0.0}s",FiveFloorActive?-1:squad?5:6);
            if(GUI.Button(mmoSkill2Button,GUIContent.none,GUIStyle.none))mmoSkill2=true;
            GUI.enabled=previous&&mmoPanel.Length==0;
            if(squad){
                if(RuneButton(new Rect(206,608,150,34),"조작 설정"))OpenMmoControlSettings();
                if(RuneButton(new Rect(206,650,150,34),"항복 · 마을"))SquadLeave(true);
            }else{
                if(RuneButton(new Rect(206,608,150,34),"장비 · 소지품")){ReleaseDungeonCursor();mmoPanel="equipment";}
                if(RuneButton(new Rect(206,650,72,34),"설정"))OpenMmoControlSettings();
                if(RuneButton(new Rect(284,650,72,34),"마을")){if(mmoWorld!=null)MmoLeave();else{ShutdownMmo();screen=Screen.Lobby;}}
                RuneFrame(new Rect(926,594,334,112),true);
                if(RuneButton(new Rect(1020,608,110,34),"캐릭터 · 임무")){ReleaseDungeonCursor();mmoPanel="profile";}
                if(RuneButton(new Rect(1138,608,110,34),"공동 사냥터"))OpenMmoWorld("frontier");
                if(RuneButton(new Rect(1020,650,110,34),"위험 지대"))OpenMmoWorld("minefield");
                if(RuneButton(new Rect(1138,650,110,34),"고대 유적"))OpenMmoWorld("ruins");
            }
            GUI.enabled=previous;
            if(squad&&!FiveFloorActive)DrawSquadChargeGauge();
            string error=squad?squadError:mmoError;
            if(!string.IsNullOrEmpty(error))BaseText(new Rect(265,552,700,25),error,13,runeGold,TextAnchor.MiddleCenter);
            if(self!=null&&self.hp<=0){
                RuneFrame(new Rect(438,475,405,62),true);
                BaseText(new Rect(450,482,381,46),squad?$"영웅 부활까지 {squadSnapshot.respawn_left:0.0}초\n마우스 · 터치로 360° 둘러보기":"전투 불능 · 잠시 후 부활합니다\n마우스 · 터치로 360° 둘러보기",14,runeText,TextAnchor.MiddleCenter);
            }
        }
    }
}

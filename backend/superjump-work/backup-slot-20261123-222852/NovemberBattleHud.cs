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
            if(RtsActive)DrawRtsHud();GUI.enabled=old;GUI.EndGroup();
            DrawCombatRuneBar(true);
            if(RtsActive){DrawRtsStatsAndTips();DrawSquadGroundLabels();DrawSquadGearTip();DrawSquadNotice();}
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
            DrawRuneControl(mmoPad,L.T("이동")+"\nWASD",-1);
            // Icon-only action slots; names live in the hover tooltips (RtsStatsHud).
            DrawRuneSlot(mmoAttackButton,0,self?.attack_cooldown??0);
            DrawRuneSlot(mmoDodgeButton,3,squad?0:self?.dodge_cooldown??0);
            if(GUI.Button(mmoDodgeButton,GUIContent.none,GUIStyle.none)){if(squad)rtsJump=true;else mmoDodge=true;}
            DrawRuneSlot(mmoSkill1Button,4,self?.skill1_cooldown??0);
            if((!squad||RtsActive)&&GUI.Button(mmoSkill1Button,GUIContent.none,GUIStyle.none))mmoSkill1=true;
            DrawRuneSlot(mmoSkill2Button,6,self?.skill2_cooldown??0);
            if(GUI.Button(mmoSkill2Button,GUIContent.none,GUIStyle.none))mmoSkill2=true;
            // Slots above the action row: squad weapon, armor and consumables (SquadGearHud); the rest stay empty.
            if(squad&&RtsActive)DrawSquadGearSlots(self);else foreach(var slot in MmoItemSlots)DrawRuneSlot(slot,-1,0);
            GUI.enabled=previous&&mmoPanel.Length==0;
            if(squad){
                if(RuneButton(new Rect(206,608,150,34),L.T("조작 설정")))OpenMmoControlSettings();
                if(RuneButton(new Rect(206,650,150,34),L.T("항복 · 마을")))SquadLeave(true);
            }else{
                if(RuneButton(new Rect(206,608,150,34),"장비 · 소지품")){ReleaseDungeonCursor();mmoPanel="equipment";}
                if(RuneButton(new Rect(206,650,72,34),"설정"))OpenMmoControlSettings();
                if(RuneButton(new Rect(284,650,72,34),"마을")){if(mmoWorld!=null)MmoLeave();else{ShutdownMmo();screen=Screen.Lobby;}}
                RuneFrame(new Rect(926,594,128,112),true);
                if(RuneButton(new Rect(932,599,116,24),"캐릭터 · 임무")){ReleaseDungeonCursor();mmoPanel="profile";}
                if(RuneButton(new Rect(932,625,116,24),"공동 사냥터"))OpenMmoWorld("frontier");
                if(RuneButton(new Rect(932,651,116,24),"위험 지대"))OpenMmoWorld("minefield");
                if(RuneButton(new Rect(932,677,116,24),"고대 유적"))OpenMmoWorld("ruins");
            }
            GUI.enabled=previous;
            DrawMmoMinimap();
            string error=squad?squadError:mmoError;
            if(!string.IsNullOrEmpty(error))BaseText(new Rect(265,552,700,25),error,13,runeGold,TextAnchor.MiddleCenter);
            if(self!=null&&self.hp<=0){
                RuneFrame(new Rect(438,475,405,62),true);
                BaseText(new Rect(450,482,381,46),squad?L.F("영웅 부활까지 {0:0.0}초\n마우스 · 터치로 360° 둘러보기",squadSnapshot.respawn_left):"전투 불능 · 잠시 후 부활합니다\n마우스 · 터치로 360° 둘러보기",14,runeText,TextAnchor.MiddleCenter);
            }
        }
    }
}

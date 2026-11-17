using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private float dungeonYaw=90,dungeonPitch=18,dungeonDistance=5.6f;
        private bool dungeonLooking;
        private int mmoLookTouchId=-1;
        private bool DungeonLookAllowed=>ready&&!busy&&screen==Screen.Mmo&&mmoWorld!=null&&mmoPanel.Length==0&&
            (!SquadModeActive||(SquadInBattle&&mmoConnected&&MmoSelf!=null));
        private void ReleaseDungeonCursor(bool keepSquadAutoLook=false){if(!keepSquadAutoLook)squadAutoLookPending=false;mmoLookTouchId=-1;dungeonLooking=false;Cursor.lockState=CursorLockMode.None;Cursor.visible=true;}
        private void UpdateDungeonLook()
        {
            bool playing=DungeonLookAllowed;
            if(!playing||!Application.isFocused){ClearMmoTarget();ReleaseDungeonCursor(squadAutoLookPending&&SquadInBattle&&MmoSelf!=null&&MmoSelf.hp>0);return;}
            var keyboard=Keyboard.current;var mouse=Mouse.current;
            if(keyboard!=null&&keyboard.escapeKey.wasPressedThisFrame){ClearMmoTarget();ReleaseDungeonCursor();return;}
            bool began=false;
            if(ConsumeSquadAutoLook(mouse!=null&&!Application.isMobilePlatform,Application.isFocused))
            {began=true;dungeonLooking=true;Cursor.lockState=CursorLockMode.Locked;Cursor.visible=false;}
            if(mouse!=null&&mouse.leftButton.wasPressedThisFrame&&MmoHeld(mmoField)&&!DungeonPointerBlocked(MmoUiPoint(mouse.position.ReadValue())))
            {began=!dungeonLooking;dungeonLooking=true;Cursor.lockState=CursorLockMode.Locked;Cursor.visible=false;}
            if(dungeonLooking&&Cursor.lockState!=CursorLockMode.Locked){ReleaseDungeonCursor();return;}
            if(dungeonLooking&&!began&&mouse!=null)
            {ApplyMmoLookDelta(mouse.delta.ReadValue(),false);}
            if(dungeonLooking&&mouse!=null)
                dungeonDistance=Mathf.Clamp(dungeonDistance-mouse.scroll.ReadValue().y*.003f,3.5f,8);
            UpdateMmoTouchLook();
        }
        private bool DungeonPointerBlocked(Vector2 point)=>point.y>=594||MmoNavigationPointer(point)||mmoPad.Contains(point)||mmoAttackButton.Contains(point)||mmoDodgeButton.Contains(point)||mmoSkill1Button.Contains(point)||mmoSkill2Button.Contains(point);
        private bool DungeonMouseAttack=>dungeonLooking&&Mouse.current!=null&&Mouse.current.leftButton.isPressed;
        private void DrawDungeonThirdPersonField()
        {
            GUI.BeginGroup(mmoField);
            GUI.DrawTexture(new Rect(0,0,mmoField.width,mmoField.height),retroScene.View,ScaleMode.StretchToFill,false);
            DrawMmoCombatFeedback();
            if(mmoWorld.enemies!=null)foreach(var enemy in mmoWorld.enemies)if(enemy.hp>0&&retroScene.Project(enemy.x,enemy.y,enemy.kind=="base"?3.2f:SquadModeActive&&StrategyBuildingKind(enemy.kind)?2.5f:enemy.kind=="boss"?2.1f:1.35f,out var point))
            {
                if(SquadModeActive&&MmoSelf!=null&&new Vector2(enemy.x-MmoSelf.x,enemy.y-MmoSelf.y).sqrMagnitude>1000*1000)continue;
                if(point.x<0||point.x>mmoField.width||point.y<0||point.y>mmoField.height)continue;
                Fill(new Rect(point.x-38,point.y-7,76,6),new Color(.12f,.10f,.18f,.9f));
                Fill(new Rect(point.x-38,point.y-7,76*Mathf.Clamp01(enemy.hp/enemy.max_hp),6),new Color(1,.46f,.30f));
                BaseText(new Rect(point.x-90,point.y-30,180,20),SquadModeActive&&StrategyBuildingKind(enemy.kind)?StrategyKind(enemy.kind):enemy.name,12,Color.white,TextAnchor.MiddleCenter);
            }
            if(mmoWorld.players!=null)foreach(var actor in mmoWorld.players)if(actor.hp>0&&actor.id!=mmoWorld.you_id&&retroScene.Project(actor.x,actor.y,1.4f,out var point))
                BaseText(new Rect(point.x-85,point.y-28,170,22),actor.name,12,baseCyan,TextAnchor.MiddleCenter);
            for(int i=mmoActiveEffects.Count-1;i>=0;i--)
            {
                var effect=mmoActiveEffects[i];float age=Time.realtimeSinceStartup-effect.started;
                if(age>=.8f){mmoActiveEffects.RemoveAt(i);continue;}
                if(effect.effect.kind=="damage"||effect.effect.kind=="player_damage")continue;
                if(retroScene.Project(effect.effect.x,effect.effect.y,1.1f,out var point))BaseText(new Rect(point.x-70,point.y-45-age*35,140,25),effect.effect.text,16,baseGold,TextAnchor.MiddleCenter);
            }
            DrawMmoNavigation();

            BaseText(new Rect(14,mmoField.height-31,1100,23),dungeonLooking?"WASD 이동 · 좌클릭 공격 · Q/E 스킬 · Shift 회피 · Esc 해제":"화면 클릭 · 마우스로 시점 회전  |  터치 · 오른쪽 화면 드래그",13,Color.white);
            if(MmoSelf!=null&&MmoSelf.hit_flash>0)
            {var hit=new Color(1,.25f,.16f,.45f);Fill(new Rect(0,0,mmoField.width,6),hit);Fill(new Rect(0,mmoField.height-6,mmoField.width,6),hit);}
            GUI.EndGroup();
        }
    }
}

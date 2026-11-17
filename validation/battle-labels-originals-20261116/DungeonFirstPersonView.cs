using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private float dungeonYaw=RetroFantasyScene.QuarterYaw,dungeonPitch=35.264f,dungeonDistance=5.6f;
        private bool dungeonLooking;
        private int mmoLookTouchId=-1;
        private bool DungeonLookAllowed=>!SquadPauseBlocked&&ready&&!busy&&screen==Screen.Mmo&&mmoWorld!=null&&mmoPanel.Length==0&&
            (!SquadModeActive||(SquadInBattle&&mmoConnected&&MmoSelf!=null));
        private void ReleaseDungeonCursor(bool keepSquadAutoLook=false){if(!keepSquadAutoLook)squadAutoLookPending=false;mmoLookTouchId=-1;dungeonLooking=false;Cursor.lockState=CursorLockMode.None;Cursor.visible=true;}
        private void UpdateDungeonLook()
        {
            if(RtsActive){UpdateRtsInput();if(!rtsFirstPerson)return;}
            ReleaseDungeonCursor();
            dungeonYaw=RetroFantasyScene.QuarterYaw;dungeonPitch=35.264f;
            if(!DungeonLookAllowed||!Application.isFocused)return;
            var mouse=Mouse.current;
            if(mouse!=null){var point=MmoUiPoint(mouse.position.ReadValue());if(mmoField.Contains(point)&&!DungeonPointerBlocked(point))dungeonDistance=Mathf.Clamp(dungeonDistance-mouse.scroll.ReadValue().y*.003f,3.5f,8);}
        }
        private bool DungeonPointerBlocked(Vector2 point)=>point.y>=594||MmoNavigationPointer(point)||mmoPad.Contains(point)||mmoAttackButton.Contains(point)||mmoDodgeButton.Contains(point)||mmoSkill1Button.Contains(point)||mmoSkill2Button.Contains(point);
        private bool DungeonMouseAttack=>DungeonLookAllowed&&Mouse.current!=null&&Mouse.current.leftButton.isPressed&&mmoField.Contains(MmoUiPoint(Mouse.current.position.ReadValue()))&&!DungeonPointerBlocked(MmoUiPoint(Mouse.current.position.ReadValue()));
        private void DrawDungeonThirdPersonField()
        {
            GUI.BeginGroup(mmoField);
            GUI.DrawTexture(new Rect(0,0,mmoField.width,mmoField.height),retroScene.View,ScaleMode.StretchToFill,false);
            DrawMmoCombatFeedback();
            if(mmoWorld.enemies!=null)foreach(var enemy in mmoWorld.enemies)if(enemy.hp>0&&retroScene.Project(enemy.x,enemy.y,enemy.kind=="base"?3.2f:enemy.kind=="boss"?2.1f:1.35f,out var point))
            {
                if(!(RtsActive&&!rtsFirstPerson)&&SquadModeActive&&MmoSelf!=null&&new Vector2(enemy.x-MmoSelf.x,enemy.y-MmoSelf.y).sqrMagnitude>1000*1000)continue;
                if(point.x<0||point.x>mmoField.width||point.y<0||point.y>mmoField.height)continue;
                Fill(new Rect(point.x-38,point.y-7,76,6),new Color(.12f,.10f,.18f,.9f));
                Fill(new Rect(point.x-38,point.y-7,76*Mathf.Clamp01(enemy.hp/enemy.max_hp),6),new Color(1,.46f,.30f));
                BaseText(new Rect(point.x-90,point.y-30,180,20),enemy.name,12,Color.white,TextAnchor.MiddleCenter);
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

            BaseText(new Rect(14,mmoField.height-31,1100,23),(RtsActive&&!rtsFirstPerson)?"WASD 이동 · 마우스 조준 · 좌클릭 공격 · Q/E 스킬 · 휠 확대/축소":dungeonLooking?"WASD 이동 · 좌클릭 공격 · Q/E 스킬 · Shift 회피 · Esc 일시정지":"쿼터 뷰 · WASD 이동 · 마우스/터치 조준 · 좌클릭 공격 · 휠 확대/축소",13,Color.white);
            if(MmoSelf!=null&&MmoSelf.hit_flash>0)
            {var hit=new Color(1,.25f,.16f,.45f);Fill(new Rect(0,0,mmoField.width,6),hit);Fill(new Rect(0,mmoField.height-6,mmoField.width,6),hit);}
            GUI.EndGroup();
        }
    }
}

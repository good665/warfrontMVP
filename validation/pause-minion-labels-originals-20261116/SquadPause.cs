using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private bool? squadPauseIntent;
        private bool SquadPauseBlocked=>SquadModeActive&&SquadInBattle&&
            (squadSnapshot.paused||squadPauseIntent.HasValue);
        private void ClearSquadPauseInput()
        {
            ResetRtsIntents();ReleaseDungeonCursor();ClearMmoTarget();
            mmoDodge=mmoSkill1=mmoSkill2=false;squadRetry=null;
            
        }
        private void RequestSquadPause()
        {
            if(!SquadInBattle||squadExit||squadPauseIntent.HasValue)return;
            if(squadSnapshot.paused&&squadSnapshot.paused_by!=squadSnapshot.you_id)return;
            if(!squadSnapshot.paused&&!SquadVsComputer&&squadSnapshot.pause_remaining<=0)
            {squadError="이번 경기의 일시정지 3회를 모두 사용했습니다.";return;}
            squadPauseIntent=!squadSnapshot.paused;
            ClearSquadPauseInput();
        }
        private void UpdateSquadPause()
        {
            if(!SquadInBattle){squadPauseIntent=null;return;}
            if(Application.isFocused&&mmoPanel.Length==0&&Keyboard.current!=null&&Keyboard.current.escapeKey.wasPressedThisFrame)
                RequestSquadPause();
            if(squadPauseIntent.HasValue&&!squadRequest)SendSquadPause(squadPauseIntent.Value);
        }
        private async void SendSquadPause(bool value)
        {
            int generation=squadGeneration;var client=api;string code=squadSnapshot.code;
            squadRequest=true;
            try
            {
                var state=await client.SquadPauseAsync(code,value);
                if(SquadCurrent(generation,client))SquadApply(state);
            }
            catch(System.Exception error)
            {
                if(SquadCurrent(generation,client))
                {
                    var apiError=error as ApiException;
                    squadError=apiError?.Code=="squad_pause_limit"?"이번 경기의 일시정지 3회를 모두 사용했습니다.":
                        apiError?.Code=="squad_pause_owner"?"상대가 일시정지했습니다. 상대가 재개할 때까지 기다려 주세요.":
                        "일시정지 상태를 확인하지 못했습니다. ESC를 눌러 다시 시도해 주세요.";
                    squadNext=0;
                }
            }
            finally
            {
                if(SquadCurrent(generation,client)){squadPauseIntent=null;squadRequest=false;}
            }
        }
        private void DrawSquadPause()
        {
            if(!SquadInBattle)return;
            string remaining=SquadVsComputer?"횟수 제한 없음":$"남은 횟수 {squadSnapshot.pause_remaining}/3";
            bool previous=GUI.enabled;
            if(!SquadPauseBlocked)
            {
                GUI.enabled=previous&&!squadExit&&mmoPanel.Length==0;
                if(MmoButton(new Rect(770,540,270,38),"일시정지 [ESC] · "+remaining))RequestSquadPause();
                GUI.enabled=previous;
                if(squadError.Length>0)BaseText(new Rect(370,554,590,32),squadError,13,baseGold);
                return;
            }
            Fill(new Rect(0,0,1280,720),new Color(.02f,.025f,.04f,.8f));
            bool owner=squadSnapshot.paused_by==squadSnapshot.you_id;
            string title=squadPauseIntent.HasValue?"서버 확인 중…":owner?"일시정지":"상대가 일시정지했습니다";
            BaseText(new Rect(280,240,720,60),title,36,baseText,TextAnchor.MiddleCenter);
            BaseText(new Rect(280,308,720,40),remaining,20,baseGold,TextAnchor.MiddleCenter);
            BaseText(new Rect(240,354,800,40),owner?"ESC를 다시 누르면 경기를 재개합니다.":"일시정지한 플레이어가 재개할 때까지 기다려 주세요.",18,baseMuted,TextAnchor.MiddleCenter);
            GUI.enabled=previous&&owner&&!squadPauseIntent.HasValue&&!squadExit;
            if(MmoButton(new Rect(490,420,300,52),"경기 재개 [ESC]"))RequestSquadPause();
            GUI.enabled=previous&&!squadRequest&&!squadExit;
            if(MmoButton(new Rect(490,486,300,44),"항복 · 마을로"))SquadLeave(true);
            GUI.enabled=previous;
        }
    }
}

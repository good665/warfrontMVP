using System;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private SquadSnapshot squadSnapshot;
        private bool squadMode,squadRequest,squadExit,squadReturnTown;
        private int squadGeneration,squadSequence,squadSavedRole;
        private float squadNext;
        private string squadCode="",squadError="";
        private SquadInput squadRetry;
        private MmoProfile squadSavedProfile;
        private bool SquadModeActive=>squadMode;
        private bool SquadVsComputer=>squadSnapshot?.mode=="computer";
        private bool SquadInBattle=>squadMode&&squadSnapshot?.status=="active"&&squadSnapshot.world!=null&&!string.IsNullOrEmpty(squadSnapshot.world.you_id);
        private void OpenSquadLobby()
        {
            if(!ready||squadMode||mmoRequest)return;
            squadSavedProfile=mmoProfile;squadSavedRole=mmoRole;
            squadMode=true;screen=Screen.Mmo;mmoWorld=null;mmoConnected=false;mmoPanel="";
            ResetRtsIntents();squadSnapshot=null;squadRetry=null;squadSequence=0;squadError="";squadNext=0;
            ClearMmoTarget();ReleaseDungeonCursor();++squadGeneration;
            SquadRequest(c=>c.SquadCurrentAsync());
        }
        private bool SquadCurrent(int generation,ApiClient client)=>this!=null&&squadMode&&generation==squadGeneration&&api==client;
        private void SquadApply(SquadSnapshot state)
        {
            if(state==null||string.IsNullOrEmpty(state.status))throw new ApiException(0,"invalid_response");
            bool gameState=state.status=="active"||state.status=="finished";
            if(gameState&&(state.world==null||string.IsNullOrEmpty(state.world.you_id)))throw new ApiException(0,"invalid_response");
            bool wasActive=SquadInBattle,wasAlive=MmoSelf!=null&&(MmoSelf.hp>0||RtsActive);
            string previousCode=squadSnapshot?.code,previousPlayer=mmoWorld?.you_id;
            // JsonUtility can instantiate inline serializable objects for JSON null.
            // The authoritative room status decides whether a world exists.
            if(!gameState)state.world=null;
            if(squadSnapshot?.code!=state.code||state.status=="none")ResetRtsIntents();
            if(squadSnapshot?.code!=state.code||state.status!="active")squadPauseIntent=null;
            if(state.paused){ClearSquadPauseInput();}
            squadSnapshot=state;
            if(state.world!=null){MmoApply(state.world);squadSequence=Math.Max(squadSequence,state.world.last_sequence);}
            else {mmoWorld=null;mmoConnected=false;}
            if(state.status!="active"){mmoConnected=false;ClearMmoTarget();ReleaseDungeonCursor();}
            ObserveSquadLookTransition(wasActive,wasAlive,previousCode,previousPlayer);
            squadError="";
        }
        private async void SquadRequest(Func<ApiClient,Task<SquadSnapshot>> request)
        {
            if(squadRequest||!squadMode)return;
            int generation=squadGeneration;var client=api;squadRequest=true;squadNext=Time.realtimeSinceStartup+.2f;
            try {var state=await request(client);if(SquadCurrent(generation,client))SquadApply(state);}
            catch(Exception e){if(SquadCurrent(generation,client)){SquadRecoverError(e);squadNext=Time.realtimeSinceStartup+1;}}
            finally {if(SquadCurrent(generation,client))squadRequest=false;}
        }
        private string SquadError(Exception error)
        {
            if(error is ApiException e)
            {
                if(e.Code=="squad_room_not_found")return "방을 찾을 수 없습니다. 코드를 확인해 주세요.";
                if(e.Code=="squad_room_full")return "이미 두 명이 참가한 방입니다.";
                if(e.Code=="squad_already_in_match")return "진행 중인 경기를 다시 연결하고 있습니다.";
            }
            return "서버 연결을 확인해 주세요. 자동으로 다시 연결합니다.";
        }
        private void SquadRecoverError(Exception error)
        {
            mmoConnected=false;
            if(error is ApiException apiError&&(apiError.Code=="squad_room_not_found"||apiError.Code=="squad_not_member"))
            {
                ResetRtsIntents();squadRetry=null;mmoDodge=mmoSkill1=mmoSkill2=false;
                SquadApply(new SquadSnapshot{status="none"});
                squadError="경기 세션이 종료되었습니다. 새 상대를 찾거나 친구 방에 다시 참가해 주세요.";
                return;
            }
            squadError=SquadError(error);
        }


        // A tapped action bypasses movement polling, but never overtakes an in-flight request.
        private bool SquadSendReady(float now)=>!squadRequest&&(now>=squadNext||mmoDodge||mmoSkill1||mmoSkill2);
        private void UpdateSquad()
        {
            if(!squadMode)return;
            if(squadExit){if(!squadRequest)SquadLeave(squadReturnTown);return;}
            if(!Application.isFocused)SuspendMmoInput();else if(mmoSuspended){mmoSuspended=false;mmoConnected=false;squadNext=0;}
            UpdateSquadPause();
            if(SquadPauseBlocked){
                ClearSquadPauseInput();
                if(!squadRequest&&Time.realtimeSinceStartup>=squadNext)SquadRequest(c=>c.SquadStateAsync(squadSnapshot.code));
                return;
            }
            var k=Keyboard.current;
            bool controls=SquadInBattle&&mmoConnected&&!mmoSuspended&&mmoPanel.Length==0&&Time.realtimeSinceStartup-mmoLastResponse<1.2f&&MmoSelf!=null&&(MmoSelf.hp>0||RtsActive);
            if(controls&&k!=null)
            {
                mmoSkill1|=k.qKey.wasPressedThisFrame;rtsJump|=k.spaceKey.wasPressedThisFrame;
                mmoDodge|=(!RtsActive||rtsFirstPerson)&&(k.leftShiftKey.wasPressedThisFrame||k.rightShiftKey.wasPressedThisFrame);mmoSkill2|=k.eKey.wasPressedThisFrame;

            }
            if(!SquadSendReady(Time.realtimeSinceStartup))return;
            if(!SquadInBattle)
            {
                if(squadSnapshot?.status=="finished")return;
                SquadRequest(c=>squadSnapshot!=null&&!string.IsNullOrEmpty(squadSnapshot.code)?c.SquadStateAsync(squadSnapshot.code):c.SquadCurrentAsync());return;
            }
            if(squadRetry!=null)
            {
                if(!controls)
                {
                    squadRetry=PrepareSquadRetry(squadRetry,false);
                    mmoDodge=mmoSkill1=mmoSkill2=false;
                }
                SquadSend(squadRetry);return;
            }
            Vector2 move=Vector2.zero;
            if(controls&&k!=null){move.x=(k.dKey.isPressed||((!RtsActive||rtsFirstPerson)&&k.rightArrowKey.isPressed)?1:0)-(k.aKey.isPressed||((!RtsActive||rtsFirstPerson)&&k.leftArrowKey.isPressed)?1:0);move.y=(k.sKey.isPressed||((!RtsActive||rtsFirstPerson)&&k.downArrowKey.isPressed)?1:0)-(k.wKey.isPressed||((!RtsActive||rtsFirstPerson)&&k.upArrowKey.isPressed)?1:0);}
            if(controls&&MmoHeld(mmoPad))
            {
                Vector2 p=Mouse.current!=null?MmoUiPoint(Mouse.current.position.ReadValue()):mmoPad.center;
                if(Touchscreen.current!=null)foreach(var t in Touchscreen.current.touches)if(t.press.isPressed&&mmoPad.Contains(MmoUiPoint(t.position.ReadValue())))p=MmoUiPoint(t.position.ReadValue());
                move=(p-mmoPad.center)/Mathf.Max(1,Mathf.Min(mmoPad.width,mmoPad.height)*.42f);
            }
            move=DungeonFirstPersonMath.Move(Vector2.ClampMagnitude(move,1),RtsActive&&!rtsFirstPerson?0:dungeonYaw);
            var self=MmoSelf;var aim=MmoTargetAim(new Vector2(self?.x??0,self?.y??0)+DungeonFirstPersonMath.Forward(dungeonYaw)*800);
            var input=new SquadInput {sequence=++squadSequence,move_x=move.x,move_y=move.y,aim_x=aim.x,aim_y=aim.y,attack=controls&&(MmoHeld(mmoAttackButton)||DungeonMouseAttack),dodge=controls&&mmoDodge,skill1=controls&&mmoSkill1,skill2=controls&&mmoSkill2,character=rtsCharacter,jump=controls&&rtsJump};
            rtsJump=false;
            if(RtsActive)ApplyRtsInput(input,controls);
            mmoDodge=mmoSkill1=mmoSkill2=false;
            SquadSend(input);
        }
        private async void SquadSend(SquadInput input)
        {
            if(squadRequest)return;
            int generation=squadGeneration;var client=api;string code=squadSnapshot.code;squadRequest=true;squadRetry=input;squadNext=Time.realtimeSinceStartup+.05f;
            try {var state=await client.SquadInputAsync(code,input);if(SquadCurrent(generation,client)){SquadApply(state);squadRetry=null;}}
            catch(Exception e){if(SquadCurrent(generation,client)){SquadRecoverError(e);squadNext=Time.realtimeSinceStartup+1;}}
            finally {if(SquadCurrent(generation,client))squadRequest=false;}
        }
        private async void SquadLeave(bool town)
        {
            if(!squadMode)return;squadExit=true;squadReturnTown=town;ReleaseDungeonCursor();mmoConnected=false;
            if(squadRequest)return;
            int generation=squadGeneration;var client=api;squadRequest=true;
            try
            {
                await client.SquadLeaveAsync();
                if(!SquadCurrent(generation,client))return;
                ShutdownSquad();screen=town?Screen.Lobby:Screen.Mmo;
                if(!town)OpenSquadLobby();
            }
            catch(Exception e){if(SquadCurrent(generation,client)){squadExit=false;squadError=SquadError(e);}}
            finally {if(SquadCurrent(generation,client))squadRequest=false;}
        }
        private void ShutdownSquad()
        {
            ResetRtsIntents();
            if(!squadMode)return;
            ResetRtsIntents();++squadGeneration;squadMode=false;squadRequest=squadExit=false;squadSnapshot=null;squadRetry=null;
            mmoWorld=null;mmoConnected=false;mmoProfile=squadSavedProfile;mmoRole=squadSavedRole;mmoParty=null;mmoPanel="";mmoSequence=0;
            mmoDodge=mmoSkill1=mmoSkill2=false;ClearMmoTarget();ReleaseDungeonCursor();ResetMmoCombatFeedback();MmoClearEffects();mmoRenderActors.Clear();mmoMuzzleUntil.Clear();
        }

        private bool SquadOverlayPointer(Vector2 point)=>RtsActive&&new Rect(1200,8,30,30).Contains(point-mmoField.position);
        private SquadInput PrepareSquadRetry(SquadInput original,bool controls)
        {
            if(controls)return original;
            if(!string.IsNullOrEmpty(original.command)&&original.command!="none")
                return new SquadInput{sequence=original.sequence,unit_ids=original.unit_ids,command=original.command,order_x=original.order_x,order_y=original.order_y,target_id=original.target_id,aim_x=original.aim_x,aim_y=original.aim_y};
            return new SquadInput{sequence=++squadSequence,aim_x=MmoSelf?.x??0,aim_y=MmoSelf?.y??0};
        }
        private void DrawSquad()
        {
            Fill(new Rect(0,0,1280,720),new Color(.055f,.05f,.075f));
            if(mmoWorld!=null){DrawSquadBattle();return;}
            BaseText(new Rect(30,14,740,36),SquadVsComputer?"WARFRONT · 컴퓨터 RTS":"WARFRONT · 단일 전장 RTS",26,baseText);
            bool enabled=GUI.enabled;
            GUI.enabled=enabled&&!squadExit&&mmoPanel.Length==0;
            if(MmoButton(new Rect(975,18,125,36),"조작 설정"))OpenMmoControlSettings();
            if(MmoButton(new Rect(1110,18,140,36),SquadInBattle?"항복 · 마을":"마을로"))SquadLeave(true);
            GUI.enabled=enabled;
            BaseText(new Rect(30,56,790,28),SquadVsComputer?"컴퓨터 지휘관과 대전 · 같은 웨이브·부활 규칙 · 적 본진을 파괴하세요":"플레이어 대전 / 컴퓨터 대전 · 12간지 영웅과 직접 지휘하는 병력 · 적 본진을 파괴하세요",16,baseMuted);
            {
                Panel(mmoField);
                bool waiting=squadSnapshot?.status=="waiting";
                BaseText(new Rect(75,156,1100,40),waiting?"상대 플레이어를 기다리고 있습니다":"RTS · 출전 준비",27,baseText);
                BaseText(new Rect(75,208,1100,48),waiting?$"{squadSnapshot.members?.Length??0}/{squadSnapshot.capacity}명 · 정원이 모이면 시작합니다.":"컴퓨터와 바로 대전하거나, 다른 플레이어와 분대를 지휘해 싸우세요.",19,baseMuted);
                GUI.enabled=enabled&&!squadRequest&&!squadExit&&mmoPanel.Length==0;
                if(!waiting){if(MmoButton(new Rect(795,230,150,40),"1 : 1"))rtsTeamSize=1;if(MmoButton(new Rect(955,230,150,40),"2 : 2"))rtsTeamSize=2;}
                if(waiting)
                {
                    BaseText(new Rect(75,282,1100,55),"친구 방 코드  "+squadSnapshot.code,30,baseGold);
                    if(MmoButton(new Rect(75,370,330,55),"대기 취소"))SquadLeave(false);
                }
                else
                {
                    if(MmoButton(new Rect(75,285,330,64),$"자동 {rtsTeamSize} : {rtsTeamSize} 매칭"))SquadRequest(c=>c.SquadQueueAsync(rtsTeamSize));
                    if(MmoButton(new Rect(435,285,330,64),"친구 방 만들기"))SquadRequest(c=>c.SquadCreateAsync(rtsTeamSize));
                    if(MmoButton(new Rect(795,285,330,64),"컴퓨터와 대전"))SquadRequest(c=>c.SquadComputerAsync(rtsTeamSize));
                    squadCode=GUI.TextField(new Rect(75,380,330,48),squadCode,12);
                    if(MmoButton(new Rect(435,380,330,48),"코드로 참가")&&!string.IsNullOrWhiteSpace(squadCode))SquadRequest(c=>c.SquadJoinAsync(squadCode.Trim().ToUpperInvariant()));
                }
                if(MmoButton(new Rect(795,380,330,48),"마을로 가기"))SquadLeave(true);
                GUI.enabled=enabled;
                DrawRtsCharacterSelection(new Rect(75,445,1050,110));
            }
            BaseText(new Rect(30,590,1200,24),squadError.Length>0?squadError:squadExit?"경기 종료 요청 중…":squadRequest?"서버 확인 중…":"30초마다 거점에서 근접 3명·궁수 2명 출격",14,baseGold);
            if(squadSnapshot?.status=="finished")DrawSquadResult();
            if(mmoPanel=="controls")DrawMmoControlSettings();
        }
        private void DrawSquadResult()
        {
            Fill(mmoField,new Color(.03f,.04f,.08f,.9f));
            int winner=squadSnapshot.winner;
            bool draw=winner<0;
            bool win=winner==squadSnapshot.team;
            BaseText(new Rect(200,210,880,60),draw?"무승부":win?"승리":"패배",42,win?baseGold:baseText,TextAnchor.MiddleCenter);
            string reason=squadSnapshot.reason;
            string detail=reason=="headquarters_destroyed"||reason=="hq_destroyed"||reason=="base_destroyed"?"본진이 파괴되어 경기가 종료되었습니다.":reason=="surrender"||reason=="forfeit"?"항복으로 경기가 종료되었습니다.":reason=="disconnect"?"연결 종료로 경기가 종료되었습니다.":reason=="timeout"?"제한 시간이 종료되었습니다.":reason=="simultaneous_destruction"?"양측 본진이 동시에 파괴되었습니다.":"경기 종료 · "+reason;
            BaseText(new Rect(200,280,880,42),detail,20,baseMuted,TextAnchor.MiddleCenter);
            bool previous=GUI.enabled;GUI.enabled=previous&&!squadRequest&&!squadExit&&mmoPanel.Length==0;
            if(MmoButton(new Rect(340,365,280,58),"다시 출전"))SquadLeave(false);
            if(MmoButton(new Rect(660,365,280,58),"마을로 돌아가기"))SquadLeave(true);
            GUI.enabled=previous;
        }
    }
}

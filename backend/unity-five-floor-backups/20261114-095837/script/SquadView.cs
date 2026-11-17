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
        private string squadCode="",squadError="",squadOrder="none";
        private Vector2 squadOrderPoint;
        private string squadOrderTarget="";
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
            ResetStrategy();ResetSquadCharge();squadSnapshot=null;squadRetry=null;squadSequence=0;squadError="";squadNext=0;
            ClearMmoTarget();ReleaseDungeonCursor();++squadGeneration;
            SquadRequest(c=>c.SquadCurrentAsync());
        }
        private bool SquadCurrent(int generation,ApiClient client)=>this!=null&&squadMode&&generation==squadGeneration&&api==client;
        private void SquadApply(SquadSnapshot state)
        {
            if(state==null||string.IsNullOrEmpty(state.status))throw new ApiException(0,"invalid_response");
            bool gameState=state.status=="active"||state.status=="finished";
            if(gameState&&(state.world==null||string.IsNullOrEmpty(state.world.you_id)))throw new ApiException(0,"invalid_response");
            bool wasActive=SquadInBattle,wasAlive=MmoSelf!=null&&MmoSelf.hp>0;
            int previousFloor=squadSnapshot?.battle?.floor??0;
            string previousCode=squadSnapshot?.code,previousPlayer=mmoWorld?.you_id;
            // JsonUtility can instantiate inline serializable objects for JSON null.
            // The authoritative room status decides whether a world exists.
            if(!gameState)state.world=null;
            if(squadSnapshot?.code!=state.code||state.status=="none")ResetStrategy();
            if(squadSnapshot?.code!=state.code||state.status!="active")squadPauseIntent=null;
            if(state.paused){ClearSquadPauseInput();}
            squadSnapshot=state;
            ValidateStrategySelection();
            if(state.world!=null){MmoApply(state.world);squadSequence=Math.Max(squadSequence,state.world.last_sequence);}
            else {mmoWorld=null;mmoConnected=false;}
            if(state.battle?.five_floor==true&&state.status=="active"&&(!wasActive||!wasAlive&&MmoSelf!=null&&MmoSelf.hp>0||previousFloor!=state.battle.floor))
                dungeonYaw=previousFloor>0&&previousFloor!=state.battle.floor?(state.battle.floor>previousFloor?0:180):(state.battle.floor==1?0:180);
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
                ResetStrategy();squadRetry=null;squadOrder="none";mmoDodge=mmoSkill1=mmoSkill2=false;
                SquadApply(new SquadSnapshot{status="none"});
                squadError="경기 세션이 종료되었습니다. 새 상대를 찾거나 친구 방에 다시 참가해 주세요.";
                return;
            }
            squadError=SquadError(error);
        }
        private void SquadOrder(string command)
        {
            if(!SquadInBattle||mmoPanel.Length>0||MmoSelf==null||MmoSelf.hp<=0)return;
            squadOrder=command;squadOrderPoint=new Vector2(MmoSelf.x,MmoSelf.y);squadOrderTarget="";
            if(command=="focus"&&squadOrderTarget.Length==0&&squadSnapshot.bases!=null)
                foreach(var b in squadSnapshot.bases)if(b.team!=squadSnapshot.team)squadOrderTarget=b.id;
        }
        // A tapped action bypasses movement polling, but never overtakes an in-flight request.
        private bool SquadSendReady(float now)=>!squadRequest&&(now>=squadNext||mmoDodge||mmoSkill1||mmoSkill2||squadChargeRelease);
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
            bool controls=SquadInBattle&&mmoConnected&&!mmoSuspended&&mmoPanel.Length==0&&Time.realtimeSinceStartup-mmoLastResponse<1.2f&&MmoSelf!=null&&MmoSelf.hp>0;
            if(controls&&k!=null)
            {
                if(FiveFloorActive){mmoSkill1|=k.qKey.wasPressedThisFrame;fiveJump|=k.spaceKey.wasPressedThisFrame;if(k.fKey.wasPressedThisFrame)fivePortal=1;if(k.gKey.wasPressedThisFrame)fivePortal=-1;}
                mmoDodge|=k.leftShiftKey.wasPressedThisFrame||k.rightShiftKey.wasPressedThisFrame;mmoSkill2|=k.eKey.wasPressedThisFrame;

            }
            bool chargeHeld=!FiveFloorActive&&controls&&((k!=null&&k.qKey.isPressed)||MmoHeld(mmoSkill1Button));
            CaptureSquadCharge(chargeHeld,controls&&k!=null&&k.qKey.wasPressedThisFrame,controls);
            if(!FiveFloorActive)UpdateStrategyPointer();
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
                    mmoDodge=mmoSkill1=mmoSkill2=false;squadOrder="none";squadOrderTarget="";
                }
                SquadSend(squadRetry);return;
            }
            Vector2 move=Vector2.zero;
            if(controls&&k!=null){move.x=(k.dKey.isPressed||k.rightArrowKey.isPressed?1:0)-(k.aKey.isPressed||k.leftArrowKey.isPressed?1:0);move.y=(k.sKey.isPressed||k.downArrowKey.isPressed?1:0)-(k.wKey.isPressed||k.upArrowKey.isPressed?1:0);}
            if(controls&&MmoHeld(mmoPad))
            {
                Vector2 p=Mouse.current!=null?MmoUiPoint(Mouse.current.position.ReadValue()):mmoPad.center;
                if(Touchscreen.current!=null)foreach(var t in Touchscreen.current.touches)if(t.press.isPressed&&mmoPad.Contains(MmoUiPoint(t.position.ReadValue())))p=MmoUiPoint(t.position.ReadValue());
                move=(p-mmoPad.center)/Mathf.Max(1,Mathf.Min(mmoPad.width,mmoPad.height)*.42f);
            }
            move=DungeonFirstPersonMath.Move(Vector2.ClampMagnitude(move,1),dungeonYaw);
            var self=MmoSelf;var aim=MmoTargetAim(new Vector2(self?.x??0,self?.y??0)+DungeonFirstPersonMath.Forward(dungeonYaw)*800);
            if(squadChargeRelease)aim=squadChargeReleaseAim;
            var input=new SquadInput {sequence=++squadSequence,move_x=move.x,move_y=move.y,aim_x=aim.x,aim_y=aim.y,attack=controls&&((!FiveFloorActive&&k!=null&&k.spaceKey.isPressed)||MmoHeld(mmoAttackButton)||DungeonMouseAttack),dodge=controls&&mmoDodge,skill1=controls&&mmoSkill1,skill2=controls&&mmoSkill2,charge_held=controls&&squadChargeHeld,charge_release=controls&&squadChargeRelease,command=controls?squadOrder:"none",target_id=squadOrderTarget,order_x=squadOrderPoint.x,order_y=squadOrderPoint.y,economy=controls?strategyEconomy:"none",squad_id=strategySquad,formation=controls?strategyFormation:"none"};
            if(FiveFloorActive){input.character=fiveCharacter;input.portal_delta=controls?fivePortal:0;input.jump=controls&&fiveJump;input.replace_slot=fiveReplace;fivePortal=0;fiveJump=false;fiveReplace=-1;}else ConsumeStrategyIntent(input,controls);
            mmoDodge=mmoSkill1=mmoSkill2=false;squadChargeRelease=false;if(controls)squadOrder="none";
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
            ResetFiveIntents();
            if(!squadMode)return;
            ResetStrategy();ResetSquadCharge();++squadGeneration;squadMode=false;squadRequest=squadExit=false;squadSnapshot=null;squadRetry=null;squadOrder="none";
            mmoWorld=null;mmoConnected=false;mmoProfile=squadSavedProfile;mmoRole=squadSavedRole;mmoParty=null;mmoPanel="";mmoSequence=0;
            mmoDodge=mmoSkill1=mmoSkill2=false;ClearMmoTarget();ReleaseDungeonCursor();ResetMmoCombatFeedback();MmoClearEffects();mmoRenderActors.Clear();mmoMuzzleUntil.Clear();
        }

        private readonly Rect squadMap=new Rect(14,14,212,142);
        private bool SquadOverlayPointer(Vector2 point)
        {
            var local=point-mmoField.position;
            if(FiveFloorActive)return StrategyPointer(local)||new Rect(470,460,300,83).Contains(local)||new Rect(14,132,310,140).Contains(local)||new Rect(940,430,300,60).Contains(local)||new Rect(940,14,300,230).Contains(local)||new Rect(14,14,440,108).Contains(local);
            return SquadInBattle&&(StrategyPointer(local)||squadMap.Contains(local)||new Rect(14,162,225,94).Contains(local)||new Rect(970,80,252,112).Contains(local));
        }
        private string SquadCommandLabel(string command)=>command=="move"?"이동":command=="attack_move"?"공격 이동":command=="focus"?"집중 공격":command=="hold"?"위치 사수":command=="retreat"?"본진 후퇴":"영웅 집결";
        private void DrawSquad()
        {
            Fill(new Rect(0,0,1280,720),new Color(.055f,.05f,.075f));
            if(mmoWorld!=null){DrawSquadBattle();return;}
            BaseText(new Rect(30,14,740,36),SquadVsComputer?"WARFRONT · 컴퓨터 분대전":"WARFRONT · 분대 본진전",26,baseText);
            bool enabled=GUI.enabled;
            GUI.enabled=enabled&&!squadExit&&mmoPanel.Length==0;
            if(MmoButton(new Rect(975,18,125,36),"조작 설정"))OpenMmoControlSettings();
            if(MmoButton(new Rect(1110,18,140,36),SquadInBattle?"항복 · 마을":"마을로"))SquadLeave(true);
            GUI.enabled=enabled;
            BaseText(new Rect(30,56,790,28),SquadVsComputer?"컴퓨터 지휘관과 대전 · 같은 모집·부활 규칙 · 적 본진을 파괴하세요":"플레이어 대전 / 컴퓨터 대전 · 12간지 동물 영웅과 자동 미니언 · 적 본진을 파괴하세요",16,baseMuted);
            if(mmoWorld!=null)BaseText(new Rect(930,56,315,28),squadSnapshot.respawn_left>0?$"영웅 부활 {squadSnapshot.respawn_left:0.0}초":$"영웅 HP {MmoSelf?.hp??0:0}/{MmoSelf?.max_hp??160:0}",16,baseCyan);
            if(squadSnapshot?.bases!=null)
            {
                int i=0;foreach(var b in squadSnapshot.bases)
                {
                    float x=30+i++*600;Color color=b.team==squadSnapshot.team?baseCyan:new Color(1,.38f,.3f);
                    BaseText(new Rect(x,85,560,22),(b.team==squadSnapshot.team?"아군 본진":"적 본진")+$"  {b.hp:0} / {b.max_hp:0}",15,color);
                    Fill(new Rect(x,111,560,8),new Color(.15f,.16f,.2f));Fill(new Rect(x,111,560*Mathf.Clamp01(b.hp/Mathf.Max(1,b.max_hp)),8),color);
                }
            }
            if(mmoWorld!=null)DrawMmoField();
            else
            {
                Panel(mmoField);
                bool waiting=squadSnapshot?.status=="waiting";
                BaseText(new Rect(75,156,1100,40),waiting?"상대 플레이어를 기다리고 있습니다":"분대전 · 출전 준비",27,baseText);
                BaseText(new Rect(75,208,1100,48),waiting?"플레이어 대전은 두 명이 모이면 경기가 자동으로 시작됩니다.":"컴퓨터와 바로 대전하거나, 다른 플레이어와 분대를 지휘해 싸우세요.",19,baseMuted);
                GUI.enabled=enabled&&!squadRequest&&!squadExit&&mmoPanel.Length==0;
                if(waiting)
                {
                    BaseText(new Rect(75,282,1100,55),"친구 방 코드  "+squadSnapshot.code,30,baseGold);
                    if(MmoButton(new Rect(75,370,330,55),"대기 취소"))SquadLeave(false);
                }
                else
                {
                    if(MmoButton(new Rect(75,285,330,64),"자동 1 대 1 매칭"))SquadRequest(c=>c.SquadQueueAsync());
                    if(MmoButton(new Rect(435,285,330,64),"친구 방 만들기"))SquadRequest(c=>c.SquadCreateAsync());
                    if(MmoButton(new Rect(795,285,330,64),"컴퓨터와 대전"))SquadRequest(c=>c.SquadComputerAsync());
                    squadCode=GUI.TextField(new Rect(75,380,330,48),squadCode,12);
                    if(MmoButton(new Rect(435,380,330,48),"코드로 참가")&&!string.IsNullOrWhiteSpace(squadCode))SquadRequest(c=>c.SquadJoinAsync(squadCode.Trim().ToUpperInvariant()));
                }
                if(MmoButton(new Rect(795,380,330,48),"마을로 가기"))SquadLeave(true);
                GUI.enabled=enabled;
                DrawFiveFloorSelection(new Rect(75,445,1050,110));
            }
            if(SquadInBattle)
            {
                GUI.enabled=enabled&&mmoConnected&&mmoPanel.Length==0&&MmoSelf!=null&&MmoSelf.hp>0;
                GUI.Box(mmoPad,"이동\nWASD");GUI.Box(mmoAttackButton,"활 발사\nSPACE / 누르기");
                if(MmoButton(mmoDodgeButton,$"회피 Shift\n{MmoSelf?.dodge_cooldown??0:0.0}s"))mmoDodge=true;
                GUI.Box(mmoSkill1Button,(MmoSelf?.skill1_cooldown??0)>0?$"차지샷 Q\n{MmoSelf.skill1_cooldown:0.0}s":"차지샷 Q\n길게 누른 뒤 놓기");
                if(MmoButton(mmoSkill2Button,$"폭탄 E\n{MmoSelf?.skill2_cooldown??0:0.0}s"))mmoSkill2=true;
                GUI.enabled=enabled;
            }
            DrawSquadChargeGauge();
            BaseText(new Rect(30,590,1200,24),squadError.Length>0?squadError:squadExit?"경기 종료 요청 중…":squadRequest&&!SquadInBattle?"서버 확인 중…":SquadInBattle?"Space / 좌클릭 활 14m · Q 길게 눌러 충전 후 놓기 · Shift 회피 · E 폭탄":"",14,baseGold);
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
        private Vector2 SquadMapPoint(float x,float y)=>new Vector2(squadMap.x+8+x/Mathf.Max(1,mmoWorld?.world_width??3600)*(squadMap.width-16),squadMap.y+8+y/Mathf.Max(1,mmoWorld?.world_height??2400)*(squadMap.height-16));
        private void DrawSquadNavigation()
        {
            if(FiveFloorActive){DrawFiveFloorNavigation();return;}
            if(squadSnapshot==null||mmoWorld==null)return;
            if(retroScene!=null)retroScene.StrategyObjectives(squadSnapshot);
            Fill(squadMap,new Color(.03f,.05f,.08f,.9f));
            DrawStrategyFog();
            if(mmoWorld.obstacles!=null)foreach(var obstacle in mmoWorld.obstacles)
            {
                var p=SquadMapPoint(obstacle.x,obstacle.y);var far=SquadMapPoint(obstacle.x+obstacle.width,obstacle.y+obstacle.height);
                Fill(new Rect(p.x,p.y,far.x-p.x,far.y-p.y),new Color(.35f,.4f,.48f));
            }
            if(squadSnapshot.camps!=null)foreach(var camp in squadSnapshot.camps){var p=SquadMapPoint(camp.x,camp.y);Fill(new Rect(p.x-5,p.y-5,10,10),camp.team==squadSnapshot.team?new Color(.2f,.7f,.4f):new Color(.8f,.45f,.2f));}
            if(squadSnapshot.bases!=null)foreach(var b in squadSnapshot.bases){var p=SquadMapPoint(b.x,b.y);Fill(new Rect(p.x-6,p.y-6,12,12),b.team==squadSnapshot.team?baseCyan:new Color(1,.3f,.2f));}
            if(mmoWorld.players!=null)foreach(var a in mmoWorld.players)if(a.hp>0){var p=SquadMapPoint(a.x,a.y);Fill(new Rect(p.x-2,p.y-2,4,4),a.id==mmoWorld.you_id?Color.white:baseCyan);}
            if(mmoWorld.enemies!=null)foreach(var e in mmoWorld.enemies)if(e.hp>0&&e.kind!="base"){var p=SquadMapPoint(e.x,e.y);Fill(new Rect(p.x-2,p.y-2,4,4),new Color(1,.3f,.2f));}
            Fill(new Rect(14,162,225,94),new Color(.03f,.05f,.08f,.87f));
            BaseText(new Rect(22,166,210,24),squadSnapshot.recruited?"목표 · 적 본진 파괴":"목표 · 아군 야영지로 이동",14,baseGold);
            BaseText(new Rect(22,191,210,24),squadSnapshot.respawn_left>0?$"영웅 부활 {squadSnapshot.respawn_left:0.0}초":"명령 · "+SquadCommandLabel(squadSnapshot.command),13,baseText);
            int alive=0;if(squadSnapshot.roster!=null)foreach(var r in squadSnapshot.roster)if(r.hp>0)alive++;
            BaseText(new Rect(22,218,210,30),$"동료 {alive}/3 · 야영지에서 충원",12,baseMuted);
            Fill(new Rect(970,80,252,112),new Color(.03f,.05f,.08f,.87f));
            if(squadSnapshot.roster!=null)
            {
                int row=0;foreach(var r in squadSnapshot.roster)
                {
                    string role=r.kind=="guard"?"수호병":r.kind=="archer"?"궁수":r.kind=="healer"?"치유사":r.kind;
                    string status=r.hp>0?$"{r.hp:0}/{r.max_hp:0}":r.respawn_left>0?$"충원 대기 {r.respawn_left:0}초":"야영지에서 합류";
                    BaseText(new Rect(980,86+row++*30,232,26),role+" · "+status,13,r.hp>0?baseCyan:baseMuted);
                }
            }
            bool previous=GUI.enabled;GUI.enabled=previous&&SquadInBattle&&mmoConnected&&mmoPanel.Length==0&&MmoSelf!=null&&MmoSelf.hp>0;
            
            GUI.enabled=previous;
            if(retroScene!=null&&squadSnapshot.camps!=null)foreach(var camp in squadSnapshot.camps)
                if(retroScene.Project(camp.x,camp.y,2.2f,out var point)&&point.x>240&&point.x<mmoField.width-270&&point.y>75&&point.y<mmoField.height-100&&!StrategyPointer(point))
                    BaseText(new Rect(point.x-140,point.y-22,280,24),camp.team==squadSnapshot.team?"아군 야영지 · 동료 합류 / 충원":"적 야영지",13,camp.team==squadSnapshot.team?baseCyan:baseGold,TextAnchor.MiddleCenter);
        }
    }
}




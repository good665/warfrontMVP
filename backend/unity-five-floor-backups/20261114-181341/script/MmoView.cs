using System;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private MmoSnapshot mmoWorld;
        private MmoProfile mmoProfile;
        private MmoParty mmoParty;
        private int mmoGeneration, mmoSequence, mmoRole;
        private bool mmoRequest, mmoConnected, mmoSuspended;
        private float mmoNextSend, mmoLastResponse;
        private string mmoError = "", mmoPanel = "", mmoCode = "";
        private string mmoSelectedZone = "frontier";
        private Vector2 mmoInventoryScroll;
        private bool mmoDodge, mmoSkill1, mmoSkill2;
        private Texture2D mmoAtlas;
        private Action mmoPendingAction;
        private readonly System.Collections.Generic.Dictionary<string,float> mmoMuzzleUntil = new System.Collections.Generic.Dictionary<string,float>();
        private sealed class MmoFloatingEffect { public MmoEffect effect; public float started; }
        private readonly System.Collections.Generic.HashSet<string> mmoSeenEffects = new System.Collections.Generic.HashSet<string>();
        private readonly System.Collections.Generic.Queue<string> mmoEffectOrder = new System.Collections.Generic.Queue<string>();
        private readonly System.Collections.Generic.List<MmoFloatingEffect> mmoActiveEffects = new System.Collections.Generic.List<MmoFloatingEffect>();
        private sealed class MmoRenderActor {public Vector2 position;public int frame;}
        private readonly System.Collections.Generic.Dictionary<string,MmoRenderActor> mmoRenderActors=new System.Collections.Generic.Dictionary<string,MmoRenderActor>();
        private readonly Rect mmoField = new Rect(20, 14, 1240, 572);
        private Rect mmoPad => MmoControlRect(0);
        private Rect mmoAttackButton => MmoControlRect(2);
        private Rect mmoDodgeButton => MmoControlRect(3);
        private Rect mmoSkill1Button => MmoControlRect(4);
        private Rect mmoSkill2Button => MmoControlRect(5);

        private MmoActor MmoSelf
        {
            get { if (mmoWorld?.players != null) foreach (var a in mmoWorld.players) if (a.id == mmoWorld.you_id) return a; return null; }
        }
        private Vector2 MmoCamera
        {
            get { var a=MmoSelf;var position=a==null?new Vector2(620,230):MmoRenderPosition("mmo-player:"+a.id,a.x,a.y); return new Vector2(Mathf.Clamp(position.x-mmoField.width/2,0,Mathf.Max(0,(mmoWorld?.world_width ?? 3600)-mmoField.width)), Mathf.Clamp(position.y-mmoField.height/2,0,Mathf.Max(0,(mmoWorld?.world_height ?? 2400)-mmoField.height))); }
        }
        private Vector2 MmoUiPoint(Vector2 p) => new Vector2((p.x-UiOrigin.x)/Mathf.Max(.01f,UiScale),(UnityEngine.Screen.height-p.y-UiOrigin.y)/Mathf.Max(.01f,UiScale));
        private bool MmoHeld(Rect r)
        {
            if (Touchscreen.current != null) foreach(var t in Touchscreen.current.touches) if(t.press.isPressed && r.Contains(MmoUiPoint(t.position.ReadValue()))) return true;
            return Mouse.current != null && Mouse.current.leftButton.isPressed && r.Contains(MmoUiPoint(Mouse.current.position.ReadValue()));
        }
        private async void OpenMmoWorld(string zone)
        {
            if(RetiredWorldEntry())return;
            if(SquadModeActive)return;
            if (!ready) return;
            if(mmoRequest){mmoPendingAction=()=>OpenMmoWorld(zone);return;}
            ClearMmoTarget();
            mmoSelectedZone=zone;
            screen=Screen.Mmo; mmoPanel=""; mmoError="전장에 연결 중…";
            int generation=++mmoGeneration; mmoRequest=true; mmoConnected=false;
            var client=api;
            try { var state=await client.MmoEnterAsync(zone,mmoProfile != null ? mmoProfile.role : mmoRole); if(!MmoCurrent(generation,client))return; MmoApply(state); }
            catch(Exception e) { if(MmoCurrent(generation,client)) mmoError=MmoError(e); }
            finally { if(MmoCurrent(generation,client)) mmoRequest=false; }
        }
        private bool MmoCurrent(int generation, ApiClient client) => this != null && generation==mmoGeneration && client==api && screen==Screen.Mmo;
        private void MmoApply(MmoSnapshot state)
        {
            if(state==null || state.profile==null || state.players==null || string.IsNullOrEmpty(state.you_id)) throw new ApiException(0,"invalid_response");
            if(mmoWorld!=null && (mmoWorld.zone!=state.zone || mmoWorld.instance_id!=state.instance_id)){ClearMmoTarget();ResetMmoCombatFeedback();MmoClearEffects();mmoRenderActors.Clear();}
            var liveKeys=new System.Collections.Generic.HashSet<string>();
            foreach(var actor in state.players)liveKeys.Add("mmo-player:"+actor.id);
            if(state.enemies!=null)foreach(var enemy in state.enemies)liveKeys.Add("mmo-enemy:"+enemy.id);
            foreach(var key in new System.Collections.Generic.List<string>(mmoRenderActors.Keys))if(!liveKeys.Contains(key))mmoRenderActors.Remove(key);
            if(state.effects!=null)foreach(var effect in state.effects)
            {
                if(string.IsNullOrEmpty(effect.id) || !mmoSeenEffects.Add(effect.id))continue;
                mmoEffectOrder.Enqueue(effect.id);
                while(mmoEffectOrder.Count>256)mmoSeenEffects.Remove(mmoEffectOrder.Dequeue());
                if(mmoActiveEffects.Count>=64)mmoActiveEffects.RemoveAt(0);
                mmoActiveEffects.Add(new MmoFloatingEffect {effect=effect,started=Time.realtimeSinceStartup});
            }
            foreach(var actor in state.players)
            {
                float old=0; if(mmoWorld?.players!=null)foreach(var previous in mmoWorld.players)if(previous.id==actor.id){old=previous.attack_cooldown;break;}
                if(actor.attack_cooldown>old+.05f)mmoMuzzleUntil[actor.id]=Time.realtimeSinceStartup+.14f;
            }
            if(mmoMuzzleUntil.Count>64)mmoMuzzleUntil.Clear();
            MmoApplyCombatFeedback(mmoWorld,state);if(!SquadModeActive)MmoObserveLoot(mmoProfile,state.profile);
            mmoWorld=state; mmoProfile=state.profile; mmoParty=state.party; mmoRole=state.profile.role;
            mmoSequence=Math.Max(mmoSequence,state.last_sequence); mmoLastResponse=Time.realtimeSinceStartup; mmoConnected=true; mmoError="";
        }
        private string MmoError(Exception e)
        {
            if(!(e is ApiException error))return "연결을 확인한 뒤 다시 시도해 주세요";
            switch(error.Code)
            {
                case "mmo_insufficient_gold": return "골드가 부족합니다. 적을 처치하거나 임무 보상을 받아 주세요";
                case "mmo_upgrade_max": return "이미 최고 강화 단계입니다";
                case "mmo_quest_not_ready": return "임무 목표를 완료한 뒤 보상을 받아 주세요";
                case "mmo_party_not_found": return "파티를 찾을 수 없습니다. 초대 코드를 확인해 주세요";
                case "mmo_party_full": return "파티가 가득 찼습니다. 최대 4명까지 참가할 수 있습니다";
                case "mmo_already_in_party": return "이미 파티에 참가 중입니다. 현재 파티에서 나간 뒤 다시 시도해 주세요";
                case "mmo_zone_full": return "전장이 가득 찼습니다. 잠시 후 다시 입장해 주세요";
                case "mmo_not_in_world": return "전장에 다시 연결하고 있습니다";
                case "mmo_item_not_found": return "장비를 찾을 수 없습니다. 장비 목록을 다시 확인해 주세요";
                case "mmo_invalid_slot": return "강화할 장비를 다시 선택해 주세요";
                case "mmo_party_leader_only": return "파티장만 사용할 수 있는 기능입니다";
                case "network_error": return "연결이 끊겼습니다. 연결을 확인하면 자동으로 다시 접속합니다";
                default: return "요청을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요";
            }
        }
        private void SuspendMmoInput() { ResetFiveIntents();ClearMmoTarget();ReleaseDungeonCursor(); mmoSuspended=true; mmoDodge=mmoSkill1=mmoSkill2=false; }
        private void ShutdownMmo()
        {
            ShutdownSquad();
            ClearMmoTarget();ReleaseDungeonCursor();ResetMmoCombatFeedback();
            ++mmoGeneration; mmoConnected=false; mmoRequest=false; mmoWorld=null; mmoProfile=null; mmoParty=null;
            mmoDodge=mmoSkill1=mmoSkill2=false; mmoPanel=""; mmoSequence=0;
            mmoMuzzleUntil.Clear();
            mmoRenderActors.Clear();
            MmoClearEffects();
            mmoPendingAction=null;
        }
        private void UpdateMmo()
        {
            if(SquadModeActive){UpdateSquad();return;}
            if(screen!=Screen.Mmo) return;
            if(!mmoRequest && mmoPendingAction!=null){var action=mmoPendingAction;mmoPendingAction=null;action();return;}
            var k=Keyboard.current;
            if(!Application.isFocused) SuspendMmoInput();
            else if(mmoSuspended) { mmoSuspended=false; mmoConnected=false; mmoNextSend=0; }
            bool controls=mmoConnected && !mmoSuspended && mmoPanel.Length==0 && Time.realtimeSinceStartup-mmoLastResponse<1.2f;
            if(controls && k!=null) { mmoDodge |= k.leftShiftKey.wasPressedThisFrame || k.rightShiftKey.wasPressedThisFrame; mmoSkill1 |= k.qKey.wasPressedThisFrame; mmoSkill2 |= k.eKey.wasPressedThisFrame; }
            if(mmoRequest || mmoWorld==null || Time.realtimeSinceStartup<mmoNextSend) return;
            Vector2 move=Vector2.zero;
            if(controls && k!=null) { move.x=(k.dKey.isPressed||k.rightArrowKey.isPressed?1:0)-(k.aKey.isPressed||k.leftArrowKey.isPressed?1:0); move.y=(k.sKey.isPressed||k.downArrowKey.isPressed?1:0)-(k.wKey.isPressed||k.upArrowKey.isPressed?1:0); }
            if(controls && MmoHeld(mmoPad))
            {
                Vector2 p=Mouse.current!=null?MmoUiPoint(Mouse.current.position.ReadValue()):mmoPad.center;
                if(Touchscreen.current!=null)foreach(var t in Touchscreen.current.touches)if(t.press.isPressed && mmoPad.Contains(MmoUiPoint(t.position.ReadValue())))p=MmoUiPoint(t.position.ReadValue());
                move=(p-mmoPad.center)/Mathf.Max(1,Mathf.Min(mmoPad.width,mmoPad.height)*.42f);
            }
            move=DungeonFirstPersonMath.Move(move,dungeonYaw);
            var self=MmoSelf;var forward=DungeonFirstPersonMath.Forward(dungeonYaw);
            Vector2 aim=MmoTargetAim(new Vector2(self?.x??0,self?.y??0)+forward*800);
            var input=new MmoInputRequest { sequence=++mmoSequence,move_x=move.x,move_y=move.y,aim_x=aim.x,aim_y=aim.y,attack=controls&&((k!=null&&k.spaceKey.isPressed)||MmoHeld(mmoAttackButton)||DungeonMouseAttack),dodge=controls&&mmoDodge,skill1=controls&&mmoSkill1,skill2=controls&&mmoSkill2 };
            mmoDodge=mmoSkill1=mmoSkill2=false;
            MmoSend(input);
        }
        private async void MmoSend(MmoInputRequest input)
        {
            int generation=mmoGeneration; var client=api; bool recover=!mmoConnected; mmoRequest=true; mmoNextSend=Time.realtimeSinceStartup+.2f;
            try
            {
                MmoSnapshot state;
                if(recover)
                {
                    try { state=await client.MmoStateAsync(); }
                    catch(ApiException error) when(error.Code=="mmo_not_in_world")
                    {
                        if(!MmoCurrent(generation,client))return;
                        state=await client.MmoEnterAsync(mmoSelectedZone,mmoRole);
                    }
                }
                else state=await client.MmoInputAsync(input);
                if(MmoCurrent(generation,client))MmoApply(state);
            }
            catch(Exception e) { if(MmoCurrent(generation,client)) { mmoConnected=false; mmoError=MmoError(e); mmoNextSend=Time.realtimeSinceStartup+1; } }
            finally { if(MmoCurrent(generation,client))mmoRequest=false; }
        }
        private void CloseMmoPanel()
        {
            // Finish an in-flight save before leaving, using the existing request queue.
            if(mmoRequest){mmoPendingAction=CloseMmoPanel;return;}
            if(SquadModeActive||mmoWorld!=null){MmoLeave();return;}
            mmoPanel="";mmoPendingAction=null;mmoError="";
            mmoDodge=mmoSkill1=mmoSkill2=false;
            ClearMmoTarget();ReleaseDungeonCursor();screen=Screen.Lobby;
        }
        private void OpenMmoEquipment() => OpenSquadLobby();
        private void OpenMmoProfile() => OpenSquadLobby();
        private async void MmoOpenPanel(string panel)
        {
            if(SquadModeActive)return;
            screen=Screen.Mmo; mmoPanel=panel;
            if(mmoRequest || mmoProfile!=null)return;
            int generation=mmoGeneration; var client=api; mmoRequest=true;
            try { var profile=await client.MmoProfileAsync(); if(MmoCurrent(generation,client)){MmoObserveLoot(mmoProfile,profile);mmoProfile=profile;mmoRole=profile.role;} }
            catch(Exception e) { if(MmoCurrent(generation,client))mmoError=MmoError(e); }
            finally { if(MmoCurrent(generation,client))mmoRequest=false; }
        }
        private async void MmoCommand(Func<ApiClient,Task<MmoProfile>> command)
        {
            if(mmoRequest){mmoPendingAction=()=>MmoCommand(command);return;} int generation=mmoGeneration;var client=api;mmoRequest=true;
            try { var profile=await command(client);if(MmoCurrent(generation,client)){MmoObserveLoot(mmoProfile,profile);mmoProfile=profile;mmoError="";} }
            catch(Exception e) {if(MmoCurrent(generation,client))mmoError=MmoError(e);}
            finally {if(MmoCurrent(generation,client))mmoRequest=false;}
        }
        private async void MmoPartyCommand(string action)
        {
            if(mmoRequest){mmoPendingAction=()=>MmoPartyCommand(action);return;}int generation=mmoGeneration;var client=api;mmoRequest=true;
            try {var party=await client.MmoPartyAsync(action,mmoCode.Trim().ToUpperInvariant());if(MmoCurrent(generation,client)){mmoParty=party;mmoError="";}}
            catch(Exception e){if(MmoCurrent(generation,client))mmoError=MmoError(e);}
            finally{if(MmoCurrent(generation,client))mmoRequest=false;}
        }
        private async void MmoLeave()
        {
            if(SquadModeActive){SquadLeave(true);return;}
            if(mmoRequest){mmoPendingAction=MmoLeave;return;}int generation=mmoGeneration;var client=api;mmoRequest=true;
            try {await client.MmoLeaveAsync();if(MmoCurrent(generation,client)){ShutdownMmo();screen=Screen.Lobby;}}
            catch(Exception e){if(MmoCurrent(generation,client))mmoError=MmoError(e);}
            finally{if(MmoCurrent(generation,client))mmoRequest=false;}
        }
        private bool MmoButton(Rect r,string text) => GUI.Button(r,text);
        private void DrawMmo()
        {
            if(SquadModeActive){DrawSquad();return;}
            Fill(new Rect(0,0,1280,720),new Color(.10f,.09f,.16f));
            if(mmoWorld!=null)DrawMmoField();
            else {Panel(mmoField);BaseText(new Rect(60,170,1100,50),"미니 던전 거점 · 장비를 준비하고 사냥터에 입장하세요",26,baseText);if(mmoPanel.Length==0&&MmoButton(new Rect(480,280,320,65),"사냥터 입장"))OpenMmoWorld("frontier");}
            DrawCombatRuneBar(false);
            DrawMmoLootToast();
            if(mmoPanel.Length>0)DrawMmoPanel();
        }
        private string MmoZoneName(string zone) => zone=="squad"?"분대 전장":zone=="minefield"?"위험 지대":zone=="ruins"?"고대 유적":"공동 사냥터";
        private void DrawMmoField()
        {
            if(HasRetroField){DrawDungeonThirdPersonField();return;}
            Vector2 camera=MmoCamera;
            GUI.BeginGroup(mmoField);
            Fill(new Rect(0,0,mmoField.width,mmoField.height),new Color(.13f,.18f,.13f));
            // Tile origin moves with the camera so walking reveals the larger server world.
            bool modelField=HasRetroField;
            if(modelField)GUI.DrawTexture(new Rect(0,0,mmoField.width,mmoField.height),retroScene.View,ScaleMode.StretchToFill,false);
            if(!modelField)DrawPixelGround(new Rect(-camera.x%96-96,-camera.y%96-96,mmoField.width+192,mmoField.height+192),mmoWorld.zone=="minefield"?2:mmoWorld.zone=="ruins"?3:0,.63f);
            if(!modelField && mmoWorld.obstacles!=null)foreach(var o in mmoWorld.obstacles){var r=new Rect(o.x-camera.x,o.y-camera.y,o.width,o.height);Fill(r,new Color(.22f,.24f,.25f));DrawPixelGround(r,3,.8f);MmoArt(r,mmoWorld.zone=="frontier"?0:1);}
            if(mmoWorld.hazards!=null)foreach(var h in mmoWorld.hazards)DrawBombEffect(new Vector2(h.x-camera.x,h.y-camera.y),h.radius,131,.8f);
            if(mmoWorld.enemies!=null)foreach(var e in mmoWorld.enemies)if(e.hp>0){var rendered=MmoRenderPosition("mmo-enemy:"+e.id,e.x,e.y);var point=rendered-camera;if(point.x<-100||point.x>1340||point.y<-100||point.y>560)continue;MmoWorldMotion("mmo-enemy:"+e.id,rendered.x,rendered.y);if(!modelField && (e.kind!="boss"||!MmoArt(new Rect(point.x-58,point.y-75,116,116),3)))DrawPixelSoldier(new ArenaPoint(point.x,point.y),e.kind=="guard"?ArenaRole.Guardian:ArenaRole.Assault,1,-1,e.hit_flash>0,e.kind=="boss","mmo-enemy:"+e.id);MmoHealth(point,e.hp,e.max_hp,e.name,new Color(.9f,.25f,.2f));}
            if(mmoWorld.players!=null)foreach(var a in mmoWorld.players){var rendered=MmoRenderPosition("mmo-player:"+a.id,a.x,a.y);var point=rendered-camera;bool own=a.id==mmoWorld.you_id;MmoWorldMotion("mmo-player:"+a.id,rendered.x,rendered.y);if(!modelField)DrawPixelSoldier(new ArenaPoint(point.x,point.y),(ArenaRole)Mathf.Clamp(a.role,0,2),own?0:2,a.fx,a.hit_flash>0,false,"mmo-player:"+a.id,a.dodge_left>0);DrawMmoCombat(a,point);MmoHealth(point,a.hp,a.max_hp,a.name+" · "+a.level,own?baseCyan:baseGold);}
            for(int i=mmoActiveEffects.Count-1;i>=0;i--)
            {
                var visual=mmoActiveEffects[i];float age=Time.realtimeSinceStartup-visual.started;
                if(age>=.8f){mmoActiveEffects.RemoveAt(i);continue;}
                var e=visual.effect;Color color=e.kind=="damage"?Color.white:baseGold;color.a*=Mathf.Clamp01(1-age/.8f);
                BaseText(new Rect(e.x-camera.x-80,e.y-camera.y-90-age*35,160,28),e.text,16,color,TextAnchor.MiddleCenter);
            }
            DrawMmoNavigation();
            GUI.EndGroup();
        }
        private void MmoHealth(Vector2 p,float hp,float max,string name,Color color)
        {
            Fill(new Rect(p.x-27,p.y-47,54,5),new Color(.08f,.08f,.08f));Fill(new Rect(p.x-27,p.y-47,54*Mathf.Clamp01(hp/Mathf.Max(1,max)),5),color);
            BaseText(new Rect(p.x-100,p.y+29,200,23),name,12,color,TextAnchor.MiddleCenter);
        }
        private void MmoClearEffects() {mmoSeenEffects.Clear();mmoEffectOrder.Clear();mmoActiveEffects.Clear();}
        private void MmoWorldMotion(string key,float x,float y)
        {
            // Sample world position before drawing: the same-frame motion guard prevents
            // the renderer's camera-relative sample from replacing the actual walk pose.
            MotionFor(key,new ArenaPoint(x,y));
        }
        private Vector2 MmoRenderPosition(string key,float x,float y)
        {
            var target=new Vector2(x,y);
            if(!mmoRenderActors.TryGetValue(key,out var actor)){actor=new MmoRenderActor {position=target,frame=Time.frameCount};mmoRenderActors[key]=actor;}
            if(Vector2.Distance(actor.position,target)>180)actor.position=target;
            else if(actor.frame!=Time.frameCount)actor.position=Vector2.Lerp(actor.position,target,1-Mathf.Exp(-14*Mathf.Min(Time.unscaledDeltaTime,.1f)));
            actor.frame=Time.frameCount;return actor.position;
        }
        private bool MmoArt(Rect rect,int index)
        {
            if(mmoAtlas==null)mmoAtlas=Resources.Load<Texture2D>("Sprites/warfront-mmo-world-v1");
            if(mmoAtlas==null)return false;mmoAtlas.filterMode=FilterMode.Point;
            GUI.DrawTextureWithTexCoords(rect,mmoAtlas,new Rect((index%2)*.5f,index<2?.5f:0,.5f,.5f),true);return true;
        }
        private void DrawMmoCombat(MmoActor actor,Vector2 point)
        {
            if(actor.dodge_left>0) {Color old=GUI.color;GUI.color=new Color(.3f,.85f,1,.2f);GUI.DrawTexture(new Rect(point.x-38,point.y-34,76,68),CircleTexture());GUI.color=old;}
            if(!mmoMuzzleUntil.TryGetValue(actor.id,out float until)||until<Time.realtimeSinceStartup)return;
            Matrix4x4 matrix=GUI.matrix;
            try {GUIUtility.RotateAroundPivot(Mathf.Atan2(actor.fy,actor.fx)*Mathf.Rad2Deg,point);Fill(new Rect(point.x+23,point.y-8,22,7),baseGold);Fill(new Rect(point.x+50,point.y-6,72,2),new Color(1,.9f,.55f,.8f));}
            finally {GUI.matrix=matrix;}
        }
        private void DrawMmoPanel()
        {
            if(mmoPanel=="controls"){DrawMmoControlSettings();return;}
            if(mmoPanel=="equipment"){DrawMmoEquipmentPanel();return;}
            Fill(new Rect(0,120,1280,480),new Color(0,0,0,.72f));Panel(new Rect(170,130,940,455));
            BaseText(new Rect(200,146,750,40),mmoPanel=="equipment"?"던전 장비 보관실":mmoPanel=="guide"?"3인칭 모험 안내":"캐릭터 · 임무 · 파티",26,baseText);
            if(MmoButton(new Rect(980,145,100,35),"닫기")){CloseMmoPanel();return;}
            if(mmoPanel=="guide")
            {
                string[] lines={"WASD / 방향키 · 바라보는 방향을 기준으로 이동","플레이 화면 클릭 · 마우스로 시점 회전","마우스 왼쪽 / Space · 공격   |   Shift · 회피","Q · 폭발 룬   |   E · 회복","Esc · 커서를 풀고 장비·파티·마을 복귀 버튼 사용","모바일 · 왼쪽 이동 패드 / 오른쪽 화면 드래그로 시점 회전"};
                for(int i=0;i<lines.Length;i++)BaseText(new Rect(210,207+i*49,850,38),lines[i],20,i%2==0?baseText:baseGold);
                return;
            }
            var p=mmoProfile;if(p==null)return;
            if(mmoPanel=="equipment")
            {
                BaseText(new Rect(200,193,840,30),$"골드 {p.gold} · 무기 +{p.weapon_rank} / 방어구 +{p.armor_rank} · 공격력 {p.attack:0} · 최대 HP {p.max_hp:0}",17,baseGold);
                if(MmoButton(new Rect(200,233,400,38),p.weapon_rank>=20?"무기 · 최고 강화 +20":$"무기 강화 · {50*(p.weapon_rank+1)} 골드") && p.weapon_rank<20)MmoCommand(c=>c.MmoUpgradeAsync("weapon"));
                if(MmoButton(new Rect(620,233,450,38),p.armor_rank>=20?"방어구 · 최고 강화 +20":$"방어구 강화 · {50*(p.armor_rank+1)} 골드") && p.armor_rank<20)MmoCommand(c=>c.MmoUpgradeAsync("armor"));
                var items=p.inventory??Array.Empty<MmoItem>();
                mmoInventoryScroll=GUI.BeginScrollView(new Rect(200,287,870,275),mmoInventoryScroll,new Rect(0,0,840,Mathf.Max(270,items.Length*51)));
                for(int i=0;i<items.Length;i++){var item=items[i];BaseText(new Rect(4,i*51,620,23),$"{item.name} · {(item.slot=="weapon"?"무기":"방어구")} · 위력 {item.power} · 등급 {item.rarity}",14,item.equipped?baseGold:baseText);BaseText(new Rect(4,i*51+23,620,22),MmoEquipmentComparison(item),12,MmoEquipmentComparisonColor(item));if(MmoButton(new Rect(650,i*51+3,160,38),item.equipped?"장착 중":"장착"))MmoCommand(c=>c.MmoEquipAsync(item.id));}
                GUI.EndScrollView();
            }
            else
            {
                BaseText(new Rect(200,193,840,30),$"레벨 {p.level} · 경험치 {p.xp}/{p.xp_next} · 골드 {p.gold}",19,baseGold);
                DrawMmoQuestDetails(new Rect(200,229,870,108));
                BaseText(new Rect(200,344,830,22),"병과 외형 선택 · 전투 능력은 동일합니다",14,baseMuted);
                string[] roles={"돌격병","수호병","지원병"};for(int i=0;i<3;i++){int role=i;if(MmoButton(new Rect(200+i*290,371,270,32),(mmoRole==i?"✓ ":"")+roles[i])){mmoRole=role;MmoChangeRole(role);}}
                BaseText(new Rect(200,412,840,27),"파티 코드 · "+(string.IsNullOrEmpty(mmoParty?.code)?"솔로":mmoParty.code+" · "+(mmoParty.members?.Length??0)+" / 4명"),18,baseCyan);
                mmoCode=GUI.TextField(new Rect(200,451,265,33),mmoCode,12);
                if(MmoButton(new Rect(480,451,180,33),"파티 생성"))MmoPartyCommand("create");
                if(MmoButton(new Rect(675,451,180,33),"코드로 참가"))MmoPartyCommand("join");
                if(MmoButton(new Rect(870,451,190,33),"파티 나가기"))MmoPartyCommand("leave");
                BaseText(new Rect(200,497,850,64),"파티와 함께 유적에 입장해 보스를 처치하세요.\n창을 열어도 전장은 계속 진행됩니다. 안전한 곳에서 준비하세요.",16,baseMuted);
            }
        }
        private async void MmoChangeRole(int role)
        {
            if(mmoRequest){mmoPendingAction=()=>MmoChangeRole(role);return;}int generation=mmoGeneration;var client=api;mmoRequest=true;
            try {var state=await client.MmoEnterAsync(mmoWorld?.zone??"frontier",role);if(MmoCurrent(generation,client))MmoApply(state);}
            catch(Exception e){if(MmoCurrent(generation,client))mmoError=MmoError(e);}
            finally{if(MmoCurrent(generation,client))mmoRequest=false;}
        }
    }
}

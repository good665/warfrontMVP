using System;
using System.Collections.Generic;
using UnityEngine;

namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private bool mmoTrackQuest = true;
        private readonly HashSet<string> mmoKnownLoot = new HashSet<string>();
        private readonly Queue<string> mmoLootMessages = new Queue<string>();
        private string mmoLootMessage = "";
        private float mmoLootUntil;

        private void DrawMmoQuestDetails(Rect rect)
        {
            Fill(rect, new Color(.08f,.13f,.17f,.96f));
            var quest = mmoProfile?.quest;
            if (quest == null) { BaseText(rect, "서버에서 임무를 확인하고 있습니다",16,baseMuted); return; }
            BaseText(new Rect(rect.x+12,rect.y+5,rect.width-225,25),quest.title,18,baseGold);
            BaseText(new Rect(rect.x+12,rect.y+32,rect.width-24,23),quest.description ?? "",14,baseText);
            BaseText(new Rect(rect.x+12,rect.y+57,rect.width-24,22),$"{MmoZoneName(quest.zone)} · {quest.progress}/{quest.target} · 보상 XP {quest.reward_xp} / 골드 {quest.reward_gold}",14,baseCyan);
            var bar = new Rect(rect.x+12,rect.y+88,rect.width-240,7);
            Fill(bar,new Color(.2f,.23f,.27f));
            Fill(new Rect(bar.x,bar.y,bar.width*Mathf.Clamp01((float)quest.progress/Mathf.Max(1,quest.target)),bar.height),quest.ready?baseGold:baseCyan);
            if (GUI.Button(new Rect(rect.xMax-205,rect.y+5,193,26),mmoTrackQuest?"목표 추적 끄기":"목표 추적 켜기")) mmoTrackQuest=!mmoTrackQuest;
            bool enabled=GUI.enabled;
            GUI.enabled=enabled && !mmoRequest && (quest.ready || !string.IsNullOrEmpty(quest.zone));
            if (GUI.Button(new Rect(rect.xMax-205,rect.y+76,193,26),quest.ready?"임무 보상 받기":"임무 지역으로 입장"))
            {
                if(quest.ready) MmoCommand(c=>c.MmoClaimAsync());
                else OpenMmoWorld(quest.zone);
            }
            GUI.enabled=enabled;
        }

        private int MmoEquipmentDelta(MmoItem item)
        {
            if(item==null || item.equipped) return 0;
            int power=0;
            string equipped=item.slot=="weapon"?mmoProfile?.equipped_weapon:item.slot=="helmet"?mmoProfile?.equipped_helmet:mmoProfile?.equipped_armor;
            if(mmoProfile?.inventory!=null) foreach(var current in mmoProfile.inventory)
                if(current!=null && current.slot==item.slot && (current.id==equipped || current.equipped)) {power=current.power;break;}
            return item.power-power;
        }
        private string MmoEquipmentComparison(MmoItem item)
        {
            if(item==null) return "";
            string stat=item.slot=="weapon"?"공격력":"최대 HP";
            float current=item.slot=="weapon"?(mmoProfile?.attack??0):(mmoProfile?.max_hp??0);
            int delta=MmoEquipmentDelta(item);
            return item.equipped?$"장착 중 · {stat} {current:0}":$"{stat} {current:0} → {current+delta:0} ({delta:+0;-0;0})";
        }
        private Color MmoEquipmentComparisonColor(MmoItem item)
        {
            int delta=MmoEquipmentDelta(item);
            return delta>0?baseCyan:delta<0?new Color(1,.55f,.45f):baseMuted;
        }
        private void MmoObserveLoot(MmoProfile previous, MmoProfile current)
        {
            if(current==null) return;
            if(previous==null) {mmoKnownLoot.Clear();mmoLootMessages.Clear();mmoLootMessage="";}
            if(previous?.inventory!=null) foreach(var item in previous.inventory)
                if(item!=null && !string.IsNullOrEmpty(item.id)) mmoKnownLoot.Add(item.id);
            if(current.inventory==null) return;
            foreach(var item in current.inventory)
            {
                if(item==null || string.IsNullOrEmpty(item.id) || !mmoKnownLoot.Add(item.id) || previous==null) continue;
                if(mmoLootMessages.Count>=6) mmoLootMessages.Dequeue();
                mmoLootMessages.Enqueue($"장비 획득 · {item.name}  [{(item.slot=="weapon"?"무기":"방어구")} +{item.power}]");
            }
        }
        private void DrawMmoLootToast()
        {
            if(Time.realtimeSinceStartup>=mmoLootUntil)
            {
                mmoLootMessage=mmoLootMessages.Count>0?mmoLootMessages.Dequeue():"";
                mmoLootUntil=Time.realtimeSinceStartup+3.5f;
            }
            if(string.IsNullOrEmpty(mmoLootMessage) || mmoPanel.Length>0) return;
            Fill(new Rect(370,540,540,36),new Color(.05f,.12f,.15f,.96f));
            BaseText(new Rect(380,543,520,30),mmoLootMessage,16,baseGold,TextAnchor.MiddleCenter);
        }

        private Vector2 MmoMapPoint(Rect map,float x,float y)
        {
            float width=mmoWorld!=null && mmoWorld.world_width>0?mmoWorld.world_width:3600;
            float height=mmoWorld!=null && mmoWorld.world_height>0?mmoWorld.world_height:2400;
            return new Vector2(map.x+Mathf.Clamp01(x/width)*map.width,map.y+Mathf.Clamp01(y/height)*map.height);
        }
        private void MmoMapDot(Vector2 point,Color color,float size)
        { Fill(new Rect(point.x-size/2,point.y-size/2,size,size),color); }

        // Called within the field GUI group, including the 3D field renderer.
        private void DrawMmoNavigation()
        {
            if(SquadModeActive){DrawSquadNavigation();return;}
            if(mmoWorld==null) return;
            var map=new Rect(16,39,180,120);
            Fill(new Rect(10,10,192,223),new Color(.035f,.06f,.08f,.94f));
            BaseText(new Rect(16,13,180,22),MmoZoneName(mmoWorld.zone),13,baseText);
            Fill(map,new Color(.12f,.19f,.15f));
            float width=mmoWorld.world_width>0?mmoWorld.world_width:3600;
            float height=mmoWorld.world_height>0?mmoWorld.world_height:2400;
            if(mmoWorld.obstacles!=null) foreach(var obstacle in mmoWorld.obstacles)
            {
                if(obstacle==null) continue;
                Vector2 p=MmoMapPoint(map,obstacle.x,obstacle.y);
                Fill(new Rect(p.x,p.y,Mathf.Max(1,obstacle.width/width*map.width),Mathf.Max(1,obstacle.height/height*map.height)),new Color(.38f,.42f,.39f));
            }
            if(mmoWorld.enemies!=null) foreach(var enemy in mmoWorld.enemies)
                if(enemy!=null && enemy.hp>0) MmoMapDot(MmoMapPoint(map,enemy.x,enemy.y),new Color(1,.35f,.25f),enemy.kind=="boss"?6:3);
            var quest=mmoProfile?.quest;
            if(mmoTrackQuest && quest!=null && quest.zone==mmoWorld.zone && !quest.ready && MmoQuestGoal(out var goal,out var goalLabel))
            {
                Vector2 point=MmoMapPoint(map,goal.x,goal.y);
                MmoMapDot(point,baseGold,8); MmoMapDot(point,new Color(.1f,.12f,.12f),3);
            }
            if(mmoWorld.players!=null) foreach(var actor in mmoWorld.players)
            {
                if(actor==null || actor.id==mmoWorld.you_id) continue;
                bool party=!string.IsNullOrEmpty(mmoParty?.code) && actor.party_code==mmoParty.code;
                MmoMapDot(MmoMapPoint(map,actor.x,actor.y),party?baseCyan:baseMuted,party?5:3);
            }
            var self=MmoSelf;
            if(self!=null)
            {
                Vector2 point=MmoMapPoint(map,self.x,self.y);
                MmoMapDot(point,Color.white,6);
                Vector2 facing=new Vector2(self.fx,self.fy).normalized;
                MmoMapDot(point+facing*8,Color.white,3);
            }
            BaseText(new Rect(16,161,180,20),"흰색 나 · 청록 파티 · 빨강 적",10,baseMuted);
            bool enabled=GUI.enabled; GUI.enabled=enabled && mmoPanel.Length==0 && !mmoRequest;
            if(GUI.Button(new Rect(16,187,180,29),mmoWorld.zone=="ruins"?"유적 · 현재 지역":"유적 입장") && mmoWorld.zone!="ruins") OpenMmoWorld("ruins");
            GUI.enabled=enabled;
            DrawMmoObjectiveArrow();
        }
        private bool MmoQuestGoal(out Vector2 target,out string label)
        {
            target=Vector2.zero;label="임무 지점";
            var quest=mmoProfile?.quest;var self=MmoSelf;
            if(quest==null||self==null||quest.zone!=mmoWorld?.zone)return false;
            if(quest.kind=="explore"){target=new Vector2(quest.x,quest.y);return true;}
            float nearest=float.PositiveInfinity;
            if(mmoWorld.enemies!=null)foreach(var enemy in mmoWorld.enemies)
            {
                if(enemy==null||enemy.hp<=0||(quest.kind=="boss"&&enemy.kind!="boss")||(quest.kind=="elite"&&enemy.kind!="guard"&&enemy.kind!="elite")||(quest.kind=="hunt"&&enemy.kind=="boss"))continue;
                float distance=(new Vector2(enemy.x,enemy.y)-new Vector2(self.x,self.y)).sqrMagnitude;
                if(distance<nearest){nearest=distance;target=new Vector2(enemy.x,enemy.y);label=enemy.name;}
            }
            return !float.IsPositiveInfinity(nearest);
        }
        private void DrawMmoObjectiveArrow()
        {
            var quest=mmoProfile?.quest; var self=MmoSelf;
            if(!mmoTrackQuest || quest==null || self==null) return;
            string text;
            float arrowBearing=0;
            bool showArrow=false;
            if(quest.ready) text="임무 완료 · 캐릭터 창에서 보상 받기";
            else if(quest.zone!=mmoWorld.zone) text="목표 지역 · "+MmoZoneName(quest.zone);
            else if(!MmoQuestGoal(out var target,out var label))text="임무 대상이 다시 나타나기를 기다리세요";
            else
            {
                Vector2 delta=target-new Vector2(self.x,self.y);
                float bearing=Mathf.Atan2(delta.x,-delta.y)*Mathf.Rad2Deg;
                if(bearing<0) bearing+=360;
                arrowBearing=bearing; showArrow=delta.sqrMagnitude>1;
                string[] compass={"북","북동","동","남동","남","남서","서","북서"};
                text=$"{label} · {delta.magnitude:0} 거리 · {compass[Mathf.RoundToInt(bearing/45)%8]} {bearing:0}°";
            }
            Fill(new Rect(215,12,440,30),new Color(.035f,.06f,.08f,.9f));
            if(showArrow)
            {
                Matrix4x4 matrix=GUI.matrix;
                try
                {
                    GUIUtility.RotateAroundPivot(Mathf.DeltaAngle(dungeonYaw,arrowBearing),new Vector2(232,27));
                    Fill(new Rect(231,21,2,13),baseGold);
                    Fill(new Rect(229,21,6,2),baseGold);
                    Fill(new Rect(227,23,2,2),baseGold);
                    Fill(new Rect(235,23,2,2),baseGold);
                }
                finally {GUI.matrix=matrix;}
            }
            BaseText(new Rect(248,14,398,26),text,14,baseGold);
        }
    }
}

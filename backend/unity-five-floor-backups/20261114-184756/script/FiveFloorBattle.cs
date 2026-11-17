using System;
using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    [Serializable] public sealed class BattleItem { public string id,name,option; public float value; }
    [Serializable] public sealed class ZodiacCharacter { public string id,name,q,e,q_kind,e_kind; }
    [Serializable] public sealed class BattlePortal { public float x,y; public bool up,down; }
    [Serializable] public sealed class BattleMonsterCamp { public string id; public int floor; public bool alive; }
    [Serializable] public sealed class FiveFloorBattle
    {
        public bool five_floor,character_locked; public int floor; public string character,dragon_buff;
        public float buff_left,next_wave,dragon_respawn,dragon_hp; public BattleItem[] inventory,pending_items;
        public ZodiacCharacter[] characters; public BattlePortal[] portals; public BattleMonsterCamp[] monster_camps;
    }
    public sealed partial class GameBootstrap
    {
        private string fiveCharacter="rat";
        private int fivePortal,fiveReplace=-1;
        private bool fiveJump;
        private void ResetFiveIntents(){fivePortal=0;fiveJump=false;fiveReplace=-1;}
        private bool FiveFloorActive=>SquadModeActive&&squadSnapshot?.battle?.five_floor==true;
        private static readonly string[] ZodiacIds={"rat","ox","tiger","rabbit","dragon","snake","horse","goat","monkey","rooster","dog","pig"};
        private static readonly string[] ZodiacNames={"쥐","소","호랑이","토끼","용","뱀","말","양","원숭이","닭","개","돼지"};
        private bool RetiredWorldEntry(){OpenSquadLobby();return true;}
        private void DrawFiveFloorSelection(Rect area)
        {
            int columns=area.width<250?3:6, rows=(12+columns-1)/columns;
            float w=area.width/columns,h=area.height/rows;
            bool previous=GUI.enabled;GUI.enabled=previous&&!squadRequest;
            for(int i=0;i<12;i++)
            {
                var r=new Rect(area.x+(i%columns)*w,area.y+(i/columns)*h,w-4,h-4);
                if(RuneButton(r,(fiveCharacter==ZodiacIds[i]?"● ":"")+ZodiacNames[i]))fiveCharacter=ZodiacIds[i];
            }
            GUI.enabled=previous;
        }
        private string FiveSkillLabel(bool ultimate)
        {
            var b=squadSnapshot?.battle;
            if(b?.characters!=null)foreach(var c in b.characters)if(c.id==b.character)
                return (ultimate?c.e+" E":c.q+" Q")+"\n"+(ultimate?MmoSelf?.skill2_cooldown??0:MmoSelf?.skill1_cooldown??0).ToString("0.0")+"s";
            return ultimate?"필살기 E":"스킬 Q";
        }
        private void DrawFiveFloorInventory()
        {
            var b=squadSnapshot.battle;var panel=strategyPanel;
            RuneFrame(panel,true);BaseText(new Rect(panel.x+6,panel.y+3,220,24),"경기 아이템 · 9칸",13,baseGold,TextAnchor.MiddleCenter);
            bool pending=b.pending_items!=null&&b.pending_items.Length>0;
            for(int i=0;i<9;i++)
            {
                var r=new Rect(panel.x+8+(i%3)*72,panel.y+31+(i/3)*49,68,45);
                var item=b.inventory!=null&&i<b.inventory.Length?b.inventory[i]:null;
                RuneFrame(r,true);
                string title=item==null?"빈 칸":item.name.Replace("의 부적","");
                string value=item==null?"":item.option=="cooldown"?"-"+(item.value*100).ToString("0.#")+"%":ItemValue(item).Replace(" ","");
                BaseText(new Rect(r.x+2,r.y+3,r.width-4,19),title,11,baseText,TextAnchor.MiddleCenter);
                BaseText(new Rect(r.x+2,r.y+23,r.width-4,17),value,10,baseGold,TextAnchor.MiddleCenter);
                if(GUI.Button(r,GUIContent.none,GUIStyle.none)&&pending)fiveReplace=i;
            }
            BaseText(new Rect(panel.x+6,panel.y+178,220,22),pending?"새 아이템! 교체할 칸 선택":"획득 즉시 적용 · 경기 종료 시 소멸",10,pending?baseGold:baseMuted,TextAnchor.MiddleCenter);
            if(pending)
            {
                RuneFrame(new Rect(panel.x-8,panel.y-59,248,54),true);
                BaseText(new Rect(panel.x,panel.y-55,230,48),b.pending_items[0].name+" · "+ItemValue(b.pending_items[0])+"\n기존 칸을 누르거나 숫자 1~9로 교체",11,baseGold,TextAnchor.MiddleCenter);
                var keyboard=Keyboard.current;
                if(Event.current.type==EventType.Repaint&&keyboard!=null)
                {
                    var keys=new[]{keyboard.digit1Key,keyboard.digit2Key,keyboard.digit3Key,keyboard.digit4Key,keyboard.digit5Key,keyboard.digit6Key,keyboard.digit7Key,keyboard.digit8Key,keyboard.digit9Key};
                    for(int i=0;i<9;i++)if(keys[i].wasPressedThisFrame)fiveReplace=i;
                }
            }
        }
        private static string ItemValue(BattleItem item)
        {
            string name=item.option=="attack"?"공격":item.option=="health"?"체력":item.option=="speed"?"속도":item.option=="armor"?"방어":"재사용";
            return name+" +"+(item.option=="cooldown"?(item.value*100).ToString("0.#")+"%":item.value.ToString("0.#"));
        }
        private void DrawFiveFloorNavigation()
        {
            var b=squadSnapshot.battle;
            var self=MmoSelf;
            if(self!=null&&b.portals!=null)foreach(var portal in b.portals)
            {
                if(Vector2.Distance(new Vector2(self.x,self.y),new Vector2(portal.x,portal.y))>160)continue;
                var r=new Rect(470,460,300,48);RuneFrame(r,true);
                bool previous=GUI.enabled;GUI.enabled=previous&&mmoConnected&&self.hp>0&&!SquadPauseBlocked;
                if(portal.up&&RuneButton(new Rect(r.x+8,r.y+8,138,32),"위층으로 F"))fivePortal=1;
                if(portal.down&&RuneButton(new Rect(r.x+154,r.y+8,138,32),"아래층으로 G"))fivePortal=-1;
                GUI.enabled=previous;break;
            }
        }
    }
}

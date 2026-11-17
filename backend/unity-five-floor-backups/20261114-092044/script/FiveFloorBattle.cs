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
                string label=item==null?"빈 칸":item.name.Replace("의 부적","")+"\n"+(item.option=="cooldown"?"-"+(item.value*100).ToString("0.#")+"%":ItemValue(item).Replace(" ",""));
                if(RuneButton(r,label)&&pending)fiveReplace=i;
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
            Fill(new Rect(14,14,440,108),new Color(.035f,.025f,.08f,.9f));
            BaseText(new Rect(25,19,420,28),$"{b.floor}층 / 5층 · {(SquadVsComputer?"컴퓨터 대전":"사람 대 사람 1:1")}",19,baseGold);
            BaseText(new Rect(25,49,420,22),$"미니언 출격 {b.next_wave:0}초 · "+(b.dragon_respawn>0?$"용 부활 {b.dragon_respawn:0}초":"3층 중앙 용 출현"),12,baseText);
            string buff=b.buff_left>0?$"용의 축복 · {(b.dragon_buff=="attack"?"공격 +10%":b.dragon_buff=="health"?"체력 +10%":"속도 +8%")} · {b.buff_left:0}초":"중간보스 아이템 · 누적 피해량 1위 획득";
            BaseText(new Rect(25,75,420,22),buff,12,baseCyan);
            Fill(new Rect(14,132,310,104),new Color(.035f,.025f,.08f,.85f));
            BaseText(new Rect(24,137,290,23),"목표 · 상대 층의 본진 파괴",14,baseGold);
            BaseText(new Rect(24,162,290,62),"양끝 포탈에서 F 위층 / G 아래층\n좌클릭 공격 · Q 스킬 · E 필살기\nSpace 점프 · Shift 회피 · Esc 일시정지",11,baseText);
            if(RuneButton(new Rect(24,241,138,31),"점프 Space"))fiveJump=true;
            if(squadSnapshot.bases!=null)foreach(var headquarters in squadSnapshot.bases)
            {
                int row=headquarters.team==squadSnapshot.team?0:1;
                BaseText(new Rect(940,15+row*27,280,25),(row==0?"아군":"상대")+$" 본진 {headquarters.floor}층 · {headquarters.hp:0}/{headquarters.max_hp:0}",13,row==0?baseCyan:baseGold);
            }
            // Compact five-floor overview; only the current floor's actors are sent by the server.
            for(int floor=5;floor>=1;floor--)
            {
                float y=85+(5-floor)*27;Color tint=floor==b.floor?baseCyan:baseMuted;
                Fill(new Rect(990,y,230,24),new Color(.05f,.04f,.1f,.86f));
                int camps=0;if(b.monster_camps!=null)foreach(var camp in b.monster_camps)if(camp.floor==floor&&camp.alive)camps++;
                BaseText(new Rect(1000,y+1,215,22),$"{floor}층   기지 {camps}/3"+(floor==3?"   용":"")+(floor==b.floor?"   ◀":""),12,tint);
            }
            var self=MmoSelf;
            if(self!=null&&b.portals!=null)foreach(var portal in b.portals)
            {
                if(Vector2.Distance(new Vector2(self.x,self.y),new Vector2(portal.x,portal.y))>160)continue;
                var r=new Rect(470,460,300,83);RuneFrame(r,true);
                bool previous=GUI.enabled;GUI.enabled=previous&&mmoConnected&&self.hp>0&&!SquadPauseBlocked;
                if(portal.up&&RuneButton(new Rect(r.x+8,r.y+8,138,32),"위층으로 F"))fivePortal=1;
                if(portal.down&&RuneButton(new Rect(r.x+154,r.y+8,138,32),"아래층으로 G"))fivePortal=-1;
                BaseText(new Rect(r.x+8,r.y+46,284,22),"포탈 이동 중에는 잠시 보호됩니다",11,baseMuted,TextAnchor.MiddleCenter);
                GUI.enabled=previous;break;
            }
        }
    }
}

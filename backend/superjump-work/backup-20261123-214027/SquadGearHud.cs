using System;
using UnityEngine;
namespace Warfront
{
    // Squad inventory in the slot row above the skills, keys 1..0: 1 = equipped weapon, 2 = equipped armor,
    // 3..10 = bag (consumables use once, bag gear swaps in). Ctrl+number / Ctrl+click drops a slot on the ground.
    // Filled from building chests (backend squad_items.py).
    public sealed partial class GameBootstrap
    {
        private const int SquadBagSize=8;
        private static readonly UnityEngine.InputSystem.Key[] SquadSlotKeys={UnityEngine.InputSystem.Key.Digit1,UnityEngine.InputSystem.Key.Digit2,UnityEngine.InputSystem.Key.Digit3,UnityEngine.InputSystem.Key.Digit4,UnityEngine.InputSystem.Key.Digit5,
            UnityEngine.InputSystem.Key.Digit6,UnityEngine.InputSystem.Key.Digit7,UnityEngine.InputSystem.Key.Digit8,UnityEngine.InputSystem.Key.Digit9,UnityEngine.InputSystem.Key.Digit0};
        // Equipped slots (1, 2) have no use action; any slot can be dropped.
        private void SquadUseSlot(int slot,bool drop){if(drop)rtsDrop=slot;else if(slot>=2)rtsItem=slot;}
        private static readonly string[] ZodiacWeaponNames={"쥐 이빨","소 뿔","발톱","당근","용 꼬리","뱀 꼬리","말 발굽","양 뿔","펀치","달걀","개 뼈다귀","돼지꼬리"};
        // weapon_<zodiac> / fitted_armor_<zodiac> -> index into ZodiacIds, -1 for other items.
        private static int ZodiacGear(string id,out bool weapon)
        {
            weapon=id.StartsWith("weapon_");
            string z=weapon?id.Substring(7):id.StartsWith("fitted_armor_")?id.Substring(13):null;
            return z==null?-1:Array.IndexOf(ZodiacIds,z);
        }
        private bool SquadGearMine(int zodiac)=>zodiac>=0&&squadSnapshot?.battle?.character==ZodiacIds[zodiac];
        private static bool SquadIsGear(string id)=>id=="armor"||id.StartsWith("weapon_")||id.StartsWith("fitted_armor");
        private string SquadGearName(string id)
        {
            int z=ZodiacGear(id,out bool weapon);if(z<0)return SquadItemName(id);
            bool mine=SquadGearMine(z);
            return weapon?L.F("{0} · {1} 전용 무기 · 공격력 증가",L.T(ZodiacWeaponNames[z]),L.T(ZodiacNames[z]))+"\n"+L.T(mine?"내 캐릭터 전용 · 효과 100%":"다른 캐릭터 전용 · 효과 절반")
                :L.F("전용 갑옷 ({0}) · 방어력 크게 증가",L.T(ZodiacNames[z]))+"\n"+L.T(mine?"내 캐릭터 전용 · 효과 100%":"다른 캐릭터 전용 · 일반 갑옷만큼만 막아 줌");
        }
        private static string SquadSlotKey(int slot)=>(slot+1).ToString();
        private string squadGearTip;private Rect squadGearTipAnchor;
        private static string SquadItemName(string id)=>L.T(id=="axe"?"도끼 · 사용하면 앞쪽 건물 안 테이블·의자를 한 번 내려쳐 부숩니다 (50% 확률로 아이템 3개)":id=="armor"?"갑옷 · 방어력 증가"
            :id=="portal"?"포탈 · 다른 건물로 랜덤 이동 (이동 후 3초 무적)":id=="portal_plus"?"업그레이드 포탈 · 우리 기지 성벽으로 이동 (3초 무적)":id=="top"?"팽이 · 지정 위치를 10초간 돌며 피해"
            :id=="bouncy_ball"?"탱탱볼 · 벽에 튕기며 맞은 적에게 피해 (10번 튕기면 사라짐)":id=="long_whip"?"긴 채찍 · 앞쪽 돌담 건축물을 쓸어 날려버립니다":"");
        private void SquadItemIcon(Rect rect,string id)
        {
            var fbxIcon=ZodiacItemModels.Icon(id);
            if(fbxIcon!=null){GUI.DrawTexture(rect,fbxIcon,ScaleMode.ScaleToFit,true);return;}
            if(id=="armor"){GearIcon(rect,"armor",new Color(.6f,.58f,.63f));return;}
            int z=ZodiacGear(id,out bool weapon);
            if(z>=0)
            {
                // Gold when it is my character's gear, grey when the effect is reduced.
                GearIcon(rect,weapon?"weapon":"armor",SquadGearMine(z)?runeGold:new Color(.55f,.55f,.6f));
                BaseText(new Rect(rect.x,rect.yMax-12,rect.width,13),L.T(ZodiacNames[z]),9,runeText,TextAnchor.LowerRight);return;
            }
            float s=Mathf.Min(rect.width,rect.height)/32;Vector2 o=rect.center-Vector2.one*16*s;
            Action<float,float,float,float,Color> pixel=(x,y,w,h,c)=>Fill(new Rect(o.x+x*s,o.y+y*s,w*s,h*s),c);
            var steel=new Color(.62f,.62f,.70f);var wood=new Color(.45f,.28f,.16f);
            if(id=="axe"){pixel(15,4,3,25,wood);pixel(18,5,8,11,steel);pixel(24,4,3,13,new Color(.86f,.86f,.94f));pixel(11,7,4,5,steel);}
            else if(id=="portal"||id=="portal_plus"){
                var ring=id=="portal"?new Color(.45f,.55f,1):runeGold;
                pixel(10,5,12,3,ring);pixel(10,24,12,3,ring);pixel(6,9,3,14,ring);pixel(23,9,3,14,ring);pixel(8,7,3,3,ring);pixel(21,7,3,3,ring);pixel(8,22,3,3,ring);pixel(21,22,3,3,ring);
                pixel(10,9,12,14,new Color(ring.r*.35f,ring.g*.35f,ring.b*.5f));pixel(14,12,4,8,ring);
                if(id=="portal_plus"){pixel(12,1,2,3,ring);pixel(15,0,2,4,ring);pixel(18,1,2,3,ring);} // battlement = home walls
            }
            else if(id=="top"){var red=new Color(.85f,.3f,.25f);pixel(15,3,2,5,wood);pixel(7,8,18,5,red);pixel(9,13,14,4,runeGold);pixel(11,17,10,4,red);pixel(14,21,4,4,runeGold);pixel(15,25,2,4,steel);}
            else if(id=="bouncy_ball"){var c=new Color(.95f,.35f,.55f);pixel(11,6,10,20,c);pixel(7,10,18,12,c);pixel(9,8,14,16,c);pixel(11,9,4,3,Color.white);pixel(7,15,18,2,runeGold);}
            else if(id=="long_whip"){pixel(4,22,3,8,wood);pixel(6,18,4,4,wood);pixel(9,14,4,4,new Color(.55f,.36f,.2f));pixel(13,11,5,3,new Color(.55f,.36f,.2f));pixel(18,9,5,3,new Color(.62f,.42f,.24f));pixel(23,10,4,3,new Color(.62f,.42f,.24f));pixel(26,13,3,4,new Color(.7f,.5f,.3f));}
        }
        // Called from DrawCombatRuneBar in place of the empty placeholder row; GUI.enabled is set by the caller.
        private void DrawSquadGearSlots(MmoActor self)
        {
            squadGearTip=null;var b=squadSnapshot?.battle;Vector2 mouse=Event.current.mousePosition;
            for(int i=0;i<MmoItemSlots.Length;i++)
            {
                var slot=MmoItemSlots[i];
                string stack=b==null?"":i==0?b.weapon:i==1?b.armor:i<2+SquadBagSize&&b.bag!=null&&i-2<b.bag.Length?b.bag[i-2]:"";
                bool filled=!string.IsNullOrEmpty(stack);
                // Stacked gear "id*2" / "id*3" (backend squad_items.tier): silver / gold frame, x2 / x3 effect.
                string id=filled?stack.Split('*')[0]:"";int tier=filled&&stack.Contains("*")?int.Parse(stack.Split('*')[1]):1;
                DrawRuneSlot(slot,-1,0);
                if(tier>=2)
                {
                    var c=tier==2?new Color(.82f,.84f,.9f):new Color(1,.8f,.25f);
                    Fill(new Rect(slot.x,slot.y,slot.width,2),c);Fill(new Rect(slot.x,slot.yMax-2,slot.width,2),c);
                    Fill(new Rect(slot.x,slot.y,2,slot.height),c);Fill(new Rect(slot.xMax-2,slot.y,2,slot.height),c);
                }
                if(filled)SquadItemIcon(new Rect(slot.x+4,slot.y+4,slot.width-8,slot.height-8),id);
                BaseText(new Rect(slot.x+2,slot.y,18,14),SquadSlotKey(i),10,new Color(1,1,1,.45f),TextAnchor.UpperLeft);
                // Right-click equips bag gear (GUI.Button only takes the left button).
                var e=Event.current;
                if(filled&&GUI.enabled&&i>=2&&SquadIsGear(id)&&e.type==EventType.MouseDown&&e.button==1&&slot.Contains(mouse)){rtsItem=i;e.Use();}
                if(filled&&GUI.Button(slot,GUIContent.none,GUIStyle.none))SquadUseSlot(i,Event.current.control);
                if(filled&&slot.Contains(mouse))
                {
                    string key=SquadSlotKey(i),action=i<2?"":SquadIsGear(id)?L.F("[{0}] 또는 우클릭 장착 · ",key):L.F("[{0}] 사용 · 1회용 · ",key);
                    string grade=tier==2?"\n"+L.T("은색 · 같은 장비 2개 · 효과 2배"):tier==3?"\n"+L.T("금색 · 같은 장비 3개 · 효과 3배"):"";
                    squadGearTip=SquadGearName(id)+grade+"\n"+L.F("{0}Ctrl+{1} 버리기",action,key);squadGearTipAnchor=slot;
                }
            }
            // Enemy curses: the sealed action slot turns red with the seconds left.
            if(self==null)return;
            SquadCurse(mmoAttackButton,self.curse_attack_left);SquadCurse(mmoSkill1Button,self.curse_skill_left);SquadCurse(mmoSkill2Button,self.curse_ultimate_left);
        }
        private void SquadCurse(Rect slot,float left)
        {
            if(left<=0)return;
            Fill(slot,new Color(.55f,.05f,.1f,.7f));
            BaseText(slot,L.T("봉인")+"\n"+Mathf.CeilToInt(left),10,Color.white,TextAnchor.MiddleCenter);
            if(slot.Contains(Event.current.mousePosition)){squadGearTip=L.F("저주로 봉인됨 · {0}초 남음",Mathf.CeilToInt(left));squadGearTipAnchor=slot;}
        }
        // Server names stacked gear "도끼 x2": translate the name, keep the count.
        private static string SquadStackName(string name){int k=name.LastIndexOf(" x");return k>0?L.T(name.Substring(0,k))+name.Substring(k):L.T(name);}
        private void DrawSquadGearTip(){if(squadGearTip!=null)DrawRtsTip(squadGearTipAnchor,squadGearTip);}
        // Names over items lying on the ground (3D bundles in SquadItemVisual); walk over one with a free slot to pick it up.
        private void DrawSquadGroundLabels()
        {
            var items=mmoWorld?.ground_items;if(items==null||retroScene==null)return;
            foreach(var g in items)
                if(g!=null&&g.floor==mmoWorld.floor&&MinimapPointVisible(g.x,g.y)&&retroScene.Project(g.x,g.y,.9f,out var p))
                    BaseText(new Rect(mmoField.x+p.x-70,mmoField.y+p.y-20,140,18),SquadStackName(g.name),11,runeGold,TextAnchor.MiddleCenter);
        }

        // Curse notices: the caster gets a gold banner, the cursed player a short red popup.
        private string squadNoticeCode,squadNoticeText;private int squadNoticeSeen;private bool squadNoticeAlert;private float squadNoticeUntil;
        private void DrawSquadNotice()
        {
            var b=squadSnapshot?.battle;if(b==null)return;
            // A new match (or rejoin) only records the current id so an old notice is not replayed.
            if(squadSnapshot.code!=squadNoticeCode){squadNoticeCode=squadSnapshot.code;squadNoticeSeen=b.notice_id;squadNoticeUntil=0;}
            else if(b.notice_id!=squadNoticeSeen){squadNoticeSeen=b.notice_id;squadNoticeText=b.notice;squadNoticeAlert=b.notice_alert;squadNoticeUntil=Time.realtimeSinceStartup+3;}
            float left=squadNoticeUntil-Time.realtimeSinceStartup;if(left<=0||string.IsNullOrEmpty(squadNoticeText))return;
            float a=Mathf.Clamp01(left/.5f);
            if(squadNoticeAlert)
            {
                var box=new Rect(440,190,400,112);
                Fill(box,new Color(.08f,.02f,.04f,.92f*a));Fill(new Rect(box.x,box.y,box.width,30),new Color(.6f,.06f,.12f,a));
                BaseText(new Rect(box.x,box.y,box.width,30),L.T("저주"),16,new Color(1,1,1,a),TextAnchor.MiddleCenter);
                BaseText(new Rect(box.x+12,box.y+34,box.width-24,box.height-40),L.T(squadNoticeText),17,new Color(1,.85f,.85f,a),TextAnchor.MiddleCenter);
            }
            else
            {
                var strip=new Rect(340,120,600,44);
                Fill(strip,new Color(.05f,.04f,.08f,.75f*a));
                BaseText(strip,L.T(squadNoticeText),20,new Color(runeGold.r,runeGold.g,runeGold.b,a),TextAnchor.MiddleCenter);
            }
        }
    }
}

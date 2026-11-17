using System;
using System.Collections.Generic;
using UnityEngine;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private int equipmentFilter;
        private string equipmentSelected="";
        private static readonly string[] GearSlots={"helmet","armor","weapon"};
        private string GearSlotName(string slot)=>slot=="helmet"?"투구":slot=="armor"?"방어구":"주무기";
        private Color GearColor(int rarity)=>rarity>=3?runeGold:rarity==2?runePurple:rarity==1?new Color(.38f,.66f,.95f):new Color(.6f,.58f,.63f);
        private MmoItem GearItem(string id){if(mmoProfile?.inventory!=null)foreach(var item in mmoProfile.inventory)if(item.id==id)return item;return null;}
        private string GearEquipped(string slot)=>slot=="helmet"?mmoProfile.equipped_helmet:slot=="armor"?mmoProfile.equipped_armor:mmoProfile.equipped_weapon;
        private int GearRank(string slot)=>slot=="helmet"?mmoProfile.helmet_rank:slot=="armor"?mmoProfile.armor_rank:mmoProfile.weapon_rank;
        private void GearIcon(Rect rect,string slot,Color tint)
        {
            // Crisp icon silhouettes match the existing pixel models without external font glyphs.
            float s=Mathf.Min(rect.width,rect.height)/32;Vector2 o=rect.center-Vector2.one*16*s;
            Action<float,float,float,float,Color> pixel=(x,y,w,h,c)=>Fill(new Rect(o.x+x*s,o.y+y*s,w*s,h*s),c);
            var steel=new Color(.45f,.43f,.52f);var dark=new Color(.14f,.13f,.20f);
            if(slot=="helmet"){
                pixel(8,6,16,19,steel);pixel(5,12,22,10,steel);pixel(8,15,16,5,dark);pixel(9,16,6,2,tint);pixel(18,16,5,2,tint);pixel(15,4,3,24,new Color(.64f,.6f,.69f));
            }else if(slot=="armor"){
                pixel(7,8,18,21,steel);pixel(3,7,8,9,steel);pixel(21,7,8,9,steel);pixel(12,6,8,6,dark);pixel(11,16,10,2,tint);pixel(15,12,2,13,tint);pixel(7,25,18,3,dark);
            }else{
                pixel(15,3,5,17,steel);pixel(17,2,2,15,new Color(.8f,.78f,.88f));pixel(9,19,18,3,tint);pixel(16,22,4,8,new Color(.35f,.21f,.15f));pixel(14,28,8,3,tint);
            }
        }
        private void GearSlot(Rect rect,string slot)
        {
            var item=GearItem(GearEquipped(slot));var color=item==null?baseMuted:GearColor(item.rarity);
            RuneFrame(rect,false,item!=null);GearIcon(new Rect(rect.x+16,rect.y+10,rect.width-32,rect.height-38),slot,color);
            BaseText(new Rect(rect.x+4,rect.yMax-28,rect.width-8,21),GearSlotName(slot),12,color,TextAnchor.MiddleCenter);
            if(GUI.Button(rect,GUIContent.none,GUIStyle.none)&&item!=null)equipmentSelected=item.id;
        }
        private void DrawMmoEquipmentPanel()
        {
            var p=mmoProfile;
            Fill(new Rect(0,0,1280,720),new Color(.035f,.028f,.05f,.97f));
            RuneFrame(new Rect(24,16,1232,686),true);
            RuneFrame(new Rect(380,25,520,52),true,true);
            BaseText(new Rect(390,28,500,42),"인벤토리 · 캐릭터 장비",27,runeText,TextAnchor.MiddleCenter);
            if(RuneButton(new Rect(1137,31,99,34),"닫기")){CloseMmoPanel();return;}
            if(p==null){BaseText(new Rect(100,150,1050,60),mmoError.Length>0?mmoError:"장비 정보를 불러오는 중…",22,runeText);return;}
            bool previous=GUI.enabled;GUI.enabled=previous&&!mmoRequest;
            for(int i=0;i<3;i++){
                int index=i;bool active=p.active_loadout==i;
                if(RuneButton(new Rect(48+i*208,92,198,48),$"장비 세트 {i+1}"+(active?" · 사용 중":""),active))MmoCommand(c=>c.MmoLoadoutAsync(index));
            }
            RuneFrame(new Rect(48,152,614,372));
            BaseText(new Rect(66,164,570,26),$"장비 세트 {p.active_loadout+1}  ·  LV {p.level} 모험가",18,runeGold);
            // rpg.html: helmet above the model, armor and weapon at its lower corners.
            if(retroScene!=null&&retroScene.Portrait!=null)GUI.DrawTexture(new Rect(230,274,252,238),retroScene.Portrait,ScaleMode.ScaleToFit,false);
            GearSlot(new Rect(310,200,96,98),"helmet");
            GearSlot(new Rect(80,354,110,112),"armor");GearSlot(new Rect(520,354,110,112),"weapon");
            BaseText(new Rect(210,489,285,22),"보라빛 룬의 수호자",15,runePurple,TextAnchor.MiddleCenter);
            RuneFrame(new Rect(48,536,614,142),true);
            BaseText(new Rect(68,546,570,25),$"캐릭터 능력치    공격력 {p.attack:0}     최대 HP {p.max_hp:0}     골드 {p.gold}",16,runeGold);
            for(int i=0;i<3;i++){
                string slot=GearSlots[i];int rank=GearRank(slot);bool old=GUI.enabled;GUI.enabled=old&&rank<20&&p.gold>=50*(rank+1);
                if(RuneButton(new Rect(64+i*196,583,188,47),$"{GearSlotName(slot)} +{rank}\n"+(rank>=20?"최고 강화":$"강화 {50*(rank+1)} G")))MmoCommand(c=>c.MmoUpgradeAsync(slot));GUI.enabled=old;
            }
            BaseText(new Rect(68,640,570,22),"각 세트는 서버에 저장됩니다 · 강화 수치는 모든 세트에 공통 적용",11,baseMuted);
            RuneFrame(new Rect(682,92,550,332));
            BaseText(new Rect(700,101,510,25),$"보유 장비 가방   {p.inventory?.Length??0} / 100",18,runeText);
            string[] filters={"전체","투구","방어구","주무기"};
            for(int i=0;i<4;i++)if(RuneButton(new Rect(700+i*128,138,120,31),filters[i],equipmentFilter==i)){equipmentFilter=i;mmoInventoryScroll=Vector2.zero;}
            var items=new List<MmoItem>();if(p.inventory!=null)foreach(var item in p.inventory)if(equipmentFilter==0||item.slot==GearSlots[equipmentFilter-1])items.Add(item);
            mmoInventoryScroll=GUI.BeginScrollView(new Rect(700,181,516,228),mmoInventoryScroll,new Rect(0,0,492,Mathf.Max(219,Mathf.CeilToInt(items.Count/6f)*91)));
            for(int i=0;i<items.Count;i++){
                var item=items[i];var rect=new Rect(i%6*81,i/6*91,74,84);var color=GearColor(item.rarity);
                RuneFrame(rect,false,equipmentSelected==item.id);Fill(new Rect(rect.x+6,rect.y+6,rect.width-12,2),color);GearIcon(new Rect(rect.x+13,rect.y+10,48,47),item.slot,color);
                BaseText(new Rect(rect.x+4,rect.y+58,66,20),item.equipped?"장착 중":$"위력 {item.power}",11,item.equipped?runePurple:color,TextAnchor.MiddleCenter);
                if(GUI.Button(rect,GUIContent.none,GUIStyle.none))equipmentSelected=item.id;
            }
            if(items.Count==0)BaseText(new Rect(10,40,470,80),"이 종류의 장비가 없습니다.\n사냥터에서 적을 처치해 장비를 획득하세요.",16,baseMuted,TextAnchor.MiddleCenter);
            GUI.EndScrollView();
            RuneFrame(new Rect(682,437,550,241),true);
            var selected=GearItem(equipmentSelected);
            if(selected==null)BaseText(new Rect(710,475,490,120),"가방의 장비를 선택하세요\n현재 장착품과 비교하고 장착할 수 있습니다",18,baseMuted,TextAnchor.MiddleCenter);
            else{
                var worn=GearItem(GearEquipped(selected.slot));int delta=selected.power-(worn?.power??0);
                BaseText(new Rect(705,452,500,30),selected.name,22,GearColor(selected.rarity));
                BaseText(new Rect(705,490,500,25),$"{GearSlotName(selected.slot)} · 등급 {selected.rarity} · 위력 {selected.power}",16,runeText);
                BaseText(new Rect(705,524,500,45),$"현재 장착: {worn?.name??"없음"}\n{(selected.slot=="weapon"?"공격력":"최대 HP")} 변화  {delta:+0;-0;0}",14,delta>0?new Color(.5f,.85f,.55f):delta<0?new Color(1,.48f,.4f):baseMuted);
                bool old=GUI.enabled;GUI.enabled=old&&!selected.equipped;
                if(RuneButton(new Rect(705,587,502,49),selected.equipped?"현재 세트에 장착 중":$"장비 세트 {p.active_loadout+1}에 장착",true))MmoCommand(c=>c.MmoEquipAsync(selected.id));GUI.enabled=old;
                BaseText(new Rect(705,643,500,20),"같은 장비를 여러 세트에 저장할 수 있습니다",11,baseMuted);
            }
            GUI.enabled=previous;
            if(mmoRequest)BaseText(new Rect(704,682,500,19),"서버에 장비 변경을 저장하는 중…",12,runeGold);
            else if(mmoError.Length>0)BaseText(new Rect(704,682,500,19),mmoError,12,runeGold);
        }
    }
}

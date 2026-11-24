using UnityEngine;
namespace Warfront
{
    // Character stats panel between the skill bar and the minimap, plus hover popups for stats and skills.
    public sealed partial class GameBootstrap
    {
        private static readonly Rect RtsStatsRect=new Rect(926,594,128,112);
        private ZodiacCharacter RtsCharacterRules
        {
            get{var b=squadSnapshot?.battle;if(b?.characters!=null)foreach(var c in b.characters)if(c.id==b.character)return c;return null;}
        }
        private void DrawRtsStatsAndTips()
        {
            var stats=squadSnapshot?.battle?.stats;var self=MmoSelf;var rules=RtsCharacterRules;
            if(stats==null||self==null||rules==null)return;
            Vector2 mouse=Event.current.mousePosition;string tip=null;Rect anchor=default;
            RuneFrame(RtsStatsRect,true);
            string range=L.T(rules.reach>=400?"장거리":"단거리");
            BaseText(new Rect(934,597,112,16),L.T(rules.name)+" · "+range,11,runeGold,TextAnchor.MiddleCenter);
            string[] labels={"HP",L.T("공격력"),L.T("물리 방어력"),L.T("마법 방어력"),L.T("스피드")};
            string[] values={$"{self.hp:0}/{self.max_hp:0}",$"{stats.attack:0.#}",$"{stats.armor:0}",$"{stats.magic_armor:0}",$"{stats.speed:0}"};
            string[] tips={null,L.F("HP 흡수율 {0:0}%",stats.lifesteal*100),L.F("물리 방어력 무시 {0:0}%",stats.armor_pen*100),L.F("마법 방어력 무시 {0:0}%",stats.magic_pen*100),null};
            for(int i=0;i<labels.Length;i++)
            {
                var row=new Rect(934,614+i*18,112,17);
                bool hover=tips[i]!=null&&row.Contains(mouse);
                if(hover){Fill(row,new Color(1,1,1,.08f));tip=tips[i];anchor=row;}
                BaseText(new Rect(row.x,row.y,64,row.height),labels[i],10,tips[i]!=null?runeGold:runeText); // gold label = hover for details
                BaseText(new Rect(row.x+60,row.y,52,row.height),values[i],11,Color.white,TextAnchor.MiddleRight);
            }
            if(mmoPanel.Length==0)
            {
                if(mmoAttackButton.Contains(mouse)){tip=L.F("기본 공격 · {0}\n{1} 물리 공격 (공격력 {2:0.#})",L.T(rules.basic),range,stats.attack);anchor=mmoAttackButton;}
                if(mmoSkill1Button.Contains(mouse)){tip=L.F("스킬 Q · {0}  (재사용 {1:0}초, 마법 피해)\n{2}",L.T(rules.q),rules.q_cooldown>0?rules.q_cooldown:6,L.T(rules.q_desc));anchor=mmoSkill1Button;}
                if(mmoSkill2Button.Contains(mouse)){tip=L.F("필살기 E · {0}  (재사용 22초, 마법 피해)\n{1}",L.T(rules.e),L.T(rules.e_desc));anchor=mmoSkill2Button;}
            }
            if(tip!=null)DrawRtsTip(anchor,tip);
        }
        // Translucent popup just above the hovered control; clamped to the 1280-wide UI.
        private void DrawRtsTip(Rect anchor,string text)
        {
            var rows=text.Split('\n');int longest=0;foreach(var r in rows)longest=Mathf.Max(longest,r.Length);
            float width=Mathf.Clamp(longest*10.5f+20,150,400),height=12+rows.Length*17;
            var rect=new Rect(Mathf.Clamp(anchor.center.x-width/2,8,1272-width),anchor.y-height-6,width,height);
            Fill(rect,new Color(.05f,.04f,.08f,.78f));Fill(new Rect(rect.x,rect.y,rect.width,2),new Color(runeGold.r,runeGold.g,runeGold.b,.8f));
            BaseText(new Rect(rect.x+10,rect.y+6,rect.width-20,rect.height-12),text,11,runeText,TextAnchor.UpperLeft);
        }
    }
}

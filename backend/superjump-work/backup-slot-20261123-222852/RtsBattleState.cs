using System;
using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    [Serializable] public sealed class ZodiacCharacter { public string id,name,q,e,q_kind,e_kind,basic,q_desc,e_desc; public float reach,q_cooldown; }
    [Serializable] public sealed class ZodiacStats { public float hp,attack,armor,magic_armor,speed,armor_pen,magic_pen,lifesteal; }
    [Serializable] public sealed class RtsBattleState
    {
        public bool rts,character_locked;
        public string character,weapon,armor;
        public string[] bag;
        public string notice;public int notice_id;public bool notice_alert;// one-shot curse message (squad_items.notify)
        public float next_wave;
        public RtsPing[] pings;
        public ZodiacCharacter[] characters;
        public ZodiacStats stats;
    }
    public sealed partial class GameBootstrap
    {
        private string rtsCharacter="rat";
        private bool rtsJump;
        private int rtsItem=-1,rtsDrop=-1;// inventory slot 0..9 to use / drop this send (number keys, Ctrl+number, clicks)
        private void ResetRtsIntents(){rtsJump=false;rtsItem=rtsDrop=-1;rtsOrder="none";rtsTarget="";}
        private static readonly string[] ZodiacIds={"rat","ox","tiger","rabbit","dragon","snake","horse","goat","monkey","rooster","dog","pig"};
        private static readonly string[] ZodiacNames={"쥐","소","호랑이","토끼","용","뱀","말","양","원숭이","닭","개","돼지"};
        private bool RetiredWorldEntry(){OpenSquadLobby();return true;}
        private void DrawRtsCharacterSelection(Rect area)
        {
            int columns=area.width<250?3:6, rows=(12+columns-1)/columns;
            float w=area.width/columns,h=area.height/rows;
            bool previous=GUI.enabled;GUI.enabled=previous&&!squadRequest;
            for(int i=0;i<12;i++)
            {
                var r=new Rect(area.x+(i%columns)*w,area.y+(i/columns)*h,w-4,h-4);
                if(RuneButton(r,(rtsCharacter==ZodiacIds[i]?"● ":"")+L.T(ZodiacNames[i])))rtsCharacter=ZodiacIds[i];
            }
            GUI.enabled=previous;
        }


    }
}

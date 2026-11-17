using UnityEngine;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private static Texture2D runeStone,runeWood;
        private static readonly Color runePurple=new Color(.72f,.40f,1),runeGold=new Color(.83f,.68f,.43f),runeText=new Color(.91f,.87f,.81f);
        private static Texture2D RuneSurface(bool wood)
        {
            if(wood&&runeWood!=null)return runeWood;if(!wood&&runeStone!=null)return runeStone;
            var texture=new Texture2D(64,64,TextureFormat.RGBA32,false){name=wood?"Rune walnut":"Rune slate",filterMode=FilterMode.Point,wrapMode=TextureWrapMode.Repeat,hideFlags=HideFlags.HideAndDontSave};
            var colors=new Color[4096];for(int y=0;y<64;y++)for(int x=0;x<64;x++){
                int hash=((x*13+y*71)^(x*y*7))&31;float grain=hash/31f;
                bool seam=wood?y%16==0:y%24==0||(x+(y/24%2)*21)%42==0;
                colors[y*64+x]=seam?new Color(.08f,.065f,.08f):wood?new Color(.18f+grain*.045f,.115f+grain*.03f,.09f+grain*.025f):new Color(.23f+grain*.045f,.215f+grain*.04f,.255f+grain*.045f);
            }
            texture.SetPixels(colors);texture.Apply(false,true);if(wood)runeWood=texture;else runeStone=texture;return texture;
        }
        private void RuneFrame(Rect rect,bool wood=false,bool selected=false)
        {
            Fill(new Rect(rect.x+3,rect.y+5,rect.width,rect.height),new Color(0,0,0,.45f));
            GUI.DrawTextureWithTexCoords(rect,RuneSurface(false),new Rect(0,0,rect.width/64,rect.height/64));
            Fill(new Rect(rect.x+2,rect.y+2,rect.width-4,2),selected?runePurple:new Color(.45f,.41f,.46f));
            Fill(new Rect(rect.x+2,rect.y+2,2,rect.height-4),new Color(.40f,.37f,.43f));
            Fill(new Rect(rect.xMax-3,rect.y+3,2,rect.height-6),new Color(.10f,.09f,.12f));
            Fill(new Rect(rect.x+3,rect.yMax-4,rect.width-6,3),new Color(.09f,.08f,.10f));
            var inside=new Rect(rect.x+7,rect.y+7,rect.width-14,rect.height-14);
            if(wood)GUI.DrawTextureWithTexCoords(inside,RuneSurface(true),new Rect(0,0,inside.width/64,inside.height/64));else Fill(inside,new Color(.065f,.065f,.095f,.97f));
            foreach(var point in new[]{new Vector2(rect.x+2,rect.y+2),new Vector2(rect.xMax-10,rect.y+2),new Vector2(rect.x+2,rect.yMax-10),new Vector2(rect.xMax-10,rect.yMax-10)}){
                Fill(new Rect(point.x,point.y,8,8),new Color(.31f,.28f,.34f));Fill(new Rect(point.x+2,point.y+2,2,2),selected?runePurple:runeGold);
            }
        }
        private bool RuneButton(Rect rect,string title,bool selected=false)
        {
            bool hover=GUI.enabled&&rect.Contains(Event.current.mousePosition);RuneFrame(rect,true,selected||hover);
            BaseText(new Rect(rect.x+8,rect.y+3,rect.width-16,rect.height-6),title,14,GUI.enabled?selected?runePurple:runeText:baseMuted,TextAnchor.MiddleCenter);
            return GUI.Button(rect,GUIContent.none,GUIStyle.none);
        }
        private void DrawRuneControl(Rect rect,string title,int icon)
        {
            RuneFrame(rect,true,MmoHeld(rect));
            if(icon>=0&&icon<12){LoadWidgetArt();if(widgetIcons!=null)GUI.DrawTexture(new Rect(rect.x+9,rect.y+10,43,43),widgetIcons[icon],ScaleMode.ScaleToFit,true);}
            BaseText(new Rect(rect.x+(icon>=0?52:8),rect.y+4,rect.width-(icon>=0?57:16),rect.height-8),title,12,runeText,TextAnchor.MiddleCenter);
        }
    }
}

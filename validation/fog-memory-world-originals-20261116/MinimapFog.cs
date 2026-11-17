using System;
using UnityEngine;

namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        // Same 1000-unit visibility distance used by the encounter HUD.
        private const float MinimapSightRadius=1000f;
        private const int MinimapFogWidth=180,MinimapFogHeight=120;
        private static readonly Color32 MinimapUnknown=new Color32(43,43,43,255);
        private Texture2D mmoMinimapFog;
        private readonly bool[] mmoMinimapVisible=new bool[MinimapFogWidth*MinimapFogHeight];
        private readonly Color32[] mmoMinimapFogPixels=new Color32[MinimapFogWidth*MinimapFogHeight];
        private MmoSnapshot mmoMinimapFogSnapshot;
        private string mmoMinimapFogWorld="";
        private float mmoMinimapFogNext;

        private bool MinimapSameFloor(int floor)=>mmoWorld==null||mmoWorld.floor<=0||floor<=0||floor==mmoWorld.floor;
        private bool MinimapAlly(MmoActor actor)=>actor!=null&&actor.hp>0&&MinimapSameFloor(actor.floor)&&
            (SquadModeActive?squadSnapshot!=null&&actor.team==squadSnapshot.team:actor.id==mmoWorld.you_id||(!string.IsNullOrEmpty(mmoParty?.code)&&actor.party_code==mmoParty.code));
        private void UpdateMinimapFog(bool force=false)
        {
            if(mmoWorld==null)return;
            string world=mmoWorld.zone+":"+mmoWorld.instance_id+":"+mmoWorld.floor;
            if(!force&&mmoMinimapFogSnapshot==mmoWorld&&mmoMinimapFogWorld==world&&Time.realtimeSinceStartup<mmoMinimapFogNext)return;
            mmoMinimapFogSnapshot=mmoWorld;mmoMinimapFogWorld=world;mmoMinimapFogNext=Time.realtimeSinceStartup+.10f;
            Array.Clear(mmoMinimapVisible,0,mmoMinimapVisible.Length);
            if(mmoWorld.players!=null)foreach(var actor in mmoWorld.players)if(MinimapAlly(actor))RevealMinimapCircle(actor.x,actor.y);
            // Some squad snapshot versions place same-team units in enemies.
            if(SquadModeActive&&squadSnapshot!=null)
            {
                if(mmoWorld.enemies!=null)foreach(var actor in mmoWorld.enemies)
                    if(actor!=null&&actor.hp>0&&actor.team==squadSnapshot.team&&MinimapSameFloor(actor.floor))RevealMinimapCircle(actor.x,actor.y);
                if(squadSnapshot.bases!=null)foreach(var headquarters in squadSnapshot.bases)
                    if(headquarters.hp>0&&headquarters.team==squadSnapshot.team&&MinimapSameFloor(headquarters.floor))RevealMinimapCircle(headquarters.x,headquarters.y);
            }
            for(int y=0;y<MinimapFogHeight;y++)for(int x=0;x<MinimapFogWidth;x++)
                mmoMinimapFogPixels[(MinimapFogHeight-1-y)*MinimapFogWidth+x]=mmoMinimapVisible[y*MinimapFogWidth+x]?new Color32(0,0,0,0):MinimapUnknown;
            if(mmoMinimapFog==null)mmoMinimapFog=new Texture2D(MinimapFogWidth,MinimapFogHeight,TextureFormat.RGBA32,false){name="Current allied minimap vision",filterMode=FilterMode.Point,wrapMode=TextureWrapMode.Clamp,hideFlags=HideFlags.HideAndDontSave};
            mmoMinimapFog.SetPixels32(mmoMinimapFogPixels);mmoMinimapFog.Apply(false,false);
        }
        private void RevealMinimapCircle(float x,float y)
        {
            var size=MmoMapWorldSize;
            if(x<0||y<0||x>size.x||y>size.y)return;
            int left=Mathf.Clamp(Mathf.FloorToInt((x-MinimapSightRadius)/size.x*MinimapFogWidth),0,MinimapFogWidth-1);
            int right=Mathf.Clamp(Mathf.CeilToInt((x+MinimapSightRadius)/size.x*MinimapFogWidth),0,MinimapFogWidth-1);
            int top=Mathf.Clamp(Mathf.FloorToInt((y-MinimapSightRadius)/size.y*MinimapFogHeight),0,MinimapFogHeight-1);
            int bottom=Mathf.Clamp(Mathf.CeilToInt((y+MinimapSightRadius)/size.y*MinimapFogHeight),0,MinimapFogHeight-1);
            for(int row=top;row<=bottom;row++)for(int column=left;column<=right;column++)
            {
                float dx=(column+.5f)/MinimapFogWidth*size.x-x,dy=(row+.5f)/MinimapFogHeight*size.y-y;
                if(dx*dx+dy*dy<=MinimapSightRadius*MinimapSightRadius)mmoMinimapVisible[row*MinimapFogWidth+column]=true;
            }
        }
        private bool MinimapPointVisible(float x,float y)
        {
            var size=MmoMapWorldSize;
            if(x<0||y<0||x>size.x||y>size.y)return false;
            int column=Mathf.Clamp((int)(x/size.x*MinimapFogWidth),0,MinimapFogWidth-1);
            int row=Mathf.Clamp((int)(y/size.y*MinimapFogHeight),0,MinimapFogHeight-1);
            return mmoMinimapVisible[row*MinimapFogWidth+column];
        }
        private void DisposeMinimapFog()
        {
            if(mmoMinimapFog!=null){if(Application.isPlaying)Destroy(mmoMinimapFog);else DestroyImmediate(mmoMinimapFog);}
            mmoMinimapFog=null;mmoMinimapFogSnapshot=null;mmoMinimapFogWorld="";
            Array.Clear(mmoMinimapVisible,0,mmoMinimapVisible.Length);
        }
    }
}

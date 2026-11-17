using System.Collections.Generic;
using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        private readonly List<Texture2D> runeGroundTextures=new List<Texture2D>();
        private void InitializeRuneGround()
        {
            var source=Resources.Load<Material>("MiniDungeon/Materials/Floor");if(source==null)return;
            foreach(var entry in textureNames){
                bool grass=entry.Key=="grass",wood=entry.Key=="planks"||entry.Key=="roof"||entry.Key=="barrel"||entry.Key=="fence";
                var texture=new Texture2D(32,32,TextureFormat.RGBA32,false){name="Rune terrain "+entry.Key,filterMode=FilterMode.Point,wrapMode=TextureWrapMode.Repeat,hideFlags=HideFlags.HideAndDontSave};
                var pixels=new Color[1024];for(int y=0;y<32;y++)for(int x=0;x<32;x++){
                    float noise=(((x*19+y*73)^(x*y*11))&31)/31f;
                    bool seam=wood?y%8==0:y%16==0||(x+(y/16%2)*8)%16==0;
                    pixels[y*32+x]=grass?new Color(.20f+noise*.075f,.245f+noise*.08f,.15f+noise*.055f):wood?
                        seam?new Color(.13f,.085f,.065f):new Color(.24f+noise*.07f,.15f+noise*.05f,.10f+noise*.04f):
                        seam?new Color(.13f,.12f,.15f):new Color(.32f+noise*.055f,.30f+noise*.05f,.34f+noise*.06f);
                }
                texture.SetPixels(pixels);texture.Apply(false,true);runeGroundTextures.Add(texture);
                var material=new Material(source){name="Rune environment "+entry.Key,hideFlags=HideFlags.HideAndDontSave};material.SetTexture("_BaseMap",texture);material.SetColor("_BaseColor",Color.white);materials[entry.Key]=material;
            }
        }
        private void DisposeRuneGround(){foreach(var material in materials.Values)if(material!=null&&material.name.StartsWith("Rune environment"))RemoveOwned(material);foreach(var texture in runeGroundTextures)if(texture!=null)RemoveOwned(texture);runeGroundTextures.Clear();}
    }
}

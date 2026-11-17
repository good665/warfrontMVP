using System.Collections.Generic;
using UnityEngine;

namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private sealed class CombatPulse { public float x,y,started,damage,height=1.7f; public string target; public int lane; public bool death,self; }
        private readonly List<CombatPulse> mmoCombatPulses=new List<CombatPulse>();
        private AudioSource mmoImpactSource;
        private AudioClip mmoImpactClip;
        private AudioClip mmoHurtClip;
        private float mmoNextImpactSound;
        private float mmoNextHurtSound;

        // HP transitions are authoritative and naturally idempotent across repeated snapshots.
        private void MmoApplyCombatFeedback(MmoSnapshot previous,MmoSnapshot current)
        {
            if(current==null)return;
            if(previous==null||previous.zone!=current.zone||previous.instance_id!=current.instance_id||previous.you_id!=current.you_id)
            {ResetMmoCombatFeedback();return;}
            bool impact=false,death=false,hurt=false;
            if(current.enemies!=null&&previous.enemies!=null)foreach(var enemy in current.enemies)
                foreach(var old in previous.enemies)if(old.id==enemy.id)
                {
                    if(Mathf.Min(old.hp,enemy.max_hp>0?enemy.max_hp:old.hp)>enemy.hp&&old.hp>0)
                    {
                        bool killed=enemy.hp<=0;AddMmoCombatPulse(enemy.x,enemy.y,killed,false,Mathf.Min(old.hp,enemy.max_hp>0?enemy.max_hp:old.hp)-enemy.hp,"enemy:"+enemy.id,enemy.kind=="base"?3.6f:enemy.kind=="boss"?2.55f:1.8f);
                        if(retroScene!=null)retroScene.EnemyImpact(enemy.id,killed);
                        impact=true;death|=killed;
                    }
                    break;
                }
            if(current.players!=null&&previous.players!=null)foreach(var actor in current.players)
                foreach(var old in previous.players)if(old.id==actor.id)
                {
                    float damage=Mathf.Min(old.hp,actor.max_hp>0?actor.max_hp:old.hp)-actor.hp;
                    if(damage>0&&old.hp>0)
                    {
                        bool own=actor.id==current.you_id;
                        AddMmoCombatPulse(actor.x,actor.y,actor.hp<=0,own,damage,"player:"+actor.id);
                        if(own&&retroScene!=null)retroScene.PlayerImpact(actor.id);
                        impact=true;hurt|=own;
                    }
                    break;
                }
            if(impact)PlayMmoImpact(death,hurt);
        }
        private void AddMmoCombatPulse(float x,float y,bool death,bool self,float damage=0,string target=null,float height=1.7f)
        {
            if(mmoCombatPulses.Count>=32)mmoCombatPulses.RemoveAt(0);
            int lane=0;foreach(var previous in mmoCombatPulses)if(previous.target==target&&Time.realtimeSinceStartup-previous.started<.25f)lane++;
            mmoCombatPulses.Add(new CombatPulse{x=x,y=y,death=death,self=self,damage=damage,target=target,height=height,lane=lane%4,started=Time.realtimeSinceStartup});
        }
        private void DrawMmoCombatFeedback()
        {
            if(mmoWorld==null||retroScene==null)return;
            if(mmoWorld.enemies!=null)foreach(var enemy in mmoWorld.enemies)
            {
                if(enemy.hp<=0||enemy.windup_left<=0)continue;
                if(!retroScene.Project(enemy.x,enemy.y,enemy.kind=="boss"?2.55f:1.8f,out var point))continue;
                point.y-=34; // Keep the warning above the existing name and health bar.
                float progress=Mathf.Clamp01(1-enemy.windup_left/Mathf.Max(.01f,enemy.windup_duration));
                Fill(new Rect(point.x-55,point.y-12,110,22),new Color(.16f,.04f,.02f,.94f));
                Fill(new Rect(point.x-55,point.y+9,110*progress,3),new Color(1,.45f,.12f));
                BaseText(new Rect(point.x-55,point.y-12,110,22),"공격 예고 "+Mathf.RoundToInt(progress*100)+"%",12,new Color(1,.78f,.45f),TextAnchor.MiddleCenter);
            }
            for(int i=mmoCombatPulses.Count-1;i>=0;i--)
            {
                var pulse=mmoCombatPulses[i];float age=Time.realtimeSinceStartup-pulse.started;
                float duration=.8f;
                if(age>=duration){mmoCombatPulses.RemoveAt(i);continue;}
                float alpha=1-age/duration;
                if(pulse.target!=null){
                    if(pulse.target.StartsWith("player:")&&mmoWorld.players!=null)foreach(var actor in mmoWorld.players)if(pulse.target=="player:"+actor.id){pulse.x=actor.x;pulse.y=actor.y;break;}
                    if(pulse.target.StartsWith("enemy:")&&mmoWorld.enemies!=null)foreach(var enemy in mmoWorld.enemies)if(pulse.target=="enemy:"+enemy.id){pulse.x=enemy.x;pulse.y=enemy.y;break;}
                }
                if(pulse.damage>0&&retroScene.Project(pulse.x,pulse.y,pulse.height,out var numberPoint))
                {
                    var tint=pulse.self?new Color(1,.48f,.32f,alpha):new Color(1,.9f,.5f,alpha);
                    var rect=new Rect(numberPoint.x-90,numberPoint.y-56-age*45-pulse.lane*22,180,34);
                    BaseText(new Rect(rect.x+1,rect.y+2,rect.width,rect.height),"-"+pulse.damage.ToString("0.#"),22,new Color(0,0,0,alpha),TextAnchor.MiddleCenter);
                    BaseText(rect,"-"+pulse.damage.ToString("0.#"),22,tint,TextAnchor.MiddleCenter);
                }
                if(pulse.self)
                {
                    float hurtFade=Mathf.Clamp01(1-age/.4f);float strength=hurtFade*hurtFade;
                    Fill(new Rect(0,0,mmoField.width,mmoField.height),new Color(.8f,.025f,.02f,strength*.065f));
                    for(int layer=0;layer<7;layer++)
                    {
                        float inset=layer*5;var tint=new Color(.95f,.04f,.025f,strength*(.38f-layer*.042f));
                        Fill(new Rect(inset,inset,mmoField.width-2*inset,5),tint);
                        Fill(new Rect(inset,mmoField.height-inset-5,mmoField.width-2*inset,5),tint);
                        Fill(new Rect(inset,inset+5,5,mmoField.height-2*inset-10),tint);
                        Fill(new Rect(mmoField.width-inset-5,inset+5,5,mmoField.height-2*inset-10),tint);
                    }
                    if(retroScene.Project(pulse.x,pulse.y,1.7f,out var hitPoint))
                    {
                        var tint=new Color(1,.48f,.32f,alpha);
                        float radius=15+age*55;
                        Fill(new Rect(hitPoint.x-radius-12,hitPoint.y-1,12,3),tint);Fill(new Rect(hitPoint.x+radius,hitPoint.y-1,12,3),tint);
                        Fill(new Rect(hitPoint.x-1,hitPoint.y-radius-12,3,12),tint);Fill(new Rect(hitPoint.x-1,hitPoint.y+radius,3,12),tint);
                    }
                }
                else if(retroScene.Project(pulse.x,pulse.y,1,out var point))
                {
                    var tint=new Color(1,.85f,.55f,alpha);float r=8+age*32;
                    Fill(new Rect(point.x-r-5,point.y-1,7,2),tint);Fill(new Rect(point.x+r-2,point.y-1,7,2),tint);
                    Fill(new Rect(point.x-1,point.y-r-5,2,7),tint);Fill(new Rect(point.x-1,point.y+r-2,2,7),tint);
                    if(pulse.death)BaseText(new Rect(point.x-70,point.y-35-age*30,140,24),"처치",18,tint,TextAnchor.MiddleCenter);
                }
            }
        }
        private void PlayMmoImpact(bool death,bool hurt=false)
        {
            if(!mmoImpactAudio||mmoImpactVolume<=0||Time.realtimeSinceStartup<(hurt?mmoNextHurtSound:mmoNextImpactSound))return;
            if(hurt)mmoNextHurtSound=Time.realtimeSinceStartup+.12f;else mmoNextImpactSound=Time.realtimeSinceStartup+.085f;
            if(mmoImpactSource==null)
            {
                mmoImpactSource=gameObject.AddComponent<AudioSource>();mmoImpactSource.playOnAwake=false;
                mmoImpactSource.spatialBlend=0;mmoImpactSource.loop=false;
            }
            if(!hurt&&mmoImpactClip==null)
            {
                const int rate=22050;var samples=new float[3308];uint seed=12345;
                for(int i=0;i<samples.Length;i++)
                {
                    float t=i/(float)rate,fade=Mathf.Exp(-t*38);seed=1664525u*seed+1013904223u;
                    float noise=((seed>>8)/(float)0xFFFFFF)*2-1;
                    samples[i]=(Mathf.Sin(2*Mathf.PI*(190*t-350*t*t))*.65f+noise*.35f)*fade*.6f*Mathf.Min(1,t*500);
                }
                mmoImpactClip=AudioClip.Create("Local combat impact",samples.Length,1,rate,false);mmoImpactClip.SetData(samples,0);
            }
            if(hurt&&mmoHurtClip==null)mmoHurtClip=CreateMmoHurtClip();
            mmoImpactSource.pitch=hurt?1:death?.72f:1;mmoImpactSource.PlayOneShot(hurt?mmoHurtClip:mmoImpactClip,Mathf.Clamp01(mmoImpactVolume));
        }
        private static AudioClip CreateMmoHurtClip()
        {
            const int rate=22050;var samples=new float[4851];uint seed=54321;
            for(int i=0;i<samples.Length;i++)
            {
                float t=i/(float)rate,fade=Mathf.Exp(-t*25);seed=1664525u*seed+1013904223u;
                float noise=((seed>>8)/(float)0xFFFFFF)*2-1;
                samples[i]=(Mathf.Sin(2*Mathf.PI*(95*t-120*t*t))*.78f+noise*.22f)*fade*.7f*Mathf.Min(1,t*650);
            }
            var clip=AudioClip.Create("Player hurt thud",samples.Length,1,rate,false);clip.SetData(samples,0);return clip;
        }
        private void ResetMmoCombatFeedback()
        {mmoCombatPulses.Clear();mmoNextImpactSound=mmoNextHurtSound=0;if(mmoImpactSource!=null)mmoImpactSource.Stop();if(retroScene!=null)retroScene.ClearPlayerImpacts();}
        private void DisposeMmoCombatFeedback()
        {
            ResetMmoCombatFeedback();if(mmoImpactSource!=null)Destroy(mmoImpactSource);mmoImpactSource=null;
            if(mmoImpactClip!=null)Destroy(mmoImpactClip);mmoImpactClip=null;
            if(mmoHurtClip!=null)Destroy(mmoHurtClip);mmoHurtClip=null;
        }
    }
}

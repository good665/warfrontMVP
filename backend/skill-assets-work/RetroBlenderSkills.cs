using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        private AnimationClip skillHeavyClip,skillThrowClip,skillDodgeClip;
        private void EnsureBlenderSkillClips(Animation animation)
        {
            if(skillHeavyClip==null)skillHeavyClip=Resources.Load<AnimationClip>("SkillVisuals/Heavy");
            if(skillThrowClip==null)skillThrowClip=Resources.Load<AnimationClip>("SkillVisuals/Throw");
            if(skillDodgeClip==null)skillDodgeClip=Resources.Load<AnimationClip>("SkillVisuals/Dodge");
            if(skillHeavyClip!=null&&animation.GetClip("Heavy")!=skillHeavyClip)animation.AddClip(skillHeavyClip,"Heavy");
            if(skillThrowClip!=null&&animation.GetClip("Throw")!=skillThrowClip)animation.AddClip(skillThrowClip,"Throw");
            if(skillDodgeClip!=null&&animation.GetClip("Dodge")!=skillDodgeClip)animation.AddClip(skillDodgeClip,"Dodge");
        }
        private Vector3 HeldBombPosition(MmoBomb bomb)
        {
            GameObject owner;
            if(actors.TryGetValue("player:"+bomb.owner_id,out owner)||actors.TryGetValue("enemy:"+bomb.owner_id,out owner))
            {
                var hand=owner.transform.Find("root/torso/arm-right");
                if(hand!=null)return field.transform.InverseTransformPoint(hand.TransformPoint(new Vector3(0,-.12f,.06f)));
            }
            return WorldPoint(bomb.start_x,bomb.start_y)+Vector3.up*.85f;
        }
    }
}

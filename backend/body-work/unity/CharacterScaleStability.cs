using System.Collections.Generic;
using UnityEngine;

namespace Warfront
{
    // Body proportions are immutable. Weapons and effects are intentionally excluded.
    [DefaultExecutionOrder(450)]
    public sealed class CharacterScaleStability : MonoBehaviour
    {
        private readonly Dictionary<Transform, Vector3> scales = new Dictionary<Transform, Vector3>();
        public void Capture()
        {
            if(scales.Count>0)return;
            scales.Add(transform,transform.localScale);
            foreach(var skin in GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                skin.updateWhenOffscreen=true;
                foreach(var bone in skin.bones)
                    if(bone!=null&&!scales.ContainsKey(bone))scales.Add(bone,bone.localScale);
                if(skin.rootBone!=null&&!scales.ContainsKey(skin.rootBone))scales.Add(skin.rootBone,skin.rootBone.localScale);
            }
        }
        public void RestoreScales()
        {
            foreach(var entry in scales)if(entry.Key!=null)entry.Key.localScale=entry.Value;
        }
        private void LateUpdate(){RestoreScales();}
    }
}

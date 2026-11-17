using UnityEngine;
namespace Warfront
{
    // Applied after Unity's Animation evaluation, without cancelling server actions.
    public sealed class HeroHitReaction : MonoBehaviour
    {
        public const float Duration=.32f;
        private float expires;
        private bool applied;
        private Transform torso,head,rightArm,leftArm,bow;
        private Vector3 basePosition;
        private Quaternion baseRotation,torsoRotation,headRotation,rightRotation,leftRotation;
        private void Awake()
        {
            torso=transform.Find("root/torso");head=transform.Find("root/torso/head");
            rightArm=transform.Find("root/torso/arm-right");leftArm=transform.Find("root/torso/arm-left");
        }
        public void PlayUntil(float until){expires=until;}
        private void LateUpdate(){Sample(Time.unscaledTime);}
        private void SyncBow()
        {
            if(bow==null)bow=transform.Find("Archer Bow");
            if(bow!=null&&leftArm!=null){var visual=bow.GetComponent<ArcheryBowVisual>();if(visual!=null){visual.Refresh();return;}bow.position=leftArm.TransformPoint(new Vector3(0,-.12f,.035f));bow.rotation=transform.rotation;}
        }
        public void RestorePose()
        {
            if(!applied)return;
            transform.localPosition=basePosition;transform.localRotation=baseRotation;
            if(torso!=null)torso.localRotation=torsoRotation;if(head!=null)head.localRotation=headRotation;
            if(rightArm!=null)rightArm.localRotation=rightRotation;if(leftArm!=null)leftArm.localRotation=leftRotation;
            applied=false;SyncBow();
        }
        public void Sample(float now)
        {
            RestorePose();if(now>=expires)return;
            if(torso==null)Awake();
            float age=Mathf.Max(0,Duration-(expires-now));
            float strength=Mathf.Clamp01(age/.045f)*Mathf.Pow(Mathf.Clamp01(1-age/Duration),1.2f);
            if(strength<=0)return;
            basePosition=transform.localPosition;baseRotation=transform.localRotation;
            if(torso!=null){torsoRotation=torso.localRotation;torso.localRotation=torsoRotation*Quaternion.Euler(-24*strength,0,9*strength);}
            if(head!=null){headRotation=head.localRotation;head.localRotation=headRotation*Quaternion.Euler(12*strength,0,-5*strength);}
            if(rightArm!=null){rightRotation=rightArm.localRotation;rightArm.localRotation=rightRotation*Quaternion.Euler(-5*strength,0,-8*strength);}
            if(leftArm!=null){leftRotation=leftArm.localRotation;leftArm.localRotation=leftRotation*Quaternion.Euler(-5*strength,0,8*strength);}
            transform.localRotation=baseRotation*Quaternion.Euler(-9*strength,0,6*strength);
            transform.localPosition=basePosition-(baseRotation*Vector3.forward)*(.10f*strength);
            applied=true;SyncBow();
        }
        public void Clear(){RestorePose();expires=0;}
        private void OnDisable(){Clear();}
    }
}

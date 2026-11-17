using System.Collections.Generic;
using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        // Only idle instances count toward the cap; active server events are never dropped.
        private const int CombatPoolCapacity=64;
        private Transform combatPoolRoot;
        private readonly Stack<GameObject> arrowPool=new Stack<GameObject>(CombatPoolCapacity);
        private readonly Stack<GameObject> blastEffectPool=new Stack<GameObject>(CombatPoolCapacity);
        private readonly Stack<GameObject> bombPool=new Stack<GameObject>(CombatPoolCapacity);
        private readonly Stack<GameObject> blastRingPool=new Stack<GameObject>(CombatPoolCapacity);
        private readonly HashSet<int> projectileIds=new HashSet<int>();
        private readonly List<int> expiredProjectileIds=new List<int>();
        private readonly HashSet<int> bombIds=new HashSet<int>();
        private readonly List<int> expiredBombIds=new List<int>();
        private Transform CombatPoolRoot()
        {
            if(combatPoolRoot==null){var root=new GameObject("Combat visual pool");root.transform.SetParent(transform,false);root.SetActive(false);combatPoolRoot=root.transform;}
            return combatPoolRoot;
        }
        private GameObject RentCombatVisual(Stack<GameObject> pool,GameObject prefab,string label)
        {
            GameObject item=null;
            while(pool.Count>0&&item==null)item=pool.Pop();
            if(item==null){item=Instantiate(prefab,CombatPoolRoot());SetLayer(item);}
            item.SetActive(false);item.name=label;item.transform.SetParent(field.transform,false);
            item.transform.localPosition=Vector3.zero;item.transform.localRotation=Quaternion.identity;item.transform.localScale=prefab.transform.localScale;
            item.SetActive(true);return item;
        }
        private LineRenderer RentBlastRing(string label,Color color)
        {
            GameObject item=null;
            while(blastRingPool.Count>0&&item==null)item=blastRingPool.Pop();
            var line=item==null?CombatLine(label,CombatPoolRoot(),49,color,.055f):item.GetComponent<LineRenderer>();
            item=line.gameObject;item.SetActive(false);item.name=label;item.transform.SetParent(field.transform,false);
            item.transform.localPosition=Vector3.zero;item.transform.localRotation=Quaternion.identity;item.transform.localScale=Vector3.one;
            line.enabled=false;line.useWorldSpace=false;line.positionCount=49;line.widthMultiplier=.055f;line.startColor=line.endColor=color;
            item.SetActive(true);return line;
        }
        private void ReturnCombatVisual(Stack<GameObject> pool,GameObject item)
        {
            if(item==null)return;
            item.SetActive(false);item.transform.SetParent(CombatPoolRoot(),false);
            if(pool.Count<CombatPoolCapacity)pool.Push(item);else RemoveOwned(item);
        }
        private void ReturnFieldCombatVisuals()
        {
            foreach(var item in flyingArrows.Values)ReturnCombatVisual(arrowPool,item);
            foreach(var item in squadBombs.Values)ReturnCombatVisual(bombPool,item);
            foreach(var item in squadBlastRings.Values)if(item!=null)ReturnCombatVisual(blastRingPool,item.gameObject);
            foreach(var item in squadBlastEffects.Values)ReturnCombatVisual(blastEffectPool,item);
            squadBlastEffects.Clear();squadBlastReplayStart.Clear();bombLaunchPoints.Clear();
            flyingArrows.Clear();arrowReplayStart.Clear();arrowVisualStarts.Clear();squadBombs.Clear();squadBlastRings.Clear();
            projectileIds.Clear();expiredProjectileIds.Clear();bombIds.Clear();expiredBombIds.Clear();
        }
    }
}

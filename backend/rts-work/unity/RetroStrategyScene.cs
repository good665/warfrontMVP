using System.Collections.Generic;
using UnityEngine;
namespace Warfront
{
    public sealed partial class RetroFantasyScene
    {
        private GameObject strategyRoot;
        private readonly Dictionary<string,GameObject> strategyNodes=new Dictionary<string,GameObject>();
        public void StrategyObjectives(SquadSnapshot snapshot)
        {
            if(field==null||snapshot?.strategy==null){if(strategyRoot!=null)strategyRoot.SetActive(false);return;}
            if(strategyRoot==null||strategyRoot.transform.parent!=field.transform)
            {
                if(strategyRoot!=null)Destroy(strategyRoot);
                strategyNodes.Clear();strategyRoot=new GameObject("RTS capture and construction");strategyRoot.transform.SetParent(field.transform,false);
            }
            strategyRoot.SetActive(true);var live=new HashSet<string>();var st=snapshot.strategy;
            if(st.points!=null)foreach(var p in st.points)
            {
                string key="capture:"+p.id;live.Add(key);
                if(!strategyNodes.TryGetValue(key,out var node))
                {
                    node=new GameObject(key);node.transform.SetParent(strategyRoot.transform,false);strategyNodes[key]=node;
                    Model("floor-detail",Vector3.zero,Vector3.zero,Vector3.one*3,node.transform);
                    Model("banner",Vector3.zero,Vector3.zero,Vector3.one*2,node.transform);SetLayer(node);
                }
                node.SetActive(true);node.transform.localPosition=WorldPoint(p.x,p.y);
                TintStrategy(node,p.owner==snapshot.team?new Color(.35f,.8f,1):p.owner<0?new Color(.8f,.78f,.6f):new Color(1,.35f,.25f));
            }
            if(st.buildings!=null)foreach(var b in st.buildings)
            {
                string key="structure:"+b.id;live.Add(key);
                if(!strategyNodes.TryGetValue(key,out var node))
                {
                    node=new GameObject(key);node.transform.SetParent(strategyRoot.transform,false);strategyNodes[key]=node;
                    if(b.kind=="tower")Model("column",Vector3.zero,Vector3.zero,new Vector3(2,3,2),node.transform);
                    else if(b.kind=="outpost"){Model("banner",Vector3.zero,Vector3.zero,Vector3.one*2,node.transform);Model("barrel",Vector3.right,Vector3.zero,Vector3.one,node.transform);}
                    else {Model("gate",Vector3.zero,Vector3.zero,Vector3.one*1.5f,node.transform);Model(b.kind=="academy"?"chest":"barrel",Vector3.right,Vector3.zero,Vector3.one,node.transform);}
                    SetLayer(node);
                }
                node.SetActive(b.hp>0);node.transform.localPosition=WorldPoint(b.x,b.y);node.transform.localScale=new Vector3(1,b.remaining>0?.45f:1,1);
                TintStrategy(node,b.team==snapshot.team?new Color(.55f,.8f,1):new Color(1,.4f,.3f));
            }
            foreach(var entry in strategyNodes)if(!live.Contains(entry.Key))entry.Value.SetActive(false);
        }
        private void TintStrategy(GameObject node,Color tint)
        {
            var block=new MaterialPropertyBlock();block.SetColor("_BaseColor",tint);
            foreach(var renderer in node.GetComponentsInChildren<Renderer>())renderer.SetPropertyBlock(block);
        }
    }
}

using System;
using System.Reflection;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public static class StrategyChecks
    {
        const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
        static void Set(object o,string n,object v)=>o.GetType().GetField(n,Flags).SetValue(o,v);
        static object Get(object o,string n)=>o.GetType().GetField(n,Flags).GetValue(o);
        static object Call(object o,string n,params object[] args)=>o.GetType().GetMethod(n,Flags).Invoke(o,args);
        static void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        [MenuItem("Warfront/Squad/Check RTS Strategy")]
        public static void Run()
        {
            var input=new SquadInput{sequence=19,economy="train_scout",squad_id="squad-2",formation="spread",command="attack_move",order_x=1800,order_y=1500};
            var round=JsonUtility.FromJson<SquadInput>(JsonUtility.ToJson(input));
            Check(round.sequence==19&&round.economy=="train_scout"&&round.squad_id=="squad-2"&&round.formation=="spread"&&round.command=="attack_move"&&round.order_x==1800,"Strategy intent JSON lost data");
            var state=JsonUtility.FromJson<SquadSnapshot>("{\"strategy\":{\"supplies\":120,\"income\":2,\"population_cap\":9,\"points\":[{\"id\":\"p1\",\"progress\":0.5,\"owner\":-1}],\"squads\":[{\"id\":\"s2\",\"members\":3,\"alive\":2}],\"explored\":[0,31,599],\"vision\":[{\"x\":60,\"y\":60,\"radius\":520}]}}");
            Check(state.strategy.supplies==120&&state.strategy.points[0].owner==-1&&state.strategy.squads[0].alive==2&&state.strategy.explored[2]==599,"Strategy snapshot DTO mismatch");
            var go=new GameObject("RTS client intent checks");go.SetActive(false);
            try
            {
                var game=go.AddComponent<GameBootstrap>();Set(game,"strategySquad","s2");Set(game,"strategyEconomy","train_guard");Set(game,"strategyFormation","wedge");
                var first=new SquadInput{sequence=20};Call(game,"ConsumeStrategyIntent",first,true);
                var second=new SquadInput{sequence=21};Call(game,"ConsumeStrategyIntent",second,true);
                Check(first.economy=="train_guard"&&first.formation=="wedge"&&first.squad_id=="s2"&&second.economy=="none"&&second.formation=="none","Economy and formation must be consumed once");
                Check(first.economy=="train_guard"&&first.sequence==20,"Consuming later input mutated retry payload");
                var failed=new SquadInput{sequence=77,economy="build_tower",formation="spread",command="attack_move",squad_id="s2",order_x=1400,order_y=900,target_id="enemy",aim_x=1500,aim_y=950,attack=true,charge_held=true,charge_release=true,dodge=true,skill1=true,skill2=true,move_x=1,move_y=-1};
                Check(ReferenceEquals(Call(game,"PrepareSquadRetry",failed,true),failed),"Connected retry must keep its exact payload");
                var safe=(SquadInput)Call(game,"PrepareSquadRetry",failed,false);var safeAgain=(SquadInput)Call(game,"PrepareSquadRetry",safe,false);
                Check(safe.sequence==77&&safe.economy=="build_tower"&&safe.formation=="spread"&&safe.command=="attack_move"&&safe.squad_id=="s2"&&safe.order_x==1400&&safe.order_y==900&&safe.target_id=="enemy"&&safe.aim_x==1500&&safe.aim_y==950,"Disconnected retry lost authoritative strategy intent or sequence");
                Check(!safe.attack&&!safe.charge_held&&!safe.charge_release&&!safe.dodge&&!safe.skill1&&!safe.skill2&&safe.move_x==0&&safe.move_y==0,"Disconnected strategy retry retained combat input");
                Check(JsonUtility.ToJson(safeAgain)==JsonUtility.ToJson(safe),"Repeated disconnected strategy retry changed its sequence or intent");
                Set(game,"squadSequence",80);var combatRetry=(SquadInput)Call(game,"PrepareSquadRetry",new SquadInput{sequence=79,attack=true},false);Check(combatRetry.sequence==81&&!combatRetry.attack&&combatRetry.economy=="none","Legacy combat retry must send a fresh neutral sequence");
                Set(game,"squadOrder","hold");Call(game,"SelectStrategySquad","all");Check((string)Get(game,"strategySquad")=="s2","Pending order changed selected squad before capture");Set(game,"squadOrder","none");
                Set(game,"strategyEconomy","build_tower");Set(game,"strategyBuildPoint",new Vector2(700,900));var build=new SquadInput{order_x=5,order_y=6,command="move"};Call(game,"ConsumeStrategyIntent",build,true);Check(build.order_x==700&&build.order_y==900&&build.command=="none","Pending building lost its captured placement");
                Set(game,"squadSnapshot",state);Call(game,"ValidateStrategySelection");Check((string)Get(game,"strategySquad")=="s2","Valid selected squad was lost");
                Set(game,"strategySquad","dead-squad");Call(game,"ValidateStrategySelection");Check((string)Get(game,"strategySquad")=="","Removed selected squad was not reset");
                Set(game,"strategyPlacement","build_tower");Set(game,"strategyEconomy","research_attack");Call(game,"ResetStrategy");Check((string)Get(game,"strategyPlacement")==""&&(string)Get(game,"strategyEconomy")=="none"&&(string)Get(game,"strategySquad")=="","Exit/rematch reset retained strategy action");
                Check(!(bool)Call(game,"StrategyPointer",new Vector2(300,100))&&(bool)Call(game,"StrategyPointer",new Vector2(300,25)),"Collapsed strategy HUD must leave the central battlefield interactive");
                Call(game,"ToggleStrategyPanel");Check((bool)Call(game,"StrategyPointer",new Vector2(300,100)),"Expanded strategy HUD must consume look/attack pointer");
                Call(game,"ResetStrategy");Check(!(bool)Get(game,"strategyExpanded"),"Rematch must collapse strategy HUD");
            }
            finally{UnityEngine.Object.DestroyImmediate(go);}
            var visual=new GameObject("RTS scene checks");
            try
            {
                var scene=visual.AddComponent<RetroFantasyScene>();scene.Initialize();
                var world=new MmoSnapshot{zone="squad",instance_id="strategy-check",world_width=3600,world_height=2400,obstacles=new MmoObstacle[0]};scene.BeginField(world,Vector2.zero);
                state.world=world;state.strategy.points[0].x=1000;state.strategy.points[0].y=800;
                state.strategy.buildings=new[]{new StrategyBuilding{id="tower-1",kind="tower",x=600,y=700,hp=400,max_hp=400,remaining=5}};
                scene.StrategyObjectives(state);
                var root=visual.transform.Find("Encounter squad/RTS capture and construction");Check(root!=null&&root.childCount==2,"Native capture/building models missing");
                var tower=root.Find("structure:tower-1");Check(Vector3.Distance(tower.localPosition,RetroFantasyScene.WorldPoint(600,700))<.001f&&tower.localScale.y<1,"Construction model position/state mismatch");
                state.strategy.buildings=new StrategyBuilding[0];scene.StrategyObjectives(state);Check(!tower.gameObject.activeSelf,"Hidden/destroyed building remains visible");
                state.strategy=null;scene.StrategyObjectives(state);Check(!root.gameObject.activeSelf,"Strategy scene visuals persist outside strategy state");
            }
            finally{UnityEngine.Object.DestroyImmediate(visual);}
            Debug.Log("RTS_STRATEGY_CHECKS_OK: JSON, one-shot economy/formation, retry immutability, selection/lifecycle, input gating, native capture/building visibility");
        }
    }
}

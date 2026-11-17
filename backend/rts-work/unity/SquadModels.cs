using System;
namespace Warfront
{
    [Serializable] public sealed class SquadBase { public string id; public int team; public float x,y,hp,max_hp; }
    [Serializable] public sealed class SquadCamp { public int team; public float x,y,radius; }
    [Serializable] public sealed class SquadRoster { public string id,kind; public float hp,max_hp,respawn_left; }
    [Serializable] public sealed class SquadSnapshot { public string code,status,you_id,reason,command,mode,opponent_name; public int team,winner=-1; public float elapsed,respawn_left; public bool recruited; public SquadBase[] bases; public SquadCamp[] camps; public SquadRoster[] roster; public MmoSnapshot world; public SquadStrategy strategy; }
    [Serializable] public sealed class SquadJoinRequest { public string code; }
    [Serializable] public sealed class SquadInput { public int sequence; public float move_x,move_y,aim_x,aim_y,order_x,order_y; public bool attack,dodge,skill1,skill2,charge_held,charge_release; public string command="none",target_id="",economy="none",squad_id="",formation="none"; }
    [Serializable] public sealed class SquadStrategy { public float supplies,income; public int population,population_cap,squad_cap,tech_attack,tech_armor,tech_recon; public string action_error; public StrategyPoint[] points; public StrategySquad[] squads; public StrategyQueue[] queue; public StrategyBuilding[] buildings; public StrategyResearch[] research; public StrategyVision[] vision; public int[] explored; }
    [Serializable] public sealed class StrategyPoint { public string id,name; public float x,y,radius,progress; public int owner=-1,capturing=-1; public bool contested; }
    [Serializable] public sealed class StrategySquad { public string id,kind,command,formation,target_id; public float x,y,hp,max_hp; public int members,alive; }
    [Serializable] public sealed class StrategyQueue { public string id,kind; public float remaining,duration; }
    [Serializable] public sealed class StrategyBuilding { public string id,kind; public int team; public float x,y,hp,max_hp,remaining; }
    [Serializable] public sealed class StrategyResearch { public string id; public float remaining,duration; }
    [Serializable] public sealed class StrategyVision { public float x,y,radius; }
}


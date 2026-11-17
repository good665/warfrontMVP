using System;
namespace Warfront
{
    [Serializable] public sealed class SquadBase { public string id; public int team; public float x,y,hp,max_hp; }
    [Serializable] public sealed class SquadCamp { public int team; public float x,y,radius; }
    [Serializable] public sealed class SquadRoster { public string id,kind; public float hp,max_hp,respawn_left; }
    [Serializable] public sealed class SquadSnapshot { public string code,status,you_id,reason,command,mode,opponent_name; public int team,winner=-1; public float elapsed,respawn_left; public bool recruited; public SquadBase[] bases; public SquadCamp[] camps; public SquadRoster[] roster; public MmoSnapshot world; }
    [Serializable] public sealed class SquadJoinRequest { public string code; }
    [Serializable] public sealed class SquadInput { public int sequence; public float move_x,move_y,aim_x,aim_y,order_x,order_y; public bool attack,dodge,skill1,skill2,charge_held,charge_release; public string command="none",target_id=""; }
}


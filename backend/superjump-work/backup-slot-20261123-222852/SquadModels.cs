using System;
namespace Warfront
{
    [Serializable] public sealed class SquadBase { public string id; public int team; public int floor; public float x,y,hp,max_hp; }
    [Serializable] public sealed class SquadCamp { public int team,floor; public float x,y,radius; }
    [Serializable] public sealed class SquadSnapshot { public int team_size,capacity; public RtsMember[] members; public string code,status,you_id,reason,command,mode,opponent_name; public RtsBattleState battle; public int team,winner=-1; public float elapsed,respawn_left; public bool recruited,paused; public string paused_by; public int pause_remaining; public SquadBase[] bases; public SquadCamp[] camps; public MmoSnapshot world; }
    [Serializable] public sealed class SquadMapRect { public string kind; public float x,y,width,height; }
    [Serializable] public sealed class SquadMapInterior { public int floor; public float x,y; public string[] rows; public string kind; }
    [Serializable] public sealed class SquadMapDoor { public int floor,cx,cy,to_floor; public float to_x,to_y; }
    [Serializable] public sealed class SquadChest { public string id; public int floor; public float x,y; public bool ready; }
    [Serializable] public sealed class SquadMapProp { public string id,kind; public int floor,cx,cy; public float x,y; }
    [Serializable] public sealed class SquadMap { public string version; public float cell; public SquadMapRect[] outdoor; public SquadMapInterior[] interiors; public SquadMapDoor[] doors; public SquadChest[] chests; public SquadMapProp[] props; }
    [Serializable] public sealed class SquadPauseRequest { public bool paused; }
    [Serializable] public sealed class SquadJoinRequest { public string code; }
    [Serializable] public sealed class SquadInput { public string[] unit_ids=new string[0]; public string character=""; public bool jump; public int sequence; public float move_x,move_y,aim_x,aim_y,order_x,order_y; public bool attack,dodge,skill1,skill2; public int item=-1,drop=-1; public string command="none",target_id=""; }
}


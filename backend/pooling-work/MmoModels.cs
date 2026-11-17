using System;
namespace Warfront
{
    [Serializable] public sealed class MmoQuest { public string id,title,kind,zone,description; public float x,y; public int progress,target,reward_xp,reward_gold; public bool ready; }
    [Serializable] public sealed class MmoItem { public string id,name,slot; public int power,rarity; public bool equipped; }
    [Serializable] public sealed class MmoProfile { public int level,xp,xp_next,gold,role,weapon_rank,armor_rank; public float attack,max_hp; public string equipped_weapon,equipped_armor; public MmoQuest quest; public MmoItem[] inventory; }
    [Serializable] public sealed class MmoPartyMember { public string id,name,zone; public int level; }
    [Serializable] public sealed class MmoParty { public string code,leader_id; public MmoPartyMember[] members; }
    [Serializable] public sealed class MmoActor { public string id,name,party_code,kind,action_kind,attack_phase; public int action_id; public float action_left,action_duration,action_fx,action_fy,body_radius; public int role,level; public float x,y,fx,fy,hp,max_hp,attack_cooldown,dodge_cooldown,skill1_cooldown,skill2_cooldown,dodge_left,hit_flash; }
    [Serializable] public sealed class MmoEnemy { public string id,kind,name,action_kind,attack_phase; public int action_id; public float fx,fy,dodge_left,action_left,action_duration,action_fx,action_fy,body_radius; public float x,y,hp,max_hp,hit_flash,respawn_left,windup_left,windup_duration,attack_radius,attack_x,attack_y,stagger_left; }
    [Serializable] public sealed class MmoCombatRules { public float attack_reach=145,heavy_reach=210,attack_dot=.35f,bomb_range=600,bomb_radius=150,attack_windup=.16f,heavy_windup=.20f,melee_active_end=.43f; }
    [Serializable] public sealed class MmoProjectile { public int id,team; public string owner_id,target_id; public float start_x,start_y,end_x,end_y,x,y,age,flight; public bool resolved; }
    [Serializable] public sealed class MmoBomb { public int id,team; public string owner_id; public float start_x,start_y,x,y,target_x,target_y,age,flight,radius; public bool exploded; }
    [Serializable] public sealed class MmoHazard { public float x,y,radius,age; }
    [Serializable] public sealed class MmoEffect { public string id,text,kind; public float x,y; }
    [Serializable] public sealed class MmoObstacle { public float x,y,width,height; }
    [Serializable] public sealed class MmoSnapshot { public string zone,instance_id,you_id; public int last_sequence; public float world_width,world_height,server_time; public MmoProjectile[] projectiles; public MmoBomb[] bombs; public MmoCombatRules combat_rules; public MmoProfile profile; public MmoActor[] players; public MmoEnemy[] enemies; public MmoHazard[] hazards; public MmoEffect[] effects; public MmoObstacle[] obstacles; public MmoParty party; }
    [Serializable] public sealed class MmoEnterRequest { public string zone; public int role; }
    [Serializable] public sealed class MmoInputRequest { public int sequence; public float move_x,move_y,aim_x,aim_y; public bool attack,dodge,skill1,skill2; }
    [Serializable] public sealed class MmoEquipRequest { public string item_id; }
    [Serializable] public sealed class MmoUpgradeRequest { public string slot; }
    [Serializable] public sealed class MmoPartyRequest { public string action,code; }
}

using System;
using System.Reflection;
using System.IO;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification {
public static class SquadCursorChecks {
 const BindingFlags F=BindingFlags.NonPublic|BindingFlags.Instance;
 static object Call(object o,string n,params object[] a)=>o.GetType().GetMethod(n,F).Invoke(o,a);
 static object Get(object o,string n)=>o.GetType().GetField(n,F).GetValue(o);
 static void Set(object o,string n,object v)=>o.GetType().GetField(n,F).SetValue(o,v);
 static void Check(bool ok,string m){if(!ok)throw new Exception(m);}
 static SquadSnapshot State(float hp,string code="cursor")=>new SquadSnapshot{code=code,status="active",team=0,world=new MmoSnapshot{zone="squad",instance_id=code,you_id="self",profile=new MmoProfile{max_hp=160,inventory=new MmoItem[0]},players=new[]{new MmoActor{id="self",kind="hero",hp=hp,max_hp=160}},enemies=new MmoEnemy[0]}};
 [InitializeOnLoadMethod] static void Auto(){EditorApplication.delayCall+=()=>{var p=Path.Combine(Path.GetTempPath(),"warfront-cursor.request");if(!File.Exists(p))return;if(EditorApplication.isPlayingOrWillChangePlaymode){Auto();return;}File.Delete(p);try{Run();File.WriteAllText(p+".result","PASS");}catch(Exception e){Debug.LogException(e);File.WriteAllText(p+".result",e.ToString());}};}
 [MenuItem("Warfront/Squad/Check Entry Respawn Cursor")]
 public static void Run(){var root=new GameObject("Squad cursor checks");root.SetActive(false);try{var game=root.AddComponent<GameBootstrap>();Set(game,"squadMode",true);Call(game,"SquadApply",State(160));Check((bool)Get(game,"squadAutoLookPending"),"Entry did not request automatic mouse capture");Check(!(bool)Call(game,"ConsumeSquadAutoLook",false,true),"Touch-only input captured mouse");Check(!(bool)Call(game,"ConsumeSquadAutoLook",true,false),"Unfocused app captured mouse");Check((bool)Call(game,"ConsumeSquadAutoLook",true,true),"Focused entry did not capture mouse");Call(game,"SquadApply",State(150));Check(!(bool)Get(game,"squadAutoLookPending"),"Ordinary snapshot stole deliberately released cursor");Call(game,"SquadApply",State(0));Call(game,"SquadApply",State(160));Check((bool)Get(game,"squadAutoLookPending"),"Respawn did not request mouse capture");Set(game,"strategyExpanded",true);Check(!(bool)Call(game,"ConsumeSquadAutoLook",true,true),"Strategy panel lost its mouse");Set(game,"strategyExpanded",false);Check((bool)Call(game,"ConsumeSquadAutoLook",true,true),"Respawn capture did not resume after UI gate");Call(game,"SquadApply",State(160,"next"));Check((bool)Get(game,"squadAutoLookPending"),"Rematch did not capture mouse");Call(game,"ReleaseDungeonCursor",false);Check(!(bool)Get(game,"squadAutoLookPending"),"Explicit cursor release retained capture request");Call(game,"SquadApply",State(155,"next"));Check(!(bool)Get(game,"squadAutoLookPending"),"Esc release was overridden by a later snapshot");Call(game,"SquadApply",new SquadSnapshot{status="none"});Check(!(bool)Get(game,"squadAutoLookPending"),"Lobby retained auto-capture");Debug.Log("SQUAD_CURSOR_CHECKS PASS: entry/respawn/rematch, no repeated capture, focus/mouse/UI gates, explicit release and lobby cleanup");}finally{UnityEngine.Object.DestroyImmediate(root);}}
}}

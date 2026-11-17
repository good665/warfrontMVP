using System;
using System.IO;
using System.Threading.Tasks;
using UnityEditor;
using UnityEngine;
namespace Warfront.Verification
{
    public static class NovemberNetworkChecks
    {
        [InitializeOnLoadMethod] static void AutoRun(){EditorApplication.delayCall+=()=>{
            string request=Path.Combine(Path.GetTempPath(),"warfront-november-network.request");if(!File.Exists(request))return;
            File.Delete(request);Run();
        };}
        static void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        [MenuItem("Warfront/November/Check Local Equipment API")]
        public static async void Run()
        {
            try{await Scenario();File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-november-network.result"),"PASS: Unity ApiClient + JsonUtility / login / 3 loadouts / helmet equip / upgrade / live stats / persisted profile");}
            catch(Exception e){Debug.LogException(e);File.WriteAllText(Path.Combine(Path.GetTempPath(),"warfront-november-network.result"),e.ToString());}
        }
        private static async Task Scenario()
        {
            var client=new ApiClient("http://127.0.0.1:58741");
            await client.GuestLoginAsync("november-unity-e2e","NovemberCheck");
            var profile=await client.MmoProfileAsync();Check(profile.loadouts?.Length==3,"JsonUtility failed to read three loadouts");
            profile=await client.MmoLoadoutAsync(0);var state=await client.MmoEnterAsync("frontier",0);
            float hp=state.players[0].hp;
            profile=await client.MmoLoadoutAsync(1);profile=await client.MmoEquipAsync("e2e-helm");
            Check(profile.equipped_helmet=="e2e-helm"&&profile.loadouts[1].helmet=="e2e-helm","Helmet equip was not saved to set 2");
            state=await client.MmoStateAsync();Check(state.players[0].max_hp==profile.max_hp&&state.players[0].hp<=hp,"Gear change did not synchronize live stats or healed");
            int rank=profile.helmet_rank;profile=await client.MmoUpgradeAsync("helmet");Check(profile.helmet_rank==rank+1,"Helmet upgrade failed");
            profile=await client.MmoLoadoutAsync(2);profile=await client.MmoEquipAsync("e2e-sword");
            Check(profile.active_loadout==2&&profile.loadouts[2].weapon=="e2e-sword","Set 3 equip failed");
            profile=await client.MmoLoadoutAsync(0);Check(profile.equipped_helmet!= "e2e-helm"&&profile.equipped_weapon!="e2e-sword","Sets leaked into each other");
            profile=await client.MmoLoadoutAsync(1);Check(profile.equipped_helmet=="e2e-helm","Set 2 was not restored");
            await client.MmoLeaveAsync();
            var restored=new ApiClient("http://127.0.0.1:58741");await restored.GuestLoginAsync("november-unity-e2e","NovemberCheck");profile=await restored.MmoProfileAsync();
            Check(profile.active_loadout==1&&profile.loadouts[2].weapon=="e2e-sword","Reconnect lost loadouts");
            Debug.Log("NOVEMBER_NETWORK_CHECKS PASS");
        }
    }
}

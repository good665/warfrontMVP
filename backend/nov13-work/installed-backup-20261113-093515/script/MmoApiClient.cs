using System.Threading.Tasks;
using UnityEngine;
namespace Warfront
{
    public sealed partial class ApiClient
    {
        public Task<MmoProfile> MmoProfileAsync() => SendAsync<MmoProfile>("GET", "/v1/mmo/profile");
        public Task<MmoSnapshot> MmoEnterAsync(string zone, int role) => SendAsync<MmoSnapshot>("POST", "/v1/mmo/enter", JsonUtility.ToJson(new MmoEnterRequest {zone=zone,role=role}));
        public Task<MmoSnapshot> MmoStateAsync() => SendAsync<MmoSnapshot>("GET", "/v1/mmo/state");
        public Task<MmoSnapshot> MmoInputAsync(MmoInputRequest input) => SendAsync<MmoSnapshot>("POST", "/v1/mmo/input", JsonUtility.ToJson(input));
        public Task<MmoProfile> MmoLeaveAsync() => SendAsync<MmoProfile>("POST", "/v1/mmo/leave", "{}");
        public Task<MmoProfile> MmoEquipAsync(string id) => SendAsync<MmoProfile>("POST", "/v1/mmo/equip", JsonUtility.ToJson(new MmoEquipRequest {item_id=id}));
        public Task<MmoProfile> MmoUpgradeAsync(string slot) => SendAsync<MmoProfile>("POST", "/v1/mmo/upgrade", JsonUtility.ToJson(new MmoUpgradeRequest {slot=slot}));
        public Task<MmoProfile> MmoClaimAsync() => SendAsync<MmoProfile>("POST", "/v1/mmo/quest/claim", "{}");
        public Task<MmoParty> MmoPartyAsync(string action, string code="") => SendAsync<MmoParty>("POST", "/v1/mmo/party", JsonUtility.ToJson(new MmoPartyRequest {action=action,code=code}));
    }
}

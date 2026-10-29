using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace Warfront
{
    [Serializable]
    public sealed class ServerPlayer
    {
        public string id;
        public string display_name;
        public int diamonds;
        public int stamina;
        public int rating;
        public int wins;
        public int losses;
        public int power;
        public int pve_best_stage;
        public int next_stamina_in_seconds;
        public int daily_ad_views;
        public bool daily_reward_claimed;
    }

    public sealed class GameApiClient
    {
        [Serializable]
        private sealed class GuestRequest { public string device_id; public string display_name; }
        [Serializable]
        private sealed class AuthResponse { public string access_token; public ServerPlayer player; }

        private readonly string baseUrl;
        private string accessToken;
        public bool IsAuthenticated => !string.IsNullOrEmpty(accessToken);

        public GameApiClient(string url)
        {
            baseUrl = (url ?? string.Empty).Trim().TrimEnd('/');
        }

        public IEnumerator Login(string deviceId, string displayName, Action<ServerPlayer> success, Action<long, string> failure)
        {
            accessToken = null;
            var payload = new GuestRequest { device_id = deviceId, display_name = displayName };
            yield return Send<AuthResponse>("POST", "/v1/auth/guest", JsonUtility.ToJson(payload), response =>
            {
                if (string.IsNullOrEmpty(response.access_token) || !ValidPlayer(response.player))
                {
                    failure(0, "서버의 로그인 응답을 확인할 수 없습니다.");
                    return;
                }
                accessToken = response.access_token;
                success(response.player);
            }, failure);
        }

        public IEnumerator GetPlayer(Action<ServerPlayer> success, Action<long, string> failure)
        {
            if (!IsAuthenticated)
            {
                failure(401, "로그인이 필요합니다.");
                yield break;
            }
            yield return Send<ServerPlayer>("GET", "/v1/me", null, player =>
            {
                if (ValidPlayer(player)) success(player);
                else failure(0, "서버의 플레이어 응답을 확인할 수 없습니다.");
            }, failure);
        }

        private static bool ValidPlayer(ServerPlayer player)
        {
            return player != null && !string.IsNullOrEmpty(player.id) && !string.IsNullOrEmpty(player.display_name);
        }

        private IEnumerator Send<T>(string method, string path, string json, Action<T> success, Action<long, string> failure) where T : class
        {
            if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out Uri uri) ||
                (uri.Scheme != "http" && uri.Scheme != "https") ||
                !string.IsNullOrEmpty(uri.Query) || !string.IsNullOrEmpty(uri.Fragment) || !string.IsNullOrEmpty(uri.UserInfo))
            {
                failure(0, "서버 주소를 확인해 주세요.");
                yield break;
            }

            using (var request = new UnityWebRequest(baseUrl + path, method))
            {
                request.downloadHandler = new DownloadHandlerBuffer();
                request.timeout = 10;
                request.SetRequestHeader("Accept", "application/json");
                if (json != null)
                {
                    request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
                    request.SetRequestHeader("Content-Type", "application/json");
                }
                if (IsAuthenticated) request.SetRequestHeader("Authorization", "Bearer " + accessToken);
                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success)
                {
                    long code = request.responseCode;
                    if (code == 401) accessToken = null;
                    string message = code == 409 ? "이미 사용 중인 이름입니다. 다른 이름을 입력해 주세요."
                        : code == 422 ? "이름은 한글·영문·숫자·공백·_·-로 2~24자 입력해 주세요."
                        : code == 401 ? "세션이 만료되었습니다. 다시 로그인해 주세요."
                        : code >= 500 ? "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
                        : "서버에 연결하지 못했습니다. 주소와 서버 실행 상태를 확인해 주세요.";
                    failure(code, message);
                    yield break;
                }

                T response = null;
                try { response = JsonUtility.FromJson<T>(request.downloadHandler.text); }
                catch (ArgumentException) { }
                if (response == null) failure(0, "서버 응답을 읽을 수 없습니다.");
                else success(response);
            }
        }
    }
}

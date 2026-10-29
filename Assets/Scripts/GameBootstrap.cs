using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;
using Random = UnityEngine.Random;

namespace Warfront
{
    public sealed class GameBootstrap : MonoBehaviour
    {
        private const float DesignWidth = 1280f;
        private const float DesignHeight = 720f;
        private enum Screen { Lobby, Matchmaking, Duel, Pve, Rush, Bomb, Result, Ranking, Workshop, Account }
        private sealed class Hazard { public Vector2 position; public float size; public float speed; }

        private GameData data;
        [SerializeField] private string apiBaseUrl = "http://localhost:8000";
        private GameApiClient api;
        private ServerPlayer serverPlayer;
        private string guestDeviceId;
        private string guestDisplayName;
        private string accountMessage = "게스트 로그인으로 서버 계정을 확인하세요.";
        private string accountUpdatedAt;
        private bool accountBusy;
        private Screen screen = Screen.Lobby;
        private readonly List<Hazard> hazards = new List<Hazard>();
        private float playerX;
        private float elapsed;
        private float spawnTimer;
        private float matchTimer;
        private int playerHp;
        private int enemyHp;
        private float playerAttackCooldown;
        private float enemyAttackTimer;
        private string duelLog;
        private int pveStage;
        private string resultTitle;
        private string resultDetail;
        private bool isBombMode;

        private readonly Color ink = new Color(0.05f, 0.06f, 0.1f);
        private readonly Color acid = new Color(0.85f, 1f, 0.26f);

        private float UiScale => Mathf.Min(UnityEngine.Screen.width / DesignWidth, UnityEngine.Screen.height / DesignHeight);
        private float UiWidth => DesignWidth;
        private float UiHeight => DesignHeight;
        private Vector2 UiOrigin => new Vector2(
            (UnityEngine.Screen.width - DesignWidth * UiScale) * .5f,
            (UnityEngine.Screen.height - DesignHeight * UiScale) * .5f
        );

        private void Awake()
        {
            Application.targetFrameRate = 60;
            data = new GameData();
            api = new GameApiClient(apiBaseUrl);
            guestDeviceId = PlayerPrefs.GetString("serverGuestDeviceId", string.Empty);
            if (string.IsNullOrEmpty(guestDeviceId))
            {
                guestDeviceId = Guid.NewGuid().ToString("N");
                PlayerPrefs.SetString("serverGuestDeviceId", guestDeviceId);
                PlayerPrefs.Save();
            }
            guestDisplayName = PlayerPrefs.GetString("serverGuestDisplayName", "지휘관_" + guestDeviceId.Substring(0, 12));
            playerX = UiWidth * 0.5f;
        }

        private void Update()
        {
            data.RecoverStamina();
            if (screen == Screen.Matchmaking) UpdateMatchmaking();
            if (screen == Screen.Duel) UpdateDuel();
            if (screen == Screen.Pve) UpdatePve();
            if (screen == Screen.Rush || screen == Screen.Bomb) UpdateSurvival();
        }

        private void UpdateMatchmaking()
        {
            matchTimer += Time.deltaTime;
            if (matchTimer < 2f) return;
            playerHp = 100;
            enemyHp = 100;
            playerAttackCooldown = 0f;
            enemyAttackTimer = 1.1f;
            duelLog = "적 지휘관과 조우했습니다. ATTACK을 누르세요.";
            screen = Screen.Duel;
        }

        private void UpdateDuel()
        {
            playerAttackCooldown = Mathf.Max(0f, playerAttackCooldown - Time.deltaTime);
            enemyAttackTimer -= Time.deltaTime;
            if (Keyboard.current != null && Keyboard.current.spaceKey.wasPressedThisFrame) TryPlayerAttack();
            if (screen != Screen.Duel) return;
            if (enemyAttackTimer > 0f) return;
            enemyAttackTimer = Random.Range(.85f, 1.45f);
            int damage = Random.Range(8, 17);
            playerHp = Mathf.Max(0, playerHp - damage);
            duelLog = $"적의 포격! 내 병력이 {damage} 피해를 받았습니다.";
            if (playerHp <= 0) EndDuel(false);
        }

        private void TryPlayerAttack()
        {
            if (screen != Screen.Duel || playerAttackCooldown > 0f) return;
            playerAttackCooldown = .45f;
            int damage = Random.Range(12, 23) + data.Power * 2;
            enemyHp = Mathf.Max(0, enemyHp - damage);
            duelLog = $"돌격 성공! 적 군단에 {damage} 피해를 입혔습니다.";
            if (enemyHp <= 0) EndDuel(true);
        }

        private void EndDuel(bool won)
        {
            data.RecordPvpResult(won);
            resultTitle = won ? "VICTORY" : "DEFEAT";
            resultDetail = won ? "1:1 전투 승리  ·  점수 +100  ·  다이아 +3" : "1:1 전투 패배  ·  점수 -100";
            screen = Screen.Result;
        }

        private void StartPve()
        {
            if (!data.TrySpendGameStamina()) { ShowNoStamina(); return; }
            pveStage = data.PveBestStage + 1;
            playerHp = 100 + data.Power * 5;
            enemyHp = 70 + pveStage * 35;
            playerAttackCooldown = 0f;
            enemyAttackTimer = 1.25f;
            duelLog = $"작전 {pveStage} 시작. 적 전선을 돌파하세요.";
            screen = Screen.Pve;
        }

        private void UpdatePve()
        {
            playerAttackCooldown = Mathf.Max(0f, playerAttackCooldown - Time.deltaTime);
            enemyAttackTimer -= Time.deltaTime;
            if (Keyboard.current != null && Keyboard.current.spaceKey.wasPressedThisFrame) TryPveAttack();
            if (screen != Screen.Pve) return;
            if (enemyAttackTimer > 0f) return;
            enemyAttackTimer = Mathf.Max(.65f, 1.35f - pveStage * .04f);
            int damage = Random.Range(6, 12) + pveStage * 2;
            playerHp = Mathf.Max(0, playerHp - damage);
            duelLog = $"적 방어선의 반격! {damage} 피해를 받았습니다.";
            if (playerHp <= 0) EndPve(false);
        }

        private void TryPveAttack()
        {
            if (screen != Screen.Pve || playerAttackCooldown > 0f) return;
            playerAttackCooldown = .40f;
            int damage = Random.Range(14, 25) + data.Power * 3;
            enemyHp = Mathf.Max(0, enemyHp - damage);
            duelLog = $"전선 돌파! 적에게 {damage} 피해를 입혔습니다.";
            if (enemyHp <= 0) EndPve(true);
        }

        private void EndPve(bool cleared)
        {
            if (cleared)
            {
                int reward = 2 + pveStage;
                data.RecordPveClear(pveStage);
                data.RewardDiamonds(reward);
                resultTitle = "OPERATION CLEAR";
                resultDetail = $"작전 {pveStage} 클리어  ·  다이아 +{reward}";
            }
            else
            {
                resultTitle = "OPERATION FAILED";
                resultDetail = $"작전 {pveStage}에서 후퇴했습니다. 정비소에서 전투력을 강화하세요.";
            }
            screen = Screen.Result;
        }

        private void UpdateSurvival()
        {
            elapsed += Time.deltaTime;
            float width = UiWidth;
            float playerWidth = 46f;
            float axis = GetMoveAxis();
            if (Pointer.current != null && Pointer.current.press.isPressed)
                playerX = (Pointer.current.position.ReadValue().x - UiOrigin.x) / UiScale;
            else
                playerX += axis * 490f * Time.deltaTime;
            playerX = Mathf.Clamp(playerX, playerWidth, width - playerWidth);

            spawnTimer -= Time.deltaTime;
            if (spawnTimer <= 0f)
            {
                float size = isBombMode ? Mathf.Lerp(32f, 108f, Mathf.Clamp01(elapsed / 75f)) : Random.Range(20f, 42f);
                hazards.Add(new Hazard { position = new Vector2(Random.Range(size, width - size), -size), size = size, speed = (isBombMode ? 95f : 180f) + elapsed * 4.2f });
                spawnTimer = Mathf.Max(.18f, (isBombMode ? .78f : .46f) - elapsed * .004f);
            }

            Rect player = new Rect(playerX - playerWidth / 2, UiHeight - 132f, playerWidth, 44f);
            for (int i = hazards.Count - 1; i >= 0; i--)
            {
                Hazard hazard = hazards[i];
                hazard.position.y += hazard.speed * Time.deltaTime;
                if (hazard.position.y - hazard.size > UiHeight + 20f) { hazards.RemoveAt(i); continue; }
                Rect danger = new Rect(hazard.position.x - hazard.size / 2, hazard.position.y - hazard.size / 2, hazard.size, hazard.size);
                if (player.Overlaps(danger)) { EndSurvival(); return; }
            }
        }

        private float GetMoveAxis()
        {
            if (Keyboard.current == null) return 0f;
            bool left = Keyboard.current.aKey.isPressed || Keyboard.current.leftArrowKey.isPressed;
            bool right = Keyboard.current.dKey.isPressed || Keyboard.current.rightArrowKey.isPressed;
            return left == right ? 0f : left ? -1f : 1f;
        }

        private void StartSurvival(bool bomb)
        {
            if (!data.TrySpendGameStamina()) { resultTitle = "체력이 부족합니다"; resultDetail = "다음 체력 회복까지 기다려 주세요."; screen = Screen.Result; return; }
            isBombMode = bomb;
            elapsed = 0f;
            spawnTimer = .5f;
            hazards.Clear();
            playerX = UiWidth * .5f;
            screen = bomb ? Screen.Bomb : Screen.Rush;
        }

        private void ShowNoStamina()
        {
            resultTitle = "체력이 부족합니다";
            resultDetail = "다음 체력 회복까지 기다려 주세요.";
            screen = Screen.Result;
        }

        private void StartRandomMatch()
        {
            if (!data.TrySpendGameStamina()) { resultTitle = "체력이 부족합니다"; resultDetail = "다음 체력 회복까지 기다려 주세요."; screen = Screen.Result; return; }
            matchTimer = 0f;
            screen = Screen.Matchmaking;
        }

        private void TryAdStaminaRecovery()
        {
            if (data.TryRecoverStaminaByAd(out int recovered))
            {
                resultTitle = "AD REWARD";
                resultDetail = $"테스트 광고 보상으로 체력 {recovered}를 회복했습니다.";
            }
            else if (data.Stamina >= 100)
            {
                resultTitle = "체력이 가득 찼습니다";
                resultDetail = "체력을 사용한 후 다시 시도해 주세요.";
            }
            else
            {
                resultTitle = "오늘의 광고 보상을 모두 받았습니다";
                resultDetail = "광고 체력 회복은 하루 최대 5회입니다.";
            }
            screen = Screen.Result;
        }

        private void EndSurvival()
        {
            int reward = Mathf.Max(1, Mathf.FloorToInt(elapsed / 15f));
            data.RewardDiamonds(reward);
            resultTitle = "MISSION COMPLETE";
            resultDetail = $"생존 {elapsed:F1}초  ·  다이아 +{reward}";
            screen = Screen.Result;
        }

        private void OnGUI()
        {
            Matrix4x4 previousMatrix = GUI.matrix;
            GUI.matrix = Matrix4x4.TRS(UiOrigin, Quaternion.identity, Vector3.one * UiScale);
            GUI.backgroundColor = ink;
            GUI.Box(new Rect(0, 0, UiWidth, UiHeight), GUIContent.none);
            if (screen == Screen.Lobby) DrawLobby();
            else if (screen == Screen.Matchmaking) DrawMatchmaking();
            else if (screen == Screen.Duel) DrawDuel();
            else if (screen == Screen.Pve) DrawPve();
            else if (screen == Screen.Rush || screen == Screen.Bomb) DrawSurvival();
            else if (screen == Screen.Result) DrawResult();
            else if (screen == Screen.Ranking) DrawRanking();
            else if (screen == Screen.Account) DrawAccount();
            else DrawWorkshop();
            GUI.matrix = previousMatrix;
        }

        private void DrawLobby()
        {
            Label(new Rect(34, 34, 500, 35), "WARFRONT", 30, acid);
            Label(new Rect(36, 76, 500, 24), "전쟁 스토리 · MVP BUILD 0.1", 13, Color.white);
            if (GUI.Button(new Rect(UiWidth - 280, 42, 245, 42), "서버 계정")) screen = Screen.Account;
            Panel(new Rect(28, 124, UiWidth - 56, 86));
            Label(new Rect(52, 145, 180, 22), $"체력  {data.Stamina} / 100", 18, Color.white);
            Label(new Rect(52, 174, 180, 16), data.RecoveryText(), 11, new Color(.7f, .7f, .74f));
            if (GUI.Button(new Rect(300, 164, 230, 30), $"광고 보기 · 체력 +10  ({data.DailyAdViews}/5)")) TryAdStaminaRecovery();
            Label(new Rect(UiWidth - 210, 145, 170, 22), $"◆ {data.Diamonds}", 20, acid);
            Label(new Rect(UiWidth - 210, 174, 170, 16), $"RATING  {data.Rating}", 11, new Color(.7f, .7f, .74f));

            Label(new Rect(32, 245, 500, 30), "PLAY NOW", 20, Color.white);
            if (Button(new Rect(28, 290, UiWidth - 56, 67), "1 : 1  랜덤 매칭", "AI 지휘관 전투 · 승리 +100점 · 체력 10")) StartRandomMatch();
            if (Button(new Rect(28, 370, UiWidth - 56, 67), "돌격 게임", "탄환과 박쥐를 오래 피하세요 · 체력 10")) StartSurvival(false);
            if (Button(new Rect(28, 450, UiWidth - 56, 67), "폭탄 피하기", "점점 커지는 폭탄을 피해 생존하세요 · 체력 10")) StartSurvival(true);
            if (Button(new Rect(28, 540, UiWidth - 56, 50), "랭킹 보기", $"승 {data.Wins} · 패 {data.Losses} · 현재 점수 {data.Rating}")) screen = Screen.Ranking;
            if (Button(new Rect(28, 603, UiWidth - 56, 50), "정비소", $"전투력 {data.Power} · 다이아로 지휘관을 강화합니다")) screen = Screen.Workshop;
            if (Button(new Rect(28, 666, UiWidth - 56, 42), "PvE 작전", $"최고 작전 {data.PveBestStage} · 체력 10")) StartPve();
        }

        private void DrawMatchmaking()
        {
            Center("MATCHMAKING", UiHeight * .38f, 30, acid);
            Center("상대 지휘관을 찾는 중...", UiHeight * .46f, 16, Color.white);
            Center($"{Mathf.CeilToInt(Mathf.Max(0, 2f - matchTimer))}초", UiHeight * .54f, 42, Color.white);
        }

        private void DrawDuel()
        {
            Label(new Rect(30, 30, 500, 28), "1 : 1 COMMAND DUEL", 24, acid);
            DrawHealthBar(new Rect(34, 95, UiWidth - 68, 30), playerHp / 100f, acid, $"나의 군단  {playerHp} HP");
            DrawHealthBar(new Rect(34, 152, UiWidth - 68, 30), enemyHp / 100f, new Color(1f, .36f, .25f), $"적 군단  {enemyHp} HP");
            Center("⚔", UiHeight * .37f, 90, Color.white);
            Center(duelLog, UiHeight * .57f, 14, Color.white);
            string attackText = playerAttackCooldown > 0f ? $"재장전 {playerAttackCooldown:F1}s" : "돌격 공격  [ SPACE ]";
            if (GUI.Button(new Rect(UiWidth / 2f - 125, UiHeight * .68f, 250, 58), attackText)) TryPlayerAttack();
        }

        private void DrawPve()
        {
            Label(new Rect(30, 30, 500, 28), $"PVE OPERATION  {pveStage:00}", 24, acid);
            DrawHealthBar(new Rect(34, 95, UiWidth - 68, 30), playerHp / (100f + data.Power * 5), acid, $"내 군단  {playerHp} HP");
            float enemyMaxHp = 70f + pveStage * 35f;
            DrawHealthBar(new Rect(34, 152, UiWidth - 68, 30), enemyHp / enemyMaxHp, new Color(1f, .36f, .25f), $"적 방어선  {enemyHp} HP");
            Center("◆", UiHeight * .37f, 82, acid);
            Center(duelLog, UiHeight * .57f, 14, Color.white);
            string attackText = playerAttackCooldown > 0f ? $"재장전 {playerAttackCooldown:F1}s" : "전선 돌파  [ SPACE ]";
            if (GUI.Button(new Rect(UiWidth / 2f - 125, UiHeight * .68f, 250, 58), attackText)) TryPveAttack();
        }

        private void DrawHealthBar(Rect rect, float fraction, Color color, string text)
        {
            GUI.color = new Color(.2f, .21f, .28f);
            GUI.DrawTexture(rect, Texture2D.whiteTexture);
            GUI.color = color;
            GUI.DrawTexture(new Rect(rect.x, rect.y, rect.width * Mathf.Clamp01(fraction), rect.height), Texture2D.whiteTexture);
            GUI.color = Color.white;
            GUIStyle style = new GUIStyle(GUI.skin.label) { fontSize = 13, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter, normal = { textColor = ink } };
            GUI.Label(rect, text, style);
        }

        private void DrawSurvival()
        {
            Label(new Rect(30, 30, 400, 28), isBombMode ? "BOMB RUN" : "CHARGE RUN", 24, acid);
            Label(new Rect(30, 64, 400, 18), $"생존 시간  {elapsed:F1}s", 14, Color.white);
            Label(new Rect(30, 90, 400, 15), "A / D 또는 화면을 드래그해 이동", 11, new Color(.7f, .7f, .74f));
            GUI.color = acid;
            GUI.DrawTexture(new Rect(playerX - 23, UiHeight - 132, 46, 44), Texture2D.whiteTexture);
            GUI.color = isBombMode ? new Color(1f, .38f, .2f) : new Color(.68f, .56f, 1f);
            foreach (Hazard hazard in hazards)
                GUI.DrawTexture(new Rect(hazard.position.x - hazard.size / 2, hazard.position.y - hazard.size / 2, hazard.size, hazard.size), Texture2D.whiteTexture);
            GUI.color = Color.white;
        }

        private void DrawResult()
        {
            Center(resultTitle, UiHeight * .38f, 30, acid);
            Center(resultDetail, UiHeight * .47f, 15, Color.white);
            if (GUI.Button(new Rect(UiWidth / 2f - 110, UiHeight * .59f, 220, 48), "로비로 돌아가기")) screen = Screen.Lobby;
        }

        private void DrawRanking()
        {
            Label(new Rect(34, 38, 500, 30), "DAILY RANKING", 25, acid);
            string[] names = { "IRON FALCON", "NOVA COMMAND", "RED SQUAD", "YOU" };
            int[] scores = { data.Rating + 240, data.Rating + 90, data.Rating + 25, data.Rating };
            for (int i = 0; i < names.Length; i++)
            {
                Panel(new Rect(28, 95 + i * 62, UiWidth - 56, 49));
                Label(new Rect(48, 110 + i * 62, 50, 20), $"{i + 1:00}", 16, i == 3 ? acid : Color.white);
                Label(new Rect(112, 110 + i * 62, 220, 20), names[i], 16, Color.white);
                Label(new Rect(UiWidth - 146, 110 + i * 62, 105, 20), scores[i].ToString(), 16, i == 3 ? acid : Color.white);
            }
            int rank = 4;
            string rewardText = data.HasClaimedDailyReward() ? "오늘의 일일 보상을 수령했습니다." : "현재 4위 보상: 다이아 10개";
            Center(rewardText, UiHeight - 132, 12, new Color(.75f, .75f, .78f));
            if (!data.HasClaimedDailyReward() && GUI.Button(new Rect(UiWidth / 2f - 110, UiHeight - 100, 220, 38), "일일 보상 받기"))
            {
                data.TryClaimDailyReward(rank, out int reward);
                resultTitle = "DAILY REWARD";
                resultDetail = $"일일 랭킹 보상으로 다이아 {reward}개를 받았습니다.";
                screen = Screen.Result;
            }
            if (GUI.Button(new Rect(UiWidth / 2f - 110, UiHeight - 53, 220, 38), "로비로 돌아가기")) screen = Screen.Lobby;
        }

        private IEnumerator RefreshAccount()
        {
            accountBusy = true;
            accountMessage = "서버 계정을 확인하는 중입니다...";
            try
            {
                if (!api.IsAuthenticated)
                    yield return api.Login(guestDeviceId, guestDisplayName.Trim(), AcceptServerPlayer, AccountFailed);
                if (!api.IsAuthenticated) yield break;

                bool expired = false;
                yield return api.GetPlayer(AcceptServerPlayer, (code, message) =>
                {
                    expired = code == 401;
                    AccountFailed(code, message);
                });
                if (expired)
                {
                    accountMessage = "세션을 갱신하는 중입니다...";
                    yield return api.Login(guestDeviceId, guestDisplayName.Trim(), AcceptServerPlayer, AccountFailed);
                    if (api.IsAuthenticated)
                        yield return api.GetPlayer(AcceptServerPlayer, AccountFailed);
                }
            }
            finally { accountBusy = false; }
        }

        private void AcceptServerPlayer(ServerPlayer player)
        {
            serverPlayer = player;
            guestDisplayName = player.display_name;
            PlayerPrefs.SetString("serverGuestDisplayName", guestDisplayName);
            PlayerPrefs.Save();
            accountUpdatedAt = DateTime.Now.ToString("HH:mm:ss");
            accountMessage = "서버 계정이 연결되었습니다.";
        }

        private void AccountFailed(long code, string message)
        {
            accountMessage = message;
        }

        private void DrawAccount()
        {
            Label(new Rect(34, 38, 600, 35), "SERVER ACCOUNT", 25, acid);
            Label(new Rect(36, 88, UiWidth - 72, 26), "로컬 연습과 별도로 서버에 저장된 계정을 조회합니다.", 15, Color.white);
            Label(new Rect(36, 132, 180, 28), "지휘관 이름", 16, Color.white);
            bool wasEnabled = GUI.enabled;
            GUI.enabled = wasEnabled && !accountBusy && !api.IsAuthenticated;
            guestDisplayName = GUI.TextField(new Rect(220, 132, 390, 32), guestDisplayName, 24);
            GUI.enabled = wasEnabled && !accountBusy;
            if (GUI.Button(new Rect(640, 132, 230, 36), accountBusy ? "연결 중..." : api.IsAuthenticated ? "서버 상태 새로고침" : "게스트 로그인"))
                StartCoroutine(RefreshAccount());
            GUI.enabled = wasEnabled;
            Label(new Rect(36, 186, UiWidth - 72, 34), accountMessage, 15, acid);

            if (serverPlayer != null)
            {
                Panel(new Rect(28, 245, UiWidth - 56, 265));
                Label(new Rect(52, 265, 1100, 30), $"{serverPlayer.display_name}  ·  마지막 조회 {accountUpdatedAt}", 21, Color.white);
                Label(new Rect(52, 318, 500, 28), $"체력 {serverPlayer.stamina}/100  ·  다이아 {serverPlayer.diamonds}", 19, acid);
                Label(new Rect(52, 365, 1100, 28), $"점수 {serverPlayer.rating}  ·  승 {serverPlayer.wins} / 패 {serverPlayer.losses}", 19, Color.white);
                Label(new Rect(52, 412, 1100, 28), $"전투력 {serverPlayer.power}  ·  최고 작전 {serverPlayer.pve_best_stage}", 19, Color.white);
                string recovery = serverPlayer.next_stamina_in_seconds < 0 ? "체력 MAX" : $"조회 시 다음 회복까지 {serverPlayer.next_stamina_in_seconds}초";
                Label(new Rect(52, 459, 1100, 26), recovery, 15, Color.white);
            }
            Center("현재 전투와 보상은 로컬 연습 데이터에 반영됩니다.", 550, 15, Color.white);
            if (GUI.Button(new Rect(UiWidth / 2f - 110, 635, 220, 42), "로비로 돌아가기")) screen = Screen.Lobby;
        }

        private void DrawWorkshop()
        {
            Label(new Rect(34, 38, 500, 30), "COMMAND WORKSHOP", 25, acid);
            Center("전투력을 올려 1:1 전투의 공격력을 강화하세요.", UiHeight * .25f, 14, Color.white);
            Center($"현재 전투력  {data.Power}", UiHeight * .37f, 38, acid);
            Center($"공격력 보너스  +{data.Power * 2}", UiHeight * .46f, 16, Color.white);
            string upgradeText = $"강화하기  ◆ {data.UpgradeCost}";
            if (GUI.Button(new Rect(UiWidth / 2f - 125, UiHeight * .60f, 250, 50), upgradeText))
            {
                if (data.TryUpgradePower())
                {
                    resultTitle = "UPGRADE COMPLETE";
                    resultDetail = $"전투력이 {data.Power}로 상승했습니다.";
                    screen = Screen.Result;
                }
                else
                {
                    resultTitle = "다이아가 부족합니다";
                    resultDetail = $"강화에는 다이아 {data.UpgradeCost}개가 필요합니다.";
                    screen = Screen.Result;
                }
            }
            if (GUI.Button(new Rect(UiWidth / 2f - 110, UiHeight * .72f, 220, 42), "로비로 돌아가기")) screen = Screen.Lobby;
        }

        private bool Button(Rect rect, string title, string subtitle)
        {
            Panel(rect);
            Label(new Rect(rect.x + 20, rect.y + 12, rect.width - 40, 21), title, 17, Color.white);
            Label(new Rect(rect.x + 20, rect.y + 37, rect.width - 40, 15), subtitle, 10, new Color(.7f, .7f, .74f));
            return GUI.Button(rect, GUIContent.none, GUIStyle.none);
        }

        private void Panel(Rect rect) { GUI.color = new Color(.12f, .13f, .2f); GUI.DrawTexture(rect, Texture2D.whiteTexture); GUI.color = Color.white; }
        private void Label(Rect rect, string text, int size, Color color) { GUIStyle s = new GUIStyle(GUI.skin.label) { fontSize = size, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleLeft, normal = { textColor = color } }; GUI.Label(rect, text, s); }
        private void Center(string text, float y, int size, Color color) { GUIStyle s = new GUIStyle(GUI.skin.label) { fontSize = size, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter, normal = { textColor = color } }; GUI.Label(new Rect(20, y, UiWidth - 40, 55), text, s); }
    }
}

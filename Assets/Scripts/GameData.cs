using System;
using UnityEngine;

namespace Warfront
{
    /// <summary>
    /// MVP 로컬 저장소. 프로덕션에서는 FastAPI의 Player API 구현체로 교체한다.
    /// </summary>
    public sealed class GameData
    {
        private const int MaxStamina = 100;
        private const int GameCost = 10;
        private const float RecoverySeconds = 60f * 60f;
        private const int RecoveryAmount = 5;

        public int Stamina { get; private set; }
        public int Diamonds { get; private set; }
        public int Rating { get; private set; }
        public int Wins { get; private set; }
        public int Losses { get; private set; }
        public int Power { get; private set; }
        public int PveBestStage { get; private set; }
        public int UpgradeCost => 10 + Power * 5;
        public int DailyAdViews
        {
            get
            {
                ResetDailyAdViewsIfNeeded();
                return PlayerPrefs.GetInt("dailyAdViews", 0);
            }
        }

        public GameData()
        {
            Stamina = PlayerPrefs.GetInt("stamina", MaxStamina);
            Diamonds = PlayerPrefs.GetInt("diamonds", 0);
            Rating = PlayerPrefs.GetInt("rating", 1000);
            Wins = PlayerPrefs.GetInt("wins", 0);
            Losses = PlayerPrefs.GetInt("losses", 0);
            Power = PlayerPrefs.GetInt("power", 0);
            PveBestStage = PlayerPrefs.GetInt("pveBestStage", 0);
            RecoverStamina();
        }

        public bool TrySpendGameStamina()
        {
            RecoverStamina();
            if (Stamina < GameCost) return false;
            if (Stamina >= MaxStamina)
                PlayerPrefs.SetString("staminaLast", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString());
            Stamina -= GameCost;
            Save();
            return true;
        }

        public void RewardDiamonds(int amount)
        {
            Diamonds += Mathf.Max(0, amount);
            Save();
        }

        public void RecordPvpResult(bool won)
        {
            Rating = Mathf.Max(0, Rating + (won ? 100 : -100));
            if (won) { Wins++; RewardDiamonds(3); }
            else Losses++;
            Save();
        }

        public bool TryClaimDailyReward(int rank, out int reward)
        {
            string today = DateTime.UtcNow.ToString("yyyy-MM-dd");
            if (PlayerPrefs.GetString("dailyRewardDate", string.Empty) == today)
            {
                reward = 0;
                return false;
            }

            reward = rank == 1 ? 100 : rank == 2 ? 50 : rank == 3 ? 20 : rank <= 10 ? 10 : rank <= 20 ? 5 : 0;
            if (reward == 0) return false;

            PlayerPrefs.SetString("dailyRewardDate", today);
            RewardDiamonds(reward);
            return true;
        }

        public bool HasClaimedDailyReward()
        {
            return PlayerPrefs.GetString("dailyRewardDate", string.Empty) == DateTime.UtcNow.ToString("yyyy-MM-dd");
        }

        public bool TryUpgradePower()
        {
            if (Diamonds < UpgradeCost) return false;
            Diamonds -= UpgradeCost;
            Power++;
            Save();
            return true;
        }

        public void RecordPveClear(int stage)
        {
            PveBestStage = Mathf.Max(PveBestStage, stage);
            Save();
        }

        public bool TryRecoverStaminaByAd(out int recovered)
        {
            ResetDailyAdViewsIfNeeded();
            if (DailyAdViews >= 5 || Stamina >= MaxStamina)
            {
                recovered = 0;
                return false;
            }

            int before = Stamina;
            Stamina = Mathf.Min(MaxStamina, Stamina + 10);
            PlayerPrefs.SetInt("dailyAdViews", DailyAdViews + 1);
            recovered = Stamina - before;
            Save();
            return true;
        }

        public void RecoverStamina()
        {
            long now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            if (Stamina >= MaxStamina) return;
            long last = long.Parse(PlayerPrefs.GetString("staminaLast", now.ToString()));
            long intervals = (now - last) / (long)RecoverySeconds;
            if (intervals <= 0) return;
            Stamina = Mathf.Min(MaxStamina, Stamina + (int)intervals * RecoveryAmount);
            long recoveryStart = Stamina >= MaxStamina ? now : last + intervals * (long)RecoverySeconds;
            PlayerPrefs.SetString("staminaLast", recoveryStart.ToString());
            Save();
        }

        public string RecoveryText()
        {
            if (Stamina >= MaxStamina) return "MAX";
            long now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            long last = long.Parse(PlayerPrefs.GetString("staminaLast", now.ToString()));
            long remain = Math.Max(0L, (long)RecoverySeconds - (now - last));
            return $"다음 회복 {remain / 60:D2}:{remain % 60:D2}";
        }

        private void Save()
        {
            PlayerPrefs.SetInt("stamina", Stamina);
            PlayerPrefs.SetInt("diamonds", Diamonds);
            PlayerPrefs.SetInt("rating", Rating);
            PlayerPrefs.SetInt("wins", Wins);
            PlayerPrefs.SetInt("losses", Losses);
            PlayerPrefs.SetInt("power", Power);
            PlayerPrefs.SetInt("pveBestStage", PveBestStage);
            if (!PlayerPrefs.HasKey("staminaLast"))
                PlayerPrefs.SetString("staminaLast", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString());
            PlayerPrefs.Save();
        }

        private void ResetDailyAdViewsIfNeeded()
        {
            string today = DateTime.Now.ToString("yyyy-MM-dd");
            if (PlayerPrefs.GetString("dailyAdDate", string.Empty) == today) return;
            PlayerPrefs.SetString("dailyAdDate", today);
            PlayerPrefs.SetInt("dailyAdViews", 0);
            PlayerPrefs.Save();
        }
    }
}

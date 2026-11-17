using UnityEngine;
using UnityEngine.UI;

namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private Canvas portraitCanvas;
        private RawImage portraitImage;

        private void LateUpdate()
        {
            bool visible = ready && !busy && screen == Screen.Mmo && mmoWorld != null &&
                HasRetroField && mmoPanel.Length == 0 && !SquadPauseBlocked && !paused;
            if (!visible)
            {
                if (portraitCanvas != null) portraitCanvas.gameObject.SetActive(false);
                if (retroScene != null && HasRetroField && mmoPanel == "equipment")
                {
                    var self = MmoSelf;
                    retroScene.SelectPortraitActor(self != null && self.hp > 0 ? "player:" + self.id : "");
                }
                if (retroScene != null) retroScene.SetPortraitHudVisible(screen == Screen.Mmo && mmoPanel == "equipment");
                return;
            }
            string key = ResolvePortraitActor();
            retroScene.SelectPortraitActor(key);
            retroScene.SetPortraitHudVisible(true);
            if (portraitCanvas == null)
            {
                var root = new GameObject("Unit Portrait HUD", typeof(RectTransform), typeof(Canvas));
                root.transform.SetParent(transform, false);
                portraitCanvas = root.GetComponent<Canvas>();
                portraitCanvas.renderMode = RenderMode.ScreenSpaceOverlay;
                portraitCanvas.sortingOrder = 10;
                // No raycaster: the portrait cannot consume attack, touch or HUD input.
                var frame = new GameObject("Portrait Frame", typeof(RectTransform), typeof(Image));
                frame.transform.SetParent(root.transform, false);
                var border = frame.GetComponent<Image>();
                border.color = new Color(.39f, .32f, .48f, 1);
                border.raycastTarget = false;
                var image = new GameObject("Unit Portrait RawImage", typeof(RectTransform), typeof(RawImage));
                image.transform.SetParent(frame.transform, false);
                portraitImage = image.GetComponent<RawImage>();
                portraitImage.raycastTarget = false;
                var rect = portraitImage.rectTransform;
                rect.anchorMin = Vector2.zero; rect.anchorMax = Vector2.one;
                rect.offsetMin = new Vector2(2, 2); rect.offsetMax = new Vector2(-2, -2);
            }
            portraitCanvas.gameObject.SetActive(true);
            portraitImage.texture = retroScene.Portrait;
            var panel = (RectTransform)portraitImage.transform.parent;
            panel.anchorMin = panel.anchorMax = new Vector2(0, 1);
            panel.pivot = new Vector2(0, 1);
            panel.anchoredPosition = new Vector2(UiOrigin.x + 926 * UiScale, -(UiOrigin.y + 594 * UiScale));
            panel.sizeDelta = new Vector2(86, 112) * UiScale;
        }

        private string ResolvePortraitActor()
        {
            if (SquadModeActive && !FiveFloorActive && strategySquad.Length > 0 && strategySquad != "all")
            {
                // Server-generated member IDs are <squad id>:<slot>; keep a stable representative.
                if (mmoWorld.players != null)
                    foreach (var actor in mmoWorld.players)
                        if (actor.hp > 0 && actor.id.StartsWith(strategySquad + ":", System.StringComparison.Ordinal))
                            return "player:" + actor.id;
                return "";
            }
            var self = MmoSelf;
            return self != null && self.hp > 0 ? "player:" + self.id : "";
        }
    }

    public sealed partial class RetroFantasyScene
    {
        private UnitPortraitStudio portraitStudio;
        private GameObject townPortraitSource;
        public void SelectPortraitActor(string key)
        {
            GameObject actor = null;
            if (!string.IsNullOrEmpty(key)) actors.TryGetValue(key, out actor);
            portraitStudio.SetSource(actor);
        }
        public void SetPortraitHudVisible(bool visible)
        {
            // Equipment still uses the same texture through IMGUI.
            portraitCamera.enabled = visible || townMode;
        }
        private void InitializePortraitStudio()
        {
            portrait = new GameObject("Unit Portrait Studio");
            portrait.transform.SetParent(transform, false);
            portrait.transform.localPosition = new Vector3(-35, 0, 0);
            portraitCamera = CameraNode("Portrait Camera", portrait.transform, 384, 512, out portraitTarget);
            portraitStudio = portrait.AddComponent<UnitPortraitStudio>();
            portraitStudio.Initialize(portraitCamera);
            if (hero != null)
            {
                townPortraitSource = Instantiate(hero, transform);
                townPortraitSource.name = "Equipment portrait source";
                townPortraitSource.AddComponent<RuneKnightVisual>().Configure(false, new Color(.72f, .4f, 1));
                townPortraitSource.SetActive(false);
                portraitStudio.SetSource(townPortraitSource);
            }
        }
        private void RefreshTownPortrait(bool helmetEquipped)
        {
            if (townPortraitSource == null) return;
            var art = townPortraitSource.GetComponent<RuneKnightVisual>();
            art.Configure(helmetEquipped, new Color(.72f, .4f, 1));
            if (townMode) portraitStudio.SetSource(townPortraitSource);
        }
    }
}

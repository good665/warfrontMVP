using UnityEngine;

namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        private Texture2D widgetAtlas;
        private Texture2D[] widgetButtons, widgetIcons;
        private Texture2D widgetPanel;
        private Texture2D widgetHealthFrame;
        private GUISkin widgetSkin;
        private GUIStyle[] widgetFrames;
        private GUIStyle widgetPanelStyle;
        private GUIStyle widgetHealthStyle;
        private bool widgetsLoaded;

        // Pixel bounds use the original 1536 x 1024 sheet, measured from its top-left.
        private Texture2D WidgetSlice(int x, int y, int width, int height, int divisor = 1)
        {
            var texture = new Texture2D(width/divisor, height/divisor, TextureFormat.RGBA32, false);
            texture.name = "Warfront widget";
            texture.hideFlags = HideFlags.HideAndDontSave;
            texture.filterMode = FilterMode.Point;
            texture.wrapMode = TextureWrapMode.Clamp;
            var source=widgetAtlas.GetPixels(x,widgetAtlas.height-y-height,width,height);
            var pixels=new Color[texture.width*texture.height];
            for(int row=0;row<texture.height;row++)for(int column=0;column<texture.width;column++)pixels[row*texture.width+column]=source[row*divisor*width+column*divisor];
            texture.SetPixels(pixels);
            texture.Apply(false, true);
            return texture;
        }

        private void LoadWidgetArt()
        {
            if (widgetsLoaded) return;
            widgetsLoaded = true;
            widgetAtlas = Resources.Load<Texture2D>("Sprites/mini-dungeon-ui-v1");
            if (widgetAtlas == null || !widgetAtlas.isReadable || widgetAtlas.width != 1536 || widgetAtlas.height != 1024) return;
            widgetButtons = new[] { WidgetSlice(40, 26, 460, 130, 4), WidgetSlice(536, 26, 464, 130, 4), WidgetSlice(1034, 26, 466, 130, 4) };
            widgetPanel = RuneSurface(true);
            widgetButtons = new[]{RuneSurface(false),RuneSurface(false),RuneSurface(false)};
            widgetHealthFrame = WidgetSlice(30, 490, 350, 66);
            widgetHealthStyle = new GUIStyle { border = new RectOffset(10, 10, 10, 14), normal = { background = widgetHealthFrame } };
            widgetFrames = new GUIStyle[3];
            for (int i = 0; i < 3; i++)
                widgetFrames[i] = new GUIStyle { border = new RectOffset(4, 4, 4, 7), normal = { background = widgetButtons[i] } };
            widgetPanelStyle = new GUIStyle { border = new RectOffset(7, 7, 7, 10), normal = { background = widgetPanel } };
            widgetIcons = new Texture2D[12];
            int[] columns = { 52, 300, 548, 792, 1038, 1286 };
            for (int i = 0; i < widgetIcons.Length; i++) widgetIcons[i] = WidgetSlice(columns[i % 6], i < 6 ? 596 : 808, 194, 176);
        }

        private GUISkin WidgetSkin(GUISkin original)
        {
            LoadWidgetArt();
            if (widgetButtons == null) return original;
            if (widgetSkin != null) return widgetSkin;
            widgetSkin = Instantiate(original);
            widgetSkin.hideFlags = HideFlags.HideAndDontSave;
            var style = widgetSkin.button;
            style.border = new RectOffset(4, 4, 4, 7);
            style.padding = new RectOffset(12, 12, 6, 6);
            style.fontSize = 16;
            style.fontStyle = FontStyle.Bold;
            style.normal.background = widgetButtons[0];
            style.hover.background = style.active.background = widgetButtons[1];
            style.focused.background=widgetButtons[1];style.onFocused.background=widgetButtons[1];
            style.onNormal.background = style.onHover.background = style.onActive.background = widgetButtons[1];
            style.normal.textColor = style.hover.textColor = style.active.textColor = Color.white;
            style.onNormal.textColor = style.onHover.textColor = style.onActive.textColor = Color.white;
            widgetSkin.box = new GUIStyle(widgetPanelStyle) { padding=new RectOffset(12,12,8,8), alignment=TextAnchor.MiddleCenter, fontSize=14, normal={textColor=new Color(.9f,.88f,1)} };
            foreach(var input in new[]{widgetSkin.textField,widgetSkin.textArea})
            {input.normal.background=widgetPanel;input.focused.background=widgetButtons[0];input.border=new RectOffset(14,14,14,20);input.padding=new RectOffset(12,12,9,9);input.fontSize=18;input.normal.textColor=Color.white;input.focused.textColor=Color.white;}
            widgetSkin.verticalScrollbarThumb.normal.background=widgetButtons[1];
            widgetSkin.horizontalScrollbarThumb.normal.background=widgetButtons[1];
            widgetSkin.toggle.normal.background=widgetButtons[2];widgetSkin.toggle.onNormal.background=widgetButtons[1];widgetSkin.toggle.hover.background=widgetButtons[0];widgetSkin.toggle.onHover.background=widgetButtons[1];
            widgetSkin.toggle.border=new RectOffset(10,10,10,14);widgetSkin.toggle.padding=new RectOffset(28,4,2,2);widgetSkin.toggle.normal.textColor=Color.white;widgetSkin.toggle.onNormal.textColor=Color.white;
            foreach(var chrome in new[]{widgetSkin.verticalScrollbar,widgetSkin.horizontalScrollbar,widgetSkin.verticalScrollbarUpButton,widgetSkin.verticalScrollbarDownButton,widgetSkin.horizontalScrollbarLeftButton,widgetSkin.horizontalScrollbarRightButton,widgetSkin.horizontalSlider,widgetSkin.verticalSlider,widgetSkin.horizontalSliderThumb,widgetSkin.verticalSliderThumb,widgetSkin.window})
            {chrome.normal.background=widgetButtons[0];chrome.hover.background=widgetButtons[1];chrome.active.background=widgetButtons[1];chrome.focused.background=widgetButtons[1];chrome.border=new RectOffset(10,10,10,14);}
            return widgetSkin;
        }

        private bool DrawWidgetFrame(Rect rect, bool panel = false, bool selected = false)
        {
            LoadWidgetArt();
            if (widgetButtons == null) return false;
            var style = panel ? widgetPanelStyle : widgetFrames[!GUI.enabled ? 2 : selected ? 1 : 0];
            Color previous = GUI.color;
            GUI.color = Color.white;
            if (Event.current.type == EventType.Repaint) style.Draw(rect, GUIContent.none, false, false, false, false);
            GUI.color = previous;
            return true;
        }

        private void DrawWidgetIcon(Rect rect, int index)
        {
            LoadWidgetArt();
            if (widgetIcons == null || index < 0 || index >= widgetIcons.Length) return;
            Color previous = GUI.color;
            GUI.color = Color.white;
            GUI.DrawTexture(rect, widgetIcons[index], ScaleMode.ScaleToFit, true);
            GUI.color = previous;
        }

        private void DisposeWidgetArt()
        {
            if (widgetButtons != null) foreach (var texture in widgetButtons) ReleaseWidget(texture);
            if (widgetIcons != null) foreach (var texture in widgetIcons) ReleaseWidget(texture);
            ReleaseWidget(widgetPanel);
            ReleaseWidget(widgetHealthFrame);
            ReleaseWidget(widgetSkin);
        }

        private static void ReleaseWidget(Object resource)
        {
            if (resource == null) return;
            if (Application.isPlaying) Destroy(resource); else DestroyImmediate(resource);
        }

        private bool DrawWidgetHealth(Rect rect, float fraction, Color color)
        {
            LoadWidgetArt();
            if (widgetHealthStyle == null) return false;
            Color previous = GUI.color;
            GUI.color = Color.white;
            if (Event.current.type == EventType.Repaint) widgetHealthStyle.Draw(rect, GUIContent.none, false, false, false, false);
            Rect fill = new Rect(rect.x + 10, rect.y + 6, Mathf.Max(0, rect.width - 20) * Mathf.Clamp01(fraction), Mathf.Max(0, rect.height - 12));
            GUI.color = color;
            GUI.DrawTexture(fill, Texture2D.whiteTexture);
            GUI.color = previous;
            return true;
        }
    }
}

using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Warfront;

// Run without the backend: Unity -batchmode -projectPath ... -executeMethod UnitPortraitValidation.Run
public static class UnitPortraitValidation
{
    [MenuItem("Warfront/Validate Unit Portrait")]
    public static void Run()
    {
        string output = Path.Combine(Path.GetTempPath(), "WarfrontPortraitValidation");
        Directory.CreateDirectory(output);
        var scene = EditorSceneManager.NewPreviewScene();
        GameObject root = null;
        RenderTexture target = null;
        try
        {
            root = new GameObject("Portrait validation");
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);
            var camera = new GameObject("Validation Portrait Camera").AddComponent<Camera>();
            camera.transform.SetParent(root.transform, false);
            camera.scene = scene;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.GetUniversalAdditionalCameraData().SetRenderer(Resources.Load<RetroRenderConfig>("RetroFantasy/RenderConfig").rendererIndex);
            target = new RenderTexture(384, 512, 24); target.Create(); camera.targetTexture = target;
            var studio = root.AddComponent<UnitPortraitStudio>(); studio.Initialize(camera);
            string[] resources = { "MiniDungeon/Characters/Human", "MiniDungeon/Characters/Orc", "Zodiac/rat/Character", "Zodiac/dragon/Character" };
            int checks = 0;
            foreach (string resource in resources)
            {
                var prefab = Resources.Load<GameObject>(resource);
                Require(prefab != null, "Missing fixture: " + resource);
                var source = UnityEngine.Object.Instantiate(prefab, root.transform);
                source.transform.localPosition = Vector3.right * 30;
                Vector3 original = source.transform.position;
                studio.SetSource(source);
                Require(studio.DisplayModel != null, "Selected model missing");
                foreach (var component in studio.DisplayModel.GetComponentsInChildren<Component>(true))
                    Require(component is Transform || component is Renderer || component is MeshFilter, "Gameplay component copied: " + component.GetType());
                foreach (var renderer in studio.DisplayModel.GetComponentsInChildren<Renderer>(true))
                    Require(renderer.gameObject.layer == UnitPortraitStudio.PortraitLayer, "Portrait layer isolation failed");
                foreach (var light in root.GetComponentsInChildren<Light>())
                    Require(light.cullingMask == (1 << UnitPortraitStudio.PortraitLayer), "Light isolation failed");
                var model = studio.DisplayModel;
                studio.SetSource(source); Require(model == studio.DisplayModel, "Unchanged selection rebuilt");
                studio.SampleIdle(0);
                var bones = model.GetComponentsInChildren<Transform>(true);
                var rotations = new Quaternion[bones.Length];
                for (int i = 0; i < bones.Length; i++) rotations[i] = bones[i].localRotation;
                studio.SampleIdle(1.7f);
                bool changed = false;
                for (int i = 0; i < bones.Length; i++) changed |= Quaternion.Angle(rotations[i], bones[i].localRotation) > .01f;
                Require(changed, "Idle/head motion missing: " + resource);
                var positions = new Vector3[bones.Length];
                var scales = new Vector3[bones.Length];
                for (int i = 0; i < bones.Length; i++) { positions[i] = bones[i].localPosition; scales[i] = bones[i].localScale; rotations[i] = bones[i].localRotation; }
                for (int frame = 0; frame < 600; frame++) studio.SampleIdle(1.7f);
                for (int i = 0; i < bones.Length; i++)
                    Require(Vector3.Distance(positions[i], bones[i].localPosition) < .00001f && Vector3.Distance(scales[i], bones[i].localScale) < .00001f && Quaternion.Angle(rotations[i], bones[i].localRotation) < .01f, "Accumulating idle deformation: " + resource);
                Require(source.transform.position == original, "Portrait moved source unit");
                RenderPipeline.SubmitRenderRequest(camera, new UniversalRenderPipeline.SingleCameraRequest { destination = target });
                var texture = new Texture2D(target.width, target.height, TextureFormat.RGB24, false);
                var previous = RenderTexture.active; RenderTexture.active = target;
                texture.ReadPixels(new Rect(0, 0, target.width, target.height), 0, 0); texture.Apply(); RenderTexture.active = previous;
                int foreground = 0;
                var pixels = texture.GetPixels32();
                foreach (var pixel in pixels) if (pixel.r > 40 || pixel.g > 40 || pixel.b > 65) foreground++;
                Require(foreground > pixels.Length / 50, "Empty/dark render: " + resource + " foreground=" + foreground);
                File.WriteAllBytes(Path.Combine(output, resource.Replace('/', '_') + ".png"), texture.EncodeToPNG());
                UnityEngine.Object.DestroyImmediate(texture);
                studio.SetSource(null); Require(studio.DisplayModel == null, "Missing selection retained old portrait");
                UnityEngine.Object.DestroyImmediate(source);
                checks++;
            }
            // Exercise complete scene initialization and legacy equipment texture ownership.
            var presentation = new GameObject("Integration validation");
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(presentation, scene);
            var retro = presentation.AddComponent<RetroFantasyScene>(); retro.Initialize();
            Require(retro.Portrait is RenderTexture rt && rt.IsCreated(), "Integration RT not created");
            var portraitCamera = presentation.transform.Find("Unit Portrait Studio/Portrait Camera").GetComponent<Camera>();
            Require(portraitCamera.cullingMask == 1 << UnitPortraitStudio.PortraitLayer, "Studio layer overwritten during initialize");
            ValidateHud(retro);
            retro.SelectPortraitActor("");
            UnityEngine.Object.DestroyImmediate(presentation);
            File.WriteAllText(Path.Combine(output, "result.txt"), "PASS: " + checks + " visual fixtures; selection reuse/clear; motion; source/layer/light isolation; full scene initialization and teardown.\n");
            Debug.Log("UNIT_PORTRAIT_VALIDATION_PASS " + output);
        }
        catch (Exception exception)
        {
            File.WriteAllText(Path.Combine(output, "result.txt"), exception.ToString());
            Debug.LogException(exception);
            if (Application.isBatchMode) EditorApplication.Exit(1);
            throw;
        }
        finally
        {
            if (root != null) UnityEngine.Object.DestroyImmediate(root);
            if (target != null) { target.Release(); UnityEngine.Object.DestroyImmediate(target); }
            EditorSceneManager.ClosePreviewScene(scene);
        }
        if (Application.isBatchMode) EditorApplication.Exit(0);
    }
    private static void ValidateHud(RetroFantasyScene retro)
    {
        const System.Reflection.BindingFlags flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
        var type = typeof(GameBootstrap);
        var host = new GameObject("Offline portrait HUD checks"); host.SetActive(false);
        var game = host.AddComponent<GameBootstrap>();
        Action<string, object> set = (name, value) => type.GetField(name, flags).SetValue(game, value);
        Func<string, object> call = name => type.GetMethod(name, flags).Invoke(game, null);
        var hero = new MmoActor { id = "hero", hp = 100 };
        var member = new MmoActor { id = "group:1", hp = 100 };
        var world = new MmoSnapshot { you_id = "hero", players = new[] { hero, new MmoActor { id = "group:0", hp = 0 }, member } };
        set("mmoWorld", world); set("squadMode", true); set("strategySquad", "group");
        Require((string)call("ResolvePortraitActor") == "player:group:1", "Dead squad representative selected");
        set("strategySquad", "missing"); Require((string)call("ResolvePortraitActor") == "", "Missing squad used unrelated hero");
        set("strategySquad", "all"); Require((string)call("ResolvePortraitActor") == "player:hero", "All selection lacks hero fallback");
        set("squadMode", false); set("retroScene", retro); set("ready", true); set("mmoPanel", "");
        set("screen", Enum.Parse(type.GetField("screen", flags).FieldType, "Mmo"));
        var actor = UnityEngine.Object.Instantiate(Resources.Load<GameObject>("MiniDungeon/Characters/Human"), retro.transform);
        actor.AddComponent<RuneKnightVisual>().Configure(false, Color.magenta);
        var actors = (System.Collections.Generic.Dictionary<string, GameObject>)typeof(RetroFantasyScene).GetField("actors", flags).GetValue(retro);
        actors["player:hero"] = actor;
        typeof(RetroFantasyScene).GetField("townMode", flags).SetValue(retro, false);
        call("LateUpdate");
        var canvas = (Canvas)type.GetField("portraitCanvas", flags).GetValue(game);
        var image = canvas.GetComponentInChildren<UnityEngine.UI.RawImage>(true);
        Require(image != null && image.texture == retro.Portrait && !image.raycastTarget, "HUD RawImage binding/input isolation failed");
        Require(canvas.GetComponent<UnityEngine.UI.GraphicRaycaster>() == null, "Portrait consumes HUD input");
        var studio = retro.GetComponentInChildren<UnitPortraitStudio>();
        var before = studio.DisplayModel;
        set("mmoPanel", "equipment");
        retro.EquipmentAppearance("player:hero", true);
        call("LateUpdate");
        Require(studio.DisplayModel != before, "Equipment menu failed to refresh changed helmet");
        Require(!canvas.gameObject.activeSelf, "HUD overlays equipment menu");
        set("mmoPanel", ""); hero.hp = 0; call("LateUpdate");
        Require(studio.DisplayModel == null, "Dead hero portrait retained");
        UnityEngine.Object.DestroyImmediate(host);
    }
    private static void Require(bool condition, string message) { if (!condition) throw new Exception(message); }
}

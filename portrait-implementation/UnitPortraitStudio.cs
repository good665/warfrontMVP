using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Warfront
{
    // Copies rendering data only. Never instantiates combat, audio or lifecycle scripts.
    [DefaultExecutionOrder(200)]
    public sealed class UnitPortraitStudio : MonoBehaviour
    {
        public const int PortraitLayer = 29;
        private Camera portraitCamera;
        private GameObject source, model;
        private AnimationClip idle;
        private Transform head, torso;
        private Vector3 torsoPosition, torsoScale;
        private Quaternion headRotation;
        private readonly List<Material> ownedMaterials = new List<Material>();
        private readonly List<Mesh> ownedMeshes = new List<Mesh>();
        private int appearance;
        public GameObject DisplayModel => model;

        public void Initialize(Camera camera)
        {
            portraitCamera = camera;
            camera.cullingMask = 1 << PortraitLayer;
            camera.backgroundColor = new Color(.012f, .018f, .032f, 1);
            camera.orthographic = true;
            camera.nearClipPlane = .02f;
            camera.farClipPlane = 20;
            camera.useOcclusionCulling = false;
            AddLight("Portrait Key", new Vector3(2, 3, 3), new Color(1, .83f, .68f), 8);
            AddLight("Portrait Fill", new Vector3(-2, 1.8f, 2), new Color(.42f, .61f, 1), 3);
            AddLight("Portrait Rim", new Vector3(-1.5f, 2.8f, -1.5f), new Color(.42f, .64f, 1), 12);
        }

        private void AddLight(string label, Vector3 position, Color color, float intensity)
        {
            var node = new GameObject(label);
            node.transform.SetParent(transform, false);
            node.transform.localPosition = position;
            var light = node.AddComponent<Light>();
            light.type = LightType.Point;
            light.range = 8;
            light.color = color;
            light.intensity = intensity;
            light.cullingMask = 1 << PortraitLayer;
            light.shadows = LightShadows.None;
        }

        public void SetSource(GameObject actor)
        {
            int signature = AppearanceSignature(actor);
            if (actor == source && signature == appearance && (actor == null || model != null)) return;
            ClearModel();
            source = actor;
            appearance = signature;
            if (actor == null) return;
            var map = new Dictionary<Transform, Transform>();
            model = CopyTransforms(actor.transform, transform, map).gameObject;
            model.name = "Portrait visual only: " + actor.name;
            model.transform.localPosition = Vector3.zero;
            model.transform.localRotation = Quaternion.identity;
            model.transform.localScale = Vector3.one;
            model.SetActive(true);
            foreach (var renderer in actor.GetComponentsInChildren<Renderer>(true))
            {
                Renderer copy;
                if (renderer is SkinnedMeshRenderer skin)
                {
                    var target = map[skin.transform].gameObject.AddComponent<SkinnedMeshRenderer>();
                    target.sharedMesh = skin.sharedMesh;
                    var bones = skin.bones;
                    for (int i = 0; i < bones.Length; i++) bones[i] = bones[i] != null && map.TryGetValue(bones[i], out var bone) ? bone : null;
                    target.bones = bones;
                    target.rootBone = skin.rootBone != null && map.TryGetValue(skin.rootBone, out var root) ? root : null;
                    target.localBounds = skin.localBounds;
                    target.updateWhenOffscreen = true;
                    for (int i = 0; skin.sharedMesh != null && i < skin.sharedMesh.blendShapeCount; i++) target.SetBlendShapeWeight(i, skin.GetBlendShapeWeight(i));
                    copy = target;
                }
                else if (renderer is MeshRenderer && renderer.TryGetComponent<MeshFilter>(out var filter))
                {
                    // Runtime armor meshes may be destroyed with the source unit.
                    var mesh = filter.sharedMesh != null ? Instantiate(filter.sharedMesh) : null;
                    if (mesh != null) ownedMeshes.Add(mesh);
                    map[renderer.transform].gameObject.AddComponent<MeshFilter>().sharedMesh = mesh;
                    copy = map[renderer.transform].gameObject.AddComponent<MeshRenderer>();
                }
                else continue; // Excludes trails, particles and combat lines.
                var materials = renderer.sharedMaterials;
                for (int i = 0; i < materials.Length; i++)
                {
                    if (materials[i] == null) continue;
                    materials[i] = new Material(materials[i]);
                    ownedMaterials.Add(materials[i]);
                }
                copy.sharedMaterials = materials;
                copy.enabled = renderer.enabled;
                copy.shadowCastingMode = ShadowCastingMode.Off;
                copy.receiveShadows = false;
                copy.lightProbeUsage = LightProbeUsage.Off;
                copy.reflectionProbeUsage = ReflectionProbeUsage.Off;
            }
            var animation = actor.GetComponent<Animation>();
            idle = animation != null ? animation.GetClip("Idle") : null;
            head = model.transform.Find("root/torso/head");
            torso = model.transform.Find("root/torso");
            foreach (var bone in model.GetComponentsInChildren<Transform>(true))
            {
                if (head == null && bone.name.ToLowerInvariant() == "head") head = bone;
                if (torso == null && bone.name.ToLowerInvariant() == "torso") torso = bone;
            }
            if (idle != null) idle.SampleAnimation(model, 0);
            if (head != null) headRotation = head.localRotation;
            if (torso != null) { torsoPosition = torso.localPosition; torsoScale = torso.localScale; }
            FrameBust();
        }

        private static Transform CopyTransforms(Transform original, Transform parent, Dictionary<Transform, Transform> map)
        {
            var copy = new GameObject(original.name).transform;
            copy.gameObject.layer = PortraitLayer;
            copy.SetParent(parent, false);
            copy.localPosition = original.localPosition;
            copy.localRotation = original.localRotation;
            copy.localScale = original.localScale;
            copy.gameObject.SetActive(original.gameObject.activeSelf);
            map.Add(original, copy);
            foreach (Transform child in original) CopyTransforms(child, copy, map);
            return copy;
        }

        private static int AppearanceSignature(GameObject actor)
        {
            if (actor == null) return 0;
            unchecked
            {
                int hash = 17;
                foreach (var renderer in actor.GetComponentsInChildren<Renderer>(true))
                {
                    hash = hash * 31 + (renderer.gameObject.activeSelf ? 1 : 0);
                    foreach (var material in renderer.sharedMaterials) hash = hash * 31 + (material != null ? material.GetInstanceID() : 0);
                }
                return hash;
            }
        }

        private void FrameBust()
        {
            Bounds bounds = new Bounds();
            bool found = false;
            foreach (var renderer in model.GetComponentsInChildren<Renderer>())
            {
                if (!renderer.enabled) continue;
                if (!found) { bounds = renderer.bounds; found = true; } else bounds.Encapsulate(renderer.bounds);
            }
            float height = found ? Mathf.Max(.1f, bounds.size.y) : 1;
            Vector3 center = found ? bounds.center : model.transform.position + Vector3.up * .7f;
            float top = found ? bounds.max.y : center.y + height * .5f;
            // Top margin 7%, lower edge at the upper chest. Reframe per model, not per frame.
            float bottom = head != null ? head.position.y - height * .24f : top - height * .46f;
            float halfHeight = Mathf.Max(.05f, (top - bottom) * .57f);
            if (head != null) { center.x = head.position.x; center.z = head.position.z; }
            portraitCamera.aspect = portraitCamera.targetTexture.width / (float)portraitCamera.targetTexture.height;
            // Combined animal meshes need their ears/horns measured, not just a head bone point.
            float left = center.x, right = center.x, headTop = float.MinValue, headBottom = float.MaxValue;
            foreach (var renderer in model.GetComponentsInChildren<Renderer>())
            {
                if (!renderer.enabled) continue;
                Mesh mesh = null;
                bool baked = renderer is SkinnedMeshRenderer;
                if (renderer is SkinnedMeshRenderer skin) { mesh = new Mesh(); skin.BakeMesh(mesh); }
                else if (renderer.TryGetComponent<MeshFilter>(out var filter)) mesh = filter.sharedMesh;
                if (mesh != null && mesh.isReadable)
                {
                    var vertices = mesh.vertices;
                    var skinned = renderer as SkinnedMeshRenderer;
                    var weights = skinned != null && skinned.sharedMesh.isReadable ? skinned.sharedMesh.boneWeights : null;
                    var bones = skinned != null ? skinned.bones : null;
                    for (int i = 0; i < vertices.Length; i++)
                    {
                        var point = renderer.transform.TransformPoint(vertices[i]);
                        if (point.y < bottom) continue;
                        bool headVertex = head == null || renderer.transform.IsChildOf(head);
                        if (weights != null && weights.Length == vertices.Length)
                        {
                            var weight = weights[i];
                            headVertex |= HeadWeight(bones, weight.boneIndex0, weight.weight0) || HeadWeight(bones, weight.boneIndex1, weight.weight1) ||
                                HeadWeight(bones, weight.boneIndex2, weight.weight2) || HeadWeight(bones, weight.boneIndex3, weight.weight3);
                        }
                        else if (skinned != null && renderer.name.ToLowerInvariant().Contains("head")) headVertex = true;
                        if (!headVertex) continue;
                        left = Mathf.Min(left, point.x); right = Mathf.Max(right, point.x);
                        headTop = Mathf.Max(headTop, point.y); headBottom = Mathf.Min(headBottom, point.y);
                    }
                }
                if (baked && mesh != null) Release(mesh);
            }
            if (headTop > headBottom)
            {
                top = headTop;
                bottom = headBottom - height * .16f;
                halfHeight = Mathf.Max(.05f, (top - bottom) * .57f);
            }
            halfHeight = Mathf.Max(halfHeight, (right - left) * .56f / portraitCamera.aspect);
            center.x = (left + right) * .5f;
            center.y = (top + bottom) * .5f;
            portraitCamera.orthographicSize = halfHeight;
            portraitCamera.transform.SetPositionAndRotation(center + Vector3.forward * 4, Quaternion.Euler(0, 180, 0));
        }

        private bool HeadWeight(Transform[] bones, int index, float weight)
        {
            return head != null && weight > .25f && index >= 0 && index < bones.Length &&
                bones[index] != null && (bones[index] == head || bones[index].IsChildOf(head));
        }

        public void SampleIdle(float seconds)
        {
            if (model == null) return;
            // Some clips animate rotation only. Reset additives even if a clip exists.
            if (torso != null) { torso.localPosition = torsoPosition; torso.localScale = torsoScale; }
            if (head != null) head.localRotation = headRotation;
            if (idle != null) idle.SampleAnimation(model, Mathf.Repeat(seconds, Mathf.Max(.01f, idle.length)));
            float breath = Mathf.Sin(seconds * 1.65f);
            if (torso != null)
            {
                if (idle == null) { torso.localPosition = torsoPosition; torso.localScale = torsoScale; }
                torso.localPosition += Vector3.up * (.0025f * breath);
                torso.localScale = Vector3.Scale(torso.localScale, new Vector3(1 + .006f * breath, 1 + .008f * breath, 1 + .01f * breath));
            }
            if (head != null)
            {
                if (idle == null) head.localRotation = headRotation;
                head.localRotation *= Quaternion.Euler(Mathf.Sin(seconds * .73f) * 1.1f, Mathf.Sin(seconds * .47f) * 2.2f, Mathf.Sin(seconds * .61f) * .6f);
            }
        }

        private void LateUpdate() { SampleIdle(Time.unscaledTime); }
        private void ClearModel()
        {
            if (model != null) { model.SetActive(false); Release(model); }
            foreach (var material in ownedMaterials) Release(material);
            foreach (var mesh in ownedMeshes) Release(mesh);
            ownedMaterials.Clear(); ownedMeshes.Clear();
            model = null; head = torso = null; idle = null;
        }
        private void OnDestroy() { ClearModel(); }
        private static void Release(Object value) { if (Application.isPlaying) Destroy(value); else DestroyImmediate(value); }
    }
}

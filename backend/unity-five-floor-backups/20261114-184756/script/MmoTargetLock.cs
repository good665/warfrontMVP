using UnityEngine;
namespace Warfront
{
    public sealed partial class GameBootstrap
    {
        // Retain lifecycle/input helpers without a lock-on state or acquisition path.
        private void ClearMmoTarget() { }
        private Vector2 MmoTargetAim(Vector2 freeAim) => StrategicViewActive?StrategicAim(freeAim):freeAim;
    }
}

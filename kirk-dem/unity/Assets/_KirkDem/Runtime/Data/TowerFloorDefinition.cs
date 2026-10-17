using KirkDem.Core;
using UnityEngine;

namespace KirkDem.Data
{
    [CreateAssetMenu(menuName = "Kirk Dem/Tower Floor", fileName = "Floor_")]
    public sealed class TowerFloorDefinition : ScriptableObject
    {
        public RingId ring;
        public int capacity;
        public string socketTransform;
        public GameObject gearPrefab;
        public float baseHz;

        void OnValidate()
        {
            if (ring != RingId.None && capacity != RingCatalog.RoomCount(ring))
                Debug.LogWarning($"{name}: kapasite {RingCatalog.RoomCount(ring)} olmalı.", this);
        }
    }
}

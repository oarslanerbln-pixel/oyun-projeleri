using KirkDem.Core;
using UnityEngine;

namespace KirkDem.Data
{
    [CreateAssetMenu(menuName = "Kirk Dem/Ring", fileName = "Ring_")]
    public sealed class RingDefinition : ScriptableObject
    {
        public string id;                 // toprak … an
        public RingId ring;
        public int roomCount;             // RingCatalog ile çapraz doğrulanır
        public TimeRuleKind timeRuleKind; // yalnız gösterim; kural Core'da
        public GuardianKind guardianKind;
        public Color accentColor;
        public AudioRingProfile audioProfile;
        public RoomDefinition[] rooms;
        public SecretDefinition secret;
        public float cameraStepIn;        // sanat kitabından
        public string sceneName;          // Magara_Halka{n}

        void OnValidate()
        {
            if (ring != RingId.None && roomCount != RingCatalog.RoomCount(ring))
                Debug.LogWarning($"{name}: {ring} için oda sayısı {RingCatalog.RoomCount(ring)} olmalı.", this);
            if (ring != RingId.None && id != RingCatalog.Id(ring))
                Debug.LogWarning($"{name}: id '{RingCatalog.Id(ring)}' olmalı.", this);
        }
    }
}

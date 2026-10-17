using KirkDem.Core;
using UnityEngine;

namespace KirkDem.Data
{
    [CreateAssetMenu(menuName = "Kirk Dem/Secret", fileName = "S")]
    public sealed class SecretDefinition : ScriptableObject
    {
        public string id;               // S1 … S7
        public RingId ring;
        public string ownerId;          // kasabalı id
        public string textKey;          // "secret.S3.text" — tek cümle, gösterilir, silinir
        public string resolvesTroubleId;
        public float displaySeconds = 6f;

        void OnValidate()
        {
            if (ring != RingId.None && id != RingCatalog.SecretId(ring))
                Debug.LogWarning($"{name}: id '{RingCatalog.SecretId(ring)}' olmalı.", this);
        }
    }
}

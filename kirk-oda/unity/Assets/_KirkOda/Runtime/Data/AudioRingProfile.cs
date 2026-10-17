using KirkOda.Core;
using UnityEngine;

namespace KirkOda.Data
{
    [CreateAssetMenu(menuName = "Kirk Oda/Audio Ring Profile", fileName = "Audio_")]
    public sealed class AudioRingProfile : ScriptableObject
    {
        public RingId ring;
        public float baseHz;            // halkanın temel notası (ses-mimarisi §1)
        public float[] arpeggioHz;      // oda sayısı kadar adım
        public TimbreDef timbre;
        public bool silent;             // yalnız Sessizlik: true

        void OnValidate()
        {
            if (ring == RingId.Sessizlik && !silent)
                Debug.LogWarning($"{name}: Sessizlik halkası silent olmalı.", this);
        }
    }
}

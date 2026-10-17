using KirkOda.Core;
using UnityEngine;
using UnityEngine.Rendering;

namespace KirkOda.Data
{
    [CreateAssetMenu(menuName = "Kirk Oda/Era", fileName = "Era_")]
    public sealed class EraDefinition : ScriptableObject
    {
        public string id;                  // bugun, bir-yil, kirk-yil, terk
        public EraId era;
        public float colorTemperature;     // sanat kitabı: nötr, solgun, gri-mavi
        public VolumeProfile lightingProfile;
        public SeasonVariant[] seasonVariants; // yalnız bir-yil
        public TownStateOverride[] townStateOverrides;
        public string videoOnEnter;        // "bir-yil", "kirk-yil" ya da boş
    }
}

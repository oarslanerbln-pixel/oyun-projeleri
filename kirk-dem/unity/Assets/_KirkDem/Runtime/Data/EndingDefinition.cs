using KirkDem.Core;
using UnityEngine;

namespace KirkDem.Data
{
    [CreateAssetMenu(menuName = "Kirk Dem/Ending", fileName = "Ending_")]
    public sealed class EndingDefinition : ScriptableObject
    {
        public string id;              // donus, kalis, dagitis
        public EndingId ending;
        public StoneGesture gesture;   // Lift, Hold, Bury
        public string videoId;         // son-{id}
        public EraId finalEra;         // Dönüş/Dağıtış: Terk; Kalış: KirkYil
        public TownStateOverride[] finalTownState;
    }
}

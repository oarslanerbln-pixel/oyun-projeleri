using UnityEngine;

namespace KirkOda.Data
{
    [CreateAssetMenu(menuName = "Kirk Oda/Guardian", fileName = "G-R")]
    public sealed class GuardianDefinition : ScriptableObject
    {
        public string id;              // G-R{n}-{nn}
        public GuardianKind kind;
        public WantKind wantsKind;
        public string wantedItemId;    // yalnız Item: kasabadan getirilir
        public GameObject prefab;
        public string voiceOwnerId;    // Gölge'deki yaşlı saatçi ve baba aynı oyuncu (iç not)
    }
}

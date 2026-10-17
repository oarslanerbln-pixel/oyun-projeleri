using UnityEngine;

namespace KirkDem.Data
{
    [CreateAssetMenu(menuName = "Kirk Dem/Townsperson", fileName = "NPC_")]
    public sealed class TownspersonDefinition : ScriptableObject
    {
        public static readonly string[] Ids =
            { "degirmenci", "degirmenci-kizi", "kahveci", "imam", "ebe", "coban", "muhtar" };

        public string id;
        public string troubleId;         // imam için boş
        public EraVariant[] eras = new EraVariant[4];
        public EraVariant resolvedVariant;
        public string voiceOwnerId;

        void OnValidate()
        {
            if (System.Array.IndexOf(Ids, id) < 0)
                Debug.LogWarning($"{name}: '{id}' yedi kasabalıdan biri değil.", this);
        }
    }
}

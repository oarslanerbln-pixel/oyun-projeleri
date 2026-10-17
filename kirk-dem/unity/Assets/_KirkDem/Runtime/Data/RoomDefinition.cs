using KirkDem.Core;
using UnityEngine;

namespace KirkDem.Data
{
    [CreateAssetMenu(menuName = "Kirk Dem/Room", fileName = "Room_R")]
    public sealed class RoomDefinition : ScriptableObject
    {
        public string id;                    // R{n}-{nn}
        public RingId ring;
        public int index;                    // 1..roomCount
        public GuardianDefinition guardian;
        [TextArea] public string oneLinerKey; // senaryo kilidindeki tek cümle (tasarım notu)
        public GameObject dioramaBase;
        public DioramaVariable dioramaVariable;
        public GameObject[] modules;
        public AudioEmitterDef[] emitters;
        public HalKind halKind;
        public bool dogGuides = true;
        public float breathSeconds;          // yalnız Nefes
        public RecordEditDef[] recordEdits;  // yalnız Ayna
        public CameraRigDef cameraRig;
        public int estimatedMinutes = 3;

        void OnValidate()
        {
            if (!RingCatalog.TryParseRoomId(id, out var r, out var i) || r != ring || i != index)
                Debug.LogWarning($"{name}: id '{id}' ring/index ile uyuşmuyor (beklenen {(ring == RingId.None ? "?" : RingCatalog.RoomId(ring, Mathf.Max(1, index)))}).", this);
        }
    }
}

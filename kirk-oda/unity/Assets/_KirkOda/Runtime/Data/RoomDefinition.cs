using KirkOda.Core;
using UnityEngine;

namespace KirkOda.Data
{
    [CreateAssetMenu(menuName = "Kirk Oda/Room", fileName = "Room_R")]
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

        [Header("Köpek ipucu ve kilometre taşı (sistemler.md §10, karar K-13)")]
        [Tooltip("2–3 kademe: bak, yanına otur, burnunu yönelt. Cevap değil yön verir. Sessizlik'te boş.")]
        public HintStepDef[] hintSteps;
        public float hintDelaySeconds = HintTimer.DefaultDelaySeconds;
        [Tooltip("Oda içi geri alınamaz adım sayısı. Sessiz kontrol noktası ve ipucu zamanlayıcısı bunu okur.")]
        public int milestoneCount = 2;

        void OnValidate()
        {
            int hints = hintSteps == null ? 0 : hintSteps.Length;
            if (ring == RingId.Sessizlik && hints > 0)
                Debug.LogWarning($"{name}: Sessizlik'te köpek ipucu yok; hintSteps boş olmalı.", this);
            else if (ring != RingId.Sessizlik && ring != RingId.An && (hints < 2 || hints > 3))
                Debug.LogWarning($"{name}: köpek ipucu 2–3 kademe olmalı (şu an {hints}).", this);

            if (!RingCatalog.TryParseRoomId(id, out var r, out var i) || r != ring || i != index)
                Debug.LogWarning($"{name}: id '{id}' ring/index ile uyuşmuyor (beklenen {(ring == RingId.None ? "?" : RingCatalog.RoomId(ring, Mathf.Max(1, index)))}).", this);
        }
    }
}

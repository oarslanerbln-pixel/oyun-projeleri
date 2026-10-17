using System;
using KirkDem.Core;
using UnityEngine;

namespace KirkDem.Data
{
    // Tüm metin alanları Unity Localization anahtarıdır (string). Paket bağımlılığını iskelette tutmamak için
    // LocalizedString yerine anahtar kullanılır; dikey dilimde LocalizedString'e geçilebilir.

    public enum GuardianKind { Animal, Child, Elder, Self, Reflection, None }
    public enum WantKind { Item, Habit, Anger, Fear, Memory, Name, Silence, Nothing }
    public enum DioramaVariableKind { Material, Fill, Position, Count, Season, State }

    [Serializable]
    public sealed class AudioEmitterDef
    {
        public string localName = "Emitter_";       // odadaki Emitter_* nesnesi
        public AudioClip clip;
        [Range(-1f, 1f)] public float pitch;       // PitchMap ile çizgi titreşimi
        [Range(0f, 1f)] public float intensity = 1f; // çizgi kalınlığı
        public bool isReversed;                     // Ayna
        public string subtitleKey;                  // "room.R2-05.subtitle.drip"
    }

    [Serializable]
    public sealed class DioramaVariable
    {
        public DioramaVariableKind kind;
        public string target;   // diorama içindeki alt nesne adı
        public string value;    // "0.7", "Kis", "Kuru"
    }

    [Serializable]
    public sealed class CameraRigDef
    {
        public Vector3 position;
        public Vector3 lookAt;
        public float focalLengthMm = 35f;
    }

    /// <summary>Köpeğin ipucu kademesi. Hiçbiri cevabı vermez, yalnız yönü.</summary>
    public enum HintCue { LookAt, SitBeside, PointNose }

    [Serializable]
    public sealed class HintStepDef
    {
        public HintCue cue;
        public string targetId;   // RoomRoot altındaki nesnenin kimliği
    }

    [Serializable]
    public sealed class RecordEditDef
    {
        public string recordId;   // kasaba kaydı: mezar taşı, fotoğraf, kitabe
        public string newState;
    }

    [Serializable]
    public sealed class EraVariant
    {
        public EraId era;
        public bool present = true;      // ölü/yok ise false
        public GameObject prefab;
        public string spawnPoint;
        public string dialogueTable;
        public string graveRecordId;     // present=false ise mezar taşı
    }

    [Serializable]
    public sealed class TimbreDef
    {
        [Tooltip("Harmonik ağırlıkları; index 0 = temel")]
        public float[] harmonics = { 1f, 0.5f, 0.25f };
        public float attackSeconds = 0.05f;
        public float releaseSeconds = 1.5f;
    }

    [Serializable]
    public sealed class SeasonVariant
    {
        public int seasonIndex;
        public Material[] overrides;
    }

    [Serializable]
    public sealed class TownStateOverride
    {
        public string recordId;
        public string state;
    }
}

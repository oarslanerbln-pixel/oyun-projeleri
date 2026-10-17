using KirkDem.Core;
using UnityEngine;

namespace KirkDem.Gameplay
{
    /// <summary>Boot sahnesinde tek örnek. Core GameState'i tutar; kural kararı vermez.</summary>
    public sealed class GameRoot : MonoBehaviour
    {
        public static GameRoot Instance { get; private set; }

        [SerializeField, Tooltip("Babanın adının harf sayısı (senaryo kilidinden).")]
        int inscriptionLetters = 6; // DURSUN — senaryo kilidi, diyalog-ilkeleri.md

        public GameState State { get; private set; }

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            DontDestroyOnLoad(gameObject);
            State = new GameState(inscriptionLetters);
            // TODO: SaveSystem.TryLoad(State) — tek slot, kasabada başlar (ADR-0006)
        }

        /// <summary>Kasabadaki her eylemden sonra çağrılır (ADR-0005: eylem = kayıt).</summary>
        public void SaveNow()
        {
            // TODO: SaveSystem.Write(State) — JSON + .bak
        }
    }
}

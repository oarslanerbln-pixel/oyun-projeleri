using KirkDem.Core;
using UnityEngine;

namespace KirkDem.Gameplay
{
    /// <summary>
    /// Tek "yetenek": dinle tuşu basılıyken saatçi kıpırdayamaz; ses kaynakları ışık çizgisi olur.
    /// Karar TimeRule'dan; bu sınıf yalnız girdi → Core → Presentation köprüsüdür.
    /// </summary>
    public sealed class ListeningController : MonoBehaviour
    {
        [SerializeField] float minimumHoldSeconds = 0.2f; // erişilebilirlik: ayarlanabilir

        public bool IsListening { get; private set; }
        public BreathState Breath { get; set; } = BreathState.Releasing; // Nefes halkasında BreathController yazar
        public bool InLight { get; set; } = true;                        // Gölge halkasında LightMask yazar

        float _held;

        /// <summary>Girdi katmanı her kare çağırır (Input System ya da legacy; iskelette soyut).</summary>
        public void SetListenHeld(bool held)
        {
            var rule = TimeRuleTable.For(GameRoot.Instance.State.CurrentRing);
            var ctx = new ListenContext(Breath, InLight);

            if (!held) { _held = 0f; SetListening(false, rule); return; }

            _held += Time.deltaTime;
            if (_held < minimumHoldSeconds) return;

            // Sessizlik'te CanListen false ama hareket kilidi yine uygulanır: saatçi dinler, hiçbir şey duymaz.
            SetListening(true, rule);
        }

        void SetListening(bool on, TimeRule rule)
        {
            if (IsListening == on) return;
            IsListening = on;
            bool hears = on && rule.CanListen(new ListenContext(Breath, InLight));
            // TODO: SoundLineRenderer.SetActive(hears) — emitter listesi RoomRoot'tan; Ayna'da ters yön
            // TODO: PlayerMotor.Lock(on) — dinlerken kıpırdanmaz
            // TODO: Sessizlik: hears=false iken DogCompanion.ShowDirectionCue()
        }
    }
}

using System;

namespace KirkDem.Core
{
    /// <summary>
    /// Kasabada zaman tek yönlü ve eylemle ölçülür (ADR-0005). Dört çağ aynı haritanın dört hali.
    /// Çağ geçişi yalnız halka çıkışında; kırk yıl yalnız Sessizlik ilk odasının hamlesiyle.
    /// Sessizlik'ten iki kez çıkılır: ilk odadan sonra (KirkYil) ve dördüncü odadan sonra (Terk).
    /// </summary>
    public sealed class TownClock
    {
        public EraId Era { get; private set; } = EraId.Bugun;
        public int Vakit { get; private set; }            // her eylem +1; güneş saati gölgesi bunu gösterir
        public int SeasonIndex { get; private set; }      // 0..3; yalnız BirYil içinde anlamlı (Gölge çıkışı)
        public bool FortyYearLeapApplied { get; private set; }
        public int SilenceExits { get; private set; }     // 0, 1 (kırk yıl), 2 (terk)

        public event Action<EraId> EraChanged;
        public event Action<int> VakitAdvanced;

        /// <summary>Konuşma, sır söyleme, dem takma. Dolaşmak değil.</summary>
        public void AdvanceVakit()
        {
            Vakit++;
            VakitAdvanced?.Invoke(Vakit);
        }

        /// <summary>Çağ yalnız ileri gider; geri istek yok sayılır.</summary>
        public bool TrySetEra(EraId era)
        {
            if (era <= Era) return false;
            Era = era;
            EraChanged?.Invoke(era);
            return true;
        }

        /// <summary>Sessizlik ilk odasının tek hamlesi. Yalnız bir kez işler.</summary>
        public bool ApplyFortyYearLeap()
        {
            if (FortyYearLeapApplied) return false;
            FortyYearLeapApplied = true;
            TrySetEra(EraId.KirkYil);
            return true;
        }

        /// <summary>Halka çıkışı: kasaba en az TimeRule.EraAfterExit çağında bulunur.</summary>
        public void OnRingExit(RingId ring)
        {
            if (ring == RingId.None || ring == RingId.An) return; // Ân'dan kasabaya "çıkış" yok; sonu ending belirler
            var rule = TimeRuleTable.For(ring);
            if (ring == RingId.Golge) SeasonIndex = (SeasonIndex + 1) % 4; // mevsimler geçer, çağ değişmez
            if (ring == RingId.Sessizlik)
            {
                SilenceExits++;
                TrySetEra(SilenceExits >= 2 ? EraId.Terk : EraId.KirkYil); // 7. dönüş: kasaba terk edilmiş
                return;
            }
            TrySetEra(rule.EraAfterExit);
        }

        public void Restore(EraId era, int vakit, int seasonIndex, bool leapApplied, int silenceExits = 0)
        {
            Era = era; Vakit = vakit; SeasonIndex = seasonIndex; FortyYearLeapApplied = leapApplied; SilenceExits = silenceExits;
        }
    }
}

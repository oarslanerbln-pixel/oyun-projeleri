using System;

namespace KirkOda.Core
{
    /// <summary>
    /// Taşın perdesi: saklanan − söylenen, sayılan sır sayısına (6) bölünmüş (−1..+1). S7 sayılmaz.
    /// Ölçek ahlaki değil müzikaldir.
    /// Audio, Haptics ve Presentation aynı NormalizedPitch değerini PitchMap üzerinden okur.
    /// </summary>
    public sealed class StoneState
    {
        public int RawPitch { get; private set; }          // −6..+6
        public float NormalizedPitch { get; private set; } // −1..+1
        public bool IsSwinging { get; set; }               // sallanmazken ses vermez

        public event Action<float> PitchChanged;

        public void Recalculate(int keptCount, int toldCount)
        {
            int raw = keptCount - toldCount;
            const int n = SecretLedger.CountedSecrets;
            if (keptCount < 0 || toldCount < 0 || keptCount + toldCount > n)
                throw new ArgumentOutOfRangeException(nameof(keptCount), "kept + told sayılan sır sayısını (6) aşamaz.");
            RawPitch = raw;
            float normalized = raw / (float)n;
            if (Math.Abs(normalized - NormalizedPitch) > 1e-6f)
            {
                NormalizedPitch = normalized;
                PitchChanged?.Invoke(normalized);
            }
        }

        public void Recalculate(SecretLedger ledger) => Recalculate(ledger.KeptCount, ledger.ToldCount);
    }

    /// <summary>Tek kaynak, üç kanal (ADR-0007). Tablolar burada, başka yerde değil.</summary>
    public static class PitchMap
    {
        public const float BaseHz = 220f;

        /// <summary>220 Hz merkez, oktav başına ×2: −1 → 110 Hz, +1 → 440 Hz.</summary>
        public static float Frequency(float normalizedPitch) => BaseHz * (float)Math.Pow(2.0, normalizedPitch);

        /// <summary>Gamepad titreşim darbesi/sn: 1 … 8 (üstel).</summary>
        public static float HapticRate(float normalizedPitch) => (float)Math.Pow(8.0, (normalizedPitch + 1f) * 0.5f);

        /// <summary>Taş yüzeyi dalga sıklığı, çizgi/cm: 0.5 … 6.</summary>
        public static float RippleDensity(float normalizedPitch) => 0.5f * (float)Math.Pow(12.0, (normalizedPitch + 1f) * 0.5f);
    }
}

using System;

namespace KirkOda.Core
{
    /// <summary>
    /// Köpeğin ipucu zamanlayıcısı (sistemler.md §10, analiz O1). Oyuncu bir süre kilometre taşı ilerletmezse
    /// köpek bir kademe daha belirgin yön gösterir. Hiçbir kademe cevabı vermez, yalnız yönü.
    /// Köpeğin yol göstermediği odalarda yalnız son kademe çalışır ve gecikme iki katıdır.
    /// Sessizlik'te kapalıdır.
    /// </summary>
    public sealed class HintTimer
    {
        public const float DefaultDelaySeconds = 150f;
        public const float MinDelaySeconds = 60f;
        public const float MaxDelaySeconds = 300f;

        public int MaxLevel { get; }
        public bool DogGuides { get; }
        public bool Enabled { get; set; } = true;
        public float DelaySeconds { get; private set; }
        public int Level { get; private set; }

        float _idle;

        public event Action<int> LevelChanged;

        public HintTimer(int maxLevel, bool dogGuides, float delaySeconds = DefaultDelaySeconds)
        {
            if (maxLevel < 1) throw new ArgumentOutOfRangeException(nameof(maxLevel));
            MaxLevel = maxLevel;
            DogGuides = dogGuides;
            SetDelay(delaySeconds);
        }

        /// <summary>Erişilebilirlik ayarı: 60–300 sn arası.</summary>
        public void SetDelay(float seconds)
        {
            DelaySeconds = seconds < MinDelaySeconds ? MinDelaySeconds : (seconds > MaxDelaySeconds ? MaxDelaySeconds : seconds);
        }

        float EffectiveDelay => DogGuides ? DelaySeconds : DelaySeconds * 2f;

        public int Tick(float dt)
        {
            if (dt < 0f) throw new ArgumentOutOfRangeException(nameof(dt));
            if (!Enabled || Level >= MaxLevel) return Level;
            _idle += dt;
            while (_idle >= EffectiveDelay && Level < MaxLevel)
            {
                _idle -= EffectiveDelay;
                Level = DogGuides ? Level + 1 : MaxLevel;
                LevelChanged?.Invoke(Level);
            }
            return Level;
        }

        /// <summary>Oyuncu ilerledi: sayaç ve kademe sıfırlanır.</summary>
        public void OnMilestone()
        {
            _idle = 0f;
            if (Level != 0)
            {
                Level = 0;
                LevelChanged?.Invoke(0);
            }
        }
    }
}

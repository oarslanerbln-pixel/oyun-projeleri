namespace KirkDem.Core
{
    public enum BreathState { Holding, Releasing }

    /// <summary>Dinleme izni için bağlam. Gameplay doldurur, TimeRule karar verir.</summary>
    public readonly struct ListenContext
    {
        public readonly BreathState Breath;
        public readonly bool InLight; // Gölge: fenerin aydınlattığı yerde mi

        public ListenContext(BreathState breath, bool inLight)
        {
            Breath = breath; InLight = inLight;
        }
    }

    /// <summary>Bir halkanın zaman kuralı. Salt okunur; tablo TimeRuleTable'da.</summary>
    public readonly struct TimeRule
    {
        public readonly RingId Ring;
        public readonly TimeRuleKind Kind;
        public readonly bool AllowsRewind;    // Su (gelgit), Gölge (gölge katmanı)
        public readonly bool IsSilent;        // Sessizlik: hiçbir şey duyulmaz
        public readonly bool AllowsMovement;  // Ân: hayır
        public readonly EraId EraAfterExit;   // halka çıkışında kasabanın en az hangi çağda olacağı

        public TimeRule(RingId ring, TimeRuleKind kind, bool allowsRewind, bool isSilent, bool allowsMovement, EraId eraAfterExit)
        {
            Ring = ring; Kind = kind; AllowsRewind = allowsRewind; IsSilent = isSilent;
            AllowsMovement = allowsMovement; EraAfterExit = eraAfterExit;
        }

        public bool CanListen(ListenContext ctx)
        {
            switch (Kind)
            {
                case TimeRuleKind.OneWay: return false;                                   // kasabada konuşulur, dinlenmez
                case TimeRuleKind.BreathHeld: return ctx.Breath == BreathState.Holding;
                case TimeRuleKind.SingleMove: return false;                               // Sessizlik
                case TimeRuleKind.Timeless: return false;                                 // Ân
                default: return true;
            }
        }

        public bool CanMove(ListenContext ctx, bool isListening)
        {
            if (!AllowsMovement) return false;          // Ân
            if (isListening) return false;              // dinlerken kıpırdanmaz
            if (Kind == TimeRuleKind.BreathHeld) return ctx.Breath == BreathState.Holding;
            return true;
        }

        /// <summary>Gölge: ışıkta zaman ileri (+1), gölgede geri (−1). Diğer halkalarda hep ileri.</summary>
        public int FlowDirection(ListenContext ctx)
        {
            if (Kind == TimeRuleKind.DualFlow) return ctx.InLight ? 1 : -1;
            return 1;
        }
    }

    public static class TimeRuleTable
    {
        static readonly TimeRule[] Rules =
        {
            new TimeRule(RingId.None,      TimeRuleKind.OneWay,     false, false, true,  EraId.Bugun),
            new TimeRule(RingId.Toprak,    TimeRuleKind.FoldedSlow, false, false, true,  EraId.Bugun),
            new TimeRule(RingId.Su,        TimeRuleKind.Tidal,      true,  false, true,  EraId.BirYil),
            new TimeRule(RingId.Nefes,     TimeRuleKind.BreathHeld, false, false, true,  EraId.BirYil),
            new TimeRule(RingId.Golge,     TimeRuleKind.DualFlow,   true,  false, true,  EraId.BirYil),
            new TimeRule(RingId.Ayna,      TimeRuleKind.RecordEdit, false, false, true,  EraId.BirYil),
            new TimeRule(RingId.Sessizlik, TimeRuleKind.SingleMove, false, true,  true,  EraId.KirkYil),
            new TimeRule(RingId.An,        TimeRuleKind.Timeless,   false, false, false, EraId.KirkYil), // sonu ending belirler
        };

        public static TimeRule For(RingId ring) => Rules[(int)ring];
    }
}

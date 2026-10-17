using System;

namespace KirkOda.Core
{
    /// <summary>
    /// Yedi sır, her halkadan bir. Tek cümle gösterilir, silinir. Söylenir ya da saklanır; ortası yok.
    /// Saklama, bir sonraki halkaya inişle kesinleşir (FinalizeOnDescent).
    /// S7 (Ân, imam) söylenemez ve sayılmaz: "çoğu" altı sır üzerinden hesaplanır (senaryo kilidi).
    /// </summary>
    public sealed class SecretLedger
    {
        readonly SecretChoice[] _choices = new SecretChoice[RingCatalog.SecretCount + 1]; // index = ring
        readonly bool[] _revealed = new bool[RingCatalog.SecretCount + 1];

        public event Action<RingId, SecretChoice> Decided;

        public SecretChoice Choice(RingId ring) => _choices[Index(ring)];
        public bool IsRevealed(RingId ring) => _revealed[Index(ring)];

        /// <summary>Sayıma giren sırlar: S1..S6. S7 (Ân) gösterilir ama sayılmaz.</summary>
        public const int CountedSecrets = 6;

        public int ToldCount { get { int n = 0; for (int i = 1; i <= CountedSecrets; i++) if (_choices[i] == SecretChoice.Told) n++; return n; } }
        public int KeptCount { get { int n = 0; for (int i = 1; i <= CountedSecrets; i++) if (_choices[i] == SecretChoice.Kept) n++; return n; } }

        /// <summary>Halka çıkışında cümle gösterildi. Durum Undecided kalır.</summary>
        public void Reveal(RingId ring) => _revealed[Index(ring)] = true;

        /// <summary>Kasabada sahibine söylendi. Yalnız revealed ve Undecided iken.</summary>
        public bool Tell(RingId ring)
        {
            int i = Index(ring);
            if (!_revealed[i] || _choices[i] != SecretChoice.Undecided) return false;
            _choices[i] = SecretChoice.Told;
            Decided?.Invoke(ring, SecretChoice.Told);
            return true;
        }

        public bool Keep(RingId ring)
        {
            int i = Index(ring);
            if (!_revealed[i] || _choices[i] != SecretChoice.Undecided) return false;
            _choices[i] = SecretChoice.Kept;
            Decided?.Invoke(ring, SecretChoice.Kept);
            return true;
        }

        /// <summary>İniş anı: gösterilmiş ama söylenmemiş her sır (S1..S6) saklanmış sayılır.</summary>
        public void FinalizeOnDescent()
        {
            for (int i = 1; i <= CountedSecrets; i++)
                if (_revealed[i] && _choices[i] == SecretChoice.Undecided) Keep((RingId)i);
        }

        // Kayıt için düz erişim.
        public void Restore(RingId ring, bool revealed, SecretChoice choice)
        {
            int i = Index(ring); _revealed[i] = revealed; _choices[i] = choice;
        }

        static int Index(RingId ring)
        {
            int i = (int)ring;
            if (i < 1 || i > RingCatalog.SecretCount) throw new ArgumentOutOfRangeException(nameof(ring));
            return i;
        }
    }
}

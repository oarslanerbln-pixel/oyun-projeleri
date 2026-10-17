using System;

namespace KirkDem.Core
{
    public sealed class TowerFloor
    {
        public RingId Ring { get; }
        public int Capacity { get; }
        public int Carried { get; private set; }    // alınmış, henüz takılmamış dem
        public int Installed { get; private set; }  // takılı dem
        public bool? IsLit { get; private set; }    // null: sır kararlaşmadı; true: saklandı (yanık); false: söylendi (karanlık)

        public float TurnRatio => Capacity == 0 ? 0f : Installed / (float)Capacity;
        public bool IsTurningFully => Installed == Capacity;

        internal TowerFloor(RingId ring) { Ring = ring; Capacity = RingCatalog.RoomCount(ring); }

        internal void AddCarried()
        {
            if (Carried + Installed >= Capacity) throw new InvalidOperationException($"{Ring}: halkada {Capacity} dem var.");
            Carried++;
        }

        internal bool Install()
        {
            if (Carried == 0) return false;
            Carried--; Installed++;
            return true;
        }

        internal void SetLit(bool lit) => IsLit = lit;
        internal void Restore(int carried, int installed, bool? isLit) { Carried = carried; Installed = installed; IsLit = isLit; }
    }

    /// <summary>Kule kitabesi: babanın adı. Ayna'da harf harf silinir; Sessizlik'te ad verilirse tamamen boşalır.</summary>
    public sealed class Inscription
    {
        public int TotalLetters { get; private set; }
        public int Remaining { get; private set; }
        public bool IsEmpty => Remaining == 0;

        public Inscription(int totalLetters)
        {
            if (totalLetters < 1) throw new ArgumentOutOfRangeException(nameof(totalLetters));
            TotalLetters = totalLetters; Remaining = totalLetters;
        }

        public bool RemoveLetter()
        {
            if (Remaining == 0) return false;
            Remaining--;
            return true;
        }

        /// <summary>Ayna'da bir değişiklik geri alındı (R5-04): bir harf geri gelir.</summary>
        public bool RestoreLetter()
        {
            if (Remaining == TotalLetters) return false;
            Remaining++;
            return true;
        }

        public void Clear() => Remaining = 0;
        public void Fill() => Remaining = TotalLetters;
        public void Restore(int remaining) => Remaining = Math.Max(0, Math.Min(TotalLetters, remaining));
    }

    /// <summary>Yedi kat, kitabe. Menü kulenin kendisidir; burada yalnız durum var.</summary>
    public sealed class TowerState
    {
        readonly TowerFloor[] _floors = new TowerFloor[RingCatalog.RingCount + 1];

        public Inscription Inscription { get; }
        public bool NameGiven { get; private set; }

        public event Action<RingId> FloorChanged;

        public TowerState(int inscriptionLetters)
        {
            for (int i = 1; i <= RingCatalog.RingCount; i++) _floors[i] = new TowerFloor((RingId)i);
            Inscription = new Inscription(inscriptionLetters);
        }

        public TowerFloor Floor(RingId ring)
        {
            if (ring == RingId.None) throw new ArgumentException(nameof(ring));
            return _floors[(int)ring];
        }

        public int TotalInstalled { get { int n = 0; for (int i = 1; i <= RingCatalog.RingCount; i++) n += _floors[i].Installed; return n; } }
        public bool IsComplete => TotalInstalled == RingCatalog.TotalRooms;

        /// <summary>Oda çözüldü, dem alındı (taşınıyor).</summary>
        public void AddDem(RingId ring) { Floor(ring).AddCarried(); FloorChanged?.Invoke(ring); }

        /// <summary>Kulede yuvaya takıldı. Yalnız kendi halkasının katına.</summary>
        public bool InstallDem(RingId ring)
        {
            bool ok = Floor(ring).Install();
            if (ok) FloorChanged?.Invoke(ring);
            return ok;
        }

        /// <summary>Sır kararı: saklandı → yanık, söylendi → karanlık.</summary>
        public void ApplySecret(RingId ring, SecretChoice choice)
        {
            if (choice == SecretChoice.Undecided) return;
            Floor(ring).SetLit(choice == SecretChoice.Kept);
            FloorChanged?.Invoke(ring);
        }

        /// <summary>Sessizlik ilk odası, ikinci geliş: ad verildi. Kitabe boş kalır, baba hiçbir çağda anılmaz.</summary>
        public void GiveName()
        {
            NameGiven = true;
            Inscription.Clear();
        }

        public void RestoreNameGiven(bool given) => NameGiven = given;
    }
}

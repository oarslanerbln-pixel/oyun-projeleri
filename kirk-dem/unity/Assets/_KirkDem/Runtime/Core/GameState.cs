namespace KirkDem.Core
{
    /// <summary>
    /// Tüm çekirdek durumun sahibi ve zincirleme etkilerin tek yeri.
    /// Unity tarafı (GameRoot) bunu tutar; kural kararı burada verilir.
    /// </summary>
    public sealed class GameState
    {
        public TownClock Clock { get; } = new TownClock();
        public SecretLedger Secrets { get; } = new SecretLedger();
        public TowerState Tower { get; }
        public StoneState Stone { get; } = new StoneState();
        public MakamTracker Makam { get; } = new MakamTracker();
        public RoomProgressLedger Rooms { get; } = new RoomProgressLedger();

        public RingId CurrentRing { get; private set; } = RingId.None;

        public GameState(int inscriptionLetters)
        {
            Tower = new TowerState(inscriptionLetters);
            Secrets.Decided += OnSecretDecided;
        }

        // --- Sır zinciri: tek yerden ---
        void OnSecretDecided(RingId ring, SecretChoice choice)
        {
            Tower.ApplySecret(ring, choice);
            Stone.Recalculate(Secrets);
        }

        /// <summary>Kasabada sahibine söylendi: kişi kurtulur (TownRecords, Gameplay), kat kararır, taş alçalır, vakit ilerler.</summary>
        public bool TellSecret(RingId ring)
        {
            if (!Secrets.Tell(ring)) return false;
            Clock.AdvanceVakit();
            return true;
        }

        /// <summary>Kulede dem takıldı: kat döner, vakit ilerler.</summary>
        public bool InstallDem(RingId ring)
        {
            if (!Tower.InstallDem(ring)) return false;
            Clock.AdvanceVakit();
            return true;
        }

        /// <summary>Kasabada konuşma: vakit ilerler.</summary>
        public void Talk() => Clock.AdvanceVakit();

        /// <summary>Kapaktan iniş: gösterilmiş ama söylenmemiş sırlar saklanmış sayılır.</summary>
        public void Descend(RingId ring)
        {
            Secrets.FinalizeOnDescent();
            CurrentRing = ring;
        }

        /// <summary>Oda çözüldü: dem alınır, uzun yolsa makam sayacı.</summary>
        public void SolveRoom(string roomId, float ringBaseHz)
        {
            var room = Rooms.Get(roomId);
            room.Solve();
            room.CollectDem();
            Tower.AddDem(room.Ring);
            if (room.TookLongPath) Makam.RegisterLongPath(ringBaseHz);
        }

        /// <summary>Halka bitti, kasabaya çıkış: sır gösterilir, çağ geçer. Ân'dan çıkış yok.</summary>
        public void ExitRing(RingId ring)
        {
            Secrets.Reveal(ring);
            Clock.OnRingExit(ring);
            CurrentRing = RingId.None;
        }

        /// <summary>Sessizlik ilk odası: tek hamle. Kırk yıl geçer; ad verildiyse kitabe boşalır.</summary>
        public void CommitSilenceFirstRoom(bool giveName)
        {
            Clock.ApplyFortyYearLeap();
            if (giveName) Tower.GiveName();
        }

        /// <summary>
        /// Kırkıncı odaya giriş. S7 imamın sırrıdır: odaya girerken gösterilir, kimseye söylenemez ve
        /// sayılmaz (senaryo kilidi, sirlar.md). Yedinci kat yalnız demle döner.
        /// </summary>
        public void EnterAn()
        {
            Secrets.FinalizeOnDescent();
            Secrets.Reveal(RingId.An);
            CurrentRing = RingId.An;
        }

        public EndingAvailability EndingsAvailable() => EndingResolver.Available(Tower, Secrets);
    }
}

namespace KirkOda.Core
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
        public RecordLedger Records { get; }

        public RingId CurrentRing { get; private set; } = RingId.None;

        public GameState(int inscriptionLetters)
        {
            Tower = new TowerState(inscriptionLetters);
            Records = new RecordLedger(Tower.Inscription);
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

        /// <summary>Kulede kor takıldı: kat döner, vakit ilerler.</summary>
        public bool InstallEmber(RingId ring)
        {
            if (!Tower.InstallEmber(ring)) return false;
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

        /// <summary>Oda çözüldü: kor alınır, uzun yolsa makam sayacı.</summary>
        public void SolveRoom(string roomId, float ringBaseHz)
        {
            var room = Rooms.Get(roomId);
            room.Solve();
            room.CollectEmber();
            Tower.AddEmber(room.Ring);
            if (room.TookLongPath) Makam.RegisterLongPath(ringBaseHz);
        }

        /// <summary>
        /// Halka bitti, kasabaya çıkış: sır gösterilir, çağ geçer. Ân'dan çıkış yok.
        /// Sessizlik'in ikinci çıkışında (terk) kitabe okunur hale gelir: ad verilmediyse dolu, verildiyse boş (karar K-16).
        /// </summary>
        public void ExitRing(RingId ring)
        {
            Secrets.Reveal(ring);
            Clock.OnRingExit(ring);
            if (ring == RingId.Sessizlik && Clock.Era == EraId.Terk && !Tower.NameGiven)
                Tower.Inscription.Fill();
            CurrentRing = RingId.None;
        }

        /// <summary>Ayna: odada bir kayıt değiştirildi. Kitabeden bir harf silinir.</summary>
        public bool EditRecord(string recordId) => Records.Apply(recordId);

        /// <summary>Ayna R5-04: bir değişiklik geri alındı. Bir harf geri gelir.</summary>
        public bool UndoRecord(string recordId) => Records.Undo(recordId);

        /// <summary>
        /// Sessizlik ilk odası, ilk geliş: kapı kapanır, kırk yıl geçer. Saatçi adı unutur; kitabe boşalır
        /// (dünya kitabı, Kırılma 2). Yalnız bir kez işler.
        /// </summary>
        public bool CommitFortyYears()
        {
            if (!Clock.ApplyFortyYearLeap()) return false;
            Tower.Inscription.Clear();
            return true;
        }

        /// <summary>Sessizlik ilk odası, ikinci geliş: ad duvara yazıldı. Yalnız kırk yıldan sonra.</summary>
        public bool GiveName()
        {
            if (!Clock.FortyYearLeapApplied || Tower.NameGiven) return false;
            Tower.GiveName();
            return true;
        }

        /// <summary>
        /// Kırkıncı odaya giriş. S7 imamın sırrıdır: odaya girerken gösterilir, kimseye söylenemez ve
        /// sayılmaz (senaryo kilidi, sirlar.md). Yedinci kat yalnız korla döner.
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

namespace KirkDem.Core
{
    public readonly struct EndingAvailability
    {
        public readonly bool Donus;
        public readonly bool Kalis;
        public readonly bool Dagitis;

        public EndingAvailability(bool donus, bool kalis, bool dagitis) { Donus = donus; Kalis = kalis; Dagitis = dagitis; }

        public bool IsOpen(EndingId ending)
        {
            switch (ending)
            {
                case EndingId.Donus: return Donus;
                case EndingId.Kalis: return Kalis;
                default: return Dagitis;
            }
        }

        public int OpenCount => (Donus ? 1 : 0) + (Kalis ? 1 : 0) + (Dagitis ? 1 : 0);
    }

    /// <summary>
    /// Kırkıncı odada taşla hangi eylemler açık. Hiçbiri "doğru" değildir; sıralama yok, öneri yok.
    /// Koşullar arayüzsüz okunur: meydandan kat ışıkları ve kitabe.
    /// </summary>
    public static class EndingResolver
    {
        public const int Majority = 4; // altı sayılan sırrın (S1..S6) çoğu; S7 sayılmaz

        public static EndingAvailability Available(bool nameGiven, int keptCount, int toldCount)
        {
            bool donus = nameGiven && keptCount >= Majority;
            bool dagitis = toldCount >= Majority;
            return new EndingAvailability(donus, kalis: true, dagitis);
        }

        public static EndingAvailability Available(TowerState tower, SecretLedger ledger)
            => Available(tower.NameGiven, ledger.KeptCount, ledger.ToldCount);

        public static EndingId ForGesture(StoneGesture gesture)
        {
            switch (gesture)
            {
                case StoneGesture.Lift: return EndingId.Donus;
                case StoneGesture.Hold: return EndingId.Kalis;
                default: return EndingId.Dagitis;
            }
        }
    }
}

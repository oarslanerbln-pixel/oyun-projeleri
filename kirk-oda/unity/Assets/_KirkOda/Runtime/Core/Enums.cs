namespace KirkOda.Core
{
    /// <summary>Yedi halka. None = kasaba/kule (yer üstü).</summary>
    public enum RingId
    {
        None = 0,
        Toprak = 1,
        Su = 2,
        Nefes = 3,
        Golge = 4,
        Ayna = 5,
        Sessizlik = 6,
        An = 7,
    }

    /// <summary>Kasabanın dört çağı. Yalnız ileri gider.</summary>
    public enum EraId
    {
        Bugun = 0,
        BirYil = 1,
        KirkYil = 2,
        Terk = 3,
    }

    public enum EndingId
    {
        Donus,
        Kalis,
        Dagitis,
    }

    /// <summary>Bir sırrın durumu. Ortası yok: Undecided yalnız geçicidir, inişle Kept olur.</summary>
    public enum SecretChoice
    {
        Undecided = 0,
        Told = 1,
        Kept = 2,
    }

    /// <summary>Halka zaman kuralları (teknik adlar; oyun içinde geçmez).</summary>
    public enum TimeRuleKind
    {
        OneWay,       // kasaba: tek yönlü, geri gelmez
        FoldedSlow,   // Toprak: içeride bir saat, dışarıda bir gün; bekleyerek çözmek
        Tidal,        // Su: ileri akar, sonra geri; yapılan geri sarılır
        BreathHeld,   // Nefes: nefes tutulunca dünya durur, saatçi hareket eder
        DualFlow,     // Gölge: ışıkta ileri, gölgede geri
        RecordEdit,   // Ayna: odada yapılan kasaba kayıtlarını değiştirir
        SingleMove,   // Sessizlik: tek hamle; ilk odada kırk yıl
        Timeless,     // Ân: tek bir an; yalnız niyet
    }

    public enum HalKind
    {
        None,
        WallPass,      // titreşen duvardan geçmek
        TimeMatch,     // oda zamanı bir kez kasabayla eşitlenir
        GuardianSeen,  // bekçi bir kez görülür
    }

    /// <summary>Nefes halkası girişi (sistemler.md §14): basılı tut ya da aç/kapa.</summary>
    public enum BreathInputMode
    {
        Hold,
        Toggle,
    }

    public enum StoneGesture
    {
        Lift,  // yukarı taşı → Dönüş
        Hold,  // taşla kal → Kalış
        Bury,  // göm → Dağıtış
    }
}

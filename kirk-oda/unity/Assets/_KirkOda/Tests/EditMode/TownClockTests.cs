using NUnit.Framework;

namespace KirkOda.Core.Tests
{
    public class TownClockTests
    {
        [Test]
        public void Vakit_YalnizEylemleIlerler()
        {
            var c = new TownClock();
            Assert.AreEqual(0, c.Vakit);
            c.AdvanceVakit(); c.AdvanceVakit();
            Assert.AreEqual(2, c.Vakit);
        }

        [Test]
        public void Cag_GeriGitmez()
        {
            var c = new TownClock();
            Assert.IsTrue(c.TrySetEra(EraId.BirYil));
            Assert.IsFalse(c.TrySetEra(EraId.Bugun));
            Assert.IsFalse(c.TrySetEra(EraId.BirYil));
            Assert.AreEqual(EraId.BirYil, c.Era);
        }

        [Test]
        public void HalkaCikislari_DunyaKitabiTablosu()
        {
            var c = new TownClock();
            c.OnRingExit(RingId.Toprak);   Assert.AreEqual(EraId.Bugun, c.Era);
            c.OnRingExit(RingId.Su);       Assert.AreEqual(EraId.BirYil, c.Era);
            c.OnRingExit(RingId.Nefes);    Assert.AreEqual(EraId.BirYil, c.Era);
            c.OnRingExit(RingId.Golge);    Assert.AreEqual(EraId.BirYil, c.Era); Assert.AreEqual(1, c.SeasonIndex);
            c.OnRingExit(RingId.Ayna);     Assert.AreEqual(EraId.BirYil, c.Era);
            c.OnRingExit(RingId.Sessizlik);Assert.AreEqual(EraId.KirkYil, c.Era);
        }

        [Test]
        public void Sessizlik_IkinciCikis_TerkEdilmisCag()
        {
            var c = new TownClock();
            c.OnRingExit(RingId.Ayna);
            c.ApplyFortyYearLeap();
            c.OnRingExit(RingId.Sessizlik);   Assert.AreEqual(EraId.KirkYil, c.Era); Assert.AreEqual(1, c.SilenceExits);
            c.OnRingExit(RingId.Sessizlik);   Assert.AreEqual(EraId.Terk, c.Era);    Assert.AreEqual(2, c.SilenceExits);
            c.OnRingExit(RingId.An);          Assert.AreEqual(EraId.Terk, c.Era);
        }

        [Test]
        public void KirkYil_TekSefer_OyuncununEliyle()
        {
            var c = new TownClock();
            c.OnRingExit(RingId.Su);
            Assert.IsTrue(c.ApplyFortyYearLeap());
            Assert.AreEqual(EraId.KirkYil, c.Era);
            Assert.IsFalse(c.ApplyFortyYearLeap());
        }

        [Test]
        public void An_CikisiCagiDegistirmez()
        {
            var c = new TownClock();
            c.OnRingExit(RingId.An);
            Assert.AreEqual(EraId.Bugun, c.Era);
        }
    }
}

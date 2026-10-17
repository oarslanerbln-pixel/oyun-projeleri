using NUnit.Framework;

namespace KirkDem.Core.Tests
{
    public class EndingResolverTests
    {
        [Test]
        public void Kalis_HerZamanAcik()
        {
            Assert.IsTrue(EndingResolver.Available(false, 0, 0).Kalis);
            Assert.IsTrue(EndingResolver.Available(true, 6, 0).Kalis);
            Assert.IsTrue(EndingResolver.Available(false, 0, 6).Kalis);
        }

        [Test]
        public void Donus_AdVerilmisVeCoguSaklanmis()
        {
            Assert.IsTrue(EndingResolver.Available(true, 4, 2).Donus);
            Assert.IsFalse(EndingResolver.Available(true, 3, 3).Donus, "altıda üç çoğunluk değil");
            Assert.IsFalse(EndingResolver.Available(false, 6, 0).Donus, "ad verilmeden Dönüş yok");
        }

        [Test]
        public void Dagitis_CoguSoylenmis()
        {
            Assert.IsTrue(EndingResolver.Available(false, 2, 4).Dagitis);
            Assert.IsFalse(EndingResolver.Available(false, 3, 3).Dagitis);
        }

        [Test]
        public void DonusVeDagitis_AyniAndaAcilamaz()
        {
            for (int kept = 0; kept <= 6; kept++)
            {
                int told = 6 - kept;
                var a = EndingResolver.Available(true, kept, told);
                Assert.IsFalse(a.Donus && a.Dagitis, $"kept={kept} told={told}");
                Assert.That(a.OpenCount, Is.InRange(1, 2));
            }
        }

        [Test]
        public void UcUc_YalnizKalis_KararK03()
        {
            var a = EndingResolver.Available(true, 3, 3);
            Assert.IsTrue(a.Kalis);
            Assert.IsFalse(a.Donus);
            Assert.IsFalse(a.Dagitis);
            Assert.AreEqual(1, a.OpenCount, "ortası yoktur: üçe üç yalnız kalmayı açar");
        }

        [Test]
        public void Jest_SonaEslenir()
        {
            Assert.AreEqual(EndingId.Donus, EndingResolver.ForGesture(StoneGesture.Lift));
            Assert.AreEqual(EndingId.Kalis, EndingResolver.ForGesture(StoneGesture.Hold));
            Assert.AreEqual(EndingId.Dagitis, EndingResolver.ForGesture(StoneGesture.Bury));
        }
    }
}

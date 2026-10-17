using NUnit.Framework;

namespace KirkOda.Core.Tests
{
    public class RecordLedgerTests
    {
        [Test]
        public void HerDegisiklik_BirHarfSiler()
        {
            var ins = new Inscription(6);
            var r = new RecordLedger(ins);
            Assert.IsTrue(r.Apply("mezar-cobanin-kuzusu"));
            Assert.IsTrue(r.Apply("kahve-fotograf-2"));
            Assert.AreEqual(4, ins.Remaining);
            Assert.IsFalse(r.Apply("kahve-fotograf-2"), "aynı kayıt iki kez değişmez");
            Assert.AreEqual(4, ins.Remaining);
        }

        [Test]
        public void GeriAlma_BirHarfGetirir_R5_04()
        {
            var ins = new Inscription(6);
            var r = new RecordLedger(ins);
            r.Apply("defter-nisan");
            Assert.IsTrue(r.Undo("defter-nisan"));
            Assert.AreEqual(6, ins.Remaining);
            Assert.IsFalse(r.IsEdited("defter-nisan"));
            Assert.IsFalse(r.Undo("defter-nisan"));
        }

        [Test]
        public void BesOda_AltiHarf_KitabeBosalmaz()
        {
            var ins = new Inscription(6);
            var r = new RecordLedger(ins);
            for (int i = 1; i <= 5; i++) r.Apply("kayit-" + i);
            Assert.AreEqual(1, ins.Remaining, "son harfi kırk yıl siler");
            Assert.IsFalse(ins.IsEmpty);
        }
    }
}

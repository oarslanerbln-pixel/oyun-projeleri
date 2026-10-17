using NUnit.Framework;

namespace KirkOda.Core.Tests
{
    public class HintTimerTests
    {
        [Test]
        public void Kademeler_GecikmeyleArtar_KilometreTasiylaSifirlanir()
        {
            var h = new HintTimer(maxLevel: 3, dogGuides: true, delaySeconds: 100f);
            Assert.AreEqual(0, h.Tick(99f));
            Assert.AreEqual(1, h.Tick(1f));
            Assert.AreEqual(2, h.Tick(100f));
            Assert.AreEqual(3, h.Tick(500f));
            h.OnMilestone();
            Assert.AreEqual(0, h.Level);
        }

        [Test]
        public void KopekYolGostermezse_YalnizSonKademe_IkiKatGecikme()
        {
            var h = new HintTimer(maxLevel: 3, dogGuides: false, delaySeconds: 100f);
            Assert.AreEqual(0, h.Tick(199f));
            Assert.AreEqual(3, h.Tick(1f));
        }

        [Test]
        public void Gecikme_Sinirlanir_VeKapaliysaCalismaz()
        {
            var h = new HintTimer(3, true, 10f);
            Assert.AreEqual(HintTimer.MinDelaySeconds, h.DelaySeconds);
            h.SetDelay(1000f);
            Assert.AreEqual(HintTimer.MaxDelaySeconds, h.DelaySeconds);
            h.Enabled = false; // Sessizlik
            Assert.AreEqual(0, h.Tick(10000f));
        }
    }
}

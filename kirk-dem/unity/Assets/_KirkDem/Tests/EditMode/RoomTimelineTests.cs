using NUnit.Framework;

namespace KirkDem.Core.Tests
{
    public class RoomTimelineTests
    {
        [Test]
        public void GeriSarma_SonrakiOlaylariSiler()
        {
            var tl = new RoomTimeline(10f);
            tl.Advance(2f, 1);
            Assert.IsTrue(tl.Record("testi-kirildi"));
            tl.Advance(3f, 1);
            Assert.AreEqual(0.5f, tl.T, 1e-5f);

            string undone = null;
            tl.EventUndone += e => undone = e.ActionId;
            tl.Advance(4f, -1);
            Assert.AreEqual(0.1f, tl.T, 1e-5f);
            Assert.AreEqual("testi-kirildi", undone);
            Assert.IsFalse(tl.Happened("testi-kirildi"), "dal kesildi");
        }

        [Test]
        public void SaatciSarilmaz_R2_03()
        {
            var tl = new RoomTimeline(10f);
            tl.Advance(5f, 1);
            tl.Record("saatci-yerinde-durdu", rewindable: false);
            tl.Record("kopek-kapiyi-itti", rewindable: true);
            tl.Advance(5f, -1);
            Assert.IsTrue(tl.Happened("saatci-yerinde-durdu"));
            Assert.IsFalse(tl.Happened("kopek-kapiyi-itti"), "R2-07: köpeğin yaptığı geri sarılır");
        }

        [Test]
        public void T_SinirlardaKalir()
        {
            var tl = new RoomTimeline(4f);
            tl.Advance(10f, 1); Assert.AreEqual(1f, tl.T);
            tl.Advance(10f, -1); Assert.AreEqual(0f, tl.T);
        }

        [Test]
        public void Gelgit_IleriSonraGeri_VeUzar_R2_05()
        {
            var tide = new Tide(forwardSeconds: 3f, backwardSeconds: 2f, growthPerCycle: 1f);
            Assert.AreEqual(1, tide.Direction);
            Assert.AreEqual(1, tide.Tick(2.9f));
            Assert.AreEqual(-1, tide.Tick(0.2f));
            tide.Tick(2f);                       // 5.1 sn: ikinci döngü
            Assert.AreEqual(1, tide.Cycle);
            Assert.AreEqual(4f, tide.ForwardSeconds, 1e-5f);
            Assert.AreEqual(1, tide.Tick(3.5f)); // 0.1 + 3.5 = 3.6 < 4: hâlâ ileri
        }

        [Test]
        public void IkiHavuz_ZitFaz_R2_06()
        {
            var a = new Tide(2f, 2f);
            var b = new Tide(2f, 2f, phaseSeconds: 2f);
            Assert.AreEqual(1, a.Direction);
            Assert.AreEqual(-1, b.Direction);
            a.Tick(2f); b.Tick(2f);
            Assert.AreEqual(-1, a.Direction);
            Assert.AreEqual(1, b.Direction);
        }
    }
}

using NUnit.Framework;

namespace KirkOda.Core.Tests
{
    public class MakamTrackerTests
    {
        [Test]
        public void UcuncuUzunYol_NotaEkler()
        {
            var m = new MakamTracker();
            Assert.IsFalse(m.RegisterLongPath(146.8f)); Assert.AreEqual(1, m.PendingCount);
            Assert.IsFalse(m.RegisterLongPath(146.8f)); Assert.AreEqual(2, m.PendingCount);
            Assert.IsTrue(m.RegisterLongPath(174.6f));  Assert.AreEqual(0, m.PendingCount);
            Assert.AreEqual(1, m.NotesHz.Count);
            Assert.AreEqual(174.6f, m.NotesHz[0], 1e-3f, "eklenen nota, üçüncü uzun yolun halkasının temel notası");
            Assert.IsTrue(m.HasMakam);
        }

        [Test]
        public void HicUzunYolYoksa_MakamYok()
        {
            var m = new MakamTracker();
            Assert.IsFalse(m.HasMakam);
            Assert.AreEqual(0, m.NotesHz.Count);
        }

        [Test]
        public void GameState_HalKullanilmazsaUzunYol()
        {
            var g = new GameState(5);
            var id = RingCatalog.RoomId(RingId.Toprak, 1);
            g.Rooms.Get(id).OfferHal();
            g.SolveRoom(id, 146.8f);
            Assert.AreEqual(1, g.Makam.TotalLongPaths);
            Assert.AreEqual(1, g.Tower.Floor(RingId.Toprak).Carried);

            var id2 = RingCatalog.RoomId(RingId.Toprak, 2);
            g.Rooms.Get(id2).OfferHal(); g.Rooms.Get(id2).UseHal();
            g.SolveRoom(id2, 146.8f);
            Assert.AreEqual(1, g.Makam.TotalLongPaths, "hâl kullanıldı: uzun yol değil");

            var id3 = RingCatalog.RoomId(RingId.Toprak, 3); // hâl sunulmadı
            g.SolveRoom(id3, 146.8f);
            Assert.AreEqual(1, g.Makam.TotalLongPaths, "kestirme yoksa vazgeçiş yok");
        }
    }
}

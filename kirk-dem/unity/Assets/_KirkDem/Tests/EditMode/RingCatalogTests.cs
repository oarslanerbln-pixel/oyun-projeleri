using NUnit.Framework;

namespace KirkDem.Core.Tests
{
    public class RingCatalogTests
    {
        [Test]
        public void KirkOda_YediHalka()
        {
            int total = 0;
            for (int r = 1; r <= RingCatalog.RingCount; r++) total += RingCatalog.RoomCount((RingId)r);
            Assert.AreEqual(40, total);
            Assert.AreEqual(9, RingCatalog.RoomCount(RingId.Toprak));
            Assert.AreEqual(1, RingCatalog.RoomCount(RingId.An));
        }

        [Test]
        public void OdaId_Bicimi()
        {
            Assert.AreEqual("R1-01", RingCatalog.RoomId(RingId.Toprak, 1));
            Assert.AreEqual("R7-01", RingCatalog.RoomId(RingId.An, 1));
            Assert.IsTrue(RingCatalog.TryParseRoomId("R3-07", out var ring, out var i));
            Assert.AreEqual(RingId.Nefes, ring); Assert.AreEqual(7, i);
            Assert.IsFalse(RingCatalog.TryParseRoomId("R3-08", out _, out _), "Nefes'te 7 oda var");
            Assert.IsFalse(RingCatalog.TryParseRoomId("R7-02", out _, out _));
        }

        [Test]
        public void Kule_KirkDemleTamamlanir()
        {
            var g = new GameState(5);
            foreach (var room in g.Rooms.All) g.SolveRoom(room.RoomId, 220f);
            for (int r = 1; r <= RingCatalog.RingCount; r++)
                while (g.InstallDem((RingId)r)) { }
            Assert.IsTrue(g.Tower.IsComplete);
            Assert.AreEqual(40, g.Clock.Vakit, "her dem takma bir vakit");
        }
    }
}

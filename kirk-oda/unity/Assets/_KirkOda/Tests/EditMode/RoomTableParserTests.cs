using System;
using System.IO;
using KirkOda.Tooling;
using NUnit.Framework;

namespace KirkOda.Core.Tests
{
    public class RoomTableParserTests
    {
        static string ReadRealTable()
        {
            // dotnet: bin/… altından; Unity: proje kökü kirk-oda/unity.
            string path = RoomTableParser.LocateTable(TestContext.CurrentContext.TestDirectory)
                          ?? RoomTableParser.LocateTable(Environment.CurrentDirectory);
            Assert.IsNotNull(path, RoomTableParser.RelativePath + " bulunamadı");
            return File.ReadAllText(path);
        }

        [Test]
        public void GercekTablo_KirkOdaKimlikSozlesmesiyleUyusur()
        {
            var rooms = RoomTableParser.Parse(ReadRealTable());
            Assert.AreEqual(RingCatalog.TotalRooms, rooms.Count);

            var first = rooms["R1-01"];
            Assert.AreEqual(RingId.Toprak, first.Ring);
            Assert.AreEqual(1, first.Number);
            Assert.AreEqual("Geyik", first.Guardian);
            Assert.AreEqual(HalKind.None, first.Hal, "öğretici odada hâl yok");
            StringAssert.StartsWith("Damlayan suyu", first.Puzzle);

            Assert.AreEqual(HalKind.WallPass, rooms["R1-02"].Hal);
            Assert.AreEqual(HalKind.TimeMatch, rooms["R1-05"].Hal);
            Assert.AreEqual(HalKind.GuardianSeen, rooms["R1-08"].Hal);
            Assert.AreEqual(40, rooms["R7-01"].Number);
        }

        [Test]
        public void GercekTablo_DikeyDilimOdalariVar()
        {
            var rooms = RoomTableParser.Parse(ReadRealTable());
            foreach (string id in new[] { "R1-01", "R1-02", "R1-03", "R2-01", "R4-02", "R5-04" })
                Assert.IsTrue(rooms.ContainsKey(id), id);
            Assert.AreEqual(RingId.Golge, rooms["R4-02"].Ring);
            Assert.AreEqual(RingId.Ayna, rooms["R5-04"].Ring);
        }

        [Test]
        public void GercekTablo_SureButcesi()
        {
            var rooms = RoomTableParser.Parse(ReadRealTable());
            foreach (var room in rooms.Values)
            {
                Assert.Greater(room.EstimatedMinutes, 0, room.Id);
                if (room.Ring == RingId.Toprak || room.Ring == RingId.Su)
                    Assert.LessOrEqual(room.EstimatedMinutes, RoomTableParser.OuterRingMaxMinutes, room.Id + " (K-04)");
            }
            Assert.AreEqual(8, rooms["R4-02"].EstimatedMinutes, "Gölge 6–10 dk");
            Assert.AreEqual(12, rooms["R5-04"].EstimatedMinutes, "Ayna 10–15 dk");
            Assert.AreEqual(10, rooms["R7-01"].EstimatedMinutes, "Ân 10 dk civarı");
        }

        [Test]
        public void SessizlikIlkOda_IkiGelisTekVarlik()
        {
            var r = RoomTableParser.Parse(ReadRealTable())["R6-01"];
            Assert.AreEqual(2, r.Visits);
            Assert.AreEqual(36, r.Number);
            Assert.AreEqual(7, r.EstimatedMinutes, "2 dk ilk geliş + 5 dk ikinci geliş");
            StringAssert.Contains("kırk yıl", r.Puzzle);
            StringAssert.Contains("ad bekler", r.Puzzle);
            Assert.AreEqual(HalKind.None, r.Hal, "Sessizlik'te hâl yok");
        }

        [Test]
        public void BilinmeyenHal_SatirNumarasiylaHata()
        {
            string bad = ReadRealTable().Replace("| Duvar titrer |", "| Duvar konuşur |");
            var ex = Assert.Throws<FormatException>(() => RoomTableParser.Parse(bad));
            StringAssert.Contains("bilinmeyen hâl", ex.Message);
            StringAssert.StartsWith("kirk-oda.md:", ex.Message);
        }

        [Test]
        public void EksikOda_Hata()
        {
            string table = ReadRealTable();
            int start = table.IndexOf("| R3-04 (21)", StringComparison.Ordinal);
            int end = table.IndexOf('\n', start);
            var ex = Assert.Throws<FormatException>(() => RoomTableParser.Parse(table.Remove(start, end - start + 1)));
            StringAssert.Contains("R3-04 tabloda yok", ex.Message);
        }

        [Test]
        public void YanlisHalkaTablosundakiOda_Hata()
        {
            string bad = ReadRealTable().Replace("| R2-01 (10) |", "| R3-01 (10) |");
            Assert.Throws<FormatException>(() => RoomTableParser.Parse(bad));
        }
    }
}

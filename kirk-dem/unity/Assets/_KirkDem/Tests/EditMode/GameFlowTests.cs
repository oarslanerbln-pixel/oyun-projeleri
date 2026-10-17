using NUnit.Framework;

namespace KirkDem.Core.Tests
{
    /// <summary>Senaryo kilidinin omurgası uçtan uca: yedi dönüş, kırk yıl, ad, terk, sonlar.</summary>
    public class GameFlowTests
    {
        static GameState PlayToAn(bool[] tell, bool giveName)
        {
            var g = new GameState(6);
            RingId[] rings = { RingId.Toprak, RingId.Su, RingId.Nefes, RingId.Golge, RingId.Ayna };
            for (int i = 0; i < rings.Length; i++)
            {
                g.Descend(rings[i]);
                if (rings[i] == RingId.Ayna) for (int k = 1; k <= 5; k++) g.EditRecord("ayna-" + k);
                g.ExitRing(rings[i]);
                if (tell[i]) g.TellSecret(rings[i]);
            }
            g.Descend(RingId.Sessizlik);
            Assert.IsTrue(g.CommitFortyYears());
            g.ExitRing(RingId.Sessizlik);
            if (tell[5]) g.TellSecret(RingId.Sessizlik);
            g.Descend(RingId.Sessizlik);
            if (giveName) Assert.IsTrue(g.GiveName());
            g.ExitRing(RingId.Sessizlik);
            g.EnterAn();
            return g;
        }

        [Test]
        public void YediDonus_DortCag()
        {
            var g = PlayToAn(new bool[6], giveName: false);
            Assert.AreEqual(EraId.Terk, g.Clock.Era);
            Assert.AreEqual(2, g.Clock.SilenceExits);
        }

        [Test]
        public void KirkYil_KitabeyiBosaltir_AdVerilmezseTerkteDolar_K16()
        {
            var g = new GameState(6);
            g.Descend(RingId.Ayna);
            g.EditRecord("mezar"); g.EditRecord("fotograf");
            Assert.AreEqual(4, g.Tower.Inscription.Remaining);
            g.ExitRing(RingId.Ayna);
            g.CommitFortyYears();
            Assert.IsTrue(g.Tower.Inscription.IsEmpty, "Kırılma 2: kitabe boş");
            g.ExitRing(RingId.Sessizlik);
            g.ExitRing(RingId.Sessizlik);
            Assert.AreEqual(6, g.Tower.Inscription.Remaining, "ad verilmedi: terkte kitabe dolu okunur");
        }

        [Test]
        public void AdVerilirse_KitabeBosKalir()
        {
            var g = PlayToAn(new bool[6], giveName: true);
            Assert.IsTrue(g.Tower.NameGiven);
            Assert.IsTrue(g.Tower.Inscription.IsEmpty);
        }

        [Test]
        public void AdKirkYildanOnceVerilemez()
        {
            var g = new GameState(6);
            Assert.IsFalse(g.GiveName());
        }

        [Test]
        public void S7_GosterilirAmaSayilmaz()
        {
            var g = PlayToAn(new bool[6], giveName: true);
            Assert.IsTrue(g.Secrets.IsRevealed(RingId.An));
            Assert.AreEqual(SecretChoice.Undecided, g.Secrets.Choice(RingId.An));
            Assert.AreEqual(6, g.Secrets.KeptCount);
            Assert.AreEqual(1f, g.Stone.NormalizedPitch, 1e-5f);
        }

        [Test]
        public void Sonlar_UcYol()
        {
            var donus = PlayToAn(new[] { false, false, false, false, true, true }, giveName: true).EndingsAvailable();
            Assert.IsTrue(donus.Donus); Assert.IsFalse(donus.Dagitis);

            var dagitis = PlayToAn(new[] { true, true, true, true, false, false }, giveName: true).EndingsAvailable();
            Assert.IsTrue(dagitis.Dagitis); Assert.IsFalse(dagitis.Donus);

            var orta = PlayToAn(new[] { true, true, true, false, false, false }, giveName: true).EndingsAvailable();
            Assert.AreEqual(1, orta.OpenCount);
            Assert.IsTrue(orta.Kalis);
        }

        [Test]
        public void KilometreTasi_YalnizIleri()
        {
            var g = new GameState(6);
            var room = g.Rooms.Get("R5-03");
            Assert.IsTrue(room.ReachMilestone(2));
            Assert.IsFalse(room.ReachMilestone(1));
            Assert.AreEqual(2, room.Milestone);
        }
    }
}

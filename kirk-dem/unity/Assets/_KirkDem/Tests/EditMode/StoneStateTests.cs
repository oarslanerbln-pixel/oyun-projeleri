using NUnit.Framework;

namespace KirkDem.Core.Tests
{
    public class StoneStateTests
    {
        [Test]
        public void Perde_SaklananEksiSoylenen()
        {
            var s = new StoneState();
            s.Recalculate(keptCount: 4, toldCount: 1);
            Assert.AreEqual(3, s.RawPitch);
            Assert.AreEqual(3f / 6f, s.NormalizedPitch, 1e-5f);
        }

        [Test]
        public void Uclar_EksiBirVeArtiBir()
        {
            var s = new StoneState();
            s.Recalculate(6, 0); Assert.AreEqual(1f, s.NormalizedPitch, 1e-5f);
            s.Recalculate(0, 6); Assert.AreEqual(-1f, s.NormalizedPitch, 1e-5f);
            Assert.Throws<System.ArgumentOutOfRangeException>(() => s.Recalculate(4, 3), "S7 sayılmaz: en çok 6 sır");
        }

        [Test]
        public void PitchChanged_YalnizDegisimde()
        {
            var s = new StoneState();
            int fired = 0; s.PitchChanged += _ => fired++;
            s.Recalculate(0, 0); // 0 → 0: değişim yok
            s.Recalculate(1, 0);
            s.Recalculate(1, 0);
            Assert.AreEqual(1, fired);
        }

        [Test]
        public void PitchMap_OktavBasinaIkiKat()
        {
            Assert.AreEqual(220f, PitchMap.Frequency(0f), 0.01f);
            Assert.AreEqual(440f, PitchMap.Frequency(1f), 0.01f);
            Assert.AreEqual(110f, PitchMap.Frequency(-1f), 0.01f);
        }

        [Test]
        public void PitchMap_UcKanalAyniYondeArtar()
        {
            float lo = -1f, mid = 0f, hi = 1f;
            Assert.Less(PitchMap.HapticRate(lo), PitchMap.HapticRate(mid));
            Assert.Less(PitchMap.HapticRate(mid), PitchMap.HapticRate(hi));
            Assert.Less(PitchMap.RippleDensity(lo), PitchMap.RippleDensity(mid));
            Assert.Less(PitchMap.RippleDensity(mid), PitchMap.RippleDensity(hi));
        }

        [Test]
        public void Ledger_IleZincir()
        {
            var g = new GameState(inscriptionLetters: 6);
            g.Secrets.Reveal(RingId.Toprak);
            g.TellSecret(RingId.Toprak);
            Assert.AreEqual(-1f / 6f, g.Stone.NormalizedPitch, 1e-5f);
            Assert.AreEqual(false, g.Tower.Floor(RingId.Toprak).IsLit);

            g.Secrets.Reveal(RingId.Su);
            g.Descend(RingId.Nefes); // söylenmemiş sır inişle saklanır
            Assert.AreEqual(SecretChoice.Kept, g.Secrets.Choice(RingId.Su));
            Assert.AreEqual(0f, g.Stone.NormalizedPitch, 1e-5f);
            Assert.AreEqual(true, g.Tower.Floor(RingId.Su).IsLit);
        }
    }
}

using NUnit.Framework;

namespace KirkDem.Core.Tests
{
    public class ReverseRecorderTests
    {
        [Test]
        public void TerstenOynatir()
        {
            var rec = new ReverseRecorder<int>(8);
            for (int i = 1; i <= 5; i++) rec.Push(i);
            Assert.AreEqual(5, rec.Replay(0));
            Assert.AreEqual(4, rec.Replay(1));
            Assert.AreEqual(1, rec.Replay(4));
            Assert.AreEqual(1, rec.Replay(99), "kayıt bitince en eski örnekte kalır");
        }

        [Test]
        public void Kapasite_EnEskiyiUnutur()
        {
            var rec = new ReverseRecorder<int>(3);
            for (int i = 1; i <= 5; i++) rec.Push(i);
            Assert.AreEqual(3, rec.Count);
            Assert.AreEqual(5, rec.FromEnd(0));
            Assert.AreEqual(3, rec.FromEnd(2));
        }

        [Test]
        public void Bos_KayitHataVerir()
        {
            var rec = new ReverseRecorder<int>(2);
            Assert.Throws<System.InvalidOperationException>(() => rec.Replay(0));
        }
    }
}

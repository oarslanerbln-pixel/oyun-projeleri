using System.Collections.Generic;

namespace KirkDem.Core
{
    public sealed class RoomProgress
    {
        public string RoomId { get; }
        public RingId Ring { get; }
        public bool Solved { get; private set; }
        public bool HalOffered { get; private set; }
        public bool HalUsed { get; private set; }
        public bool DemCollected { get; private set; }

        /// <summary>Oda içi kilometre taşı (0 = giriş). Sessiz kontrol noktası ve köpek ipucu zamanlayıcısı bunu okur.</summary>
        public int Milestone { get; private set; }

        /// <summary>Uzun yol: hâl sunuldu, kullanılmadı, oda çözüldü.</summary>
        public bool TookLongPath => Solved && HalOffered && !HalUsed;

        internal RoomProgress(string roomId, RingId ring) { RoomId = roomId; Ring = ring; }

        public void OfferHal() => HalOffered = true;
        public void UseHal() { if (HalOffered) HalUsed = true; }
        public void Solve() => Solved = true;

        /// <summary>Bulmacada geri alınamaz bir adım atıldı. Yalnız ileri gider.</summary>
        public bool ReachMilestone(int milestone)
        {
            if (milestone <= Milestone) return false;
            Milestone = milestone;
            return true;
        }
        public void CollectDem() { if (Solved) DemCollected = true; }

        public void Restore(bool solved, bool halOffered, bool halUsed, bool demCollected, int milestone = 0)
        {
            Solved = solved; HalOffered = halOffered; HalUsed = halUsed; DemCollected = demCollected; Milestone = milestone;
        }
    }

    /// <summary>Kırk odanın ilerlemesi. Oda içinde yalnız kilometre taşı kaydedilir (ADR-0006, karar K-13).</summary>
    public sealed class RoomProgressLedger
    {
        readonly Dictionary<string, RoomProgress> _rooms = new Dictionary<string, RoomProgress>(RingCatalog.TotalRooms);

        public RoomProgressLedger()
        {
            for (int r = 1; r <= RingCatalog.RingCount; r++)
            {
                var ring = (RingId)r;
                for (int i = 1; i <= RingCatalog.RoomCount(ring); i++)
                {
                    var id = RingCatalog.RoomId(ring, i);
                    _rooms[id] = new RoomProgress(id, ring);
                }
            }
        }

        public RoomProgress Get(string roomId) => _rooms[roomId];
        public IEnumerable<RoomProgress> All => _rooms.Values;

        public int SolvedInRing(RingId ring)
        {
            int n = 0;
            foreach (var p in _rooms.Values) if (p.Ring == ring && p.Solved) n++;
            return n;
        }

        public bool RingComplete(RingId ring) => SolvedInRing(ring) == RingCatalog.RoomCount(ring);
    }
}

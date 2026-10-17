using System;
using System.Globalization;

namespace KirkDem.Core
{
    /// <summary>Kimlik sözleşmesinin tek kaynağı: halka sırası, oda sayıları, id biçimleri.</summary>
    public static class RingCatalog
    {
        public const int RingCount = 7;
        public const int TotalRooms = 40;
        public const int SecretCount = 7;

        static readonly int[] RoomCounts = { 0, 9, 8, 7, 6, 5, 4, 1 }; // index = RingId
        static readonly string[] Ids = { "kasaba", "toprak", "su", "nefes", "golge", "ayna", "sessizlik", "an" };

        public static int RoomCount(RingId ring) => RoomCounts[(int)ring];

        public static string Id(RingId ring) => Ids[(int)ring];

        public static string SecretId(RingId ring) => "S" + ((int)ring).ToString(CultureInfo.InvariantCulture);

        /// <summary>R{halka}-{oda:00}, örn. R1-01, R7-01.</summary>
        public static string RoomId(RingId ring, int index)
        {
            if (ring == RingId.None) throw new ArgumentException("Kasabada oda yok.", nameof(ring));
            if (index < 1 || index > RoomCount(ring))
                throw new ArgumentOutOfRangeException(nameof(index), $"{ring} halkasında {RoomCount(ring)} oda var.");
            return "R" + (int)ring + "-" + index.ToString("00", CultureInfo.InvariantCulture);
        }

        public static bool TryParseRoomId(string id, out RingId ring, out int index)
        {
            ring = RingId.None; index = 0;
            if (string.IsNullOrEmpty(id) || id.Length != 5 || id[0] != 'R' || id[2] != '-') return false;
            if (!int.TryParse(id.Substring(1, 1), out var r) || r < 1 || r > RingCount) return false;
            if (!int.TryParse(id.Substring(3, 2), out var i)) return false;
            ring = (RingId)r;
            if (i < 1 || i > RoomCount(ring)) return false;
            index = i;
            return true;
        }

        public static RingId Next(RingId ring) => ring == RingId.An ? RingId.An : (RingId)((int)ring + 1);

        /// <summary>0 kasaba … 1 Ân. Köpek gölgesi ve kamera kademesi bunu okur.</summary>
        public static float Depth(RingId ring) => (int)ring / (float)RingCount;
    }
}

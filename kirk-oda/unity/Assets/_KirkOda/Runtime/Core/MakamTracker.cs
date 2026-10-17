using System.Collections.Generic;

namespace KirkOda.Core
{
    /// <summary>
    /// Hâl sunulan odada uzun yol seçilince kulede bir nota asılı kalır; üçüncüde çan dizisine kalıcı eklenir.
    /// Makam sonu değiştirmez, sonun sesini değiştirir. Oyun açıklamaz.
    /// </summary>
    public sealed class MakamTracker
    {
        public const int LongPathsPerNote = 3;

        readonly List<float> _notesHz = new List<float>();

        public int PendingCount { get; private set; }               // 0..2 asılı nota
        public IReadOnlyList<float> NotesHz => _notesHz;             // çan dizisi
        public bool HasMakam => _notesHz.Count > 0;
        public int TotalLongPaths { get; private set; }

        /// <summary>Oda çözüldü, hâl sunulmuştu, kullanılmadı. baseHz: o halkanın temel notası.</summary>
        /// <returns>Bu uzun yolla kalıcı nota eklendiyse true.</returns>
        public bool RegisterLongPath(float ringBaseHz)
        {
            TotalLongPaths++;
            PendingCount++;
            if (PendingCount < LongPathsPerNote) return false;
            PendingCount = 0;
            _notesHz.Add(ringBaseHz);
            return true;
        }

        public void Restore(int pending, IEnumerable<float> notesHz, int totalLongPaths)
        {
            PendingCount = pending; _notesHz.Clear(); _notesHz.AddRange(notesHz); TotalLongPaths = totalLongPaths;
        }
    }
}

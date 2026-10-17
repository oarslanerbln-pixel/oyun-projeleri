using System;
using System.Collections.Generic;

namespace KirkDem.Core
{
    /// <summary>
    /// Ayna halkası: kasaba kayıtlarına yapılan değişiklikler (ADR-0009 §3). Her değişiklik bir komuttur;
    /// kasaba sahnesi bu listeyi okuyup mezar taşı, fotoğraf, defter ve kitabeyi günceller.
    /// Her değişiklik kitabeden bir harf siler; geri alma (R5-04) bir harfi geri getirir.
    /// </summary>
    public sealed class RecordLedger
    {
        readonly List<string> _edits = new List<string>();
        readonly Inscription _inscription;

        public RecordLedger(Inscription inscription)
        {
            _inscription = inscription ?? throw new ArgumentNullException(nameof(inscription));
        }

        public IReadOnlyList<string> Edits => _edits;
        public int Count => _edits.Count;

        /// <summary>recordId, applied (true: değişti, false: geri alındı).</summary>
        public event Action<string, bool> Changed;

        public bool IsEdited(string recordId) => _edits.Contains(recordId);

        public bool Apply(string recordId)
        {
            if (string.IsNullOrEmpty(recordId)) throw new ArgumentException("Kayıt kimliği boş.", nameof(recordId));
            if (_edits.Contains(recordId)) return false;
            _edits.Add(recordId);
            _inscription.RemoveLetter();
            Changed?.Invoke(recordId, true);
            return true;
        }

        public bool Undo(string recordId)
        {
            if (!_edits.Remove(recordId)) return false;
            _inscription.RestoreLetter();
            Changed?.Invoke(recordId, false);
            return true;
        }

        /// <summary>Kayıttan yükleme. Kitabe ayrı yüklenir; burada harf hesabı yapılmaz.</summary>
        public void Restore(IEnumerable<string> edits)
        {
            _edits.Clear();
            if (edits != null) _edits.AddRange(edits);
        }
    }
}

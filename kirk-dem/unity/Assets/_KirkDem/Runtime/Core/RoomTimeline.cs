using System;
using System.Collections.Generic;

namespace KirkDem.Core
{
    /// <summary>Zaman çizelgesinde kaydedilmiş bir eylem.</summary>
    public readonly struct TimelineEvent
    {
        public readonly string ActionId;
        public readonly float T;
        public readonly bool Rewindable;

        public TimelineEvent(string actionId, float t, bool rewindable)
        {
            ActionId = actionId; T = t; Rewindable = rewindable;
        }
    }

    /// <summary>
    /// Su ve Gölge odalarının zaman ekseni (ADR-0009 §1). t ∈ [0, 1]; dioramadaki her nesne t'nin fonksiyonudur,
    /// fizik yoktur. Oyuncunun eylemleri t üzerinde olay olarak kaydedilir. Geri sarılırken t'den sonraki
    /// geri sarılabilir olaylar silinir (dal kesilir); geri sarılamaz olaylar (R2-03: saatçi sarılmaz) kalır.
    /// </summary>
    public sealed class RoomTimeline
    {
        readonly List<TimelineEvent> _events = new List<TimelineEvent>();

        public float DurationSeconds { get; }
        public float T { get; private set; }
        public IReadOnlyList<TimelineEvent> Events => _events;

        public event Action<TimelineEvent> EventUndone;

        public RoomTimeline(float durationSeconds)
        {
            if (durationSeconds <= 0f) throw new ArgumentOutOfRangeException(nameof(durationSeconds));
            DurationSeconds = durationSeconds;
        }

        /// <summary>dt saniye kadar ilerle (direction +1) ya da geri sar (direction −1).</summary>
        public void Advance(float dt, int direction)
        {
            if (dt < 0f) throw new ArgumentOutOfRangeException(nameof(dt));
            if (direction != 1 && direction != -1) throw new ArgumentOutOfRangeException(nameof(direction));
            float next = T + direction * dt / DurationSeconds;
            T = next < 0f ? 0f : (next > 1f ? 1f : next);
            if (direction < 0) Prune();
        }

        /// <summary>Eylemi şimdiki t'de kaydet. Aynı eylem çizelgede zaten varsa false.</summary>
        public bool Record(string actionId, bool rewindable = true)
        {
            if (string.IsNullOrEmpty(actionId)) throw new ArgumentException("Eylem kimliği boş.", nameof(actionId));
            if (Happened(actionId)) return false;
            _events.Add(new TimelineEvent(actionId, T, rewindable));
            return true;
        }

        public bool Happened(string actionId)
        {
            for (int i = 0; i < _events.Count; i++) if (_events[i].ActionId == actionId) return true;
            return false;
        }

        public void Reset()
        {
            T = 0f;
            _events.Clear();
        }

        void Prune()
        {
            for (int i = _events.Count - 1; i >= 0; i--)
            {
                var e = _events[i];
                if (e.Rewindable && e.T > T)
                {
                    _events.RemoveAt(i);
                    EventUndone?.Invoke(e);
                }
            }
        }
    }

    /// <summary>
    /// Su'nun gelgiti: önce ileri, sonra geri. Her döngüde ileri akış uzayabilir (R2-05).
    /// Faz kaydırma ile iki havuz ayrı gelgitle çalışır (R2-06).
    /// </summary>
    public sealed class Tide
    {
        public float ForwardSeconds { get; private set; }
        public float BackwardSeconds { get; }
        public float GrowthPerCycle { get; }
        public int Cycle { get; private set; }

        float _clock;

        public Tide(float forwardSeconds, float backwardSeconds, float growthPerCycle = 0f, float phaseSeconds = 0f)
        {
            if (forwardSeconds <= 0f || backwardSeconds <= 0f) throw new ArgumentOutOfRangeException(nameof(forwardSeconds));
            if (growthPerCycle < 0f) throw new ArgumentOutOfRangeException(nameof(growthPerCycle));
            ForwardSeconds = forwardSeconds; BackwardSeconds = backwardSeconds; GrowthPerCycle = growthPerCycle;
            _clock = phaseSeconds < 0f ? 0f : phaseSeconds;
            Normalize();
        }

        /// <summary>Şimdiki akış yönü: +1 ileri, −1 geri.</summary>
        public int Direction => _clock < ForwardSeconds ? 1 : -1;

        public int Tick(float dt)
        {
            if (dt < 0f) throw new ArgumentOutOfRangeException(nameof(dt));
            _clock += dt;
            Normalize();
            return Direction;
        }

        void Normalize()
        {
            while (_clock >= ForwardSeconds + BackwardSeconds)
            {
                _clock -= ForwardSeconds + BackwardSeconds;
                Cycle++;
                ForwardSeconds += GrowthPerCycle;
            }
        }
    }
}

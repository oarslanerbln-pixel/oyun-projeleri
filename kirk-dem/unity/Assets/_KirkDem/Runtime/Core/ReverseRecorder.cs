using System;

namespace KirkDem.Core
{
    /// <summary>
    /// Gölge halkası: öbür yaştaki saatçi, oyuncunun kendi kaydının tersten oynatımıdır (ADR-0009 §2).
    /// Sabit kapasiteli halka arabellek; kare başına bir örnek. Ayrı bir yapay zekâ gerekmez.
    /// </summary>
    public sealed class ReverseRecorder<T>
    {
        readonly T[] _buffer;
        int _head;   // bir sonraki yazılacak yer
        int _count;

        public ReverseRecorder(int capacity)
        {
            if (capacity < 1) throw new ArgumentOutOfRangeException(nameof(capacity));
            _buffer = new T[capacity];
        }

        public int Capacity => _buffer.Length;
        public int Count => _count;

        public void Push(T sample)
        {
            _buffer[_head] = sample;
            _head = (_head + 1) % _buffer.Length;
            if (_count < _buffer.Length) _count++;
        }

        /// <summary>stepsBack = 0 en son örnek; Count − 1 en eski örnek.</summary>
        public T FromEnd(int stepsBack)
        {
            if (stepsBack < 0 || stepsBack >= _count) throw new ArgumentOutOfRangeException(nameof(stepsBack));
            int index = (_head - 1 - stepsBack) % _buffer.Length;
            if (index < 0) index += _buffer.Length;
            return _buffer[index];
        }

        /// <summary>
        /// Tersten oynatım: canlı oynanışın i. karesinde gölgedeki saatçi, kaydın sonundan i kare gerideki
        /// konumdadır. Kayıt bitince en eski örnekte kalır.
        /// </summary>
        public T Replay(int framesSinceReplayStart)
        {
            if (_count == 0) throw new InvalidOperationException("Kayıt boş.");
            int k = framesSinceReplayStart < 0 ? 0 : framesSinceReplayStart;
            return FromEnd(k < _count ? k : _count - 1);
        }

        public void Clear()
        {
            _head = 0;
            _count = 0;
            Array.Clear(_buffer, 0, _buffer.Length);
        }
    }
}

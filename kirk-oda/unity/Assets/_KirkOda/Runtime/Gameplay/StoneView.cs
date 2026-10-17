using KirkOda.Core;
using UnityEngine;

namespace KirkOda.Gameplay
{
    /// <summary>
    /// Taşın üç kanalı: ses perdesi, gamepad titreşimi, yüzey dalga sıklığı. Üçü PitchMap'ten (ADR-0007).
    /// </summary>
    public sealed class StoneView : MonoBehaviour
    {
        [SerializeField] AudioSource toneSource;      // ProceduralToneSource ya da clip
        [SerializeField] Renderer stoneRenderer;      // Shader Graph: _RippleDensity
        static readonly int RippleDensityId = Shader.PropertyToID("_RippleDensity");

        StoneState _stone;

        void OnEnable()
        {
            _stone = GameRoot.Instance.State.Stone;
            _stone.PitchChanged += Apply;
            Apply(_stone.NormalizedPitch);
        }

        void OnDisable() { if (_stone != null) _stone.PitchChanged -= Apply; }

        void Apply(float normalizedPitch)
        {
            float hz = PitchMap.Frequency(normalizedPitch);
            if (toneSource) toneSource.pitch = hz / PitchMap.BaseHz; // clip 220 Hz'de render edilmişse
            if (stoneRenderer) stoneRenderer.material.SetFloat(RippleDensityId, PitchMap.RippleDensity(normalizedPitch));
            // TODO: HapticBridge.SetRate(PitchMap.HapticRate(normalizedPitch))
        }

        void Update()
        {
            // Taş yalnız sallanırken ses verir; sallanma yürüyüşten gelir. Dinlerken saatçi durur, taş susar.
            // TODO: _stone.IsSwinging = PlayerMotor.IsMoving; toneSource.mute = !_stone.IsSwinging
        }
    }
}

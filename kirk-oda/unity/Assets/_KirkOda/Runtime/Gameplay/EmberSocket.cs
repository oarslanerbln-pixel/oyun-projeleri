using KirkOda.Core;
using UnityEngine;

namespace KirkOda.Gameplay
{
    /// <summary>Kule katındaki yuva. Yalnız kendi halkasının korunu kabul eder; hata mesajı yok, yuva kabul etmez.</summary>
    public sealed class EmberSocket : MonoBehaviour
    {
        [SerializeField] RingId ring;

        public void Interact()
        {
            var state = GameRoot.Instance.State;
            if (state.Tower.Floor(ring).Carried == 0) return; // taşınan kor yok: sessizce hiçbir şey olmaz
            if (!state.InstallEmber(ring)) return;
            GameRoot.Instance.SaveNow();
            // TODO: TowerFloorView.PlayInstall(ring) — kat döner, katın notası eklenir (ses-mimarisi §2)
        }
    }
}

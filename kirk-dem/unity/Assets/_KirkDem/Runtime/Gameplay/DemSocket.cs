using KirkDem.Core;
using UnityEngine;

namespace KirkDem.Gameplay
{
    /// <summary>Kule katındaki yuva. Yalnız kendi halkasının demini kabul eder; hata mesajı yok, yuva kabul etmez.</summary>
    public sealed class DemSocket : MonoBehaviour
    {
        [SerializeField] RingId ring;

        public void Interact()
        {
            var state = GameRoot.Instance.State;
            if (state.Tower.Floor(ring).Carried == 0) return; // taşınan dem yok: sessizce hiçbir şey olmaz
            if (!state.InstallDem(ring)) return;
            GameRoot.Instance.SaveNow();
            // TODO: TowerFloorView.PlayInstall(ring) — kat döner, katın notası eklenir (ses-mimarisi §2)
        }
    }
}

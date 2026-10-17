using KirkDem.Core;
using UnityEngine;

namespace KirkDem.Gameplay
{
    /// <summary>
    /// Halka sahnesinden kasabaya çıkış. Yalnız halkanın tüm odaları çözülmüşse açılır.
    /// Çıkışta: sır gösterilir (tek cümle, silinir), çağ geçer, kayıt alınır.
    /// </summary>
    public sealed class RingExitGate : MonoBehaviour
    {
        [SerializeField] RingId ring;

        public bool IsOpen => GameRoot.Instance.State.Rooms.RingComplete(ring);

        void OnTriggerEnter(Collider other)
        {
            if (!IsOpen) return;
            if (!other.CompareTag("Player")) return;
            var state = GameRoot.Instance.State;
            state.ExitRing(ring);
            GameRoot.Instance.SaveNow();
            // TODO: SecretPresenter.Show(RingCatalog.SecretId(ring)) — gösterilir, silinir
            // TODO: SceneFlow.ToTown(era: state.Clock.Era) — Su çıkışında "bir-yil" videosu
        }
    }
}

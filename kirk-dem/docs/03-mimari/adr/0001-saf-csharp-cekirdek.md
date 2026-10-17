# ADR-0001 — Saf C# çekirdek, Unity kabuk

**Durum:** Kabul edildi · 2026-10-16

## Bağlam
Oyunun kuralları (zaman kuralları, sır defteri, taş perdesi, kule durumu, çağ geçişi, son çözücüsü) az sayıda ama birbirine bağlı ve hatası pahalı: yanlış bir çağ geçişi ya da yanlış açılan bir son, oyuncunun 5–8 saatini bozar. Tek kişilik stüdyoda bu kuralları Unity sahnesini açarak test etmek yavaş ve kırılgandır.

## Karar
Kurallar `KirkDem.Core` assembly'sinde, `noEngineReferences = true` ile, UnityEngine'e hiç bağımlı olmadan yazılır. Unity katmanları (Gameplay, Audio, Presentation) Core'u çağırır ve yansıtır; kural kararı vermez. Core, Unity Test Runner EditMode'da NUnit ile test edilir.

## Sonuçlar
- Kural testleri milisaniyede koşar; oyun açılmaz.
- Core sınıfları düz veri taşır; kayıt (Save) doğrudan serileştirilebilir.
- Bedel: Unity tarafında ince bir köprü katmanı (olay → Core çağrısı → durum okuma) yazılır. Bu katman kasıtlı olarak aptal tutulur.
- Core'da `Vector3`, `Color`, `GameObject` yok; konum ve renk Data katmanında kalır.

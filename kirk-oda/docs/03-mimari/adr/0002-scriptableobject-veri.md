# ADR-0002 — İçerik ScriptableObject'lerde

**Durum:** Kabul edildi · 2026-10-16

## Bağlam
Kırk oda, kırk bekçi, yedi sır, yedi kasabalı × dört çağ. Bu içerik senaryo kilidiyle gelir ve üretim boyunca değişir. Kodda sabit tutulursa her değişiklik derleme ister; JSON'da tutulursa Unity referansları (prefab, clip) kopar.

## Karar
Tüm içerik `KirkOda.Data` assembly'sindeki ScriptableObject tanımlarındadır (`veri-modeli.md`). Core yalnız string id ve enum bilir. Metinler Unity Localization anahtarıdır; SO'da ham metin yok.

## Sonuçlar
- Tasarımcı Inspector'dan çalışır; kod değişmez.
- Kimlik sözleşmesi (`R{n}-{nn}`, `S{n}`, kasabalı id'leri) tek kaynaktan (`RingCatalog`) doğrulanır; Editor'de validator yazılır.
- Bedel: SO sayısı yüksek (~100). Klasör düzeni ve Ring Overview aracı bunu yönetir.

# ADR-0004 — Kasaba tek harita, dört çağ aynı sahnenin dört hali

**Durum:** Kabul edildi · 2026-10-16

## Bağlam
Oyuncu kasabayı her halkadan çıkışında başka bir çağda bulur: bugün, bir yıla yakın sonra, kırk yıl sonra, terk edilmiş. Dört ayrı sahne yapmak dört kat iş ve kasabanın "aynı yer" hissini kırar. Kırk yıl videosu da aynı kadrajdan çekilecek.

## Karar
Kasaba tek sahnedir (`Kasaba`). Çağ, `EraId`ye göre uygulanan bir **durum katmanı**dır: kasabalı prefab varyantları (`TownspersonDefinition.eras`), malzeme sıcaklığı (`EraDefinition.lightingProfile`), kayıt nesneleri (mezarlık boyutu, değirmen, kapak). Saatçinin çocukluk kasabası yeryüzünde yoktur; yalnız Su halkasında diorama olarak vardır ve ayrı küçük bir prefab'tır.

## Sonuçlar
- Kırk yıl ve Bir yıl videoları aynı sahneden sabit kamerayla çekilir; birebir tutarlı.
- Çağ yalnız ileri gider; `TownClock.TrySetEra` küçük çağı reddeder. Geri dönüş yolu kodda yoktur.
- Ayna halkasının kayıt değişiklikleri (`TownRecords`) aynı sahnedeki nesnelere yazar; "hep böyle miydi" belirsizliği için önceki durum hiçbir yerde gösterilmez.
- Bedel: sahne büyük; çağ varyantları additive alt sahnelere bölünebilir (ileride, gerekirse).

# ADR-0003 — Tek dinamik ışık, geri kalanı pişirilmiş

**Durum:** Kabul edildi · 2026-10-16

## Bağlam
Görsel dil: karanlıkta tek sıcak ışık kaynağı ve ulaşamadığı her yerde soğuk mavi. Düşük donanımda pahalı görünmesi hedefleniyor. Kırk oda için gerçek zamanlı aydınlatma hem performans hem de görsel tutarlılık riskidir.

## Karar
Sahnede tek dinamik ışık vardır: saatçinin feneri (`LanternPoint`'e bağlı, oyuncuyla gelir). Oda prefab'larında dinamik ışık yoktur. Geri kalan her şey baked lighting (Light Probe + lightmap) ve emissive malzemedir. Ses çizgileri parçacık değil, emissive çizgi mesh'idir. Bloom ve ışıma reçetesi The Sky Is Lit'ten korunur; parametreler sanat kitabına taşınır.

## Sonuçlar
- Kırk odanın ışık bütçesi sabit ve bilinir.
- Gölge halkasının "ışıkta ileri, gölgede geri" kuralı doğrudan fenerin aydınlattığı alan maskesinden türetilir; ikinci ışık gerekmez.
- Bedel: baked süreleri; oda kiti üretim ritüelinde 9–11. günlere konulur. Lightmap çözünürlüğü halka başına sabit tutulur.

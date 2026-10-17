# ADR-0006 — Tek slot, otomatik kayıt

**Durum:** Kabul edildi · 2026-10-16

## Bağlam
Oyunda ölüm, başarısızlık, geri alma yok; her seçim kalıcı ("geri gelmez"). Çoklu kayıt slotu bu ilkeyi kırar: oyuncu sır söylemeden önce kaydedip dener.

## Karar
Tek kayıt slotu. Halka çıkışında, kasabadaki her eylemde ve oda içindeki her kilometre taşında otomatik kayıt. Manuel kayıt/yükleme menüsü yok. Kasabada çıkılırsa kasabada, oda içinde çıkılırsa o odanın son kilometre taşında başlar. Yeni oyun eskisinin üstüne yazar (kulede kapıdan çıkmak = onay).

**Güncelleme, 17 Ekim 2026 (karar K-13):** Kilometre taşı kaydı eklendi. 10–15 dakikalık Ayna ve Sessizlik odalarında çıkan oyuncu odayı baştan oynamamalı. Kilometre taşları yalnız ileri gider ve geri alınamaz adımlara konur; tek slot ilkesi ve "deneyip geri alma yok" ilkesi korunur.

## Sonuçlar
- Seçimler gerçekten kalıcıdır; "deneyip geri alma" yolu yoktur.
- Kayıt verisi küçük (`GameState`), JSON, bozulmaya karşı yedek kopya (`.bak`).
- Bedel: oyuncu bir sondan sonra diğerini görmek için yeniden oynar; tasarım bunu kabul eder (üç son da yarımdır).

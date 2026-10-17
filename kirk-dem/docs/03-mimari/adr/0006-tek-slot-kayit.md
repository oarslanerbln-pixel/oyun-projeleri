# ADR-0006 — Tek slot, otomatik kayıt

**Durum:** Kabul edildi · 2026-10-16

## Bağlam
Oyunda ölüm, başarısızlık, geri alma yok; her seçim kalıcı ("geri gelmez"). Çoklu kayıt slotu bu ilkeyi kırar: oyuncu sır söylemeden önce kaydedip dener.

## Karar
Tek kayıt slotu. Halka çıkışında ve kasabadaki her eylemde otomatik kayıt. Manuel kayıt/yükleme menüsü yok. Geri yükleme kasabada başlar; oda içi ara durum kaydedilmez, çözülmüş odalar korunur. Yeni oyun eskisinin üstüne yazar (kulede kapıdan çıkmak = onay).

## Sonuçlar
- Seçimler gerçekten kalıcıdır; "deneyip geri alma" yolu yoktur.
- Kayıt verisi küçük (`GameState`), JSON, bozulmaya karşı yedek kopya (`.bak`).
- Bedel: oyuncu bir sondan sonra diğerini görmek için yeniden oynar; tasarım bunu kabul eder (üç son da yarımdır).

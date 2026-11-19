# Aurenza: kuyumcu bindirme stili

Kuyumcu Ferhat'ın (Aurenza Fine Jewelry, Berlin) konuşma videoları için sabit, lüks yazı ve grafik katmanı: ilk saniyede kanca başlık, altın kıl çizgili koyu mücevher kutusu kartları, profesyonel altyazı, sonunda fotoğraf finali ve her videoda ekranda kalan takip kartı. Türkçe ve Almanca aynı stille çalışır; yalnız `veri.json` değişir.

## Görünüm
- **Renk:** koyu sıcak cam kart (`rgba(17,13,10,.6)`), şampanya altını `#D9BE8A`, fildişi `#F7F1E6`; vurgu kelimeleri altın varak gradyanı.
- **Yazı:** Cinzel (tabeladaki AURENZA harflerine yakın, büyük harf etiketler ve marka), Cormorant Garamond (duygu cümleleri italik, başlık düz 600), Inter (altyazı, küçük alt satırlar). Fontlar `fontlar/` (OFL, Google Fonts woff2; LFS dışı).
- **Hareket:** yavaş harf harf giriş, kıl çizgi açılışı, üstünden geçen tek altın parıltı, köşelerde küçük elmaslar. Oyun/çizgi film havası yok, hızlı geçiş yok.
- **Güvenli alan (9:16):** kartlar y 256 ile 1997 arasında (1440×2560 birimde), altyazı tabanı 1935. Yüz üstteyken kartı `"y": 1440` ile alta al; ürün/ekran gösteren çekimde ince `etiket` kullan.

## Veri (`veri.json`)
- `kancalar` A/B/C + `kancaSecim`: ilk ~2 sn başlık (`ust` büyük harf etiket, `s1` italik satır, `s2` altın satır). `t0` negatif verilirse ilk karede başlık hazır görünür.
- `ogeler`: `alinti` (söz kartı, `imza`), `baslik` (kısa ara başlık), `kural` (Roma rakamlı kart; `alt` alt satır ya da `kelimeler` [[zaman, KELİME], ...] sözle senkron), `isim` (ad kartı), `etiket` (ince hap). Hepsinde `t0`, `t1`, isteğe bağlı `y`.
- `altyazi`: [[başlangıç, bitiş, metin], ...]; `gizle`: altyazının saklanacağı aralıklar (ör. söz kartı ekrandayken).
- `son`: kaynak bitince (`t0`) son kare bulanıklaşır, `foto` altın halkayla açılır, altında küpe çizgisi + `alinti` + `imza`; `cta` anında `marka`, `markaAlt`, `takip`, `takipAlt` kartı. Takip kartı stilin sabit parçasıdır (Atilla, 2026-11-19), en az 2 sn kalır. `sure` = kaynak + ~6,5 sn.
- Örnek: `ornek/veri.de.json`. Görsel yolları veri.json'un klasörüne göre çözülür.

## Kullanım
```bash
python3 aurenza.py denetle veri.json
python3 aurenza.py son-kare kaynak.mp4 son.jpg          # veri.json'ın yanına
python3 aurenza.py kareler veri.json fr --kanca C       # 6 paralel parça, 41 sn ≈ 5 dk
python3 aurenza.py bindir kaynak.mp4 fr veri.json cikti.mp4 --boyut 1440x2560
python3 aurenza.py srt veri.json altyazi.srt
node kare.js veri.json kareler 1.5 12 37.9              # önizleme için tek kareler
```
Bindirmede `-reinit_filter 0` ve `format=rgba` gerekir: finalin opak PNG'leri RGB kaydedildiği için yoksa geçişte siyah kare çıkar (`bindir` bunu yapar).

## Sipariş akışı
Konuşmayı sherpa-onnx whisper ile metne dök (isimleri Atilla'ya doğrulat), 2–3 kanca + stil karelerini tek sayfada göster, Instagram metni + tam 5 hashtag (Berlin, Kuyumcu, Kreuzberg gibi) ve takip çağrısı ekle, seçimden sonra kaynağın formatında render et. Müşteri dosyaları repoya girmez; ilk iş `/mnt/project-files/aurenza/ferhat-31/` (DEVIR.md).

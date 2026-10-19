# platform/ortak

Şablonların ortak adımları. Bir düzeltme burada yapılınca onu kullanan bütün şablonlara gider.

| Modül | Ne yapar |
| --- | --- |
| `mastering.py` | EBU R128 ölçümü ve sosyal video mastering'i: 16 kHz alçak geçiren, -14 LUFS, tepe sınırlayıcı, 48 kHz. Çıktının gerçek tepesi -2 dBTP'yi aşarsa sınırı indirip yeniden yazar; böylece AAC'den sonra teslim dosyası -1 dBTP altında kalır. |
| `formatlar.py` | Tek format tablosu (9x16, 16x9, 1x1, 4x5). `9:16` ve `9x16` yazımlarının ikisini de kabul eder; `coz()` komut satırı → senaryo `format` alanı → varsayılan sırasıyla seçer, `ikisi` 9x16 + 16x9 demektir. |
| `akis.py` | Çıktı klasörü, seslendirme (varsayılan Piper; senaryo `seslendirme.saglayici: "elevenlabs"` derse ElevenLabs), ses + görüntü birleştirme. Birleştirme sonunda kalite kapısını çalıştırır. |
| `kalite.py` | Kalite kapısı (aşağıda). |
| `sfx.py` | Ortak efekt ve vurmalılar: hi-hat (metalik osilatör), shaker, zil, clap, kick, whoosh (kayan rezonanslı süzgeç), riser, kâğıt hışırtısı (kısa taneler), parıltı (tiz çınlamalar), çıtırtı; pembe/kahverengi gürültü, bant ve kayan süzgeç. Ham beyaz gürültü kullanılmaz: tekdüze cızırtı olarak duyuluyordu (Atilla, 2026-10-19). Her vuruş küçük rastgele farkla çalar. `gurultu_analizi` kalite kapısının hışırtı ölçüsüdür. Bütün şablonların efektleri buradan gelir. |
| `devir.py` | İşin teslim klasörüne kısa `DEVIR.md` yazar: teslim edilen videolar ve kalite sonuçları, senaryolar ve yeniden üretme komutları, seslendirme, kararlar. Revizyon thread'i eski konuşma yerine bunu okur. Kullanım: `devir.py <klasör> --not "karar"`. |
| `onizleme.py` | Render'dan önce önizleme: her stil için birkaç kare tek sayfada, banding ve netlik ölçüsüyle. 4 stil yaklaşık 15 sn. Kullanım: `onizleme.py kolaj=a.json origami=b.json -o onizleme.png`. |
| `sayfa.py` | Sayfa kapısı: panel, açılış sayfası ya da HTML teslimini gerçek tarayıcıda telefon ve masaüstü ekranında açıp kontrol eder (aşağıda). |

Şablon tarafında kullanım (platform bir Python paketi olamadığı için yol eklenir):

```python
sys.path.insert(0, str(BURADA.parents[1] / "ortak"))
import akis, mastering
from formatlar import FORMATLAR
```

Taşınan şablonlar: kinetik, origami, tek çizgi, minyatür (`akis`, `mastering`). Diğer şablonlar kendi birleştirmesini ve mastering kopyasını kullanıyor ama render sonunda kalite kapısını onlar da çalıştırır (`kalite.render_sonrasi`). Efektlerin hepsi `sfx.py`'den gelir.

## Kalite kapısı

```sh
python3 platform/ortak/kalite.py video.mp4 [başka.mp4 ...] [--sessiz] [--kontakt kontakt.png] [--json]
```

Her render sonunda kendiliğinden çalışır (`akis.birlestir`), videonun yanına `<ad>.kalite.json` ve `<ad>.kontakt.png` yazar. Render'ı durdurmaz; sonucu basar. Kapatmak için `STUDYO_KALITE=0`.

| Kontrol | Hata | Uyarı |
| --- | --- | --- |
| Çözünürlük, kare hızı | kısa kenar < 1080, < 24 fps | standart dışı boyut, h264/yuv420p değil |
| Ses | ses akışı yok (`--sessiz` ile serbest), tamamen sessiz | ses ve görüntü süresi farklı |
| Ses yüksekliği | -14 LUFS'tan 3 LU'dan fazla sapma, gerçek tepe > 0 dBTP | 1 LU'dan fazla sapma, gerçek tepe > -1 dBTP |
| Hışırtı | 2 sn'den uzun kesintisiz tiz cızırtı | 1 sn'den uzun |
| Siyah, donma, sessizlik | | videonun ortasında siyah kare ya da 1 sn'den uzun sessizlik; 4 sn'den uzun donma (sondaki logo tutuşu sayılmaz) |
| Banding | degrade zeminde basamaklanan karolar ≥ %12 | ≥ %3 |
| Netlik | | kenarlar yumuşak: görüntü küçük çizilip büyütülmüş olabilir |

Banding ölçüsü: görüntü 64 px karolara bölünür; tonu yumuşak değişen (2–16 kod değeri), en az iki tonu geniş düz şeritler hâlinde taşıyan ve komşu pikselleri %90'dan fazla aynı olan karo basamaklı sayılır. Titreşimli (dither) degrade, düz dolgu ve dokulu yüzey sayılmaz; çok açık karolar da (kâğıt dokusu, yumuşak gölge) sayılmaz. Ayar gerçek işlerle yapıldı: The Leaf TV döngüsünün ilk sürümü (koyu bulanık zemin) %43 ile kalır, açık sürümü geçer; şablon örnekleri geçer; yarım çözünürlükten büyütülmüş kinetik "netlik" uyarısı alır.

Hışırtı ölçüsü (`sfx.gurultu_analizi`): ~0.1 sn'lik pencerelerde 2.5–8 kHz bandı gürültü gibi düz (spektral düzlük > 0.5) ve toplamın −15 dB'inden yüksekse an cızırtılı sayılır; ölçü en uzun kesintisiz cızırtıdır (konuşmadaki s/ş 0.2 sn'yi geçmez). LÉVA serumunun ilk sürümü (3.4 sn bant gürültüsü "parıltı") 2.7 sn ile kalır, yeni sesi geçer. `testler/test_sfx.py` şablonların müzik + efekt izini de ölçer: tiz cızırtı payı sınırın üstüne çıkan değişiklik CI'da düşer.

Kontakt sayfası 8 örnek kare gösterir. Dikey videoda Reels / TikTok / Shorts arayüzünün kapattığı yaklaşık bölgeler (üst %10, alt %22, sağ %13, sol %4) kırmızı taralıdır: yazının oraya düşüp düşmediğine insan bakar, çünkü yazıyı çizimden makine güvenilir ayıramıyor.

## Sayfa kapısı

```sh
python3 platform/ortak/sayfa.py panel.html [https://… ...] [--kontakt k.png] [--bekle 800] [--ekran telefon] [--json]
```

Videodaki kalite kapısının web karşılığı. Sayfa Chromium'da (Playwright) iki ekranda açılır: telefon 390×844 @3x ve masaüstü 1440×900 @2x, açık tema. Dosyanın yanına `<ad>.sayfa.json` ve `<ad>.sayfa.png` yazar: iki ekranın tam sayfa görüntüsü yan yana, sorunlu öğe kırmızı (hata) ya da turuncu kesikli (uyarı) çerçeveli. Claude sayfayı tek tek ekran görüntüsüyle gezmez, bu tek görüntüye ve rapora bakar.

| Kontrol | Hata | Uyarı |
| --- | --- | --- |
| Taşma | sayfa yana kayıyor; öğe ekranın dışına taşıyor (kaydırılan bir kabın içindekiler sayılmaz) | |
| Kesilen yazı | | yazı kutusuna sığmıyor, kabı kesiyor ya da üç noktayla kısaltılmış |
| Kontrast | 2:1'in altı | WCAG AA altı (normal yazı 4.5:1, büyük yazı 3:1); degrade ya da görsel zeminde ölçülmez |
| Telefon | | 12 px altı yazı; kısa kenarı 44 px altı düğme ya da bağlantı (yazı içi bağlantı sayılmaz) |
| Görsel | yüklenemeyen (kırık) görsel | doğal genişliği ekrandaki genişliğin 1,5 katından az: telefonda bulanık görünür |
| Konsol, ağ | | JavaScript hatası; yüklenemeyen dosya (bulut oturumunda ağ izni kapalı olabilir) |

Stüdyo panelinde denendi (2026-10-18): taşma yok; uyarı olarak turuncu not yazısı 3.9:1 kontrastta, sekme düğmeleri telefonda 43 px.

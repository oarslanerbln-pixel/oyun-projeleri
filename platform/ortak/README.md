# platform/ortak

Şablonların ortak adımları. Bir düzeltme burada yapılınca onu kullanan bütün şablonlara gider.

| Modül | Ne yapar |
| --- | --- |
| `mastering.py` | EBU R128 ölçümü ve sosyal video mastering'i: 16 kHz alçak geçiren, -14 LUFS, tepe sınırlayıcı, 48 kHz. Çıktının gerçek tepesi -2 dBTP'yi aşarsa sınırı indirip yeniden yazar; böylece AAC'den sonra teslim dosyası -1 dBTP altında kalır. |
| `formatlar.py` | Tek format tablosu (9x16, 16x9, 1x1, 4x5). `9:16` ve `9x16` yazımlarının ikisini de kabul eder; `coz()` komut satırı → senaryo `format` alanı → varsayılan sırasıyla seçer, `ikisi` 9x16 + 16x9 demektir. |
| `akis.py` | Çıktı klasörü, seslendirme (`otomatik`: ElevenLabs anahtarı varsa ElevenLabs, yoksa Piper), ses + görüntü birleştirme. Birleştirme sonunda kalite kapısını çalıştırır. |
| `kalite.py` | Kalite kapısı (aşağıda). |

Şablon tarafında kullanım (platform bir Python paketi olamadığı için yol eklenir):

```python
sys.path.insert(0, str(BURADA.parents[1] / "ortak"))
import akis, mastering
from formatlar import FORMATLAR
```

Taşınan şablonlar: kinetik, origami, tek çizgi, minyatür (çıktıları taşımadan önceki hâliyle bayt bayt aynı; tek fark gerçek tepe koruması). Kolaj, stil, mekan, bumper ve açık PR'lardaki şablonlar o PR'lar birleşince taşınır.

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
| Siyah, donma, sessizlik | | videonun ortasında siyah kare ya da 1 sn'den uzun sessizlik; 4 sn'den uzun donma (sondaki logo tutuşu sayılmaz) |
| Banding | degrade zeminde basamaklanan karolar ≥ %12 | ≥ %3 |
| Netlik | | kenarlar yumuşak: görüntü küçük çizilip büyütülmüş olabilir |

Banding ölçüsü: görüntü 64 px karolara bölünür; tonu yumuşak değişen (2–16 kod değeri), en az iki tonu geniş düz şeritler hâlinde taşıyan ve komşu pikselleri %90'dan fazla aynı olan karo basamaklı sayılır. Titreşimli (dither) degrade, düz dolgu ve dokulu yüzey sayılmaz; çok açık karolar da (kâğıt dokusu, yumuşak gölge) sayılmaz. Ayar gerçek işlerle yapıldı: The Leaf TV döngüsünün ilk sürümü (koyu bulanık zemin) %43 ile kalır, açık sürümü geçer; şablon örnekleri geçer; yarım çözünürlükten büyütülmüş kinetik "netlik" uyarısı alır.

Kontakt sayfası 8 örnek kare gösterir. Dikey videoda Reels / TikTok / Shorts arayüzünün kapattığı yaklaşık bölgeler (üst %10, alt %22, sağ %13, sol %4) kırmızı taralıdır: yazının oraya düşüp düşmediğine insan bakar, çünkü yazıyı çizimden makine güvenilir ayıramıyor.

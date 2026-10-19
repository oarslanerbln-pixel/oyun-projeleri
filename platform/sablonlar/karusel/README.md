# platform/sablonlar/karusel

Instagram carousel gönderisi: gerçek fotoğraflar + `marka.json` → 2–10 slayt, 4:5 (1080×1350, varsayılan) ya da 1:1 PNG. Renk, yazı tipi ve logo [`marka.json`](../../marka/README.md)'dan, metin ve fotoğraflar senaryodan gelir. Slaytlar durağan olduğu için önizleme ürünün kendisidir; render ve ses yoktur, bir gönderi birkaç saniyede çıkar.

```sh
K=platform/sablonlar/karusel/karusel.py
python3 $K denetle ornekler/demli-kahve/karusel.json
python3 $K uret    ornekler/demli-kahve/karusel.json -o cikti/        # slaytlar + <kimlik>.kontakt.png + <kimlik>.kalite.json
python3 $K kare    ornekler/demli-kahve/karusel.json --an 1 3          # yalnız 1. ve 3. slayt
python3 platform/ortak/onizleme.py karusel=ornekler/demli-kahve/karusel.json   # bütün slaytlar tek sayfada
```

Bütün slaytlarda aynı alt şerit: sayfa sayacı (`02 / 06`) ve sağ kenardan taşan ince vurgu çizgisi + ok; kaydırmaya çağırır ve slaytları birbirine bağlar. Son slaytta çizgi kalple biter. Zeminler düzdür (degrade yalnız fotoğraf üstündeki okunurluk geçişinde ve titreşimli).

## Senaryo

```json
{
  "kimlik": "le-mariage-karusel", "stil": "karusel", "dil": "de", "format": "4:5", "marka": "marka.json",
  "slaytlar": [
    { "tur": "kapak",   "foto": "foto/neon-wand.jpg", "odak": [0.5, 0.4], "ust": "Hochzeit · Henna", "baslik": "Euer Fest beginnt hier", "alt": "Wischt durch →" },
    { "tur": "foto",    "foto": "foto/festsaal.jpg", "ust": "Festsaal", "baslik": "Raum für eure Gäste", "metin": "Lange Tafeln, Blumen und Lichtdesign." },
    { "tur": "liste",   "ust": "Was euch erwartet", "baslik": "Alles für euren Tag", "maddeler": ["Festsaal", "Brautbühne", "Bar"] },
    { "tur": "kapanis", "ust": "Eure Location", "baslik": "Jetzt Termin sichern", "satirlar": ["Adresse", "@hesap"], "cagri": "Jetzt anfragen" }
  ]
}
```

Üç tasarım (`"tasarim"`, varsayılan `klasik`); metin ve fotoğraflar aynı kalır, yalnız bu alan değişir:

| `tasarim` | Görünüm |
| --- | --- |
| `klasik` | koyu `ana` zemin; fotoğraf üstte tam genişlik, altında sola yaslı yazı |
| `kemer` | krem (`ana-ustu`) zemin, koyu yazı; kapak ve foto slaytlarında fotoğraf kemer (pencere) biçiminde, ince altın kemer çizgisi, ortalı yazı. Vurgu küçük yazıda okunsun diye koyulaştırılır |
| `bordo` | `renk.bordo` (yoksa `ana`) zemin; fotoğraf içe alınmış, sağ alta kaydırılmış ince altın çerçeve, foto slaytında sağda büyük çizgi numara |

| Slayt (`tur`) | Görünüm |
| --- | --- |
| `kapak` | tam kadraj fotoğraf (yoksa büyük logo), altta koyu geçiş üstünde etiket, başlık (önce tek satır, sığmazsa iki), alt satır |
| `foto` | fotoğraf üstte tam genişlik, kendi oranında (en çok yüksekliğin %58'i), vurgu çizgisi; altında sıra numarası + etiket, başlık, en çok 4 satır metin |
| `liste` | ince çerçeve, etiket, başlık, kalp işaretli en çok 6 madde; `foto` verilirse koyu bulanık zemin (banding verirse kapı yakalar) |
| `kapanis` | logo, etiket, başlık, iletişim satırları, vurgu renginde çağrı düğmesi |

`dil` büyük harf kuralını seçer (`tr`: i → İ; diğerleri: ß → SS). Yollar senaryonun klasörüne, sonra depo köküne göre çözülür.

## Denetimler ve kalite

| Denetim | Düzey |
| --- | --- |
| marka.json HATA veriyor; format 4:5 / 1:1 değil; slayt sayısı 2–10 dışında; tür bilinmiyor; tanımsız alan | HATA |
| `foto` slaytında foto yok; fotoğraf dosyası yok ya da PNG/JPG/WebP değil; başlık yok; `liste`te madde yok | HATA |
| Karakter sınırı: `ust` 32, `baslik` 44, `alt` 60, `metin` 160, madde 38, satır 40, `cagri` 28; en çok 6 madde/satır | HATA |
| Başlık iki satıra, metin ayrılan satırlara sığmıyor (render sırasında) | HATA |
| Son slayt `kapanis` değil | UYARI |
| Kalite: slaytta banding (kapının eşikleri); fotoğraf kendi çözünürlüğünün 1,25 katından fazla büyütülmüş | HATA / UYARI |

Gerekenler stil şablonuyla aynı: `pip install skia-python numpy pillow fonttools`.

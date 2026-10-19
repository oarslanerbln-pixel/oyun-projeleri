# platform/sablonlar/mekan

Gerçek ürün fotoğraflarıyla iki kullanım: mekândaki ekranda dönen **TV vitrini** ve kısa **Reel reklamı**. Renk, yazı tipi ve logo [`marka.json`](../../marka/README.md)'dan, metin ve fotoğraflar senaryodan gelir. Görüntü ve müzik kodla üretilir; ücretli servis gerekmez.

| Varyant | Biçim (varsayılan) | Akış |
| --- | --- | --- |
| `tv` | 16:9, kesintisiz döngü | Düz marka zemini (`"tema": "koyu"` varsayılan, loş mekân için; `"acik"` krem zemin, fotoğraflar gölgeli kartta), fotoğraf paneli yavaş yakınlaşır, sahneler 1,6 sn'de yumuşakça birbirine geçer, yazılar sırayla belirip söner. Son kare ilk kareye birebir bağlanır, müzik döngü noktasında kesilmez. Müzikli ve sessiz (`-sessiz.mp4`) iki dosya; yanıp sönme, hızlı kesme yok. Varsayılan ses -16 LUFS (ortam müziği). |
| `reel` | 9:16, en çok 60 sn | Fotoğraf genişliğe oturur, altında düz zeminde yazı, sahneler ritimle alttan iterek gelir, başlık kelime kelime belirir, müzik ilk geçişte ritme girer, sonda marka kartı. İsteğe bağlı seslendirme (müzik konuşmanın ~8 dB altında), -14 LUFS. |

```sh
S=platform/sablonlar/stil/stil.py
python3 $S denetle senaryo.json --stil mekan
python3 $S kare    senaryo.json --stil mekan --an 4 13 22          # önizleme PNG
python3 $S uret    senaryo.json --stil mekan                       # Reel'de seslendirme yoksa önce üretir
python3 platform/sablonlar/mekan/mekan.py render senaryo.json --olcek 0.25   # doğrudan da çalışır
```

45 sn'lik bir TV döngüsü 1080p'de yaklaşık 4 dakikada, 15 sn'lik Reel yaklaşık 1,5 dakikada çıkar.

## Senaryo

```json
{
  "kimlik": "the-leaf-tv", "stil": "mekan", "varyant": "tv", "dil": "de", "format": "16:9",
  "marka": "marka.json",
  "sahneler": [
    { "tur": "marka", "sure": 9, "foto": "foto/marka-gorseli.jpg", "ust": "Willkommen", "baslik": "The Leaf Berlin", "alt": "Lounge · Fancy Drinks · Chef Kitchen" },
    { "tur": "urun",  "sure": 9, "foto": "foto/tavuk-makarna.png", "odak": [0.45, 0.55], "ust": "Aus unserer Chef Kitchen", "baslik": "Crispy Chicken Pasta", "alt": "…" },
    { "tur": "bilgi", "sure": 9, "baslik": "Öffnungszeiten", "satirlar": [["Sonntag – Donnerstag", "15:00 – 01:00"]], "alt": "…" }
  ]
}
```

Yollar senaryonun klasörüne, sonra depo köküne göre çözülür. `odak` fotoğrafta kadrajda kalacak nokta (0–1). `logo: [x, y, h]` (marka sahnesi) logoyu fotoğrafa oranla o noktaya çizer ve fotoğrafla birlikte hareket ettirir: düşük çözünürlüklü bir marka görselinde logo silinip yerine keskin logo konur. `dil` büyük harf kuralını seçer (`tr`: i → İ; diğerleri: ß → SS); varsayılan `tr`. Reel seslendirmesi `"seslendirme": {"ses": "thorsten", "satirlar": [{"id", "t", "metin"}]}` ile verilir. Varsayılan ElevenLabs: `ses` bir voice_id ya da Piper adı olabilir; Piper adı (`thorsten`, `kerstin`) dili ve cinsiyeti seçer ve ElevenLabs yoksa yedek ses olur.

| Sahne (`tur`) | TV | Reel |
| --- | --- | --- |
| `marka` | marka görseli panelde (yoksa logo) + karşılama yazısı | kapanış: marka görseli (yoksa logo) ve açık bilgi kartı (`ust`, `baslik`, `alt`) |
| `urun` | fotoğraf paneli sırayla sağda/solda, yanında `ust` (küçük, vurgu), `baslik`, ince çizgi, `alt` | tam kadraj fotoğraf, hap etiket, kelime kelime başlık |
| `uclu` | — | açılış: üç fotoğraf uzun kenar boyunca bant halinde vuruşlarla gelir, üstünde soru (`fotolar`, `baslik`) |
| `bilgi` | ortalanmış kart: işaret, `ust`, `baslik`, iki sütunlu `satirlar` (gün, saat), `alt`; `foto` verilirse koyu bulanık zemin | — |

| marka.json | Vitrinde |
| --- | --- |
| `renk.ana` / `ana-ustu` | koyu sahne zemini / üstündeki yazı |
| `renk.vurgu` | üst etiket, çizgi, küçük işaret, ışık noktaları |
| `renk.zemin` / `metin` / `logo` | Reel kapanış kartı ve logosu |
| `yazi.baslik` / `govde` | başlıklar / gövde ve etiketler (Google Fonts'tan indirilir) |
| `logo.dosya` | saydam PNG; tek renge boyanır (koyu zeminde açık) |
| `logo.isaret` | isteğe bağlı, yazısız işaret; küçük imzada kullanılır |
| `hareket.egri` | çizgi ve etiket girişleri |

Netlik: fotoğraflar kendi çözünürlüklerine yakın gösterilir (Reel'de genişliğe oturur, en çok %5 yakınlaşma). Zeminler düzdür; yumuşak radyal ışık 8 bit videoda dairesel basamak yaptığı için kullanılmaz.

## Denetimler

**HATA** üretimi durdurur, **UYARI** durdurmaz.

| Denetim | Düzey |
| --- | --- |
| marka.json HATA veriyor; varyant, tema ya da sahne türü bilinmiyor; tanımsız alan | HATA |
| Fotoğraf yok ya da PNG/JPG/WebP değil; `urun`da foto, `uclu`da üç foto eksik | HATA |
| Karakter sınırı: `ust` 28, `baslik` 28, `alt` 48, bilgi satırı 40 | HATA |
| TV'de seslendirme (mekânda ses çoğu zaman kapalı, döngüde tekrar eder) | HATA |
| Reel 60 sn'den uzun; seslendirme videodan taşıyor; `render` için seslendirme dosyası yok | HATA |
| Sahne yazı okunmayacak kadar kısa; TV döngüsü 20–120 sn dışında; satır sahnesinden taşıyor | UYARI |

Gerekenler stil şablonuyla aynı: `pip install skia-python numpy soundfile fonttools`, ffmpeg; seslendirme için `sherpa-onnx`.

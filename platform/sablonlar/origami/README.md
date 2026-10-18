# platform/sablonlar/origami

Kısa marka ve ürün videosu şablonu (6–15 sn): düz renkli kâğıt nesneler katlanarak açılır, fiyat etiketleri sallanarak iner, sahne bir kâğıt sayfanın üstüne kapanmasıyla değişir. Tek bir `origami.json` dosyasından görüntü, kâğıt efektleri, sentez müzik ve seslendirme aynı anlara kilitli üretilir. Ücretli bir servis gerekmez. Tek kare `t` anının saf fonksiyonudur (10 sn'lik 9:16 render yaklaşık 20 sn sürer).

```sh
O=platform/sablonlar/origami/origami.py
python3 $O denetle   ornekler/tuzak-fiyat-origami/origami.json
python3 $O seslendir ornekler/tuzak-fiyat-origami/origami.json          # platform/ses (Piper fahrettin); --saglayici elevenlabs --ses <id>
python3 $O kare      ornekler/tuzak-fiyat-origami/origami.json --an 1.5 5.6 --format 16x9   # önizleme PNG
python3 $O render    ornekler/tuzak-fiyat-origami/origami.json          # → cikti/<kimlik>-9x16.mp4 (--format 9x16 16x9 1x1 4x5)
```

Gerekenler: `pip install skia-python numpy soundfile` (scipy varsa efekt filtreleri hızlanır), ffmpeg ve Inter yazı tipi (Linux'ta `apt-get install libegl1 libgl1 fonts-inter`; başka bir klasör için `KINETIK_FONT_DIZINI`). `denetle` yalnız standart kütüphaneyle çalışır. Varsayılan format yalnız 9:16; ikincisi takvimde istenirse `--format` ile eklenir.

## Senaryo

```json
{
  "kimlik": "tuzak-fiyat-origami", "sure": 10, "fps": 30,
  "palet": {"zemin": "#F3ECDF", "koyu": "#22304A", "vurgu": "#E2603F", "ikinci": "#2E8A84", "ucuncu": "#EDB548", "acik": "#FFFBF3"},
  "muzik": {"bpm": 96},
  "seslendirme": {"satirlar": [{"id": "v0", "t": 0.35, "metin": "İki boy kahve. Çoğu, küçüğü seçer."}]},
  "sahneler": [
    {"tur": "vitrin", "bas": 0, "baslik": {"metin": "MENÜ", "t": 0.05}, "rozet": {"metin": "SADECE +5 ₺", "t": 5.45},
     "nesneler": [{"id": "buyuk", "tur": "kupa", "boy": 1.0, "renk": "vurgu", "ad": "BÜYÜK", "fiyat": "100 ₺", "t": 0.55, "etiket_t": 1.2, "one_t": 4.9}]},
    {"tur": "kapanis", "bas": 7.2, "gecis": "katla", "isaret": "turna", "satirlar": [{"metin": "Fiyat değil,", "t": 7.45}], "alt": "…", "alt_t": 8.95}
  ]
}
```

Bütün anlar videonun başından itibaren saniye cinsinden verilir. Bir sahne bir sonrakinin `bas` anına kadar sürer.

| Sahne (`tur`) | Zemin | Alanlar |
| --- | --- | --- |
| `vitrin` | zemin (hafif kâğıt kıvrımları) | `nesneler` (1–4, soldan sağa), `baslik` (akordeon gibi açılan koyu şerit), `rozet` (başlık bu anda dönüp arka yüzünde vurgu renginde kurdele olur; başlık yoksa kurdele kendisi açılır) |
| `kapanis` | vurgu | `isaret` (`turna`: katlanarak oluşan, kanat çırpan kâğıt turna; `yok`), `isaret_t`, `satirlar[{metin, t, renk}]`, `alt`, `alt_t` |

Nesne alanları: `id`, `tur` (`kupa`, `kutu`), `boy` (0,3–1,0), `renk` (palet rolü), `ad` ve `fiyat` (etiket), ve anlar: `t` (katlanarak açılır; sonradan gelen nesne için diğerleri kayarak yer açar), `etiket_t`, `zipla_t` (küçük zıplama), `one_t` (büyür, arkasında kâğıt yıldız açılır, konfeti, etiketi dönüp vurgu rengine geçer; tam ritim de burada girer), `sonuk_t` (zemine doğru solar; tuzak seçenek için).

Sahneye giriş geçişi (`gecis`): `katla` (sonraki sahnenin rengindeki sayfa iki kanatla kapanır: sağ kanat kenardan gelir, üstüne katlı sol kanat beyaz arka yüzüyle açılıp sola yatar, 0,6 sn), `kesme`.

Renkler rollerle verilir (`zemin`, `koyu`, `vurgu`, `ikinci`, `ucuncu`, `acik`); marka değişince yalnız palet değişir. Kâğıdın arka yüzü `acik` rengindedir.

## Görüntü

Her nesne, menteşesi üst yüzünün bir kenarında duran yüzlerden oluşur (`cizim.model_*`). Bir yüz menteşesi etrafında dönerek açılır; dik izdüşümde bu, menteşeye dik eksende `cos(açı)` ölçeğidir ve alt yüzler üst yüzün matrisini miras alır. Açı 90°'yi geçince arka yüz görünür, ışık açıyla azalır. Bütün dolgular ve gölgeler düz renktir (bant yapan gradyan ya da parlama yok); en üstte sabit, ±2–3 seviyelik bir kâğıt dokusu titreşimi kırar. Yeni bir nesne türü eklemek için `model_kupa` gibi bir yüz listesi yazmak ve `GENISLIK` ile `MODEL` sözlüklerine eklemek yeter.

## Ses

- **Müzik:** `bpm` hızında marimba arpeji, pad ve shaker sakin başlar. `muzik.dusus` anında (verilmediyse ilk `one_t`) yumuşak kick, parmak şıklatma ve yuvarlak bas girer. Katla geçişinden önce davul ve bas susar, kapanış ilk akora dönen parlak bir vuruşla açılır.
- **Efektler:** katlanma, kâğıt hışırtısı, kayma, etiket fiskesi, tık ve yumuşak darbe zaman çizelgesinden (`zaman.ses_olaylari`) üretilir.
- **Seslendirme:** `cikti/seslendirme/<id>.wav` dosyalarından okunur. Konuşma sırasında müzik yaklaşık 8 dB kısılır.
- **Master:** kinetik şablonla aynı: 16 kHz alçak geçiren, -14 LUFS, tepe sınırlayıcı.

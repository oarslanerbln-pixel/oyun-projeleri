# platform/sablonlar/risograf

Kısa video şablonu (6–15 sn): **risograf baskı**. En çok dört spot mürekkep (varsayılan sarı, floresan pembe, riso mavisi) ayrı tambur katmanlarında basılır ve çarpma (multiply) ile üst üste biner: pembe ile mavi mor, sarı ile pembe turuncu, sarı ile mavi yeşil verir. Her katman hafif kayık basılır, mürekkepte ince tanecik ve seyrek boşluklar vardır, kâğıt sıcak kırık beyaz ve hafif liflidir. Her sayfa baskı makinesinden çıkan yeni bir kâğıt gibi alttan gelir. Tek bir senaryo dosyasından görüntü, sentez müzik, makine efektleri ve seslendirme aynı anlara kilitli üretilir. Ücretli bir servis gerekmez.

```sh
T=platform/sablonlar/risograf/risograf.py
python3 $T fontlar                                                 # Archivo Black (SIL OFL) → ~/.cache/studyo/fonts
python3 $T denetle   ornekler/kucuk-aliskanliklar/risograf.json
python3 $T seslendir ornekler/kucuk-aliskanliklar/risograf.json    # platform/ses (Piper fahrettin); --saglayici elevenlabs --ses <id>
python3 $T kare      ornekler/kucuk-aliskanliklar/risograf.json --an 1.8 4.9 --format 16x9
python3 $T render    ornekler/kucuk-aliskanliklar/risograf.json    # → cikti/<kimlik>-9x16.mp4 + <kimlik>-kapak.png
```

Format verilmezse senaryonun `format` listesi kullanılır, o da yoksa yalnız `9x16` üretilir (`16x9`, `1x1`, `4x5` da var). Gerekenler: `pip install skia-python numpy scipy soundfile`, ffmpeg (Linux'ta skia için `apt-get install libegl1 libgl1`). Yazı tipi depoya girmez; başka bir klasör için `RISOGRAF_FONT_DIZINI`. `denetle` yalnız standart kütüphaneyle çalışır. Tanecik bilerek dokulu olduğu için MP4 dosyaları düz renkli şablonlardan büyüktür (10 sn 9:16 ≈ 17 MB).

## Senaryo

```json
{
  "kimlik": "ornek", "sure": 10, "fps": 30, "format": ["9x16"],
  "kagit": "#F4EFE4",
  "murekkepler": {"sari": {"renk": "#FFE14D", "kayma": [0, 0]}, "pembe": {"renk": "#FF48B0", "kayma": [5, -3]},
                  "mavi": {"renk": "#0078BF", "kayma": [-4, 4]}},
  "tanecik": {"guc": 1.0, "kaynama": 4},
  "sayfalar": [
    {"bas": 0, "ogeler": [
      {"tur": "daire", "murekkep": "sari", "t": 0.05, "giris": "yuksel", "x": 0.5, "y": 0.6, "r": 360},
      {"tur": "yazi", "murekkep": "pembe", "metin": "%1", "t": 1.3, "giris": "kay", "x": 0.5, "y": 0.4, "boy": 450, "hiza": 0.5}
    ]}
  ]
}
```

- `murekkepler`: 1–4 mürekkep, her birinin rengi ve baskı kayması (px). `baski_sirasi` verilmezse sıra tanımdaki gibidir.
- `tanecik`: `guc` (0 = temiz düz mürekkep, 1 = varsayılan doku), `kaynama` (tanecik ve kayma saniyede kaç kez değişir; 0 = sabit baskı).
- `isaretler`: köşe kayıt işaretleri ve sayfa numarası hangi mürekkeple basılsın (`{"murekkep": "mavi"}`), `false` ile kapanır.
- `sayfalar`: her sayfa bir `bas` anı ve öğe listesidir; sayfa geçişi `bas` anının çevresinde 0,5 sn sürer.

**Öğeler** sayfaya oranla yerleşir (`x`, `y`: 0–1) ve 1080x1350'lik kutuya göre ölçeklenir (9:16'da 1, 16:9'da 0,8). Her öğe tek mürekkeple basılır (`murekkep`); figür parçaları ayrı mürekkeplerdedir.

| `tur` | Ne yapar | Başlıca alanlar |
| --- | --- | --- |
| `yazi` | Archivo Black başlık; `y` taban çizgisidir | `metin`, `boy`, `hiza`, `genislik` (sayfa oranına sığdır), `giris` (`sil`, `kay`, `belir`, `pop`), `bitis_t`, `damga` |
| `sayac` | Sayıyı `t`'den `bitis_t`'ye sayar, sonda öne çıkar | `degerler: [ilk, son]`, `son_ek`, yazının alanları |
| `daire` | Düz mürekkep daire | `r`, `giris` (`yuksel`, `buyu`, `belir`), `sure`, `yay`, `buyume: {t, r, sure}` |
| `zemin` | Sayfanın altını kaplayan zemin, üstünde yarım ton geçiş | `y`, `yarim_ton` |
| `egri` | Bileşik büyüme dağı soldan sağa basılır | `bitis_t`, `baslangic`, `bitis`, `golge` (yarım ton mürekkebi), `noktalar` (ay noktaları mürekkebi) |
| `halkalar` | Dışa yayılan halkalar | `r0`, `r1`, `adet`, `aralik`, `sure` |
| `ok` | Soldan uzayan kalın ok | `x0`, `x1`, `y`, `kalinlik`, `sure` |
| `cizgi` | Yatay zemin çizgisi | `y`, `kalinlik` |
| `figur` | Geometrik yürüyen kişi | `renkler: {govde, bacak, sapka}`, `x0` → `x`, `y` (zemin), `bitis_t`, `hareket` (`yavasla`, `duz`) |
| `logo` | Marka logosu tek mürekkeple basılır (görselin alfa kanalı kalıp olur) | `yol`, `genislik`, `giris` (`pop`) |

**Format ayarı:** Her sayfa ya da öğe `"16x9": {…}` gibi bir format anahtarı taşıyabilir; o formatta oradaki alanlar geçerli olur.

Görsel kurallar şablonun içinde: degrade yok, tonlar düz mürekkep ya da yarım ton noktayla verilir; tanecik bantlaşmayı da önler. Şekil kenarları vektör ve kenar yumuşatmalıdır, doku yalnız mürekkebin içindedir.

## Ses

- **Müzik:** 80 BPM lo-fi (FM elektrikli piyano, yumuşak davul, sub bas, çan). `muzik.akorlar` dört bölümün (giriş, yükseliş, sakin, final) akor listeleridir; bölüm içinde iki vuruşta bir sıradaki akor çalar. Girişte piyano ve shaker, `muzik.yukselis` anında davul ve sub bas, sayaçtan önce yükselen çan arpeji, `muzik.sakin` anında tek uzun akor, `muzik.final` anında davul ve çanlı parlak kapanış.
- **Efektler:** sayfa geçişinde riso tamburu (gümleme, mekanik tık, kâğıt hışırtısı), büyük baskılarda tok damga ve çan (`zaman.damgalar`), büyüyen dairede pop, eğrinin ay noktalarında hafif tıklar.
- **Seslendirme:** `cikti/seslendirme/<id>.wav`. Müzik konuşmanın yaklaşık 8 dB altında durur, konuşurken 3 dB daha kısılır.
- **Master:** 16 kHz alçak geçiren, -14 LUFS, tepe sınırlayıcı.

## Örnek

`ornekler/kucuk-aliskanliklar/risograf.json`: stil testindeki 10 sn'lik "küçük alışkanlıklar" riso videosu (aynı satırlar ve anlar). Yatay formatta yazılar ve daireler `16x9` ayarlarıyla yan yana dizilir.

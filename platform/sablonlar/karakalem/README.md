# platform/sablonlar/karakalem

Kurşun kalemle çizilen karikatürlü anlatım videosu (8–20 sn): kişisel gelişim, "küçük adım büyük sonuç" türü açıklayıcı kısa içerik. Bir defter sayfasında kalem önce büyük bir hedefi (dağ) çizer, karakter ondan korkar; sonra her vuruşta bir basamak çizilir ve karakter üstüne zıplar; sonunda kamera geri çekilir ve basamakların tepelerinin zirveye çıkan bir eğri olduğu görünür, damga vurulur, başlık el yazısıyla yazılır. Grafit tonları ve tek bir vurgu rengi.

Tek senaryo dosyasından görüntü, kalem sesi, efektler, sentez müzik ve seslendirme aynı anlara kilitli üretilir: kalem bir köşeyi döndüğü an ses tıklar, karakter basamağa vuruşta iner, damga vuruşta düşer. Ücretli servis gerekmez. Her kare `t` anının saf fonksiyonudur (10 sn'lik video 9:16 + 16:9 birlikte yaklaşık 1 dakikada çıkar).

```sh
K=platform/sablonlar/karakalem/karakalem.py
python3 $K fontlar                                                   # Caveat + Permanent Marker, bir kez
python3 $K denetle   ornekler/kucuk-aliskanliklar/karakalem.json
python3 $K seslendir ornekler/kucuk-aliskanliklar/karakalem.json     # platform/ses; sağlayıcı senaryodan (varsayılan Piper fahrettin)
python3 $K kare      ornekler/kucuk-aliskanliklar/karakalem.json --an 1.0 4.2 8.6 --format 16x9   # önizleme PNG
python3 $K render    ornekler/kucuk-aliskanliklar/karakalem.json --format 9x16 16x9
```

Format verilmezse senaryonun `format` listesi kullanılır, o da yoksa yalnız `9x16` üretilir (`16x9`, `1x1`, `4x5` da var). Dikeyde söz bandı üstte, sahne altta; yatayda söz bandı solda, sahne sağda. Gerekenler: `pip install skia-python numpy soundfile fonttools`, ffmpeg (Linux'ta `apt-get install libegl1 libgl1`). `denetle` yalnız standart kütüphaneyle çalışır. Seslendirme önce `seslendir` ile üretilmezse video seslendirmesiz ve altyazısız çıkar.

Senaryo dosyasının adı bilerek `senaryo.json` değil: CI `ornekler/*/senaryo.json` dosyalarını kinetik şablonla denetliyor.

## Senaryo

```json
{
  "kimlik": "kucuk-aliskanliklar-karakalem", "sure": 10.2, "fps": 30, "format": ["9x16"],
  "palet": {"kagit": "#F7F4EC", "grafit": "#34343A", "vurgu": "#E0703E"},
  "karakter": {"sac": "daginik", "sac_rengi": "#4A4A52", "gozluk": true, "ten": "#F3EEE4", "kazak": "#D8D5CE", "pantolon": "#4A4A52"},
  "muzik": {"bpm": 90},
  "seslendirme": {"saglayici": "piper", "vurgulu": ["yüzde", "otuz", "yedi", "kat"],
                  "satirlar": [{"id": "v0", "t": 0.45, "metin": "Büyük hedefler göz korkutur."}]},
  "sahneler": [
    {"tur": "hedef", "bas": 0},
    {"tur": "adimlar", "bas": 2.967, "adet": 5, "buyume": 1.62, "etiket": "+%1"},
    {"tur": "sonuc", "bas": 6.967, "damga": {"metin": "37 kat", "alt": "1 yılda", "t": 8.3},
     "baslik": {"metin": "Küçük alışkanlıkların gücü", "t": 8.633}}
  ]
}
```

Hikâye her zaman üç sahnedir ve bu sırayla gelir:

| Sahne | Ne olur | Alanlar |
| --- | --- | --- |
| `hedef` | Kamera kalemin ucunda; dağ çizilir, kar ve gölge eklenir, sonra kamera geri çekilip endişeli karakteri gösterir. En az 2,7 sn. | `bas` (0) |
| `adimlar` | Kamera karaktere yaklaşır. `bas`'tan sonraki her vuruşta bir basamak biter ve karakter üstüne iner; her basamak bir öncekinden `buyume` kat yüksektir. İnişte `etiket` havalanır. | `bas`, `adet` (3–8), `buyume` (1,1–2,2), `etiket` |
| `sonuc` | Kamera geri çekilir; vurgu renginde noktalı eğri basamakların köşelerinden zirveye çıkar. `damga` vuruşla düşer (müzik bir an susar, kamera içeri vurur), `baslik` el yazısıyla yazılır. | `bas`, `damga {metin, alt, t}`, `baslik {metin, t}` |

Bütün anlar videonun başından saniyedir. Basamaklar eğriyle zirveye tam oturacak şekilde ölçeklenir, adet ve büyüme ne olursa olsun. `denetle` sahne sırasını, sürelerin yetip yetmediğini, renkleri ve (seslendirme üretildiyse) satırların birbirine taşıp taşmadığını kontrol eder.

**Karakter:** `sac` (`daginik`, `kisa`, `kel`), `sac_rengi`, `gozluk` (true/false), `ten`, `kazak`, `pantolon`. Kocaman kafa, küçük gövde, iri burun; cebindeki kalem vurgu rengindedir. Yüz ifadesi hikâyeden gelir: hedefte endişe ve ter, zıplarken şaşkınlık, inince gülümseme, damgada kahkaha ve kollar havada.

**Altyazı:** seslendirme satırları söylendikçe kelime kelime koyulaşır (her satırın süresi hecelere bölünür). Rakam ya da `%` içeren kelimeler ve `seslendirme.vurgulu` listesindekiler vurgu rengindedir.

Görsel kurallar şablonun içinde: kâğıt düz renktir, üstüne kalıcı lif dokusu ve saniyede 12 kez değişen ince gren bindirilir (radyal gradyan, vinyet ya da parlama yok, bantlaşma olmaz). Çizgiler elle çizilmiş animasyondaki gibi saniyede 12 kez hafifçe kaynar.

## Ses

- **Kalem:** Her çizginin sesi o anki kalem hızından üretilir: kâğıdın dişi (5 ms'de bir değişen pürüz), hızlandıkça parlaklaşan grafit sürtünmesi; kalem keskin bir köşeyi döndüğü an küçük bir tık. Gölge taraması saniyede ~12 ileri-geri vuruştur, başlık yazılırken de kalem duyulur.
- **Kamera ve olaylar:** Geri çekilme ve yaklaşmada hava sesi; her inişte yükselen marimba notası, tok bir "tum" ve pop; eğri çizilirken yükselen e-piyano; damgada tok vuruş, alt bas, kâğıt hışırtısı ve müzik kutusu akoru.
- **Müzik:** 90 BPM lo-fi; e-piyano akorları (varsayılan Fmaj7–Em7–Dm7–Cmaj7, `muzik.akorlar` ile değişir) ve pad baştan, davul ve bas basamaklarla girer, damgadan hemen önce bir nefeslik sessizlik, hafif plak hışırtısı.
- **Seslendirme:** `cikti/seslendirme/<id>.wav` (ortak `platform/ses` adımı). Sağlayıcı video başına seçilir: varsayılan ücretsiz Piper tr_TR "fahrettin"; öne çıkan işlerde senaryoya `"saglayici": "elevenlabs", "ses": "<voice_id>"` yazılır (ELEVENLABS_API_KEY gerekir, kredi harcar). Komut satırındaki `--saglayici` / `--ses` senaryoyu ezer. Müzik konuşmanın yaklaşık 8 dB altında durur, konuşurken 3 dB daha kısılır.
- **Master:** 16 kHz alçak geçiren, -14 LUFS, tepe sınırlayıcı (diğer şablonlarla aynı zincir).

## Örnek: Küçük alışkanlıkların gücü

`ornekler/kucuk-aliskanliklar/karakalem.json`: 10 sn. Her gün %1 iyileşmek bir yılda 1,01³⁶⁵ ≈ 37,8 kat eder ("37 kat"). Video önce korkutan büyük hedefi gösterir, sonra çözümü adım adım (her gün +%1), sonra bileşik büyümeyi tek bir görüntüde: basamakların tepeleri üstel bir eğridir ve zirveye varır.

# platform/sablonlar/minyatur

Osmanlı minyatürü dilinde kısa marka videosu (lokanta, kafe, kahvehane, mekân; varsayılan 10 sn, 9:16). Altın gök, tezhipli çerçeve, düz perspektifli bir avlu: köşk, servi ve laleli bahçe, müzisyen sekisi, sinilerin etrafında minderler. Tek bir `minyatur.json` dosyasından görüntü, efekt, rast makamında sentez müzik ve seslendirme aynı anlara kilitli üretilir. Ücretli bir servis gerekmez. Her kare `t` anının saf fonksiyonudur (10 sn'lik 9:16 render yaklaşık 30 sn sürer).

Anlatının omurgası **doluluk**tur (0–1). Boş minderler sahne sahne dolar; aynı masaya oturacak misafirler (dostlar) sokaktan birlikte gelir, kapıdan girer, halı yolundan yürüyüp yerlerine oturur. Gece çökebilir, kapıda sıra oluşabilir, video şemse (madalyon) içinde marka adıyla kapanır. Böylece sosyal kanıt ("herkes buraya geliyor") ekrana tek bir sayı yazmadan gösterilir.

```sh
M=platform/sablonlar/minyatur/minyatur.py
python3 $M denetle   ornekler/lale-sofrasi/minyatur.json
python3 $M seslendir ornekler/lale-sofrasi/minyatur.json             # platform/ses (Piper fahrettin); --saglayici elevenlabs --ses <id>
python3 $M kare      ornekler/lale-sofrasi/minyatur.json --an 3.4 7.4 --format 16:9   # önizleme PNG
python3 $M uret      ornekler/lale-sofrasi/minyatur.json             # seslendirme eksikse üretir → cikti/<kimlik>-9x16.mp4
```

Gerekenler: `pip install skia-python numpy soundfile` (Linux'ta `apt-get install libegl1 libgl1`), ffmpeg. Yazı tipleri (Cinzel Decorative, Cormorant SC; SIL OFL) ilk kullanımda Google Fonts deposundan `~/.cache/studyo/fontlar` klasörüne indirilir, başka bir klasör için `MINYATUR_FONT_DIZINI`. Depoya konmaz, çünkü depo ikili dosyaları LFS'e gönderir. `denetle` yalnız standart kütüphaneyle çalışır.

## Senaryo

```json
{
  "kimlik": "lale-sofrasi-minyatur", "sure": 10, "format": "9:16",
  "marka": {"ad": "Lale Sofrası", "alt": "Lokanta", "cagri": "Yerinizi ayırtın"},
  "mekan": {"ikram": "yemek"},
  "sahneler": [
    {"tur": "acilis", "bas": 0, "doluluk": 0.09},
    {"tur": "avlu", "bas": 2.3, "doluluk": 0.45},
    {"tur": "avlu", "bas": 5.2, "doluluk": 1.0, "gece": true, "kuyruk": 5, "kartus": "Her akşam dolu"},
    {"tur": "kapanis", "bas": 7.8}
  ],
  "seslendirme": {"satirlar": [{"id": "v0", "t": 0.5, "metin": "Bu sofraya bir kez oturan,"}]},
  "muzik": {"bpm": 96}
}
```

| Sahne (`tur`) | Ne olur | Alanlar |
| --- | --- | --- |
| `acilis` (ilk sahne) | Çerçevenin cetvel çizgileri köşelerden uzar, boya kâğıda oturur, köşk yükselir, masalar sırayla belirir | `doluluk` (başlangıçta oturanlar) |
| `avlu` | Doluluk önceki değerden hedefe çıkar, yeni misafirler masa masa gelir | `doluluk`, `gece` (gök lacivertleşir, yıldız ve hilal çıkar, kemerler yanar), `kuyruk` (0–8, kapıda sıra), `kartus` (zirvedeki tek cümle, en çok 22 karakter) |
| `kapanis` | Şemse açılır: lale amblemi, marka adı, alt satır; altında kırmızı çağrı şeridi; çevrede pırıltılar | `marka.ad`, `marka.alt`, `marka.cagri` |

`mekan.ikram`: `yemek` (pilav, kebap, salata kâseleri) ya da `kahve` (fincan ve ince belli çay bardakları). `tohum` değişirse misafirlerin kıyafeti, başlığı ve geliş sırası değişir. Ekranda az yazı ilkesi gereği yazı yalnız kartuşta ve kapanışta çıkar.

## Görsel kurallar

- Bütün yüzeyler tek renk; degrade, radyal ışık ya da parlama yok (bantlaşma olmaz). Gece geçişi bile göğün tek rengini değiştirir; kemerler ve pencereler hale yerine düz renkle yanar.
- Konturlar ince ve koyu kahve, kenarlar kenar yumuşatmalı. Değişmeyen katmanlar (zemin, duvar, çerçeve) bir kez kaydedilip her karede yeniden oynatılır.
- Dikey ve yatay yerleşim `Yerlesim` sınıfında; 16:9'da masalar dört sütuna yayılır, köşk küçülür.

## Ses

- **Müzik:** Sol rast (segâh ve eviç çeyrek ses yaklaşımıyla). Açılışta ney taksimi ve ud demi; ilk `avlu` sahnesinde def (sofyan usulü), kanun ezgisi ve ud basları girer; `gece`/`kuyruk` sahnesinde ezgi oktav çıkar, def dolgu vuruşları eklenir; kapanışta davul susar, kanun yukarı süzülür, sol rast akoru ve kanun tremolosu çınlar.
- **Senkron:** Defzen müzisyenin eli, müziğin def vuruşlarıyla aynı listeden (`cizim.usul`) vurur. Kalabalık uğultusu doluluk eğrisini izler; misafir oturdukça bardak şıngırtısı, kartuş ve kapanışta parmak zili duyulur.
- **Seslendirme:** `cikti/seslendirme/<id>.wav`. Konuşma müzik yatağının yaklaşık 8 dB üstünde tutulur, konuşurken müzik ayrıca yumuşakça kısılır.
- **Master:** 16 kHz alçak geçiren filtre, -14 LUFS ve tepe sınırlayıcı.

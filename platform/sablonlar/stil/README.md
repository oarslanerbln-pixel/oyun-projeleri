# platform/sablonlar/stil

Kâğıt kesik ve izometrik stilleri. [Kinetik şablonla](../kinetik/README.md) aynı `senaryo.json` dosyasını okur, böylece bir video içeriği değişmeden stil değiştirir. Seslendirme üç stilde ortaktır (`cikti/seslendirme/`). Ücretli servis gerekmez; her kare `t` anının saf fonksiyonudur.

| Stil | Görünüm | Ses |
| --- | --- | --- |
| `kagit-kesik` | Stop-motion: saniyede 12 poz, her pozda hafif titreme; kesilmiş kenarlı kâğıt parçalar, yumuşak gölge, kâğıt dokusu, kayan sayfa geçişleri | kalimba, yumuşak davul, kısık kâğıt efektleri |
| `izometrik` | Yüzen pastel ada, üç tonlu bloklar, uzun gölgeler, kamera kayması; yazılar adadaki tabelada | çan/pluck arpej, pad, tahta "tok" efektleri |

```sh
S=platform/sablonlar/stil/stil.py
python3 $S seslendir ornekler/kucuk-aliskanliklar/senaryo.json                   # platform/ses (Piper fahrettin), üç stil için bir kez
python3 $S denetle   ornekler/kucuk-aliskanliklar/senaryo.json --stil izometrik
python3 $S kare      ornekler/kucuk-aliskanliklar/senaryo.json --stil izometrik --an 1.5 4.7 --format 16x9
python3 $S render    ornekler/kucuk-aliskanliklar/senaryo.json --stil kagit-kesik   # → cikti/<kimlik>-kagit-kesik-9x16.mp4, -kapak.png
python3 $S render    ornekler/kucuk-aliskanliklar/senaryo.json --stil kinetik       # kinetik şablona iletilir
python3 $S uret      ornekler/kucuk-aliskanliklar/senaryo.json --stil izometrik --format 16:9   # tek adım: seslendirme yoksa üretir, sonra render
```

Stil, `--stil` ya da senaryodaki `"stil"` alanıyla seçilir. Çıktı H.264 + AAC, -14 LUFS. Biçim video başına seçilir: `--format 9:16 | 16:9 | 1:1 | 4:5 | ikisi`; verilmezse senaryodaki `"format"` alanı (aynı değerler ya da liste), o da yoksa yalnız 9:16. Kinetik de bu çözülen biçimle çağrılır. Hızlı prova için `render --olcek 0.25`. Bir biçimin render'ı stil başına yaklaşık yarım dakika sürer.

## Biçim: dört vuruş, 10 sn

Bu iki stilde kamera, müzik ve efektler vuruşlara kilitlidir: müzik sakin başlar, sayıda zirve yapar, karşıtlıkta sakinleşir, finalde parlar. Bu yüzden senaryo 10 sn olmalı, dört seslendirme satırı vuruş anlarında (±0,12 sn) başlamalı ve yuvasına sığmalıdır. Kinetik şablon serbest zamanlıdır; bu kalıba uyan bir senaryo üç stilde de çalışır.

| Vuruş | Seslendirme yuvası | Yazı yuvası ← kinetik sahne alanı |
| --- | --- | --- |
| 1 · kanca | 0,30–2,85 sn | `kanca` ← `buyuk-sayi.sayi` ("%1"), `kanca_alt` ← `kelimeler` ("her gün") |
| 2 · bileşik büyüme | 3,15–5,90 sn | `sayi` ← `egri`: (1+`oran`)^`gun` ("37x"), `sayac` ← `egri.gun` (365), `sayi_alt` ← `egri.alt` ("bir yıl sonra") |
| 3 · küçük/büyük | 6,15–8,15 sn | `kucuk`, `buyuk` ← `karsitlik` ("küçük adım", "büyük fark") |
| 4 · çağrı | 8,35–9,85 sn | `cagri` ← `kapanis.satirlar` ("Bugün başla.") |

Stile özel ince ayar, sahnelerden çıkanın üstüne yazar:

```json
"stiller": { "izometrik": { "metin": { "cagri": "Hadi başla!" } } }
```

## Denetimler

**HATA** üretimi durdurur, **UYARI** durdurmaz.

| Denetim | Düzey |
| --- | --- |
| Seslendirme satırı vuruş yuvasından uzun ya da vuruş anından kaymış | HATA |
| Satır sayısı 4 değil; `render` için seslendirme dosyası yok | HATA |
| Süre 10 sn değil | HATA |
| Yazı yuvası tanımsız, boş ya da karakter sınırını aşıyor (yerleşim taşar) | HATA |
| Seslendirme > 4 sözcük/sn | UYARI |

## Yeni stil eklemek

`motor.py`'deki `STILLER`'e modül adını ekleyin. Modül `from motor import *` ile başlar; `kare(cv, t, W, H)` (t'nin saf fonksiyonu, her oran), `muzik(n)`, `sfx(n)` ve `AYAR = {'kapak_t': …, 'sfx_db': …}` tanımlar, yazıları `METIN[...]`'dan okur. Skia'nın ham pikselleri BGRA'dır; `motor.video` bunu ffmpeg'e doğru bildirir.

Gerekenler: `pip install skia-python numpy soundfile fonttools`, ffmpeg (Linux'ta skia için `apt-get install libegl1 libgl1`). Yazı tipi Inter (SIL OFL 1.1, `fonts/OFL-Inter.txt`): ilk kullanımda Google Fonts deposundan indirilir, 700/800 ağırlıkları `fontTools` ile `~/.cache/studyo/fonts` altına çıkarılır (`STIL_FONT_DIZINI`). Depo ikili dosyaları LFS'e gönderdiği için yazı tipi depoya konmaz; elle konacaksa `fonts/Inter-800.ttf`.

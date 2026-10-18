# platform/sablonlar/stil

Kâğıt kesik, izometrik, hamur (claymation) ve piksel (retro oyun) stilleri. [Kinetik şablonla](../kinetik/README.md) aynı `senaryo.json` dosyasını okur, böylece bir video içeriği değişmeden stil değiştirir. Seslendirme stillerde ortaktır (`cikti/seslendirme/`). Ücretli servis gerekmez; her kare `t` anının saf fonksiyonudur.

| Stil | Görünüm | Ses |
| --- | --- | --- |
| `kagit-kesik` | Stop-motion: saniyede 12 poz, her pozda hafif titreme; kesilmiş kenarlı kâğıt parçalar, yumuşak gölge, kâğıt dokusu, kayan sayfa geçişleri | kalimba, yumuşak davul, kısık kâğıt efektleri |
| `izometrik` | Yüzen pastel ada, üç tonlu bloklar, uzun gölgeler, kamera kayması; yazılar adadaki tabelada | çan/pluck arpej, pad, tahta "tok" efektleri |
| `hamur` | Claymation: saniyede 12 poz, kaynayan konturlar, yoğrulan geçişler (top → kart), hacimli hamur parçalar, parmak izi, düz krem fon + tanecik. Metafor: damga yuvalı ilerleme kartı | marimba, pizz bas, yumuşak davul; vıcık/pıt/tok hamur efektleri |
| `piksel` | 16-bit oyun: 16 renkli palet, düşük iç çözünürlük en yakın komşuyla büyütülür, kendi bitmap fontu (Türkçe harfler dahil), basamak tırmanan kahraman, GÜN/GÜÇ/XP göstergesi, LEVEL UP, başlık ekranı. Yazılar büyük harfe çevrilir, sığmazsa küçültülür | chiptune (kare/üçgen dalga, arpej), 8-bit efektler |

```sh
S=platform/sablonlar/stil/stil.py
python3 $S seslendir ornekler/kucuk-aliskanliklar/senaryo.json                   # platform/ses (Piper fahrettin), tüm stiller için bir kez
python3 $S denetle   ornekler/kucuk-aliskanliklar/senaryo.json --stil izometrik
python3 $S kare      ornekler/kucuk-aliskanliklar/senaryo.json --stil izometrik --an 1.5 4.7 --format 16x9
python3 $S render    ornekler/kucuk-aliskanliklar/senaryo.json --stil kagit-kesik   # → cikti/<kimlik>-kagit-kesik-9x16.mp4, -kapak.png
python3 $S render    ornekler/kucuk-aliskanliklar/senaryo.json --stil kinetik       # kinetik şablona iletilir
python3 $S uret      ornekler/kucuk-aliskanliklar/senaryo.json --stil izometrik --format 16:9   # tek adım: seslendirme yoksa üretir, sonra render
python3 $S uret      ornekler/demli-kahve/sadakat-karti.json --stil hamur        # kafeler için: iki damgası basılı sadakat kartı
python3 $S uret      ornekler/demli-kahve/bumper.json --stil bumper              # 6 sn marka bumper'ı (../bumper), seslendirmesiz
python3 $S uret      tv.json --stil mekan                                        # ürün fotoğraflı mekân TV döngüsü ya da Reel (../mekan)
```

Stil, `--stil` ya da senaryodaki `"stil"` alanıyla seçilir. Çıktı H.264 + AAC, -14 LUFS. Biçim video başına seçilir: `--format 9:16 | 16:9 | 1:1 | 4:5 | ikisi`; verilmezse senaryodaki `"format"` alanı (aynı değerler ya da liste), o da yoksa yalnız 9:16. Kinetik de bu çözülen biçimle çağrılır. Hızlı prova için `render --olcek 0.25`. Bir biçimin render'ı stil başına yaklaşık yarım dakika sürer.

## Biçim: dört vuruş, 10 sn

Bu stillerde kamera, müzik ve efektler vuruşlara kilitlidir: müzik sakin başlar, sayıda zirve yapar, karşıtlıkta sakinleşir, finalde parlar. Bu yüzden senaryo 10 sn olmalı, dört seslendirme satırı vuruş anlarında (±0,12 sn) başlamalı ve yuvasına sığmalıdır. Kinetik şablon serbest zamanlıdır; bu kalıba uyan bir senaryo her stilde çalışır.

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

## Hamur: ilerleme kartı

Hamur stili dört vuruşu bir sadakat/ilerleme kartıyla anlatır: 1. vuruşta boş kart (`kanca` büyük, `kanca_alt` şerit), 2.'de kart yeniden yoğrulur, damga aleti yuvaları basar, `sayi` büyük ve `sayi_alt` şerit, 3.'de iki kart alt alta (16:9'da yan yana; `kucuk` soluk kart, `buyuk` başlamış kart), 4.'de `cagri` hamur düğme, marka imzası ve konfeti. Sadakat kartı, alışkanlık takibi, ilk adım teşviki gibi "ilerleme" mesajlarına uyar; kart `stiller.hamur` ile ayarlanır:

```json
"stiller": {"hamur": {
  "kart": {"bos": 8, "toplam": 10, "hazir": 2},
  "marka": "DEMLİ KAHVE",
  "dipnot": "bahşedilmiş ilerleme etkisi · Nunes & Drèze, 2006",
  "metin": {"sayi": "1,8x"}
}}
```

`bos`: 1. vuruştaki boş yuva sayısı, `toplam` ve `hazir`: 2. vuruştaki yuva ve önceden basılı damga sayısı (yuvalar iki satır). `dipnot` kapanışta küçük kaynak satırıdır. Yazı tipi Baloo 2 800 (SIL OFL 1.1, Türkçe harfler tam), Inter gibi ilk kullanımda indirilir ve `~/.cache/studyo/fonts` altına örneklenir. Aynı pozdaki kareler önbellekten gelir; 9:16 render'ı yaklaşık 5 dk sürer. Örnek: [`ornekler/demli-kahve/sadakat-karti.json`](../../../ornekler/demli-kahve/sadakat-karti.json).

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

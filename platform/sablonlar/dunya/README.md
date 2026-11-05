# dunya: dünya haritası motion graphic

Dönen 3D küre ya da düz atlas; kamera dünyadan bölgeye iner, ülkeler vurgulanır, rota çizilir, yerler belirir.
Jeopolitik analiz, seyahat / ülke sosyolojisi, askeri tarih ve çatışma senaryosu videoları için ortak harita katmanı.

```
python3 platform/sablonlar/dunya/dunya.py kur        # npm bağımlılıkları (node_modules repoya girmez)
python3 platform/sablonlar/dunya/dunya.py kontakt ornekler/dunya-1961/dunya.json --formatlar 16x9 9x16 -o sayfa.png
python3 platform/sablonlar/dunya/dunya.py kare  ornekler/dunya-1961/dunya.json --kaplama neon --an 2 6 10 --format 9x16 -o cikti/
python3 platform/sablonlar/dunya/dunya.py video ornekler/dunya-1961/dunya.json --kaplama kure --format 16x9 -o film.mp4
python3 platform/sablonlar/dunya/dunya.py video ... --ss 0.5 --olcek 0.5 --fps 25   # onay öncesi küçük animatik
```

## Nasıl çalışır
- **Veri:** Natural Earth 1:50m ülkeler ve kara (`world-atlas` TopoJSON, kamu malı). Yer adı arama ve mesafe
  `platform/ortak/harita.py` (TR/DE ülke adları, 7.342 şehir + nüfus).
- **Projeksiyon:** `d3-geo` + `d3-geo-projection` (ortografik küre, Equal Earth, Robinson, Natural Earth, eşdikdörtgen...).
- **Çizim:** `motor.js` başsız Chromium'da Canvas 2D ile çizer; tuval `--ss` kat büyük (kare 2, video 1.5), lanczos
  ile küçültülür. Yazı tipleri (fontsource, latin-ext: ğ ş ı) sayfaya gömülür. Her kare kendi zamanından hesaplanır
  (deterministik), video ffmpeg'e PNG akışıyla gider (x264 crf 14).
- **Zaman çizelgesi** (süreye oranla): giriş %0–24 (küre döner / kıyılar çizilir), kamera %16–50 (dünya → bölge),
  rota %44–74, noktalar %62–88, başlık %5–20.

## Gerçek arazi (kure, atlas, kagit)
`arazi.py` AWS Open Data **Terrain Tiles** (Mapzen terrarium: SRTM, GMTED, ETOPO1...) karolarından eşdikdörtgen
yükseklik + deniz derinliği çıkarır (dünya z5 8192×4096, rotanın çevresi z7 yaması), çok yönlü gölgelendirme yapar
ve kaplama dokusu üretir: kure gece mavisi kabartma, atlas sıcak kâğıt + basamaklı derinlik, kagit gerçek derinlik ve
yükseklik eşiklerinden kesik kâğıt katmanları (gölgeli). Kara maskesi Natural Earth 50m'den, vektör kıyıyla çakışır.
Küre WebGL'de çizilir (ortografik ters izdüşüm, ışık, deniz parlaması, atmosfer), vektör katmanlar üstüne biner.
İlk kullanımda ~90 MB karo indirilir (`~/.cache/studyo/arazi`); ağ yoksa vektör küreye düşer. `"arazi": false` kapatır.
Teslim künyesi: "Arazi: Mapzen Terrain Tiles (SRTM, GMTED, ETOPO1), Natural Earth".

## Kaplamalar
| ad | görsel dil |
|---|---|
| `atlas` | açık kâğıt, ince tel ağ, terrakota vurgu, Instrument Serif + Fraunces |
| `kure` | gece küresi, atmosfer ışıması, amber vurgu, Space Grotesk |
| `nokta` | kara nokta matrisi, kaynaktan yayılan dalga, sinyal turuncusu |
| `karakalem` | grafit kıyılar, tarama, kırmızı kalem vurgu, Caveat el yazısı |
| `parsomen` | eski harita: su çizgileri, rüzgâr gülü, kerte çizgileri, Cinzel + EB Garamond |
| `neon` | koyu zemin, ışıyan sınırlar, dünyaya açılan uçuş yayları |
| `kagit` | katmanlı kâğıt: derinlik bantları, gölgeli kara, yükselen ülkeler, etiket kartları |
| `izometrik` | eğik düzlem, kara levhası, yükselen ülkeler, şehir nüfus sütunları (her zaman düz) |

`"kure": false` diğerlerini düz haritaya çevirir (atlas Equal Earth, karakalem/neon Natural Earth, kagit Robinson,
parsomen eşdikdörtgen).

## Sahne (`ornekler/dunya-1961/dunya.json`)
`kaplama`, `sure`, `dil` (tr/de), `ust`/`baslik`/`altbaslik`, `rota` (yer adı ya da `{ad, konum: [boylam, enlem], etiket}`),
`vurgu` (ülke adları), `noktalar`, `sayacNot` (mesafe sayacı başlığı; `"sayac": false` kapatır), `veriNot`, `yaylar`
(neon uçuş yayı hedefleri), `bolge` (`{lon, lat, k, dx, dy}` elle kamera). Güvenli alan: 16:9 %6–8 kenar, 9:16 üst %11,
alt %23.

## Sinematik küre (`sinema/`, three.js)
Perspektif kamera ile dönen küre: gerçek arazi yükseltmesi, bulut, gece ışıkları, atmosfer saçılımı, bloom/vinyet/gren
ve yere yapışık katmanlar (ülke rolü, tarama, ok, değişen cephe hattı, menzil, rota, nabız) + ekran katmanı (etiket,
NATO tipi birlik, başlık, tarih damgası, konum çipi, lejant, künye). Tasarım dili ve kurallar:
`platform/docs/harita-tasarim-dili.md`; marka değerleri `sinema/marka.json`.

```
python3 platform/sablonlar/dunya/sinema/sinema.py doku                      # dokuları üret (~2 dk, ~/.cache/studyo/kure)
python3 platform/sablonlar/dunya/sinema/sinema.py kontakt ornekler/dunya-sinema/*.json --formatlar 16x9 9x16 -o sayfa.jpg
python3 platform/sablonlar/dunya/sinema/sinema.py kare  ornekler/dunya-sinema/karadeniz.json --an 1 6 10 --format 9x16 -o cikti/
python3 platform/sablonlar/dunya/sinema/sinema.py video ornekler/dunya-sinema/karadeniz.json --format 16x9 -o film.mp4
python3 platform/sablonlar/dunya/sinema/sinema.py video ... --ss 1 --olcek 0.5   # onay öncesi küçük animatik
```
Işık modları: `gece` (varsayılan), `alacakaranlik`, `gunduz`, `atlas`. Örnekler: `ornekler/dunya-sinema/`
(karadeniz = jeopolitik, barbarossa-1941 = askerî tarih, goc-1961 = göç/sosyoloji).
Dokular: NASA Blue Marble + Black Marble, Natural Earth renkli kabartma, Terrain Tiles z6 kabartma (raw.githubusercontent.com
ve s3.amazonaws.com açık olmalı). Başsız Chromium SwiftShader (GPU yok) ile kare başına birkaç saniye.

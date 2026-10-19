# platform/sablonlar/sahne — ortak sahne dili

Tek senaryo, bütün stiller. Senaryo sahne tiplerinden oluşur (`baslik`, `liste`, `sayi`, `alinti`, `karsilastirma`, `urun`, `cta`, `gecis`); her stil bu tipleri kendi görünümüyle çizer. Aynı metin bir komutla kinetikten hamura, piksele ya da vitraya döner. Zaman çizelgesi seslendirmeden çıkar: senaryoda saniye yazılmaz, sahne konuşması kadar sürer.

| Stil grubu | Stiller | Nasıl |
| --- | --- | --- |
| Kaplama (bu klasör) | `kinetik`, `kagit-kesik`, `izometrik`, `hamur`, `piksel`, `origami` | `kaplamalar/<stil>.py`, bütün tipler, 4–120 sn, her format |
| Çevirici | `vitray`, `linol`, `cini`, `teknik-cizim` (desen), `kalkis-tabelasi`, `vhs`, `akis-alani` (ekran) | senaryo hedefin biçimine çevrilir, hedefin kendi aracı render eder; hedefin sınırları geçerli (desen ≤ 20 sn, ≤ 6 sahne, başlık ≤ 16 karakter). Sığmayan yazı kesilmez, `denetle` hata verir |

```sh
S=platform/sablonlar/sahne/sahne.py
python3 $S denetle   ornekler/demli-kahve/sahne.json [--stil vitray]
python3 $S kontakt   ornekler/demli-kahve/sahne.json [--stiller kinetik hamur piksel vitray] [--format 16:9]   # stil seçimi: her stil bir satır, her sahne bir sütun
python3 $S seslendir ornekler/demli-kahve/sahne.json                     # ElevenLabs (yedek Piper), bütün stiller için bir kez
python3 $S uret      ornekler/demli-kahve/sahne.json --stil hamur --format 9:16
python3 $S kare      ornekler/demli-kahve/sahne.json --stil origami --an 2.0 8.5
```

`stil.py` (ve `uret.py` siparişleri) `"dil": "sahne"` taşıyan senaryoları buraya iletir; eski senaryo biçimleri olduğu gibi çalışır. Çıktı senaryonun yanındaki `cikti/`: `<kimlik>-<stil>-<format>.mp4`, kapak, `kalite.json` + kontakt (kalite kapısı). Hızlı prova: `render --olcek 0.25`.

## Senaryo

```json
{"dil": "sahne", "kimlik": "demli-kahve-sahne", "format": "9:16",
 "marka": {"ad": "Demli Kahve", "logo": "logo.png"},
 "seslendirme": {"ses": "<ElevenLabs ses kimliği, isteğe bağlı>"},
 "palet": {"vurgu": "#E2603F"},
 "sahneler": [
  {"tip": "baslik", "ust": "Demli Kahve", "metin": "Sabahın ilk yudumu", "alt": "her gün taze kavrum", "seslendirme": "..."},
  {"tip": "urun", "ad": "Sabah Harmanı", "gorsel": "urun.png", "fiyat": "95 ₺", "seslendirme": "..."}
 ]}
```

| Tip | Alanlar (* zorunlu, karakter sınırı) | Görünüm |
| --- | --- | --- |
| `baslik` | `metin`* 28, `alt` 40, `ust` 20 | büyük başlık, üstte küçük etiket, altta alt satır |
| `liste` | `maddeler`* 2–5 × 28, `baslik` 28 | maddeler sırayla gelir (imli kartlar) |
| `sayi` | `deger`* 8 (`37x`, `%40`, `1.200`), `etiket` 28, `ust` 20 | sayı 0'dan sayar (biçim korunur) |
| `alinti` | `metin`* 90, `kaynak` 30 | büyük tırnak, satır satır |
| `karsilastirma` | `sol`*, `sag`* 16, `sol_deger`, `sag_deger` 6, `baslik` 28 | iki kart (dikeyde alt alta), sağdaki vurgulu |
| `urun` | `ad`* 24, `gorsel` (dosya), `fiyat` 12, `ozellik` 32 | gerçek görsel yeniden çizilmeden, tam çözünürlükte; yoksa stile özgü nesne |
| `cta` | `metin`* 22, `alt` 32 | düğme kartı; `marka.logo` varsa üstte logo, `alt` yoksa marka adı |
| `gecis` | `metin` 20 | kısa ara kart (0,8 sn), seslendirme almaz |

Her sahnede ortak: `seslendirme` (okunan satır), `okunus` (farklı telaffuz), `sure` (en az), `stiller` (çeviriciye özel ayar, ör. `{"vitray": {"motif": "kalp"}}`). Sahne süresi = 0,35 sn + satır süresi + 0,45 sn (seslendirme yoksa sözcük sayısından tahmin); tipin en kısa süresinden az olmaz. Kısa video 9:16'da yazılar güvenli alanın içinde kalır (üst %10, alt %22 boş); yazı sığmazsa küçülür ya da satıra bölünür.

Müzik sahnelere kilitli: alıntı/geçiş sakin, başlık/liste/ürün orta, sayı/karşılaştırma/çağrı enerjik; son sahnede final akoru. Enstrüman stilden (kalimba, çan, marimba, kare dalga, mızrap, sinüs). Konuşurken müzik kısılır, çıktı -14 LUFS.

## Yeni stil kiti

```sh
python3 platform/sablonlar/sahne/sahne.py yeni-stil sulu-boya   # → kaplamalar/sulu_boya.py iskeleti
python3 platform/sablonlar/sahne/sahne.py kontakt ornekler/demli-kahve/sahne.json --stiller sulu-boya kinetik
```

Kaplama `Kaplama` sınıfını genişletir ve yalnız değiştirdiğini ezer. Çoğu zaman temel taşlar yeter, sekiz tip onlarla kendiliğinden yeni görünüme geçer: `fon` (arka plan), `panel` (kart zemini), `yazi` / `buyuk_yazi`, `isaret` (liste imi), `nesne` (görselsiz ürün), `gecis_ciz`, `ust_katman` (doku/tanecik). Bir tip özel bir sahne isterse `ciz_<tip>` ezilir. `POZ = 12` stop-motion yapar (aynı pozdaki kareler bir kez çizilir), `MUZIK` ve `SFX` sesi seçer. Dosya `kaplamalar/` klasörüne konunca stil listesine, `kontakt`a, `stil.py`ye ve testlere (her tip, iki format) kendiliğinden girer.

Gerekenler: `pip install skia-python numpy soundfile fonttools`, ffmpeg. Yazı tipleri stil şablonundan (Inter, hamurda Baloo 2).

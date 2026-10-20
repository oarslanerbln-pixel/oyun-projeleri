# platform/sablonlar/sahne — ortak sahne dili

Tek senaryo, bütün stiller. Senaryo sahne tiplerinden oluşur (`baslik`, `liste`, `sayi`, `alinti`, `karsilastirma`, `urun`, `cta`, `gecis`, `grafik`); her stil bu tipleri kendi görünümüyle çizer. Aynı metin bir komutla kinetikten hamura, piksele ya da vitraya döner. Zaman çizelgesi seslendirmeden çıkar: senaryoda saniye yazılmaz, sahne konuşması kadar sürer.

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
| `grafik` | `veri`* (CSV dosyası ya da `[["Ocak", 120], ...]`, etiket ≤ 12), `tur` `cubuk`/`cizgi`/`pasta`, `baslik` 28, `birim` 8 (`"%{}"`, `"{} ₺"`, `" adet"`), `kaynak` 30 | veri sahnesi: çubuklar büyür ve sayar, çizgi soldan sağa çizilir, pasta dilim dilim dolar; en büyük değer vurgulu. Dikey videoda yatay çubuk. Çubuk 2–8, çizgi 3–12, pasta 2–6 satır. Çeviricili stillerde en büyük değer başlık olur |
| `harita` | `duraklar`* 2–8 (şehir adı ya da `{"ad": "Válor", "konum": [-3.085, 36.995]}`, ad ≤ 16, `"etiket"` ile kısaltılır), `baslik` 28, `ulkeler` (vurgulanacak ülkeler: `["İspanya"]`), `mesafe` true | harita ve rota: kadraj duraklara oturur, rota durak durak çizilir ve her durağa adı söylendiği an varır; `mesafe` kuş uçuşu toplam km'yi sayar. Yer adları Türkçe/Almanca da olur (Kurtuba, München); aynı adlı şehirde rotaya yakın olan seçilir. Çeviricili stillerde rota yazıyla. Arama: `platform/ortak/harita.py bul Sevilla` |

CSV: ilk iki sütun (etiket, değer), `;` ya da `,` ayraç, başlık satırı kendiliğinden atlanır, `1.200,5` gibi Türkçe/Almanca sayılar okunur. Çubuk/dilim etiketi söylendiği an girer (senkron).

Senaryo düzeyinde: `"altyazi": true` (kelime kelime yakılı altyazı), `"senkron": false` (öğeler sabit zamanda). `"muzik": false` müzik yatağını kapatır (seslendirme ve sahne efektleri kalır). `"yerlesim": "simetrik"` güvenli alanın iki yanını geniş olana eşitler: 9:16'da içerik ve altyazı kadrajın tam ortasında durur (sağdaki Reels sütunu yine boş kalır); origamide fon üçgenleri sol-sağ aynalanır. İkisi de varsayılan kapalı, eski senaryolar aynı kalır. Her sahnede ortak: `seslendirme` (okunan satır), `kanca` (`sok`: ekran vurgu rengiyle dolar, yazı büyükten oturur), `okunus` (farklı telaffuz), `sure` (en az), `stiller` (çeviriciye özel ayar, ör. `{"vitray": {"motif": "kalp"}}`). Sahne süresi = 0,35 sn + satır süresi + 0,45 sn (seslendirme yoksa sözcük sayısından tahmin); tipin en kısa süresinden az olmaz. Kısa video 9:16'da yazılar güvenli alanın içinde kalır (üst %10, alt %22 boş); yazı sığmazsa küçülür ya da satıra bölünür.

Müzik sahnelere kilitli: alıntı/geçiş sakin, başlık/liste/ürün orta, sayı/karşılaştırma/çağrı enerjik; son sahnede final akoru. Enstrüman stilden (kalimba, çan, marimba, kare dalga, mızrap, sinüs). Konuşurken müzik kısılır, çıktı -14 LUFS.

## Metinden sahneye (`bol.py`) ve kanca varyantları (`kanca.py`)

```sh
python3 platform/sablonlar/sahne/bol.py metin.txt --format 9:16      # → metin.sahne.json taslağı + sahne listesi
python3 platform/sablonlar/sahne/kanca.py kontakt metin.sahne.json --stil kinetik   # 3 açılış tek sayfada
python3 platform/sablonlar/sahne/kanca.py uret metin.sahne.json --stil kinetik --format 9:16
```

`bol.py` düz metni sahnelere böler; okunan satır metnin kendisi, ekran yazısı ondan kısaltılır (uzun başlık ana yazı + alt satıra dengeli bölünür, bağlaçta bölünmez). Biçim tipi seçer: ilk satır/`#` → `baslik`; `- madde` satırları (öncesinde `Başlık:`) → `liste`; en az iki `Ocak: 120` satırı (isteğe bağlı `tur: pasta`) → `grafik`; tırnaklı söz, `> söz — kaynak` ya da `*vurgu*` → `alinti`; sayı içeren cümle (`%40`, `37 kat`, `1.200 kişi`, `yüzde 40`; cümledeki son sayı) → `sayi`; `X yerine Y` / `X değil Y` / `statt X, Y` → `karsilastirma`; `---` → `gecis`; son paragrafta çağrı sözcüğü (takip, kaydet, link, folgen, jetzt...) → `cta`. 24 sahneyi aşan metin `-1`, `-2` senaryolarına bölünür. Taslak her zaman `denetle`den geçer; ekran yazılarını önizlemede (`onizleme.py`) gözden geçir.

`kanca.py` aynı videonun üç açılışını yazar (`<ad>-kanca-soru|rakam|sok.json`): **soru** başa "Bunu biliyor muydun?" (Almanca metinde "Wusstest du das?"), **rakam** videodaki ilk sayı sahnesini (yoksa grafiğin en büyük değerini) başa alır, **sok** ilk sahneyi görsel şokla açar. Kendi kanca metnin: senaryoda `"kancalar": {"soru": "Hâlâ hazır kahve mi?"}` (ya da sahne alanlarıyla sözlük). Her varyant `cikti/kanca-<tür>/` klasörüne çıkar; seslendirme satırları önbellekten gelir, yalnız yeni kanca satırı kredi harcar.

## Kelimeye senkron ve altyazı

ElevenLabs her satırın harf zamanlarını verir (`cikti/seslendirme/<id>.hizalama.json`). Öğeler anlatıcı kendi kelimesini söylediği an girer: liste maddeleri, sayının saymaya başlaması, karşılaştırmanın iki kartı, başlığın alt satırı, ürünün özelliği ve fiyatı, alıntının satırları. Eşleşme ekleri tanır (`adım` ~ `adımlar`) ve rakamları sözle bulur (`37x` → "otuz yedi", `%1` → "yüzde"). Liste efektleri ve sayaç tıkları aynı ana kayar. Eşleşmeyen öğe eski sabit zamanında gelir; `"senkron": false` hepsini sabite döndürür.

Her render yanına `<kimlik>-<stil>.srt`, `.vtt` (platforma yüklemek için) ve `.altyazi.json` yazar. Senaryoda `"altyazi": true` kelime kelime altyazıyı videoya yakar: 2–4 kelimelik grup, söylenen kelime vurgu renkli pulda. Kaplamalar altyazıyı kendi yazı tipi ve paletiyle çizer ve bandı güvenli alanın altından ayırır (sahne yazısı altına girmez); çeviricili stillerde altyazı render sonrası libass ile yakılır. Varsayılan kapalı (az yazı kuralı); sessiz izlenecek kısa videolarda açın. Hizalama yoksa (Piper, eski önbellek) zamanlar hecelerden tahmin edilir ve uyarı verilir. Ortak çekirdek `platform/ortak/altyazi.py`; başka bir videoya: `altyazi.py yak video.mp4 x.altyazi.json`.

## Stil karışımı ve stil geçişi

Bir videoda sahneler farklı stillerde olabilir. Sahneye `"stil": "piksel"` yazılırsa o sahne ve stil yazmayan sonrakiler pikselde çizilir; stil değiştiği an eski stil yenisine imza geçişle döner. `"donustur": "origami"` (ya da `{"stil": "origami", "an": 0.5, "sure": 0.9}`, `an` sahnenin oranı 0,15–0,85) aynı sahneyi ortasında yeni stile çevirir, sonraki sahneler yeni stilde sürer. Geçiş biçimi senaryo düzeyinde: `"stil_gecisi": {"tur": "firca" | "murekkep", "sure": 0.8}` (fırça: dalgalı kenarlı çapraz darbe; mürekkep: ortadan yayılan leke; ikisinde de kenarda yeni stilin mürekkep renginde ince çizgi). Müzik ve efektler `--stil` ile verilen ana stilden. Kod: `karisim.py`.

```json
{"dil": "sahne", "stil_gecisi": {"tur": "firca"},
 "sahneler": [{"tip": "baslik", "metin": "..."}, {"tip": "liste", "stil": "piksel", "maddeler": ["..."]},
              {"tip": "karsilastirma", "donustur": "origami", "sol": "...", "sag": "..."}]}
```

Yalnız kaplama stilleri karışır (kare kare çizilir). Çeviricili stiller (vitray, çini, VHS...) ve ayrı şablonlar (karakalem, tek çizgi) arasında aynı imza geçiş uzun video kurgusunda: `kurgu.json` sahnesinde `"gecis": {"tur": "firca"}`.

## Görsel regresyon testi

Her stilin 3 sabit karesi (liste, karşılaştırma ve çağrı sahnelerinin bitmiş hali; karışımda üç geçişin ortası) CI'da kayıtlı referansla karşılaştırılır. Bir değişiklik başka bir stili bozarsa PR kırmızı olur ve iş akışının eklerinde `gorsel-regresyon` fark sayfası (referans | yeni | fark kırmızı) çıkar. Yazı kenarı yumuşatmasındaki küçük farklar geçer; kayma, renk ya da öğe değişimi geçmez.

```sh
R=platform/sablonlar/sahne/regresyon.py
python3 $R karsilastir [--stiller hamur vitray] [-o fark/]
python3 $R guncelle --stiller hamur      # görünüm bilerek değiştiyse referansı yenile ve PR'a ekle
```

Senaryo `testler/regresyon/regresyon.json` (seslendirmesiz), referanslar `testler/regresyon/referans/<stil>.npz` (PNG depoda Git LFS'e gittiği için sıkıştırılmış numpy). Yeni stil eklenince `guncelle --stiller <ad>` ile referansı eklenir; eklenmezse test hatırlatır.

## Yeni stil kiti

```sh
python3 platform/sablonlar/sahne/sahne.py yeni-stil sulu-boya   # → kaplamalar/sulu_boya.py iskeleti
python3 platform/sablonlar/sahne/sahne.py kontakt ornekler/demli-kahve/sahne.json --stiller sulu-boya kinetik
```

Kaplama `Kaplama` sınıfını genişletir ve yalnız değiştirdiğini ezer. Çoğu zaman temel taşlar yeter, sekiz tip onlarla kendiliğinden yeni görünüme geçer: `fon` (arka plan), `panel` (kart zemini), `yazi` / `buyuk_yazi`, `isaret` (liste imi), `nesne` (görselsiz ürün), `gecis_ciz`, `ust_katman` (doku/tanecik). Bir tip özel bir sahne isterse `ciz_<tip>` ezilir. `POZ = 12` stop-motion yapar (aynı pozdaki kareler bir kez çizilir), `MUZIK` ve `SFX` sesi seçer. Dosya `kaplamalar/` klasörüne konunca stil listesine, `kontakt`a, `stil.py`ye ve testlere (her tip, iki format) kendiliğinden girer; görsel regresyon referansını `regresyon.py guncelle --stiller <ad>` ekler.

Gerekenler: `pip install skia-python numpy soundfile fonttools`, ffmpeg. Yazı tipleri stil şablonundan (Inter, hamurda Baloo 2).

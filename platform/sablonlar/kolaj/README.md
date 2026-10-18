# platform/sablonlar/kolaj

Dergi kesiği kolaj şablonu (6–15 sn reklam): kraft pano üstünde yırtık gazete kâğıtları, yarım ton baskılı kesik "fotoğraflar", fidye notu gibi tek tek yapıştırılan harfler, kâğıt bant ve keçeli kalem. Hareket stop-motion gibi saniyede 15 adımdır ve parçalar her adımda çok hafif kıpırdar. Tek bir `senaryo.json` dosyasından görüntü, kâğıt efektleri, sentez müzik ve seslendirme aynı anlara kilitli üretilir. Ücretli bir servis ya da telifli görsel gerekmez.

```sh
K=platform/sablonlar/kolaj/kolaj.py
python3 $K fontlar                                                   # bir kez: OFL yazı tipleri → ~/.cache/studyo/fonts
python3 $K denetle   platform/sablonlar/kolaj/ornek/senaryo.json
python3 $K seslendir platform/sablonlar/kolaj/ornek/senaryo.json      # platform/ses (Piper fahrettin); --saglayici elevenlabs --ses <id>
python3 $K kare      platform/sablonlar/kolaj/ornek/senaryo.json --an 2.7 6.9 --format 16x9   # önizleme PNG
python3 $K render    platform/sablonlar/kolaj/ornek/senaryo.json      # → cikti/<kimlik>-9x16.mp4
```

Gerekenler: `pip install skia-python numpy soundfile scipy fonttools`, ffmpeg (Linux'ta `apt-get install libegl1 libgl1`). Yazı tipleri depoya konmaz (ikili dosyalar LFS'e düşer); `fontlar` komutu Fraunces, Archivo Black, Anton, Abril Fatface ve Courier Prime'ı Google Fonts deposundan indirir, Inter sistemden gelir. Bir yazı tipi yoksa DejaVu/Liberation yedeği kullanılır, render durmaz. `denetle` yalnız standart kütüphaneyle çalışır. 10 sn'lik 9:16 render yaklaşık 1,5 dakika sürer.

Format senaryodaki `format` alanından gelir (`"9x16"` ya da liste), verilmezse yalnız 9:16 üretilir. `--format 9x16 16x9` ile ezilir. Dikey ve yatay yerleşim ayrı tanımlıdır; 1:1 ve 4:5 dikey yerleşimi kullanır.

## Senaryo

Örnek: [`ornek/senaryo.json`](ornek/senaryo.json). Uydurma B2B marka *Demli Ofis* (örnek marka Demli Kahve'nin ofis aboneliği), ilke **çapalama + fiyat çerçeveleme**: önce kabaran kafe fişi ("PAHALI") yüksek bir çapa kurar, sonra aynı şey küçük ve tanıdık bir günlük birime çevrilir ("çalışan başına günde 1 simit"). Rakam uydurulmaz; fişteki tutarlar `₺₺₺` simgeleridir.

Bütün anlar videonun başından itibaren saniye cinsindendir. Bir sahne bir sonrakinin `bas` anına kadar sürer.

| Sahne (`tur`) | Ne | Alanlar |
| --- | --- | --- |
| `fis` | Çapa: yazıcıdan satır satır uzayan fiş, birikip yapışan kesik bardaklar, damga gibi basılan kelime | `kalemler[]`, `kalem_t`, `kalem_son`, `toplam`, `toplam_tutar` (yoksa `para` ×5), `para` (fiyat simgesi, varsayılan `₺`), `fis_alt` (varsayılan `*** FİŞ ***`), `toplam_t`, `cember_t` (toplamın etrafına kalem halkası), `nesne{tur,t,adet}`, `damga{metin,t,son}`, `baslik` |
| `esitlik` | Yeniden çerçeveleme: üst yazı, nesne = nesne2, alt yazı, kalem altı çizgisi | `ust{metin,t,son}`, `nesne{t,buhar}` (buhar çizgileri yalnız bardak/kupada, başka nesnede `buhar: true`), `esit_t`, `nesne2{t}` (zirvede çarparak iner), `alt{metin,t,son}`, `cizgi_t` |
| `kapanis` | Marka: kelime kelime yapışan marka şeritleri, daktilo etiketi, yuvarlak mühür | `marka{metin,t,son}`, `alt{metin,t}`, `nesne{t}`, `damga_t`, `damga{metin}` (mühür çevresindeki yazı) |

Kesik harf yazılarında (`ust`, `alt`, `damga`) her harf `t` → `son` arasında tek tek düşer; sığmazsa kelime aralarından satıra bölünür, yine sığmazsa küçülür. Ekranda az yazı kuralı için üç dört kelimeyi geçmeyin.

Nesneler (`tur`): `bardak` (karton kahve bardağı), `kupa`, `simit`, `cekirdek`. Hepsi kodla çizilip yarım tona çevrilir. Gerçek ürün için `{"gorsel": "urun.png", "genislik": 420, "t": 3.3}` verilir: görsel gri tona, oradan yarım ton baskıya çevrilir, saydam PNG ise siluetinden makasla kesilir. Okunması gereken görseller (kitap kapağı, ambalaj yazısı) için `"renkli": true` yarım tonu atlar, görsel kendi renkleriyle makasla kesilir.

Sahneye giriş geçişi (`gecis`): `yirt` (önceki sayfa ortadan yırtılır, iki yarısı beyaz lifli kenarlarıyla ekrandan çıkar), `kaydir` (yeni kâğıt alttan kayarak gelir, 0,3 sn önce başlar), `kesme`.

Renkler rollerle verilir: `zemin` (kraft pano), `kagit`, `gazete`, `murekkep`, `vurgu`, `ikinci`, `marka`. Marka değişince yalnız palet değişir.

## Görüntü kalitesi

Kenarlar vektördür ve tam çözünürlükte çizilir: yırtık kenar her 2 pikselde örneklenen yumuşak çok katmanlı gürültüdür, altında beyaz lif şeridi görünür; makas kenarı kısa düz kesimlerdir. Radyal gradyan ya da ışık parlaması yok. Gölgeler bulanık ama tüm kareye çok ince, sabit bir kâğıt greni bindiği için bantlaşmaz.

## Ses

- **Müzik:** 100 BPM, çekilen gitar arpeji, ped ve parmak şıklatmasıyla sakin başlar. Tam ritim (kick, alkış, shaker, kontrbas) `muzik.dusus` anında, yırtılmayla girer. `muzik.zirve` anında çan akoru ve ek darbe vurur, `muzik.sakin` aralığında davul susar, kapanışta çan motifi ve tonik akor çalar.
- **Efektler:** harf yapışması, fiş yazıcısı, bant, kâğıt kayması, mühür, yırtılma, çarpma ve keçeli kalem zaman çizelgesinden (`zaman.ses_olaylari`) üretilir. Konuşmanın yaklaşık 9 dB altında, sessiz tutulur.
- **Seslendirme:** `cikti/seslendirme/<id>.wav`. Konuşma sırasında müzik ~8 dB altta, ek 3 dB kısılır.
- **Master:** 16 kHz alçak geçiren, -14 LUFS, tepe sınırlayıcı.

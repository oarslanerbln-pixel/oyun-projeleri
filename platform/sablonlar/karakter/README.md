# platform/sablonlar/karakter

Karakterli anlatım videosu (5–90 sn): bir karakter poz değiştirerek, yüz ifadesiyle ve seslendirmeye göre oynayan ağzıyla anlatır; ekranda az yazı, tek vurgu rengi. Ortak bir iskelet (eklemler, 8 poz, 7 ifade, göz kırpma, nefes, ağız senkronu) ile görünüm katmanı ayrıdır: ilk görünüm **çizgisel insan** (ince siyah çizgi, beyaz yamuk gövde, nokta gözler, sarı vurgu dairesi). Diğer görünümler: **konuşan nesne maskot** (`maskot`) ve **gün batımı siluet** (`siluet`); yeni görünümler yalnız `gorunumler/<ad>.py` ekler.

Ağız senkronu ElevenLabs'in harf zamanlarından gelir (platform/ses `with-timestamps` ister, aynı kredi; `<id>.hizalama.json`). Harf zamanı yoksa (Piper yedeği ya da zamanlar eklenmeden önce önbelleğe girmiş satır) ağız ses genliğinden oynar ve render bunu bildirir.

```sh
K=platform/sablonlar/karakter/karakter.py
python3 $K denetle   ornekler/kucuk-aliskanliklar/cizgisel.json
python3 $K seslendir ornekler/kucuk-aliskanliklar/cizgisel.json      # ElevenLabs (varsayılan), yedek Piper
python3 $K kare      ornekler/kucuk-aliskanliklar/cizgisel.json --an 1.0 7.5 --format 16x9
python3 $K render    ornekler/kucuk-aliskanliklar/cizgisel.json --format 9x16 16x9
python3 platform/sablonlar/stil/stil.py uret ornekler/kucuk-aliskanliklar/cizgisel.json --stil cizgisel --format 9:16
```

Format verilmezse senaryonun `format` listesi, o da yoksa yalnız `9x16`. Dikeyde karakter ortada, yazı altında ve Reels güvenli alanında (üst %10, alt %22 ve sağ sütun boş); yatayda karakter solda, yazı sağda. 15 sn'lik video 9:16 + 16:9 birlikte ~30 sn'de çıkar. Gerekenler: `pip install skia-python numpy soundfile`, ffmpeg, Inter (`apt-get install libegl1 libgl1 fonts-inter`). `denetle` yalnız standart kütüphaneyle çalışır.

## Senaryo

```json
{
  "kimlik": "kucuk-aliskanliklar-cizgisel", "stil": "cizgisel", "sure": 15.0, "format": ["9x16"],
  "palet": {"zemin": "#F7F5EF", "cizgi": "#161616", "vurgu": "#FFD25A", "dolgu": "#FFFFFF", "yazi": "#161616"},
  "karakter": {"sac": "kase", "gozluk": false, "ust": "#FFFFFF", "ten": "#FFFFFF", "sac_rengi": "#161616"},
  "muzik": {"bpm": 104},
  "sahneler": [
    {"bas": 0, "poz": "selam", "ifade": "gulumse", "yazi": "büyük hedefler", "enerji": "sakin",
     "anahtarlar": [{"t": 1.6, "poz": "dusun", "ifade": "dusunceli"}]},
    {"bas": 6.2, "poz": "el_kaldir", "ifade": "sasir", "nesne": {"tur": "tabela", "metin": "%1"}, "yazi": "fikir geldi", "x": 0.3}
  ],
  "seslendirme": {"ses": "george", "satirlar": [{"id": "v1", "t": 0.35, "metin": "Büyük hedefler insanı korkutur."}]}
}
```

- **poz**: `ayakta`, `el_kaldir`, `isaret`, `dusun`, `sevin` (zıplar), `yuru` (adım atar; `x` değişirse bir sonraki anahtara kadar yürür), `selam` (el sallar), `omuz` (omuz silker). Geçişler 0,38 sn yumuşak.
- **ifade**: `notr`, `gulumse`, `sevincli`, `sasir`, `uzgun`, `kararli`, `dusunceli`. Göz kırpma ve nefes kendiliğinden.
- **anahtarlar**: sahne içinde ek poz/ifade/konum değişimi (`t` sahnenin içinde).
- **x**: karakterin yatay yeri, -1..1 (kadrajın karaktere ayrılan bandında).
- **nesne**: `tabela` (kaldırılan elde, kısa `metin`), `ampul`, `soru`, `kalp`, `balon` (konuşma balonu, `metin`), `grafik` (yükselen çubuklar). `t` verilmezse sahne başından 0,35 sn sonra.
- **yazi**: en fazla 42 karakter, iki satıra kendisi böler; `t` verilmezse sahne başından 0,25 sn sonra.
- **enerji**: `sakin` (yalnız tel + pad), `orta`, `enerjik` (kick, bas, shaker). Müzik konuşmanın ~8 dB altında.
- **karakter.sac**: `kase`, `kisa`, `uzun`, `topuz`, `kel`; `gozluk: true`.
- **seslendirme.satirlar[].konusan**: `karakter` (varsayılan, ağız oynar) ya da `anlatici` (ağız kapalı kalır).

## Konuşan nesne maskot (`"stil": "maskot"`)

Ürün konuşur: gövde `karakter.nesne` = `kupa`, `sise`, `kutu` ya da `gorsel` (müşterinin **şeffaf PNG** ürün fotoğrafı, `karakter.gorsel` senaryoya göre yol; yüz üstüne çizilir, `"yuz": false` ile kapatılır). Logo: `karakter.logo` (PNG) ya da `karakter.logo_metin` (en fazla 14 karakter, koyu hap); kupa/şişe/kutunun üstünde hep görünür, `{"tur": "logo"}` nesnesi başın üstünde büyük rozet açar (kapanış sahnesi). Diğer alanlar: `govde_rengi`, `icerik_rengi` (kahve bandı, kapak), `buhar` (kupa). Palet varsayılanı pembe zemin + düz yer gölgesi (`palet.golge`). Yüz, ağız senkronu ve yanaklar ortak iskeletten; beden kısa bacaklı, kadrajda insandan büyük durur. Örnek: `ornekler/kucuk-aliskanliklar/maskot.json` (uydurma marka). Müşteri dosyaları repoya girmez; senaryo müşteri klasöründe durur.

## Gün batımı siluet (`"stil": "siluet"`)

Düz renk bantlı gökyüzü (`palet.bantlar`, yukarıdan aşağı 2–9 renk; gradyan yok), video boyunca yavaşça batan güneş (`palet.vurgu`), koyu tepe ve tek renk siluet (`palet.cizgi`), uçan kuşlar. Yazı tepenin koyu zemininde açık renkle (`palet.yazi`). `karakter.eslik`: yanında ikinci siluet, `{"x": 0.36, "boy": 0.9, "sac": "uzun", "poz": "ayakta"}`. Yüz çizilmez, ifade beden dilinden okunur; seslendirme satırlarında `"konusan": "anlatici"` kullan. Örnek: `ornekler/kucuk-aliskanliklar/siluet.json`.

## Yeni görünüm eklemek (konuşan maskot, siluet...)

1. `gorunumler/<ad>.py` içinde `Gorunum(s, cizici)` sınıfı: `karakter(cv, govde, yuz, ekran)` ve `nesne(cv, nesne, govde, ekran, olcek, gecen)`. `govde` eklem konumlarını (`iskelet.Govde`: baş, boyun, omuz, dirsek, el, kalça, diz, ayak; karakter boyu birimi), `yuz` ifade ve ağız değerlerini (`iskelet.Yuz`: kaş, göz, ağız açıklığı ve biçimi A/E/O/M/F) verir; `ekran(p)` karakter birimini piksele çevirir.
2. `senaryo.GORUNUMLER`'e ve `stil/stil.py` içindeki `KARAKTER_STILLERI`'ne adı ekle, `ci.json`'a örnek dosya desenini ekle.
3. Beden oranı farklıysa modülde `ORAN = iskelet.Oranlar(...)` ver (maskot); pozlar ve ağız senkronu aynen çalışır.
4. İsteğe bağlı: `Gorunum.zemin(cv, t, govde, ekran)` kendi zeminini çizer (siluet), modüldeki `DUZEN = {"16x9": {...}}` format düzenini değiştirir, `senaryo.STIL_PALETLERI` varsayılan paleti, `senaryo.EK_NESNELER` yalnız o görünüme ait nesneleri verir.

Senaryo dosyasının adı bilerek `senaryo.json` değil: CI `ornekler/*/senaryo.json` dosyalarını kinetik şablonla denetliyor.

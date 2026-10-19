# platform/sablonlar/desen

Desen ve zanaat stilleri: **vitray**, **linol baskı**, **çini** ve **teknik çizim**. Dördü aynı senaryoyu okur; bir video içeriği değişmeden stil değiştirir (`--stil`). Görüntü PIL + numpy ile, müzik ve efektler kodla üretilir; ücretli servis ve GPU gerekmez. Seslendirme `platform/ses` (ElevenLabs, yoksa Piper yedeği, satırlar önbellekten).

| Stil | Görünüm ve hareket | Ses | Uygun konular |
| --- | --- | --- | --- |
| `vitray` | Kurşun çizgili cam; hücreler sırayla yanar, motif sıcak camdan, arka cam soğuk, ışık arkadan kayar; yazı kurşun levhada | cam çan arpeji + ped, hücre yanarken parıltı | lüks, kafe, kültür, "aydınlanma" anı |
| `linol` | Oyulmuş baskı, saniyede 12 poz: merdane mürekkebi yayar, oyma çizgiler kazınır, yazı damga gibi basılır, yaprak yukarı çekilir | marimba + bas, merdane gümbürtüsü, damga | kişisel gelişim, zanaat, kahve |
| `cini` | Sekiz köşeli yıldız karolar ortadan dışa dizilir ve sırlanır, desen yavaşça kayar; madalyonda motif, çerçeveli panoda yazı | mızraplı ud benzeri ezgi (Re hicaz) + def (düm-tek) | Türk/İslam kültürü, restoran, gezi |
| `teknik-cizim` | Mavi çizim kâğıdı: kurulum çizgileri, motif cetvelle çizilir, ölçüler açılır ve sayar, yazı daktiloyla gelir, sayfa sola kayar; köşede antet | yumuşak sinüs darbeleri, cetvel tıkları | ürün tanıtımı, "planla", teknoloji |

```sh
D=platform/sablonlar/desen/desen.py
python3 $D denetle   ornekler/kucuk-aliskanliklar/vitray.json
python3 $D seslendir ornekler/kucuk-aliskanliklar/vitray.json            # dört stil aynı seslendirmeyi kullanır
python3 $D kare      ornekler/kucuk-aliskanliklar/vitray.json --an 1.6 4.6 9.7 --format 16x9
python3 $D uret      ornekler/kucuk-aliskanliklar/cini.json --format 9:16   # seslendirme yoksa üretir, sonra render
python3 $D render    ornekler/kucuk-aliskanliklar/cini.json --stil linol   # aynı içerik başka stilde
python3 platform/sablonlar/stil/stil.py uret ornekler/kucuk-aliskanliklar/linol.json --stil teknik-cizim   # stil.py de iletir
```

Biçim: `--format 9:16 | 16:9 | 1:1 | 4:5 | ikisi`, yoksa senaryodaki `format`, o da yoksa 9:16. Hızlı prova için `render --olcek 0.25`. 1080×1920 10 sn'lik bir render 4 çekirdekte 25–55 sn sürer (vitray en uzun). Render sonunda kalite kapısı (`platform/ortak/kalite.py`) kendiliğinden çalışır: `<ad>.kalite.json` + kontakt sayfası. Çıktı H.264 + AAC, -14 LUFS.

## Senaryo

```json
{
  "kimlik": "kahve-vitray", "stil": "vitray", "format": "9:16", "sure": 10,
  "sahneler": [
    {"t": 0,   "motif": "fincan", "baslik": "Demli sabah", "alt": "her gün taze"},
    {"t": 3.5, "motif": "kalp",   "baslik": "El emeği"},
    {"t": 7,   "motif": "yildiz", "baslik": "Bugün uğra.", "alt": "Residenzstraße 109"}
  ],
  "seslendirme": {"satirlar": [{"id": "v0", "t": 0.3, "metin": "..."}]},
  "gorsel": {"dosya": "logo.png"},
  "imza": "DEMLİ KAHVE"
}
```

| Alan | Ne | Sınır |
| --- | --- | --- |
| `sure` | video süresi | 6–20 sn |
| `sahneler[].t` | sahne başlangıcı (ilki 0, sırayla) | sahne en az 1,6 sn |
| `sahneler[].motif` | `gunes`, `kalp`, `yildiz`, `fincan`, `ampul`, `yaprak`, `dag`, `ok`, `ev` (boş bırakılabilir) | |
| `sahneler[].baslik` / `alt` | büyük yazı / küçük satır; sığmazsa küçülür | 16 / 32 karakter |
| `sahneler[].olcu` | teknik çizimde ölçü değerleri `[yatay, dikey]`, sıfırdan sayar; birim `birim` alanından (varsayılan mm) | |
| `seslendirme.satirlar` | `id`, `t` (sn), `metin`, isteğe bağlı `okunus`; satırlar sırayla, her biri bir sonrakinden önce biter | |
| `gorsel.dosya` | müşteri logosu ya da ürün fotoğrafı (senaryoya göre yol); son sahnede motifin yerine tam çözünürlükte gösterilir | |
| `imza` | teknik çizim anteti (marka ya da proje adı) | 24 karakter |
| `renkler` | stil renklerini ezer: vitray `sicak`/`soguk` listeleri; linol `kagit`, `murekkep`, `vurgu`; çini `zemin`, `kobalt`, `turkuaz`, `mercan`; teknik çizim `zemin`, `izgara`, `izgara_kalin`, `cizgi` | |
| `muzik` | `bpm`, `kok` (MIDI kök nota) | |
| `yerlesim.<format>` | yerleşim ince ayarı (`mx`, `my`, `mr`, `bx`, `by`, `ay`, `gen`, `boy`; ekran oranı) | |

Yerleşim: 9:16'da motif üstte, yazı altta; üst %10 ve alt %22 Reels arayüzüne bırakılır. 16:9'da motif solda, yazı sağda. Testler (`testler/test_desen.py`) her formatta yazının ekrana tam sığdığını ve güvenli alanda kaldığını denetler.

Sahne geçişi her stilde kendi dilinde: vitrayda hücreler söner ve yenileri yanar, linolde yaprak yukarı çekilir, çinide madalyon küçülüp yenisi açılır, teknik çizimde sayfa sola kayar. Son sahne geçiş yapmaz, ekranda kalır (çağrı).

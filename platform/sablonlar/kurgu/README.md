# platform/sablonlar/kurgu

Uzun video için sahne birleştirici: tek bir `kurgu.json`, farklı şablonların (kinetik, analiz, karakalem, tek çizgi, kolaj, gölge oyunu, origami) sahnelerini sırayla dizer; sahneler geçişlerle tek videoda birleşir, seslendirme bütün sahnelerden tek seferde ve tek sesle üretilir, müzik baştan sona kesintisiz çalar ve sahnenin enerjisine göre sakinleşip coşar. Örnek: `ornekler/kucuk-aliskanliklar-uzun/` (4 sahne, 61 sn, 16:9, 4 dk'da çıkar).

```sh
K=platform/sablonlar/kurgu/kurgu.py
python3 $K denetle   ornekler/kucuk-aliskanliklar-uzun/kurgu.json   # her sahne kendi şablonunun denetiminden de geçer
python3 $K onizle    ornekler/kucuk-aliskanliklar-uzun/kurgu.json   # her sahneden 3 kare, tek sayfa (render yok)
python3 $K seslendir ornekler/kucuk-aliskanliklar-uzun/kurgu.json   # ElevenLabs (yedek Piper); kurguda seslendirme.saglayici "piper" ise Piper
python3 $K uret      ornekler/kucuk-aliskanliklar-uzun/kurgu.json   # eksik ses varsa üretir, sonra render + kalite kapısı
```

Format sırası: `--format` (`16:9`, `9:16`, `1:1`, `4:5`, `ikisi`), yoksa kurgunun `format` alanı, o da yoksa 16:9 (uzun video varsayılanı). Çıktı kurgunun yanındaki `cikti/`: `<kimlik>-16x9.mp4`, kalite raporu ve kontakt sayfası, YouTube açıklaması için `<kimlik>-bolumler.txt`.

## kurgu.json

```json
{
  "kimlik": "kucuk-aliskanliklar-uzun", "format": "16:9", "fps": 30, "dil": "tr",
  "muzik": {"bpm": 100, "akorlar": [[57, 60, 64, 69], [53, 57, 60, 65]], "ses_ustu_db": 8},
  "gecis": {"tur": "erime", "sure": 0.5},
  "sahneler": [
    {"id": "acilis", "baslik": "Giriş", "stil": "kinetik", "senaryo": "sahneler/01-acilis.json", "enerji": "enerjik"},
    {"id": "matematik", "baslik": "Yüzde birin matematiği", "stil": "analiz", "senaryo": "sahneler/02-matematik.json", "enerji": "sakin"},
    {"id": "kapanis", "baslik": "Bugün başla", "stil": "kinetik", "senaryo": "sahneler/04-kapanis.json", "gecis": "kaydir"}
  ]
}
```

| Alan | Anlamı |
| --- | --- |
| `sahneler[].stil` | Sahnenin şablonu: `kinetik`, `analiz`, `karakalem`, `tek_cizgi`, `kolaj`, `golge_oyunu`, `origami`, `ekran` (kalkış tabelası, VHS, akış alanı; görünüm sahne senaryosunun `stil` alanından) |
| `sahneler[].senaryo` | O şablonun kendi senaryo dosyası (kurguya göre yol). Süre, görüntü ve seslendirme satırları oradan gelir; anlar sahnenin başından sayılır |
| `sahneler[].enerji` | `sakin`, `orta` (varsayılan), `enerjik`: müziğin o bölümdeki yoğunluğu |
| `sahneler[].baslik` | YouTube bölüm listesindeki adı |
| `sahneler[].gecis` | Önceki sahneden geçiş: `erime`, `kaydir`, `silme`, `kesme`; ya da `{"tur": "erime", "sure": 0.8}` |
| `gecis` | Bütün sahnelerin varsayılan geçişi (varsayılan 0,5 sn erime) |
| `seslendirme` | Bütün video için tek ses: `saglayici`, `ses`, `dil`. Sahne dosyalarındaki sağlayıcı yok sayılır |
| `muzik` | Tek müzik yatağı: `bpm` (60–160), `akorlar` (MIDI, ölçü başına bir akor), `ses_ustu_db` (konuşma müziğin kaç dB üstünde; varsayılan 8), `vurusa_otur` (varsayılan true), `efekt_db` (sahne efektleri, varsayılan −12), `gecis_sesi` (`otomatik`), `gecis_db` (varsayılan −16) |
| `sahneler[].efekt_db` | Bu sahnenin efekt seviyesi (konuşmaya göre dB) |

Sahne dosyaları `ornekler/<iş>/sahneler/` altında durur; böylece şablonların kendi CI denetimi (`ornekler/*/senaryo.json` gibi) onları ikinci kez denetlemez, kurgunun denetimi her birini kendi şablonuyla denetler.

## Nasıl çalışır

- **Zaman çizelgesi.** Sahneler art arda dizilir; geçiş süresi kadar üst üste biner (0,5 sn erimede bir sonraki sahne 0,5 sn erken başlar). Süreler kare sayısına yuvarlanır.
- **Görüntü.** Her sahne kendi şablonunun `cizim.video` işleviyle, ayrı bir süreçte, sessiz çizilir (şablonların `cizim` modülleri aynı süreçte çakışır). Sahneler paralel çizilir (`--paralel`, varsayılan çekirdek/2) ve `cikti/is/sahneler/` altında önbelleğe girer: senaryo, boyut, ses süreleri ve şablon kodu değişmedikçe sahne yeniden çizilmez. Revizyonda yalnız değişen sahne çizilir. Birleştirme tek kodlamadır (ffmpeg `xfade` / `concat`, H.264 CRF 16).
- **Seslendirme.** Bütün sahnelerin satırları `<sahne>-<satır>` kimliğiyle tek listede, kurgu zamanında; `platform/ses` önbelleği sayesinde yalnız değişen satır yeniden üretilir. Denetim, satırların birbirine ve kendi sahnesinin sonuna taşmadığına bakar. Karakalemin kelime altyazısı bu süreleri kullanır.
- **Müzik** (`muzik.py`). Tempo ve akorlar baştan sona süren tek parça. `sakin`: pad ve çeyrek arpej; `orta`: 1. ve 3. vuruşta davul, hi-hat, uzun bas; `enerjik`: her vuruşta davul, clap, sekizlik bas, yan zincir. Enerji yükselmeden önceki ölçüde yükselen bir dalga, enerjik bölüm girişinde alçak bir vuruş çalar. Konuşurken müzik kendiliğinden 6 dB iner (`platform/ortak/miks.py`: önden bakar, kelime aralarında tutar, cümle aralarında açılır); konuşma müziğin `ses_ustu_db` üstünde kalır. Master `platform/ortak/mastering.py` (-14 LUFS, gerçek tepe korumalı), sonra kalite kapısı.
- **Vuruşa oturan kurgu.** Kesme anı (geçişin ortası) müziğin vuruşuna oturtulur: önceki sahnenin son karesi en çok 1,25 sn tutulur (çoğu zaman bir vuruştan az). Enerji yükselirken kesme güçlü vuruşa (1. ya da 3.) gider; müziğin katmanları ve vurguları da kesme anında değiştiği için hepsi vuruşta olur. Kapatmak için `muzik.vurusa_otur: false`.
- **Sahne efektleri.** Her sahnenin kendi efektleri (kinetiğin whoosh'u, karakalemin kalemi, origaminin katlanması...) şablonun miksinden `efekt.wav` kökü olarak alınır ve kurgu zamanına yerleşir; seviyesi her sahnede konuşmanın `efekt_db` (varsayılan −12 dB) altında, konuşurken 3 dB daha çekilir. Kökler `cikti/is/efektler/` altında önbellekli. Kesmelerde geçiş sesi yalnız kayıtlı kütüphane varsa çalar (hedef sahnenin paletindeki `gecis` rolü; `muzik.gecis_sesi`: `otomatik` / `true` sentez yedeğiyle / `false`). Özet: `cikti/is/ses-raporu.json`.

## Sahne olabilen şablonlar

Bugün: **kinetik** (serbest metin ve süre), **analiz** (veri, grafik, kaynaklı sayılar), **karakalem** (sabit yapı: dağ, basamaklar, damga; 8–20 sn), **tek çizgi**, **kolaj**, **gölge oyunu** ve **origami** (ürün vitrini); desen stilleri **vitray**, **linol**, **cini**, **teknik-cizim** (sahnenin `stil` adı senaryodaki stille aynı olmalı). Yeni bir şablon eklemek `kurgu.py` içindeki `STILLER` tablosuna bir satırdır, yeter ki şablonun `cizim.video(s, W, H, hedef)` işlevi ve bir `yukle` işlevi olsun: minyatür de bu biçimde (`yukle` `minyatur.py`'de). Ancak bazıları içeriğe kilitli olduğu için önce genelleştirilmeli: izometrik, kâğıt kesik, piksel ve hamur "%1 her gün" hikâyesine ve sabit 10 sn yapısına bağlı; origami kahve fincanı vitrinine bağlı. Çizgi roman ve risograf `cizim.video`'ya format da istediği için küçük bir uyarlama ister.

## Bilinen sınırlar

- Karakalemin basamakları kendi `muzik.bpm`'ine göre zamanlanır; vuruşa otursun diye sahne dosyasında kurgununkiyle aynı bpm yazılmalı.
- Kalite kapısının banding ölçüsü, yan yana iki düz rengin bir kanalda 1–16 kod değeri farklı olduğu kenarları basamak sanabiliyor (ör. sarı #FFD23F üstünde turuncu #E0703E: mavi kanalları 63 ve 62). Önizlemede banding uyarısı çıkarsa paletteki yakın kanalı açmak yeter; örnekte turuncu #E2611A oldu.

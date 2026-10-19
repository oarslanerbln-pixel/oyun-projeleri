# platform/sablonlar/neon

Neon logo açılışı: mekân duvarındaki neon tabelanın yanışı gibi 6–10 sn'lik logo animasyonu (Reel, hikâye, video sonu). Renk ve yazı tipi [`marka.json`](../../marka/README.md)'dan, birkaç kelime senaryodan gelir. Görüntü ve müzik kodla üretilir; ücretli servis ve seslendirme yok.

| An (8 sn'de) | Ne olur |
| --- | --- |
| 0,3 | karanlık duvarda iki spot yanar |
| 0,8 | altın halka tepeden saat yönünde kendini çizer, ucunda kıvılcım; duvara sıcak ışık vurur |
| 2,0 | halkanın içinde monogram (ışımayan pirinç, harfler iç içe) aşağıdan süzülür |
| 2,6 | logo yazısı harf harf, kısa titreşimlerle neon tüp gibi yanar |
| 3,9 | logonun altındaki çizgi kalpten iki yana açılır, kalp bir kez atar |
| 4,6 / 5,4 | alt satır (harf aralıklı) ve çağrı belirir; son kare logonun tam yandığı hâlde durur |

Süre değişince bütün anlar orantılı kayar. Işıma 8 bitte dairesel basamak yapmasın diye her kareye ince, her karede değişen tane eklenir ve video `-tune grain` ile kodlanır; kalite kapısı (`platform/ortak/kalite.py`) render'dan sonra kendiliğinden çalışır. Müzik: sıcak Dmaj9 ped, halkada yükselen ses, harflerde yumuşak tık, tam yanışta gümbürtü + açılan akor, kalpte çan arpeji; efektler `platform/ortak/sfx.py`'den (beyaz gürültü yok), -14 LUFS.

```sh
N=platform/sablonlar/neon/neon.py
python3 $N denetle ornekler/demli-kahve/neon.json
python3 $N kare    ornekler/demli-kahve/neon.json --an 1.6 3 7.9     # önizleme kareleri
python3 $N uret    ornekler/demli-kahve/neon.json --format 9:16      # 1080×1920, ~4 dk (CPU)
```

## Senaryo

```json
{
  "kimlik": "le-mariage-neon", "stil": "neon", "dil": "de", "format": "9:16", "sure": 8, "marka": "marka.json",
  "neon": { "logo": "Le Mariage", "monogram": "LM", "ust": "Hochzeit · Henna · Verlobung", "cagri": "Jetzt Besichtigung vereinbaren" }
}
```

| Alan | Ne | Sınır |
| --- | --- | --- |
| `neon.logo` | neon yanan yazı; yoksa marka.json `logo.metin`, o da yoksa marka adı | 18 karakter |
| `neon.monogram` | halkanın içindeki harfler; ilk harf büyük, sonrakiler ayağına biner. Boşsa halka boş kalır | 3 |
| `neon.ust` / `neon.cagri` | alt satır (büyük harf, vurgu rengi) / çağrı | 34 / 34 |
| `neon.kalp` | logo altındaki kalpli çizgi (varsayılan `true`) | |
| `sure` | 6–10 sn (varsayılan 8) | |

| marka.json | Neon'da |
| --- | --- |
| `renk.ana` (yoksa `zemin`) | duvar |
| `renk.isik.sicak` (yoksa `vurgu`) | neon ışıması; tüpün içi bunun beyaza yakın tonu |
| `renk.vurgu` | monogram pirinci |
| `renk.ana-ustu` | çağrı yazısı |
| `yazi.baslik` / `govde` | logo ve monogram / alt satır ve çağrı |

Biçim: `--format 9:16 | 1:1 | 4:5 | 16:9`, yoksa senaryodaki `format`, o da yoksa 9:16. Blok her biçimde güvenli alanın ortasına oturur (9:16'da Reels arayüzü için üst %13, alt %22 boş).

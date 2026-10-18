# platform/sablonlar/golge_oyunu

Karagöz esintili gölge oyunu şablonu (6–20 sn). Düz renkli, aydınlatılmış bir perdenin önünde renkli, yarı saydam deri kuklalar oynar. Kuklaların koyu konturu, zımba delikleri (delikten perde ışığı görünür), eklem pimleri ve aşağı inen kuklacı çubukları vardır. Levhalar önce bulanık, iri bir gölge olarak görünür, perdeye yaklaştıkça keskinleşir. Sahne geçişlerinde kandil bir an kısılır ve büyük bir lale göstermelik perdenin önünden geçer. Müzikte ud ve darbuka çalar, açılışta nareke öter.

Tek bir `golge-oyunu.json` dosyasından görüntü, efektler, müzik ve seslendirme aynı anlara kilitli üretilir. Ücretli bir servis gerekmez. Her kare `t` anının saf fonksiyonudur. 10 sn'lik video 9:16 ve 16:9 formatlarında birlikte yaklaşık 35 sn'de çıkar.

```sh
G=platform/sablonlar/golge_oyunu/golge_oyunu.py
python3 $G denetle   ornekler/kucuk-aliskanliklar/golge-oyunu.json
python3 $G seslendir ornekler/kucuk-aliskanliklar/golge-oyunu.json          # platform/ses (Piper fahrettin); --saglayici elevenlabs --ses <id>
python3 $G kare      ornekler/kucuk-aliskanliklar/golge-oyunu.json --an 2.5 4.9 --format 16x9   # önizleme PNG
python3 $G render    ornekler/kucuk-aliskanliklar/golge-oyunu.json          # → cikti/<kimlik>-9x16.mp4 (--format 9x16 16x9 1x1 4x5)
```

Format önceliği şöyledir: önce `--format`, yoksa senaryonun `format` alanı, o da yoksa 9x16. İki format ancak açıkça istenirse birlikte çıkar.

Gerekenler: `pip install skia-python numpy soundfile` (scipy varsa efekt filtreleri hızlanır), ffmpeg ve Inter yazı tipi. Linux'ta `apt-get install libegl1 libgl1 fonts-inter` yeter; yazı tipi başka bir klasördeyse `KINETIK_FONT_DIZINI` ile gösterilir. `denetle` yalnız standart kütüphaneyle çalışır.

## Senaryo

```json
{
  "kimlik": "kucuk-adimlar-golge", "sure": 10, "fps": 30, "format": "9x16",
  "palet": {"perde": "#F2DDB0", "govde": "#2E7D4F", "vurgu": "#B83A2E"},
  "kukla": {"entari": "govde", "kulah": "vurgu", "bacak": "lacivert"},
  "muzik": {"bpm": 100, "makam": "hicaz", "nareke": true},
  "seslendirme": {"satirlar": [{"id": "v0", "t": 0.3, "metin": "Her gün, sadece yüzde bir daha iyi ol."}]},
  "sahneler": [
    {"tur": "yuruyus", "bas": 0, "giris_t": 0.15, "kol_t": 1.45, "levha": {"metin": "%1", "t": 1.35}},
    {"tur": "kapanis", "bas": 8, "bayrak_t": 8.25, "levha": {"metin": "BUGÜN BAŞLA", "t": 8.35}}
  ]
}
```

Bütün anlar videonun başından itibaren saniyedir. Bir sahne, bir sonraki sahnenin `bas` anına kadar sürer. Sahneler istenen sırada ve sayıda kullanılabilir.

| Sahne (`tur`) | Ne olur | Alanlar |
| --- | --- | --- |
| `yuruyus` | Kahraman soldan yürüyerek girer (1,5 sn), durur, kolunu levhaya kaldırır | `giris_t` (zorunlu), `kol_t`, `levha` |
| `merdiven` | Basamaklar alttan sırayla yükselir, kahraman basamak basamak sekerek çıkar, tepede kolunu kaldırır | `t` (merdiven kurulur), `tirman_t`, `tirman_sure` (1,0), `basamak` (3–10, varsayılan 7), `zafer_t`, `levha` |
| `agac` | Filiz çıkar, hayat ağacı büyür, dallarda yapraklar ve laleler sırayla açılır | `t` (büyüme), `filiz_t`, `levha` (verilirse ağaç sola kayar) |
| `kapanis` | Kahraman ve dalgalanan bayrak, üstte levha | `bayrak_t`, `kol_t`, `levha` |

Her sahnede ortak olan alanlar:

- **`levha`:** `{metin, t, renk, boy, zil}`. Yazı levhaya delik olarak açılır, bu yüzden perde ışığı harflerin içinden görünür. Levhanın boyu metne göre kendiliğinden ayarlanır; `boy` bunun için bir üst sınır koyar. `zil` alanı ilk sahne dışındaki levhalarda varsayılan olarak açıktır.
- **`gecis`:** `lale` (ilk sahne dışında varsayılan; kandil kısılır, lale göstermelik geçer, ortası sahne başına denk gelir) ya da `kesme`.
- **`muzik`:** Müziğin o sahnedeki kipi; aşağıdaki Ses bölümüne bakın.

## Renk ve kukla

Renkler rollerle verilir: `perde`, `isik` (deliklerden sızan ışık), `cerceve`, `cerceve_cizgi`, `kontur`, `govde`, `vurgu`, `altin`, `lacivert`, `ten`, `turuncu`, `yaprak`, `toprak`, `gece` (geçişte kısılan kandilin rengi). `palet` alanı yalnız değişen rolleri ezer, gerisi varsayılan Karagöz paletinden gelir.

`kukla` alanı, kahramanın parçalarını (`entari`, `kusak`, `kulah`, `kol`, `bacak`, `pabuc`, `ten`) palet rollerine bağlar. Marka renklerine geçmek için çoğu zaman `palet` içinde birkaç rolü değiştirmek yeter.

Perde ve bütün dolgular düz renktir: degrade, parlama ya da metnin arkasında halka yoktur. Yalnız levhanın yaklaşma bulanıklığı ve kandilin kısılması geçicidir.

## Ses

- **Müzik:** `muzik.makam` alanı `hicaz`, `kurdi`, `nihavent` ya da `rast` olabilir; hepsi Re üzerinde, en yakın yarım sese yuvarlanmış olarak çalar. Her sahnenin `muzik` kipi şunlardan biridir:
  - `taksim`: serbest bir ud cümlesi ve dem.
  - `ritim`: düyek usulünde darbuka ile sekizlik ud ezgisi.
  - `sakin`: iki uzun nota, ardından ritim.

  Varsayılan kipler sahne türüne göre şöyledir: yürüyüş `taksim`, merdiven `ritim`, ağaç `sakin`, kapanış `ritim`. Son sahne bir oktav yukarıda çalar. Video, makamın dağıtılmış akoruyla biter.
- **Efektler:** Açılışta nareke (`muzik.nareke`) öter. Levhalar tahta tıkırtısı ve zil sesiyle, geçişler perde hışırtısıyla gelir. Merdivende basamak tıkırtıları, ağaçta yaprak hışırtıları duyulur. Hepsi `zaman.ses_olaylari` içinde, görüntüyle aynı anlardan hesaplanır.
- **Seslendirme:** `cikti/seslendirme/<id>.wav` dosyalarından okunur. Müzik konuşmanın 8 dB altında tutulur ve konuşma sırasında 3 dB daha kısılır.
- **Master:** Diğer şablonlarla aynıdır: 16 kHz alçak geçiren filtre, -14 LUFS ve tepe sınırlayıcı.

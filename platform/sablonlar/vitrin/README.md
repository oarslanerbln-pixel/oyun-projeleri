# platform/sablonlar/vitrin

3D ürün vitrini: ürün stüdyo ışığında kaidenin üstünde döner, özellikleri birer birer belirir, marka adı ve çağrı düğmesiyle biter. E-ticaret, lansman ve ürün reklamları için 6–20 sn. Ücretli servis gerekmez: görüntü three.js ile başsız Chromium'da çizilir, müzik ve efektler numpy ile sentezlenir. Her kare `t` anının saf fonksiyonudur.

```sh
V=ornekler/demli-kahve/vitrin.json
python3 platform/sablonlar/stil/stil.py uret    $V --stil urun-vitrini                 # tek adım: seslendirme yoksa üretir, sonra render (9:16)
python3 platform/sablonlar/stil/stil.py uret    $V --stil urun-vitrini --format 16:9
python3 platform/sablonlar/vitrin/vitrin.py denetle $V
python3 platform/sablonlar/vitrin/vitrin.py kare    $V --an 2.8 9.8 --olcek 0.5        # hızlı önizleme kareleri
```

Çıktı senaryonun yanındaki `cikti/`: `<kimlik>-urun-vitrini-<format>.mp4` (H.264 + AAC, -14 LUFS) ve `-kapak.png`. Biçim stil.py ile aynı kuralla seçilir: `--format`, yoksa senaryodaki `"format"`, yoksa yalnız 9:16. Dikeyde ürün üstte, yazı altta; yatayda ürün solda, yazı sağda.

## Senaryo (`vitrin.json`)

| Alan | İçerik |
| --- | --- |
| `marka` | marka.json yolu (depo köküne göre). `ana`, `ana-ustu`, `vurgu`, `vurgu-ustu` renkleri gerekli; `isik.sicak` varsa anahtar ışık rengi olur |
| `sure`, `format`, `muzik.tempo` | 6–20 sn (varsayılan 12), biçim, 70–140 BPM (varsayılan 96) |
| `urun.tur` | kodla kurulan ürün: `paket` (ayakta duran kahve paketi, aroma valfli) ya da `kutu` |
| `urun.model` | gerçek ürün için `.glb`/`.gltf`; verilince `tur` yok sayılır. Tabanı kaideye oturur, boyu `model_boy` (varsayılan 3.2) birime ölçeklenir |
| `urun.etiket`, `ust`, `alt`, `agirlik`, `govde` | kodla kurulan ürünün ön baskısı (etiket yoksa logo metni) ve gövde rengi |
| `urun.sus` | kaide süsü: `kahve-cekirdegi` ya da boş |
| `ozellikler` | en çok 4: `metin` (≤18), `alt` (≤32), `odak`: `on`, `ust`, `yan`, `alt`. Kamera her özellikte ürünün o bölgesine döner, odakta halka belirir |
| `final` | `logo` (yoksa marka logosu), `cagri` (düğme, ≤18), `alt` (adres, ≤28) |
| `seslendirme.satirlar` | isteğe bağlı: `id`, `metin`, `t` (saniye ya da `"final"`). Varsa müzik konuşmanın altında kısılır |

Zamanlar müzik ızgarasına oturtulur: giriş (karanlıktan ışık açılır, ürün yükselerek döner) → her özellik bir bölüm (yumuşak davul, her girişte zil) → final (yükseliş, vuruş, parlak son akor; ürün öne döner). Özelliksiz senaryo 6 sn bumper olarak da çalışır.

## Denetimler

**HATA** üretimi durdurur: süre/tempo aralık dışı, marka geçersiz ya da renk eksik, ürün türü/modeli yok, 4'ten çok özellik, karakter sınırı aşımı, bölüm 1,4 sn'den kısa (süre yetmiyor), seslendirme dosyası yok ya da video sonuna taşıyor, metinde marka yasak sözcüğü.

## Gerekenler

Node 18+ ve ffmpeg; `npm install` (three 0.170, playwright) ilk render'da kendiliğinden çalışır, tarayıcı indirmez (`CHROMIUM` ortam değişkeni ya da Playwright'ın kurulu Chromium'u). Python: `numpy soundfile fonttools` (+ seslendirme için `sherpa-onnx`). Yazı tipi Inter (SIL OFL 1.1), stil şablonuyla aynı önbellekten (`~/.cache/studyo/fonts`).

Render süresi GPU'suz 4 çekirdekte 12 sn'lik bir biçim için yaklaşık 10 dakika (kare başına ~1,6 sn, SwiftShader); GPU'lu makinede çok daha hızlı. Prova için `--olcek 0.5`.

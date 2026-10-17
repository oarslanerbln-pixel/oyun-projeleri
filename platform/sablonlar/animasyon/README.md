# platform/sablonlar/animasyon

Animasyon videosu hattının depoda yaşayan ilk yarısı (mimari §5.1): **brif → metin → çekim listesi → animatik**. Animatik zamanlamayı ve yerleşimi V1 kapısında onaylatmak içindir; son görüntü depo dışındaki araçlarda yapılır.

```sh
python3 platform/sablonlar/animasyon/animasyon.py yeni musteriler/acme --ad "Acme"
python3 platform/sablonlar/animasyon/animasyon.py denetle musteriler/acme/proje.json
python3 platform/sablonlar/animasyon/animasyon.py uret musteriler/acme/proje.json   # → musteriler/acme/cikti/
```

Örnek: [`ornekler/demli-kahve/`](../../../ornekler/demli-kahve) (14 sn dikey/kare/4:5 + 6 sn bumper, TR/EN).

## Proje

`proje.json` (yollar depo köküne göre):

```json
{
  "kimlik": "demli-kahve-sabah", "tur": "animasyon",
  "marka": "…/marka/marka.json", "diller": ["tr", "en"],
  "metin": { "tablolar": ["…/metin/metin.csv"], "sozlukler": ["platform/metin/temel.tsv"] },
  "brif": "…/docs/01-oz/brif.json",
  "kurgular": [{ "ad": "sabah-14", "cekimler": "…/docs/04-yapi/cekimler-sabah-14.csv", "fps": 30,
                 "teslim": ["dikey", "kare", "dikey-akis"] }]
}
```

- **Brif** (`01-oz`): `hedef, kitle, icgoru, onerme, olcut` zorunlu; `cagri`, `kanitlar`.
- **Kurgu:** bir çekim listesi, bir kare hızı, bir ya da daha çok teslim ön ayarı. Aynı brif birden çok kurgu taşır (15 sn dikey, 6 sn bumper).
- **Çekim listesi** (`04-yapi`): mimarideki sütunlar (`cekim, sure_sn, metin_anahtari, gorsel, kamera, gecis, odak_x, odak_y, sinif, durum`) + animatik için `ekran` (ekran yazısının metin anahtarı), `zemin`, `on` (marka renk adları), `logo`, `cagri` (`evet`). `gecis`: `kesme | erime | kayma`; `durum`: `animatik | uretim | onay | kilit`; `sinif`: `A | B | C | elle`.

## Denetimler

**HATA** üretimi durdurur, **UYARI** durdurmaz.

| Denetim | Düzey |
| --- | --- |
| Marka şeması ve kontrast çiftleri (`platform/marka`) | HATA |
| Metin tablosu: yasak ifade (temel + proje + marka), `azami` uzunluk | HATA |
| Çekimde tanımsız metin anahtarı ya da renk adı | HATA |
| Ekran yazısı kontrastı < 3.0 (WCAG büyük metin) | HATA |
| Kurgu süresi ön ayarın sınırını aşıyor (örn. bumper 6 sn) | HATA |
| Brifte zorunlu alan boş; bilinmeyen ön ayar; desteklenmeyen fps | HATA |
| Seslendirme > 2.5 sözcük/sn, ekran yazısı > 3 sözcük/sn | UYARI |
| Kısa biçimde logo ilk 3 sn'de yok; brifte çağrı var ama çekimde yok | UYARI |
| Önerme 12 sözcüğü aşıyor ya da "ve" içeriyor; kanıt yok; çeviri boş | UYARI |

## Çıktılar (`cikti/`, depoya girmez)

```
brif.md                                   müşteriye giden tek sayfa
marka/tokens.css figma.json unity.uss unity.json prompt.txt
<kurgu>/manifest.json                     araçtan bağımsız zaman çizelgesi (kare aralıkları, odak, hareket)
<kurgu>/altyazi.<dil>.srt | .vtt          seslendirme satırlarından, zaman çekim listesinden
<kurgu>/<ön ayar>/kareler/NN-cekim.svg    güvenli alana göre yerleşik kareler
<kurgu>/<ön ayar>/animatik.html           tarayıcıda oynar: zaman çubuğu, kare sayacı, geçişler, kamera itme/çekme, kılavuz aç/kapa
```

Karelerde kılavuz katmanı (görsel notu, kamera, YZ sınıfı, güvenli alan, kırpma odağı) animatikte kapatılabilir.

`manifest.json` Clipkit, DaVinci (EDL/FCPXML) ve Unity Timeline bağdaştırıcılarının girdisidir; bağdaştırıcılar faz 3'te ilk gerçek işle yazılır.

## Kod

| Dosya | Görev |
| --- | --- |
| `animasyon.py` | Komut satırı |
| `proje.py` | `proje.json` + brif; bütün katmanları birlikte yükler ve doğrular |
| `cekimler.py` | Çekim listesi, zaman çizelgesi, kurgu denetimleri |
| `cizim.py` | SVG kareler, animatik, manifest, altyazı |
| `sablon/` | `yeni` komutunun kopyaladığı proje iskeleti |
| `_yollar.py` | Kardeş modülleri (`marka`, `metin`, `medya`) yükler; `platform` adı Python paketi olamaz (standart kitaplığı gölgeler) |

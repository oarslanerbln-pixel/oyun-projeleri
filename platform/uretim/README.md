# platform/uretim

Animasyon hattının YZ üretim adımı: çekim listesindeki **`sinif=C`** (öne çıkan) çekimleri bir video sağlayıcısına gönderir, her çıktıyı yapay zekâ kaydına (`yz-kaydi.csv`, mimari §4.4) yazar. Geri kalan her şey (yazı, logo, CTA, geçişler) kod katmanında kalır; YZ yalnız birkaç saniyelik kahraman çekimlerinde para harcar.

```sh
python3 platform/uretim/uretim.py plan     ornekler/demli-kahve/proje.json            # iş ve maliyet, para harcamaz
python3 platform/uretim/uretim.py calistir ornekler/demli-kahve/proje.json            # → <proje>/cikti/uretim/
python3 platform/uretim/uretim.py plan     ornekler/demli-kahve/proje.json --saglayici veo-lite   # başka sağlayıcıyla tahmin
python3 platform/uretim/uretim.py denetle  ornekler/demli-kahve/proje.json            # lisans kapısı (V3)
python3 platform/medya/turev.py klip.mp4 dikey.mp4 dikey --odak 0.6 0.4               # oran türevi + loudness
python3 platform/sablonlar/animasyon/animasyon.py render ornekler/demli-kahve/proje.json   # klip + yazı katmanı → MP4
```

## Ayar (`proje.json`)

```json
"uretim": { "saglayici": "fal-kling", "butce_usd": 20, "azami_deneme": 2, "tohum": 1, "ticari": true },
"yz_kaydi": "…/yz-kaydi.csv"
```

`yz_kaydi` verilmezse kayıt proje klasöründe `yz-kaydi.csv` olur ve depoya girer; çıktı dosyaları `cikti/` altında kalır, depoya girmez.

## Kurallar

| Kural | Nasıl |
| --- | --- |
| **Önce şablon denetimi** | Proje `animasyon.py denetle`'den HATA'sız geçmezse plan kurulmaz. |
| **V1'den önce para yok** | Yalnız `durum=uretim` çekimler üretilir. `animatik` "V1 bekliyor", `onay`/`kilit` "kilitli" görünür, maliyeti 0. |
| **Faturalı süre** | Sağlayıcı yalnız belli süreleri üretir (`saglayicilar.json` → `sureler`). 3 sn'lik çekim Kling'de 5 sn faturalanır; tahmin bunu hesaba katar. En uzun süreyi aşan çekim HATA: bölünmeli. |
| **Bütçe kesici** | Kayıttaki harcama + bu plan > `butce_usd` ise plan HATA verir; `calistir` her işten önce yeniden bakar. |
| **Önbellek** | İstek özeti = SHA-256(sağlayıcı, model, prompt, negatif, anahtar karenin içeriği, faturalı süre, tohum). Aynı istek kayıttaysa ikinci kez ödenmez. Dosya bu makinede yoksa "kayıtta" görünür ve yine ödenmez; `--yeniden` zorlar. |
| **Lisans kapısı** | Proje `ticari: true` ise ticari kullanıma kapalı sağlayıcı (Kling/Flow ücretsiz katmanları) seçilemez. `denetle`: `onay`/`kilit` her C çekiminin en son kaydı `lisans=ticari` olmalı; `kuru` prova çıktısı teslime giremez. |
| **Yeniden deneme** | Sağlayıcı hatasında `azami_deneme` kez, tohum bir artırılarak. Başarısız deneme kayda yazılmaz, bütçeden düşülmez. Kalite yüzünden yeniden üretim elle: `tohum` değiştirilir, istek özeti değişir. |
| **Prompt** | Markanın `prompt.uslup` cümlesi + çekimin `gorsel` ve `kamera` sütunları. `prompt.negatif` ayrı alana (`negative_prompt`) gider. |

Çekim listesine bir sütun eklendi: **`anahtar_kare`** (depo köküne göre başlangıç karesi). Görüntüden video üreten sağlayıcılarda zorunlu; marka tutarlılığı en çok bununla sağlanır.

## Sağlayıcılar (`saglayicilar.json`)

| Ad | Tür | Durum |
| --- | --- | --- |
| `kuru` | prova | Ağa çıkmaz, isteği `.kuru.json` olarak yazar. Örnek proje ve CI bununla çalışır. |
| `fal-kling` | `fal` | fal.ai kuyruk API'si yazıldı (`FAL_KEY`), sahte HTTP ile test edildi; **gerçek anahtarla henüz denenmedi.** Model yolu ve fiyat ilk işten önce fal.ai'de doğrulanmalı. |
| `veo-lite`, `runpod-wan`, `yerel-wan` | `henuz-yok` | Yalnız tahmin; bağdaştırıcı sırada. |
| `kling-ucretsiz`, `flow-ucretsiz` | `elle` | Araç dışında üretilip kayda elle girilen çıktılar için; çağrılamaz, ticari değil. |

Yeni bağdaştırıcı `saglayici.py` içinde `uret(is_, hedef, ayar, ag) -> Path` imzalı bir işlevdir ve `BAGDASTIRICILAR`'a tür adıyla eklenir.

## Kayıt sütunları

Mimarideki `dosya, sinif, model, tarih, prompt, kullanildigi_yer, kaynak_ozeti, arac, duzenleme` + üretim için `istek_ozeti` (önbellek anahtarı), `maliyet_usd`, `lisans` (`ticari | ticari-degil | kuru`), `tohum`. `kaynak_ozeti` çıktı dosyasının SHA-256'sıdır (dosya yeniden adlandırılsa da bulunur), `istek_ozeti` isteğin.

## Sırada

- Klipleri makineler arasında paylaşmak için bulut depolama (R2/S3); bugün dosya yalnız üretildiği makinede.
- `veo-lite` (taslak) ve `yerel-wan`/`runpod-wan` (ComfyUI API) bağdaştırıcıları.
- Kalite kapısı: üretilen klipten birkaç kare çıkarıp marka ve hata denetimi (Claude ile); bugün onay elle `durum=onay`.

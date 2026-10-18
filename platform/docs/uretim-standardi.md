# Üretim standardı

Stüdyoda her videonun aynı yoldan geçmesi için çalışma kuralları. Amaç iki şey: **kalite her teslimde aynı**, **maliyet ölçülü ve öngörülebilir**. Kurallar 18 Ekim 2026'da Atilla'nın onayıyla konuldu; gerekçeleri ve ölçümler `/mnt/project-files/gelistirme/gelistirme-plani.md` G bölümünde.

## 1. İş türleri

| Tür | Ne | Nerede | Düşünme seviyesi |
| --- | --- | --- | --- |
| **Üretim** | Hazır şablondan video: sipariş, müşteri işi, kanal videosu | Siparişe özel kısa thread | Orta |
| **Revizyon** | Teslim edilmiş bir videoda değişiklik | Yeni kısa thread, eski teslimin özetiyle başlar | Orta |
| **Geliştirme** | Yeni stil, şablona yeni sahne türü, altyapı | Ayrı geliştirme thread'i, taslak PR | Yüksek |
| **Araştırma** | Araç, fiyat, rakip, veri | Ayrı thread, sonucu bir dosyada | Orta |

Üretim sırasında şablonda eksik çıkarsa (ör. yeni bir sahne türü gerekirse) üretim thread'i şablonu kendi değiştirmez; eksik bir geliştirme işi olarak açılır, üretim mevcut şablonla devam eder.

## 2. Sipariş akışı

| # | Adım | Çıktı | Kural |
| --- | --- | --- | --- |
| 1 | **Brif** | Aşağıdaki şablonla doldurulmuş kısa brif | Eksik bilgi için makul varsayılan seçilir ve yazılır; yalnız geri dönüşü olmayan kararlar sorulur |
| 2 | **Senaryo + önizleme** | Senaryo metni ve tek önizleme sayfası (`onizleme.py`) | Tam render yok, seslendirme yok. Birden çok stil isteniyorsa her stil için 3 kare, tek sayfada |
| 3 | **Onay** | Atilla'nın "tamam" ya da düzeltmesi | Onaysız tam render yapılmaz (Atilla "direkt üret" demedikçe) |
| 4 | **Seslendirme** | `seslendirme/*.wav` | Varsayılan Piper. ElevenLabs yalnız brif isterse; önce tek kısa satırla ses denenir, sonra tam metin bir kez üretilir |
| 5 | **Render** | Yalnız brifteki format(lar) | Seçilen stil(ler) için, bir kez |
| 6 | **Kalite kapısı** | `<ad>.kalite.json`, `<ad>.kontakt.png` | Sonuç `kaldi` ise teslim edilmez, düzeltilir. `uyarili` ise uyarının nedeni teslim mesajında bir cümleyle yazar. Claude yalnız kontakt sayfasına bakar, kareleri tek tek açmaz |
| 7 | **Teslim ve kapanış** | Teslim klasörü, `DEVIR.md`, maliyet satırı | Teslim mesajı: dosyalar, kalite sonucu, harcanan ses kredisi. `devir.py` ile devir özeti yazılır (kararlar ve Atilla'nın geri bildirimi `--not` ile), maliyet satırı eklenir, thread kapanır |

```sh
# 2. adım: önizleme (birkaç saniye; ses ve video yok)
python3 platform/ortak/onizleme.py kolaj=is/kolaj.json origami=is/origami.json -o is/onizleme.png
# 5–6. adım: render; kalite kapısı kendiliğinden çalışır
python3 platform/sablonlar/stil/stil.py uret is/senaryo.json --stil <ad> --format 9:16
# 7. adım: devir özeti (her teslimde güncellenir; önceki notlar korunur)
python3 platform/ortak/devir.py /mnt/project-files/<müşteri> --not "Atilla tabağın büyük görünmesini istedi"
```

## 3. Teslim tanımı (hepsi sağlanmadan "teslim" denmez)

- Kısa kenar en az 1080 px, 24 fps ve üstü, H.264 / yuv420p.
- Kalite kapısı `gecti` ya da gerekçeli `uyarili`: banding yok, ses -14 LUFS ±1, gerçek tepe -1 dBTP altında, ortada siyah ya da donmuş kare yok.
- Bütün yazı ve hareketli öğeler ekranın içinde; dikey videoda platform arayüzünün kapattığı bölgede (kontakt sayfasında kırmızı) yazı yok.
- Müzik var (Atilla'nın içerik kuralı); ses ve müzik lisansı teslim klasöründe yazılı.
- Marka renkleri ve logo marka dosyasından; metin yazım ve rakam kontrolünden geçmiş (fiyat, tarih, adres).
- Yalnız istenen formatlar; dosya adları `<marka>-<konu>-<stil>-<format>.mp4`.
- Panel, açılış sayfası ya da HTML teslimi: sayfa kapısı (`platform/ortak/sayfa.py`) `gecti` ya da gerekçeli `uyarili`; telefonda yana kayma, ekrandan taşan öğe, okunmaz kontrast ve kırık görsel yok. Claude yalnız `<ad>.sayfa.png` kontakt sayfasına bakar.
- YZ görseli (`platform/uretim/gorsel.py`): önce `flux-schnell` taslak varyantları, seçilen fikir final modelle (`flux-ultra`, `recraft`, `recraft-svg`) bir kez. Final görsel hedefe büyütülmez; `gorsel-kaydi.csv` teslim klasöründe kalır (model, maliyet, lisans).

## 4. Revizyon

- Revizyon yeni bir thread'de başlar ve yalnız teslim klasöründeki `DEVIR.md`'yi, brifi ve istenen değişikliği okur. Eski thread okunmaz, eski konuşma taşınmaz; gereken her şey (dosyalar, kalite sonucu, yeniden üretme komutu, kararlar) devir dosyasındadır.
- Revizyon bitince `devir.py` yeniden çalışır ve yeni kararlar `--not` ile eklenir.
- Yalnız değişen şey yeniden üretilir: metin değiştiyse o satırın sesi (gerisi önbellekten gelir) ve yalnız ilgili format.
- Aynı videoda üçüncü revizyon turu gelirse sebep brife yazılır (brif mi eksikti, şablon mu yetmedi) ki bir sonraki siparişte tekrarlanmasın.

## 5. Maliyet kuralları

1. **Bir sipariş, bir kısa thread.** Teslimde kapanır. Uzun yaşayan thread her adımda bütün geçmişini yeniden okur; maliyetin üçte ikisi buradan geliyordu.
2. **Şablondan üretim tek komutla.** Üretim thread'i şablon kodu yazmaz.
3. **Önce önizleme, sonra tek render** (akıştaki 2. ve 3. adım).
4. **Çok stilli isteklerde önce kareler, sonra 1–2 video.** Bütün stillerin tam videosu yalnız açıkça istenirse.
5. **Kalite kapısı göz yerine.** Claude kareleri tek tek açmaz; `kalite.json` raporunu ve tek kontakt sayfasını okur. Önizlemede de yalnız `onizleme.png` açılır. Bir görüntü dosyası, aynı bilgiyi taşıyan birkaç kareden çok daha az token tutar.
6. **Devir dosyası hafıza yerine.** Bir işe dönülürken thread geçmişi değil `DEVIR.md` okunur.
7. **Aynı anda en fazla 3 iş thread'i.** Fazlası sıraya girer; haftalık kullanım limiti bir günde dolmasın.
8. **Ses:** Piper varsayılan; ElevenLabs işe göre, önbellekten, önce kısa deneme.

## 6. Ölçüm

Her sipariş thread'i kapanırken `/mnt/project-files/gelistirme/maliyet.csv` dosyasına bir satır ekler. Kullanım sayacı oturumun kendi kaydından (`get_session` → `external_metadata.usage`) okunur, tahmin edilmez.

```
tarih,is,tur,stil_sayisi,video_sayisi,revizyon_turu,cevap_sayisi,cikti_token,onbellek_okuma_token,kullanim_usd,elevenlabs_karakter
```

Her ayın başında bu dosyadan video başına ortalama çıkarılır; hedef şablondan kısa video başına 1–2 $.

## 7. Brif şablonu

```
İş: <marka / kanal> — <konu>
Tür: üretim | revizyon (önceki teslim: <klasör>)
Amaç ve hedef kitle: <bir cümle>
Stil(ler): <ad>  (birden çoksa: önce önizleme, sonra seçilen 1–2'si)
Format: 9:16 | 16:9 | 1:1 | 4:5   Süre: <sn>   Dil: tr | de
Ses: yok | Piper <ses> | ElevenLabs <ses>   Müzik: <ruh hâli>
Metin: <ekrandaki kısa metinler; fiyat, tarih, adres aynen>
Marka: <marka.json yolu ya da renk + logo>
Teslim: <proje klasörü yolu>   Son tarih: <tarih>
```

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
| 4 | **Seslendirme** | `seslendirme/*.wav` | Varsayılan ElevenLabs (bkz. §8). Yeni bir ses ilk kez kullanılacaksa önce tek kısa satırla denenir, sonra tam metin bir kez üretilir. İş, kalan kredi yetmezse başlamaz |
| 5 | **Render** | Yalnız brifteki format(lar) | Seçilen stil(ler) için, bir kez |
| 6 | **Kalite kapısı** | `<ad>.kalite.json`, `<ad>.kontakt.png` | Sonuç `kaldi` ise teslim edilmez, düzeltilir. `uyarili` ise uyarının nedeni teslim mesajında bir cümleyle yazar. Claude yalnız kontakt sayfasına bakar, kareleri tek tek açmaz |
| 7 | **Teslim ve kapanış** | Teslim klasörü, `DEVIR.md`, maliyet satırı | Teslim mesajı: dosyalar, kalite sonucu, harcanan ses kredisi. `devir.py` ile devir özeti yazılır (kararlar ve Atilla'nın geri bildirimi `--not` ile), maliyet satırı eklenir, thread kapanır |

**Tek komut (önerilen):** adımlar 2–7 `platform/ortak/uret.py siparis.json` ile yürür; önizlemede durur, `--onay` ile ses + render + kalite kapısı + `DEVIR.md`, `--kapat` ile maliyet satırı. Komut sırası `.claude/skills/siparis-uretimi/SKILL.md`'de. Aşağıdaki tek tek komutlar elle iş içindir.

```sh
# 2. adım: önizleme (birkaç saniye; ses ve video yok)
python3 platform/ortak/onizleme.py kolaj=is/kolaj.json origami=is/origami.json -o is/onizleme.png
# 5–6. adım: render; kalite kapısı kendiliğinden çalışır
python3 platform/sablonlar/stil/stil.py uret is/senaryo.json --stil <ad> --format 9:16
# uzun video: birden çok şablonun sahneleri tek videoda (önizleme → seslendirme → render, aynı kurallar)
python3 platform/sablonlar/kurgu/kurgu.py onizle is/kurgu.json && python3 platform/sablonlar/kurgu/kurgu.py uret is/kurgu.json
# 7. adım: devir özeti (her teslimde güncellenir; önceki notlar korunur)
python3 platform/ortak/devir.py /mnt/project-files/<müşteri> --not "Atilla tabağın büyük görünmesini istedi"
```

## 3. Teslim tanımı (hepsi sağlanmadan "teslim" denmez)

- Kısa kenar en az 1080 px, 24 fps ve üstü, H.264 / yuv420p.
- Kalite kapısı `gecti` ya da gerekçeli `uyarili`: banding yok, ses -14 LUFS ±1, gerçek tepe -1 dBTP altında, ortada siyah ya da donmuş kare yok.
- Bütün yazı ve hareketli öğeler ekranın içinde; dikey videoda platform arayüzünün kapattığı bölgede (kontakt sayfasında kırmızı) yazı yok.
- Müzik var (Atilla'nın içerik kuralı); ses ve müzik lisansı teslim klasöründe yazılı.
- Seslendirme ElevenLabs ile. Kalite raporunda `seslendirme` uyarısı (Piper yedeği) varsa teslim edilmez; kredi ya da anahtar sorunu çözülüp yeniden seslendirilir.
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
8. **Ses:** ElevenLabs varsayılan; satırlar önbellekten tekrar kullanılır, kredi boşa harcanmaz (bkz. §8).
9. **Thread sınırı.** Bir thread ~250k bağlama ya da ~12 cevaba ulaşınca yeni tur o thread'de başlamaz: `devir.py` ile `DEVIR.md` yazılır, iş yeni thread'de sürer. Aynı siparişin revizyonları da buna dahildir (19 Ekim'de Markalaşma 18, Al-Andalus 16, e-kitap 28 cevaba çıktı).
10. **Az adım, kısa çıktı.** Maliyet ≈ adım sayısı × bağlam boyu. Komutlar tek Bash çağrısında birleştirilir; uzun komutlar `platform/ortak/sessiz.py` ile çalışır; büyük JSON ve loglar olduğu gibi okunmaz. Kısa kurallar repo kökündeki `CLAUDE.md`'de, her oturum otomatik okur.
11. **Alt ajan yalnız gerektiğinde.** Her alt ajan ~60–70k token ile sıfırdan başlar.
12. **Kullanılmayan eklenti ve bağlantılar kapalı.** Hesaptaki her eklentinin beceri listesi ve her bağlantının araç listesi, her thread'in her adımında okunan ~130k'lık başlangıç bağlamına girer (19 Ekim: 60 eklenti, ~440 beceri, ~65 MCP sunucusu; çoğu bu projede hiç kullanılmadı).

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
Ses: ElevenLabs <ses> (varsayılan) | yok | Piper (yalnız bilerek)   Müzik: <ruh hâli>
Metin: <ekrandaki kısa metinler; fiyat, tarih, adres aynen>
Marka: <marka.json yolu ya da renk + logo>
Teslim: <proje klasörü yolu>   Son tarih: <tarih>
```

## 8. Seslendirme

Atilla, 2026-10-19: "ses kullanımını ElevenLabs'ten yapalım, diğer sesler çok mekanik."

- **Sağlayıcı:** `otomatik` (bütün şablonların varsayılanı) ElevenLabs demektir (`eleven_multilingual_v2`, Türkçe ve Almanca). Bütün şablonlar sesi tek yerden alır: `platform/ses/seslendirme.py` (`senaryodan`).
- **Piper yalnız yedek:** anahtar yoksa, `api.elevenlabs.io`'ya ulaşılamazsa ya da kalan kredi işe yetmezse bütün iş Piper ile (Türkçe `fahrettin`, Almanca `thorsten`/`kerstin`) üretilir, render durmaz. `seslendirme.json`'a `yedek` yazılır ve kalite raporu `seslendirme` uyarısı verir; bu video teslim edilmez. Senaryoda `"seslendirme": {"saglayici": "piper"}` yalnız bilerek seçilen durumlar içindir (deneme, iç önizleme).
- **Kredi koruması:** iş başlamadan hesapta kalan kredi sorulur. Önbellekte olmayan satırların toplamı kalandan fazlaysa tek satır bile üretilmez (yarım ElevenLabs, yarım Piper iş olmaz). `--saglayici elevenlabs` açıkça verilmişse iş hatayla durur.
- **Önbellek:** aynı metin + ses + ayar ikinci kez kredi harcamaz (`/mnt/project-files/.onbellek/ses`). Revizyonda yalnız değişen satır yeniden üretilir.
- **Ses seçimi:** senaryoda `seslendirme.ses`: havuzdan bir ad ya da bir voice_id; yoksa `ELEVENLABS_VOICE_ID_TR` / `_DE`, o da yoksa dilin varsayılanı. Liste: `seslendirme.py sesler`.

  | Ad (`seslendirme.ses`) | Ses | Ne zaman |
  | --- | --- | --- |
  | `george` | erkek, sıcak anlatıcı | **Türkçe anlatım varsayılanı** (Atilla, 2026-10-19 denemesinde seçti) |
  | `turk-haber` | erkek, İstanbul aksanlı haber sesi | anadil tınısı istenen Türkçe işler, haber/analiz |
  | `bella` | kadın, parlak ve sıcak | kadın anlatıcı; Almanca reklamlar (Lezzet Dünyası) |
  | `matilda` | kadın, bilgilendirici | kadın varsayılanı |
  | `liam` | erkek, enerjik | sosyal medya, hızlı kurgular |

  Denemeler: `/mnt/project-files/elevenlabs-ses/turkce-deneme/`. Yeni ses havuza `ELEVEN_ADLI_SESLER`'e eklenir (yalnız ücretsiz planda çalışan, kısa satırla denenmiş sesler).
- **Takip:** `seslendirme.py kredi` hesapta kalanı, `seslendirme.py kullanim` iş başına harcamayı gösterir. Teslim mesajı harcanan karakteri, maliyet satırı `elevenlabs_karakter`'i yazar.
- **Plan ve lisans:** hesap ücretsiz planda (10.000 kredi/ay, ticari kullanım yok, mp3 indirme). Aylık hedef (5 uzun + 15 kısa video) yaklaşık 26.000 kredi ister; müşteri işi ve satılan ürünler için ticari lisans gerekir. Starter (~5–6 $/ay, ~30.000 kredi, ticari) hedefi az payla karşılar; denemeler ve revizyonlarla birlikte rahat çalışmak için Creator (~22 $/ay, ≥100.000 kredi). Fiyatlar 2026-10'da üçüncü taraf kaynaklardan; satın almadan önce ElevenLabs sayfasında doğrulanır.

# Harita tasarım dili (dünya / sinematik küre)

Jeopolitik analiz, seyahat ve ülke sosyolojisi, askerî tarih ve çatışma senaryosu videolarında kullanılan harita
çekimlerinin ortak kuralları. Motor: `platform/sablonlar/dunya/sinema/` (three.js). Marka değerleri:
`sinema/marka.json`. Bu belge, motorun varsayılanlarının **neden** öyle olduğunu anlatır; yeni bir geri bildirim
gelince önce burası, sonra `marka.json` / motor güncellenir (sistemsel öğrenme döngüsü, en altta).

## 1. Referanslar ve onlardan aldıklarımız
| Referans türü | Aldığımız ilke |
|---|---|
| Belgesel küre açılışları (uzaydan iniş, Google Earth Studio tarzı) | Tam dünya → bölge uçuşu tek kesintisiz hareket; uçuş yolunda önce yükselip sonra iner (van Wijk "uçuş" eğrisi), düz zoom yapmaz. |
| Askerî tarih anlatım kanalları (cephe ve ok haritaları) | Oklar incelen gövde + keskin uç, beyaz ince kontur, yere gölge; cephe hattı dişli çizgi ve zamanla biçim değiştirir; NATO tipi birlik sembolleri (kademe işareti üstte). |
| Gazete veri haritaları (The Economist, NYT, Bloomberg) | Renk = rol (taraf), asla dekor değil; en fazla 3–4 rol rengi; nötr ülkeler gri; etiketler büyük harf, geniş harf aralığı, yoğun kontrast. |
| Uydu görüntüsü + gece ışıkları (NASA Blue/Black Marble) | Gerçek arazi ve şehir ışıkları "yer duygusu" verir; katmanlar bunun üstüne yarı saydam biner, araziyi öldürmez. |
| Sinema post prodüksiyonu | ACES ton eşleme, ölçülü bloom (yalnız ışıklar), hafif vinyet, ince gren; parlama ve geniş gradyan yok (bantlanma kuralı). |

## 2. Işık modları (`"isik"`)
- **gece** (öncü yön, Atilla 2026-11-05 "ilk stil güzel"): gece mavisi kabartma, amber şehir ışıkları her yerde
  yanık, mavi atmosfer halkası. Jeopolitik analizlerin varsayılanı.
- **alacakaranlık**: gerçek uydu rengi, terminatör ekranı çaprazlar, gece yarısında şehir ışıkları, turuncu
  terminatör ışıması. Dramatik açılışlar, askerî tarih.
- **gündüz**: uydu rengi, güneş kameranın sol üstünde; seyahat ve ülke sosyolojisi.
- **atlas**: Natural Earth renkli kabartma, düz ışık, bulutsuz; eğitici/kartografik anlatım.

Güneş varsayılan olarak kameraya göre sabittir (yörüngede ışık tutarlı kalır). Gerçek gün ışığı için
`"gunes": [boylam, enlem]` (alt güneş noktası) ve `"gunesHiz"` verilir.

## 3. Kamera dili (`"kamera"` anahtar kareleri)
Alanlar: `t`, `hedef` (yer adı, ülke adı ya da `[boylam, enlem]`), `irtifa` (dünya yarıçapı cinsinden ya da
`dunya 3.6`, `kita 1.6`, `bolge 0.75`, `ulke 0.45`, `sehir 0.12`), `egim` (0 = tepeden, 35–50 sinematik),
`yon` (0 = kuzey yukarı), `kayX`/`kayY_dikey` (konuyu yazıya yer açmak için kaydırır), `egri: "dogrusal"`,
`ucus: false` (uçuş eğrisini kapatır). Sahne geneli `"yorunge"` = saniyede derece dönüş.

Kurallar:
1. **Açılış tam dünya** (irtifa 3.6, eğim 0) en az 1.5 sn; izleyici nerede olduğunu anlar.
2. **İniş tek hareket**, 5–7 sn; varışta eğim 35–50°, ufuk görünür (perspektif "orada olma" hissi).
3. **Varıştan sonra asla durma**: 1–3°/sn yön kayması ya da çok yavaş irtifa düşüşü (nefes alan kamera).
4. Kesme yerine uçuş: iki bölge arası geçişte yeniden yükselip in (uçuş eğrisi bunu kendiliğinden yapar).
5. 9:16'da konu kadrajın üst-orta üçte birinde (`kayY_dikey` −0.04…−0.08); alt %23 Reels arayüzüne kalır.
6. Yatay kadrajda konu sağa kayar (`kayX` 0.05–0.1), başlık bloğu solda nefes alır.

## 4. Katmanlar (`"katmanlar"`, hepsi `t: [giriş, çıkış]` ile zamanlanır)
| tip | ne | ipucu |
|---|---|---|
| `ulke` | rol renginde yarı saydam dolgu + iç kenar ışıması + kontur + etiket | `rol`: ana, karsi, dost, notr, tartismali, ittifak |
| `bolge` | birden çok ülke tek grup; `desen: "tarama"` tartışmalı/işgal alanı | lejantta da `desen` verilir |
| `ok` | askerî ok, `cizim` sn içinde uzar | 3–4 noktalı yol yeter, motor yumuşatır |
| `cephe` | dişli cephe hattı; `durumlar` arasında biçim değiştirir | `taraf: -1` dişleri doğuya çevirir |
| `rota` | büyük daire üstünde kesikli yol | göç, ticaret, sefer |
| `menzil` | jeodezik menzil halkası (`km`) | füze/uçak menzili, etki alanı |
| `nabiz` | yayılan halkalar | olay yeri, varış noktası |
| `sehir` | nokta (başkent kare) + etiket | `yon: -1` etiketi sola alır |
| `deniz` | italik serif, açık mavi | deniz/okyanus/boğaz adları |
| `birlik` | NATO tipi sembol; `yol` + `hareket` ile ilerler | `sembol`: piyade, zirhli, mekanize, topcu, suvari; `kademe`: XX, XXX, XXXX |
| `kart` | veri kartı: işaret noktası, kırık bağlantı çizgisi, açılan kart, sayan rakam | `baslik`, `deger`, `ondalik`, `onek`, `birim`, `alt`, `yon: -1` sola |

Sınır görüşü: uluslararası tanınan sınırlar. Natural Earth'ün fiilî görünümü Kırım'ı Rusya'ya bağlar; motor
Kırım'ı Ukrayna'ya taşır. Tartışmalı bölgeler `bolge` + `tarama` ile ayrıca gösterilir.

## 4b. Anlatım grafiklerinin hareket dili (Atilla 2026-11-05: "grafikler, animasyonlar çok daha klas olsun")
- **Ülke girişi:** dolgu etiket noktasından dairesel açılır (1.5 sn, ease-out quint), kontur aynı anda çizilerek dolanır;
  ülke adı geniş harf aralığından yerine oturur (tracking-in). Ani belirme yok.
- **Ok:** uzayarak çizilir (eio), uçta kısa beyaz ışık yalnız çizilirken; gövdede uca doğru akan ince şevronlar yönü
  ve hareketi sürekli hissettirir; üç katmanlı yumuşak gölge, beyaz ince kontur.
- **Cephe hattı:** önce çizilerek gelir, sonra durumlar arasında biçim değiştirir; dişler ilerleme yönünde.
- **Birlik:** hafif geri yaylanmayla (back-out) belirir, yolda ilerlerken arkasında noktalı iz bırakır.
- **Veri kartı:** işaret noktası → bağlantı çizgisi çizilir → kart yandan açılır → rakam sayarak yerine gelir (TR/DE biçimi).
- **Nabız:** iki ince halka, yavaş (2.4 sn), merkezde sabit nokta. Abartılı yanıp sönme yok.
- Genel: hareketler 0.5–1.6 sn, yalnız ease-out/ease-in-out; aynı anda en fazla iki öğe giriş yapar; giriş zamanları
  anlatım cümlesine bağlanır (`t`).

## 5. Renk sistemi (roller)
- Rol renkleri `marka.json → roller`. **ana** amber (anlatının öznesi; kanal imzası), **karsi** kırmızı,
  **dost** mavi, **ittifak** yeşil-turkuaz, **tartismali** kum sarısı (çoğunlukla tarama), **notr** gri.
- Bir karede en fazla 3 rol rengi + nötr. Dolgu alfası 0.28–0.32: arazi ve şehir ışıkları görünmeye devam eder.
- Sınırlar beyaz %38, 0.9 px; vurgu ülkesinde 1.6 px kontur + 6 px yumuşak dış hale.

## 6. Yazı ve marka sistemi
| Rol | Yazı tipi | Biçim |
|---|---|---|
| Üst etiket (kicker) | Inter Tight 700 | BÜYÜK HARF, %22 aralık, vurgu renginde, solunda büyüyen ince çizgi |
| Başlık | Barlow Condensed 700 | büyük, maskeyle aşağıdan yükselir |
| Alt başlık | Inter Tight 500 | cümle düzeni |
| Ülke adı (haritada) | Barlow Condensed 600 | BÜYÜK HARF, %24 aralık, boyu ülkenin ekrandaki genişliğiyle ölçeklenir |
| Şehir | Inter Tight 600 | cümle düzeni, nokta/kare işaret |
| Deniz | Source Serif 4 italik | %16 aralık, açık mavi |
| Tarih damgası | Barlow Condensed 600 | sağ üst, altında vurgu çizgisi; olay sırasında değişir |
| Konum çipi | Inter Tight 700 + IBM Plex Mono | sol alt; yer adı + canlı koordinat |
| Lejant | Inter Tight 500 | sağ alt, rol kutuları sırayla belirir |
| Künye | Inter Tight 400, küçük | kaynaklar her zaman yazılır |

Türkçe büyük harf `toLocaleUpperCase("tr")` (i → İ). Bütün metinler güvenli alanda: 16:9 kenar %6, üst %8, alt %8;
9:16 kenar %7, üst %11, alt %23. Etiketler çakışmaz (öncelik sırasıyla yerleşir, yer yoksa düşer).

## 7. Kalite kuralları
- İç çizim 2× (3840×2160), kutu filtresiyle 1920×1080'e iner; kenarlar temiz.
- Deniz parlaması yalnız gündüz/alacakaranlıkta, çok sıkı ve düşük; gece ve atlas modunda kapalı (Atilla: parlama yok).
- Bloom eşiği yüksek (0.88): yalnız şehir ışıkları ve atmosfer parlar, metin parlamaz.
- Bulut yalnız yüksek irtifada; bölgeye inerken söner ki katmanlar okunsun.
- Kaynak künyesi: "Harita: Natural Earth · Arazi: Mapzen Terrain Tiles (SRTM, GMTED, ETOPO1) · NASA Blue/Black Marble".

## 8. Sistemsel öğrenme döngüsü
1. Atilla'nın her harita geri bildirimi tarihiyle bu belgenin ilgili bölümüne kural olarak yazılır.
2. Kural sayısal ise `marka.json`'a (renk, boy, aralık, güvenli alan) ya da motor varsayılanına işlenir; belge
   yalnız gerekçeyi tutar.
3. Beğenilen kareler `ornekler/dunya-sinema/` altında sahne dosyası olarak kalır; yeni iş bunlardan kopyalanır.
4. Kayıtlı kararlar:
   - 2026-11-05: kure/atlas/kağıt beğenildi; yükseltilmiş üçlüden ilki (gece küresi) öncü yön.
   - 2026-11-05: amaç jeopolitik + seyahat/sosyoloji + askerî tarih; 16:9 ve 9:16; kürenin etrafında dönen kamera,
     ara ara tam dünya; ülke adları marka yazı sistemiyle.
   - Kalıcı: parlama/bantlanma yok, yazı güvenli alanda ve tam görünür, müşteri logosu öne çıkar.

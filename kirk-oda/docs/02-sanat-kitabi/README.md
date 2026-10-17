# Kırk Oda — Sanat Kitabı

Durum: Taslak v0.1 · Kaynak: `docs/00-dunya-kitabi.md` ("Görsel ve ses yönü", "Sinematikler") · Hedef araçlar: Unity 6 (URP), Blender, Google Flow, DaVinci Resolve, Inkscape

Bu belge üretimdeki her görsel kararın ölçütüdür. Bir kare bu belgeyle çelişiyorsa kare yanlıştır, belge değil; belge değişecekse önce burada değişir. Sayısal değerler başlangıç aralığıdır: dikey dilimde ölçülür, sonra kilitlenir.

---

## 1. Görsel dil

**Tek cümle:** Karanlıkta tek bir sıcak ışık kaynağı ve onun ulaşamadığı her yerde soğuk bir mavi.

**Beş bağlayıcı ilke**

1. **Tek sıcak ışık.** Sahnede yalnız bir sıcak kaynak vardır: saatçinin feneri (kasabada güneş ya da kahvenin lambası onun yerini alır, ikisi aynı anda sıcak olmaz). Her kadraj bu kaynağa göre kurulur. İkinci sıcak kaynak yalnız kor ve çark gibi "zamana ait" nesnelerdir ve fenerden hiçbir zaman parlak değildir.
2. **Soğuk mavi her yerdedir.** Işığın ulaşmadığı yer siyah değil kök mavisidir. Tam siyah yalnız gölgenin kendisidir (köpek gölgesi, saatçinin gölgesi). Böylece karanlık korkutmaz, derinleşir.
3. **Sessizlik.** Kadrajda ne kadar az şey varsa o kadar iyi. Her oda tek bir odak nesnesi, tek bir bekçi, tek bir ışık. Dekor birikimi yok; boş duvar, boş zemin kabul edilir.
4. **Az yüz hattı.** Karakterlerde burun, dudak çizgisi ve kaş yoktur; yalnız kafatası biçimi, saç/başlık silueti ve ışıklı gözler. Duygu beden duruşundan ve göz ışığının sıcaklığından okunur.
5. **Arayüz yok.** Ekranda tek bir piksel UI yoktur. Bilgi taşıyan her şey dünyanın içinde bir nesnedir: taş elde, kor avuçta, kule meydanda, gölge yerde.

---

## 2. Palet

### 2.1 Ana renkler

| Ad | HEX | sRGB | Rol | Kullanılmaz |
| --- | --- | --- | --- | --- |
| Kor turuncusu | `#E8701A` | 232, 112, 26 | Fener ışığı rengi (ışık kaynağı: `#FFB36B` daha açık ton), çark dişlilerinin emissive kenarları, kor çekirdeği, kor | Duvar/zemin albedo'da asla; yalnız ışık ve emissive |
| Kor turuncusu (açık) | `#FFB36B` | 255, 179, 107 | Fener Light bileşeninin rengi; kor dış halesi | — |
| Kök mavisi | `#1E3A5F` | 30, 58, 95 | Ambient/sky rengi, mağara damarları, ay ışığı, gölgelerin "dolgu" tonu | Emissive olarak kullanılmaz (Su halkası hariç, bkz. 2.2) |
| Kök mavisi (derin) | `#0E1E33` | 14, 30, 51 | Kameradan en uzak düzlemler, tüneller, su dipleri | — |
| İs karası | `#0A0908` | 10, 9, 8 | Gerçek gölge (köpek, saatçi), kapak altı, çan içi | Tam `#000000` kullanılmaz; her zaman bu hafif sıcak kara |

Kural: Albedo dokularının ortalama parlaklığı %18–35 arasında kalır (taş, ahşap, toprak). Sahnenin sıcaklığını doku değil ışık verir; doku nötr ve koyu kalır ki fener ona rengini basabilsin.

### 2.2 Halka vurgu renkleri

Her halkaya tek vurgu rengi. Vurgu rengi halkanın "zamana ait" yüzeylerinde yaşar: kök damarları, bekçinin göz ışığı, ses çizgisinin uç rengi, korun halesinin ikinci tonu. Vurgu rengi hiçbir zaman zemine, duvara ya da fenere girmez.

| Halka | Renk | HEX | Nerede | Nerede değil |
| --- | --- | --- | --- | --- |
| 1 Toprak | Kahve | `#8A5A2B` | Kök damarları (mat, emissive yok), geyik/turna/yılan/arı bekçilerinin göz ışığı, filizlenen tohumun ucu | Fener, zemin |
| 2 Su | Yeşil (su yeşili) | `#2E8B7A` | Su yüzeyinin emissive altı, çocuk bekçilerin göz ışığı, gelgit çizgisi; palette emissive maviye en yakın izin | Köklerde (köklerde kahveden yeşile geçiş yalnız suya değen uçlarda) |
| 3 Nefes | Süt beyazı | `#EFE6D8` | Durmuş dünyada askıda kalan toz, nefes buharı, yaşlı bekçilerin göz ışığı (sıcak değil, süt) | Fener (fener hâlâ turuncu) |
| 4 Gölge | Mor | `#5B3A7A` | Gölgedeki geri-akış bölgelerinin kenar ışığı, öbür saatçinin göz ışığı, ikinci fenerin halesi | Işıktaki (ileri akan) bölgelerde hiç |
| 5 Ayna | Gümüş | `#B8BFC6` | Yansıma yüzeyleri, kayıtlar (mezar taşı harfleri, fotoğraf kenarları), yansıma-bekçilerin göz ışığı (soğuk) | Kor (kor turuncu kalır) |
| 6 Sessizlik | Hiç | — | Vurgu rengi yok. Palet üç ana renge iner; kökler kurumuş, rengi is karasına yakın `#2A2420` | Hiçbir ekleme |
| 7 Ân | Beyaz | `#FFFFFF` | Yalnız taşın iç ışığı ve son karede yüz. Oyunda saf beyazın tek kullanıldığı yer | Başka hiçbir yerde saf beyaz yok |

Not: Sessizlik'te "hiç" bir tasarım kararıdır: oyuncu altı halkada bir renk beklemeyi öğrenir, yedincide rengin gelmemesini fark eder.

### 2.3 Kasaba çağları — renk derecelendirme

Dört çağ aynı sahnenin dört Volume profilidir. Işık ve malzeme değişmez; derecelendirme değişir (ve bkz. 5.2 yıpranma katmanları). Aşağıdaki değerler URP Volume → Color Adjustments / White Balance / Lift Gamma Gain için başlangıç aralığıdır.

| Çağ | Duygu | White Balance Temp | Tint | Saturation | Contrast | Lift (gölge tonu) | Gain (ışık tonu) | Vignette |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Çocukluk (yalnız Su dioraması) | Altın | +20 … +30 | 0 | +10 … +15 | −5 | hafif sıcak `#2A1E10` | `#FFE0B0` | 0.25 |
| Bugün | Nötr | 0 | 0 | 0 | 0 | nötr | nötr | 0.30 |
| Bir yıla yakın sonra | Nötr, hafif soğuk | −5 | 0 | −5 | +5 | nötr | nötr | 0.30 |
| Kırk yıl sonra | Solgun | −10 … −15 | +3 (hafif yeşil) | −25 … −35 | −10 | `#141820` | `#D8D4CC` | 0.35 |
| Terk edilmiş | Gri-mavi | −25 … −35 | 0 | −45 … −55 | −15 | `#101624` | `#B8C0CC` | 0.40 |

Kural: Fener bu derecelendirmeden etkilenir ama ayrı tutulur: terk edilmiş çağda bile fenerin çekirdeği turuncu okunmalıdır. Bunun için fener emissive'i Volume'den önce değil sonra uygulanan ayrı bir "warm pass" ile korunur (Renderer Feature ile ya da fener çekirdeğini post-process katmanı dışında bir Render Layer'a alarak). Dikey dilimde test edilir; olmazsa fener emissive yoğunluğu çağ başına el ile artırılır (bugün 1.0 → terk 1.6).

---

## 3. Işık reçetesi

### 3.1 İlke

Tek gerçek zamanlı ışık: fener. Geri kalan her şey pişirilmiş (Lightmap + Light Probe) ya da emissive. Böylece sahne düşük donanımda pahalı görünür ve ışık dili tek elden okunur.

### 3.2 Fener (dinamik ışık)

| Parametre | Başlangıç değeri | Aralık | Not |
| --- | --- | --- | --- |
| Tip | Point | — | Spot değil; fener her yöne eşit vermez ama bunu cookie değil, fener gövdesi modelinin kendi gölgesi yapar |
| Renk | `#FFB36B` | 2600–3200 K karşılığı | Sıcaklık modunda çalışılırsa 2900 K |
| Yoğunluk | 3.5 (URP, Lux tabanlı değil) | 2.5–5.0 | Halka içe daraldıkça +0.3/halka (Ân'da 5.0) |
| Menzil | 7 m | 5–9 m | Dış halkalarda 7–8, iç halkalarda 5–6: alan daralırken ışık da daralır |
| Gölge | Soft, Realtime | — | Shadow resolution 1024 (fener tek ışık olduğu için bütçe var) |
| Gölge gücü | 0.85 | 0.8–0.95 | Köpek gölgesinin net okunması için yüksek |
| Titreme (flicker) | Yoğunluk ±4 %, 0.8–1.4 Hz Perlin | ±2–6 % | Sessizlik'in ilk odasında hamle öncesi ±15 % ve 6 Hz (kırk yıl uyarısı; dünya kitabı) |
| Konum | Saatçinin sol elinde, göğüs hizası | — | Kamera omuz üstü sağdan bakar; fener ekranın sol yarısında kalır |

### 3.3 Pişirilmiş ışık

- Lightmapper: Progressive GPU. Odalar küçüktür; 1024–2048 lightmap/oda yeter.
- Pişen ışık kaynakları: kök damarlarının emissive'i (çok düşük, 0.1–0.3 yoğunluk, yalnız ambient dolgu için), gökyüzü (kasaba), kahve lambası (kasaba, bugün ve bir yıl çağlarında).
- Ambient: Gradient; Sky `#1E3A5F`, Equator `#152A45`, Ground `#0E1E33`. Yoğunluk 0.35 (mağara), 0.6 (kasaba gece), 1.0 (kasaba gündüz).
- Light Probe grubu her odada zorunludur; saatçi ve köpek probe'lardan aydınlanır.
- Reflection Probe: oda başına bir tane, 128 çözünürlük, baked. Ayna halkasında 256 ve gerçek zamanlı değil, planar reflection yerine ters çevrilmiş ikinci sahne kopyası kullanılır (bkz. ADR, mimari belgeleri).

### 3.4 Emissive kuralları

- Emissive yalnız "zamana ait" nesnelerde: kor, çark kenarları, kök damarları, bekçi gözleri, ses çizgisi, taşın dalgaları, su yüzeyi (Su halkası), kitabe harfleri (çok hafif).
- Emissive yoğunlukları (HDR): kor çekirdeği 6–8; kor halesi 2; çark kenarı 1.5; kök damarı 0.1–0.3; bekçi gözü 3; ses çizgisi 4 (perde yükselince 6'ya kadar).
- Bloom'u tetiklemesi istenen tek şey kor ve ses çizgisidir; başka hiçbir emissive bloom eşiğini geçmez. Eşik buna göre ayarlanır (aşağıda).

### 3.5 Post-process (URP Volume) — başlangıç değerleri

| Efekt | Parametre | Başlangıç | Aralık | Not |
| --- | --- | --- | --- | --- |
| Bloom | Threshold | 1.1 | 0.9–1.3 | Fener çekirdeği ve kor geçer, duvar geçmez |
| Bloom | Intensity | 0.6 | 0.4–0.9 | Mağarada 0.7, kasabada 0.4 |
| Bloom | Scatter | 0.65 | 0.5–0.8 | Yumuşak, geniş; parçacık hissi değil "ışıma" |
| Bloom | Tint | `#FFB36B` | — | Soğuk bloom yalnız Su (`#2E8B7A` %30 karışım) |
| Tonemapping | ACES | — | Sabit |
| Color Adjustments | Post Exposure | 0.0 | −0.3…+0.3 | Çağ Volume'leri bunu değil White Balance'ı değiştirir |
| Vignette | Intensity | 0.30 | 0.25–0.40 | Çağ başına tablo 2.3 |
| Vignette | Smoothness | 0.6 | — | — |
| Film Grain | Type / Intensity | Medium / 0.15 | 0.1–0.25 | Terk edilmiş çağda 0.25 |
| Chromatic Aberration | — | 0 | — | Yalnız Ayna halkasında 0.15 (yansımanın "yanlışlığı") |
| Depth of Field | Mode | Bokeh, kapalı | — | Yalnız Ân odasında açık: f/1.8, focus saatçinin yüzü |
| Motion Blur | — | kapalı | — | Sabit kapalı |

### 3.6 "The Sky Is Lit" reçetesi aktarım tablosu

Önceki projenin ışıma ve bloom reçetesi korunacak (dünya kitabı). Elimizde parametreler yok; o projeden okunup buraya yazılır. Boş kalan satır varsa yukarıdaki başlangıç değerleri geçerlidir.

| Parametre | The Sky Is Lit değeri | Kırk Oda'ya aktarılan değer | Fark gerekçesi |
| --- | --- | --- | --- |
| Bloom Threshold | | | |
| Bloom Intensity | | | |
| Bloom Scatter | | | |
| Bloom Tint | | | |
| Tonemapping | | | |
| Emissive HDR tavanı | | | |
| Ambient yoğunluk | | | |
| Ana ışık rengi/yoğunluğu | | | |
| Film Grain | | | |
| Vignette | | | |

---

## 4. Kamera

### 4.1 Temel

- Üçüncü şahıs, omuz üstü, saatçinin **sağ** omzu üzerinden. Fener sol elde, bu yüzden fener ekranın sol üçte birinde kalır ve kadrajın "kaynağı" olur.
- Sanal lens 35 mm (36×24 sensör) → dikey FOV ≈ 37.8°. Unity'de Physical Camera açık, Focal Length 35, Sensor Size 36×24. Bu bütün oyunda sabittir; "yaklaşma" FOV ile değil mesafeyle yapılır (bkz. 4.3).
- Kasabada serbest takip (Cinemachine ThirdPersonFollow). Odalarda sabit açılı diorama kadraj.

### 4.2 Diorama kadraj kuralları (odalar)

1. Kamera sabittir ve oda bir vitrin gibi görülür: hafif yukarıdan (pitch 8–14°), odanın uzun eksenine 20–35° açıyla. Tam cepheden ya da tam profilden bakılmaz.
2. Üçte bir kuralı: fener (ve dolayısıyla saatçi) sol dikey üçte bir çizgisinde; odanın odak nesnesi (bekçi ya da bulmaca) sağ dikey üçte birde; ufuk/zemin çizgisi alt üçte bir çizgisinde.
3. Köpek fenerin **tam yanında** durur (dünya kitabı: "her odada fenerin yanında"). Gölgesi, fenerden kaynaklanarak sol alt üçte birden duvara doğru uzar; yani gölgenin düştüğü duvar daima kamera açısından görünür olacak şekilde oda planlanır. Bu, oda tasarımının birinci kısıtıdır.
4. Odak nesnesi hiçbir zaman tam merkezde değildir. Merkez boş bırakılır; oyuncunun gözü fenerden odak nesnesine yürür.
5. Negatif alan: kadrajın en az %40'ı kök mavisi karanlıktır.
6. Kesme yok. Oda içinde kamera açısı değişmez; oyuncu diorama içinde dolaşır, kamera yalnız çok hafif paralaks yapar (±0.3 m yanal, saatçiyi takip ederek).

### 4.3 Halka başına yaklaşma kademeleri

Lens sabit (35 mm), kamera-saatçi mesafesi ve yükseklik değişir. Her halkada bir kademe: oyuncu fark etmez ama hisseder.

| Halka | Mesafe (kamera→saatçi) | Kamera yüksekliği (zeminden) | Pitch | Saatçinin kadrajdaki yüksekliği | Not |
| --- | --- | --- | --- | --- | --- |
| Kasaba | 3.8 m | 1.9 m | 10° | ≈ %35 | Serbest takip |
| 1 Toprak | 3.6 m | 1.85 m | 12° | %38 | Diorama, en geniş |
| 2 Su | 3.3 m | 1.8 m | 12° | %41 | — |
| 3 Nefes | 3.0 m | 1.75 m | 11° | %45 | Durmuş dünyada paralaks sıfır |
| 4 Gölge | 2.7 m | 1.7 m | 10° | %50 | İkinci saatçi kadraja girer; kadraj iki figürü taşır |
| 5 Ayna | 2.4 m | 1.65 m | 8° | %56 | Pitch düşer, yansıma düzlemleri okunur |
| 6 Sessizlik | 2.1 m | 1.6 m | 6° | %63 | Omuz hizası; köpeğin beden dili okunur |
| 7 Ân | 0.9 m → 0.6 m | 1.55 m (göz hizası) | 0° | Yüz | Kamera yavaşça (20 sn) saatçinin önüne döner, yüze bakar. DoF açılır. Oyunun tek yüz kadrajı |

### 4.4 Kasabada kamera

- Cinemachine ThirdPersonFollow; omuz ofseti (0.45, 0, 0), damping 0.6.
- Kule meydandan her bakışta kadrajın üst üçte birine girecek şekilde kameranın "kuleye bakma" eğilimi (Cinemachine Target Group ile kule %20 ağırlık). Oyuncu kuleyi aramadan görür.
- Çağ geçiş videoları (Bir yıl, Kırk yıl) kasaba haritasında sabit bir "efsane kamerası" noktasından çekilir: meydanın güneydoğu köşesi, 4.2 m yükseklik, kule ve kapak aynı kadrajda. Bu kamera sahnede boş bir GameObject olarak kilitli durur; iki videonun birebir aynı kadrajı garanti edilir.

---

## 5. Mekân tasarımı

### 5.1 Kule

- Taş gövde, kare plan ≈ 5×5 m, yükseklik ≈ 21 m (7 kat × 3 m). Dışta tek kapı, dört yüzde dörder dar pencere; saat kadranı yalnız meydana bakan yüzde.
- İçte yedi katlı ahşap çark düzeneği: her kat tek bir ana çark + iki ara dişli, katlar arası ahşap merdiven. Katlar kor takılınca döner ve dişli kenarları emissive (1.5) yanar; takılmamış kat durur ve karanlıktır. Sır söylenmiş kat "kararır": emissive kapalı, ahşap bir ton daha koyu (ikinci malzeme varyantı). Oyuncu meydandan pencerelerden bakarak hangi katın yandığını görür (dünya kitabı: sonlar arayüzsüz okunur).
- Tepede tek çan, bronz, 0.9 m çap. Çan içi is karası.
- Sarkaç taşı: kulenin zemin katında, 0.25 m çapında, düzensiz yuvarlak, koyu gri-yeşil (serpantine benzer) taş; yüzeyinde ince, konsantrik dalga çizgileri (bkz. 7.2). Taş yerinden alınınca zincir boş sallanır.
- Kitabe: kapının üstünde, 1.2×0.4 m taş plaka, oyma harfler. Harfler çok hafif emissive (0.15) ki geceleyin okunur. Ayna halkasında harfler silinirken oyma dolmaz; harfin yerinde pürüzsüz taş kalır (sanki hiç yazılmamış).
- Kapak: zemin katta, sarkacın tam altında, 1.1 m çapında yuvarlak taş kapak; kenarı aşınmış, ortasında demir halka. Açıkken altında kök mavisi derin karanlık ve ilk basamak görünür.

### 5.2 Kasaba

- Tek harita, ≈ 180×140 m. Kırk hane, cami (küçük, tek minareli ya da minaresiz; tanınabilir dini sembol yüzeye çıkmaz — kubbe ve hilal yok, taş duvarlı sade bir yapı, kapı üstünde kitabe yeri boş), kahve, mezarlık (kasabanın batı kenarı, kuleye en uzak), değirmen (dere kenarı, güney), meydan (kule ortada), dere.
- Toros mimarisi: taş alt kat, ahşap üst kat, kiremit/düz toprak dam karışık, ahşap cumbalar. Düz, modern hiçbir nesne yok (elektrik direği, araba, plastik). Çağ "bugün" bile tarihsiz durur; dünya kitabının "hiçbir şeyi kesinleştirmeme" ilkesine görsel karşılık.
- **Çağ varyantları, aynı modelin yıpranma katmanları olarak üretilir:**
  - Katman 0 (model): tek set. Her bina prefab'ı dört "durum" alt nesnesi taşır: `Bugun`, `BirYil`, `KirkYil`, `Terk`. Yalnız biri aktiftir.
  - Katman 1 (malzeme): Her ana malzemenin dört varyantı; yıpranma maskesiyle (vertex color R kanalı = yıpranma ağırlığı) tek shader'da kontrol edilir. Bugün 0.0, Bir yıl 0.15, Kırk yıl 0.6, Terk 1.0. Maske kenarları, çatı dipleri, pencere altlarını vurgular.
  - Katman 2 (ek geometri): Kırk yıl: çökmüş 3 çatı, kapanmış 2 pencere, büyümüş mezarlık (mezar taşı sayısı 40 → 70). Terk: çökmüş 11 çatı, yıkılmış 1 duvar, otlar (kart yığını), değirmen çarkı düşmüş.
  - Katman 3 (derecelendirme): Volume profili (tablo 2.3).
  - Katman 4 (ses ve hareket): bu belgenin dışında; ses mimarisi belgesine bakılır.
- Mezarlık, Ayna halkasının değiştirdiği kayıtların mekânıdır: her mezar taşı bir `KayitNesnesi`dir, metin bir dokuya değil, oyma mesh'e yazılır (text mesh değil; harf başına küçük oyma prefab, böylece "silinen harf" pürüzsüz taşa dönüşebilir).
- Kahve: duvarda 7 çerçeveli fotoğraf (kasabanın yedi kişisi). Fotoğraflar Ayna'da değiştirilebilen kayıtlardır; dört çağda fotoğraflar değişir (bugün: yedi kişi genç/orta yaşlı; kırk yıl: aynı çerçevelerde yaşlanmış ya da siyah bantlı; terk: çerçeveler boş ya da yerde).

### 5.3 Mağara ve kökler

- Hayat Ağacı hiç görünmez. Görünen yalnız köklerdir; kökler tavandan ve duvarlardan geçer, hiçbir yerde "gövdeye" bağlanmaz, hiçbir yerde yukarıya doğru birleşmez. Oyuncu kökleri takip edip bir ağaca varamaz.
- Halka başına kök kalınlığı ve rengi (dıştan içe):

| Halka | Ortalama kök çapı | Yoğunluk (duvar alanı yüzdesi) | Kök rengi (albedo) | Damar emissive |
| --- | --- | --- | --- | --- |
| 1 Toprak | 0.35 m | %25 | Kahve-toprak `#4A3524` | Kahve `#8A5A2B` 0.2 |
| 2 Su | 0.30 m | %22 | Islak, koyu `#3A2E26` | Uçlarda yeşil `#2E8B7A` 0.3 |
| 3 Nefes | 0.25 m | %18 | Kül tonu `#4C463E` | Süt beyazı 0.15 |
| 4 Gölge | 0.20 m | %15 | `#2E2630` | Mor `#5B3A7A` 0.25 yalnız gölge tarafında |
| 5 Ayna | 0.15 m | %12 | `#3A3C40` | Gümüş 0.2 |
| 6 Sessizlik | 0.10 m, kurumuş, çatlak | %8 | `#2A2420` kuru | 0 (ilk odada hamle anında son kalan damarlar söner) |
| 7 Ân | Yok | 0 | — | — Ân odasında kök yoktur; yalnız düz taş ve taşın beyaz iç ışığı |

- Mağara taşı: kireçtaşı, soğuk gri `#5A5E62` albedo (fener basınca sıcak okunur), ıslak yüzeylerde smoothness 0.7, kuru 0.3.
- Odalar arası geçitler alçak (1.9 m) ve dar; oyuncu "iniyor" hisseder. Halkalar arası geçiş kısa bir merdiven (7 basamak) + kapı eşiği.

### 5.4 Kapak ve iniş

- Kapak kalkınca ilk 4 basamak fener ışığında, gerisi kök mavisi. Bu kare oyunun ilk görsel vaadidir; açılış kadrajı olarak ayrıca tasarlanır (bkz. `halka-konseptleri.md`).

---

## 6. Karakter

### 6.1 Ortak kurallar

- Oranlar: 7 baş yüksekliği, hafif uzun gövde, büyük eller (eller konuşur: fener, taş, kor).
- Yüz: kafatası biçimi + saç/başlık silueti + iki ışıklı göz. Burun, ağız, kaş yok. Göz ışığı küçük, 3 mm çapında emissive disk; rengi ve yoğunluğu duyguyu taşır (sıcak = yakınlık, soğuk = uzaklık, sönük = yorgunluk/ölüm yakınlığı).
- Malzeme: stilize, mat; dokuda detay yerine renk alanı. Kumaş kırışığı normal map ile, boyalı değil.
- Poligon: karakter başına 8–12k üçgen; bekçi hayvanları 4–6k.

### 6.2 Saatçi

- Kırk yaşında, orta boy, yorgun duruş (omuzlar hafif önde). Koyu yün ceket `#2B2622`, keçe başlık, deri önlük (çark işi). Sol elde fener, sağ el serbest (taş, kor).
- Göz ışığı: sıcak amber `#FFB36B`, 2.5 yoğunluk. Sessizlik'te 1.5'e düşer, Ân'da beyaza döner.
- Dinleme pozu: baş hafif yana eğik, kıpırtısız; fener yere yakın iner. Bu poz oyunun ikonudur (Steam kapsülünde kullanılır).

### 6.3 Yedi kasabalı × dört çağ

Aynı model, dört varyant. Sabit kalanlar: kafatası biçimi, boy oranı (çocuk hariç), kıyafet rengi ailesi, göz rengi. Değişenler: duruş (yaşla öne eğilir), saç/başlık rengi ve hacmi, kıyafet yıpranma maskesi (bina shader'ıyla aynı mantık), göz ışığı yoğunluğu (çağ ilerledikçe −0.3/çağ).

| Kişi | Silüet anahtarı | Bugün | Bir yıl | Kırk yıl | Terk (kimse yok; kalan) |
| --- | --- | --- | --- | --- | --- |
| Değirmenci | Geniş omuz, un tozlu önlük, uykusuz yüz | 50'li | Aynı; sır söylendiyse dinlenmiş yüz | Yok (mezar, dere yatağına bakar) | Çark yerinde durur |
| Değirmencinin kızı | İnce, uzun örgü, yeşil yemeni | 17–18, nişanlı | Ebe çırağı (fener, defter) ya da gelin (muhtarın evinde) | Ebe: kır saç, yemeni solmuş, dizinde eski ebenin defteri, kapağın başında | Ebenin evinde defter masada |
| Kahveci | Kısa, yuvarlak, kolları sıvalı; rafta ters fincan | 40'lı | Aynı, gözler çökük | Yok (kahve kapalı, fincan vitrinde; ya da kahve açık, kimse yok, fincan rafta) | Kepenk yarı açık, fotoğraflar solmuş |
| İmam | Uzun, dik, sade koyu giysi (sembol yok), elinde değnek | 30'lu, genç | Aynı | Yaşlanmış, yerinde; değneği hâlâ diker. Yaşlı varyant isteyen tek erkek karakter | Değnek dikili, gölgesi yürür |
| Ebe | Küçük, bükülmüş, beyaz başörtü, defter, titreyen eller | 70'li | Aynı; kız yanında ya da yalnız | Yok (mezar; taşta tarih yok) | — |
| Çoban | Uzun, kepenek silueti, kaval yok | 30'lu, kuzu sayar | Aynı; sayar ya da saymaz | Yok; sır söylendiyse oğlu çoban (babasının genç modeli) | Ağıl boş, çan yerde |
| Muhtar | Kalın, kasket, dik bakış, defter koltuk altında, palto | 50'li | Aynı; taş kenarda ya da kapağın yarısında | Yok; oğlu muhtar (babasının genç modeli). Defter meydanda asılı ya da kayıp | Muhtarlık masasında defter |

Kırk yıl sütunu senaryo kilidiyle (`01-senaryo-kilidi/kasaba-halki.md`) kesinleşti: yaşlı varyant yalnız değirmencinin kızı (ebe) ve imam için üretilir; çobanın oğlu ve muhtarın oğlu babalarının genç modelidir (yeniden kullanım). Diğer üç kişi için kırk yıl varyantı yoktur, yalnız mezar taşı ve mekân durumu değişir. Terk çağında kasabada kimse yoktur; silüetler yalnız kahvedeki fotoğraflarda kalır.

### 6.4 Bekçiler

| Halka | Tür | Görsel kural |
| --- | --- | --- |
| Toprak | Hayvanlar (geyik, turna, yılan, arı…) | Gerçek oranlar, stilize yüzey, göz ışığı kahve. Konuşmazlar; başlarını istenen eşyanın bulunduğu yöne çevirirler |
| Su | Çocuklar | 5–9 yaş, saatçinin çocukluk kasabasının kıyafetleri (altın çağ paletinde); yüzleri olmadığı için "tanıdık ama adsız" kendiliğinden gelir; göz ışığı yeşil |
| Nefes | Yaşlılar | Kasabanın eski ihtiyarları; kıyafetleri bugünün kasabalılarından bir kuşak eski. Göz ışığı süt beyazı, 1.0 (sönük). Durmuş dünyada askıda duran toz onların etrafında yoğunlaşır |
| Gölge | Saatçinin kendisi | Aynı model, başka yaşlar: 12, 25, 40 (bugün), 60, 75. Göz ışığı mor. Yalnız gölge (geri akan) bölgede görünür |
| Ayna | Kasabalıların yansımaları | Aynı yedi model, aynalı (sol-sağ ters), gümüş göz ışığı, kıyafet renkleri tersine (koyu→açık). Yüzleri yoktur zaten; "tersine" duruşla okunur |
| Sessizlik | Yok | Oda boş. Bekçinin "yeri" (fenerin karşısında boş bir taş çıkıntı) vardır, bekçi yoktur |
| Ân | Yok | Yalnız saatçi ve taş |

### 6.5 Köpek ve gölgesi

Köpek: Anadolu çoban köpeği silueti (iri, kısa tüylü görünüm, kuyruk hafif kıvrık, kulak düşük), krem-boz albedo `#B8A98C`, göz ışığı amber. **Köpek hiç değişmez.** Değişen yalnız gölgesidir. Gölge gerçek ışık gölgesi değildir: fenerin köpeğe göre konumundan hesaplanan bir **projeksiyon mesh'idir** (gölge-silüet mesh), böylece halka başına morph edilebilir. Gerçek gölge köpek için kapatılır (Cast Shadows: Off), gölge mesh'i is karasıyla çizilir.

Kurda yaklaşma eğrisi (yalnız gölge; kasabaya çıkınca sıfırlanır):

| Halka | Kulak | Çene / burun | Kuyruk | Duruş | Blend ağırlığı (köpek→kurt morph) |
| --- | --- | --- | --- | --- | --- |
| Kasaba / 1 Toprak | Düşük, yuvarlak | Kısa | Kıvrık | Oturur | 0.00 |
| 2 Su | Uçları hafif kalkık | Kısa | Kıvrık | Oturur | 0.12 |
| 3 Nefes | Dik, uçlar sivri | Hafif uzamış | Kıvrım azalmış | Oturur, baş kalkık | 0.28 |
| 4 Gölge | Dik, geniş | Uzamış, belirgin burun | Düz | Ayakta | 0.45 |
| 5 Ayna | Dik, dar | Uzun | Düz, aşağı | Ayakta, baş alçak | 0.62 |
| 6 Sessizlik | Dik, arkaya yatık | Uzun, ağız hafif açık (yalnız silüette) | Düz, aşağı | Öne eğik, ilerlemeyi reddeder | 0.80 |
| 7 Ân | — | — | — | Köpek yok (dünya kitabı: "köpek kapıda bekler") | — |

Kural: Köpek ile gölgesi hiçbir karede aynı anda net okunmaz; ya köpek odaktadır ya gölgesi. Oyuncu farkı yalnız halkalar arasında hatırlayarak kurar.

---

### 6.6 Varlık ekonomisi (karar K-15)

Kırk bekçi tek kişi için en büyük modelleme yüküdür. Kural: bekçiler silüet + ışıklı göz, yüz hattı yok; her bekçi en çok bir iş günü.

| Rig | Bekçiler | Ayrım nasıl yapılır |
| --- | --- | --- |
| Dörtbacaklı | Geyik, keçi, kaplumbağa, kirpi (Toprak) | Ölçek, boynuz/kabuk/diken eki, doku |
| Kuş | Turna, baykuş (Toprak) | Kanat açıklığı, duruş |
| Sürü | Arı, karınca (Toprak) | Tek model + GPU parçacık; davranış sürüde |
| Yılan | Yılan (Toprak) | Kemik zinciri, tek model |
| Çocuk | Su'nun 8 çocuğu | Saç, kıyafet, el nesnesi (sapan, testi, örgü) |
| İhtiyar | Nefes'in 7 ihtiyarı | Kasabalı modellerinin bir kuşak eski kıyafeti; göz ışığı sönük |
| Saatçi | Gölge'nin 6 yaşı | Tek model; ölçek, duruş, saç; 7 ve 17 yaş için ayrı oran blend shape'i |

Ayna'nın yansımaları yeni model değildir: kasabalı modellerinin ters shader'lı (gümüş, negatif ışık) kopyasıdır. Kırk yıl çağında yalnız ebe (değirmencinin kızı) ve imam yaşlı varyant ister; çobanın ve muhtarın oğulları babalarının genç modelidir (§6.3). Toplam benzersiz karakter modeli: saatçi, köpek, 7 kasabalı, 2 yaşlı varyant, 7 rig = 18.

## 7. Ses görünürlüğü

### 7.1 Ses çizgisi

Dinleme sırasında ses kaynakları ince ışık çizgileri olarak çizilir. Parçacık değil, LineRenderer/Shader tabanlı tek çizgi.

| Özellik | Değer | Perdeye bağlılık |
| --- | --- | --- |
| Başlangıç | Saatçinin kulağı hizası | — |
| Bitiş | Ses kaynağına **doğru**, kaynağa varmadan 0.6–1.2 m önce söner (çizgi yönü verir, cevabı değil) | — |
| Kalınlık | 2–6 mm (dünya ölçeği), kamera mesafesine göre sabit piksel değil dünya ölçeği | Perde yükseldikçe kalınlaşır: en pes 2 mm → en tiz 6 mm |
| Titreşim | Çizgi boyunca sinüs ofseti, genlik 1–2 cm | Frekans perdeyi birebir izler: 2 Hz (pes) → 12 Hz (tiz) |
| Renk | Kor turuncusu `#E8701A` çekirdek, halka vurgu rengi uç | Renk perdeyi taşımaz (renk körlüğü kuralı) |
| Emissive | 4 → 6 | Perdeyle |
| Halka istisnaları | Nefes: yalnız dünya durmuşken çizilir. Gölge: öbür benliğin adımları ikinci, mor uçlu çizgi. Ayna: çizgi kaynaktan kulağa doğru (ters). Sessizlik: çizgi yok | — |

### 7.2 Taşın dalga çizgileri

Taşın yüzeyinde konsantrik, ince oyuk çizgiler. Shader'da UV tabanlı prosedürel halkalar: sıklık (halka/cm) perdeyi izler: 0.8 (pes, çoğu sır söylendi) → 2.4 (tiz, çoğu sır saklandı). Çizgiler çok hafif emissive (0.3), Ân odasında beyaz ve 2.0. Taş sallanırken halkalar sallanma hızında yavaşça akar (UV ofset).

### 7.3 Kor

Avuç içi kadar (≈ 7 cm) ışık topu. Çekirdek `#FFE0B0` emissive 7, hale `#E8701A` emissive 2 + halkanın vurgu rengi %20 karışım. Hale yumuşak, parçacık yok, tek bir additive sphere + bloom. Kuleye takılınca çark kenarına yayılır (1.5 sn) ve çekirdek söner.

---

## 8. Tipografi ve metin

Oyun içi metin yalnız: sır cümlesi (ekranda belirip silinir), ses altyazıları (erişilebilirlik seçeneği), kitabe/mezar taşı oymaları (3D, font değil mesh), sinematik altyazıları, ana menü (kulenin kendisi; metin yalnız "devam/yeni/ayarlar" eşdeğeri üç kelime, kule kapısında oyma).

| Kullanım | Yazı tipi önerisi | Lisans | Türkçe karakter | Boyut (1080p) | Not |
| --- | --- | --- | --- | --- | --- |
| Sır cümlesi, sinematik mısraları | **EB Garamond** (Google Fonts) | OFL | Var — doğrulanacak (İ, ı, ğ, ş glifleri kontrol edilir) | 34–38 px, satır aralığı 1.4 | Serif, eski kitap hissi, mürekkep üslubuyla uyumlu |
| Ses altyazıları ("su damlıyor") | **Noto Sans** (Google Fonts) | OFL | Var | 28 px | Okunabilirlik önceliği; italik kullanılır |
| Oyma metinler (kitabe, mezar) | Font yok; harf başına mesh. Biçim referansı: Garamond büyük harf | — | — | — | Harf silinmesi mesh değişimiyle |

Sır cümlesi animasyonu: belirme 0.8 sn (opaklık 0→1, hafif 4 px yukarı kayma), bekleme cümle uzunluğuna göre 3–5 sn (okuma hızı 12 karakter/sn üzerinden), silinme 1.6 sn (karakterler soldan sağa teker teker mürekkep gibi dağılır; shader: harf başına noise ile alpha erozyonu). Ekranda konum: alt üçte bir çizgisi, ortalanmış, maksimum genişlik ekranın %60'ı. Renk `#EFE6D8`, %85 opaklık, arka fon yok, hafif siyah dış gölge (2 px, %60).

---

## 9. Malzeme ve model

### 9.1 Blender iş akışı

1. Blockout (gri kutular) → Unity'ye FBX, kamera kadrajı onaylanır. Kadraj onaylanmadan detay modellenmez.
2. Modelleme: ölçek 1 BU = 1 m; origin zeminde; modifier'lar uygulanmış; normaller dışa.
3. UV: tek UV seti + ikinci UV lightmap için (Unity Generate Lightmap UVs yerine Blender'da elle; yüzey alanı oranı korunur).
4. Vertex color R kanalı = yıpranma maskesi (bkz. 5.2); G kanalı = ıslaklık (mağara); B = emissive maskesi (kök damarları).
5. Dışa aktarım: FBX, Apply Transform, −Z Forward / Y Up, yalnız mesh (malzeme Unity'de).
6. Adlandırma: `KD_<Alan>_<Nesne>_<Varyant>` (örn. `KD_Kasaba_Degirmen_KirkYil`).

### 9.2 Poligon bütçesi (üçgen)

| Varlık | Hedef | Tavan |
| --- | --- | --- |
| Oda (kök + taş + bulmaca nesneleri) | 60k | 120k |
| Kule (iç ve dış, 7 kat çark) | 150k | 250k |
| Kasaba toplamı (bir çağ görünürde) | 600k | 900k |
| Karakter | 10k | 12k |
| Bekçi hayvanı | 5k | 6k |
| Köpek | 9k | 11k |
| Taş (yakın plan, Ân) | 20k | 30k |

Hedef donanım: GTX 1060 / RX 580 sınıfı, 1080p 60 fps. Tek dinamik ışık ve pişirilmiş sahne bu bütçeyi rahat taşır; bütçeyi asıl zorlayan kasaba çağ varyantlarının aynı anda bellekte durmasıdır — yalnız aktif çağ yüklenir (Addressables).

### 9.3 Texel density

- Oda ve kule: 512 px/m (yakın bakılan yüzeyler: kitabe, kapak, taş 1024 px/m).
- Kasaba dış yüzeyler: 256 px/m.
- Karakter: 2048 doku, yaklaşık 1024 px/m gövdede.
- Doku formatı: BC7 (albedo, normal), BC4 (maske). Trilinear, aniso 4.

### 9.4 Poly Haven (CC0) doku kategorileri

Belirli varlık adları burada yazılmaz; aşağıdaki arama terimleriyle bulunur, seçilen adlar `varlik-listesi.md` dosyasına eklenir ve lisans (CC0) teyit edilir.

| İhtiyaç | Arama terimi (Poly Haven) | Kullanım | Durum |
| --- | --- | --- | --- |
| Mağara kireçtaşı | `limestone`, `rock wall`, `cave` | Oda duvarları, tavan | doğrulanacak |
| Kule kesme taş | `castle wall`, `stone bricks`, `medieval blocks` | Kule dış | doğrulanacak |
| Kaba taş duvar (kasaba) | `rough stone wall`, `dry stone` | Hane alt katları | doğrulanacak |
| Eski ahşap kalas | `wood planks`, `weathered wood`, `old planks` | Çark, cumbalar, kapak kenarı | doğrulanacak |
| Ham ahşap tomruk | `bark`, `wood log` | Çark ana gövdeleri | doğrulanacak |
| Toprak zemin | `dirt`, `forest ground`, `mud` | Toprak halkası zemini, kasaba sokakları | doğrulanacak |
| Kalay / mat metal | `tin`, `metal plate`, `scratched metal` | Fener gövdesi, kapak halkası | doğrulanacak |
| Bronz (çan) | `bronze`, `brass` | Çan | doğrulanacak |
| Islak kaya | `wet rock`, `river rock` | Su halkası | doğrulanacak |
| Keçe / yün | `fabric wool`, `felt` | Saatçi başlığı, kepenek | doğrulanacak |
| Kiremit / toprak dam | `roof tiles`, `clay tiles` | Kasaba çatıları | doğrulanacak |

Kural: Poly Haven dokuları olduğu gibi kullanılmaz; albedo parlaklığı %18–35 bandına çekilir (bkz. 2.1), renk doygunluğu −20 düşürülür. Palet dokudan değil ışıktan gelir.

---

## 10. Renk körlüğü ve okunabilirlik

### 10.1 İlke

Oyunun hiçbir mekanik bilgisi yalnız renkle taşınmaz. Renk atmosfer verir; bilgi kalınlık, sıklık, biçim ve konumla taşınır. Bu kural dikey dilimden itibaren geçerlidir (dünya kitabı: erişilebilirlik katmanı dekor değil).

### 10.2 Halka vurgu renklerinin ayrışması

Vurgu renkleri halkayı "tanımak" içindir, bir bulmacayı çözmek için değil; bu yüzden ayrışma şart değil ama istenir. Deuteranopi/protanopi simülasyonu altında (Unity'de bir Color Blind Renderer Feature ya da Resolve'da simülasyon LUT'u ile kontrol edilir):

| Halka | Renk | Deuteranopi altında | Protanopi altında | Ayrışma |
| --- | --- | --- | --- | --- |
| Toprak | Kahve `#8A5A2B` | Koyu hardal | Koyu hardal | Nefes'ten parlaklıkla ayrılır |
| Su | Yeşil `#2E8B7A` | Gri-mavi | Gri-mavi | Gölge morundan parlaklıkla ayrılır (yeşil daha açık) |
| Nefes | Süt beyazı `#EFE6D8` | Değişmez | Değişmez | Tek açık nötr; sorun yok |
| Gölge | Mor `#5B3A7A` | Koyu mavi | Koyu mavi | Su'dan koyuluğuyla ayrılır |
| Ayna | Gümüş `#B8BFC6` | Değişmez | Değişmez | Nefes'ten sıcaklık değil parlaklıkla (gümüş daha koyu) ayrılır |
| Sessizlik | — | — | — | Rengin yokluğu her görüşte aynı |
| Ân | Beyaz | Değişmez | Değişmez | — |

Riskli çift: Su yeşili ile Gölge moru, her ikisi de maviye düşer. Çözüm: parlaklık farkı korunur (yeşil L≈52, mor L≈30) ve iki halkanın kök dokusu farklıdır (ıslak/parlak vs kuru/mat). Tritanopi için Toprak kahve ile Gölge mor yakınlaşabilir; kök kalınlığı farkı (0.35 m vs 0.20 m) bunu taşır.

### 10.3 Renge bağlı olmayan sinyaller

- Ses çizgisi: perde = kalınlık + titreşim sıklığı. Renk yalnız halka kimliği.
- Taş dalgaları: perde = çizgi sıklığı. Renk yok.
- Kule katları: yanan/kararan = emissive var/yok + çark dönüyor/duruyor (hareket). Renk değil.
- Kitabe: dolu/boş = oyma var/yok (geometri).
- Köpeğin reddi: beden dili (öne eğik, hareketsiz), renk yok.
- Fener titremesi (kırk yıl uyarısı): yoğunluk ve frekans, renk yok.
- Gamepad titreşimi perdeyi birebir izler; altyazı seçeneği her ses ipucunu yazar.

### 10.4 Kontrast kontrolü

Sır cümlesi metni (`#EFE6D8` %85) ile en açık zemin (süt beyazı tozlu Nefes odası) arasında kontrast riski vardır; Nefes'te sır metni arkasına %30 is karası yumuşak bir leke (radial gradient, 1.5× metin kutusu) eklenir. Diğer halkalarda gerek yok (zemin daima koyu). Hedef: WCAG AA (4.5:1) her halkada.

---

## Ek: Dikey dilimde ölçülecekler

- Fenerin çağ derecelendirmesinden korunması (3.6'daki "warm pass") çalışıyor mu.
- Kamera kademeleri 4.3: Toprak ile Su arasındaki fark hissediliyor ama fark ediliyor mu (fark edilmemeli).
- Ses çizgisinin 0.6–1.2 m erken sönmesi bulmacayı çözülebilir bırakıyor mu.
- Köpek gölgesi morph 0.12 (Su) oyuncuya görünür mü (görünmemeli; 0.28'de ilk fark edilmeli).
- Kök mavisi ambient 0.35 çok mu karanlık (OLED ve IPS ekranlarda ayrı bakılır).

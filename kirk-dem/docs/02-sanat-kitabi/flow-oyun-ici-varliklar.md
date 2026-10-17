# Flow ile Oyun İçi Varlıklar — Üretim Rehberi

Karar K-18 (17 Ekim 2026): Google Flow oyunun içinde de kullanılır, ama üç sınıfta ve beş yasakla. Amaç tek kişilik stüdyonun en pahalı iki işini hızlandırmak: 2D boyama ve doku. Bunu yaparken görsel dil bozulmamalı ve Steam bildirimi dar kalmalı. Açılış efsanesinin kuralları ayrı belgededir (`flow-uslup-kitabi.md`); bu belge oyunun 3D dünyasına giren varlıklar içindir.

## 1. Üç sınıf

| Sınıf | Ne | Oyuna girer mi | Steam bildirimi |
| --- | --- | --- | --- |
| **A — Referans** | Konsept kareleri, Blender referans sayfaları, renk ve ışık denemeleri, illüstratör brifi | Hayır | Gerekmez; yalnız geliştirmede kullanılır |
| **B — Arka plan ve doku katmanı** | Uzak dağ kartları, gökyüzü katmanları, mürekkep ve kâğıt katmanları, yağmur, kar, toz, duman, su kırılması dokuları | Evet, oyuncunun odağında değil | "Arka plan resimleri ve bazı doku katmanları yapay zekâ ile üretildi" |
| **C — Anlatı sinematiği** | Açılış efsanesinin hareketi | Evet | Açılış satırı (`flow-uslup-kitabi.md` §6) |

Bir varlığın sınıfı belirsizse üst sınıf sayılır. A'da kalan bir kare oyuna girerse B ya da C olur ve bildirime eklenir.

## 2. Beş yasak (her sınıfta)

1. **Yüz ve karakter.** Saatçi, köpek, kasabalılar, bekçiler 3D'dir ve elle yapılır. Flow karakter dokusu, yüz ya da silüet üretmez; A sınıfındaki referans sayfaları dışında.
2. **Yazı.** Kitabe, defter, mezar taşları, fotoğraf kenarları, sır cümleleri elle yazılır. Türkçe yazının tek harfi bile Flow'dan gelmez.
3. **Ses.** Veo klibinin sesi her zaman atılır (`flow.sh strip-audio`). Dünya kitabı: yapay ses yok.
4. **Oynanışın odağı.** Oyuncunun baktığı ve bulmacayı çözen hiçbir nesne (dem, taş, kapak, çark, bekçi, diorama değişkeni) Flow'dan gelmez. Flow yalnız odağın arkasını ve havasını yapar.
5. **Kimlik.** Tanınabilir dini sembol, gerçek yer, gerçek kişi, marka yok (`flow-uslup-kitabi.md` §1.1 negatif listesi her prompta eklenir). "Toros" adı promptta geçmez; dağ tarifle verilir.

## 3. Varlık listesi ve sıra

Sıra dikey dilim planına bağlıdır (`docs/08-dikey-dilim-plani.md`). Önce A sınıfı, çünkü modellemeyi hızlandırır ve hiçbir bildirim gerektirmez.

| # | Varlık | Sınıf | Nerede | Adet | Biçim | Hafta |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Karakter ve köpek referans sayfası | A | Bütün konsept karelerinde "ingredient" | 2 | Görüntü | 19–25 Eki |
| 2 | Konsept kareleri: B1, C1, A1, A7, sonra kalan sekiz | A | Sanat kitabı adım 2 | 12 + varyant | Görüntü 16:9 | 19 Eki–8 Kas |
| 3 | Blender referans sayfaları: kule ön ve yan, üç ev tipi, değirmen, kahve, kapak | A | Modelleme | 8 | Görüntü, ortografik | 2–15 Kas |
| 4 | Bekçi rig silüet sayfaları (K-15'in yedi rigi) | A | Modelleme | 7 | Görüntü | 2–15 Kas |
| 5 | Açılış anahtar karelerinin ilk geçişi | A → C | İllüstratör bunun üstüne boyar (K-05) | 12 | Görüntü 16:9 → 21:9 kırpma | Kasım |
| 6 | Uzak dağ kartları, bugün çağı | B | Kasaba arka planı | 5 kart | Görüntü → `edge-fade` | 9–15 Kas |
| 7 | Dağ kartlarının çağ ve mevsim varyantları | B | Kasaba; 6 numaranın düzenlemesi, yeniden üretim değil | 5 × 6 | Görüntü düzenleme | Faz 1 |
| 8 | Gece göğü bulut katmanı | B | Kasaba, açılış | 3 | Görüntü, siyah zemin | Faz 1 |
| 9 | Su dioramasının altın arka planı | B | Su halkası | 2 | Görüntü | 14–20 Ara |
| 10 | Su kırılması (caustic) döngüsü | B | Su halkası, ışık çerezi | 1 | Video → `loop` | 14–20 Ara |
| 11 | Askıda toz | B | Nefes halkası | 1 | Video → `flipbook` | Faz 2 |
| 12 | Kar | B | Açılış, kasaba bugün çağı | 1 | Video → `flipbook` | 28 Ara–3 Oca |
| 13 | Çıra dumanı | B | R1-04 | 1 | Video → `flipbook` | Faz 2 |
| 14 | Yağmur | B | Üç son | 1 | Video → `loop` ve `flipbook` | Faz 2 |
| 15 | Mürekkep yayılması ve kâğıt dokusu | B | Mürekkep efekti hattı (Bir yıl, Kırk yıl, Kökler, sonlar); sır cümlesinin silinmesi | 3 | Video → `loop`; görüntü | Faz 2 |

## 4. Teknik şartlar

**Model.** Görüntü için Flow'daki en yüksek kaliteli görüntü modeli (Ekim 2026'da Nano Banana Pro ya da Imagen 4), video için Veo'nun en yüksek kalite seçeneği. Çözünürlük Flow'da seçilebilen en yüksek değerdir; 1080p altı hiçbir çıktı oyuna girmez. Flow'un özellikleri sık değişir; seçenekler [Flow destek sayfasından](https://support.google.com/flow/answer/16352836) doğrulanır.

**Tutarlılık.** Konsept karelerinde saatçi ve köpek her zaman aynı referans görüntüden ("ingredient") gelir. Çağ ve mevsim varyantları yeniden üretilmez, aynı kare düzenlenir: "aynı görüntü, sonbahar". Böylece kompozisyon kilitli kalır.

**Alfa yok.** Flow saydam çıktı vermez. Yağmur, kar, toz ve duman siyah zemin üzerinde üretilir ve Unity'de toplamalı (additive) karışımla kullanılır. Arka plan kartları `flow.sh edge-fade` ile kenarlardan saydamlığa yumuşatılır ve sahnede birbirine biner; birleştirme (stitch) yapılmaz.

**Hazırlık hattı.** Her video önce sesten arındırılır, sonra kullanım yerine göre döngü ya da atlas olur. Komutlar (`kirk-dem/tools/flow/flow.sh`):

```bash
flow.sh strip-audio ham.mp4 sessiz.mp4          # her video için zorunlu
flow.sh loop sessiz.mp4 dongu.mp4 1             # dikişsiz döngü: su kırılması, yağmur, mürekkep
flow.sh flipbook sessiz.mp4 atlas.png 8 8 256   # 64 karelik 2048 px atlas: kar, toz, duman
flow.sh edge-fade dag_p01.png dag_p01_a.png 160 80
flow.sh luma dag_p01_a.png 4 14                 # çağın parlaklık aralığında mı
```

**Parlaklık aralıkları.** Sanat kitabının "dokuyu değil ışığı sıcak tut" kuralının B sınıfındaki karşılığı:

| Varlık | Ortalama parlaklık |
| --- | --- |
| Uzak dağ kartı, bugün, gece | %4–14 |
| Uzak dağ kartı, gündüz ya da ikindi | %12–28 |
| Albedo olarak kullanılan her doku | %18–35 (sanat kitabı §2.1) |
| Siyah zeminli efekt (kar, yağmur, toz, duman) | %1–10 |

Aralık dışındaki bir çıktı ya yeniden üretilir ya DaVinci'de `KirkDem_Flow_v1.cube` LUT'undan geçirilir. Renk düzeltmesi Unity'de yapılmaz; Unity'de çağın Volume profili zaten derecelendirir, çift derecelendirme rengi bozar.

**Unity içe aktarma.** `Assets/_KirkDem/Art/Flow/<sınıf>/` altına konur. İkili dosyalar Git LFS ile izlenir (K-17).

| Tür | Ayar |
| --- | --- |
| Arka plan kartı | Texture Type Default, sRGB açık, Alpha Is Transparency açık, Wrap Clamp, Max Size 4096, Mipmap açık; Unlit Transparent malzeme, sis etkisinde |
| Efekt atlası | sRGB açık, Wrap Clamp, Max Size 2048, Mipmap kapalı; VFX Graph ya da Particle System Texture Sheet Animation 8×8; Additive |
| Döngü video | `StreamingAssets` değil `Assets` altında VideoClip, Transcode açık, H.264; VideoPlayer → Render Texture → Unlit malzeme; ses yok |
| Kâğıt dokusu | Wrap Repeat, Mipmap açık; yalnız mürekkep efekti Renderer Feature'ında |

**Adlandırma.** `FLOW_<sınıf>_<varlık>_<çağ|halka>_<parça>_v<nn>.<uzantı>`. Örnek: `FLOW_B_dag_bugun_p03_v02.png`, `FLOW_B_kar_atlas_v01.png`.

**Kayıt.** Oyuna giren her Flow çıktısı `kirk-dem/art/flow-manifest.csv` dosyasına bir satır yazılır: dosya adı, sınıf, model, tarih, prompt, kullanıldığı yer. Bu hem Steam bildiriminin dayanağıdır hem de bir varlığı aynı üslupta yeniden üretmenin tek yoludur.

## 5. Promptlar

### 5.1 Ortak blok (oyun içi görünüm)

Açılışın mürekkep üslubundan farklıdır; bu blok oyunun 3D görünümünü tarif eder. Her promptun başına eklenir; `flow-uslup-kitabi.md` §1.1 negatif listesi sonuna.

```
STYLE: Painterly concept art for a stylized 3D game. Dark and quiet. A single warm light source (a hand lantern, warm orange #FFB36B) in a world of cold deep blue (#1E3A5F) shadow; nothing outside the light falls to pure black, it falls into deep blue. Simple, slightly chunky hand-modeled shapes; rough stone, old wood, packed earth; dark, muted surface colors. Characters are stylized and faceless: no nose, no mouth, no eyebrows, only two small glowing eye dots. Fixed camera, slightly from above, 35 mm lens. Generous empty darkness. Matte, low saturation, soft bloom only around light sources.
```

### 5.2 Referans (A)

**Karakter ve köpek sayfası (her konsept karesinin ingredient'i).**
```
Character reference sheet on a plain mid-grey background: a forty-year-old village clockmaker shown from front, side and back. Stylized, faceless, two small warm glowing eye dots, short dark beard silhouette, plain woollen cap, long work coat, heavy boots, a small hand lantern in the left hand. Next to him, a large pale shepherd dog, calm, shown from front and side. Flat even lighting, no shadows on the background, no text.
```

**Kule ortografik referansı.**
```
Orthographic front elevation of a tall square stone clock tower in a mountain village: rough limestone blocks, seven narrow window slits stacked up the shaft, a round clock face with two hands near the top, a small wooden belfry with a single bell on the roof, a heavy wooden door at the base. Flat neutral lighting, plain light background, architectural reference drawing look, no perspective, no text.
```
Yan görünüş için aynı prompt, "Orthographic side elevation". Ev tipi, değirmen ve kahve aynı kalıpla; kasaba mimarisi sanat kitabı §5.2'den: taş alt kat, ahşap üst kat, ahşap cumbalar.

**Bekçi rig silüet sayfası (örnek: dörtbacaklı).**
```
Silhouette design sheet: four animals drawn as flat dark shapes on a plain light background, side view, same scale grid: a deer, a goat, a tortoise, a hedgehog. Each has only two small glowing eye dots, no other facial detail. Simple readable silhouettes for a stylized game. No text.
```

### 5.3 Konsept kareleri (A)

Her kare `halka-konseptleri.md` içindeki brifin İngilizce kısaltmasıdır; ışık değerleri ve göz ışığı rengi brifteki gibi kalır. Karakter ve köpek sayfası her karede ingredient olarak eklenir.

| Kare | Prompt (ortak bloğun ardından) |
| --- | --- |
| B1 Kule, kar gecesi | `Night, snow. A village square seen from a raised corner. A tall square stone clock tower in the right third, its seven window slits dark, clock hands stopped. Snow-covered roofs on the left, an empty square in the middle. The only warm light is one café window at lower left. The tower door is ajar with lantern light leaking out; a pale dog sits at the door, its shadow cast long across the snow.` |
| C1 Kasaba bugün | `Same view as the tower-at-night frame, late afternoon in winter. Smoke from three chimneys, the café window warm, a water mill wheel turning in the far left background. The tower's shadow falls sharply across the square like a sundial. Two faceless villagers as distant silhouettes.` |
| A1 Toprak | `Inside an earthen cave room seen from slightly above, a diorama. The clockmaker with his lantern in the left third. In the right third a single green sprout rises from the soil and a deer stands before it, head turned to the sprout, eyes glowing brown. Thick dry roots descend from the ceiling into the floor. The dog sits by the lantern. The centre is empty.` |
| A2 Su | `A cave room with a shallow pool in the middle. Beneath the water, at miniature scale, a tiny golden-lit village with houses and a stream but no tower. The clockmaker kneels at the left edge, leaning over the water. Across the pool stands a faceless seven-year-old child in old clothes, eyes glowing water-green, looking at the water. Wet dark roots whose tips glow faint green where they touch the water.` |
| A3 Nefes | `An ash-grey cave room full of thousands of dust motes frozen in mid-air, glowing milky white only where the lantern light reaches. The clockmaker holds his breath, body tense, in the left third. In the right third an old faceless woman sits with hands on her knees, the dust thicker around her like a halo. Petrified roots.` |
| A4 Gölge | `A cave room split in two: the left half in lantern light, the right half in shadow. In the shadow stands an older version of the clockmaker, sixty, stooped, grey hair silhouette, holding his own lantern whose glow is violet and lights only itself. Violet rim light outlines the shadow side. Both figures look at a stopped gear in the middle. The dog sits by the lantern but its shadow on the wall is standing.` |
| A5 Ayna | `A cave room that is an upside-down graveyard: blank headstones hang from the ceiling, earth above. The clockmaker stands normally on the floor. Facing him, upside down among the hanging stones, a mirrored faceless villager in a heavy coat and flat cap, colours inverted. Thin grey-blue roots grow upward from the floor and wrap the stones. Silver rim light on stone edges.` |
| A6 Sessizlik | `An almost empty cave room: flat stone floor, thin dried cracked roots, a bare stone ledge opposite the lantern with nothing on it. The lantern sits low on the floor and its light trembles. The dog leans forward at the threshold, refusing to enter; its shadow on the wall is long, larger than the dog, ears laid back. Only three colours: warm orange, deep blue, soot black.` |
| A7 Ân | `Close portrait at eye level of the faceless clockmaker holding a rough round stone at chest height. White light from inside the stone lights him from below; his eye dots have turned white. Behind him only flat stone and darkness. Shallow depth of field, focus on the eye dots. The lantern is on the floor out of frame, a faint orange glow at the bottom edge.` |

C2, C3 ve C4 kareleri C1'in düzenlenmesidir, yeniden üretim değil: "aynı görüntü, bahar sonu, kar yok" (C2); "aynı görüntü, kırk yıl sonra, üç çatı çökmüş, değirmen durmuş, kule kapısında yaşlı bir kadın oturuyor" (C3); "aynı görüntü, terk edilmiş, kimse yok, otlar meydanı yarı örtmüş" (C4). Ayrıntılar `halka-konseptleri.md` C bölümünde.

### 5.4 Arka plan ve doku katmanı (B)

**Uzak dağ kartı (bugün, kış gecesi).** Beş kart, her biri ufkun başka bir yönü; kartlar arasında %15 örtüşme bırakılır.
```
A distant rugged limestone mountain ridge seen from a valley at night in winter, painted as a flat background card for a game. Snow on the upper slopes, dark pine-less rocky faces, no buildings, no lights, no roads. Cold deep blue sky gradient above, slightly lighter toward the horizon. Very low contrast, distant atmospheric haze. Wide 16:9 framing with the ridge line in the lower half. Nothing in the foreground.
```
Varyantlar düzenlemeyle: "same image, late spring, no snow, green on lower slopes" · "same image, summer dusk" · "same image, autumn, bare and brown" · "same image, forty years later, nothing changed but a paler, colder light" · "same image, overcast grey-blue, abandoned stillness".

**Gece göğü bulut katmanı.** `Thin wispy night clouds drifting over a pure black background, soft edges, faint blue-grey, no stars, no moon, no ground. For additive layering.`

**Su dioramasının altın arka planı.** `A soft golden-hour sky and distant rolling hills seen through slightly rippling water, warm amber light, dreamlike and blurred, no buildings, no people.`

**Su kırılması (video).** `Top-down view of caustic light patterns from rippling water dancing on a dark stone floor, slow gentle motion, green-gold light lines on near-black. Camera static.`

**Kar (video).** `Large soft snowflakes falling slowly and steadily against a pure black background, no ground, no wind gusts, evenly spread, camera static.`

**Yağmur (video).** `Thin straight rain streaks falling steadily against a pure black background, no splashes, no ground, no lightning, camera static.`

**Askıda toz (video).** `Tiny dust motes floating almost motionless in a dark void, catching a faint milky-white light, extremely slow drift, pure black background, camera static.`

**Çıra dumanı (video).** `A thin wisp of grey smoke rising slowly from below and curling, against a pure black background, camera static.`

**Mürekkep yayılması (video).** `Black ink slowly blooming and spreading through wet cream-coloured paper, organic feathered edges, top-down, camera static.`

**Kâğıt dokusu.** `Seamless tileable texture of old handmade cream paper with fine fibres and very faint stains, even flat lighting, no text, no creases.` Döşenebilirlik Unity'de 2×2 döşenerek kontrol edilir; dikiş görünüyorsa kullanılmaz.

## 6. Kontrol listesi (oyuna giren her Flow çıktısı)

- [ ] Sınıfı belli (A, B, C); beş yasaktan hiçbirine girmiyor.
- [ ] Video ise sesi atıldı (`strip-audio`).
- [ ] Parlaklık aralığında (`luma`).
- [ ] Adı kurala uyuyor ve `Assets/_KirkDem/Art/Flow/<sınıf>/` altında.
- [ ] `flow-manifest.csv` satırı yazıldı.
- [ ] Oyunda çağın Volume'ü altında, fener ışığıyla birlikte bakıldı: arka planda kalıyor, odağı çalmıyor.

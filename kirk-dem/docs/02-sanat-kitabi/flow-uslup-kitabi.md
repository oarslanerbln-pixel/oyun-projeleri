# Kırk Dem — Google Flow Üslup Kitabı

Durum: Taslak v0.1 · Bağlı belgeler: `README.md` (sanat kitabı), `halka-konseptleri.md`, dünya kitabı "Sinematikler" bölümü · Kapsam: Açılış efsanesi, Kökler, üç son (Flow); Bir yıl ve Kırk yıl oyun içi kameradan (Flow değil).

## 0. Anlatım ilkesi (dünya kitabından)

Videolar oyunun 3D görüntüsünü taklit etmez. Kasabanın kendi efsanesini anlatan resimli bir kitap gibidir: mürekkep ve kor ışığı, minyatür perspektifi, az hareket. Kareler arası tutarsızlık bir kusur değil, üsluptur: her kare ayrı bir sayfa, her sayfa aynı elden çıkmış gibi.

Bu belge iki şeyi sabitler: (1) her promptun başına eklenen **ortak üslup bloğu**, (2) her klibin başlangıç görseli olarak kullanılacak **sabit kareler**. Sabit kareler beğenilmeden klip üretilmez.

---

## 1. Ortak üslup bloğu

Her promptun başına aynen eklenir (İngilizce; Flow İngilizce promptta daha tutarlı sonuç verir — doğrulanacak). Türkçe karşılığı ekipte iletişim içindir.

```
STYLE: Hand-inked illustration on aged paper, in the manner of a painted manuscript page — not photorealistic, not 3D render, not anime. Flat ink line work with limited brush shading. Single warm light source (ember orange) in an otherwise cold, deep blue darkness. Palette strictly: ember orange (#E8701A), root blue (#1E3A5F), soot black (#0A0908), paper cream (#EFE6D8). No other hues unless specified. Miniature-painting perspective: slightly flattened depth, stacked planes, no true vanishing point. Very little motion. Grain of paper visible. Ultra-wide 21:9 cinematic frame with generous empty darkness.
```

Türkçesi (iç kullanım): Eski kâğıt üzerine elle mürekkep çizim, boyalı yazma sayfası üslubunda; fotogerçekçi değil, 3D değil, anime değil. Düz mürekkep çizgisi, az fırça gölgesi. Soğuk derin mavi karanlıkta tek sıcak (kor turuncusu) ışık. Palet yalnız dört renk. Minyatür perspektifi: düzleşmiş derinlik, üst üste düzlemler, gerçek kaçış noktası yok. Çok az hareket. Kâğıt dokusu görünür. 21:9, bol boş karanlık.

### 1.1 Negatif yönlendirmeler (her prompta eklenir)

```
AVOID: realistic human faces, any facial features (no nose, no mouth, no eyebrows — only eye glow), any text or lettering or calligraphy, modern objects (wires, vehicles, plastic, glass panes, electric light), recognizable religious symbols (no crescent, no cross, no star, no dome with finial, no prayer beads, no specific robes), recognizable real places or people, a visible tree or trunk or canopy (roots only), bright daylight, saturated greens or reds, lens flare, 3D render look, photographic depth of field, camera shake, fast motion, crowds.
```

Not: Flow negatif prompt alanı sunmuyorsa bu blok ana promptun sonuna "Do not include:" ile eklenir. Doğrulanacak.

### 1.2 Palet kilidi

Flow'un paleti tutması beklenmez. Tutmazsa iki yol: (a) sabit kareyi Inkscape/Resolve'da palete çekip klibin başlangıç görseli yapmak (önerilen), (b) Resolve'da proje LUT'u ile düzeltmek (bkz. §5). Her iki durumda da kaynak kare arşivlenir.

---

## 2. Sabit kareler (üslup kitabı)

Hedef 12–15 kare. Her kare için 4 varyant alınır; beğenilen varyant `uslup/kareler/<no>-<ad>-vN.png` olarak arşivlenir ve sonraki kliplerin başlangıç görseli olur. Kare üretim sırası: 01, 02, 03, 05, 08 önce (bunlar kule-kasaba-kapak-köpek-taş: üslubun bel kemiği); beğenilmezse üslup bloğu revize edilir, diğerlerine geçilmez.

Her satır: **[ortak üslup bloğu] + aşağıdaki sahne metni + [negatif blok]**.

| No | Ad | Sahne promptu (İngilizce) | Kullanım |
| --- | --- | --- | --- |
| 01 | Kule, kar gecesi | `A tall square stone clock tower with a single bell at the top stands over a small mountain town under snow at night. Seven dark window slits up the tower's side. The clock face shows stopped hands. A single warm window glows in a low building at the far left. Everything else is cold blue darkness. The tower sits in the right third of the frame.` | Açılış son karesi; üç sonun temel karesi |
| 02 | Dağın zamansız çağı | `A bare mountain slope at the edge of a vast cold blue dusk, before any town existed. No buildings, no paths, no people. A single ember-colored point of light far off, like a lantern being carried toward the slope. Enormous empty sky.` | Açılış 1. sahne |
| 03 | Yabancı kule kurar | `A lone hooded figure seen from behind, small in frame, stacking cut stones into the first course of a tower on a mountain slope at night. A lantern rests on the ground beside the stones, the only light. The figure's face is not visible. Roots show faintly in the exposed earth.` | Açılış 2. sahne |
| 04 | Taş yerleştirilir | `Close view of two large stylized hands lowering a rough, round, dark grey-green stone the size of a head onto an iron chain inside a dark stone chamber. Thin concentric ripple lines are carved into the stone's surface. Warm lantern light from one side. No face visible.` | Açılış 3. sahne; Dönüş sonu |
| 05 | Kapak | `A round stone hatch set into a stone floor, about the width of a doorway, with an iron ring at its center. The hatch is slightly lifted, and from the gap beneath it spills deep cold blue darkness and the top of a stone stair. A lantern's warm light falls across the hatch from the upper left. A large pale shepherd dog sits at the hatch's edge, looking down into it.` | Açılış 4. sahne; Kalış sonu; Kökler başlangıç |
| 06 | Yabancı iner, dönmez | `Looking down a narrow stone stairway that descends into blue darkness. Far below, a small warm lantern light is moving away, almost gone. Thick roots cross the stair walls. No figure is clearly visible, only the lantern's glow receding.` | Açılış 4. sahne |
| 07 | Kasaba kuleyi kurmayı öğrenir | `A row of five faceless townspeople in simple old wool clothing, seen in silhouette against a stone tower under construction, passing cut stones hand to hand. Their eyes are small warm points of light. Lantern light from the left. Cold blue night behind them.` | Açılış 5. sahne |
| 08 | Köpek ve gölgesi | `A large pale shepherd dog sits beside a lantern on a stone floor. The lantern throws the dog's shadow long across a rough stone wall behind it. The shadow is slightly more wolf-like than the dog — ears a little sharper, muzzle a little longer — but the dog itself is calm and ordinary. Warm light, cold blue shadows.` | Kökler; Kalış |
| 09 | Taş, yakın | `A rough, round, dark grey-green stone resting in two open stylized hands. Fine concentric ripple lines on its surface. A faint white light from within the stone lights the hands from below. Everything beyond the hands is black. No face.` | Kökler son kare; üç son açılışı |
| 10 | Kökler, aşağı | `Looking straight down a vertical shaft of roots. Thick roots at the top become thinner and drier toward the bottom, where they end in a point of white light. No trunk, no tree, no leaves — only roots descending. The roots nearest the viewer are faintly lit ember orange; the rest fade to cold blue.` | Kökler videosu ana sahne |
| 11 | Çan sallanır, yağmur | `The top of a stone clock tower with a single bronze bell, seen from below at a steep angle. The bell is mid-swing. Rain falls in a tight column onto the small square in front of the tower and nowhere else — the rooftops around it are dry. Night, warm light from the tower's windows, cold blue beyond.` | Dönüş sonu |
| 12 | Çırak ve usta | `Inside the base of a stone tower: a tall faceless man in a dark wool coat shows a small faceless child how to hold a lantern up toward a huge wooden gear. The gear's edge glows faintly ember orange. Seven stacked gears rise into darkness above them.` | Dönüş sonu |
| 13 | Kapalı kapak, yağmur | `A round stone hatch set into a stone floor, closed, with an iron ring. Rain falls on the hatch alone from somewhere above; the floor around it is dry. No dog. No lantern. A faint cold blue light, as if from a window out of frame. Very still.` | Kalış sonu |
| 14 | Sökülen kule | `A stone clock tower being taken apart stone by stone at dusk; only the lower floors remain, the top is open sky. Cut stones lie stacked in the square. A single faceless man in a dark coat carries one stone toward the left. Cold blue, one warm lantern on the ground.` | Dağıtış sonu |
| 15 | Mezarlık, gömülen taş | `A small hillside graveyard of plain uncarved stones at dawn, blue-grey light. Freshly turned earth in the foreground with a round grey-green stone half buried in it. Rain falls only on that patch of earth. No people. A town with a missing tower is faintly visible below.` | Dağıtış son kare |

Opsiyonel 16: Kahve duvarı, yedi çerçeve (`Seven empty wooden picture frames on a dark plaster wall...`) — yalnız Flow kredisi yeterse.

### 2.1 Kare onay ölçütleri

Bir kare şu beşini geçerse arşive girer:
1. Palet dört rengin dışına çıkmıyor (küçük sapmalar Resolve'da düzelir; büyük yeşil/kırmızı varsa red).
2. Yüz hattı yok; gözler ışık noktası.
3. Metin/harf yok (Flow sık sık yazı uydurur; tek harf bile varsa red ya da Inkscape'te kapatılır).
4. Tanınabilir dini sembol yok (özellikle kule tepesi ve cami çevresi kontrol edilir).
5. Hayat Ağacı görünmüyor: gövde, dal, yaprak yok.

---

## 3. Klip üretim kuralları

1. **8 saniyelik parçalar.** Her sahne 8 sn'lik kliplere bölünür. Açılış 90–120 sn → 12–15 klip; Kökler 30–40 sn → 4–5 klip; her son 45–60 sn → 6–8 klip. Toplam ≈ 40–50 klip, her biri 3–4 varyant → 120–200 üretim üst sınır. Dünya kitabındaki 60–80 tahmini iyimserdir; kredi üslup kitabı aşamasında ölçülür ve yetmezse önce açılış ve üç son yapılır, Kökler oyun içi kameraya alınır (dünya kitabı kararı).
2. **Başlangıç karesi zinciri.** Her klibin başlangıç görseli ya onaylı bir sabit kare ya da önceki klibin son karesidir (Resolve'dan PNG dışa aktarılır). Böylece bir sahne içinde süreklilik, sahneler arası ise "sayfa çevirme" hissi kalır.
3. **Hareket promptu asgari.** Hareket yönergesi tek cümle, tek eylem: `The lantern light slowly brightens.` / `The dog turns its head toward the hatch.` / `Rain begins to fall on the square only.` İki eylem birden istenmez.
4. **Kamera hareketi.** Yalnız üç izin: çok yavaş ileri (push-in), çok yavaş aşağı (tilt-down, Kökler), sabit. Pan, zoom-out, el kamerası yok. Promptta: `Camera: static.` ya da `Camera: extremely slow push-in.`
5. **21:9 letterbox.** Flow 16:9 üretir; Resolve'da 2.39:1 maske uygulanır. Kenarlardaki tutarsızlıklar (Flow'un en zayıf bölgeleri) kadraj dışında kalır. Önemli hiçbir öğe üst ve alt %12'lik banda yerleştirilmez — promptta "generous empty darkness at top and bottom" bunun içindir.
6. **Varyant seçimi.** 3–4 varyanttan seçim ölçütü sırayla: (1) onay ölçütlerini geçiyor mu, (2) hareket az mı, (3) palet yakın mı, (4) kompozisyon üçte bir kuralına uyuyor mu. Güzellik dördüncü ölçütten sonra gelir.
7. **Arşiv.** Her üretim (red edilenler dahil) `uslup/uretim/<tarih>-<sahne>-<klip>-<varyant>.mp4` ve promptu `.txt` yanında saklanır. Steam bildirimi ve olası telif sorusu için kayıt gerekir.

---

## 4. Sahne çizelgeleri (Flow)

### 4.1 Açılış efsanesi (90–120 sn)

| Sıra | Süre | Kare | Hareket | Anlatıcı (mısra yeri) |
| --- | --- | --- | --- | --- |
| 1 | 8–16 | 02 Dağ | Uzaktaki fener yaklaşır | Mısra 1 |
| 2 | 16 | 03 Yabancı kule kurar | Taşlar birikir (iki klip, ikinci klip ilk klibin son karesinden) | Mısra 2 |
| 3 | 8 | 04 Taş yerleştirilir | Eller taşı indirir; taş hafif sallanmaya başlar | Mısra 3 ("zaman başlar") |
| 4 | 8 | 01 Kule (çalışan varyant: pencereler yanıyor) | Çan bir kez sallanır | — |
| 5 | 8 | 05 Kapak | Kapak aralanır | Mısra 4 |
| 6 | 8 | 06 İner, dönmez | Fener ışığı uzaklaşır, söner | Mısra 5 |
| 7 | 16 | 07 Kasaba kuleyi kurmayı öğrenir | Taşlar elden ele | Mısra 6 |
| 8 | 8–16 | 01 Kule, kar gecesi (duran) | Hiç hareket; kar yağar | Sessizlik; son kare: bugün, kar, duran çan |

### 4.2 Kökler (30–40 sn, 40. oda öncesi)

| Sıra | Süre | Kare | Hareket | Anlatıcı |
| --- | --- | --- | --- | --- |
| 1 | 8 | 05 Kapak (köpek yok varyantı) | Statik | — |
| 2 | 16 | 10 Kökler, aşağı | Çok yavaş tilt-down; kökler incelir | Tek mısra |
| 3 | 8 | 09 Taş, yakın | Taşın iç ışığı belirir | — |

### 4.3 Üç son (45–60 sn her biri)

| Son | Kareler sırayla | Son kare |
| --- | --- | --- |
| Dönüş | 09 Taş → 04 Taş yerleştirilir (ters: yukarı) → 11 Çan ve yağmur → 12 Çırak ve usta → 01 Kule (çalışan, kitabe boş) | 12 ya da 01; köpek kapıda |
| Kalış | 09 Taş → 08 Köpek ve gölgesi (köpek kalkar, gider) → 13 Kapalı kapak, yağmur → 01 Kule (pencereler yanıyor, akrep sabit) | 13 |
| Dağıtış | 09 Taş → 14 Sökülen kule → 15 Mezarlık, gömülen taş → kasaba kulesiz, sabah | 15 |

Üç sonda da yağmur yalnız bir noktaya yağar; promptta `Rain falls only on X; everything else stays dry.` zorunludur.

---

## 5. DaVinci Resolve: kurgu ve renk eşitleme

1. **Proje:** 1920×1080, 24 fps, Rec.709 Gamma 2.4. Flow klipleri 16:9 gelir; `Output Blanking 2.39` ile letterbox.
2. **Proje LUT'u (Kırk Dem LUT):** Unity'den referans olarak `Bugun` çağı Volume'ü uygulanmış bir oyun içi kare alınır (efsane kamerası, B1 kadrajı). Resolve'da bu kare ile Flow'un 01 numaralı karesi yan yana açılır; Color Match yerine el ile: (a) Lift gölgeleri `#0E1E33`'e çek, (b) Gain ışıkları `#FFB36B`'ye, (c) Saturation −15, (d) Hue vs Sat eğrisinde yeşil ve kırmızı bantları −40. Sonuç `.cube` olarak dışa aktarılır: `KirkDem_Flow_v1.cube`. Bütün Flow kliplerine aynı LUT bir node'da; klip başına yalnız exposure ve küçük sıcaklık düzeltmesi.
3. **Mürekkep efekti (Bir yıl / Kırk yıl oyun içi videoları):** Oyun içi kayıt → Resolve → (a) Edge Detect (ResolveFX Stylize) düşük eşik, blend Multiply %35, (b) Film Grain 35mm 500T %30, (c) hafif Watercolor/Paper Texture overlay (ücretsiz kâğıt dokusu, CC0 — doğrulanacak), (d) aynı LUT. Böylece Flow kareleriyle aynı "sayfa" hissi.
4. **Ses:** Anlatıcı kaydı (Audacity, insan ses) ayrı kanal; oyunun kendi tonları (halka notaları) altta −18 dB. Müzik yok. Yağmur foley'i yalnız yağmur kadrajda görünürken ve mono, sağ ya da sol kanaldan ("başka yerden duyulur").
5. **Altyazı:** Resolve'da değil; Unity Localization üzerinden (TR/EN) oyun içinde çizilir. Resolve'dan yalnız zaman kodları `.srt` olarak dışa aktarılır.
6. **Dışa aktarım:** H.264, 1920×1080 (letterbox gömülü), 24 fps, 12–16 Mbps, AAC 192 kbps, `StreamingAssets/Video/<ad>.mp4`.

---

## 6. Steam yapay zekâ bildirimi — taslak metin

Steam, yapay zekâ ile üretilen içeriğin mağaza sayfasında açıklanmasını ister. Görseller bu kapsamdadır; senaryo, mısralar, seslendirme, kurgu ve oyun içi 3D içerik insan işidir ve öyle yazılır. Nihai metin yayın adımında (üretim planı 11) hukuki okumadan geçer.

**TR (taslak):**
> Bu oyundaki açılış efsanesi, "Kökler" ara sahnesi ve üç son sinematiğinin resimli kareleri, geliştiricinin yazdığı ve yönettiği promptlarla yapay zekâ görüntü/video üretim aracı (Google Flow) kullanılarak oluşturulmuş, ardından geliştirici tarafından elle seçilmiş, renk düzenlemesi yapılmış ve kurgulanmıştır. Oyunun senaryosu, diyalogları, anlatıcı mısraları, seslendirmeleri, müziği/ses tasarımı ve oyun içi tüm 3D içerik (mekânlar, karakterler, animasyonlar) yapay zekâ kullanılmadan üretilmiştir. Oyun içinde çalışma anında yapay zekâ içerik üretimi yoktur.

**EN (taslak):**
> The illustrated frames of this game's opening legend, the "Roots" interlude and the three ending cinematics were generated with an AI image/video tool (Google Flow) from prompts written and directed by the developer, then hand-selected, color-graded and edited by the developer. The game's story, dialogue, narrator verses, voice recordings, sound design and all in-game 3D content (environments, characters, animation) were made without AI. The game does not generate any content with AI at runtime.

Not: "Bir yıl" ve "Kırk yıl" videoları oyun içi kameradan çekildiği için bildirime girmez; metinde bilerek sayılmamıştır. Eğer Flow kredisi yetmez ve Kökler de oyun içi çekilirse metinden "Kökler" çıkarılır.

---

## 7. Kontrol listesi (her Flow üretimi için)

- [ ] Ortak üslup bloğu promptun başında
- [ ] Negatif blok promptun sonunda
- [ ] Başlangıç görseli onaylı bir kare ya da önceki klibin son karesi
- [ ] Hareket tek cümle, tek eylem
- [ ] Kamera: static ya da slow push-in / tilt-down
- [ ] Üst ve alt %12 banda önemli öğe yok
- [ ] Çıktı 5 onay ölçütünden geçti (palet, yüz, metin, sembol, ağaç)
- [ ] Prompt ve çıktı arşivlendi

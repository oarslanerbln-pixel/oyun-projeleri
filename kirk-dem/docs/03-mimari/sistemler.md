# Çekirdek Sistemler — Sözleşmeler

Her sistem için: amaç, girdi/çıktı, durumlar, kenar durumları. Kural metni dünya kitabından (`00-dunya-kitabi.md`) alınmıştır; burada yalnız teknik karşılığı yazılır. Kavram adları (zamanın katlanması vb.) kodda ve veride geçmez; teknik adlar kullanılır.

Sistemlerin Core karşılıkları `unity/Assets/_KirkDem/Runtime/Core/` altındadır. Bir sistem Core'da yoksa (Camera, Video gibi) yalnız Unity tarafında yaşar.

---

## 1. TimeRule (zaman kuralı)

**Amaç.** Her halkanın zaman kuralını tek bir veri yapısında tutmak; dinleme, hareket ve geri alma izinlerini bu kuraldan türetmek.

**Core:** `TimeRule`, `TimeRuleKind`, `TimeRuleTable`.

| Halka | Kind | Dinleme | Hareket | Geri alma | Çıkış bedeli (çağ) |
| --- | --- | --- | --- | --- | --- |
| Kasaba | `OneWay` | yok (konuşma var) | serbest | yok | — |
| Toprak | `FoldedSlow` | her an | serbest | yok | günler (çağ değişmez) |
| Su | `Tidal` | her an | serbest | gelgit: oda durumunu "ileri/geri" sardırır | aylar; perde sonunda `BirYil` |
| Nefes | `BreathHeld` | yalnız nefes tutulurken | yalnız nefes tutulurken; nefes verilince dünya ilerler, saatçi durur | yok | neredeyse hiç |
| Gölge | `DualFlow` | öbür benliğin adımları duyulur | ışık katmanı ileri, gölge katmanı geri | gölgede evet | mevsimler (çağ `BirYil` kalır) |
| Ayna | `RecordEdit` | sesler tersten | serbest | yok; her kayıt değişikliği kalıcı | yıllar + kitabeden bir harf |
| Sessizlik | `SingleMove` | **yok** | tek hamle | yok | ilk odada kırk yıl (`KirkYil`) |
| Ân | `Timeless` | yok | **yok**; yalnız niyet | yok | hiç ya da hepsi |

**Girdi.** `RingId`.
**Çıktı.** `TimeRule` (salt okunur): `CanListen(ListenContext)`, `CanMove(MoveContext)`, `AllowsRewind`, `IsSilent`, `EraAfterExit`.

**Durumlar (halka içi).**
- `Tidal` için oda bir `TideTimeline` tutar: oyuncunun yaptığı her eylem zaman çizgisine eklenir; gelgit geri geldiğinde eylemler sondan başa geri alınır, oyuncu başka yoldan yeniden yapar. Geri alma oyuncu komutu değil, odanın ritmidir (geri sarmayı oyuncu değil su yapar).
- `BreathHeld` için `BreathState { Holding, Releasing }`. `Holding` sürerken dünya saati durur, oyuncu hareket eder ve dinler; `Releasing` olunca dünya saati ilerler, oyuncu kilitlenir. Nefes süresi oda tanımında (`RoomDefinition.breathSeconds`).
- `DualFlow` için odada iki katman vardır: `LightLayer` (ileri) ve `ShadowLayer` (geri). Oyuncu tek gövdedir; fenerin aydınlattığı yerde ileri, gölgede geri akış kuralı uygulanır. "Kendinle karşılaşma" bekçi tarafından (`GuardianDefinition.kind = Self`) sağlanır, ikinci karakter kontrolcüsü yoktur.
- `RecordEdit` için oda, kasabadaki `RecordId` listesine yazar (mezar taşı, fotoğraf, kitabe). Yazma `TownRecords.Apply(edit)` ile olur; her `Apply`, `TowerState.RemoveInscriptionLetter()` çağırır.
- `SingleMove` için oda yalnız bir `Commit()` kabul eder; ikinci girdi yok sayılır. İlk odanın `Commit()`i `TownClock.ApplyFortyYearLeap()` tetikler.
- `Timeless` için hiçbir hareket girdisi işlenmez; yalnız `IntentSelector` (bkz. Stone).

**Kenar durumları.**
- Nefes halkasında oyuncu nefes tutmayı bırakıp tekrar tutmak zorundadır; süre bitiminde zorunlu `Releasing`. Zorunlu salımda yarım kalan etkileşim iptal edilir, oda durumu korunur.
- Su halkasında gelgit sırasında oyuncu konumu değişmez; yalnız oda nesneleri geri sarılır.
- Sessizlik ilk odasında `Commit()` öncesi uyarı metni yok; ipuçları yalnız Dog (reddetme), fener titremesi ve kök kuruması (Presentation). Karar oyuncunun eliyledir.

---

## 2. Listening (dinleme)

**Amaç.** Oyunun tek "yeteneği". Dinlerken saatçi kıpırdayamaz; ses kaynakları ince ışık çizgileri olarak görünür hale gelir. Çizgi yönü verir, cevabı vermez.

**Core:** `ListenContext` (hangi halka, nefes durumu, ışık/gölge katmanı). Karar `TimeRule.CanListen`.
**Gameplay:** `ListeningController`. **Presentation:** `SoundLineRenderer` (ileride).

**Girdi.** "Dinle" tuşu basılı (hold). `AudioEmitter` listesi (odadaki ses kaynakları; her birinde `pitch`, `intensity`, `isReversed`).
**Çıktı.** `ListeningSession { IsActive, Emitters[] }`. Presentation her emitter için fenerden kaynağa doğru ince çizgi çizer: kalınlık = intensity, titreşim sıklığı = pitch. Parçacık yok, çizgi.

**Halka başına yeniden tanım.**
- Toprak/Su: her an dinlenir.
- Nefes: `CanListen` yalnız `BreathState.Holding` iken true.
- Gölge: emitter listesine `SelfEcho` eklenir (öbür benliğin adımları; kaynak gölge katmanındaki konumdur).
- Ayna: emitter'lar `isReversed = true`; Presentation çizgiyi kaynaktan fenere doğru çizer, Audio ters oynatır.
- Sessizlik: `CanListen = false`. Tuş basılı tutulursa hareket kilidi yine uygulanır (saatçi dinlemeye çalışır, hiçbir şey duymaz); emitter listesi boş döner; Dog beden dili ve fener açıları devreye girer (bkz. Dog, ses-mimarisi §6).
- Ân: dinleme girdisi yok sayılır.

**Kenar durumları.** Dinleme sırasında hareket girdisi gelirse dinleme kesilir (önce bırak, sonra yürü). Oyuncu bir odada hiç dinlemezse oda yine çözülebilir; dinleme hız kazandırır, zorunluluk değildir. Altyazı seçeneği açıksa her emitter için `subtitleKey` ("su damlıyor") gösterilir.

---

## 3. Dem

**Amaç.** Her odanın sonunda alınan avuç içi ışık. Kulenin yedi katından halkanın katına takılır; takılan dem katı döndürür, kasaba zamanı o kadar düzelir.

**Core:** `TowerState.AddDem(RingId)`, `TowerState.InstallDem(RingId)`.

**Girdi.** Oda çözüldü → `RoomProgress.CollectDem()` → `TowerState.AddDem(ring)` (taşınan dem).
Kulede yuvaya dokunuldu → `InstallDem(ring)` (takılı dem).
**Çıktı.** `TowerFloor { Capacity, Carried, Installed }`. `Capacity` = halkanın oda sayısı (9,8,7,6,5,4,1). `Installed / Capacity` oranı Presentation'da çarkın dönüş hızı ve Audio'da katın notasının ses yüksekliğidir.

**Kural.** Dem yalnız kendi halkasının katına takılır; yanlış kata takma girdisi yoktur (yuva kabul etmez, hata mesajı yok). Kırk dem takılınca `TowerState.IsComplete`. Dem taşımak envanter değildir: arayüzde sayı yok, avuçtaki ışığın büyüklüğü `Carried`ı gösterir.

**Kenar.** Oyuncu demleri takmadan aşağı inebilir; `Carried` birikir. Taşınan dem kaybolmaz.

---

## 4. Secret / Sır

**Amaç.** Yedi sır, her halkadan bir, her biri yedi kasabalıdan birine ait. Tek cümle gösterilir, silinir. Kasabada söylenirse kişi kurtulur, halkanın katı kararır, taş alçalır; saklanırsa kat yanar, taş yükselir. Ortası yok.

**Core:** `SecretLedger`, `SecretChoice { Undecided, Told, Kept }`.

**Girdi.** Halka çıkışı → `Reveal(S{n})` (cümle gösterildi; durum `Undecided`). Kasabada ilgili kişiyle konuşmada "söyle" → `Tell(S{n})`. Söylenmeden bir sonraki halkaya inilirse `Keep(S{n})` — **saklama, inmeyle kesinleşir**; oyuncu sırrı söylememeyi seçmeden de "saklamış" olur. Bu, "ortası yok" kuralının teknik karşılığıdır.
**Çıktı.** `ToldCount`, `KeptCount`, `Choice(S{n})`.

**Zincirleme etkiler (tek yerden, `GameState.Apply(SecretChoice)`):**
- `Told` → `TownRecords.Resolve(townspersonId)` (dert çözülür; çağ varyantı değişir) → `TowerState.SetFloorLit(ring, false)` → `StoneState.Recalculate()`.
- `Kept` → `TowerState.SetFloorLit(ring, true)` → `StoneState.Recalculate()`.

**Kenar durumları.**
- Söylenen sır aşağı inmeyi asla engellemez.
- `Tell` yalnız sırrın sahibine yapılabilir (`SecretDefinition.ownerId`). Başkasına söyleme girdisi yok.
- Sahip kişi o çağda kasabada yoksa (Nefes halkasının ihtiyarları gibi ölmüşse) sır yine de söylenebilir: mezar taşına. Bu, Ayna halkası kayıt mekaniğiyle çakışmaz; mezar başında konuşma `Tell` sayılır.
- Kırk yıl sonrası çağda sahibi ölmüş sırların durumu değişmez; `Undecided` bir sır o noktada hâlâ varsa inişle `Kept` olur.
- S7 (Ân) özel: Ân'dan kasabaya çıkış yoktur; S7 imamın sırrıdır, odaya girerken gösterilir (`GameState.EnterAn`), kimseye söylenemez ve sayılmaz. "Çoğu" altı sır üzerinden hesaplanır (`SecretLedger.CountedSecrets = 6`, `EndingResolver.Majority = 4`); senaryo kilidi, `01-senaryo-kilidi/sirlar.md`.

---

**İlk sırrın öğretilmesi (analiz O2).** Arayüz olmadığı için söyleme eyleminin varlığı ilk sırda öğretilmek zorundadır; aksi hâlde "saklamak" varsayılan olur ve son dağılımı Dönüş/Kalış'a kayar. Kural: S1'in sahibi (çoban) Toprak'tan dönüşte kapakla meydan arasındaki tek yolun üstünde durur; oyuncu yanından geçerken taş kendiliğinden sallanır ve perdesi duyulur biçimde yükselir, köpek çobanın önünde durur, altyazı "taş çekiyor" der. "Dinle" tuşu basılıyken saatçinin dudakları kıpırdar (dinlemez, söyler). Oyuncu yine geçebilir; bu bir zorlama değil, eylemin gösterilmesidir. Sonraki sırlarda hiçbir yönlendirme yoktur.

---

## 5. Stone / Taş

**Amaç.** Tek ilerleme göstergesi. Perde saklanan sırlarla yükselir, söylenen sırlarla alçalır. Ölçek ahlaki değil müzikaldir. Kırkıncı odada taşla yapılan eylem sonu belirler.

**Core:** `StoneState`.

**Hesap.** `RawPitch = KeptCount - ToldCount` (−7..+7). `NormalizedPitch = RawPitch / 7` (−1..+1). Audio bunu frekansa, Haptics titreşim sıklığına, Presentation yüzey dalga sıklığına eşler; üçü de **aynı değeri** okur (ADR-0007, eşleme tablosu `ses-mimarisi.md §4`).

**Girdi.** `SecretLedger` değişimi → `Recalculate()`. Sallama girdisi (hareketle taş sallanır) → `IsSwinging`.
**Çıktı.** `NormalizedPitch`, `IsSwinging`. Taş sallanmazken ses vermez; kule durduğundan beri kuledeki taş sessizdir.

**Kırkıncı oda.** `IntentSelector`, `EndingResolver.Available(state)` ile açık eylemleri alır ve yalnız onları sunar. Arayüz yoktur: eylemler fiziksel jesttir (taşı kaldır = Dönüş, taşı tut = Kalış, taşı yere bırak/göm = Dağıtış). Kapalı eylemde taş elden kaymaz, yalnız ağırlaşır (Presentation) ve hiçbir metin açıklamaz.

---

## 6. Hâl ve Makam

**Hâl — amaç.** Bazı odalarda geçici, tek kullanımlık kestirme: titreşen duvardan geçmek, oda zamanının bir kez kasabayla eşitlenmesi, bekçinin bir kez görünmesi. Hiçbir oda hâle bağlı değildir.

**Core:** `RoomProgress { Solved, HalOffered, HalUsed }`. `RoomDefinition.halKind { None, WallPass, TimeMatch, GuardianSeen }`.

**Makam — amaç.** Oyuncu hâl sunulan odada uzun yolu seçtiğinde kulede bir nota asılı kalır; üçüncüde o nota çanın dizisine kalıcı eklenir. Makam sonu değiştirmez, sonun sesini değiştirir.

**Core:** `MakamTracker`.
**Girdi.** Oda çözüldü ve `HalOffered && !HalUsed` → `RegisterLongPath(ring)`.
**Çıktı.** `PendingCount` (0..2, asılı notalar), `Notes[]` (kalıcı eklenen notalar; her 3 uzun yolda bir, eklenen nota o anki halkanın temel notası). `HasMakam = Notes.Count > 0`.

**Kenar.** Hâl sunulmayan odada uzun yol sayılmaz (kestirme yoksa vazgeçiş yoktur). Hâl kullanıldıysa asılı sayaç sıfırlanmaz; yalnız artmaz. Oyun sonunda çan `Notes` dizisini çalar; boşsa tek nota.

---

## 7. TownClock / Kasaba

**Amaç.** Kasabada zaman tek yönlü, eylemle ölçülür. Dört çağ aynı haritanın dört halidir. Halka çıkışında görünür değişim.

**Core:** `TownClock`, `EraId { Bugun, BirYil, KirkYil, Terk }`.

**Vakit.** Her konuşma, sır söyleme ve dem takma `AdvanceVakit()` çağırır (+1). Vakit, Presentation'da kulenin meydana düşen gölgesinin açısıdır (kule durunca güneş saati). Gün/saat sayısı hiçbir yerde yazılmaz.

**Çağ geçişi.** `OnRingExit(ring)`:
| Çıkılan halka | Yeni çağ |
| --- | --- |
| Toprak | `Bugun` (günler geçti; yüzler aynı, ekin/kar değişir) |
| Su | `BirYil` (Kırılma 1 videosu) |
| Nefes | `BirYil` (değişim yok denecek kadar az) |
| Gölge | `BirYil` (mevsimler; aynı çağ, mevsim varyantı) |
| Ayna | `BirYil` (yıllar; kayıt değişiklikleri yansır) |
| Sessizlik | `KirkYil` (ilk odanın hamlesiyle; `ApplyFortyYearLeap()`; Kırılma 2 videosu) |
| Sessizlik (2. çıkış, R6-04 sonrası) | `Terk`: kasaba boş, neden söylenmez; 7. dönüş. Kökler videosu bu çıkıştan sonra oynar |
| Ân | çıkış yok; üç son `Terk` çağının kasabasında oynar |

Çağ yalnız ileri gider: `TrySetEra(newEra)` daha küçük bir çağ isterse yok sayar. `ApplyFortyYearLeap()` yalnız bir kez işler (`FortyYearLeapApplied`).

**Mevsim.** `BirYil` içinde Gölge çıkışı için `SeasonIndex` (0..3) tutulur; Presentation varyantı seçer. Bu bir çağ değil, aynı çağın malzeme/ışık sıcaklığıdır.

**Kenar.** Oyuncu kasabada istediği kadar dolaşabilir; vakit yalnız eylemle ilerler, dolaşmakla değil. Çağ geçişi ancak halka çıkışında olur; kasabada ne yapılırsa yapılsın çağ atlamaz.

---

## 8. Tower / Kule

**Amaç.** Yedi kat, her biri bir halkaya ait; kat yanık ya da karanlık (sır kararı), kat dönüyor ya da durmuş (dem oranı). Kitabede babanın adı; harf sayacı. Menü kulenin kendisidir.

**Core:** `TowerState`, `TowerFloor`, `Inscription`.

**Kat durumu.** `IsLit : bool?` — `null` (sır henüz kararlaşmadı), `true` (saklandı, yanıyor), `false` (söylendi, karardı). `Installed / Capacity` dönüş.
**Kitabe (karar K-16).** `Inscription { TotalLetters = 6, Remaining }` (DURSUN). Ayna'da her kayıt değişikliği bir harf siler, R5-04'te geri alma bir harf getirir (`RecordLedger`). Sessizlik ilk odasının ilk gelişinde kırk yıl geçer ve kitabe boşalır: saatçi adı unutmuştur (`GameState.CommitFortyYears`). İkinci gelişte ad duvara yazılırsa (`GameState.GiveName`) kitabe boş kalır; yazılmazsa terk çağında kitabe dolu okunur (`GameState.ExitRing`). Adın nasıl geri geldiği söylenmez. Sonlardan önce kitabe her zaman ya dolu ya boştur.
**Menü.** Kule sahnesi ana menüdür: devam = kapağa in; seçenekler = çark odası; çıkış = kapıdan çık. Metin menüsü yok (ayarlar hariç; ayarlar erişilebilirlik gereği klasik metin arayüzüdür, ADR-0007).

**Okunabilirlik.** Kat ışıkları ve kitabe meydandan görülür. Kırkıncı odaya inmeden sonların koşulu bu görünümden okunur; arayüz yok.

---

## 9. EndingResolver

**Amaç.** Kırkıncı odada taşla hangi eylemlerin açık olduğunu belirlemek.

**Core:** `EndingResolver.Available(nameGiven, keptCount, toldCount) → EndingAvailability`.

| Son | Koşul |
| --- | --- |
| Kalış (`kalis`) | her zaman |
| Dönüş (`donus`) | `nameGiven && keptCount >= 4` |
| Dağıtış (`dagitis`) | `toldCount >= 4` |

`kept + told <= 7` olduğu için Dönüş ve Dağıtış aynı anda açık olamaz; en az bir, en fazla iki eylem açıktır. Hiçbiri "doğru" değildir; çözücü sıralama ya da öneri döndürmez.

**Kenar.** Ad verilmemiş ve kept ≥ 4 ise yalnız Kalış açıktır; bu bilerek böyledir (dünya kitabı: "vermezse kule çalışır ama akrebi hiç ilerlemez" — Kalış sonunun tanımıyla örtüşür). S7 sayılmaz; `Available` yalnız S1–S6'yı görür. 3 saklı / 3 söylenmiş durumunda yalnız Kalış açıktır.

---

## 10. Dog / Köpek

**Amaç.** Yol gösterir, bazen göstermez; hiç değişmez. Değişen fenerin duvara düşürdüğü gölgesidir: halkadan halkaya biraz daha kurda benzer, kasabada yine köpek.

**Gameplay:** `DogCompanion`. **Presentation:** `DogShadowProjector`.

**Gölge.** `ShadowMorph = ringIndex / 7f` (0 kasaba, 1 Ân). Gölge mesh'i blend shape ile köpek→kurt; fener konumuna göre projeksiyon. Köpeğin kendi modeli hiç değişmez.
**Yol gösterme.** `GuideTarget` oda tanımından; köpek hedefe doğru durur, fenerin yanında bekler. `RoomDefinition.dogGuides = false` olan odalarda köpek yalnız fenerin yanında durur (kaybolmak serbest).
**Reddetme.** Sessizlik ilk odasında `Commit()` öncesi `RefuseAdvance = true`: köpek ilerlemez, geri bakar. Tek seferlik.
**Sessizlik'te kanal.** Ses yokken köpeğin bakış yönü ve gölgenin yönü ses çizgisinin yerini alır (`ses-mimarisi.md §6`).
**İpucu zamanlayıcısı (analiz O1).** Harita, görev listesi ve ipucu menüsü olmadığı için takılma tek ipucu kanalına ihtiyaç duyar; o kanal köpektir. `RoomDefinition.hintSteps[]` her odada 2–3 kademe tanımlar. Oyuncu `hintDelay` (varsayılan 150 sn, erişilebilirlik ayarıyla 60–300 sn) boyunca ilerleme sayacını (`RoomProgress.Milestone`) ilerletmezse köpek bir kademe gösterir: önce odanın anahtar nesnesine bakar, sonra yanına yürüyüp oturur, en son ses çizgisinin yönüne havlamadan burnunu uzatır. Hiçbir kademe cevabı vermez, yalnız yönü. `dogGuides = false` odalarda yalnız üçüncü kademe çalışır ve gecikme iki katıdır. Sessizlik'te zamanlayıcı kapalıdır.

---

## 11. Camera

Üçüncü şahıs, omuz üstü, 35 mm eşdeğeri. Odalarda sabit açılı diorama kadraj (`RoomDefinition.cameraRig` içinde pozisyon, hedef, FOV); kasabada serbest takip. Halka geçişinde `CameraStepIn(ringIndex)`: mesafe ve FOV bir kademe yaklaşır (sayısal değerler sanat kitabında). Ân odasında kamera yüze döner (`FaceRig`). Cinemachine kullanılır; her oda prefab'ında bir `CinemachineCamera` bulunur, halka sahnesinde bir takip kamerası.

---

## 12. Save

Tek slot. Halka çıkışında (kasabaya dönüş anı) ve oda içinde her kilometre taşında (`RoomProgress.Milestone`, karar K-13) otomatik; ölüm olmadığı için başka ara kayıt yok. Geri yükleme kasabada başlar (en son çağ, meydan). Kaydedilen: `GameState` (TownClock, SecretLedger, TowerState, MakamTracker, RoomProgress[40], Inscription, nameGiven, FortyYearLeapApplied, ayarlar). JSON (`JsonUtility` ya da System.Text.Json; Core sınıfları serileştirilebilir düz veri tutar). Manuel kayıt menüsü yok; "kapat" her zaman güvenlidir çünkü kasabada yapılan her eylem anında kaydedilir (eylemle ölçülen zaman geri gelmez — kayıt da öyle).

**Kenar.** Oda içinde çıkılırsa oyun o odanın son kilometre taşından devam eder; kilometre taşları geri alınamaz adımlardır, bu yüzden "deneyip geri alma" yolu açılmaz. Su ve Gölge odalarında zaman çizelgesi (`RoomTimeline`) kilometre taşında sıfırdan başlar.

---

## 13. Localization ve Video

**Localization.** Unity Localization; TR ve EN. Tüm oyun içi metin (sır cümleleri, kısa diyaloglar, altyazı ipuçları, ayarlar) String Table'da; Core yalnız `key` taşır. Anlatıcı sesi iki dilde ayrı kayıt; ilk açılışta "Orijinal Türkçe ses" seçeneği belirgin (açık karar, dünya kitabı).

**Video.** `VideoPlayer`, H.264 MP4 1920×1080, `StreamingAssets/Video/`. Beş video: `acilis`, `bir-yil`, `kirk-yil`, `kokler`, `son-{donus|kalis|dagitis}`. İlk izlemede atlanamaz (`GameState.VideosSeen`), sonra atlanabilir. Altyazı Localization üzerinden.

---

## 14. Accessibility

Oyunun omurgası ses olduğu için her işitsel ipucunun görsel ve dokunsal eşi vardır; bu dekor değil mekaniğin parçasıdır (ADR-0007).

- **Üçlü kanal.** `StoneState.NormalizedPitch` → Audio (frekans), Haptics (gamepad titreşim sıklığı), Presentation (taş yüzeyi dalga sıklığı, ses çizgisi kalınlığı/titreşimi). Tek kaynak, üç çıkış.
- **Altyazı.** Ses ipuçları için seçenek: her `AudioEmitter.subtitleKey` ("su damlıyor", "çark takılıyor").
- **Renk körlüğü.** Halka vurgu renkleri tek başına bilgi taşımaz; her vurgu rengine bir doku/şekil eşi vardır (sanat kitabı). Kat yanık/karanlık ayrımı parlaklıkla (renk değil) verilir.
- **Giriş.** Klavye+fare ve gamepad; "dinle" basılı tutma süresi ayarlanabilir; tek elle oynanabilir düzen.
- **Ayarlar arayüzü** oyunun "arayüz yok" ilkesinden muaftır; klasik, okunur, büyük yazı.

**Nefes tutma girişi (analiz O3).** Nefes halkası "basılı tut" girdisine dayanır; sürekli basılı tutmak motor erişilebilirlik sorunudur ve uzun odalarda (R3-07) yorar. Seçenek: `BreathInput = Hold | Toggle`. Toggle'da nefes bir basışla tutulur, ikinciyle verilir; nefesin "bitmesi" iki modda da aynı süreyle çalışır (`TimeRule.BreathHeld.maxHoldSeconds`). Ses tasarımı: nefes süresi azalırken kalp sesi değil, saatçinin kendi nefes sesi sıklaşır; görsel eşi: fener ışığı daralır; dokunsal eşi: titreşim sıklaşır.

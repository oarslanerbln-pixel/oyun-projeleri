# Kırk Oda — Teknik Mimari (Genel Bakış)

Hedef: Unity 6 LTS, URP, C#. Tek kişilik stüdyo için okunabilir, az sayıda sistemden oluşan, dünya kitabındaki kurallardan sapmayan bir yapı. Mimari ilkesi tek cümledir: **oyunun kuralları motordan bağımsız saf C#'ta yaşar; Unity yalnız gösterir, çalar ve kaydeder.**

Bu klasördeki dokümanlar:

| Dosya | İçerik |
| --- | --- |
| `sistemler.md` | Her çekirdek sistemin sözleşmesi (amaç, girdi/çıktı, durumlar, kenar durumları) |
| `veri-modeli.md` | ScriptableObject şeması ve sabit kimlik sözleşmesi |
| `oda-kiti.md` | Modüler oda kiti: prefab anatomisi, diorama değişkenleri, üretim akışı |
| `ses-mimarisi.md` | Ton sistemi, makam birikimi, taş perdesi eşlemesi, Sessizlik'te kanal devri |
| `adr/` | Mimari kararlar (ADR) |

Kod iskeleti: `kirk-oda/unity/Assets/_KirkOda/`. **Çekirdek (`KirkOda.Core`) Unity olmadan derlenir ve test edilir:** `tools/core-tests`, C# 9 (Unity 6 ile aynı), uyarılar hata sayılır; GitHub Actions her PR'da koşturur. Data ve Gameplay katmanları 17 Ekim 2026'da asgari bir UnityEngine taklidine karşı hatasız derlendi; gerçek doğrulama ilk Unity açılışındadır.

## Katmanlar ve bağımlılık yönü

Bağımlılık yalnız aşağıdan yukarıya doğru akar; üst katman alt katmanı bilir, alt katman üstü bilmez.

```
KirkOda.Presentation  (kamera, ışık çizgisi, taş yüzeyi, köpek gölgesi, altyazı)
KirkOda.Audio         (ton üretimi, makam, foley, titreşim köprüsü)
KirkOda.Gameplay      (MonoBehaviour'lar: dinleme, kor yuvası, halka çıkışı, kasaba sahneleri)
KirkOda.Data          (ScriptableObject tanımları; yalnız veri, davranış yok)
KirkOda.Core          (saf C#; UnityEngine YOK; kurallar, durum, çözücüler)
```

- **Core**, `noEngineReferences = true` ile derlenir. Zaman kuralları, taş perdesi, sır defteri, kule durumu, kasaba saati, makam sayacı ve son çözücüsü burada yaşar. Unity Test Runner'da EditMode testleri milisaniyede koşar; oyun açılmadan kural doğrulanır.
- **Data**, Core'daki enum ve id sözleşmesine referans verir; içerik üreticisinin (tasarımcı) dokunduğu tek katmandır.
- **Gameplay**, Core nesnelerini sahiplenir ve Unity olaylarını (giriş, tetikleyici, zaman) Core çağrılarına çevirir. Kural kararı Gameplay'de verilmez; Core'a sorulur.
- **Audio** ve **Presentation**, Core durumunu okur ve yansıtır. Yazmaz. Taşın perdesi, ışık çizgisinin kalınlığı ve titreşim aynı `StoneState.NormalizedPitch` değerinden türetilir; üçü birbirinden değil kaynaktan okur (ADR-0007).

## Assembly yapısı

| Assembly | Klasör | Referanslar | Not |
| --- | --- | --- | --- |
| `KirkOda.Core` | `Runtime/Core` | — | Saf C#, motor yok |
| `KirkOda.Data` | `Runtime/Data` | Core | ScriptableObject'ler |
| `KirkOda.Gameplay` | `Runtime/Gameplay` | Core, Data, Unity.InputSystem, Unity.Localization | MonoBehaviour'lar |
| `KirkOda.Audio` | `Runtime/Audio` | Core, Data | (ileride) |
| `KirkOda.Presentation` | `Runtime/Presentation` | Core, Data, URP | (ileride) |
| `KirkOda.Core.Tests` | `Tests/EditMode` | Core, NUnit | EditMode |
| `KirkOda.Editor` | `Editor` | Hepsi | Oda kiti araçları, id doğrulayıcı |

Audio, Presentation ve Editor assembly'leri dikey dilimde açılır; iskelette yalnız Core, Data, Gameplay ve Tests var.

## Sahne yapısı

Oyunun fiziksel ekseni tek bir dikey çizgidir: kule, kasaba, kırk oda. Sahneler de bu ekseni izler ve additive yüklenir.

```
Boot                 (kalıcı: GameRoot, Core durumu, kayıt, yerelleştirme, video oynatıcı)
└─ Kule              (menü = kule; 7 kat, kitabe, çan; kor takma)
└─ Kasaba            (TEK harita; 4 çağ aynı sahnenin 4 hali — ADR-0004)
└─ Magara_Halka{1..7} (halka sahnesi: kök çemberi, oda giriş kapıları, köpek, fener)
   └─ Oda prefab'ları (R1-01 … R7-01; sahneye değil halkaya additive yüklenir)
```

- **Boot** hiç boşaltılmaz. `GameRoot` tek `MonoBehaviour`dur ve Core'daki `GameState`i tutar.
- **Kule** ve **Kasaba** aynı anda yüklü olabilir (meydandan kule görünür; kat ışıkları ve kitabe meydandan okunur — bu, sonların arayüzsüz koşul okumasıdır).
- **Kasaba** sahnesi çağ değiştirmez; `EraId`ye göre `TownspersonDefinition` varyantları, malzeme sıcaklığı ve mezarlık/değirmen durumları aynı sahnede değiştirilir. Çağlar yalnız ileri gider.
- **Halka** sahneleri odaları additive yükler; aynı anda en fazla bir oda açıktır. Gölge halkasında "aynı anda iki yerde olmak" iki ayrı oda değil, tek odanın iki ışık katmanıdır (bkz. `sistemler.md`, TimeRule → DualFlow).
- Odalar `RoomDefinition` + modüler prefab kitiyle kurulur (`oda-kiti.md`).

## Veri akışı (bir halka döngüsü)

```
Giriş → Gameplay (ListeningController)        "dinle" tutuldu
      → Core.TimeRule.CanListen(ring, state)  halka kuralı izin veriyor mu
      → Presentation (SoundLineRenderer)      ses kaynağı → ince ışık çizgisi (yön, cevap değil)
Oda çözüldü → Core.RoomProgress.Solve()       hâl kullanıldı mı kaydedilir
            → Core.MakamTracker.RegisterPath() uzun yolsa sayaç
            → Kor alınır (Core.TowerState.AddEmber)
Halka bitti → Gameplay (RingExitGate)
            → Core.SecretLedger.Reveal(S{n})  tek cümle gösterilir, silinir
            → Core.TownClock.OnRingExit(ring) çağ geçişi, vakit
            → Save                             tek slot, otomatik
Kasaba      → her eylem Core.TownClock.AdvanceVakit()
            → sır söylenirse SecretLedger.Tell → TowerState.FloorDarkens → StoneState değişir
            → kor takılırsa TowerState.FloorTurns → kasaba zamanı düzelir
40. oda     → Core.EndingResolver.Available(state) → yalnız açık eylemler sunulur
```

## Olmayanlar (mimaride de yok)

Savaş, ölüm ekranı, envanter, harita, görev listesi, başarım bildirimi. Bunlar için sistem, veri ya da UI katmanı tasarlanmaz. Steam başarımları yalnız bir son ulaşıldığında `GameRoot` üzerinden arka planda gönderilir; oyun içinde hiçbir geri bildirim yoktur (dünya kitabı, Açık kararlar → Başarımlar).

## Ortam ve araç notu

Bu depo bir Unity projesi değil, Unity projesine taşınacak `Assets/_KirkOda` klasörüdür. Unity 6 LTS'de yeni URP projesi açılır, `_KirkOda` klasörü `Assets/` altına kopyalanır, Input System ve Localization paketleri eklenir; Test Runner → EditMode → `KirkOda.Core.Tests` çalıştırılır.

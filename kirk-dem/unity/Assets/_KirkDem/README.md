# `_KirkDem` — Unity kod iskeleti

> **Durum: derlenmedi.** Bu klasör Unity ve dotnet bulunmayan bir ortamda yazıldı. İlk Unity açılışında derleme hataları beklenir ve orada düzeltilir; mimari ve sözleşmeler bağlayıcı, satırlar değil.

## Klasör yapısı

```
_KirkDem/
├─ Runtime/
│  ├─ Core/        KirkDem.Core      saf C#, UnityEngine YOK (noEngineReferences)
│  │  Enums, RingCatalog, TimeRule, SecretLedger, StoneState (+PitchMap),
│  │  TowerState (+Inscription), TownClock, MakamTracker, EndingResolver,
│  │  RoomProgress, GameState
│  ├─ Data/        KirkDem.Data      ScriptableObject tanımları (veri-modeli.md)
│  └─ Gameplay/    KirkDem.Gameplay  MonoBehaviour köprüleri (GameRoot, ListeningController,
│                                    StoneView, DemSocket, RingExitGate)
└─ Tests/
   └─ EditMode/    KirkDem.Core.Tests  NUnit; Core saf C# olduğu için anında koşar
```

Dokümanlar: `kirk-dem/docs/03-mimari/` (README, sistemler, veri-modeli, oda-kiti, ses-mimarisi, adr/).

## İlk Unity açılışında yapılacaklar

1. Unity 6 LTS'de **URP** şablonuyla yeni proje aç; `_KirkDem` klasörünü `Assets/` altına kopyala.
2. Package Manager: **Input System**, **Localization**, **Cinemachine**, **Test Framework** (varsayılan gelir).
3. Derleme hatalarını gider. Beklenen noktalar:
   - `KirkDem.Data.asmdef` → `Unity.RenderPipelines.Core.Runtime` referansı (VolumeProfile için); URP paketi yoksa `EraDefinition.lightingProfile`i geçici olarak yoruma al.
   - `Renderer.material` kullanımı StoneView'da; prefab'ta materyal örneği istenmiyorsa `MaterialPropertyBlock`a çevir.
4. **Window → General → Test Runner → EditMode → Run All.** `KirkDem.Core.Tests` beş sınıf, ~20 test: EndingResolver, StoneState/PitchMap, TownClock, MakamTracker, RingCatalog. Hepsi geçmeden Gameplay'e dokunma.
5. `GameRoot.inscriptionLetters` = 6 (DURSUN). Ad hassasiyet okumasından sonra değişirse burayı ve `diyalog-ilkeleri.md` dosyasını birlikte güncelle.
6. Oda kiti için Editor araçlarını (`Editor/` assembly: Room Scaffold, Id Validator, Ring Overview) dikey dilimde yaz; `oda-kiti.md §6`.

## Kurallar (kod incelemesinde kontrol edilir)

- **Core'da UnityEngine yok.** `using UnityEngine;` görülürse PR reddedilir.
- **Kural kararı Core'da.** Gameplay bir `if` ile oyun kuralı uyguluyorsa Core'a taşınır.
- **Tek kaynak üç kanal.** Perde, titreşim, dalga: yalnız `PitchMap` (ADR-0007). Her `AudioEmitterDef`in `subtitleKey`i dolu olmalı.
- **Kimlikler `RingCatalog`'tan.** Elle yazılmış `"R3-04"` yalnız veri dosyalarında; kodda `RingCatalog.RoomId`.
- **Oyun içinde geçmeyen kavram adları kodda da yok.** `FoldedSlow`, `BreathHeld` gibi teknik adlar kullanılır.
- **Olmayanlar yok.** Envanter, harita, görev listesi, ölüm, başarım bildirimi için sınıf açılmaz.

## Bilinçli eksikler

Audio, Presentation ve Editor assembly'leri; SaveSystem; SceneFlow; PlayerMotor; DogCompanion; HapticBridge; SoundLineRenderer. Hepsi `sistemler.md`de sözleşmeyle tanımlı, kodu dikey dilimde yazılır.

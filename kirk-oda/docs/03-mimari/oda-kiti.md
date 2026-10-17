# Modüler Oda Kiti

Kırk oda, yedi halka, 16–18 haftada. Bu ancak her odanın sıfırdan değil, bir kitten kurulmasıyla mümkündür. Kit; prefab modülleri, oda prefab anatomisi, diorama değişken sistemi ve bir üretim ritüelinden oluşur.

## 1. Oda prefab anatomisi

Her oda tek bir prefab'tır: `Room_R{n}-{nn}.prefab`. Kök nesnede `RoomRoot` (Gameplay) ve `RoomDefinition` referansı. Alt yapı sabittir; her odada aynı adlarla bulunur:

```
Room_R2-05
├─ Geometry/              (kitten modüller; yalnız statik mesh)
│  ├─ Floor_*             zemin modülleri (2×2 m ızgara)
│  ├─ Wall_*              duvar modülleri (2 m, 4 m; köşe; kemer)
│  ├─ Root_*              kök modülleri (Hayat Ağacı'nın kökleri; duvardan geçer, her halkada kalınlaşır)
│  └─ Diorama/            odanın öznesi (bkz. §3)
├─ Points/                (boş transform'lar; sistemler bunlara bağlanır)
│  ├─ LanternPoint        fenerin durağı; tek dinamik ışık buraya bağlanır
│  ├─ DogPoint            köpek fenerin yanında burada bekler
│  ├─ GuardianPoint       bekçi
│  ├─ EmberSocket           kor burada belirir (çözüm sonrası)
│  ├─ PlayerSpawn         giriş
│  └─ ExitGate            halka sahnesine dönüş tetikleyicisi
├─ Emitters/              (AudioEmitter; RoomDefinition.emitters ile eşleşir)
│  ├─ Emitter_drip
│  └─ Emitter_gear
├─ CameraRig/             CinemachineCamera (sabit diorama kadraj; RoomDefinition.cameraRig)
├─ Lighting/              Light Probe Group, Reflection Probe; baked yalnız
└─ Hal/                   (yalnız halKind != None) WallPass titreşen duvar, TimeMatch tetikleyici, GuardianSeen nokta
```

Kurallar:
- Oda prefab'ında **hiç dinamik ışık yok**; fener oyuncuyla gelir (ADR-0003).
- Oda prefab'ında script yalnız `RoomRoot`, `AudioEmitter`, `HalTrigger`, `EmberSocket`, `ExitGate`. Bulmaca davranışı `RoomDefinition.timeRuleKind` ve halka kuralından türetilir; odaya özel script yazılması istisnadır ve ADR gerektirir.
- Her nokta adı sabittir; `RoomRoot` eksik noktayı Editor'de hata olarak işaretler.

## 2. Modül kitabı

Blender'da elle modellenir, Poly Haven CC0 dokularıyla (taş, ahşap, toprak, kalay). Tüm modüller 2 m ızgaraya oturur, pivot sol-alt-arka köşede.

| Modül ailesi | Parçalar | Varyant |
| --- | --- | --- |
| Floor | düz, çatlak, su birikintili, kök çıkıntılı | halka başına doku seti |
| Wall | 2 m, 4 m, köşe iç, köşe dış, kemer, niş | halka başına doku seti |
| Root | ince, orta, kalın; düğüm; duvardan geçiş | kalınlık halkayla artar; Sessizlik'te kuru varyant |
| Ceiling | düz, kubbeli, açık (yukarıdan kök) | |
| Prop | fener askısı, taş kapak, çark parçası, su kanalı, tohum yuvası, ayna çerçevesi, mezar taşı | halka öznesine göre |

Halka başına doku seti: aynı mesh, halkanın vurgu rengine çekilmiş malzeme (`MaterialVariant`). Mesh sayısı sabit kalır, malzeme sayısı 7 kat artar; bu bilinçli ve ucuzdur.

## 3. Diorama değişken sistemi

Dış halkalarda (Toprak, Su, Nefes) odalar **aynı dioramanın tek bir değişkenini** değiştirir. Diorama, odanın öznesidir: bir tohum yatağı, bir çeşme, bir ocak başı. Değişken odayı yeni oda yapar.

`RoomDefinition.dioramaBase` ortak prefab; `RoomDefinition.dioramaVariable` tek kayıt:

```
DioramaVariable {
  kind: Material | Fill | Position | Count | Season | State
  target: string      (diorama içindeki alt nesne adı)
  value: string/float (ör. Fill=0.7, Season=Kış, State=Kuru)
}
```

Örnek, Toprak halkası (bekleyerek çözme; tema: tohum, erime, çökme):
| Oda | Diorama | Değişken |
| --- | --- | --- |
| R1-01 | tohum yatağı | Fill: toprak nemi |
| R1-02 | tohum yatağı | Season: kar örtüsü |
| R1-03 | tohum yatağı | State: taş kapak çökmüş |
| R1-04 | çeşme | Fill: buz |
| … | … | … |

İç halkalarda (Gölge, Ayna, Sessizlik, Ân) odalar az ve uzun; diorama paylaşılmaz, her oda kendi dioramasını kurar ama **kit modülleri yine kullanılır**. Ân odası kitten yalnız zemin ve kök alır; geri kalanı karanlıktır.

Bir diorama en fazla üç odada tekrar eder; dördüncüde yeni diorama. Toprak'ta 9 oda = 3 diorama × 3 değişken. Toprak 7 odaya inerse (üretim planı seçeneği) 3 + 2 + 2.

## 4. Üretim ritüeli (halka başına 2–2,5 hafta)

| Gün | İş | Çıktı |
| --- | --- | --- |
| 1 | Halkanın `RingDefinition` ve `AudioRingProfile`i kurulur; senaryo kilidindeki tek cümleler `RoomDefinition.oneLiner`a girilir | 9/8/7… boş RoomDefinition |
| 2–3 | Halka doku seti (MaterialVariant) ve kök kalınlığı; halka sahnesi `Magara_Halka{n}` greybox | Yürünebilir halka |
| 4–6 | Diorama(lar) Blender'da; kit modüllerinden odalar greybox; CameraRig kadrajları | Tüm odalar greybox, kadrajlı |
| 7–8 | Emitter yerleşimi, hâl odaları, kor yuvaları; `TimeRule` davranışı oynanır | Oynanabilir halka (çirkin) |
| 9–11 | Malzeme, prop, kök detayı; Light Probe + baked lighting | Görsel hedefte |
| 12 | Foley ve arpej eşlemesi; altyazı anahtarları | Duyulur |
| 13–14 | Kendi oynatması, kenar durumları, kayıt/geri yükleme halkadan | Kilitli halka |
| (15–17) | Yedek: iç halkalarda uzun odalar için | |

Kural: bir sonraki halkaya önceki halka "kilitli" olmadan geçilmez; ama cila (polish) Oynatma testi 2'ye bırakılır.

## 5. İsimlendirme

| Varlık | Biçim | Örnek |
| --- | --- | --- |
| Oda prefab | `Room_R{n}-{nn}` | `Room_R3-04` |
| Diorama prefab | `Dio_{halka}_{özne}` | `Dio_toprak_tohum` |
| Modül mesh | `M_{aile}_{parça}_{boyut}` | `M_Wall_Arch_4m` |
| Malzeme varyantı | `MAT_{aile}_{halka}` | `MAT_Stone_golge` |
| Emitter | `Emitter_{ses}` | `Emitter_drip` |
| Halka sahnesi | `Magara_Halka{n}` | `Magara_Halka5` |
| Kasabalı prefab | `NPC_{id}_{çağ}` | `NPC_coban_kirk-yil` |
| Altyazı anahtarı | `room.{odaId}.subtitle.{ses}` | `room.R2-05.subtitle.drip` |

## 6. Editor araçları (dikey dilimde yazılacak)

- **Room Scaffold**: `RoomDefinition` seçilir → boş oda prefab'ı tüm `Points/` ile oluşturulur.
- **Id Validator**: tüm SO'ları `veri-modeli.md` kurallarına göre tarar.
- **Ring Overview**: halkanın odalarını, hâl/emitter/kor durumlarını tek tabloda gösterir.

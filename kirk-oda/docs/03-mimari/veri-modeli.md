# Veri Modeli — ScriptableObject Şeması ve Kimlik Sözleşmesi

Tüm içerik `KirkOda.Data` assembly'sindeki ScriptableObject'lerdedir. Core yalnız kimlik (string id) ve enum taşır; Unity nesnesine referans vermez. Kimlikler sabittir ve kodda, veride, sahne adlarında, yerelleştirme anahtarlarında aynı yazılır.

## Kimlik sözleşmesi

| Tür | Değerler | Not |
| --- | --- | --- |
| Halka | `toprak`, `su`, `nefes`, `golge`, `ayna`, `sessizlik`, `an` | Sıra 1..7; oda sayıları 9, 8, 7, 6, 5, 4, 1 |
| Oda | `R{halkaNo}-{odaNo:00}` | `R1-01` … `R1-09`, `R2-01` … `R2-08`, …, `R7-01` (= kırkıncı oda) |
| Kasabalı | `degirmenci`, `degirmenci-kizi`, `kahveci`, `imam`, `ebe`, `coban`, `muhtar` | 7 kişi; geri kalanı fon |
| Çağ | `bugun`, `bir-yil`, `kirk-yil`, `terk` | Yalnız ileri |
| Sır | `S1` … `S7` | Numara = halka numarası |
| Son | `donus`, `kalis`, `dagitis` | |
| Video | `acilis`, `bir-yil`, `kirk-yil`, `kokler`, `son-donus`, `son-kalis`, `son-dagitis` | StreamingAssets/Video/{id}.mp4 |
| Yerelleştirme anahtarı | `{tür}.{id}.{alan}` | örn. `secret.S3.text`, `room.R2-05.subtitle.drip` |

Core'daki `RingCatalog` bu sözleşmenin tek kaynağıdır (halka sırası, oda sayıları, id biçimi). Editor'de bir doğrulayıcı (ileride) tüm SO'ların bu kurallara uyduğunu kontrol eder.

## Şema

Alanlar `camelCase`; Unity `[SerializeField]`. Tüm metinler Localization anahtarıdır, ham metin değil.

### RingDefinition
| Alan | Tür | Açıklama |
| --- | --- | --- |
| id | string | `toprak` … `an` |
| ring | RingId (Core enum) | 1..7 |
| roomCount | int | 9,8,7,6,5,4,1 (RingCatalog ile çapraz doğrulanır) |
| timeRuleKind | TimeRuleKind | Core tablosuyla aynı; SO yalnız gösterim için tekrarlar |
| guardianKind | GuardianKind | Animal, Child, Elder, Self, Reflection, None |
| accentColor | Color | Sanat kitabı: kahve, yeşil, süt beyazı, mor, gümüş, yok, beyaz |
| audioProfile | AudioRingProfile | temel nota + arpej |
| rooms | RoomDefinition[] | sıralı |
| secret | SecretDefinition | S{n} |
| cameraStepIn | float | halka geçişinde yaklaşma kademesi (sanat kitabından) |
| sceneName | string | `Magara_Halka{n}` |

### RoomDefinition
| Alan | Tür | Açıklama |
| --- | --- | --- |
| id | string | `R{n}-{nn}` |
| ring | RingId | |
| index | int | 1..roomCount |
| guardian | GuardianDefinition | |
| oneLiner | LocalizedString | senaryo kilidindeki tek cümle (tasarım notu; oyunda gösterilmez) |
| dioramaBase | GameObject (prefab) | dış halkalarda ortak diorama |
| dioramaVariable | DioramaVariable | tek değişken (bkz. oda-kiti) |
| modules | RoomModuleSet | zemin/duvar/kök modülleri |
| emitters | AudioEmitterDef[] | ses kaynakları: localKey, pitch, intensity, subtitleKey |
| halKind | HalKind | None, WallPass, TimeMatch, GuardianSeen |
| dogGuides | bool | köpek yol gösterir mi |
| breathSeconds | float | yalnız Nefes |
| recordEdits | RecordEditDef[] | yalnız Ayna: hangi kasaba kaydını değiştirir |
| cameraRig | CameraRigDef | pozisyon, hedef, FOV |
| estimatedMinutes | int | Kilit sekmesindeki süre; Toprak ve Su'da en çok 3 (K-04) |
| hintSteps | HintStepDef[] | 2–3 kademe: `LookAt`, `SitBeside`, `PointNose` + hedef nesne; Sessizlik'te boş |
| hintDelaySeconds | float | varsayılan 150; oyuncu ayarıyla 60–300 |
| milestoneCount | int | oda içi geri alınamaz adım sayısı (K-13) |

### GuardianDefinition
| Alan | Tür | Açıklama |
| --- | --- | --- |
| id | string | `G-R{n}-{nn}` |
| kind | GuardianKind | |
| wantsKind | WantKind | Item (Toprak), Habit (Su), Anger (Nefes), Fear (Gölge), Memory (Ayna), Name (Sessizlik ilk oda), Silence, Nothing |
| wantedItemId | string | yalnız Item; kasabadan getirilmesi gereken eşya |
| prefab | GameObject | hayvan/çocuk/ihtiyar/benlik/yansıma |
| voiceOwnerId | string | Gölge'deki yaşlı saatçi ve baba aynı oyuncu (iç not; veride yalnız oyuncu id'si) |

### SecretDefinition
| Alan | Tür | Açıklama |
| --- | --- | --- |
| id | string | `S1` … `S7` |
| ring | RingId | |
| ownerId | string | kasabalı id |
| text | LocalizedString | tek cümle; gösterilir, silinir |
| resolvesTroubleId | string | söylenirse çözülen dert (TownspersonDefinition.trouble) |
| displaySeconds | float | ekranda kalma süresi |

### TownspersonDefinition
| Alan | Tür | Açıklama |
| --- | --- | --- |
| id | string | 7 kişi |
| troubleId | string | derdi (imam için boş) |
| eras | EraVariant[4] | çağ başına: prefab varyantı, konum, konuşma tablosu anahtarı, mevcut mu (ölü/yok), mezar taşı recordId |
| resolvedVariant | EraVariant | derdi çözülmüş hali (çağa göre override) |
| voiceOwnerId | string | |

`EraVariant { era: EraId, present: bool, prefab, spawnPoint: string, dialogueTable: string, graveRecordId: string }`

### EraDefinition
| Alan | Tür | Açıklama |
| --- | --- | --- |
| id | string | `bugun` … `terk` |
| era | EraId | |
| colorTemperature | float | sanat kitabı: altın (yalnız Su diorama), nötr, solgun, gri-mavi |
| lightingProfile | VolumeProfile | URP volume |
| seasonVariants | SeasonVariant[4] | yalnız `bir-yil` |
| townStateOverrides | RecordId → state | mezarlık boyutu, değirmen çalışır/durmuş, kapak örtülü mü |
| videoOnEnter | string | `bir-yil`, `kirk-yil` ya da boş |

### TowerFloorDefinition
| Alan | Tür | Açıklama |
| --- | --- | --- |
| ring | RingId | kat = halka |
| capacity | int | halkanın oda sayısı |
| socketTransform | string | kule sahnesindeki yuva adı |
| gearPrefab | GameObject | |
| baseNote | Note | AudioRingProfile ile aynı |

### EndingDefinition
| Alan | Tür | Açıklama |
| --- | --- | --- |
| id | string | `donus`, `kalis`, `dagitis` |
| ending | EndingId | |
| gesture | StoneGesture | Lift, Hold, Bury |
| videoId | string | `son-{id}` |
| finalEra | EraId | Üç son da `terk` (Sessizlik'in ikinci çıkışından sonra kasaba zaten terk edilmiştir) |
| finalTownState | RecordId → state | kapak kapalı/açık, kule sökük vb. |

### AudioRingProfile
| Alan | Tür | Açıklama |
| --- | --- | --- |
| ring | RingId | |
| baseNote | Note | halkanın temel notası (ses-mimarisi §1) |
| arpeggio | Note[] | odalar bu dizinin adımları |
| timbre | TimbreDef | harmonik ağırlıkları |
| silent | bool | yalnız Sessizlik: true |

## Kayıt verisi (GameState)

Core'daki `GameState` düz, serileştirilebilir veridir; SO'lara referans vermez, yalnız id ve sayılar tutar:

```
GameState {
  era, vakit, seasonIndex, fortyYearLeapApplied,
  secrets: { S1..S7 → Undecided|Told|Kept },   // S7 gösterilir, sayılmaz
  floors:  { ring → carried, installed, isLit? },
  inscriptionRemaining, nameGiven, silenceExits,
  recordEdits: [recordId…],                    // Ayna (RecordLedger)
  makam: { pendingCount, notes[] },
  rooms:  { R.. → solved, halOffered, halUsed, emberCollected, milestone },
  videosSeen[], settings
}
```

## Doğrulama kuralları (Editor, ileride)

- Her RingDefinition.roomCount == RingCatalog.RoomCount(ring).
- Her RoomDefinition.id biçime uyar ve benzersizdir.
- Her SecretDefinition.ownerId 7 kasabalıdan biridir; S1..S7 her biri bir kez.
- İmam dışındaki altı kasabalının troubleId'si, tam bir SecretDefinition tarafından çözülür.
- Sessizlik halkasının AudioRingProfile.silent == true.
- Ân halkasında tek oda, guardianKind == None.

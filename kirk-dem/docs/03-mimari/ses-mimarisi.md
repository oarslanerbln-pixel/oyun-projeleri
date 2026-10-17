# Ses Mimarisi

Müzik yok, ton var. Her halkanın bir temel notası, her odanın o notanın bir arpej adımı vardır. Kuleye dem takıldıkça kasabada bu notalar birikir; oyun sonunda "müzik" oyuncunun kurduğu kulenin sesidir. Anlatıcı sesi yalnız sinematiklerde.

## 1. Halka notaları

Yedi halka, yedi nota; dıştan içe yükselmez, **daralır**: aralıklar küçülür, Sessizlik'te nota yok, Ân'da tek saf ton. Aşağıdaki dizi bir öneridir; sanat ve ses yönetimi makam bilgisiyle son halini verir (üretim planı adım 7). Kodda nota, frekans (Hz) ve harmonik ağırlık olarak tutulur; makam adı veride geçmez.

| Halka | Temel nota (öneri) | Hz (A4 = 440) | Tını |
| --- | --- | --- | --- |
| Toprak | D3 | 146.8 | kalın, ahşap, yavaş saldırı |
| Su | F3 | 174.6 | cam, uzun kuyruk |
| Nefes | G3 | 196.0 | nefesli, süt beyazı |
| Gölge | A♭3 | 207.7 | iki ses, biri ters zarf |
| Ayna | A3 | 220.0 | metalik, ters çalınan |
| Sessizlik | — | — | **yok** |
| Ân | A4 | 440.0 | saf sinüs, tek |

Arpej: halkanın temel notası üzerinde, oda sayısı kadar adım (`AudioRingProfile.arpeggio`). Oda çözülünce o adım kuleye "taşınır".

## 2. Kulede biriken makam

Kule sahnesinde her kat bir `FloorVoice`dir. `Installed / Capacity` oranı o katın sesinin yüksekliğini ve kaç arpej adımının çaldığını belirler. Yedi kat birlikte, kasabadan duyulan tonu oluşturur. Kat karardıysa (sır söylendi) katın sesi alçak oktava iner; yandıysa (saklandı) üst oktavda kalır. Taşın perdesiyle aynı yönde.

`MakamTracker.Notes[]` çanın dizisine eklenir: her uzun yol üçlüsü bir nota. Oyun sonunda çan `Notes` dizisini çalar; boşsa tek nota. Bu dizi makamın kendisidir; oyun açıklamaz, kulede duyulur.

## 3. Ton üretimi

İki yol, ikisi de desteklenir:

- **Prosedürel** (`ProceduralToneSource`): `OnAudioFilterRead` ile sinüs + harmonikler (`TimbreDef.harmonics[]`), zarf (ADSR). Avantaj: perde sürekli değişebilir (taş). Kullanım: taş, ses çizgileri, Ân.
- **Önceden render** (`AudioClip`): Audacity'de üretilen tonlar; halka katları, arpej adımları. Avantaj: tını kontrolü, CPU ucuz. Perde değişimi `AudioSource.pitch` ile sınırlı.

Foley gerçek kayıt (taş, ahşap, su, nefes); `AudioEmitter` üzerinde `AudioClip`. Emitter'ın `pitch` ve `intensity` değerleri hem ses hem ışık çizgisi için ortak kaynaktır.

## 4. Taş perdesi eşlemesi

`StoneState.NormalizedPitch` ∈ [−1, +1] tek kaynak. Üç çıkış aynı tabloyu okur:

| NormalizedPitch | Ses (Hz) | Titreşim (gamepad, darbe/sn) | Yüzey dalga sıklığı (çizgi/cm) |
| --- | --- | --- | --- |
| −1.0 (7 söylendi) | 110 | 1 | 0.5 |
| −0.5 | 155 | 2 | 1.0 |
| 0.0 | 220 | 3 | 2.0 |
| +0.5 | 311 | 5 | 3.5 |
| +1.0 (7 saklandı) | 440 | 8 | 6.0 |

Eşleme üstel (oktav başına ×2) ve tek fonksiyondadır: `PitchMap.Frequency(p) = 220 · 2^p`, `PitchMap.HapticRate(p)`, `PitchMap.RippleDensity(p)`. Audio, Haptics ve Presentation bu fonksiyonu çağırır; kendi tablolarını tutmaz (ADR-0007). Ses çizgisinin kalınlığı ve titreşim sıklığı emitter perdesini aynı fonksiyonla izler.

Taş yalnız sallanırken ses verir (`IsSwinging`). Sallanma yürüyüşten gelir; duran saatçinin taşı susar. Dinlerken saatçi durur: dinleme anında taş sessizdir, bu kasıtlıdır (dinlemek için taşı susturmak gerekir).

## 5. Ayna halkası

Emitter'lar `isReversed = true`: `AudioClip` ters oynatılır (ters render edilmiş kopya; `pitch = -1` yerine, çünkü ters pitch tüm platformlarda güvenilir değil). Ses çizgisi kaynaktan fenere doğru çizilir. Halka tonu ters zarflı (önce kuyruk, sonra saldırı).

## 6. Sessizlik: kanal devri

Sessizlik halkasında ses kanalı **tamamen** kapanır: `AudioRingProfile.silent = true`; `AudioMixer` ana grubu −80 dB'ye iner (foley dahil; adımlar dahil). Oyuncu hiçbir şey duymaz.

Ses çizgisinin işlevi iki kanala devredilir:
- **Köpek beden dili ve gölgesi.** `DogCompanion.GuideTarget` yönüne bakış; gölgenin duvardaki yönü. Fener açısı (oyuncu feneri çevirebilir) gölgenin uzunluğunu değiştirir: doğru yönde gölge uzar.
- **Fener ışık açıları.** `LanternPoint`'ten çıkan ışığın duvara düştüğü yerde kökler çok hafif parlar (emissive, çok düşük); yanlış yönde parlamaz.
- **Dokunsal.** Gamepad'de taş yine titrer (NormalizedPitch); doğru yöne dönüldüğünde kısa tek darbe (`HapticCue.Direction`).

Oyuncu körlemesine tahmine zorlanmaz; üç kanal da aynı yönü söyler. Altyazı seçeneği açıksa Sessizlik'te altyazı da yoktur (sessizliğin kendisi altyazısız kalır; ayarlarda açıkça yazılır).

Ân odasında ses geri gelir: tek saf ton, taşın perdesinde.

## 7. Mixer yapısı

```
Master
├─ Tone        (halka katları, arpej, taş, Ân tonu)
├─ Foley       (emitter clip'leri, adımlar, kapak, çark)
├─ Narration   (yalnız video; VideoPlayer çıkışı)
└─ UI          (yalnız ayarlar menüsü)
```

Sessizlik: `Tone` ve `Foley` −80 dB. Kasabaya dönüşte normale. Snapshot geçişleri 2 sn.

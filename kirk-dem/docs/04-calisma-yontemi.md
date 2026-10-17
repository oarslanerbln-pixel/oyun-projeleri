# Çalışma Yöntemi — Strateji, Model ve Eklenti Yönlendirmesi

Tek kişilik stüdyo artı Claude. Amaç: görsel olarak çok kaliteli, anlatı olarak çok sağlam bir oyunu 10 ayda, sürekli test etmeden ama doğru noktalarda doğrulayarak bitirmek. Yöntem üç şeye dayanır: **kilitli dokümanlar**, **az ama kesin doğrulama kapısı**, **işe göre model**.

## 1. Omurga: dokümandan koda tek yön

```
00 Dünya kitabı  →  01 Senaryo kilidi  →  02 Sanat kitabı  →  03 Mimari / veri modeli  →  Unity
```

Bir alt katmandaki değişiklik üst katmana aykırıysa üst katman değişmez, alt katman düzeltilir. Üst katmanı değiştirmek bir "karar" sayılır ve dünya kitabının "Açık kararlar" listesinden geçer.

## 2. Doğrulama kapıları (sürekli test yok, üç kapı var)

| Kapı | Ne zaman | Ne doğrulanır | Ölçüt | Model |
| --- | --- | --- | --- | --- |
| K0 Senaryo kilidi | Bu PR | 40 oda × 7 sır × 4 çağ birbirini tutuyor mu; söylenmeyecekler ihlali var mı | Çapraz okuma listesi (aşağıda) temiz | Fable 5.1 tek okuma |
| K1 Dikey dilim | 10 Ocak 2027 (8 hafta) | Dinleme, dem, sır, taş; Toprak'ın 3 odası tam kalitede **ve** Su, Gölge, Ayna'dan birer gri kutu oda (ADR 0009: `RoomTimeline`, `InputRecorder`, `RecordEdit`) | 5 oyuncu: dinleme anlaşılıyor, ilk sır (S1) en az 4 oyuncu tarafından söylenebildi ya da bilinçli saklandı; üç gri kutu çalışıyor | Opus 5.5 |
| K2 Üçüncü halka | Nefes bitince (Nisan 2027 sonu) | Oda kiti verimi (halka başına ≤ 2,5 hafta), bedel eğrisi, çukur hissi | Kendi oynayışı + 2 oyuncu | Opus 5.5 |
| K3 Tam oyun | Kasım 2027 | Bitirme oranı, son dağılımı, kaybolma noktaları | 10 oyuncu, ≥ 3 yabancı | Opus 5.5 |

Aralarda test yok; EditMode testleri yalnız `KirkDem.Core` değiştiğinde koşar (saniyeler sürer). Oyun içi hata ayıklama ihtiyaç oldukça yapılır, takvime bağlanmaz.

**Takvim (karar K-02).** 14 ay üretim, çıkış Ocak 2028 sonu, demo Haziran 2027 Steam Next Fest. Dönem dönem iskelet `06-karar-kaydi.md` içindedir. K2'de ölçülen halka hızı 2 haftanın altındaysa çıkış Kasım 2027'ye çekilir.

**Sürekli güvence.** Tek otomatik test çekirdektir: `tools/core-tests` her PR'da GitHub Actions'ta koşar, saniyeler sürer. Yerelde: `dotnet test kirk-dem/tools/core-tests`.

**K0 çapraz okuma listesi:** her sırrın söylenebileceği çağda sahibi hayatta mı · her Toprak eşyasının vereni bugün çağında kasabada mı · Ayna değişiklikleri kitabe harf sayısını (6) aşmıyor mu · her hâl kestirmesi olmadan oda çözülüyor mu · hiçbir bekçi/sır/mısra bir kavramın adını söylüyor mu · üç sonun koşulları `EndingResolver` ile birebir mi.

## 3. Haftalık ritim

- **Pazartesi (90 dk):** haftanın tek hedefi; hangi dokümana dokunulacak; hangi model.
- **Salı–Perşembe:** üretim. Claude Code oturumu, aşağıdaki modelle. Oturum başında `CLAUDE.md` otomatik okunur; ek bağlam olarak yalnız o haftanın dokümanı verilir.
- **Cuma (60 dk):** oynanabilir ya da izlenebilir çıktı kaydı (OBS, 2–3 dk), `docs/` güncellemesi, commit, PR. Karar günlüğüne (dünya kitabı "Açık kararlar") bir satır.
- Ayda bir: dünya kitabına karşı tutarlılık okuması (Fable 5.1, tek oturum).

## 4. Model yönlendirmesi

Bütün işler Claude Code içinden yürür; model `/model` ile seçilir. Varsayılan Opus 5.5'tir; aşağıdaki tablo ne zaman yukarı ya da aşağı kayılacağını söyler. Fiyatlar milyon token başına giriş/çıkış (Anthropic API, Ekim 2026): Fable 5.1 $10/$50 · Opus 5.5 $4/$20 · Sonnet 5.5 $2/$10 · Haiku 5.5 $0,10/$0,50.

| İş | Model | Effort | Neden |
| --- | --- | --- | --- |
| Senaryo kilidi çapraz okuması, üç sonun tutarlılığı, hassasiyet ön-okuması, dünya kitabı değişikliği | **Fable 5.1** | high | 40 oda × 7 sır × 4 çağ aynı anda akılda tutulmalı; hata burada en pahalı. Ayda bir oturum yeter. |
| Zaman kurallarının birbirine girdiği hatalar (Su geri sarma + kayıt, Gölge çift akış) | **Fable 5.1** | xhigh | Nadir, zor; Opus takılırsa yükselt. |
| Oda tasarımı, diyalog, mısra, karakter sahneleri | **Opus 5.5** | high | Ton ve bağlam; varsayılan. |
| Mimari, ADR, sistem sözleşmesi, C# çekirdek, kod incelemesi (PR) | **Opus 5.5** | xhigh | Kodda doğruluk ve sadelik. |
| Sanat kararları, konsept brif, Flow karelerini karşılaştırma (görüntü girdisi) | **Opus 5.5** | high | Görsel yargı. |
| Unity Editor işleri (Unity MCP / unity-cli), prefab kurulumu, shader düğümü, URP Volume ayarı, Localization tabloları | **Sonnet 5.5** | medium | Hızlı döngü, çok küçük adım; Opus gereksiz. Zor hata → Opus. |
| Flow prompt varyantları, altyazı tabloları, Steam metni taslakları | **Sonnet 5.5** | low–medium | Üslup kitabı zaten yazılı; türetme işi. |
| 40 `RoomDefinition` SO'sunu `kirk-oda.md` tablosundan üretme, CSV ↔ Localization dönüşümü, yeniden adlandırma, lint, toplu dosya işleri | **Haiku 5.5** | low | Mekanik, hacimli, ucuz. Çıktıyı Opus bir kez okur. |
| Alt ajanlar (fork/Explore) | Opus 5.5 ana, Sonnet 5.5 işçi | — | Ana oturum bağlamı tutar; işçi dar görev alır. |

Kurallar:
- Effort'u model yerine önce dene: Opus 5.5 `xhigh` çoğu zaman Fable'ı gereksiz kılar.
- Model değiştirmek önbelleği sıfırlar; bir oturumda tek model, oturumlar arası geçiş.
- Fable 5.1 yalnız kapılarda ve ayda bir okumada; günlük üretimde değil.
- Hiçbir model kimliği commit'e, PR'a, oyun varlığına yazılmaz.

## 5. Eklenti ve araç haritası

| Araç | Ne için | Not |
| --- | --- | --- |
| **Unity (resmî eklenti)** — `new-unity-project`, `unity-cli`, `urp-postprocessing`, `localization`, `audio-setup-mixers`, `shader-graph-create-custom-node`, `unity-package-management` | 3. adım: proje kurulumu, URP Volume (sanat kitabı §3.5 değerleri), TR/EN, mixer yapısı (ses mimarisi §mixer), ses çizgisi/taş dalgası shader düğümleri | Unity yalnız kullanıcının bilgisayarında; bulut oturumunda çalışmaz. Unity MCP bağlantısı için Claude masaüstü oturumu ya da bilgisayarın bu oturuma bağlanması gerekir. |
| **unity-perf** — `csharp-zero-gc`, `unity-performance`, `code-standards` | 10. adım cila; Core için GC bütçesi | Erken kullanılmaz. |
| **design** — `design-critique`, `accessibility-review` | Sanat kitabı ve erişilebilirlik katmanının dış gözle okunması (K1 öncesi) | |
| **Clipkit** | Açılış efsanesinin animatiği: illüstratör karelerinden önce zamanlama ve mısra provası | Kilit sekmesindeki üç dörtlükle kuruldu (bkz. README). |
| **Three.js görüntüleyici** | Dünya ekseni ve kamera kademeleri için hızlı 3D blokaj | Bu oturumda bir blokaj gösterildi; Blender'a geçmeden önce ölçek kararı için. |
| **Figma `generate_image`** | 7 halka konsept karesi için hızlı eskiz | Bir Figma dosya anahtarı ister ve ücretli kredi tüketir; Flow üslup kitabı öncesi yalnız karşılaştırma amaçlı. |
| **Claude Docs** | Dünya kitabı ve "Senaryo kilidi" sekmesi | Depo kanonik kaynaktır; doc özet ve bağlantı taşır. |
| **GitHub** | PR, kod incelemesi (`/code-review`), ADR'lerin izlenmesi | Her hafta bir PR. |
| **Blender, Audacity, DaVinci, OBS, FFmpeg** | Yerel üretim | Claude bu araçları doğrudan kullanmaz; dışa aktarım adlandırması `oda-kiti.md` ile uyumlu olur. |
| **Godot** | Kullanılmaz | Kurulu ama bu proje Unity 6; yalnız bir prototip fikri Unity'de pahalıysa hızlı deneme için (karar gerektirir). |

Kullanılmayanlar: Vercel, Twilio, Orshot, Simplio3D, oyun mağazası katalogları — bu projeyle ilgisiz; oturumda yüklü olsalar da çağrılmaz.

## 6. Oturum protokolü (Claude Code)

1. Haftanın dokümanını aç, hedefi tek cümleyle yaz.
2. Modeli tabloya göre seç (`/model`).
3. İş bitince: değişen dokümanların çapraz güncellemesi, Core değiştiyse EditMode testleri, commit, PR.
4. PR açıklamasına "hangi dokümana dokunuldu" satırı; `/code-review` Opus 5.5 ile.
5. Oturum sonunda açık kararlar listesine bakılır; yeni karar varsa `[ ]` ile eklenir.

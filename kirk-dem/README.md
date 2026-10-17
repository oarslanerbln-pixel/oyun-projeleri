# Kırk Dem

Toroslarda bir kasabanın saat kulesi durur. Kulenin altındaki kırk odalı mağarada her odanın kendi zamanı vardır; saatçi her odadan bir "dem" getirip kuleyi yeniden kurmaya çalışır. 5–8 saatlik anlatı ve bulmaca oyunu, Unity 6 (URP), hedef 14,99 $.

Oyun hiçbir şeyi kesinleştirmez. Bu ilke bu deponun da ilkesidir: dokümanlar ne olduğunu değil, oyuncunun ne göreceğini yazar.

## Depo düzeni

```
kirk-dem/
  CLAUDE.md                  Claude için bağlayıcı kurallar, kimlikler, nerede ne var
  docs/
    00-dunya-kitabi.md       Kanonik dünya kitabı ve senaryo omurgası (Claude Docs'tan)
    01-senaryo-kilidi/       40 oda · 7 kasabalı × 4 çağ · 7 sır · anlatıcı mısraları · diyalog ilkeleri
    02-sanat-kitabi/         Palet, ışık, kamera, mekân, karakter · halka konsept brifleri · Flow üslup kitabı
    03-mimari/               Sistemler, veri modeli, oda kiti, ses mimarisi, 8 ADR
    04-calisma-yontemi.md    Doğrulama kapıları, haftalık ritim, model ve eklenti yönlendirmesi
    05-acimasiz-analiz.md    Uzman gözüyle 12 bulgu: uygulananlar ve karar bekleyenler
  unity/Assets/_KirkDem/     Kod iskeleti: saf C# çekirdek, ScriptableObject veri, Unity kabuk, EditMode testleri
```

`unity/` bir Unity projesi değil, bir Unity projesine kopyalanacak `Assets/_KirkDem/` klasörüdür. Bu ortamda derlenmedi; ilk Unity açılışında doğrulanır (`unity/Assets/_KirkDem/README.md`).

## Okuma sırası

1. `docs/00-dunya-kitabi.md` — her şeyin kaynağı.
2. `docs/01-senaryo-kilidi/kirk-oda.md` ve `sirlar.md` — oyunun gerçek omurgası.
3. `docs/03-mimari/README.md` — kod nasıl bölünür.
4. `docs/04-calisma-yontemi.md` — nasıl çalışılır, hangi modelle, hangi eklentiyle.

## Üretim planındaki yer

| # | Adım | Durum |
| --- | --- | --- |
| 1 | Senaryo kilidi | Claude Docs sekmesinde kilitli; depo kopyası + uygulama katmanı burada; hassasiyet okuması bekliyor |
| 2 | Sanat kitabı | Taslak tamam; Flow üslup kitabı kareleri üretilmedi |
| 3 | Dikey dilim | Mimari ve kod iskeleti hazır; Unity projesi açılmadı |
| 4–11 | — | Başlamadı |

## Bu oturumda üretilen yardımcı çıktılar

- Açılış efsanesi animatiği (Clipkit, 100 sn, mısralar zamanlanmış): https://www.clipkit.dev/public-editor?id=3fdfc580-ca29-49da-a5e9-8ffee1d6648b — not: animatik depodaki eski mısra taslağıyla kuruldu; kilit sekmesindeki üç dörtlükle güncellenmesi gerekir.
- Dünya ekseni 3D blokajı (Three.js görüntüleyici): kule, kasaba, yedi halka, kırk oda; oturum içinde gösterildi, Blender ölçek kararı için referans.

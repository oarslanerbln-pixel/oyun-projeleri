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
    05-acimasiz-analiz.md    Uzman gözüyle bulgular ve uygulananlar
    06-karar-kaydi.md        17 karar: gerekçe, geri dönüş tetikleyicisi, 14 aylık takvim
    07-hassasiyet-okumasi.md İki okuyucuya gidecek brif: ad, baba adı, imam, sırlar
  unity/Assets/_KirkDem/     Kod: saf C# çekirdek, ScriptableObject veri, Unity kabuk, EditMode testleri
  tools/core-tests/          Çekirdeği Unity olmadan derleyip test eden .NET projesi (CI bunu koşar)
```

`unity/` bir Unity projesi değil, bir Unity projesine kopyalanacak `Assets/_KirkDem/` klasörüdür. Çekirdek Unity olmadan derlenir ve test edilir (`dotnet test tools/core-tests`, 45 test); Data ve Gameplay katmanlarının gerçek doğrulaması ilk Unity açılışındadır.

## Okuma sırası

1. `docs/00-dunya-kitabi.md` — her şeyin kaynağı.
2. `docs/01-senaryo-kilidi/kirk-oda.md` ve `sirlar.md` — oyunun gerçek omurgası.
3. `docs/03-mimari/README.md` — kod nasıl bölünür.
4. `docs/04-calisma-yontemi.md` — nasıl çalışılır, hangi modelle, hangi eklentiyle.
5. `docs/06-karar-kaydi.md` — neye karar verildi, neden, ne olursa geri dönülür.

## Üretim planındaki yer

| # | Adım | Durum |
| --- | --- | --- |
| 0 | Kararlar | 17 karar verildi (`docs/06-karar-kaydi.md`); takvim 14 ay, çıkış Ocak 2028 sonu |
| 1 | Senaryo kilidi | Claude Docs sekmesinde kilitli; depo kopyası + uygulama katmanı burada; hassasiyet okuması 14 Kasım'a kadar |
| 2 | Sanat kitabı | Taslak tamam; Flow üslup kitabı kareleri üretilmedi |
| 3 | Dikey dilim | Çekirdek derleniyor ve test ediliyor; ADR 0009 yapı taşları (`RoomTimeline`, `Tide`, `ReverseRecorder`, `RecordLedger`, `HintTimer`) kodda; Unity projesi açılmadı |
| 4–11 | — | Başlamadı |

## Bu oturumda üretilen yardımcı çıktılar

- Açılış efsanesi animatiği (Clipkit, kilit sekmesindeki üç dörtlükle zamanlanmış): https://www.clipkit.dev/public-editor?id=3fdfc580-ca29-49da-a5e9-8ffee1d6648b
- Dünya ekseni 3D blokajı (Three.js görüntüleyici): kule, kasaba, yedi halka, kırk oda; oturum içinde gösterildi, Blender ölçek kararı için referans.

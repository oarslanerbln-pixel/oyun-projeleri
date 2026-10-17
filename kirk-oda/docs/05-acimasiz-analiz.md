# Acımasız Analiz — Kırk Oda

Tarih: 17 Ekim 2026. Bakış: anlatı-bulmaca türünde yayınlamış bir tasarımcı-yapımcının gözüyle, dünya kitabı ve senaryo kilidi sekmesi okunarak. Amaç övmek değil, kırılacak yeri bulmak. Her madde: bulgu → risk → ne yapıldı (bu PR'da uygulandı) ya da ne öneriliyor (karar kullanıcıya ait).

Kısaltma: **U** = uygulandı, **Ö** = öneri, karar bekliyor.

## Özet yargı

Tasarım fikri olarak proje türünün üst yüzdesinde: tek mekanik (dinleme), tek ilerleme göstergesi (taş), bedelin oyuncunun eliyle ödenmesi ve "hiçbir şeyi kesinleştirmeme" disiplini tutarlı. Senaryo kilidi sekmesi de bu disiplini satır satır taşıyor. Asıl sorun anlatıda değil, **üretim ölçeğinde ve oyuncunun eylemi fark edip edemeyeceğinde**. Aşağıdaki on iki maddenin dördü projeyi batırabilir (Ü1, T1, O2, O1); geri kalanı cila.

## Üretim

**Ü1. 10 ay gerçekçi değil.** 40 oda, 40 bekçi (beş ayrı tür: hayvan, çocuk, ihtiyar, saatçinin altı yaşı, yansıma), 7 kasabalı × çağ varyantı, 4 çağda tek harita, 7 farklı zaman sistemi, 6 video, iki dilde ses. Üretim planı yedi halkaya 16–18 hafta veriyor: oda başına 2–3 gün, bekçi modeli ve animasyonu dahil. Tek kişi için bu hız yalnız dış halkalarda (kit odaları) tutar. Benzer kapsamlı solo anlatı-bulmaca oyunları 2–3 yılda çıkar.
Risk: 6. adımda takvim iki katına çıkar, ses/cila/pazarlama adımları ezilir.
**U:** `04-calisma-yontemi.md`'ye 14–16 aylık alternatif takvim notu ve K2 kapısında ölçülen halka hızına göre karar kuralı eklendi.
**Ö:** Bekçileri "silüet + ışıklı göz" seviyesinde tutmak (sanat kitabı zaten izin veriyor); Toprak hayvanlarını tek bir dörtbacaklı rig üzerinde dokuyla ayırmak; saatçinin altı yaşı için tek model, yalnız duruş ve ölçek. Kırk sayısı anlatının sayısıdır, üretimin değil: dış iki halkada oda süresi 2 dakikayı geçmesin.

**Ü2. Dikey dilim riski ölçmüyordu.** Plan K1'i Toprak'ın 3 odasıyla tanımlıyordu; Toprak en ucuz ve en az riskli halka. Su'nun geri sarması, Gölge'nin çift akışı ve Ayna'nın kayıt düzenlemesi kanıtlanmadan kırk oda üretimine girilmesi, 14. haftada mimari yeniden yazmak demektir.
**U:** K1 artık Toprak'ın 3 tam odası + Su, Gölge, Ayna'dan birer gri kutu oda; ADR 0009 bu üçünü tek soyutlamaya indirdi.

**Ü3. Flow kredisi ve yapay zekâ bildirimi.** Sanat kolu klip sayısını 120–200 olarak hesapladı; dünya kitabı 60–80 diyor. Ayrıca niş kitle (anlatı, el yapımı, folk) yapay zekâ görselini mağaza sayfasında gördüğünde güven kaybı yaşayabilir; bu kitle için "AI disclosure" nötr değil, negatif sinyaldir.
**Ö:** Flow yalnız açılış için; Kökler ve üç son oyun içi kameradan (zaten Bir yıl / Kırk yıl öyle). Üslup kitabının 10–15 sabit karesini bir illüstratöre çizdirip (bütçe: tek kişilik stüdyo için en pahalı dış alım ama en yüksek getirili) Flow'u yalnız hareket için kullanmak. Bildirim metni o zaman "hareket yapay zekâ, kareler el" diyebilir.

**Ü4. Oynatma testi örneklemi.** 5 ve 10 kişi kullanılabilirlik için yeterli, son dağılımı ve fiyat kararı için değil. "Ortalama bitirme 5 saatin altındaysa 9,99 $" kuralını 10 kişiyle vermek gürültüye karar vermektir.
**Ö:** Fiyat kararını K3'e değil, Steam Next Fest demo verisine (yüzlerce oturum) bağlamak.

## Teknik

**T1. Geri sarma ve çift akış fizikle yapılırsa proje biter.** Her nesnenin her karesini kaydedip tersten oynatmak, deterministik olmayan fizikle birleşince "bazen çalışan" bulmacalar üretir. Tek kişilik ekipte en çok zaman yiyen hata sınıfı budur.
**U:** ADR 0009: her odanın bir `t` ekseni var, nesneler `t`'nin fonksiyonu; Su = yazılmış çizelge + dal; Gölge = oyuncunun kendi girdi kaydının ters oynatımı; Ayna = komut listesi; Nefes = odaya özel dünya saati. Fizik yalnız yürüyüş ve köpek için.

**T2. Tek dinamik ışık + baked** doğru karar ama 40 oda × bake süresi ve 4 çağ × kasaba bake'i gerçek bir iş yükü. **Ö:** Kasaba çağları için dört ayrı lightmap seti yerine tek bake + çağa göre emissive/post-process (sanat kitabı §2.3 zaten bu yönde); yalnız terk çağında ayrı bake.

**T3. Kayıt (save) tek slot, halka çıkışında.** Doğru ve temaya uygun; ama 10–15 dakikalık Ayna odalarında çıkış yapan oyuncu odayı baştan oynar. **Ö:** Oda içi "sessiz kontrol noktası": `RoomProgress.Milestone` zaten var; odaya dönüşte son kilometre taşından başlatmak, kaydı yine halka çıkışında yazmak. Oyuncuya gösterilmez.

## Oyuncu deneyimi

**O1. İpucu sistemi yok, kaybolmak serbest.** "Oyuncu kaybolabilir; köpek yol gösterir" bir cümle, bir sistem değil. Harita ve görev listesi olmayan bir oyunda takılma tek nedenle bırakılır: ne yapacağını bilememek. Steam'de bu tür oyunların bitirme oranı %30–40'tır; sessiz ipucu kanalı olmayanlarda daha düşük.
**U:** `sistemler.md §10` köpek ipucu zamanlayıcısı: odaya özel 2–3 kademe, yönü verir cevabı vermez, erişilebilirlik ayarıyla gecikme.

**O2. Sır söylemek görünmez bir eylem.** Arayüz yok, buton yok; "dinle" tuşunu bir kişinin yanında basılı tutmak gerekiyor. Oyuncuların büyük kısmı bunu keşfetmez, bütün sırlar varsayılan olarak saklanır, son dağılımı Dönüş/Kalış'a yığılır ve Dağıtış sonu kimse tarafından görülmez. Tasarımın en güzel seçimi oyuncuya ulaşmadan ölür.
**U:** `sistemler.md §4` ilk sırrın öğretilmesi: çoban yolun üstünde, taş kendiliğinden çeker, köpek durur, altyazı "taş çekiyor". Zorlama yok, gösterim var. K1 ölçütü: 5 oyuncudan en az 4'ü S1'de eylemi fark etti.

**O3. Nefes tutma = basılı tutma.** Motor erişilebilirlik ve yorgunluk. **U:** `sistemler.md §14` Hold/Toggle seçeneği, üç kanallı geri bildirim.

**O4. Ân'da seçim çoğu zaman tek seçenek.** S7 sayılmadığı için altı sır üzerinden 3/3 bölünme yalnız Kalış'ı açar; ad verilmemişse Dönüş hiç açılmaz. Kaba tahmin: oyuncuların üçte biri kırkıncı odaya tek açık eylemle gelir ve "eli taşa gider, kalkmaz" iki kez görür. Bu temaya uygun (niyet, kabul) ama oyuncu için "sahte seçim" hissi riski taşır.
**Ö:** Ya Dağıtış eşiğini 3'e indirmek (3/3 → Kalış ve Dağıtış açık; Dönüş yine ad + 4 saklı ister, asimetri korunur), ya da tek seçenekli durumu bilinçli olarak sahnelemek: saatçinin eli taşa gider, kalkmaz, köpek bakar, ikinci denemede taş kendi kararını "söyler". İkisi de sekmedeki "çoğu = 4" kararını değiştirir ya da sahneler; karar kullanıcıya ait.

**O5. Toprak çok uzun bir öğretici.** Dokuz oda, hepsi "bekle"; ilk 40–50 dakika tek fikir. Türün oyuncusu sabırlıdır ama Steam'in iki saatlik iade penceresi Toprak + Su'yu kapsar; ilk iki saat yalnız iki fikir gösterir.
**Ö:** Toprak'ı 7 odaya indirme seçeneğini (dünya kitabında var) varsayılan yapmak ve Su'nun 8. odasını (babanın inişi) 2. saatten önce garanti etmek. Kesilecek odalar: R1-05 (keçi) ve R1-06 (kaplumbağa, üç bekleyiş); ikisi de "bekleme" fikrine yeni bir şey katmıyor.

**O6. Kasaba dönüşleri 8–12 dakika serbest dolaşım.** Dört çağda aynı harita, 40 hane; konuşma bütçesi 40 cümle. Serbest dolaşım + az metin = boş gezinme riski. **Ö:** Her dönüşü tek bir "vakit" hedefiyle sahnelemek: oyuncu meydana çıkar, değişen tek şey kadrajın ortasındadır (nişan alayı, kuru dere, kapalı kahve), sır sahibi görüş hattındadır. Dolaşım serbest, ama sahne kurulu.

## Anlatı

**N1. Sekmedeki kilit sağlam.** Yedi sır "söylenen kişinin kendi hayatından" ve doğrulanmıyor; defter motifi (ebe, muhtar, Ayna) üç kişiyi bağlıyor; imamın sırrı ("değnek kuleden eskidir") oyunun en iyi cümlesi. Dokunulmadı.

**N2. Muhtarın sırrı soyut.** "Yanlış yazdığın gün yok; kasaba senin yazdığın günü yaşıyor" entelektüel olarak güzel, duygusal olarak uzak; diğer altı sır somut bir nesneye (kuzu, defter, dere, fincan) basıyor. **Ö:** Cümleyi defterle bağlamak: "Defterindeki günler yanlış değil; kasaba senin yazdığın günü yaşıyor." Tek sözcük farkı, nesne gelir.

**N3. Terk çağı anti-klimaks riski.** Boş kasabada serbest dolaşım, Ân'dan hemen önce, oyuncuyu düşürebilir. **U:** `kasaba-halki.md`'ye 3–4 dakikalık tek rota sahnelemesi eklendi (kapak → meydan → kahve → ebenin evi → kapak; köpek önden, kapılar arkadan kapanır).

**N4. Babanın adı kararı gecikmiş.** Kitabe harf sayısı Ayna'nın mekaniğini belirliyor; ad yoksa Ayna tasarlanamaz. **U:** DURSUN (6 harf) önerisi `diyalog-ilkeleri.md`'de, açık karar olarak; kodda 6.

**N5. "Kırk Dem" adı (kapandı: K-07 ve K-19, ad "Kırk Oda" oldu).** Dünya kitabı riski zaten yazıyor; ekleyeceğim tek şey zamanlama: Steam sayfası, alan adı ve kapak bu ada bağlı, hassasiyet okuması 1. adımın sonunda yapılmalı, 9. adımda değil. **Ö:** Okumayı bu PR'dan sonraki iki hafta içine almak; sonuç olumsuzsa "Kırk Oda" varsayılan.

## Ticari

**C1. 14,99 $ ve 5–6 saat** türün normu; sorun fiyat değil görünürlük. Türkçe folk-mistik anlatı bir USP ama Steam etiketleriyle bulunmaz; "Kırk yıl" videosu ve taşın sesi gibi 15 saniyelik, sözsüz anlaşılan anlar pazarlamanın malzemesi olmalı. **Ö:** 11. adımı beklemeden, dikey dilimden sonra bir 20 saniyelik sessiz GIF ("fener titrer, köpek girmez, kökler kurur") üretip Steam sayfasını o anda açmak; wishlists 8 ay birikir.

**C2. Yerelleştirme kapsamı.** TR/EN yeterli başlangıç; Almanca ve Japonca bu türün en güçlü ikinci pazarları ama metin az olduğu için (≈ 80 cümle + 20 mısra) maliyet düşük. **Ö:** Metin azlığını avantaja çevirip çıkışta 4 dil; anlatıcı sesi yalnız TR/EN, diğerleri altyazı.

## Bu PR'da uygulananların listesi

| Madde | Nerede |
| --- | --- |
| Ü1 takvim notu | `docs/04-calisma-yontemi.md` §2 |
| Ü2 K1 yeniden tanımı | `docs/04-calisma-yontemi.md` K1 satırı |
| T1 tek soyutlama | `docs/03-mimari/adr/0009-…md` |
| O1 köpek ipucu zamanlayıcısı | `docs/03-mimari/sistemler.md` §10 |
| O2 ilk sırrın öğretilmesi | `docs/03-mimari/sistemler.md` §4 |
| O3 nefes Hold/Toggle | `docs/03-mimari/sistemler.md` §14 |
| N3 terk rotası | `docs/01-senaryo-kilidi/kasaba-halki.md` |
| N4 ad önerisi | `docs/01-senaryo-kilidi/diyalog-ilkeleri.md` |

## Kararlar (17 Ekim 2026)

Kullanıcı kararları yönetmene bıraktı. Tamamı gerekçe ve geri dönüş tetikleyicisiyle `06-karar-kaydi.md` içindedir.

- [x] Ü1 → K-02: 14 ay, çıkış Ocak 2028 sonu; K-15: bekçiler 7 rig üzerinde.
- [x] Ü3 → K-05: Flow yalnız açılış; Kökler ve üç son oyun içi; açılış kareleri illüstratörden.
- [x] Ü4 → K-09: fiyat kararı Next Fest demo verisi ve K3 ile.
- [x] T3 → K-13: oda içi kilometre taşı kaydı (kod: `RoomProgress.Milestone`).
- [x] O4 → K-03: eşik 4 kalır, ölçüme bağlı.
- [x] O5 → K-04: Toprak 9 oda, oda başına 3 dk tavan, ölçüme bağlı kesinti.
- [x] O6 → K-14: yedi dönüşün açılış kadrajı.
- [x] N2 → K-10: muhtarın sırrı "defter"e bağlandı.
- [x] N5 → K-07 ve K-19: ad "Kırk Oda"; hassasiyet okuması artık adı değil, oyunun hiçbir inanç topluluğuna kaymadığını doğrular (`07-hassasiyet-okumasi.md`).
- [x] C1 → K-11: Steam sayfası Şubat 2027.
- [x] C2 → K-12: beş dil altyazı.
- [x] Yeni bulgu → K-16: kanonda kitabenin terk çağındaki hali tanımsızdı; karara bağlandı.

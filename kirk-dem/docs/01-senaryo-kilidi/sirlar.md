# Yedi Sır

Kaynak: Claude Docs "Senaryo kilidi" sekmesi; depoya özgü eklemeler **(depo)** ile işaretli.

Her sır ekranda tek cümle olarak belirir ve silinir; aşağıdaki cümleler oyun içi metindir. Hiçbiri taşı, babayı, bekçileri ya da yağmuru anmaz; hepsi söylenen kişinin kendi hayatından bir şeydir ve doğruluğu kasabada sınanmaz. Söylenen sır o halkanın kule katını karartır ve taşın sesini alçaltır; saklanan katı yakar ve sesi yükseltir. Ortası yoktur; söylenen sır aşağı inmeyi asla engellemez.

| # | Halka / oda | Sır (TR) | Sır (EN, depo) | Kime ait | Söylenirse hayatında ne değişir |
| --- | --- | --- | --- | --- | --- |
| S1 | Toprak / R1-09 | Kuzu sürüde; sen her gece dünkü sayıyı sayıyorsun. | The lamb is in the flock; every night you count yesterday's number. | Çoban | Saymayı bırakır ve o gece uyur; sabah kuzu sürüdedir. Kırk yıl sonra oğlu çobandır. |
| S2 | Su / R2-08 | Değirmencinin kızı yedi yaşındayken defterini okudu. | The miller's daughter read your book when she was seven. | Ebe | Kızı çırak alır; nişan kızın kendi eliyle bozulur. Defter ölümünde iki yolda da kıza kalır, ama bu yolda elden ele verilir. |
| S3 | Nefes / R3-07 | Dere kurumadı; değirmen onu içiyor. | The stream did not dry; the mill is drinking it. | Değirmenci | Çarkı geceleri durdurur, aylar içinde dere geri gelir; uyur. Değirmen kırk yıl sonra yine durmuştur, bu kez kendisi durdurmuştur. |
| S4 | Gölge / R4-06 | Yanlış yazdığın gün yok; kasaba senin yazdığın günü yaşıyor. | There is no day you wrote wrong; the town lives the day you write. | Muhtar | Defteri meydana asar, kapaktaki taşı kaldırtır; kuleyi yine sevmez ama korkmaz. Defter kasabanın tek takvimi olur. |
| S5 | Ayna / R5-05 | Fincanı otuz yıl önce, ilk gece sen yıkadın. | You washed the cup thirty years ago, on the first night. | Kahveci | O akşam kepengi kapatır, fincanı vitrine koyar. Bekleme biter; kimi beklediği yine söylenmez. |
| S6 | Sessizlik / R6-01, ilk geliş | Ebe seni nişanından önce seçmişti. | The midwife chose you before your engagement. | Değirmencinin kızı (kırk yıl sonra ebe) | Kırk yılda ilk kez güler; defteri kapatıp son sayfasını boş bırakır ve masada açık bırakır. Terk edilmiş çağda defter oradadır. |
| S7 | Ân / R7-01 | Değnek kuleden eskidir. | The staff is older than the tower. | İmam | Söylenemez: Ân'dan sonra yalnız son gelir ve imamın derdi yoktur. Taş onu saymaz; bu cümleyi oyundan oyuncu çıkarır. |

İki sır aynı düğümü iki ucundan çözer (ebeninki ve kızın bugünkü derdi), Ayna'nın defter odası (R5-03) üçüncü yoldur; oyuncu nişanın bozulmasını ya hiç görmez ya üç kez görür ve hangisinin "gerçek" neden olduğu söylenmez.

## Sır söyleme eylemi (depo)

Arayüzsüzdür: oyuncu kişinin yanında "dinle" tuşunu basılı tutar; saatçi dinlemez, söyler. Cümle ekranda bir kez daha belirir ve bu kez kişi de duyar. Söylemeden kapaktan inmek saklamaktır (`SecretLedger.FinalizeOnDescent`); bir sonraki çağda söylenemez. S6 kırk yıl çağında ebeye, kapağın başında söylenir ya da söylenmez.

## Sırların kaynağı belirsizdir (depo)

| Sır | Keramet okuması | Dünyevi okuma |
| --- | --- | --- |
| S1 | Karıncalar dünkü yolu taşıdı. | Çobanın her gece aynı sayıyı söylediğini herkes duyar. |
| S2 | Gelgit o yılı geri sardı. | Çocukken ebenin defterini kızın elinde görmüştü. |
| S3 | Ölmüş değirmenci söyledi. | Çarkın gece sesini kulede duymuştu. |
| S4 | Kendi gölgesi gördü. | Muhtarın defterini herkes bilir, kimse söylemez. |
| S5 | Yansıma gösterdi. | Rafta ters duran fincanı otuz yıldır herkes görür. |
| S6 | Duvar yazdı. | Eski ebe kızı herkesin gözü önünde seçmişti; kız görmemişti. |
| S7 | Ân'da taş söyledi. | Değneğin kuleden eski olduğunu kasaba zaten anlatır. |

## Sayım ve sonlar

- S7 sayılmaz. "Çoğu" altı sır üzerinden hesaplanır: dört ve üstü.
- **Dönüş** açık: ad verilmiş ve saklanan ≥ 4 (S1–S6).
- **Dağıtış** açık: söylenen ≥ 4 (S1–S6).
- **Kalış** her zaman açık.
- 3 saklı / 3 söylenmiş: yalnız Kalış açıktır. Ad verilmemişse Dönüş hiçbir sayımda açılmaz.

Kodda: `EndingResolver.Majority = 4`, sayım `SecretLedger.KeptCount/ToldCount` S1–S6 üzerinden (`CountedSecrets = 6`).

## Kule katları ve taş (depo)

| Kat | Halka | Söylendi | Saklandı |
| --- | --- | --- | --- |
| 1–6 | Toprak…Sessizlik | karanlık | yanık |
| 7 | Ân | — | demle döner, sırla değil |

Taşın perdesi = saklanan − söylenen (S1–S6); aralık −6…+6. Perdenin ses, titreşim ve dalga çizgisi karşılığı `03-mimari/ses-mimarisi.md` içindedir. Kırkıncı odaya inmeden önce kulenin hangi katlarının yandığı ve kitabenin dolu mu boş mu olduğu meydandan görülür; arayüz yoktur.

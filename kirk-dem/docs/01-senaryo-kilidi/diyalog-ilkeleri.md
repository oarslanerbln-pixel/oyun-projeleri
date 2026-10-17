# Diyalog İlkeleri ve İki Zorunlu Sahne (depo)

Bu dosya senaryo kilidi sekmesinde olmayan uygulama katmanıdır: konuşma kuralları, iki zorunlu sahnenin akışı, babanın adı önerisi ve konuşma bütçesi. Sekmeye yeni kural eklemez; sekmedeki kararlarla (muhtarın oğlu, ebenin defteri, taşın yeri) uyumludur.

## İlkeler

1. **Az.** Bir sahne sözsüz anlatılabiliyorsa sözsüzdür. Bir kasaba dönüşünde toplam konuşma 40 cümleyi geçmez.
2. **Soru yok.** Kasabalılar soru sormaz, saatçi soru sormaz. Söylenen şey ya bir gözlemdir ya bir istek.
3. **Açıklama yok.** Hiç kimse zaman kuralını, taşı, kapağı, bekçileri açıklamaz. "Hep böyle miydi" belirsizliği cümleyle değil bakışla verilir.
4. **Kavram adı yok.** Nefs, hâl, makam, tayy, bast, ân, keramet, veli sözcükleri geçmez. "Sır" yalnız gündelik anlamıyla ve tercihen hiç.
5. **Gerçek ad yok.** Kasabalılara işleriyle seslenilir. Oyundaki tek özel ad babanın adıdır.
6. **Çağa göre ağız.** bugun: kısa, sıcak, "usta". bir-yil: biraz mesafeli; nişan, kuzu, dere konuşulur. kirk-yil: yalnız ebe ve imam konuşur (imam tek cümle ya da hiç); başkaları bakar. terk: kimse yok.
7. **Yağmur doğaldır.** Kasabada yağmur anılmaz; yalnız sinematiklerde yağar ve kimse sormaz.
8. **Saygı.** İmam hiçbir inanç cümlesi söylemez; ikindiyi gölgeyle ölçmesi gösterilir, anlatılmaz. Hiçbir sahne bir inancı doğrulamaz ya da yalanlamaz.
9. **Altyazı eşi.** Her konuşmanın altyazısı vardır; ses ipuçlarının da ("su damlıyor", "çark takılıyor"). Altyazı metni diyalog metninden ayrı tabloda tutulur.

## Babanın adı — açık karar

Kilit sekmesi adı seçmez; ebe adı "eski ebenin defterinden" okur. Depo önerisi: **DURSUN**, altı harf. Türkçede hem ad hem dilektir; kule için de Kalış sonu için de yankı verir; İngilizce oyuncu için yalnız bir addır. Yedek: **SABRİ** (beş harf; Ayna'nın beş odası harfleri bitirir, kırk yıla harf kalmaz; ikinci sırada). İki ad da gerçek bir veli ya da tarihi kişiyle örtüşmez. Karar hassasiyet okumasına bırakılır; dünya kitabının açık kararlar listesine eklenmelidir.

Ad yalnız üç yerde geçer: kitabede (görsel), ebenin ağzında (Kırılma 2), oyuncunun yazdığı anda (Sessizlik, sessiz). Anlatıcı adı hiç söylemez. Kodda `GameRoot.inscriptionLetters = 6`.

## Babanın sesi (R4-05)

Tek cümle, gölgede tersten gelir, ışığa çıkınca düz duyulur:

> Geri dönmek için inmek gerekmezdi. / You never had to go down to come back.

Bir daha duyulmaz (Gölge 5'te verilen korku). Yaşlı saatçi ile aynı oyuncu; doğrulanmaz.

## Kırılma 1 — Kapak (bir-yil çağı, Su'dan dönüş)

Muhtar kapağın başına taş getirtmiştir; kahveci ve çoban yanında, imam değneğinin başında. Değirmencinin kızı muhtarın oğluna nişanlıdır; S2 söylendiyse ebenin çırağıdır ve nişanı bozmuştur, muhtar bunu da taşır.

**İkna yolu.** Oyuncu meydanda üç şeyden en az ikisini yapar: (a) imamın yanında durup gölgeye bakar; imam değneği bir karış oynatır, muhtar görür; (b) değirmenciyle konuşur ("kule çalışsın, su gelir"); (c) kahveciyle konuşur, kahveci muhtara çay uzatır, "otur" der. Muhtar tek cümle söyler ve gider; taş kenarda kalır.

> MUHTAR: Örtmeyin. Ben bakmam.

**Gizli yol.** Oyuncu gece kahvenin arka kapısından geçer; taş kapağın yarısındadır, geçit dardır. Sabah kasaba saatçiye farklı bakar: kahveci çay vermez, çoban ipini geri ister, imam değişmez. Gölge'den sonra S4 söylenirse muhtar taşı kaldırtır ve defteri meydana asar; yol bakışı değiştirir, kaderi değil.

İki yolda da inilen odalar aynıdır.

## Kırılma 2 — Ebe (kirk-yil çağı, Sessizlik'in ilk odasından dönüş)

Kapak açılır. Kapağın başında yaşlı bir kadın oturur; dizinde eski ebenin defteri, yanında fener. Değirmencinin kızıdır, artık ebedir; saatçi onu tanımaz, o saatçiyi tanır. Konuşma bitmeden inilemez; kamera bir kademe yaklaşır.

> EBE: Usta.
> (Sessizlik. Saatçi kuleye bakar; kitabe boştur.)
> EBE: Kitabeye bakma. Boş. Kırk yıldır boş.
> (Defteri açar; bir sayfayı bulur, okumaz, parmağını koyar. Köpek ebenin dizine başını koyar; ebe köpeğin gölgesine bakar, gülümsemez.)
> EBE: Baban. Adı burada. Dursun.
> (Sessizlik.)
> EBE: Ben söyledim. Sen bilirsin.

Sonra ebe kalkmaz; oyuncu isterse S6'yı söyler ("dinle" tuşu basılı). Söylerse ebe kırk yılda ilk kez güler, defteri kapatıp son sayfasını boş bırakır ve eve gider. Söylemezse oturur; defter kilitli kalır.

"Sen bilirsin" ikili okunur: hem "karar senin" hem "sen zaten bilirsin". Çeviride korunur: "I've said it. You'll know."

## Konuşma bütçesi

| Dönüş | Çağ | Konuşan | Cümle |
| --- | --- | --- | --- |
| Toprak sonu | bugun | kahveci, çoban, değirmenci, imam (sessiz) | ≤ 12 |
| Su sonu | bir-yil | ebe (S2), değirmenci, kız, muhtar (Kırılma 1) | ≤ 25 |
| Nefes sonu | bir-yil | değirmenci (S3), kahveci | ≤ 10 |
| Gölge sonu | bir-yil | muhtar (S4), imam (sessiz) | ≤ 8 |
| Ayna sonu | bir-yil (yıllar) | kahveci (S5), herkes "hep böyle miydi" bakışı | ≤ 12 |
| Sessizlik ilk odasından | kirk-yil | ebe (Kırılma 2, S6), imam (tek cümle ya da hiç) | ≤ 14 |
| Sessizlik dördüncü odasından | terk | kimse | 0 |

Toplam ≈ 80 cümle diyalog + anlatıcı 20 mısra + 7 sır + 7 öfke + 5 hatıra + 8 alışkanlık + 6 korku göstergesi. Yerelleştirme tablosu bu sayılara göre planlanır.

# İnanç Çağrışımı Denetimi

Tarih: 17 Ekim 2026. Yönerge (kullanıcı): "Oyun Alevi Bektaşiliğe kaymasın. Dikkat edelim." Karar: K-19.

## İlke

Kırk Oda Türk mitolojisinden, halk masallarından ve tasavvufun genel kavramlarından beslenir; bunları yapı olarak kullanır, adlarını anmaz. Hiçbir inanç topluluğunun öğretisini, ritüelini, terimini, müziğini ya da anlatısını taşımaz. Özellikle Alevi-Bektaşi geleneğine kaymaz. Bu, dünya kitabının "inanç kaynak olarak kullanılır, alay ya da iddia konusu yapılmaz" ilkesinin bir adım ötesidir: kaynak olarak bile belirli bir topluluğun ayırt edici unsurları kullanılmaz.

## Bulgular

Tarama, dünya kitabı, senaryo kilidi, sanat kitabı, mimari ve kodda her unsuru gözden geçirdi.

| # | Unsur | Çağrışım | Risk | Karar |
| --- | --- | --- | --- | --- |
| 1 | Ad "Kırk Dem" | Kırklar Cemi; cemde paylaşılan içkinin adı "dem" | Yüksek | **Değişti:** Kırk Oda / Forty Rooms |
| 2 | Odalardan alınan ışığın adı "dem" | Aynı; "kırk dem" sözü kendiliğinden oluşuyordu | Yüksek | **Değişti:** "kor" (kodda `Ember`) |
| 3 | Anlatıcı "bir âşık gibi konuşur" | Saz eşliğinde deyiş ve nefes geleneği | Orta | **Değişti:** masalcı; saz, bağlama, ezgi yok; konuşur gibi söylenir |
| 4 | Kırk oda + kulede biriken "makam" | "Dört kapı kırk makam" yol öğretisi | Orta | **Sınırlandı:** "makam" yalnız müzik anlamında, oyunda hiç adı geçmez; en çok altı nota; "kırk makam" hiçbir yerde kurulmaz (denetim HATA) |
| 5 | Halka adı "Nefes" | Alevi-Bektaşi şiir türü "nefes" | Düşük | **Kalır:** mekanik nefes tutmaktır; ad oyunda geçmez; mısralar ve ses tasarımı bu türe benzetilmez |
| 6 | Sır saklama ve söyleme | Yolun "sır" ahlakı | Düşük | **Kalır:** sırlar kişisel ve gündeliktir (kuzu, defter, dere, fincan); "sır ehli", "sırrı fâş etmek" gibi deyimler kullanılmaz |
| 7 | Yedi halka | Nefs mertebeleri; ayrıca "yedi ulu ozan" | Düşük | **Kalır:** nefs mertebeleri tasavvufun genel kavramıdır; sayı oyunda vurgulanmaz |
| 8 | Hayat Ağacı, kam, yada taşı | Türk-Altay mitolojisi | Düşük | **Kalır:** bir inanç topluluğuyla ilişkilendirilmez; pazarlama metinlerinde topluluk adı geçmez |
| 9 | İmam ve cami | Kasabanın tek din görevlisi | Düşük | **Kalır:** genel bir Anadolu kasabası; imam hiçbir inanç cümlesi söylemez, hiçbir mezhep öne çıkarılmaz |
| 10 | Yeşil yemeni, kırk sayısı, dört çağ | Genel kültür | Yok | Kalır |

Denetlenip hiçbir yerde geçmediği doğrulanan sözcükler: cem, cemevi, semah, deyiş, duaz, gülbank, dede (unvan), pir, mürşit, musahip, rehber (unvan), zakir, lokma, erkân, Hızır, Kerbela, Muharrem, Zülfikar, dergâh, tekke, derviş, şeyh, tarikat, abdal, can (hitap), eyvallah, aşk olsun.

## Kalıcı güvence

1. **Tek kaynak.** Oyuncunun gördüğü her metin `localization/oyuncu-metni.csv` dosyasındadır: sırlar, mısralar, replikler, ses altyazıları. Yeni metin önce buraya yazılır; Unity Localization tabloları buradan beslenir. Mağaza ve basın metinleri `magaza/` altında tutulur ve aynı denetimden geçer.
2. **Denetim.** `tools/metin-denetimi/denetle.py` bu dosyayı `yasak-sozcukler.tsv` listesine karşı denetler. HATA düzeyindeki bir eşleşme GitHub Actions'ta PR'ı düşürür. Denetleyici Türkçe büyük-küçük harf kurallarına uyar ve kendi testleriyle gelir (`--self-test`).
3. **İzin.** Bir satırda bilerek izin verilen bir eşleşme `izin` sütununa desen kimliğiyle yazılır ve karar kaydında gerekçelendirilir. Liste büyür, küçülmez.
4. **Ses ve müzik.** Saz, bağlama, ney ya da dini ezgi kullanılmaz; çanın dizisi tek tek notalardan oluşur ve bir dini ezgiye benzetilmez (`03-mimari/ses-mimarisi.md`).
5. **Görsel.** Flow negatif listesi zaten tanınabilir dini sembolleri dışlar; buna ek olarak semah dönüşüne, cem halkasına, on iki imam simgelerine ya da Zülfikar'a benzeyen hiçbir kompozisyon kullanılmaz.
6. **Okuma.** Alevi-Bektaşi okurun hassasiyet okuması (`07-hassasiyet-okumasi.md`) bu denetimin dış doğrulamasıdır.

## Kapsam dışı bir not

Köpeğin gölgesinin kurda dönüşmesi Türk mitolojisindeki kurt rehberden gelir. Aynı imge bugün siyasi bir simge olarak da kullanılır. Oyunda yalnız gölgede, sözsüz ve belirsiz kaldığı sürece risk düşüktür. Pazarlama görsellerinde kurt gölgesi öne çıkarılmamalıdır.

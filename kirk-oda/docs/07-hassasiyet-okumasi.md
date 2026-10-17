# Hassasiyet Okuması — Brif

Teslim: 14 Kasım 2026. Gönderim: en geç 24 Ekim 2026. İki okuyucu, birbirinden bağımsız: (1) bir halk edebiyatı ya da tasavvuf okuru, (2) bir Alevi-Bektaşi okur. Okuyuculara ücret ödenir ve adları isterlerse jenerikte "kültür danışmanı" olarak yer alır.

**Okumanın amacı (karar K-19, 17 Ekim 2026).** Oyun hiçbir inanç topluluğunun öğretisine, ritüeline, terimine ya da anlatısına kaymamalı, özellikle Alevi-Bektaşi geleneğine. Ad ("Kırk Dem" → "Kırk Oda") ve nesne adı ("dem" → "kor") bu yüzden okumadan önce değiştirildi. Okuma artık bir adı onaylamıyor; oyunun bütününde kalan çağrışımları arıyor. Alevi-Bektaşi okur bu yüzden en önemli okuyucudur: kaymayı en iyi o görür.

## Okuyucuya giden mektup (TR)

> Merhaba,
>
> Toroslarda bir kasabada geçen, beş-altı saatlik bir anlatı ve bulmaca oyunu yapıyoruz: Kırk Oda. Kasabanın saat kulesi durur; altındaki kırk odalı mağarada her odanın kendi zamanı vardır ve saatçi kuleyi yeniden kurmaya çalışır. Oyun Türk mitolojisinden, halk masallarından ve tasavvufun genel kavramlarından beslenir ama hiçbir kavramın adını anmaz, hiçbir inancı doğrulamaz ya da yalanlamaz, hiçbir gerçek kişiyi, tarikatı ya da inanç topluluğunu konu edinmez.
>
> Sizden istediğimiz, oyunun herhangi bir inanç topluluğunun, özellikle Alevi-Bektaşi geleneğinin öğretisine, ritüeline ya da anlatısına benzeyip benzemediğini söylemenizdir. Benzeyen bir yer varsa, istemeden de olsa, onu değiştireceğiz. Ekte dört sayfa var; okuma yaklaşık bir saat sürer.

## Ekler (dört sayfa)

1. Dünya kitabının "İlkeler" ve "Dünya" bölümleri.
2. Oyuncunun gördüğü bütün metin: yedi sır, açılışın üç dörtlüğü, Kökler ve üç sonun mısraları, iki sahnenin replikleri (`localization/oyuncu-metni.csv`).
3. Kasaba halkının dört çağı, imamın satırı dahil (`01-senaryo-kilidi/kasaba-halki.md`).
4. Yapı özeti: kırk oda, yedi halka, halkaların sırası, kulede biriken notalar, anlatıcının üslubu.

## Sorular

Her soruya üç cevaptan biri yeterli: **temiz** / **dikkat, şu değişirse temiz** / **kullanılmamalı**.

| # | Soru | Neden soruyoruz |
| --- | --- | --- |
| S1 | Oyunun yapısı (kırk oda, yedi halka, kulede biriken notalardan oluşan bir dizi) "dört kapı kırk makam" gibi bir yol öğretisine gönderme gibi okunuyor mu? | Kırk sayısı ve "makam" sözcüğü tasarım dilinde yan yana; oyunda ikisi de adıyla geçmiyor. |
| S2 | Anlatıcının üslubu (on bir heceli mısralar, "imiş" ve "derler" ile, sazsız ve ezgisiz) bir dini şiir türünü (deyiş, nefes, ilahi) çağırıyor mu? | Anlatıcı masalcı olmalı. |
| S3 | Kahramanın babasının adı "Dursun". Bu ad bilinen bir din büyüğüne gönderme gibi okunur mu? | Erken Osmanlı döneminde bu adı taşıyan bilinen bir din adamı var; ad çok yaygın olduğu için risk düşük görünüyor. |
| S4 | Kasabanın imamı kule durunca ikindiyi değnek dikip gölgeyle bulur ve hiçbir inanç cümlesi söylemez. Bu tasvir saygılı mı, bir mezhebi öne çıkarıyor mu? | Oyun hiçbir mezhebi yüceltmemeli ya da küçültmemeli. |
| S5 | Yedi sır cümlesinden herhangi biri bir inanç iddiası ya da bir topluluğun "sır" anlayışına gönderme gibi okunuyor mu? | Sırlar kişisel ve gündeliktir; öyle kalmalı. |
| S6 | Açılış efsanesindeki "yabancı" ya da bekçiler bir veli, ermiş ya da kutsal kişi gibi okunuyor mu? | Adsız kalmaları ve tanınmamaları gerekiyor. |
| S7 | Oyunda gördüğünüz herhangi bir şey alay, iddia ya da kutsalın sıradanlaştırılması gibi duruyor mu? | Açık soru. |

## Kararın okunması

- İki okuyucudan biri bile bir soruya "kullanılmamalı" derse o unsur değiştirilir; çoğunluk aranmaz.
- "Dikkat" notları `09-inanc-cagrisim-denetimi.md` bulgular tablosuna eklenir; gereken sözcükler `tools/metin-denetimi/yasak-sozcukler.tsv` listesine girer.
- S3 "temiz" değilse baba adı SABRİ olur (5 harf; `veri-modeli.md`, `GameRoot.inscriptionLetters` ve `localization/oyuncu-metni.csv` birlikte güncellenir).

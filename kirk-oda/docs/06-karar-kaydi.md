# Karar Kaydı

Tarih: 17 Ekim 2026. Yetki: kullanıcı açık kararları yönetmene bıraktı ("Kararları sana bırakıyorum"). Her karar bir gerekçe ve ölçülebilir bir **geri dönüş tetikleyicisi** taşır: tetikleyici gerçekleşirse karar yeniden açılır, gerçekleşmezse kapalı kalır. Kanonik belgeye (Claude Docs) taşınan kararlar orada da işaretlidir.

## Özet

| No | Konu | Karar | Geri dönüş tetikleyicisi |
| --- | --- | --- | --- |
| K-01 | Depo düzeni | `main` taban dalı; iş dalları PR ile birleşir; çekirdek testleri her PR'da koşar | — |
| K-02 | Takvim | 14 ay üretim, çıkış Ocak 2028 sonu; demo Haziran 2027 Steam Next Fest | K2'de halka hızı ≤ 2 hafta ise çıkış Kasım 2027'ye çekilir |
| K-03 | Dağıtış eşiği | 4 kalır (altı sırrın çoğu); 3/3 yalnız Kalış'ı açar | K3'te oyuncuların %35'inden fazlası Ân'a tek seçenekle gelirse eşik 3'e iner |
| K-04 | Toprak | 9 oda kalır; oda başına 3 dk tavan | K3'te "Su 8'e varış" medyanı 1 sa 45 dk'yı aşarsa R1-05 ve R1-06 kesilir |
| K-05 | Sinematik | Flow yalnız açılış efsanesinde; Kökler ve üç son oyun içinde, mürekkep efektiyle. Açılış kareleri: Flow ilk geçiş, illüstratör üstüne boyar | İllüstratör bulunamazsa Flow kareleri elle rötuşlanır |
| K-06 | Babanın adı | DURSUN; kitabe 6 harf | Hassasiyet okuması itiraz ederse SABRİ (5 harf) |
| K-07 | Oyunun adı | **Kırk Oda** (EN: Forty Rooms); "Kırk Dem" bırakıldı (K-19) | — |
| K-08 | Anlatıcı dili | İki dilde kayıt; varsayılan oyuncunun dili; ilk açılışta "Orijinal Türkçe ses" belirgin | — |
| K-09 | Fiyat | 14,99 $ sabit; çıkış indirimi %15 | Demo + K3 medyan bitirme < 4 sa ise 12,99 $ |
| K-10 | Muhtarın sırrı | "Defterindeki günler yanlış değil; kasaba senin yazdığın günü yaşıyor." | — |
| K-11 | Steam sayfası | Şubat 2027 başı, K1 ve K-07'den sonra; 20 sn sessiz GIF ile | K-07 gecikirse sayfa da gecikir; kamuya ad açılmadan sayfa yok |
| K-12 | Yerelleştirme | Çıkışta ses TR/EN; altyazı TR, EN, DE, JA, ZH-Hans | Wishlist coğrafyasında FR ya da ES ilk beşe girerse eklenir |
| K-13 | Oda içi kayıt | Tek slot kalır; oda içi kilometre taşı sessizce kaydedilir | — |
| K-14 | Kasaba dönüşleri | Her dönüş "tek kadraj, tek değişim" ile açılır; sır sahibi görüş hattında | — |
| K-15 | Varlık ekonomisi | Bekçiler silüet + ışıklı göz; 40 bekçi 7 rig üzerinde | K1'de bekçi başına üretim 1 günü aşarsa rig sayısı 5'e iner |
| K-16 | Kitabe durumu | Kırk yıl kitabeyi boşaltır; terk çağında ad verilmediyse kitabe dolu, verildiyse boş okunur | — |
| K-18 | Flow oyun içinde | Üç sınıf: A referans (oyuna girmez), B arka plan ve doku katmanı, C açılış. Beş yasak: yüz ve karakter, yazı, ses, oynanışın odağı, kimlik | Steam sayfası yorumlarında ya da demo geri bildiriminde yapay zekâ tepkisi belirginleşirse B sınıfı elle yapılmış karşılıklarıyla değiştirilir; manifest bunu mümkün kılar |
| K-19 | İnanç çağrışımı | Oyun hiçbir inanç topluluğunun, özellikle Alevi-Bektaşi geleneğinin öğretisine, ritüeline, terimine ya da anlatısına kaymaz. "Dem" → "kor"; anlatıcı masalcı, sazsız; oyuncunun gördüğü her metin yasak sözcük denetiminden geçer (CI) | Hassasiyet okumasında "dikkat" notu alan her unsur değiştirilir; denetim listesi büyür, küçülmez |
| K-17 | Kaynak dosyalar | Oyuna giren varlıklar Git LFS ile depoda; `.blend`, ham ses ve kurgu projeleri depo dışında yedekli klasörde | LFS kotası dolarsa yalnız oyuna giren varlıklar kalır |

## Gerekçeler

**K-01 Depo düzeni.** Depo boştu; PR açılabilmesi için bir taban dalı gerekiyordu. `main` en küçük ilk commit ile açıldı, iş dalı onun üstüne taşındı. Çekirdek (`KirkOda.Core`) artık Unity olmadan derlenip test ediliyor (`tools/core-tests`); bu testler GitHub Actions'ta her PR'da koşar. Bu, tek kişilik ekipte geriye dönük kırılmayı ucuza yakalayan tek güvencedir.

**K-02 Takvim.** Dünya kitabının 10 ayı, 40 bekçi, 4 çağ ve 7 zaman sistemi için iyimser (analiz Ü1). 14 ay, dikey dilime 8 hafta ve halka başına 3 hafta verir. İskelet:

| Dönem | Faz | Çıktı | Kapı |
| --- | --- | --- | --- |
| Eki–Kas 2026 (4 hf) | Kapanış | Hassasiyet okuması, illüstratör brifi, Unity projesi, oda kiti iskeleti | K0 |
| Kas 2026–Oca 2027 (8 hf) | Dikey dilim | Toprak 3 oda tam kalite + Su, Gölge, Ayna gri kutu; kasaba bugün çağı | K1 (10 Ocak) |
| Şub 2027 | Steam sayfası | Ad, kapsül görseli, 20 sn GIF | — |
| Oca–Nis 2027 | Halka 1–3 | Toprak, Su, Nefes; kasaba bugün ve bir-yıl çağları | K2 (Nisan sonu) |
| May 2027 | Demo | Toprak + Su + iki kasaba dönüşü, cilalı | — |
| Haz 2027 | Steam Next Fest | Demo yayında; wishlist ve oynanış verisi | Tarih Steamworks'te doğrulanır |
| Haz–Eyl 2027 | Halka 4–7 | Gölge, Ayna, Sessizlik, Ân; kırk yıl ve terk çağları | — |
| Eyl–Eki 2027 | Sinematik, ses, dil | Açılış (Flow), Kökler ve üç son (oyun içi), 5 dil altyazı | — |
| Kas 2027 | Tam oyun testi | 10+ oyuncu, en az 3 yabancı | K3 |
| Kas–Ara 2027 | Cila | Hata, denge, erişilebilirlik | — |
| Oca 2028 sonu | Çıkış | Kış indirimi sonrası, kalabalıktan uzak | — |

Next Fest'e bir oyun bir kez katılabildiği için demo tek atış olarak planlandı. Aralık çıkışı bilinçli olarak dışarıda bırakıldı: kış indirimi döneminde görünürlük düşer.

**K-03 Dağıtış eşiği.** Kanonun omurgası "ortası yoktur". 3/3 bölünmenin yalnız Kalış'ı açması bu ilkenin mekanik karşılığıdır: kararsızlık kalmaktır. Eşiği 3'e indirmek anlatıyı sulandırır; ama "sahte seçim" riski gerçek (analiz O4). Bu yüzden karar ölçüme bağlandı. İlk sırrın öğretilmesi (analiz O2) dağılımı zaten açacaktır. Ân'daki tek seçenekli durum sahnelenmiştir: açık olmayan eylemde el taşa gider, kalkmaz.

**K-04 Toprak.** Kilit sekmesindeki süreler (2–4 dk) ile Toprak 25–30 dakikadır; Su'nun son odası (babanın inişi) oyunun yaklaşık 1 sa 30 dk'sına düşer, iade penceresinin içinde. Kırk sayısı oyunun adı ve kırkıncı odanın anlamıdır; ölçüm gerektirmedikçe kesilmez. Oda başına 3 dakika tavanı K1'de ölçülür.

**K-05 Sinematik.** Üç sonun anlamı oyuncunun seçimlerindedir: hangi katlar yanıyor, kitabe dolu mu, kimin evinde ışık var, çan hangi makamı çalıyor. Önceden üretilmiş bir Flow klibi bunları gösteremez; oyun içi kamera gösterir. Bir yıl ve Kırk yıl zaten bu hatta (oyun içi sabit kamera + mürekkep efekti) olduğu için ek altyapı gerekmez. Flow yalnız açılış efsanesinde kalır, çünkü o kasabanın anlattığı ve oyuncudan bağımsız tek hikâyedir. Açılışın 12 anahtar karesi Flow'da ilk geçiş olarak üretilir, bir illüstratör üstüne boyar; Flow hareketi verir (K-18 ile güncellendi). Kazanç: sinematik için Flow kredisi beşte bire iner; Steam bildirimi açılış ve K-18'in B sınıfıyla sınırlı kalır.

**K-06 Babanın adı.** DURSUN Türkçede hem yaygın bir ad hem bir dilektir ("dursun"): ölen çocukların ardından doğana verilir. Kule durur, Kalış'ta akrep durur; bilen tanır, bilmeyen için yalnız bir addır. Altı harf, Ayna'nın beş odasının en çok beş harf silmesine ve son harfin kırk yılla gitmesine tam oturur. Bilinen bir tarihi din adamı aynı adı taşıdığı için okuyucuya ayrıca sorulur (`07-hassasiyet-okumasi.md`).

**K-07 Oyunun adı (17 Ekim 2026'da kapandı).** İlk karar ad için hassasiyet okumasını bekliyordu, çünkü "kırk" ve "dem" birlikte Alevi-Bektaşi Kırklar Cemi anlatısını güçlü biçimde çağırır: orada kırklar tek bir üzümün şerbetini paylaşır ve "dem" o paylaşılan içkinin adıdır. Kullanıcının yönergesi ("Oyun Alevi Bektaşiliğe kaymasın") bu bekleyişi gereksiz kıldı: risk yalnız bir topluluğu incitmek değil, oyunun kimliğinin kaymasıdır. Ad **Kırk Oda** (İngilizce **Forty Rooms**) oldu. Bu ad masallardaki "kırkıncı odayı açma" yasağı motifiyle örtüşür; kırkıncı oda (Ân) oyunun son seçimidir. Depo klasörü ve kod adları da `kirk-oda` / `KirkOda` olarak değişti; Unity projesi henüz açılmadığı için bedeli yok denecek kadar azdı.

**K-08 Anlatıcı dili.** Dünya kitabının önerisi aynen kabul edildi.

**K-09 Fiyat.** 5–6 saatlik el yapımı anlatı oyunu için 14,99 $ türün ortasıdır. On kişilik testle fiyat düşürmek gürültüye karar vermektir; karar Next Fest demo verisi ve K3 ile birlikte verilir.

**K-10 Muhtarın sırrı.** Diğer altı sır somut bir nesneye basar (kuzu, defter, dere, fincan); muhtarınki soyut kalıyordu. "Defter" sözcüğü muhtarın kasabadaki nesnesini (meydana asılan defter) sırra bağlar. Anlam değişmez.

**K-11 Steam sayfası.** Wishlist birikimi çıkıştan aylar önce başlamalıdır; 12 aylık bir sayfa, 3 aylık bir sayfadan anlamlı ölçüde fazla wishlist toplar. Malzeme: "fener titrer, köpek girmez, kökler kurur" anı, sözsüz anlaşılan 20 saniye.

**K-12 Yerelleştirme.** Oyunda ≈ 80 cümle diyalog, 20 mısra, 7 sır ve ses altyazıları var; metin azlığı beş dili ucuzlatır. Mısralar edebi çevirmen ister; sır cümleleri tek tek onaylanır.

**K-13 Oda içi kayıt.** 10–15 dakikalık Ayna ve Sessizlik odalarında çıkan oyuncu odayı baştan oynamamalı. `RoomProgress.Milestone` geri alınamaz adımları tutar; kayıt tek slot kalır, "deneyip geri alma" yolu yine yoktur (ADR-0006 güncellendi).

**K-14 Kasaba dönüşleri.** Serbest dolaşım + az metin boş gezinme üretir (analiz O6). Her dönüş, kapaktan çıkışta kameranın kendiliğinden gösterdiği tek bir değişimle açılır; sonra dolaşım serbesttir. Tablo: `01-senaryo-kilidi/kasaba-halki.md`.

**K-15 Varlık ekonomisi.** 40 bekçi tek kişi için en büyük modelleme yüküdür. Kural: bekçiler silüet + ışıklı gözdür, yüz hattı yok. Rig'ler: dörtbacaklı (geyik, keçi, kaplumbağa, kirpi), kuş (turna, baykuş), sürü (arı, karınca; parçacık + tek model), yılan, çocuk (Su'nun 8 çocuğu, kıyafet ve saç varyantı), ihtiyar (Nefes'in 7 ihtiyarı), saatçi (Gölge'nin 6 yaşı ölçek ve duruşla). Ayna yansımaları kasabalı modellerinin ters shader'lı kopyasıdır, yeni model değildir. Tablo: `02-sanat-kitabi/README.md` §6.6.

**K-16 Kitabe durumu.** Kanonda bir boşluk vardı: Kırılma 2'de kitabe boştur, ama sonlardan önce "kitabenin dolu mu boş mu olduğu meydandan görülür". Karar: kırk yıl kitabeyi boşaltır (saatçi unutmuştur); ebe adı söyler; ad duvara yazılırsa kitabe boş kalır ve baba hiçbir çağda anılmaz; yazılmazsa terk çağında kitabe dolu okunur. Adın nasıl geri geldiği söylenmez. Kodda: `GameState.CommitFortyYears`, `GameState.GiveName`, `GameState.ExitRing`.

**K-18 Flow oyun içinde (17 Ekim 2026, kullanıcının Flow üretim kapasitesiyle).** Flow en çok iki yerde zaman kazandırır: modellemeden önceki referans ve oyuncunun odağında olmayan arka plan ve doku katmanları. Karakterler, yazı, ses ve bulmacanın odağı insan işi kalır; oyunun kimliği bunlarda ve niş kitlenin yapay zekâ hassasiyeti en çok bunlarda. Bu çizgi Steam bildirimini "arka plan resimleri ve bazı doku katmanları" ile sınırlar. Her oyun içi çıktı bir manifest satırı taşır; tepki gelirse B sınıfı listeden tek tek değiştirilebilir. Açılış kareleri için illüstratör artık sıfırdan değil Flow ilk geçişinin üstüne boyar: daha ucuz ve daha hızlı; bildirim bunu dürüstçe söyler. Rehber: `02-sanat-kitabi/flow-oyun-ici-varliklar.md`; araçlar: `tools/flow/flow.sh`.

**K-19 İnanç çağrışımı (17 Ekim 2026, kullanıcı yönergesi).** Dünya kitabı tasavvuf kavramlarını yapı olarak kullanır ve hiçbir inancı doğrulamaz ya da yalanlamaz. Bu karar o ilkeyi bir adım ileri taşır: oyun hiçbir inanç topluluğuna kaymaz, özellikle Alevi-Bektaşi geleneğine. Tarama dört gerçek risk buldu ve dördü de giderildi: ad ("Kırk Dem" → "Kırk Oda"), nesne adı ("dem" → "kor"), anlatıcı ("âşık gibi" → masalcı, sazsız, ezgisiz) ve "kırk oda + makam" ikilisi ("makam" yalnız müzik anlamında kalır, hiçbir yerde "kırk makam" kurulmaz, oyunda adı geçmez). Kalıcı güvence: oyuncunun gördüğü her metin `localization/oyuncu-metni.csv` dosyasında tutulur ve her PR'da yasak sözcük denetiminden geçer (`tools/metin-denetimi`). Ayrıntı: `docs/09-inanc-cagrisim-denetimi.md`.

**K-17 Kaynak dosyalar.** Unity projelerinde ikili dosyalar depoyu hızla şişirir. Oyuna giren dışa aktarımlar (fbx, png, wav, ogg) LFS ile izlenir; kaynak dosyalar (`.blend`, ham kayıtlar, DaVinci projeleri) depoya girmez, iki ayrı yerde yedeklenir.

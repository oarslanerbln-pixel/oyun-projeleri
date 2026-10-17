# ADR 0009 — Geri sarma ve çift akış: fizik tekrarı değil, yazılmış zaman çizelgesi

Durum: Kabul edildi (acımasız analiz, `docs/05-acimasiz-analiz.md` madde T1).

## Bağlam

Su halkası dioramayı ileri akıtıp geri sarar; Gölge halkası ışıkta ileri, gölgede geri akan iki zaman tutar ve oyuncu kendi başka yaşıyla aynı odada iş görür. Bu iki halka projenin en yüksek teknik riskidir: fizik tabanlı geri sarma (her cismin her karedeki durumunu kaydedip tersten oynatmak) tek kişilik stüdyoda hata kaynağı, bellek yükü ve belirsiz davranış demektir. Dünya kitabı odaların "aynı dioramanın tek bir değişkeni" olduğunu söyler; bu, çözümü verir.

## Karar

1. **Su'da geri sarma bir zaman çizelgesidir.** Her Su odasının dioraması yazılmış bir `Timeline` (ya da Core'daki `RoomTimeline`: normalize zaman 0..1 → anahtar durumlar) ile tanımlanır. Gelgit bu çizelgenin `t` değerini ileri ve geri sürer. Fizik yoktur; testi, kapı, su seviyesi, çark parçası gibi her nesne `t`'nin bir fonksiyonudur. Oyuncunun yaptığı değişiklik çizelgeye "dal" olarak yazılır: `t` geriye sarılınca dal silinir, ileri sarılınca oyuncunun seçtiği dal oynar. R2-03 ve R2-04 ("saatçi sarılmaz / sarılır") yalnız saatçinin transformunun çizelgeye bağlı olup olmamasıdır.
2. **Gölge'de bekçi, oyuncunun kaydıdır.** Oyuncunun ışıklı taraftaki transform ve etkileşim girdisi odaya girişten itibaren kaydedilir (`InputRecorder`, kare başına 1 örnek, en çok 10 dk). Gölgedeki "öbür yaştaki saatçi" bu kaydın tersten oynatılmasıdır; görünümü yaş varyantıdır. Böylece "kendinle karşılaşmak" ayrı bir yapay zekâ gerektirmez. R4-04 (iki uçtan aynı kapıya) kaydın ters oynatımı ile canlı girdinin aynı kapı tetikleyicisine aynı anda dokunmasıdır.
3. **Ayna'da kayıt değişikliği bir komuttur.** Her değişiklik `RecordEdit { recordId, before, after }` olarak `GameState`'e yazılır; kasaba sahnesi bu listeyi okuyup mezar taşı/fotoğraf/defter/kitabe varlıklarını günceller. R5-04'ün "geri alma"sı listeden bir komutu silmektir. Kitabe harfi = liste uzunluğu.
4. **Nefes'te durma, `Time.timeScale` değildir.** Dünya, odaya özel bir `WorldClock` ile ilerler; nefes tutulunca yalnız bu saat durur, saatçi ve kamera kendi saatlerinde kalır. Böylece ses, animasyon ve parçacıklar tek bir noktadan durdurulur ve "köpek durmaz" (R3-05) istisnası tek satırdır.

## Sonuçlar

- Dört halkanın tekniği tek bir soyutlamaya iner: **her odanın bir `t` ekseni vardır, nesneler `t`'nin fonksiyonudur, oyuncu `t`'yi ya da dalı değiştirir.** Oda kiti bunu `RoomTimeline` bileşeniyle taşır.
- Dikey dilim (K1) bu soyutlamayı Toprak'ta değil, Su ve Gölge'den birer gri kutu odayla kanıtlamak zorundadır (`docs/04-calisma-yontemi.md`, K1).
- Fizik yalnız saatçinin yürüyüşü ve köpek için kalır; hiçbir bulmaca fiziğe dayanmaz.
- Bedel: tasarımcı her odanın çizelgesini elle yazar. Bu zaten odanın tanımıdır; "tek değişken" ilkesi çizelgeyi kısa tutar.

# platform/sablonlar/tek_cizgi

Kısa marka videosu şablonu (6–15 sn): düz zemin üstünde **hiç kopmayan tek bir çizgi** şekilden şekle, sayıdan sayıya dönüşür. Çizgi ekranın solundan girip sağından çıkar, ortada düğümlenerek ürünü, rakamı ya da logoyu çizer. Tek bir senaryo dosyasından görüntü, kalem sesi, efektler, sentez müzik ve seslendirme aynı anlara kilitli üretilir. Ücretli bir servis gerekmez. Her kare `t` anının saf fonksiyonudur (10 sn'lik 9:16 video yaklaşık 12 sn'de çıkar).

```sh
T=platform/sablonlar/tek_cizgi/tek_cizgi.py
python3 $T denetle   ornekler/hamurkar-firin/tek-cizgi.json
python3 $T seslendir ornekler/hamurkar-firin/tek-cizgi.json          # platform/ses (Piper fahrettin); --saglayici elevenlabs --ses <id>
python3 $T kare      ornekler/hamurkar-firin/tek-cizgi.json --an 1.0 4.5 --format 16x9   # önizleme PNG
python3 $T render    ornekler/hamurkar-firin/tek-cizgi.json          # → cikti/<kimlik>-9x16.mp4 + <kimlik>-kapak.png
```

Format verilmezse senaryonun `format` listesi kullanılır, o da yoksa yalnız `9x16` üretilir (`16x9`, `1x1`, `4x5` da var). Gerekenler: `pip install skia-python numpy soundfile` (scipy varsa ses filtreleri hızlanır), ffmpeg ve Inter yazı tipi (Linux'ta `apt-get install libegl1 libgl1 fonts-inter`; başka bir klasör için `TEK_CIZGI_FONT_DIZINI`). `denetle` yalnız standart kütüphaneyle çalışır.

Senaryo dosyasının adı bilerek `senaryo.json` değil: CI `ornekler/*/senaryo.json` dosyalarını kinetik şablonla denetliyor.

## Senaryo

```json
{
  "kimlik": "hamurkar-kitlik", "sure": 10, "fps": 30, "format": ["9x16"],
  "palet": {"zemin": "#F6EFE3", "murekkep": "#2B211C", "vurgu": "#D9532B", "kapanis": "#F2C14E"},
  "muzik": {"bpm": 96},
  "seslendirme": {"satirlar": [{"id": "v0", "t": 0.30, "metin": "Her sabah, sadece elli kruvasan."}]},
  "sahneler": [
    {"bas": 0, "sekil": "kruvasan"},
    {"bas": 3.0, "sayac": {"degerler": [50, 38, 24, 12, 3], "bitis_t": 4.25}, "renk": "vurgu", "yazi": {"metin": "kaldı", "t": 4.45, "renk": "vurgu"}},
    {"bas": 8.0, "sekil": "basak", "zemin": "kapanis", "olcek": 0.62, "y": 0.36, "baslik": {"metin": "Hamurkâr", "t": 8.35}}
  ]
}
```

Her sahne çizginin aldığı **tek bir biçimdir** ve şu üçünden tam birini taşır:

| Alan | Ne yapar |
| --- | --- |
| `sekil` | Kütüphaneden bir şekil (`kruvasan`, `fincan`, `tabak`, `basak`, `saat`, `canta`, `kase`, `sapka`, `kalp`; `kase` buharlı çorba kâsesi, `sapka` aşçı şapkası) ya da kendi SVG yol verin (`"M 0 100 C …"`, 0–100 kutusunda, M L H V C S Q T Z). Birden çok alt yol düz çizgilerle birleştirilir; en temiz sonuç için yolu tek parça, alt kenarda başlayıp alt kenarda bitecek şekilde çizin. Marka logosu bu yolla girer. |
| `sayi` | Rakamları tek çizgiyle yazar (`"50"`). Her rakamın yönü, bağlantılar kısa olacak ve hiçbir bağlantı bir rakamın gövdesini kesmeyecek şekilde otomatik seçilir. |
| `sayac` | `degerler` listesini `bas` ile `bitis_t` arasında geri sayar. Aralıklar giderek kısalır (kıtlık hissi). Son değer büyür, sahnenin `renk` rolünü alır, inişte kamera hafifçe öne iter ve tok bir vuruş çalar. |

Ortak alanlar: `bas` (dönüşümün başladığı an; ilk sahnede çizgi soldan çizilerek gelir), `renk` (çizginin rolü, varsayılan `murekkep`), `zemin` (farklıysa şeklin merkezinden düz renk bir daire açılır), `olcek`, `y` (şeklin dikey merkezi, yüksekliğin oranı), `yazi` / `baslik` / `alt` (`{metin, t, renk}`; taban çizgisinin altında belirir; `baslik` ve `yazi` birlikte verilirse yazı başlığın altına iner, uzun yazı ekran genişliğinin %86'sına sığacak kadar küçülür). `renk` ve yazı rengi `zemin` rolü de olabilir: altın kapanış zemininde siyah çizgi gibi. Bütün anlar videonun başından itibaren saniyedir. Dönüşüm 0,62 sn sürer; ortasında çizgi düğümlenmeden akıcı bir kavise yumuşar ve ip gibi kıvrılarak yeni biçimini alır.

Görsel kurallar şablonun içinde: zemin her zaman düz renktir (gradyan, parlama ya da bantlaşma yok), çizgi yuvarlak uçlu ve kenar yumuşatmalıdır, ekranda az yazı vardır. Marka değişince yalnız palet ve şekiller değişir.

## Ses

- **Müzik:** 96 BPM sıcak e-piyano ve pad ile sakin girer. `muzik.yukselis` anında (varsayılan: sayaç sahnesi) marimba arpeji, yumuşak kick, shaker ve bas girer; `muzik.sakin` anında (sonraki sahne) yeniden piyanoya iner; `muzik.final` anında (son sahne) çanlar ve hafif ritimle parlak bir akorla kapanır.
- **Kalem sesi:** Çizginin o anki hızından üretilir. Çizgi durunca susar, dönüşümde hafifçe duyulur. Bilerek kısık tutuldu.
- **Efektler:** Sayaç tıkları, iniş vuruşu, dönüşüm nefesi, yazı ve logo çınlaması zaman çizelgesinden (`zaman.ses_olaylari`) gelir.
- **Seslendirme:** `cikti/seslendirme/<id>.wav`. Müzik konuşmanın yaklaşık 8 dB altında durur, konuşurken 3 dB daha kısılır.
- **Master:** 16 kHz alçak geçiren, -14 LUFS, tepe sınırlayıcı (kinetik şablonla aynı zincir).

## Örnek: Hamurkâr Fırın (hayali marka)

`ornekler/hamurkar-firin/tek-cizgi.json`: fırın ve kafeler için 10 sn'lik reklam, **kıtlık + kayıp kaçınma** ilkesiyle. İnsanlar bir şeyi kazanmaktan çok kaybetmekten etkilenir ve az bulunan şeye daha çok değer verir. Video bu yüzden önce sınırı koyar ("her sabah sadece elli"), sonra azalmayı gösterir (50'den 3'e hızlanan sayaç), sonra kaybı somutlaştırır ("geç kalan sadece kokusunu alır", boş tabak) ve kapanışta tek bir eylem bırakır (saat 07:00).

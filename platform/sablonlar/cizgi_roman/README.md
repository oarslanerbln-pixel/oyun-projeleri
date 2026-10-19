# platform/sablonlar/cizgi_roman

Kısa video şablonu (6–15 sn): **dikey bir çizgi roman sayfası** (webtoon). Kamera sahneler arasında sayfayı aşağı kaydırır; her sahne bir ya da iki panelden oluşur. Kalın mürekkep konturu, düz baskı renkleri, Ben-Day noktaları, hız çizgileri, patlama balonları, panel çerçevesini kıran büyüme oku ve konuşma balonu. Tek bir senaryo dosyasından görüntü, efektler, sentez müzik ve seslendirme aynı anlara kilitli üretilir. Ücretli bir servis gerekmez. Her kare `t` anının saf fonksiyonudur (10 sn'lik 9:16 video yaklaşık 15 sn'de çıkar).

```sh
T=platform/sablonlar/cizgi_roman/cizgi_roman.py
python3 $T fontlar                                                    # Bangers (SIL OFL) → ~/.cache/studyo/fonts
python3 $T denetle   ornekler/kucuk-aliskanliklar/cizgi-roman.json
python3 $T seslendir ornekler/kucuk-aliskanliklar/cizgi-roman.json    # platform/ses (ElevenLabs; anahtar/kredi yoksa Piper yedeği); --ses <voice_id>
python3 $T kare      ornekler/kucuk-aliskanliklar/cizgi-roman.json --an 1.6 4.9 --format 16x9   # önizleme PNG
python3 $T render    ornekler/kucuk-aliskanliklar/cizgi-roman.json    # → cikti/<kimlik>-9x16.mp4 + <kimlik>-kapak.png
```

Format verilmezse senaryonun `format` listesi kullanılır, o da yoksa yalnız `9x16` üretilir (`16x9`, `1x1`, `4x5` da var). Gerekenler: `pip install skia-python numpy scipy soundfile`, ffmpeg (Linux'ta skia için `apt-get install libegl1 libgl1`). Yazı tipi depoya girmez; başka bir klasör için `CIZGI_ROMAN_FONT_DIZINI`. `denetle` yalnız standart kütüphaneyle çalışır.

Senaryo dosyasının adı bilerek `senaryo.json` değil: CI `ornekler/*/senaryo.json` dosyalarını kinetik şablonla denetliyor.

## Senaryo

```json
{
  "kimlik": "ornek", "sure": 10, "fps": 30, "format": ["9x16"],
  "palet": {"yesil_nokta": "#7CC95C"},
  "muzik": {"bpm": 120},
  "seslendirme": {"satirlar": [{"id": "v0", "t": 0.30, "metin": "Her gün, sadece yüzde bir daha iyi ol."}]},
  "sahneler": [
    {"bas": 0, "paneller": [{
      "zemin": "sari", "nokta": "turuncu", "hiz_cizgileri": {"t": 0.8},
      "anlati": {"metin": "HER GÜN...", "t": 0.25},
      "ogeler": [{"tur": "patlama", "t": 1.35, "metin": "%1"}]}]}
  ]
}
```

**Sahne** = sayfada bir ekranlık yer. `bas` anının çevresinde (0,5 sn) kamera bir sonraki sahneye kayar. `paneller` bir ya da iki panel alır; iki panel dikey formatta üst üste, yatay formatta yan yana bölünür (`bolme`: küçük panelin oranı, varsayılan 0,34).

**Panel** alanları: `zemin` (palet rolü), `nokta` (Ben-Day nokta rengi) ve `nokta_yon` (`asagi`, `yukari`, `duz`), `nokta_guc` (en büyük yarıçap), `nokta_bas` (noktaların başladığı yükseklik oranı), `hiz_cizgileri` (`{t, renk, x, y, r, donus}`; `t` verilirse çizgiler o anda içeri kapanır), `anlati` (sol üstte soldan kayan anlatıcı kutusu, `{metin, t}`), `egim` (üst kenar eğik), `vurus` (panel o anda sarsılır ve hafifçe öne çıkar).

**Öğeler** panelin içinde oranla yerleşir (`x`, `y`: 0–1) ve panelin kısa kenarına göre ölçeklenir (1000 px'lik kenar = 1; `olcek` ile çarpılır). Her öğenin `t` anı vardır; renk alanları palet rolüdür.

| `tur` | Ne yapar | Başlıca alanlar |
| --- | --- | --- |
| `yazi` | Bangers harfli başlık; `carp` girişinde ekrana düşer ve sarsar | `metin`, `renk`, `boy`, `derinlik` (kabartma), `kontur`, `hiza`, `aci`, `giris` (`carp`, `pop`, `yok`) |
| `patlama` | Yıldız patlaması ve içinde yazı ya da sayaç | `metin` **ya da** `sayac: {degerler: [1, 37], bitis_t}`, `son_ek`, `renk`, `zemin`, `r`, `boy` |
| `takvim` | Yaprakları koparak sayan takvim, sonra uçar | `bitis_t`, `degerler: [ilk, son]`, `cikis_t`, `renk` |
| `buyume_oku` | Üstel büyüyen ok ve altında sütunlar; ucu panel çerçevesini kırar | `bitis_t`, `baslangic`, `bitis` (panel oranı), `sutun`, `cerceveyi_kir` |
| `filiz` / `agac` | Saksıda filiz; meyveli ağaç ve çimen bandı | renk rolleri (`saksi`, `yaprak`, `tac`, `golge`, `meyve`, `cimen`…) |
| `kahraman` | Yumruğu havada büst karakter; alttan yükselir | `yumruk_t`, `goz_kirp_t`, `tisort`, `ten`, `sac` |
| `balon` | Konuşma balonu (1–3 satır) | `satirlar: [{metin, renk}]`, `boy`, `kuyruk: [dx, dy]` |
| `gorsel` | Marka logosu ya da ürün görseli, beyaz kartta | `yol` (senaryoya göre), `genislik` (panel oranı), `kart` |

**Format ayarı:** Her sahne, panel ya da öğe `"16x9": {…}` gibi bir format anahtarı taşıyabilir; o formatta oradaki alanlar geçerli olur (ör. yatayda balonu karakterin yanına almak için `{"x": 0.27, "olcek": 0.85}`).

Görsel kurallar şablonun içinde: degrade, parlama ya da bulanıklık yok; ton farkı nokta boyuyla verilir, her şey kenar yumuşatmalı vektördür.

## Ses

- **Müzik:** 120 BPM funk/pop-rock (davul, testere bas, bakır üflemeliler). İlk vuruşa kadar gerilim (hızlanan hihat, yükselen bas), `muzik.yukselis` anında tam groove, `muzik.sakin` anında yalnız tıkırtı ve uzun bas, `muzik.final` anında tam groove ve üç basamaklı bakır kapanışı. Varsayılan bölümler sahnelerden gelir (2., 3. ve son sahne).
- **Vuruşlar:** Çarpan yazılar, patlamalar, ağaç ve panel `vurus` anları aynı listeden (`zaman.vuruslar`) hem görüntüde sarsıntı hem seste bakır akoru, kick ve tok darbe olur. Sayaçlı patlamadan önce bakır yükselir.
- **Efektler:** sayfa kayması, sayaç tıkları, takvim yaprakları, balon ve filiz pop'u, yumruk savruluşu (`zaman.ses_olaylari`).
- **Seslendirme:** `cikti/seslendirme/<id>.wav`. Müzik konuşmanın yaklaşık 8 dB altında durur, konuşurken 3 dB daha kısılır.
- **Master:** 16 kHz alçak geçiren, -14 LUFS, tepe sınırlayıcı (öteki şablonlarla aynı zincir).

## Örnek

`ornekler/kucuk-aliskanliklar/cizgi-roman.json`: stil testindeki 10 sn'lik "küçük alışkanlıklar" webtoon'u (aynı satırlar ve anlar). Yatay format için balon, kahraman ve patlamalarda `16x9` ayarları var.

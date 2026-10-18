# platform/sablonlar/oyuncak

Pastel 3D "oyuncak dünya" şablonu (6–20 sn): yuvarlak bir kahraman spiral üzerine dizilmiş kolonları tırmanır. Birkaç sakin adımla başlar, kolonlar dalga halinde üstel olarak yükselir, kahraman doruğa koşar ve büyük sayı konfetiyle belirir. Ardından kamera küçük ilk adımdan dev kuleye çıkar, kapanışta kahraman ilk adıma geri zıplar. "Küçük alışkanlık → büyük sonuç" türü kişisel gelişim ve marka mesajları için.

Tek bir `oyuncak.json` dosyasından görüntü (three.js, başsız Chromium), sentez müzik, efektler ve seslendirme aynı anlara kilitli üretilir. Ücretli bir servis gerekmez. Her kare `t` anının saf fonksiyonudur.

```sh
O=platform/sablonlar/oyuncak/oyuncak.py
(cd platform/sablonlar/oyuncak && npm install)                       # three + playwright (bir kez)
python3 $O denetle   ornekler/kucuk-aliskanliklar/oyuncak.json
python3 $O seslendir ornekler/kucuk-aliskanliklar/oyuncak.json       # platform/ses (Piper fahrettin); --saglayici elevenlabs --ses <id>
python3 $O kare      ornekler/kucuk-aliskanliklar/oyuncak.json --an 1.6 4.8 7.5 --format 16x9   # önizleme PNG
python3 $O render    ornekler/kucuk-aliskanliklar/oyuncak.json --format 9x16 16x9               # → cikti/<kimlik>-<format>.mp4
```

Gerekenler: Node.js 18+, `npm install` (three 0.170, playwright 1.56; Chromium yoksa `npx playwright install chromium`, ya da `CHROMIUM` ortam değişkeniyle var olan bir Chromium), `pip install numpy soundfile`, ffmpeg ve Inter yazı tipi (`apt-get install fonts-inter`; başka bir klasör için `OYUNCAK_FONT_DIZINI`, yoksa DejaVu Sans Bold'a düşer). `denetle` yalnız standart kütüphaneyle çalışır. Formatlar: `9x16` (varsayılan), `16x9`, `1x1`, `4x5`.

Render süresi: GPU'suz bir bulut makinesinde (4 çekirdek, SwiftShader) 10 sn'lik bir format yaklaşık 5–6 dakika; GPU'lu bir makinede Chromium donanım WebGL'i kullanır ve çok daha hızlıdır.

## Senaryo

```json
{
  "kimlik": "kucuk-aliskanliklar-oyuncak", "sure": 10, "fps": 30,
  "palet": {"kahraman": "#FF6B5B", "kolon_bas": "#5CC9B5", "kolon_orta": "#7DA7F0", "kolon_son": "#FFC94A"},
  "muzik": {"bpm": 120, "ilk_vurus": 0.1},
  "kolonlar": {"adet": 52, "oran": 37.4},
  "seslendirme": {"satirlar": [{"id": "v0", "t": 0.30, "metin": "Her gün, sadece yüzde bir daha iyi ol."}]},
  "sahneler": [
    {"tur": "adimlar", "bas": 0, "ziplamalar": [1.1, 2.3], "yazi": {"metin": "%1", "t": 1.45, "son_t": 2.85}},
    {"tur": "buyume", "bas": 3.1, "doruk_t": 4.6, "yazi": {"metin": "37×"}, "kutlama": [4.95, 5.45]},
    {"tur": "karsitlik", "bas": 6.1, "vinc_t": 6.72, "kutlama": [7.0]},
    {"tur": "kapanis", "bas": 8.1, "inis_t": 8.36, "zipla_t": 8.68, "yazi": {"metin": "Bugün başla.", "t": 8.72}}
  ]
}
```

Bütün anlar videonun başından itibaren saniyedir. Bir sahne bir sonrakinin `bas` anına kadar sürer. Sahneler bu sırayla gelir; `adimlar` ve `buyume` zorunlu, `karsitlik` ve `kapanis` isteğe bağlıdır.

| Sahne (`tur`) | Ne olur | Alanlar |
| --- | --- | --- |
| `adimlar` | Yakın, sakin plan. Kahraman ilk kolonda durur; her zıplamadan 0,35 sn önce yanında yeni kolon çıkar. | `ziplamalar` (1–4 an), `yazi` (en çok 8 karakter, adımların üstünde; `t` belirir, `son_t` kaybolur) |
| `buyume` | Kamera geri çekilip döner, kalan kolonlar dalga halinde yükselir, kahraman tepe tepe koşar; `doruk_t` anında son kolona varır, yazı konfetiyle belirir, ışık parlar. | `doruk_t`, `yazi` (en çok 8 karakter, `doruk_t`'de belirir, kapanışa kadar kalır), `kutlama` (tepede sevinç zıplamaları) |
| `karsitlik` | Kamera ilk küçük kolona alçaktan bakar, `vinc_t` anında dev kuleye doğru yükselir. | `vinc_t`, `kutlama` |
| `kapanis` | Gökyüzü aydınlanır; kahraman gökten iner (`inis_t`), ilk kolona zıplar (`zipla_t`), yazı belirir. | `inis_t`, `zipla_t`, `yazi` (en çok 18 karakter) |

`kolonlar.adet` (8–120) spiraldeki kolon sayısı, `kolonlar.oran` (1,5–100) son kolonun ilkine oranıdır; yükseklikler arada üstel artar (52 hafta ve 37,4 = 1,01³⁶⁴). Yazılar 3D olarak kabartılır ve sığmadıkları genişlikte küçültülür.

Renkler rollerle verilir: `gok_ust`, `gok_alt` (gökyüzü degradesi), `gok_ust_son`, `gok_alt_son` (kapanıştaki aydınlık gökyüzü), `ada`, `kahraman`, `kolon_bas`, `kolon_orta`, `kolon_son` (kolon degradesi), `yazi_yuz`, `yazi_yan` (adım ve kapanış yazısının yüzü ve kenarı), `doruk_yuz`, `doruk_yan` (doruk yazısı). Verilmeyen roller varsayılanı alır.

## Görüntü

`sahne.js` three.js sahnesidir: degrade gökyüzü, yüzen ada, yumuşak gölgeli güneş ışığı, oda ortamından yansımalar, ACES ton eşleme. Kolonlar yuvarlatılmış kutulardır, kahraman gözleri kırpan, basılıp uzayan (squash & stretch) bir küredir. Kamera her formatta aynı çerçeveyi verecek şekilde en dar görüş açısına göre uzaklaşır; dikey format yukarı ve aşağı fazlasını görür. `render.mjs` sahneyi başsız Chromium'da kare kare çizer ve PNG akışını ffmpeg'e verir. Anlar Python'da `zaman.cizelge()` ile türetilir ve sahneye ayar dosyasıyla geçer; görüntü ve ses aynı tablodan okur.

## Ses

- **Müzik:** `bpm` ızgarasında (ilk vuruş `ilk_vurus`) pad, bas ve marimba/çan arpeji. Enerji eğrisi: adımlarda sakin, büyümede sekizlik ve on altılıklara hızlanan arpej, yükselen gürültü süpürmesi ve tekme; dorukta alt bas düşüşü ve zil, karşıtlıkta sakin, kapanışta parlak akor ve çanlar. Altı akor `muzik.akorlar` ile değişir (adımlar, yükseliş, doruk, karşıtlık vinçten önce/sonra, kapanış).
- **Efektler:** kolon çıkışı (pop), zıplama (boing), iniş (tok), dalganın yükselen tıkırtıları, kamera süpürmesi, konfeti çıtırtısı, yazı belirişi.
- **Seslendirme:** `cikti/seslendirme/<id>.wav` dosyalarından okunur. Müzik konuşmanın yaklaşık 8 dB altında, konuşurken 3 dB daha kısılır.
- **Master:** 16 kHz alçak geçiren, -14 LUFS, tepe sınırlayıcı.

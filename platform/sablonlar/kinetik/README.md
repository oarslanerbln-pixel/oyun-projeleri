# platform/sablonlar/kinetik

Kısa sosyal video şablonu (6–15 sn): düz renkli hareketli grafik ve ritme oturan kinetik tipografi. Tek bir `senaryo.json` dosyasından görüntü, ses efektleri, sentez müzik ve seslendirme aynı anlara kilitli üretilir. Ücretli bir servis gerekmez. Tek kare `t` anının saf fonksiyonudur, bu yüzden render tekrarlanabilir (10 sn'lik iki format yaklaşık 20 sn sürer).

```sh
K=platform/sablonlar/kinetik/kinetik.py
python3 $K denetle   ornekler/kucuk-aliskanliklar/senaryo.json
python3 $K seslendir ornekler/kucuk-aliskanliklar/senaryo.json          # platform/ses (ElevenLabs; anahtar/kredi yoksa Piper yedeği); --ses <voice_id>
python3 $K kare      ornekler/kucuk-aliskanliklar/senaryo.json --an 1.5 4.9 --format 16x9   # önizleme PNG
python3 $K render    ornekler/kucuk-aliskanliklar/senaryo.json          # → cikti/<kimlik>-9x16.mp4, -16x9.mp4
```

Gerekenler: `pip install skia-python numpy soundfile`, ffmpeg ve Inter yazı tipi (Linux'ta `apt-get install libegl1 libgl1 fonts-inter`; başka bir klasör için `KINETIK_FONT_DIZINI`). Yazı tipleri depoya konmaz, çünkü depo ikili dosyaları LFS'e gönderir. `denetle` yalnız standart kütüphaneyle çalışır.

## Senaryo

```json
{
  "kimlik": "kucuk-aliskanliklar", "sure": 10, "fps": 30,
  "palet": {"zemin": "#15122E", "vurgu": "#FFD23F", "ikinci": "#FF5A5F", "ucuncu": "#3DDC97", "acik": "#FFF8E7"},
  "muzik": {"bpm": 120, "akorlar": [[60, 64, 67, 72], [57, 60, 64, 69]]},
  "seslendirme": {"satirlar": [{"id": "v0", "t": 0.30, "metin": "Her gün, sadece yüzde bir daha iyi ol."}]},
  "sahneler": [{"tur": "kelimeler", "bas": 0, "kelimeler": [{"metin": "HER", "t": 0.34}]}, "…"]
}
```

Bütün anlar videonun başından itibaren saniye cinsinden verilir. Bir sahne bir sonrakinin `bas` anına kadar sürer. Kelime anlarını seslendirmedeki vurgulu hecelere oturtmak, videonun izlenmesini sağlayan asıl şeydir: `seslendir` komutu her satırın süresini `seslendirme.json` dosyasına yazar, `denetle` de satırların birbirine taşmasını yakalar.

| Sahne (`tur`) | Zemin | Alanlar |
| --- | --- | --- |
| `kelimeler` | zemin | `kelimeler[{metin, t, renk}]`, `acilis` (ilk sahnede açılış topu, varsayılan açık), `punto`, `gorsel{dosya, t, genislik}` (gerçek ürün fotoğrafı, saydam PNG: halkayla döne döne iner; kelimeler üste, yatayda sola geçer; fotoğraf kendi çözünürlüğünden büyütülmez) |
| `buyuk-sayi` | vurgu | `ust`, `ust_t`, `sayi`, `sayi_t` (bas efekti; "16,90 €" gibi uzun bir fiyat küçülmez, halka büyür), `etiket`, `etiket_t` |
| `egri` | zemin | `baslangic_t`, `zirve_t`, `oran`, `gun` (bileşik büyüme; sayaç `(1+oran)^gun` değerine çıkar), `eksen`, `sayac`, `rozet` |
| `karsitlik` | üçüncü + ikinci | `kucuk`, `kucuk_t`, `panel_t`, `buyuk`, `buyuk_t` (dikeyde üst/alt, yatayda sol/sağ) |
| `kapanis` | vurgu | `satirlar[{metin, t, renk}]` (hepsi aynı boyda), `cizgi_t`, `alt`, `alt_t`, `logo{dosya, t, boy}` (saydam PNG; dikeyde üstte, yatayda solda dönerek oturur, yazılar yer açar) |

Sahneye giriş geçişi (`gecis`): `iris` (önceki sahnenin odak noktasından yeni zeminin rengiyle açılır, 0,28 sn), `diyagonal` (önceki sahne yakınlaşır, yükselen sesle birlikte ikinci renkte bir perde ekranı kaplayıp çekilir, ritim bu noktada tam girer), `kesme`.

Renkler rollerle verilir (`zemin`, `vurgu`, `ikinci`, `ucuncu`, `acik`). Marka değişince yalnız palet değişir. Uzun yazılar sahneye sığacak şekilde otomatik küçülür. Ondalık ayıracı `ondalik` alanından gelir (varsayılan `,`).

## Ses

- **Müzik:** `bpm` hızında arpej, pad ve hi-hat çalar. Tam ritim (kick, clap, pompalayan bas) `muzik.dusus` anında, verilmediyse ilk diyagonal geçişte girer. Geçişlerden hemen önce kick ve bas susar.
- **Efektler:** Her kelime çarpması, sayı, geçiş ve sayaç tıkı zaman çizelgesinden (`zaman.ses_olaylari`) üretilir. Kamera sarsıntısı da aynı anlarda vurur (`zaman.darbeler`).
- **Seslendirme:** `cikti/seslendirme/<id>.wav` dosyalarından okunur. Konuşma sırasında müzik yaklaşık 8 dB kısılır.
- **Master:** 16 kHz alçak geçiren filtre, ardından -14 LUFS ve tepe sınırlayıcı uygulanır. AAC kodlamasından sonra gerçek tepe 0 dBFS'i aşmaz.

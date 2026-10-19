# platform/sablonlar/analiz

Analiz ve haber anlatımı şablonu (30–90 sn): veri gazeteciliği görünümünde grafikler, sayaçlar, harita ve zaman çizelgesi, üstüne seslendirme ve müzik. Tek bir `analiz.json` dosyasından görüntü, efektler, müzik ve seslendirme aynı anlara kilitli üretilir. Ücretli bir servis gerekmez; 60 sn'lik 16:9 video yaklaşık 40 sn'de çıkar.

```sh
A=platform/sablonlar/analiz/analiz.py
python3 $A denetle   ornekler/fransa-ekim-2026/analiz.json
python3 $A seslendir ornekler/fransa-ekim-2026/analiz.json          # platform/ses (ElevenLabs; anahtar/kredi yoksa Piper yedeği); --ses <voice_id>
python3 $A kare      ornekler/fransa-ekim-2026/analiz.json --an 3 12 --format 9:16   # önizleme PNG
python3 $A render    ornekler/fransa-ekim-2026/analiz.json          # → cikti/<kimlik>-16x9.mp4
python3 $A uret      ornekler/fransa-ekim-2026/analiz.json          # seslendirme eksikse üretir, sonra render
```

Format sırası: `--format` (`16:9`, `9:16`, `1:1`, `4:5`, `ikisi`), yoksa senaryonun `format` alanı, o da yoksa 16:9. İki format ancak `ikisi` ile birlikte çıkar.

Gerekenler: `pip install skia-python numpy soundfile` (seslendirme için `sherpa-onnx`), ffmpeg ve Inter yazı tipi (Linux'ta `apt-get install libegl1 libgl1 fonts-inter`; başka bir klasör için `ANALIZ_FONT_DIZINI`). `denetle` yalnız standart kütüphaneyle çalışır.

## Kurallar

- **Her sayı senaryodan gelir.** Ekrandaki bütün değerler `deger` alanlarındadır ve sayı olmak zorundadır. Sayı gösteren her sahnede `kaynak` zorunludur ve alt bantta görünür; `denetle` eksik kaynağı hata sayar.
- **Doğrulanamayan bilgi girmez.** Kaynaklar çelişiyorsa (ör. gözaltı sayıları) o bilgi videoya konmaz. Kaynak listesini ve linklerini video ile birlikte teslim edin.
- **Temiz görüntü.** Zeminler düz renktir; degrade, parlama ya da metin arkasında halka yoktur. Tahmin verisi kesikli çizgi ve yarı saydam düz dolguyla ayrılır.
- **Ses.** Konuşma, müzik ve efektlerin `muzik.ses_ustu_db` (varsayılan 8 dB) üstünde tutulur; master -14 LUFS.

## Senaryo

```json
{
  "kimlik": "fransa-ekim-2026", "sure": 60, "fps": 30, "format": "16:9", "tema": "koyu",
  "seri": "Analiz", "konu": "Fransa · Ekim 2026", "tarih": "18 Ekim 2026",
  "muzik": {"bpm": 96, "akorlar": [[50, 53, 57, 62], [46, 50, 53, 58]]},
  "seslendirme": {"satirlar": [{"id": "v0", "t": 0.9, "metin": "…", "okunus": "isteğe bağlı: TTS'e giden yazım"}]},
  "sahneler": [{"tur": "baslik", "bas": 0, "baslik": "…"}, "…"]
}
```

Bütün anlar videonun başından itibaren saniyedir. Bir sahne bir sonrakinin `bas` anına kadar sürer. Öğelerin (çubuk, kart, nokta, olay) giriş anı `t` ile seslendirmedeki kelimeye oturtulur; verilmezse sahne başından kademeli girer. `okunus`, ekrana çıkmayan ama sentezin doğru okuması için yazılan metindir (ör. "Lökornü", "iki bin yirmi yedi").

| Sahne (`tur`) | Ne gösterir | Alanlar |
| --- | --- | --- |
| `baslik` | Açılış: kırmızı etiket, büyük başlık, çizgi, alt başlık; isteğe bağlı ülke silüeti | `ust`, `baslik` (`\n` ile satır), `alt`, `harita` |
| `cubuk` | Büyüyen çubuklar, sayan değerler; tahmin çubukları kesikli | `cubuklar[{etiket, deger, not, tahmin, vurgu, t}]`, `on_ek` (`%`), `ek`, `basamak`, `eksen_min`, `eksen_max` |
| `cizgi` | Kendini çizen çizgi; gerçekleşen düz, tahmin kesikli ve gölgeli bölgede | `noktalar[{etiket, deger, tahmin}]`, `cizim_t`, `cizim_sure`, `on_ek`, `basamak`, `sifirdan`, `renk` |
| `sayac` | 1–4 KPI kartı, sabit genişlikli rakamlarla sayaç | `kartlar[{etiket, deger, birim, basamak, not, vurgu, yil, baslangic, t}]` |
| `harita` | Kıyısı çizilen ülke + komşular, nabızlı noktalar, etiket kutuları, yan KPI | `noktalar[{ad, lon, lat, etiket, yon (sag/sol/ust/alt), t}]`, `kpi{deger, etiket, ekler[{baslik, metin}]}`, `kutu` [lon0, lat0, lon1, lat1], `ulke` (ISO-2) |
| `karsilastirma` | İki sayı yan yana (dikeyde alt alta), oranlı çubuk | `sol`, `sag` ({etiket, deger, not, renk, t}), `basamak` |
| `zaman` | Zaman çizelgesi; geçmiş düz, gelecek kesikli, "BUGÜN" etiketi | `olaylar[{tarih, metin, durum: gelecek, vurgu, t}]`, `bugun` (indeks) |
| `alinti` | Alıntı kartı | `metin`, `kisi`, `unvan` |
| `kapanis` | Kapanış başlığı ve kaynak listesi | `baslik`, `alt`, `kaynaklar[]` |

Hepsinde ortak: `baslik`, `alt`, `kaynak`, `enerji` (0–1, müziğin o sahnedeki yoğunluğu).

Sabit çerçeve: üst bantta seri adı, konu ve tarih; altta `KAYNAK` bandı ve sahne sayacı; en altta sahne çentikli ilerleme çizgisi. Sahne değişiminde ince bir vurgu çubuğu ekranı geçer.

## Renk ve marka

Renkler rollerle verilir: `zemin`, `panel`, `cizgi`, `metin`, `soluk`, `notr`, `vurgu`, `ikinci`, `kara` (vurgu üstündeki yazı). `tema` iki hazır palet seçer: `koyu` (lacivert-antrasit, kırmızı vurgu) ve `acik` (krem zemin). `palet` alanı tek tek rolleri ezer; marka değişince yalnız palet değişir.

## Harita

`veri/bati-avrupa.json`, Natural Earth 1:50m ülke sınırlarından (kamu malı) Batı Avrupa'yı içerir. Başka bir bölge için aynı biçimde (`halkalar: {ISO-2: [[[lon, lat], …]]}`) yeni bir dosya üretilebilir.

## Ses

- **Müzik:** `bpm` hızında, ölçü başına bir akor. Pad hep çalar; 16'lık arpej, bas, hi-hat, kick ve trampet sahnenin `enerji` değerine göre girer (varsayılanlar `muzik.VARSAYILAN_ENERJI`). Böylece sakin açılış, gerilen orta bölüm ve sakin kapanış senaryodan çıkar.
- **Efektler:** Sahne geçişinde whoosh, başlıkta alçak vuruş, çubuk/nokta/olay girişinde kısa ton, sayaçlarda yavaşlayan tıklar. Hepsi çizimle aynı anlardan hesaplanır.
- **Master:** 16 kHz alçak geçiren, -14 LUFS, tepe sınırlayıcı.

# platform/sablonlar/karakalem_anlatim

Uzun video (5–10 dk YouTube analizi) için serbest uzunlukta kurşun kalem sahneleri. `karakalem` şablonu sabit üç sahneli 8–20 sn'lik bir hikâyeye kilitli; bu şablon aynı kalemi, kâğıdı, karakteri ve yazı tiplerini kullanır ama sahneler serbesttir: her sahne bir `tip` ve `sure`, video sahnelerin toplamı kadar sürer. Tek başına render edilir ya da `kurgu.json` içinde `"stil": "karakalem_anlatim"` sahnesi olur (kurgu müziği ve geçişleri verir).

```sh
A=platform/sablonlar/karakalem_anlatim/anlatim.py
python3 $A fontlar                                           # Caveat + Permanent Marker (karakalemle ortak), bir kez
python3 $A denetle   ornekler/karakalem-anlatim/anlatim.json
python3 $A kontakt   ornekler/karakalem-anlatim/anlatim.json   # her sahnenin bitmiş hâli, tek sayfa (render yok, ~3 sn)
python3 $A kare      ornekler/karakalem-anlatim/anlatim.json --an 2.0 9.5
python3 $A seslendir ornekler/karakalem-anlatim/anlatim.json   # ElevenLabs (yedek Piper)
python3 $A render    ornekler/karakalem-anlatim/anlatim.json   # varsayılan 16x9
```

Sahneler 1600×900'lük sanal sayfada kurulur; 16:9 tam dolar, diğer formatlarda sayfa ortalanır (dikey video için henüz ayrı yerleşim yok). Her sahne önce kalemle çizilir ve yazılır (en çok 2,4 sn, kısa sahnede sürenin %55'i), sonra çizgiler saniyede 12 kez kaynar, kamera yavaşça yaklaşır, oklar ve sayaçlar yaşamaya devam eder. Kâğıt düz renk + bindirme doku; radyal gradyan ve parlama yok. Altyazı alt bantta, söylendikçe kelime kelime koyulaşır (`"altyazi": false` kapatır). Titreme `"titreme": {"fps": 4, "genlik": 0.35}` ile yavaşlar ve küçülür (varsayılan 12 fps, genlik 1); `"efekt": false` kalem ve kâğıt seslerini kapatır.

## Sahne tipleri

| Tip | Alanlar (* zorunlu, karakter sınırı) | Görünüm |
| --- | --- | --- |
| `baslik` | `metin`* 40, `ust` 24, `alt` 60 | bölüm kartı: üstte damga etiketi, el yazısı başlık ve vurgu altı çizgisi, köşe parantezleri |
| `harita` | `odak` (`avrupa`, `bati-avrupa`, `almanya`, `fransa`), `vurgulu` (ISO: `["FR","DE"]`), `sehirler` (≤10; ad listesi ya da `{"ad","boylam","enlem"}`), `oklar` `[{"den","ye","etiket" ≤16, "egrilik"}]`, `etiketler` (adı yazılacak ülkeler), `baslik` 40 | gerçek sınırlarla (Natural Earth, kamu malı) elle çizilmiş Avrupa; vurgulu ülkeler taranır, kavisli ok çizilir ve üstünden dalga geçer |
| `karakter` | `metin` 90 (konuşma balonu), `poz` (`anlat`, `dusun`, `sasir`, `isaret`, `omuz`, `sevin`), `ifade` (`normal`, `endise`, `sasir`, `gulumse`, `ciddi`), `yon` (`sol`, `sag`), `notlar` ≤3 × 30 | genç anlatıcı (görünüş senaryonun `karakter` alanından); seslendirme sürerken ağız hece hece açılır |
| `belge` | `baslik`* 34, `satirlar`* 1–6 × 44, `vurgu` (satır sırası), `damga` 16, `ust` 40, `kaynak` 40 | ataşlı kâğıt kayarak gelir, satırlar yazılır, fosforlu kalem geçer, damga vurulur |
| `kalabalik` | `metin` 50, `pankartlar` ≤5 × 14, `yogunluk` (`az`, `orta`, `cok`) | şehir silueti, üç sıra insan, pankartlar sallanır |
| `sayac` | `deger`* 8 (`%37`, `1.200`, `3,5 kat`), `etiket` 36, `ust` 28, `kaynak` 50 | sayı biçimi korunarak sayar, kalemle iki tur çevrilir |
| `terazi` | `sol`*, `sag`* 18, `egim` (-1 sol ağır … 1 sağ ağır), `soru` 40, `sol_deger`, `sag_deger` 8 | olasılık terazisi: kol sönümlü salınımla eğilir, ağır kefe vurgulu |
| `takvim` | `olaylar`* 2–6 × `{"tarih" ≤12, "metin" ≤22}`, `vurgu` (olay sırası), `baslik` 40 | zaman çizgisi; vurgulu tarih çevrilir, üstünde takvim yaprağı |

Senaryoda `"dil": "de"` (ya da `en`) şablonun kendi yazdığı sözcükleri çevirir: pusuladaki K → N, "Kaynak:" → "Quelle:", vurgulu ülke adları (Almanca tablo `cizim.SOZLUK`; tek sahnede başka ad için `"adlar": {"DE": "..."}`).

Ses: anlatım varsayılan olarak kuru ve cilalıdır (uğultu kesme, oda tınısını azaltma, netlik, kompresör, de-esser; gecikmesiz, zamanlama değişmez). Eski oda yankısı için senaryoda `"yanki": 0.12`, cilasız ham ses için `"ses_cilasi": false`. Müzik konuşmanın 16 dB altındadır ve konuşurken 6 dB daha kısılır; e-piano vuruşları konuşma sırasında ve kelime bitiminden 0,4 sn sonrasına kadar 10 dB daha kısıktır (yankı gibi duyulmasın). Ayar: `"muzik": {"alti_db": 16, "kisma_db": 6}`.

Permanent Marker'da Türkçe ğ/ş/İ yok; bu harfleri taşıyan damga yazıları kendiliğinden el yazısıyla (Caveat) yazılır.

## Senaryo

```json
{"kimlik": "dalga-almanya-karakalem", "fps": 30, "format": ["16x9"],
 "palet": {"kagit": "#F7F4EC", "grafit": "#34343A", "vurgu": "#D9541E"},
 "karakter": {"sac": "kisa", "gozluk": false, "kazak": "#D6D9DC"},
 "seslendirme": {"satirlar": [{"id": "v1", "t": 0.6, "metin": "..."}]},
 "sahneler": [{"tip": "baslik", "sure": 5.5, "ust": "Bölüm 1", "metin": "Dalga Almanya'ya mı geliyor?"},
              {"tip": "harita", "sure": 6.5, "odak": "bati-avrupa", "vurgulu": ["FR", "DE"], "sehirler": ["Paris", "Berlin"],
               "oklar": [{"den": "Paris", "ye": "Berlin", "etiket": "dalga?"}]}]}
```

Seslendirme anları videonun başından saniyedir. Ses: her sahnenin çizimi duyulan kalem, sahne girişinde kâğıt, sakin lo-fi akorlar (kurguda müziği kurgu çalar, bu şablonun yalnız `efekt.wav` kökü kullanılır). Örnek: `ornekler/karakalem-anlatim/anlatim.json` (8 sahne, 47 sn; belgedeki metin örnektir).

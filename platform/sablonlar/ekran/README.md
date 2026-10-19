# platform/sablonlar/ekran

Az yazılı, güçlü kancalar için üç "ekran" stili (4–30 sn). Üçü aynı senaryo biçimini kullanır; yalnız `stil` alanı değişir, yani bir video içerik değişmeden stil değiştirebilir.

| `stil` | Görünüm | Ses | En iyi kullanım |
|---|---|---|---|
| `kalkis-tabelasi` | Havalimanı split-flap tabelası: harfler alfabe sırasıyla takırdayarak döner, kelime oturur; altta küçük şerit, üstte isteğe bağlı `baslik` etiketi (uçak simgesiyle) | Anons çanı, her kapakta tık (sütuna göre stereo), sakin elektronik nabız | Duyuru, hedef, kanca, her videonun girişi |
| `vhs` | Kaset görüntüsü: renk kanalı kayması, tarama çizgileri, kayan iz bandı, sahne girişinde dilim kayması ve renk çubukları; sol üstte ▶ PLAY ve sayaç | Synthwave (bas, kare dalga arpej, kick/clap), kaset klak, kesik cızırtısı | Gen-Z, müzik, nostalji, enerjik giriş |
| `akis-alani` | Binlerce ipçik rüzgârla akar, harflerin çevresinden dolaşır; kenara değen ipçik vurgu rengine döner, net yazı üstüne oturur. `tema`: `gece` (koyu) ya da `kagit` (krem zemin, mürekkep) | Sinüs pedler, yumuşak rüzgâr, sahne başlarında cam çan | Sakin bölümler, kapanış, arka plan |

Çizim numpy + Pillow ile yapılır (skia gerekmez). Kalkış tabelası ve VHS karesi `t` anının saf fonksiyonudur; akış alanı bir benzetimdir, tek kare istenince 3 sn önceden ısıtılır. Zeminler düz renktir, her karede ince tane eklenir (bantlanma yok). Yazı platform güvenli alanının içinde kalır (9:16'da üstten %10, alttan %22) ve sığmazsa küçülür.

```sh
E=platform/sablonlar/ekran/ekran.py
python3 $E denetle   ornekler/kucuk-aliskanliklar/kalkis-tabelasi.json
python3 $E seslendir ornekler/kucuk-aliskanliklar/kalkis-tabelasi.json     # ElevenLabs (yoksa Piper yedeği); --ses <voice_id>
python3 $E kare      ornekler/kucuk-aliskanliklar/vhs.json --an 1.5 4.9 --format 16x9
python3 $E render    ornekler/kucuk-aliskanliklar/akis-alani.json            # → cikti/<kimlik>-9x16.mp4 (--format 9x16 16x9 1x1 4x5)
# ya da ortak giriş:
python3 platform/sablonlar/stil/stil.py uret ornekler/kucuk-aliskanliklar/vhs.json --format 9:16
```

Kurgu (uzun video) içinde sahne olarak: `{"stil": "ekran", "senaryo": "sahneler/giris-tabela.json"}`; görünüm sahne senaryosunun `stil` alanından gelir.

Gerekenler: `pip install numpy pillow soundfile`, ffmpeg, Inter yazı tipi (`apt-get install fonts-inter`); VHS ekran yazısı için DejaVu Sans Mono (yoksa Inter). `denetle` yalnız standart kütüphaneyle çalışır. 10 sn'lik video tek formatta yaklaşık 1–2 dk'da çıkar.

## Senaryo

```json
{
  "kimlik": "kucuk-adimlar-tabela", "stil": "kalkis-tabelasi", "sure": 10, "format": "9x16",
  "baslik": "Kalkış · Hedef",
  "palet": {"vurgu": "#FFC233"},
  "seslendirme": {"satirlar": [{"id": "v0", "t": 0.3, "metin": "Her gün, sadece yüzde bir daha iyi ol."}]},
  "sahneler": [
    {"bas": 0, "metin": "Her gün *%1* daha iyi", "alt": "Hedef: yeni sen"},
    {"bas": 8.2, "metin": "*Bugün* başla"}
  ]
}
```

| Alan | Anlamı |
|---|---|
| `sahneler[].metin` | Birkaç kelime. `*...*` vurgu rengi (öbek satırda bölünmez), `\n` satırı zorla böler. En çok 48 (tabela) / 40 (VHS, akış) karakter |
| `sahneler[].alt` | Küçük alt satır (tabelada en çok 18 hücre) |
| `sahneler[].bas` | Sahnenin başladığı saniye; ilk sahne 0, sahneler arası en az 1,5 sn |
| `palet` | Stilin renk rolleri: tabela `zemin kasa hucre harf vurgu ayrac etiket`; VHS `zemin metin vurgu ikincil osd`; akış `zemin cizgi cizgi2 vurgu metin` |
| `tema` | Yalnız akış alanı: `gece` (varsayılan) ya da `kagit` |
| `muzik.bpm` | 60–160 (varsayılan tabela 96, VHS 108, akış 72) |

Kalkış tabelasında her kelime her formatın ızgarasına sığmalıdır (9:16'da 10 sütun × 6 satır, 16:9'da 18 × 4); `denetle` dört formatı da kontrol eder. Tabelada yalnız Türkçe büyük harfler, rakamlar ve `% . , : ! ? - + & / ' ·` vardır.

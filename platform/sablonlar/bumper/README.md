# platform/sablonlar/bumper

6 sn YouTube bumper (atlanamaz reklam) ve 3 sn video imzası. Renk, yazı tipi, logo ve hareket eğrisi yalnız [`marka.json`](../../marka/README.md)'dan gelir: başka bir marka için senaryodaki `"marka"` yolu ve birkaç kelime değişir, kod değişmez. Görüntü ve müzik kodla üretilir; ücretli servis gerekmez.

| Varyant | Süre | Akış |
| --- | --- | --- |
| `bumper` | 6 sn | marka noktası → önerme kelime kelime (her kelime bir vuruş, 120 BPM) → nokta çizgiye açılır → halka ekranı kaplar → logo harf harf oturur, halka dalgaları → alt yazı → çağrı |
| `imza` | 3 sn | nokta → halka → logo. Her videonun başına ya da sonuna eklenen marka imzası |

Müzik sentezlenir: sakin Bm9 ped ve her kelimede yükselen çan, hafif nabız, yükselen hışırtı, logoda gümbürtü + D majör akor ve parlak arpej. Seslendirme yok (6 sn'de müzik + az yazı daha iyi okunur). Çıktı H.264 + AAC, -14 LUFS, 30 fps, süre tam 6,000 sn.

```sh
python3 platform/sablonlar/stil/stil.py uret   ornekler/demli-kahve/bumper.json --stil bumper              # → cikti/demli-kahve-bumper-9x16.mp4, -kapak.png
python3 platform/sablonlar/stil/stil.py uret   ornekler/demli-kahve/imza.json   --stil bumper --format 16:9
python3 platform/sablonlar/stil/stil.py kare   ornekler/demli-kahve/bumper.json --stil bumper --an 1.5 3.5 5.9
python3 platform/sablonlar/bumper/bumper.py denetle ornekler/demli-kahve/bumper.json                         # doğrudan da çalışır
```

Biçim diğer şablonlardaki gibi video başına seçilir: `--format 9:16 | 16:9 | 1:1 | 4:5 | ikisi`, yoksa senaryodaki `"format"`, o da yoksa yalnız 9:16. YouTube bumper için 16:9 isteyin. 9:16 ve 4:5'te yazılar `platform/medya/teslim.json`'daki güvenli alanda kalır. Bir biçimin render'ı yaklaşık 15 sn sürer; hızlı prova için `--olcek 0.25`.

## Senaryo

```json
{
  "kimlik": "demli-kahve",
  "stil": "bumper",
  "sure": 6,
  "format": "9:16",
  "marka": "ornekler/demli-kahve/marka/marka.json",
  "bumper": { "varyant": "bumper", "onerme": "Sabahın on dakikası senin", "logo": "DEMLİ", "alt": "Kahve", "cagri": "demlikahve.com" }
}
```

`marka` yolu önce senaryonun klasörüne, sonra depo köküne göre çözülür. `logo` verilmezse `marka.json` → `logo.metin`, o da yoksa marka adı. `logo.dosya` (PNG ya da SVG) varsa yazı yerine o görsel açılır.

| marka.json | Bumper'da |
| --- | --- |
| `renk.ana` / `ana-ustu` | ilk bölümün zemini ve önerme yazısı; çağrı hapı |
| `renk.vurgu` | marka noktası, çizgi, halka, son kelime, logo altı çizgisi |
| `renk.zemin` / `metin` | logo bölümü (zorunlu iki rol; diğerleri eksikse bunlara düşer) |
| `renk.isik.sicak` | ilk bölümdeki sıcak ışık (yoksa vurgu) |
| `yazi.baslik` / `govde` | önerme + logo / alt yazı + çağrı. Google Fonts'tan indirilir (`~/.cache/studyo/fonts`); Türkçe harfi yoksa ya da ağ yoksa Inter |
| `hareket.egri` | bütün girişlerin `cubic-bezier` eğrisi |

## Denetimler

**HATA** üretimi durdurur, **UYARI** durdurmaz.

| Denetim | Düzey |
| --- | --- |
| marka.json yok ya da `marka.py denetle` HATA veriyor | HATA |
| Süre varyantınkinden farklı (bumper 6, imza 3) ya da 6 sn'den uzun | HATA |
| `bumper` varyantında önerme yok; logo hiçbir yerden gelmiyor | HATA |
| Karakter sınırı: önerme 32, logo 12, alt 18, çağrı 26 (yerleşim taşar) | HATA |
| Tanımsız `bumper.*` alanı | HATA |
| Kelime sınırı: önerme 5, logo 2, alt 3, çağrı 4 (6 sn'de okunmaz) | UYARI |
| marka.json kontrast uyarıları | UYARI |

Gerekenler stil şablonuyla aynı: `pip install skia-python numpy soundfile fonttools`, ffmpeg. Ortak kodlama, -14 LUFS ve kolaylaştırma eğrileri `../stil/motor.py`'den gelir.

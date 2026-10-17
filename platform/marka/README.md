# platform/marka

Marka kiti şeması, doğrulayıcısı ve dışa aktarıcıları (mimari §4.1). Tek dosya: `marka.py`, yalnız standart kitaplık.

```sh
python3 platform/marka/marka.py denetle <marka.json>
python3 platform/marka/marka.py aktar <css|figma|unity-uss|unity-json|prompt> <marka.json>
```

## Şema (`marka.json`, W3C Design Tokens)

| Bölüm | İçerik | Zorunlu |
| --- | --- | --- |
| `kimlik`, `ad` | `demli-kahve`, `Demli Kahve` | evet |
| `renk` | `{"$type": "color", "$value": "#rrggbb"}`; gruplar iç içe olabilir (`isik.sicak`) | `zemin`, `metin` |
| `ciftler` | `{"on": <renk>, "zemin": <renk>, "en_az": 4.5}`; erişilebilirlik çiftleri | yok; boşsa `metin`/`zemin` yine denetlenir |
| `yazi` | `baslik`, `govde`: `aile` (`fontFamily`), `agirlik` (`fontWeight`, 100–900) | `baslik`, `govde` |
| `logo` | `metin` ya da `dosya` (yol marka.json'a göre; dosya var mı denetlenir) | yok |
| `hareket` | `duration` (`400ms`) ve `cubicBezier` belirteçleri | yok |
| `ses` | `ton` (liste), `yasak` (metin denetimine HATA kuralı olarak girer) | yok (`ton` yoksa UYARI) |
| `prompt` | `uslup` (metin), `negatif` (liste): üretken araçlar için ortak blok | yok |

Denetim: hex biçimi, zorunlu adlar, çift başına WCAG kontrastı (en az 3.0, varsayılan 4.5), yazı kalınlığı, hareket değerleri, logo dosyası.

## Dışa aktarıcılar

| Hedef | Ne için |
| --- | --- |
| `css` | `--renk-*`, `--yazi-*`, `--hareket-*` özel özellikleri: web, HTML şablonları, Orshot, animatik |
| `figma` | İç içe DTCG belgesi: Figma değişkenleri, Tokens Studio |
| `unity-uss` | UI Toolkit için USS özel özellikleri (hareket hariç) |
| `unity-json` | `BrandTokens.asset` için veri; renkler 0–1 RGBA |
| `prompt` | Flow / Imagen / Veo için üslup + palet + ton + kaçınılacaklar |

Mimarideki `clipkit` aktarıcısı henüz yok; Clipkit'in tema biçimi ilk gerçek animasyon işinde (faz 3) okunarak yazılacak.

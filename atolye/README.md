# Atölye

Şirketlerin marka çalışmaları için animasyon videoları, oyunlar ve dijital pazarlama işlerinde ortak kullanılacak altyapının ilk çalışan iskeleti. Bir markayı bir kez tanımlarsınız; atölye her işi o tanıma ve brife karşı **doğrular**, sonra her kanal için **çıktı üretir**.

Yalnız Python 3.10+ standart kütüphanesi kullanır; kurulum gerekmez.

```sh
cd atolye
python3 -m atolye bicimler                          # kanal biçimleri
python3 -m atolye denetle ornekler/demo-kahve       # doğrula
python3 -m atolye uret ornekler/demo-kahve          # üret → ornekler/demo-kahve/cikti/
python3 -m atolye yeni ../musteriler/acme --ad Acme # yeni proje
python3 -m unittest discover -s tests -t .          # testler
```

## Bir proje

| Dosya | Ne tutar |
| --- | --- |
| `marka.json` | Renkler **rolle** (`primary`, `background`, `text`, `accent`, `on_primary`…), tipografi (`heading`, `body`), marka sesi (`tone`, `forbidden`), logo |
| `brif.json` | Hedef, kitle, içgörü, tek önerme, KPI, çağrı (CTA), kanallar, inandırıcı kanıtlar |
| `storyboard*.json` | Biçim (`reels`, `bumper`, `youtube`…), fps, sahneler: süre, renk rolleri, başlık/gövde, `show_logo`, `cta`, geçiş, hareket |

Tek brif, birden çok storyboard: aynı önerme her kanal için ayrı kurgulanır. Örnek: [`ornekler/demo-kahve/`](ornekler/demo-kahve) (15 sn Reels + 6 sn bumper).

## Denetimler (rasyonel kreatif)

Tat değil kural denetlenir. **HATA** üretimi durdurur, **UYARI** durdurmaz.

| Denetim | Düzey |
| --- | --- |
| Zorunlu renk/yazı rolleri, `#RRGGBB`, yazı kalınlığı | HATA |
| `text`/`background` kontrastı ≥ 4.5 (WCAG AA) | HATA |
| Sahnede başlık kontrastı ≥ 3.0, gövde ≥ 4.5 | HATA |
| Marka sesine aykırı ifade (Türkçe İ/ı duyarlı) | HATA |
| Toplam süre kanalın sınırını aşıyor (örn. bumper 6 sn) | HATA |
| Brifte zorunlu alan boş, bilinmeyen kanal | HATA |
| Önerme 12 sözcüğü aşıyor ya da "ve" ile iki önerme | UYARI |
| Ekran metni 3 sözcük/sn'den hızlı | UYARI |
| Kısa biçimde marka ilk 3 sn'de görünmüyor | UYARI |
| Brifte CTA var ama hiçbir sahnede yok; biçim brifin kanallarında yok | UYARI |

## Çıktılar

```
cikti/
  brif.md                         müşteriye giden tek sayfa brif
  belirtecler/tokens.css          web: CSS özel özellikleri
  belirtecler/tokens.json         W3C Design Tokens (Figma Tokens Studio, Style Dictionary)
  belirtecler/<Marka>Tokens.cs    Unity: Color32 ve yazı sabitleri
  <storyboard>/kareler/NN-id.svg  sahne kareleri, güvenli alana göre yerleşik
  <storyboard>/animatik.html      tarayıcıda oynayan animatik: zaman çubuğu, kare sayacı, geçişler
  <storyboard>/manifest.json      araçtan bağımsız zaman çizelgesi (kare aralıkları dahil)
```

`manifest.json` asıl kurgu aracına köprüdür: Clipkit, After Effects, Remotion ya da Unity Timeline bu dosyayı okuyup aynı zamanlamayı kurar. Kare sınırları birikimli süreden yuvarlanır; sahneler arasında boşluk ya da kayma olmaz.

## Kod

```
atolye/
  brand.py       marka kiti modeli ve doğrulaması
  brief.py       stratejik brif
  formats.py     kanal biçimleri, süre sınırları, güvenli alanlar
  storyboard.py  sahneler, zaman çizelgesi, kreatif denetimler
  project.py     proje klasörünü okur ve hepsini birlikte doğrular
  tokens.py      CSS / DTCG / Unity belirteçleri
  render.py      SVG kareler, HTML animatik, manifest
  cli.py         komut satırı
tests/           55 test (unittest)
```

## Sonraki adımlar

- Manifest'ten Clipkit projesine ve Unity Timeline'a doğrudan aktarıcı.
- Logo görseli (SVG) ve marka varlık kütüphanesi.
- Seslendirme metni ve müzik vuruşuna göre sahne süresi.
- Kampanya düzeyi: bir brif, çok kanal, A/B varyantları ve KPI raporu.

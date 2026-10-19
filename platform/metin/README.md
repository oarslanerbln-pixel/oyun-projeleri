# platform/metin

Görünen metnin tek tablosu, katmanlı yasak sözlük ve uzunluk sınırı (mimari §4.2). Kırk Oda'nın `tools/metin-denetimi/denetle.py` mekanizmasının genelleşmiş hâli; Kırk Oda kendi aracını K1'e kadar kullanmaya devam eder.

```sh
python3 platform/metin/metin.py denetle <tablo.csv> [--sozluk a.tsv b.tsv] [--dil tr en]
```

- **Tablo:** `anahtar, <dil>…, kaynak, not, izin, azami`. `izin` o satırda bilerek izin verilen sözlük kimlikleri; `azami` her dilde ayrı ölçülen en çok karakter.
- **Sözlük:** Kırk Oda biçimi, `kimlik  seviye  dil  desen  gerekçe` (TSV). `dil` `*` ise her dilde aranır.
- **Katmanlar:** `temel.tsv` (stüdyonun hiçbir işte kullanmadığı ifadeler: kanıtsız üstünlük iddiası, mucize vaadi…) + projenin sözlükleri + markanın `ses.yasak` listesi (HATA, Türkçe i/ı farkı gözetilmeden).
- **Türkçe:** `I→ı`, `İ→i` küçültmesi; "EN İYİ" ile "en iyi" aynı sayılır.

Uyum testi (`testler/test_metin.py`): platform denetleyicisi Kırk Oda'nın sözlüğü ve oyuncu metni üzerinde Kırk Oda'nın kendi denetleyicisiyle bulgu bulgu aynı sonucu verir (mimari faz 1 ölçütü).

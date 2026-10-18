# Küçük alışkanlıklar (kinetik, stil, çizgi roman ve risograf örnekleri)

[Kinetik şablonun](../../platform/sablonlar/kinetik/README.md) 10 saniyelik örneği: "her gün %1 daha iyi → bir yılda 37,78 kat". Seslendirme Piper "fahrettin" sesiyle yapılır (CC0). Çıktılar `cikti/` klasörüne yazılır ve depoya girmez.

Aynı senaryo [kâğıt kesik ve izometrik stillerde](../../platform/sablonlar/stil/README.md) de üretilir (seslendirme ortak):

```sh
python3 platform/sablonlar/stil/stil.py seslendir ornekler/kucuk-aliskanliklar/senaryo.json
python3 platform/sablonlar/stil/stil.py render ornekler/kucuk-aliskanliklar/senaryo.json --stil kagit-kesik
python3 platform/sablonlar/stil/stil.py render ornekler/kucuk-aliskanliklar/senaryo.json --stil izometrik
```

Ayrı şablonlarla aynı konunun webtoon ve risograf sürümleri de var (seslendirme satırları ve anlar aynı):

```sh
python3 platform/sablonlar/cizgi_roman/cizgi_roman.py render ornekler/kucuk-aliskanliklar/cizgi-roman.json   # cizgi-roman.json
python3 platform/sablonlar/risograf/risograf.py render ornekler/kucuk-aliskanliklar/risograf.json            # risograf.json
```

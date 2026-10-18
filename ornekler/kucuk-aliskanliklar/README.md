# Küçük alışkanlıklar (kinetik örnek)

[Kinetik şablonun](../../platform/sablonlar/kinetik/README.md) 10 saniyelik örneği: "her gün %1 daha iyi → bir yılda 37,78 kat". Seslendirme Piper "fahrettin" sesiyle yapılır (CC0). Çıktılar `cikti/` klasörüne yazılır ve depoya girmez.

Aynı senaryo [kâğıt kesik ve izometrik stillerde](../../platform/sablonlar/stil/README.md) de üretilir (seslendirme ortak):

```sh
python3 platform/sablonlar/stil/stil.py seslendir ornekler/kucuk-aliskanliklar/senaryo.json
python3 platform/sablonlar/stil/stil.py render ornekler/kucuk-aliskanliklar/senaryo.json --stil kagit-kesik
python3 platform/sablonlar/stil/stil.py render ornekler/kucuk-aliskanliklar/senaryo.json --stil izometrik
```

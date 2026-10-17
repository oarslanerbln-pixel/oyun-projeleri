# oyun-projeleri

Tek kişilik stüdyonun oyun projeleri. Her proje kendi klasöründe, kendi `CLAUDE.md` ve `docs/` yapısıyla.

| Proje | Durum | Klasör |
| --- | --- | --- |
| Kırk Dem (çalışma adı) — Toroslarda bir saat kulesi, altında kırk odalı mağara; 5–6 saatlik anlatı ve bulmaca oyunu (Unity 6) | Ön üretim: kararlar verildi, dikey dilime hazırlık | [`kirk-dem/`](kirk-dem/README.md) |

## Depo kuralları

- `main` korunur; her iş bir dalda yapılır ve PR ile birleşir.
- Kırk Dem çekirdeği her PR'da GitHub Actions'ta test edilir (`.github/workflows/kirk-dem-core.yml`).
- Oyuna giren ikili varlıklar Git LFS ile izlenir (`.gitattributes`); kaynak dosyalar (`.blend`, ham ses, kurgu projeleri) depoya girmez. Bilgisayarda bir kez `git lfs install` gerekir.

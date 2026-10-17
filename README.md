# oyun-projeleri

Tek kişilik stüdyonun oyun projeleri. Her proje kendi klasöründe, kendi `CLAUDE.md` ve `docs/` yapısıyla.

| Proje | Durum | Klasör |
| --- | --- | --- |
| Stüdyo platformu — animasyon, oyun ve marka işi için ortak altyapı (marka kiti, metin denetimi, medya hattı, yapay zekâ kaydı, şablonlar) | Mimari taslağı | [`platform/`](platform/docs/mimari.md) |
| Kırk Oda (İng. Forty Rooms) — Toroslarda bir saat kulesi, altında kırk odalı mağara; 5–6 saatlik anlatı ve bulmaca oyunu (Unity 6) | Ön üretim: kararlar verildi, dikey dilime hazırlık | [`kirk-oda/`](kirk-oda/README.md) |

## Depo kuralları

- `main` korunur; her iş bir dalda yapılır ve PR ile birleşir.
- Kırk Oda çekirdeği her PR'da GitHub Actions'ta test edilir (`.github/workflows/kirk-oda-core.yml`); oyuncu metni yasak sözcük denetiminden geçer (`.github/workflows/kirk-oda-metin.yml`).
- Oyuna giren ikili varlıklar Git LFS ile izlenir (`.gitattributes`); kaynak dosyalar (`.blend`, ham ses, kurgu projeleri) depoya girmez. Bilgisayarda bir kez `git lfs install` gerekir.

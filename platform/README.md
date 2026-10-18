# platform

Stüdyonun üç iş türü — animasyon videosu, oyun, marka ve kampanya — için yeniden kullanılabilir altyapı. Proje bilgisi içermez; projeler `proje.json` ve `marka.json` üzerinden bağlanır.

Mimari: [`docs/mimari.md`](docs/mimari.md). Modüller: `marka`, `metin`, `medya`, `uretim` (yapay zekâ çekimleri), `ses`, `ortak`, `ci`, `sablonlar`.

Seslendirme: [`ses/`](ses/README.md) (varsayılan yerel Piper; ElevenLabs işe göre, senaryoda `seslendirme.saglayici: "elevenlabs"` ile). Şablonların ortak adımları, önizleme ve teslim öncesi kalite kapısı: [`ortak/`](ortak/README.md). Siparişten teslime çalışma kuralları: [`docs/uretim-standardi.md`](docs/uretim-standardi.md). Şablonlar `sablonlar/` altında, her biri kendi README'siyle; güncel liste için `python3 platform/ci/calistir.py dizin`.

CI: [`ci/calistir.py`](ci/calistir.py) `platform/` altındaki her `testler/` klasörünü ve modül klasörlerindeki `ci.json` dosyalarını kendisi bulur. Yeni şablon eklerken iş akışı dosyasına ve bu README'ye dokunmak gerekmez; böylece paralel şablon PR'ları birbiriyle çakışmaz.

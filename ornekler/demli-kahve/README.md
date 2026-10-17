# Demli Kahve · örnek animasyon projesi

Uydurma bir kahve markası için 14 sn dikey/kare/4:5 tanıtım ve 6 sn YouTube bumper. Platformun animasyon şablonunu baştan sona gösterir; gerçek bir müşteri işi değildir.

```sh
python3 platform/sablonlar/animasyon/animasyon.py denetle ornekler/demli-kahve/proje.json
python3 platform/sablonlar/animasyon/animasyon.py uret ornekler/demli-kahve/proje.json
# → ornekler/demli-kahve/cikti/sabah-14/dikey/animatik.html
python3 platform/sablonlar/animasyon/animasyon.py render ornekler/demli-kahve/proje.json
# → ornekler/demli-kahve/cikti/render/sabah-14/dikey/demli-kahve-sabah-sabah-14-dikey-tr.mp4 (C03 yer tutucu)
```

| Katman | Dosya |
| --- | --- |
| 0 · Marka | `marka/marka.json` |
| 1 · Öz | `docs/01-oz/brif.json` |
| Görünen metin (TR/EN) | `metin/metin.csv` |
| 4 · Yapı | `docs/04-yapi/cekimler-*.csv` |

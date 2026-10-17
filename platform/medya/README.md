# platform/medya

Şimdilik yalnız **teslim ön ayarları** (mimari §4.3): `teslim.json` veri, `teslim.py` okuyucu.

```sh
python3 platform/medya/teslim.py listele
```

Her ön ayar oran, çözünürlük, loudness, varsa süre sınırı ve güvenli alan taşır. Platform süre sınırları sık değiştiği için her sınır bir `kontrol` tarihiyle yazılır. Animasyon şablonu kurgunun süresini ve metnin güvenli alana yerleşimini bu değerlere göre denetler.

Mimarideki `medya.sh` (Kırk Oda `flow.sh` komutları, `teslim`, `denetle`; ffmpeg) bir sonraki adımdır.

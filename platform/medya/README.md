# platform/medya

**Teslim ön ayarları** (mimari §4.3): `teslim.json` veri, `teslim.py` okuyucu. **Türev:** `turev.py` tek geniş klipten ön ayara kırpar (`odak_x/odak_y` merkezli), ölçekler ve loudness'ı ön ayarın `lufs` değerine çeker (ffmpeg). Kırpılan pencere 1,5 kattan fazla büyütülecekse uyarır: 720p yatay klipten dikey türev yalnız 404 px genişlikten çıkar.

```sh
python3 platform/medya/teslim.py listele
python3 platform/medya/turev.py klip.mp4 dikey.mp4 dikey --odak 0.6 0.4 [--yazdir]
```

Her ön ayar oran, çözünürlük, loudness, varsa süre sınırı ve güvenli alan taşır. Platform süre sınırları sık değiştiği için her sınır bir `kontrol` tarihiyle yazılır. Animasyon şablonu kurgunun süresini ve metnin güvenli alana yerleşimini bu değerlere göre denetler.

Mimarideki `medya.sh` (Kırk Oda `flow.sh` komutları, `teslim`, `denetle`; ffmpeg) bir sonraki adımdır.

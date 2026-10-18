# platform/ses

Seslendirme adımı: metin satırlarından teslime hazır 48 kHz mono WAV dosyaları ve kurgu zamanlaması için süreleri (`seslendirme.json`).

```sh
python3 platform/ses/seslendirme.py sesler                                   # kullanılabilir sesler ve lisansları
python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme  # varsayılan: Piper "fahrettin"
python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme --saglayici elevenlabs --ses <voice_id>
```

`satirlar.json`:

```json
{"satirlar": [{"id": "v0", "metin": "Her gün, sadece yüzde bir daha iyi ol."}, {"id": "v1", "metin": "Bugün başla."}]}
```

## Sağlayıcılar

| Ad | Ne | Gereken |
| --- | --- | --- |
| `piper` (varsayılan) | Yerel, ücretsiz sinirsel TTS (sherpa-onnx). Türkçe sesler: `fahrettin`, `fettah` (CC0, ticari işe uygun), `dfki` (CC BY-NC-SA, ticari işte reddedilir). Almanca: `thorsten` (CC0). | `pip install sherpa-onnx numpy`. Ses modeli ilk kullanımda GitHub'dan (`k2-fsa/sherpa-onnx` sürümü `tts-models`) `~/.cache/studyo/piper` altına iner; `PIPER_SES_DIZINI` ile değiştirilir. |
| `elevenlabs` | Ücretli API, `eleven_multilingual_v2`, Türkçe. | `ELEVENLABS_API_KEY`; ses kimliği `--ses` ya da `ELEVENLABS_VOICE_ID`. Anahtar yoksa adım açık bir HATA ile durur. **Gerçek anahtarla henüz denenmedi.** |

## Cila

İki sağlayıcının ham çıktısı da aynı ffmpeg zincirinden geçer: 80 Hz altı kesilir, 250 Hz çamuru azaltılır, 3,2 kHz varlık ve 9 kHz hava eklenir, yumuşak sıkıştırılır, baş ve sondaki sessizlik kırpılır, soxr ile 48 kHz'e çevrilir ve satır başına -16 LUFS'a getirilip -1 dBFS'te sınırlanır. Böylece sağlayıcı değişse de kurgudaki seviye ve zamanlama değişmez.

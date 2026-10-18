# platform/ses

Seslendirme adımı: metin satırlarından teslime hazır 48 kHz mono WAV dosyaları ve kurgu zamanlaması için süreleri (`seslendirme.json`).

```sh
python3 platform/ses/seslendirme.py sesler                                   # kullanılabilir sesler ve lisansları
python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme  # otomatik: anahtar varsa ElevenLabs, yoksa Piper "fahrettin"
python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme --saglayici elevenlabs --ses <voice_id>
python3 platform/ses/seslendirme.py kullanim                                 # ElevenLabs'te harcanan karakterler
```

`satirlar.json`:

```json
{"satirlar": [{"id": "v0", "metin": "Her gün, sadece yüzde bir daha iyi ol."}, {"id": "v1", "metin": "Bugün başla."}]}
```

## Sağlayıcılar

| Ad | Ne | Gereken |
| --- | --- | --- |
| `otomatik` (varsayılan) | `ELEVENLABS_API_KEY` ortamda varsa `elevenlabs`, yoksa `piper`. ElevenLabs'e ulaşılamazsa (ağ, kota, anahtar) uyarır ve Piper ile devam eder; render durmaz. | |
| `piper` | Yerel, ücretsiz sinirsel TTS (sherpa-onnx). Türkçe sesler: `fahrettin`, `fettah` (CC0, ticari işe uygun), `dfki` (CC BY-NC-SA, ticari işte reddedilir). Almanca: `thorsten` (erkek), `kerstin` (kadın, düşük kalite modeli); ikisi de CC0. | `pip install sherpa-onnx numpy`. Ses modeli ilk kullanımda GitHub'dan (`k2-fsa/sherpa-onnx` sürümü `tts-models`) `~/.cache/studyo/piper` altına iner; `PIPER_SES_DIZINI` ile değiştirilir. |
| `elevenlabs` | Ücretli API, `eleven_multilingual_v2` (dili metinden anlar; Türkçe ve Almanca). | `ELEVENLABS_API_KEY` (ortam değişkeni; depoya, dosyaya yazılmaz). Ağ izninde `api.elevenlabs.io` açık olmalı. İstek biçimi testlerde doğrulandı; bulut ortamının ağı ElevenLabs'e kapalı olduğu için gerçek anahtarla henüz denenmedi. |

### ElevenLabs sesi nasıl seçilir

1. Komut satırında `--ses <voice_id>`.
2. Senaryoda `seslendirme.ses`: bir voice_id ya da bir Piper adı. Piper adı verilirse (`kerstin` gibi) onun dili ve cinsiyeti alınır ve o dilin varsayılan ElevenLabs sesi kullanılır; böylece eski senaryolar değişmeden ElevenLabs'e geçer.
3. Ortam: `ELEVENLABS_VOICE_ID_TR`, `ELEVENLABS_VOICE_ID_DE` (dile özel), `ELEVENLABS_VOICE_ID` (hepsi).
4. Varsayılan: hazır çok dilli sesler, erkek **George** (`JBFqnCBsd6RMkjVDRZzb`), kadın **Matilda** (`XrExE9yKIg1WjnnlVkGX`). Dile özel seçimler (ör. e-kitap için beğenilen Almanca ses) `ELEVEN_DIL_SESLERI`'ne yazılır.

Dil senaryonun `seslendirme.dil` ya da `dil` alanından (yoksa `tr`) gelir.

### Kredi koruması

- **Önbellek:** her satır metin + ses + model + ayar özetiyle saklanır. Aynı satır ikinci kez üretilirken (yeniden seslendirme, başka format, başka stil) API çağrılmaz, kredi harcanmaz. Yer: `STUDYO_SES_ONBELLEK`, yoksa proje klasöründe `/mnt/project-files/.onbellek/ses` (bütün oturumlar paylaşır), o da yoksa `~/.cache/studyo/ses`.
- **Kayıt:** her iş `kullanim.jsonl`'a yazılır (zaman, ses, iş klasörü, harcanan karakter, API'den ve önbellekten gelen satır sayısı); iş sonunda özet basılır ve `seslendirme.json`'a `kullanim` alanı eklenir. Toplam: `seslendirme.py kullanim`. ElevenLabs'te 1 kredi ≈ 1 karakter.

## Cila

İki sağlayıcının ham çıktısı da aynı ffmpeg zincirinden geçer: 80 Hz altı kesilir, 250 Hz çamuru azaltılır, 3,2 kHz varlık ve 9 kHz hava eklenir, yumuşak sıkıştırılır, baş ve sondaki sessizlik kırpılır, soxr ile 48 kHz'e çevrilir ve satır başına -16 LUFS'a getirilip -1 dBFS'te sınırlanır. Böylece sağlayıcı değişse de kurgudaki seviye ve zamanlama değişmez.

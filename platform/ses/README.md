# platform/ses

Seslendirme adımı: metin satırlarından teslime hazır 48 kHz mono WAV dosyaları ve kurgu zamanlaması için süreleri (`seslendirme.json`).

```sh
python3 platform/ses/seslendirme.py sesler                                   # kullanılabilir sesler ve lisansları
python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme  # varsayılan ElevenLabs (yedek Piper "fahrettin")
python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme --saglayici elevenlabs --ses <voice_id>
python3 platform/ses/seslendirme.py kullanim                                 # ElevenLabs'te harcanan karakterler
python3 platform/ses/seslendirme.py kredi                                    # hesapta kalan kredi ve plan
```

`satirlar.json`:

```json
{"satirlar": [{"id": "v0", "metin": "Her gün, sadece yüzde bir daha iyi ol."}, {"id": "v1", "metin": "Bugün başla."}]}
```

## Sağlayıcılar

| Ad | Ne | Gereken |
| --- | --- | --- |
| `otomatik` (varsayılan) | `elevenlabs` (Atilla, 2026-10-19). Anahtar yoksa, ElevenLabs'e ulaşılamazsa ya da kalan kredi işe yetmezse bütün iş Piper ile üretilir; render durmaz, `seslendirme.json`'a `yedek` yazılır ve kalite raporu uyarır. Senaryoda `"seslendirme": {"saglayici": "piper"}` o işi bilerek Piper'la yapar. | |
| `piper` | Yerel, ücretsiz sinirsel TTS (sherpa-onnx). Türkçe sesler: `fahrettin`, `fettah` (CC0, ticari işe uygun), `dfki` (CC BY-NC-SA, ticari işte reddedilir). Almanca: `thorsten` (erkek), `kerstin` (kadın, düşük kalite modeli); ikisi de CC0. | `pip install sherpa-onnx numpy`. Ses modeli ilk kullanımda GitHub'dan (`k2-fsa/sherpa-onnx` sürümü `tts-models`) `~/.cache/studyo/piper` altına iner; `PIPER_SES_DIZINI` ile değiştirilir. |
| `elevenlabs` | Ücretli API, `eleven_multilingual_v2` (dili metinden anlar; Türkçe ve Almanca). Ses `mp3_44100_128` olarak iner ve ffmpeg ile açılır (ücretsiz ve Starter planda `pcm_44100` 403 verir). | `ELEVENLABS_API_KEY` (ortam değişkeni; depoya, dosyaya yazılmaz). Ağ izninde `api.elevenlabs.io` açık olmalı (proje ortamı "elevenlabs claude"). |

### Şablonlardan

Bütün şablonlar sesi `seslendirme.senaryodan(senaryo, klasör, sağlayıcı, ses)` ile alır: satırlar (`okunus` varsa o okunur), ses, dil ve sağlayıcı senaryonun `seslendirme` alanından gelir; komut satırındaki `--saglayici` / `--ses` senaryoyu ezer. `--saglayici elevenlabs` yedeğe düşmez, anahtar ya da kredi yoksa açık hatayla durur.

### Ses yönetmeni

`yonetmen.py` her ElevenLabs işinde satır satır ayar seçer (rol + duygu + tarz + ses profili), sese giden metni düzeltir, cümle arası uzun sessizlikleri kısaltır ve temposu aykırı satırları `seslendirme.json` → `yonetmen.uyarilar` ile kalite raporuna yazar. Tarz senaryonun `seslendirme.tarz` alanından (`yonetmen.py tarzlar`), kapatmak için `"yonetmen": false` ya da `--yonetmensiz`. Kredi harcamadan plan: `python3 platform/ses/yonetmen.py plan senaryo.json --tarz ciddi-analiz --ses eric`. Ayrıntı: `platform/docs/uretim-standardi.md` §8.

### Telaffuz sözlüğü

Marka ve yer adları (Residenzstraße, Mezquita, LÉVA) sese gitmeden önce okunuşuyla değişir; ekrandaki yazı değişmez (`telaffuz.py`, seslendirmedeki tek bağlantı noktası `uret`). Sözlükler, sonraki öncekini ezer: ortak `platform/ses/telaffuz/<dil>.tsv` (sesin diline göre, `yazılış<TAB>okunuş`), senaryo klasöründeki `telaffuz.tsv` / `telaffuz.<dil>.tsv` ve senaryonun `"seslendirme": {"telaffuz": {"LÉVA": "Leva"}}` alanı. Bütün kelime eşleşir, büyük/küçük harf yazıldığı gibi. Önbellek okunan metne göre tutulur: sözlüğe yeni ad eklemek yalnız o adın geçtiği satırlara kredi harcatır. Denemek için:

```sh
python3 platform/ses/telaffuz.py dene "Residenzstraße 109'da The Leaf" --dil tr [--klasor proje/]
python3 platform/ses/telaffuz.py liste --dil de
```

### ElevenLabs sesi nasıl seçilir

1. Komut satırında `--ses <ad ya da voice_id>`. Adlar stüdyo havuzundandır (`ELEVEN_ADLI_SESLER`): `george` (Türkçe varsayılanı), `turk-haber`, `bella`, `matilda`, `liam`; liste `seslendirme.py sesler`.
2. Senaryoda `seslendirme.ses`: bir voice_id ya da bir Piper adı. Piper adı verilirse (`kerstin` gibi) onun dili ve cinsiyeti alınır ve o dilin varsayılan ElevenLabs sesi kullanılır; böylece eski senaryoya yalnız `"saglayici": "elevenlabs"` eklemek yeter.
3. Ortam: `ELEVENLABS_VOICE_ID_TR`, `ELEVENLABS_VOICE_ID_DE` (dile özel), `ELEVENLABS_VOICE_ID` (hepsi).
4. Varsayılan: hazır çok dilli sesler, erkek **George** (`JBFqnCBsd6RMkjVDRZzb`), kadın **Matilda** (`XrExE9yKIg1WjnnlVkGX`). Dile özel seçimler (ör. e-kitap için beğenilen Almanca ses) `ELEVEN_DIL_SESLERI`'ne yazılır.

Dil senaryonun `seslendirme.dil` ya da `dil` alanından (yoksa `tr`) gelir.

### Kredi koruması

- **Önbellek:** her satır metin + ses + model + ayar özetiyle saklanır. Aynı satır ikinci kez üretilirken (yeniden seslendirme, başka format, başka stil) API çağrılmaz, kredi harcanmaz. Yer: `STUDYO_SES_ONBELLEK`, yoksa proje klasöründe `/mnt/project-files/.onbellek/ses` (bütün oturumlar paylaşır), o da yoksa `~/.cache/studyo/ses`.
- **Kredi kapısı:** iş başlamadan hesaptaki kalan kredi sorulur (`/v1/user/subscription`). Önbellekte olmayan satırların karakter toplamı kalandan fazlaysa tek satır bile üretilmez; `otomatik`te bütün iş Piper'a geçer (uyarılı), `elevenlabs`'te hata verir. Bütün satırlar önbellekteyse hesap sorulmaz.
- **Kayıt:** her iş `kullanim.jsonl`'a yazılır (zaman, ses, iş klasörü, harcanan karakter, API'den ve önbellekten gelen satır sayısı); iş sonunda özet basılır ve `seslendirme.json`'a `kullanim` alanı eklenir. Toplam: `seslendirme.py kullanim`. ElevenLabs'te 1 kredi ≈ 1 karakter.

## Cila

İki sağlayıcının ham çıktısı da aynı ffmpeg zincirinden geçer: 80 Hz altı kesilir, 250 Hz çamuru azaltılır, 3,2 kHz varlık ve 9 kHz hava eklenir, yumuşak sıkıştırılır, baş ve sondaki sessizlik kırpılır, soxr ile 48 kHz'e çevrilir ve satır başına -16 LUFS'a getirilip -1 dBFS'te sınırlanır. Böylece sağlayıcı değişse de kurgudaki seviye ve zamanlama değişmez.

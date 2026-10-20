# Proje haritası: nerede ne var

Thread'ler klasör taramak ve geçmiş okumak yerine buradan başlar. Yalnız ihtiyacın olan satırın gösterdiği dosyayı aç. Güncel durum: 2026-10-19.

**Güncelleme kuralı:** yeni teslim, final, şablon ya da modül ekleyen thread, PR'ında veya teslimde bu dosyada ilgili satırı ekler/düzeltir (tek satır, yol + ne olduğu); eskiyen "final" işaretini kaldırır.

## Başlarken
- Kurallar: `CLAUDE.md` (token), `platform/docs/uretim-standardi.md` (sipariş akışı, kalite kapısı).
- Bir işe devam: önce o klasörün `DEVIR.md` dosyası (liste aşağıda), sonra brif. Başka bir şey okuma.
- Ortak klasör: `/mnt/project-files/` (aşağıda `PF/`). Müşteri dosyaları yalnız orada, repoda değil.
- Stüdyo paneli (takvim, siparişler, fikir kutusu): https://claude.ai/artifact/Rpwozz6cNbi3XCHjQTDkxy — siparişler panelin veritabanında (`siparisler`); thread `ArtifactData` ile okur, `panel.py` ile klasöre çevirir, durumu geri yazar

## Repo (github.com/oarslanerbln-pixel/oyun-projeleri)
| Yol | Ne |
|---|---|
| `platform/docs/` | `mimari.md` (mimari), `uretim-standardi.md` (çalışma kuralları), `arastirma-3d.md` |
| `platform/ortak/` | `akis.py` (sipariş akışı), `uret.py` (tek komutla sipariş), `onizleme.py` (senaryo önizleme sayfası), `animatik.py` (onay öncesi küçük hareket taslağı), `katalog.py` (teslim kataloğu: `ara`), `panel.py` (panel siparişi ↔ sipariş klasörü), `kalite.py` (kalite kapısı → kalite.json), `devir.py` (DEVIR.md yazar), `sessiz.py` (uzun çıktıyı kısaltır), `formatlar.py`, `mastering.py`, `sfx.py`, `miks.py` (konuşmada kısma, vuruş, efekt kökü), `kutuphane.py` (CC0 kayıtlı efekt kütüphanesi; dosyalar `.onbellek/efekt-kutuphanesi`), `sayfa.py` (sayfa kontrolü), `altyazi.py` (kelime zamanları, kelime kelime altyazı, .srt/.vtt, `yak`), `dil_varyanti.py` (TR/DE varyantı: çeviri tablosu → `<ad>.de.json`; siparişte `"diller"`), `harita.py` (harita/rota geometrisi, yer adı arama, mesafe; dünya verisi `ortak/veri/`), `yayin.py` (yayın paketi: kapak, altyazı, başlık/açıklama/etiket → `<iş>/yayin/<video>/`) |
| `platform/ses/` | `seslendirme.py`: ElevenLabs (varsayılan) + Piper yedeği, önbellek `PF/.onbellek/ses` |
| `platform/uretim/` | AI üretim: `uretim.py` (fal.ai Kling), `gorsel.py` (Flux/Recraft), bütçe + önbellek; `FAL_KEY` gerekir |
| `platform/marka`, `metin`, `medya` | marka paleti, metin/çeviri tablosu, teslim formatları (`teslim.json`, `turev.py`) |
| `platform/sablonlar/stil/stil.py` | Ortak giriş: `stil.py uret <dosya> --stil <ad> --format 9:16\|16:9\|1:1\|4:5\|ikisi` |
| `platform/sablonlar/sahne/` | **Ortak sahne dili**: tek senaryo (`"dil": "sahne"`, 10 sahne tipi: grafik ve harita/rota dahil) 13 stilde; `sahne.py kontakt` her stilden kareler tek sayfada; `sahne.py yeni-stil <ad>` yeni stil kiti; sahnede `"stil"`/`"donustur"` ile stil karışımı ve fırça/mürekkep stil geçişi (`karisim.py`); `regresyon.py` görsel regresyon testi (her stilden 3 kare, referanslar `testler/regresyon/referans/`); öğeler kelimeye senkron girer, `"altyazi": true` kelime kelime altyazı (`senkron.py`); `grafik` tipi CSV'den çubuk/çizgi/pasta; `bol.py` düz metinden sahne.json taslağı; `kanca.py` üç açılış varyantı (soru, rakam, şok). README orada |
| `platform/sablonlar/kurgu/` | Uzun video kurgusu (`kurgu.json`: sahneler, tek müzik, bölüm listesi; şablonlar arası imza geçiş `"gecis": "firca"`/`"murekkep"`) |
| `platform/sablonlar/<stil>/` | Her şablonun README'si kullanımı anlatır (aşağıdaki tablo) |
| `platform/ci/`, `.github/workflows/` | CI (`platform.yml`, kirk-oda iş akışları) |
| `ornekler/` | Örnek senaryolar `ornekler/*/<stil>.json` (senaryo.json adı kullanılmaz); ortak sahne dili örnekleri `ornekler/*/sahne.json` (demli-kahve her tipi, grafik dahil, içerir) |
| `denemeler/` | ebru ve gerçekçi 3D test kodu (şablon değil) |
| `kirk-oda/` | Unity oyunu; K1 (2027-01-10) öncesi dosyaları taşınmaz |

### Şablonlar (`platform/sablonlar/`)
| Klasör | Stiller |
|---|---|
| `kinetik`, `bumper`, `mekan`, `vitrin` (ürün vitrini 3D), `analiz` | kinetik yazı, kısa bumper, mekan tanıtımı, .glb ürün, veri/haber |
| `stil/` (motor) | kağıt kesik (serbest süre), izometrik, hamur, piksel |
| `karakalem`, `tek_cizgi`, `origami`, `kolaj`, `minyatur`, `golge_oyunu`, `oyuncak` (3D oyuncak), `cizgi_roman`, `risograf` | adıyla aynı |
| `karakter/` | ortak karakter iskeleti + görünümler (`gorunumler/cizgisel.py`) |
| `ekran/` | kalkış tabelası, VHS, akış alanı |
| `desen/` | vitray, linol, çini, teknik çizim |
| `karusel/`, `neon/` | Instagram karusel, neon animasyon |
| `animasyon/` | AI çekimli proje iskeleti |

## Ortak klasör (`/mnt/project-files/`)
| Klasör | Ne / güncel final |
|---|---|
| `gelistirme/` | `DEVIR.md`, `beyin-firtinasi-2026-10-19.md` (son bölüm = güncel yol haritası), `gelistirme-plani.md`, `token-analizi-2026-10-19.md`, `maliyet.csv` (her sipariş bir satır), `katalog.jsonl` + `katalog.md` (teslim edilen her video; `katalog.py ara`), `render-sureleri.csv` |
| `the-leaf/` | Müşteri The Leaf Berlin: `1-tv-ekrani`, `2-instagram-reel`, `3-bumper` (+ `v2`), `4-ebru-3d/` (DEVIR); kaynak `proje/` |
| `lezzet-dunyasi/` | Müşteri, bitti: kinetik/kolaj/minyatür/origami (+ `-ses`) 9:16 |
| `le-mariage/` | Müşteri düğün salonu: reel, karusel (`onizleme/`), `animasyon/` neon, `sunum/le-mariage-praesentation.pdf`; DEVIR |
| `markalasma-nedir/` | Kendi kanal: güncel finaller `tek-cizgi-20sn-logo/` (TR) ve `tek-cizgi-20sn-de-logo/` (DE); her alt klasörde DEVIR. `30sn/` eski karalama |
| `atilla-ebook/` | E-kitap tanıtımı: `FINAL-roadmap-tek-cizgi-9x16.mp4`, `roadmap-*-george.mp4`; DEVIR |
| `al-andalus/` | Almanca sunum (minyatür): `STORYBOARD.md`, `klipler/`, deste kaynakları; DEVIR |
| `uzun-video/kucuk-aliskanliklar/` | Uzun video örneği (kurgu); DEVIR; `ses-paketi/` sahne efektli + vuruşa oturan sürüm |
| `yeni-stiller-2/` | 24 aday (`aday-sayfasi.png`, `karakter/`), `ARASTIRMA.md`, `GELISTIRME-PLANI.md`; çıktılar `cizgisel/`, `paket-b/`, `paket-c/`, `maskot/`, `siluet/` |
| `yeni-tarzlar/`, `ucuncu-tarz/`, `dorduncu-tarz/`, `besinci-tarz/`, `karakalem/` | İlk stil örnekleri ve havuz videoları (marka reklamı havuzu) |
| `ortak-sahne-dili/` | Ortak sahne dili örnekleri: 13 stilin kontakt sayfası, hamur + piksel örnek videoları (`cikti/`), stil geçişi örneği `stil-gecisi/`; DEVIR |
| `elevenlabs-ses/` | Ses örnekleri ve seçili sesler (README) |
| `arastirma/` | AI video araçları, orkestrasyon notları |
| `.onbellek/ses/` | Seslendirme önbelleği + `kullanim.jsonl` (karakter sayımı); elle dokunma |
| `uploads/hearth/` | Kullanıcı yüklemeleri (ID adlı); açıklamaları `.notes/inputs.md` |
| `alternatif/`, `analiz-haber/`, `bumper/`, `render/`, `urun-vitrini/`, `atolye/` | Eski demo çıktıları |

## DEVIR.md listesi
`gelistirme/`, `the-leaf/4-ebru-3d/`, `le-mariage/`, `markalasma-nedir/` (+ `30sn-v2`, `tek-cizgi-30sn`, `tek-cizgi-20sn`, `-de`, `-logo`, `-de-logo`), `atilla-ebook/`, `al-andalus/`, `uzun-video/kucuk-aliskanliklar/`, `yeni-stiller-2/cizgisel/`, `yeni-stiller-2/paket-c/`, `ortak-sahne-dili/`

# Stüdyo Platformu — Mimari Taslağı

**Durum:** Taslak · 17 Ekim 2026 · karar bekleyen maddeler `[ ]` ile işaretli.

Amaç: tek kişilik stüdyonun üç iş türünü — **animasyon videosu**, **oyun**, **marka ve kampanya işi** — aynı altyapı üzerinde, her seferinde sıfırdan kurmadan üretmek. Bu belge o altyapının bölümlerini, aralarındaki sözleşmeleri ve Kırk Oda'yı bozmadan oraya nasıl geçileceğini yazar.

Mimarinin tek cümlesi: **içerik depoda düz biçimde (Markdown, CSV, JSON) yaşar; araçlar (Unity, Clipkit, Flow, Orshot, Figma, DaVinci) yalnız bu içeriği okuyan ve çıktı üreten bağdaştırıcılardır.** Hiçbir araç tek doğruluk kaynağı değildir. Bu, Kırk Oda'nın "Unity yalnız gösterir, çalar ve kaydeder" ilkesinin (ADR-0001) stüdyo ölçeğine genişletilmiş hâlidir.

---

## 1. Kırk Oda'dan ne öğrenildi

Kırk Oda bir oyun projesi olarak başladı ama içinde, oyundan bağımsız beş parça zaten çalışıyor. Platform bunları icat etmez, ayıklar:

| Kırk Oda'daki parça | Ne yapıyor | Oyuna özgü mü | Platformdaki karşılığı |
| --- | --- | --- | --- |
| Doküman zinciri `00 → 01 → 02 → 03 → Unity` (`04-calisma-yontemi.md` §1) | Üst katman alt katmanı bağlar; çelişkide üst kazanır | Hayır | **Kanon zinciri** (§3) |
| `localization/oyuncu-metni.csv` + `tools/metin-denetimi/` | Görünen her metin tek tabloda; yasak sözcük denetimi CI'da | Sözlük evet, mekanizma hayır | **`metin` modülü** (§4.2) |
| `tools/flow/flow.sh` | ffmpeg ile ses atma, dikişsiz döngü, atlas, kenar saydamlığı, parlaklık ölçümü | Hayır | **`medya` modülü** (§4.3) |
| `art/flow-manifest.csv` + K-18 sınıfları | Yapay zekâ çıktılarının kaydı; bildirim metninin dayanağı | Sınıflar kısmen | **`yz-kaydi` modülü** (§4.4) |
| Saf C# çekirdek + `tools/core-tests` + CI | Kuralları motor açmadan test eder | Kurallar evet, desen hayır | **Oyun şablonu** (§5.2) |
| `06-karar-kaydi.md` (karar + geri dönüş tetikleyicisi) | Kararı ölçülebilir kılar | Hayır | **Karar kaydı biçimi** (§3.3) |
| `CLAUDE.md` + model yönlendirme tablosu | Claude'un bağlayıcı kuralları ve iş başına model | Kısmen | **İki katmanlı CLAUDE.md** (§7) |

Eksik olanlar da Kırk Oda'dan okunuyor: marka renkleri ve yazı tipleri yalnız sanat kitabında düz metin olarak duruyor (Flow promptunda `#FFB36B`, Unity'de ayrıca elle); bir videonun 16:9, 9:16 ve 1:1 sürümleri için ortak bir teslim tanımı yok; animatik Clipkit'te yaşıyor ama zamanlaması depoda değil.

---

## 2. Depo düzeni (hedef)

```
oyun-projeleri/
  CLAUDE.md                      Stüdyo geneli kurallar (yeni; §7)
  README.md                      Proje tablosu
  platform/                      Yeniden kullanılabilir altyapı — proje bilgisi içermez
    docs/                        Bu belge, ADR'ler, modül sözleşmeleri
    marka/                       Marka kiti şeması + dışa aktarıcılar
    metin/                       Metin tablosu şeması + denetleyici + temel sözlük
    medya/                       ffmpeg hattı + teslim ön ayarları
    yz-kaydi/                    Yapay zekâ kaydı şeması + doğrulayıcı + bildirim üretici
    sablonlar/
      oyun-unity/                Kırk Oda deseninden: Core/Data/Gameplay, core-tests, CI
      animasyon/                 Senaryo → çekim listesi → animatik → teslim
      kampanya/                  Mesaj × kanal × biçim × dil matrisi
    ci/                          Yeniden kullanılabilir GitHub Actions iş akışları (workflow_call)
  kirk-oda/                      Oyun projesi (yerinde kalır)
  <yeni-proje>/                  Şablondan doğar; proje.json taşır
```

Her proje klasörünün kökünde bir **`proje.json`** bulunur. Platform araçları projeyi bu dosyadan tanır; klasör adından ya da sabit yoldan değil.

```json
{
  "kimlik": "kirk-oda",
  "tur": "oyun",
  "marka": "kirk-oda/marka/marka.json",
  "diller": ["tr", "en", "de", "ja", "zh-Hans"],
  "metin": {
    "tablolar": ["localization/oyuncu-metni.csv"],
    "sozlukler": ["platform/metin/temel.tsv", "kirk-oda/tools/metin-denetimi/yasak-sozcukler.tsv"]
  },
  "yz_kaydi": "art/flow-manifest.csv",
  "teslim": ["steam-kapsul", "steam-fragman"],
  "kapilar": ["K1", "K2", "K3"]
}
```

`tur` üç değerden biridir: `oyun`, `animasyon`, `kampanya`. Bir marka için hem kampanya hem tanıtım videosu yapılıyorsa iki proje açılır ve ikisi aynı `marka` dosyasını gösterir.

---

## 3. Kanon zinciri

### 3.1 Zincir

Kırk Oda'nın dört katmanlı zinciri üç iş türü için ortak bir iskelete genelleşir. Katman adları türe göre değişir, kural değişmez: **alt katman üst katmana aykırıysa alt katman düzeltilir; üst katmanı değiştirmek karardır.**

| # | Katman | Oyun | Animasyon | Kampanya |
| --- | --- | --- | --- | --- |
| 0 | **Marka** | Oyunun kimliği (ad, palet, yazı, ton) | Müşterinin ya da filmin marka kiti | Müşterinin marka kiti |
| 1 | **Öz** | Dünya kitabı | Yaratıcı brif: tek fikir, izleyici, his | Strateji: hedef, kitle, tek mesaj, ölçüt |
| 2 | **Kilit** | Senaryo kilidi | Senaryo + seslendirme metni | Mesaj matrisi ve metinler |
| 3 | **Üslup** | Sanat kitabı | Üslup kitabı + storyboard | Görsel sistem (şablonlar) |
| 4 | **Yapı** | Mimari, veri modeli | Çekim listesi (`cekimler.csv`) | Varyant listesi (`matris.csv`) |
| 5 | **Üretim** | Unity | Animatik → üretim → kurgu | Toplu üretim (şablon + veri) |
| 6 | **Teslim** | Build, mağaza varlıkları | Kanal başına master ve türevler | Kanal başına dosyalar |

0. katman yenidir. Kırk Oda'da marka bilgisi sanat kitabına dağılmıştı; platformda marka, bütün katmanların üstünde tek dosyadır (§4.1).

### 3.2 Doküman numaralandırması

Her projenin `docs/` klasörü zincirin sırasını izler: `00-marka`, `01-oz`, `02-kilit`, `03-uslup`, `04-yapi`. Kırk Oda mevcut numaralarını korur (§8); şablonlar yeni düzenle doğar.

### 3.3 Karar kaydı

Kırk Oda'nın biçimi değişmeden şablona girer: her karar bir no (`K-nn`), konu, karar, gerekçe ve **ölçülebilir geri dönüş tetikleyicisi** taşır. Kampanya projelerinde tetikleyici genellikle bir ölçüttür ("ilk 7 günde kaydırma durdurma oranı %25'in altındaysa açılış karesi değişir").

---

## 4. Ortak modüller

Her modül aynı biçimde kurulur: **bir şema** (verinin biçimi), **bir doğrulayıcı** (CI'da koşar), **dışa aktarıcılar** (araçlara veri verir). Modüller Python 3 standart kitaplığı ve ffmpeg dışında bağımlılık almaz; bulut oturumunda ve yerel makinede aynı çalışır.

### 4.1 `marka` — marka kiti

**Sorun.** Renk, yazı tipi ve ton bugün en az dört yerde elle tekrarlanıyor: sanat kitabı, Flow promptları, Unity malzemeleri, Clipkit projesi. Biri değişince diğerleri kayar.

**Şema.** `marka.json`, W3C Design Tokens biçiminde (`$value`, `$type`) tek dosya:

| Bölüm | İçerik |
| --- | --- |
| `renk` | Ana palet, anlamsal adlar (`isik.sicak`, `golge.derin`), erişilebilirlik çiftleri (metin/zemin kontrastı ≥ 4.5:1) |
| `yazi` | Yazı aileleri, ağırlıklar, ölçek; lisans notu |
| `logo` | Dosya yolları (LFS), boşluk alanı, en küçük boyut, yasak kullanımlar |
| `hareket` | Süreler ve eğriler (giriş, çıkış, vurgu); animasyon ve UI aynı değerleri okur |
| `ses` | Ton ve üslup kuralları (metin denetimine kural olarak da girer), seslendirme notu, loudness hedefi |
| `prompt` | Üretken araçlar için ortak üslup bloğu ve negatif liste (Kırk Oda §5.1'in genelleşmiş yeri) |

**Dışa aktarıcılar.** `marka.py aktar <hedef>`:
- `css` → CSS değişkenleri (web, HTML şablonları, Orshot)
- `unity` → `BrandTokens.asset` için JSON + USS değişkenleri
- `clipkit` → proje teması (renk, yazı, hareket eğrileri)
- `figma` → değişken koleksiyonu JSON'u
- `prompt` → Flow/Imagen/Veo için hazır üslup bloğu

**Doğrulayıcı.** Kontrast çiftleri, eksik anlamsal ad, logo dosyasının varlığı.

### 4.2 `metin` — görünen metin

**Kırk Oda'dan alınan.** Tek tablo (`anahtar, <dil>…, kaynak, not, izin`), yasak sözcük sözlüğü (`kimlik, seviye, dil, desen, gerekçe`), CI'da HATA/UYARI ayrımı, "liste büyür, küçülmez" kuralı.

**Genelleşen.**
- Sözlük katmanlıdır: `platform/metin/temel.tsv` (stüdyonun hiçbir işte kullanmayacağı ifadeler) + markanın sözlüğü (`marka.json → ses`) + projenin sözlüğü. Denetleyici `proje.json`'daki listeyi sırayla birleştirir.
- Uzunluk sınırı sütunu (`azami`): altyazı satırı, buton, reklam başlığı, mağaza kısa açıklaması. Denetleyici her dil için ayrı ölçer.
- Dışa aktarıcılar: Unity Localization CSV'si, altyazı (`.srt`, `.vtt`; zaman çekim listesinden gelir), kampanya metin dosyaları, mağaza metinleri.

**Göç.** `kirk-oda/tools/metin-denetimi/denetle.py` zaten yolu argümanla alıyor; platforma taşındığında Kırk Oda'nın sözlüğü yerinde kalır ve `proje.json` onu gösterir.

### 4.3 `medya` — video ve görüntü hattı

**Kırk Oda'dan alınan.** `flow.sh`'in beş komutu (`strip-audio`, `loop`, `flipbook`, `edge-fade`, `luma`) değişmeden `platform/medya/medya.sh`'e taşınır.

**Eklenen.** Video ve marka işi için asıl eksik olan **teslim ön ayarlarıdır**: bir master'dan kanal başına türev.

| Ön ayar | Oran | Çözünürlük | Süre sınırı | Ses | Not |
| --- | --- | --- | --- | --- | --- |
| `yatay-master` | 16:9 | 3840×2160 | — | −23 LUFS | ProRes 422 HQ ya da DNxHR HQ; arşiv |
| `yatay-web` | 16:9 | 1920×1080 | — | −14 LUFS | H.264, YouTube, site |
| `dikey` | 9:16 | 1080×1920 | ön ayarda | −14 LUFS | Reels, Shorts, TikTok; güvenli alan maskesi |
| `kare` | 1:1 | 1080×1080 | ön ayarda | −14 LUFS | Akış içi |
| `dikey-akis` | 4:5 | 1080×1350 | ön ayarda | −14 LUFS | Instagram/Facebook akışı |
| `sessiz-gif` | özgür | ≤ 960 px | ≤ 20 sn | yok | Steam sayfası (K-11), e-posta |
| `steam-fragman` | 16:9 | 1920×1080 | — | −14 LUFS | Steam yükleme şartları |

Ön ayarlar `platform/medya/teslim.json` içinde veri olarak durur; komut `medya.sh teslim <master> <ön_ayar> [--kirp odak.json]`. Dikey ve kare türevler için kırpma merkezi çekim başına `cekimler.csv`'den gelir (bkz. §5.1); her kanalın güvenli alanı maske olarak denetlenir. Platform süre sınırları sık değiştiği için değerler ön ayar dosyasında tutulur ve tarih taşır, belgede yazılmaz.

**Doğrulayıcı.** `medya.sh denetle <dosya> <ön_ayar>`: çözünürlük, kare hızı, loudness (`ebur128`), ses kanalı varlığı, `luma` aralığı. Teslim klasörüne giren her dosya buradan geçer.

### 4.4 `yz-kaydi` — yapay zekâ çıktılarının kaydı

**Kırk Oda'dan alınan.** Manifest sütunları (`dosya, sinif, model, tarih, prompt, kullanildigi_yer`) ve "sınıfı belirsizse üst sınıf sayılır" kuralı.

**Genelleşen.**
- Sınıflar türden bağımsız adlandırılır: **A — referans** (teslime girmez), **B — destekleyici** (arka plan, doku, efekt; odağın dışında), **C — öne çıkan** (izleyicinin gördüğü ana görüntü ya da hareket). Proje kendi yasaklarını ekler (Kırk Oda'nın beş yasağı gibi).
- Yeni sütunlar: `kaynak_ozeti` (çıktının SHA-256'sı; dosya yeniden adlandırılsa da bulunur), `arac` (Flow, Clipkit, Orshot…), `duzenleme` (elle üzerine ne yapıldı).
- **Bildirim üretici:** manifestten kanal başına bildirim metni çıkar — Steam'in yapay zekâ içerik formu, sosyal platformların yapay zekâ etiketi, müşteri teslim notu. AB Yapay Zekâ Yasası'nın 50. maddesindeki şeffaflık yükümlülükleri (üretilen ya da değiştirilen gerçekçi görüntü ve videonun işaretlenmesi) Ağustos 2026'dan itibaren uygulanıyor; kampanya işinde bu bir seçenek olmaktan çıkıyor. `[ ]` Hangi kanalda hangi etiketin zorunlu olduğu bir hukuk okumasıyla doğrulanacak; bu belge hukuki görüş değildir.
- **Doğrulayıcı:** teslim klasöründeki her dosya ya manifestte vardır ya da `elle` işaretlidir; C sınıfı bir dosya teslim edilip bildirimde yoksa CI düşer.

### 4.5 `ci` — yeniden kullanılabilir iş akışları

Kök `.github/workflows/` altında yalnız ince çağırıcılar kalır; mantık `platform/ci/` altında `workflow_call` iş akışlarıdır:

| İş akışı | Girdi | Koşar |
| --- | --- | --- |
| `metin.yml` | proje kimliği | `metin` denetleyicisi |
| `yz-kaydi.yml` | proje kimliği | manifest doğrulayıcısı |
| `marka.yml` | marka dosyası | şema ve kontrast denetimi |
| `dotnet-cekirdek.yml` | test projesinin yolu | `dotnet test` (Kırk Oda'daki `kirk-oda-core.yml`'nin genelleşmişi) |
| `medya.yml` | teslim klasörü | `medya.sh denetle` (yalnız `teslim/` değişince) |

Her proje kendi `paths:` süzgeciyle çağırır; bir projedeki değişiklik başka projenin işini tetiklemez.

---

## 5. Üç iş türünün hattı

### 5.1 Animasyon videosu

```
brif (01-oz) → senaryo + VO (02-kilit, metin tablosu) → storyboard (03-uslup)
  → cekimler.csv (04-yapi) → animatik (Clipkit) → üretim → kurgu (DaVinci) → master → türevler
```

Merkezde **çekim listesi** durur. Kırk Oda'da açılış animatiği Clipkit'te kuruldu ama zamanlaması depoda değil; platformda zamanlama depodadır, Clipkit onu okur:

```
cekim,sure_sn,metin_anahtari,gorsel,kamera,gecis,odak_x,odak_y,sinif,durum
C01,4.0,vo.acilis.1,kar düşen kule,yavaş itme,kesme,0.52,0.40,B,animatik
C02,3.5,vo.acilis.2,…
```

- `metin_anahtari` metin tablosuna bağlanır; seslendirme ve altyazı aynı satırdan gelir, çeviri tek yerde yapılır.
- `odak_x/odak_y` dikey ve kare türevlerin kırpma merkezidir (§4.3).
- `sinif` yapay zekâ kaydının sınıfıdır; üretim sırasında kayıt satırı bundan doğar.
- `durum`: `animatik → uretim → onay → kilit`.

**Bağdaştırıcılar.** `animasyon.py clipkit` çekim listesinden Clipkit projesi kurar (animatik ve hızlı sosyal kesitler için); DaVinci için EDL/FCPXML dışa aktarımı kurguyu çekim sırasıyla açar. Uzun ve el yapımı animasyonun kendisi depo dışındaki araçlarda yapılır; depoya master'ın kimliği ve türevler girer.

**Doğrulama kapıları.** V1 animatik onayı (süre ve ritim kilitlenir) · V2 renk ve ses kilidi · V3 teslim denetimi (`medya.sh denetle` + `yz-kaydi`).

### 5.2 Oyun

Kırk Oda deseni şablon olur, kod değil:

- `Runtime/Core` (saf C#, `noEngineReferences: true`) · `Runtime/Data` (ScriptableObject) · `Runtime/Gameplay` (MonoBehaviour, yalnız iletir) · `Tests/EditMode` · `tools/core-tests` (Unity'siz `dotnet test`, C# 9).
- `platform/sablonlar/oyun-unity/yeni.sh <kimlik> <Ad>` assembly adlarını, asmdef'leri ve CI çağırıcısını üretir.
- Marka kiti Unity'ye `BrandTokens` olarak girer; Presentation katmanı rengi oradan okur.

Ortak kod kitaplığı **şimdi yazılmaz**. Kırk Oda'nın Core'u (sır defteri, kule, zaman kuralları) oyuna özgüdür. Kayıt, yerelleştirme köprüsü ya da erişilebilirlik ayarları gibi parçalar ikinci oyunda aynı biçimde gerekirse o zaman `Studio.Core` olarak ayıklanır (§6, kural 3).

Oyun projesi de pazarlama üretir: mağaza kapsülleri, fragman, sessiz GIF, sosyal kesitler. Bunlar oyun projesinin `teslim/` klasöründe kampanya hattıyla (§5.3) yapılır; ayrı proje açılmaz.

### 5.3 Marka ve kampanya

```
strateji (01-oz) → mesaj matrisi (02-kilit) → görsel sistem / şablonlar (03-uslup)
  → matris.csv (04-yapi) → toplu üretim → kanal teslimi → ölçüm → karar kaydı
```

**Matris.** Her satır bir teslim edilecek varlıktır:

```
varlik,mesaj,kanal,on_ayar,dil,sablon,metin_anahtari,gorsel,durum
M1-IG-4x5-tr,M1,instagram,dikey-akis,tr,urun-kart,kampanya.m1.baslik,urun_01.png,taslak
```

- Statik görseller HTML şablonundan (marka kiti CSS değişkenleriyle) ya da Orshot şablonundan toplu üretilir; hangisinin kullanılacağı şablon başına seçilir.
- Hareketli kesitler animasyon hattının `teslim` ön ayarlarıyla üretilir.
- Ölçüm sonucu (izlenme, tıklama, kaydırma durdurma) matris satırına değil karar kaydına yazılır; matris üretim belgesidir, rapor değil.

**Müşteri ayrımı.** `[ ]` Müşteri işinin bu depoda mı, müşteri başına ayrı özel depoda mı duracağı açık karardır. Öneri: platform bu depoda kalır; her müşteri ayrı özel depoda olur ve platformu git alt modülü ya da sürümlü kopya olarak alır. Gerekçe: müşterinin varlıkları ve stratejisi başka müşteriyle aynı geçmişi paylaşmamalı, erişim müşteri başına verilebilmeli. Kendi markaların (stüdyonun kendisi, oyunların pazarlaması) bu depoda kalır.

---

## 6. Tasarım kuralları

1. **İçerik düz biçimde, araç bağdaştırıcıdır.** Markdown, CSV, JSON depoda; Clipkit projesi, Orshot şablonu, Figma dosyası bunlardan üretilir ya da bunlara bağlanır. Araçta yapılan bir değişiklik depoya geri yazılmadıkça yok sayılır.
2. **Proje bilgisi platforma girmez.** `platform/` içinde hiçbir proje kimliği, renk değeri ya da metin geçmez; hepsi `proje.json` ve `marka.json` üzerinden gelir.
3. **İkinci kullanımda ayıkla.** Bir parça iki projede aynı biçimde gerekene kadar projede kalır. İstisna §1 tablosundaki beş parçadır; onlar zaten oyundan bağımsız çalışıyor.
4. **Her modül şema + doğrulayıcı + CI.** Doğrulayıcısı olmayan kural kural değildir; Kırk Oda'daki yasak sözcük denetimi gibi.
5. **Bağımlılık en az.** Python standart kitaplığı, ffmpeg, .NET SDK. Yeni bir bağımlılık bir ADR ister.
6. **İkili dosyalar** teslime giriyorsa Git LFS'te (K-17 genelleşir); kaynak dosyalar (`.blend`, `.drp`, ham ses, ham çekim) depo dışında yedekli klasörde. `[ ]` Video master'ları LFS kotası için büyük: master'lar depo dışında nesne depolamada (ör. Cloudflare R2 ya da Google Drive), depoda yalnız SHA-256 ve konum.
7. **Görünen metnin tek kaynağı metin tablosudur.** Altyazı, buton, reklam başlığı, mağaza metni; hepsi denetimden geçer.

---

## 7. Claude ile çalışma

- **İki katmanlı `CLAUDE.md`.** Kökte stüdyo geneli (dil kuralları, PR düzeni, model kimliği yazmama, yapay zekâ kaydı zorunluluğu, platform kuralları §6); her projede projenin bağlayıcı kuralları (Kırk Oda'nınki olduğu gibi kalır). Claude Code ikisini de okur.
- **Model yönlendirmesi** Kırk Oda'daki tablodan (`04-calisma-yontemi.md` §4) türe göre genelleşir: kanon ve tutarlılık okuması büyük modelle, şema/doğrulayıcı/mimari varsayılan modelle, toplu dışa aktarım ve matris doldurma küçük modelle. Tablo `platform/docs/calisma-yontemi.md`'ye taşınır; proje yalnız farkını yazar.
- **Bağdaştırıcı araçlar** (Clipkit, Orshot, Figma, Flow) yalnız `marka` ve `metin` dışa aktarıcılarından gelen veriyle çağrılır; araçta elle değer yazılmaz.

---

## 8. Kırk Oda'yı bozmadan geçiş

Kırk Oda'nın dikey dilimi 19 Ekim'de başlıyor ve K1 kapısı 10 Ocak 2027. Platform işi bu takvimi yavaşlatmamalı. Kural: **K1'e kadar `kirk-oda/` içindeki hiçbir dosya taşınmaz ya da yeniden adlandırılmaz.** Platform parçaları kopyalanıp genelleştirilir; Kırk Oda onlara K1'den sonra geçer.

| Faz | Ne | Kırk Oda'ya etkisi | Bitti ölçütü |
| --- | --- | --- | --- |
| **0 — Bu PR** | Bu belge | Yok | Mimari onaylandı ya da düzeltildi |
| **1 — İskelet** | Kök `CLAUDE.md`; `platform/metin` (denetleyici + temel sözlük + uzunluk sütunu); `platform/medya` (flow.sh'in kopyası + `teslim.json` + `denetle`); `platform/ci` | Yok; Kırk Oda kendi araçlarını kullanmaya devam eder | Platform araçları Kırk Oda verisi üzerinde aynı sonucu verir (CI'da karşılaştırma) |
| **2 — Marka ve kayıt** | `platform/marka` (şema + `css`, `prompt`, `clipkit` dışa aktarıcıları); `platform/yz-kaydi` (şema + doğrulayıcı + bildirim) | `kirk-oda/marka/marka.json` sanat kitabındaki paletten üretilir; sanat kitabı değerleri değişmez | Kırk Oda Flow ortak bloğu `marka.py aktar prompt`'tan birebir çıkar |
| **3 — İlk animasyon projesi** | `platform/sablonlar/animasyon`; çekim listesi → Clipkit; altyazı dışa aktarımı | Yok | Bir gerçek video (ör. Kırk Oda'nın 20 sn sessiz GIF'i ya da bir müşteri işi) çekim listesinden üç oranda teslim edildi |
| **4 — İlk kampanya** | `platform/sablonlar/kampanya`; matris → HTML/Orshot toplu üretim | Steam sayfası varlıkları (K-11, Şubat 2027) bu hattan üretilir | Bir kampanyanın bütün varlıkları matristen üretildi ve denetlendi |
| **5 — Kırk Oda geçişi** | K1'den sonra: `proje.json`, CI çağırıcıları platforma, `tools/` platforma yönlendirilir | Yollar değişir; bir PR | Kırk Oda CI'ı platform iş akışlarıyla yeşil |
| **6 — Oyun şablonu** | `platform/sablonlar/oyun-unity`; ikinci oyun ya da prototip ihtiyacında | Yok | Şablondan doğan proje boş Core testleriyle yeşil |

Faz 3 ve 4 gerçek bir işle tetiklenir; boş şablon yazılmaz.

---

## 9. Açık kararlar

- [ ] Platformun adı ve klasörü (`platform/` çalışma adıdır).
- [ ] Müşteri işi aynı depoda mı, müşteri başına ayrı depoda mı (öneri: ayrı, §5.3).
- [ ] Video master'larının yeri: LFS mi, nesne depolama mı (öneri: nesne depolama + SHA-256, §6 kural 6).
- [ ] Statik kampanya görselleri için birincil araç: HTML şablonu mu, Orshot mu (öneri: HTML varsayılan, Orshot müşteri kendi düzenlemek isterse).
- [ ] Kodla animasyon (Remotion ya da Motion Canvas gibi) hatta girsin mi; bugünkü öneri Clipkit + el yapımı, kodla animasyon yalnız veri güdümlü videolarda tekrar değerlendirilir.
- [ ] Yapay zekâ etiketi zorunluluklarının kanal başına hukuk okuması (§4.4).

## 10. Bu belgenin dokunmadığı

Kırk Oda'nın oyun kuralları, sanat kitabı ve karar kaydı. Bu belge onları kaynak olarak okur ve değiştirmez.

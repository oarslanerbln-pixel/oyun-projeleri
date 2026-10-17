# Kapanış ve Dikey Dilim Planı — 19 Ekim 2026 → 10 Ocak 2027

Karar K-02'nin ilk iki fazı, hafta hafta. Her satırda bir "bitti" ölçütü var; hafta o ölçüt sağlanınca biter, takvim değil. Kim sütunu: **Sen** (insan işi ya da senin bilgisayarın), **Bulut** (bu tür bir Claude Code oturumu: kod, test, doküman), **Masaüstü** (Claude masaüstü uygulaması + Unity eklentisi / Unity MCP; Unity açık bilgisayar gerekir).

## Faz 0 — Kapanış (4 hafta)

| Hafta | İş | Kim | Model | Bitti ölçütü |
| --- | --- | --- | --- | --- |
| 19–25 Eki | Hassasiyet okuması brifini iki okuyucuya gönder (`07-hassasiyet-okumasi.md`) | Sen | — | İki okuyucu kabul etti, teslim 14 Kasım |
| | İllüstratör ara; brif: `02-sanat-kitabi/flow-uslup-kitabi.md` §2, 12 kare | Sen | — | En az iki teklif |
| | `git lfs install`; Unity 6 LTS + URP projesini `kirk-dem/unity` içinde aç, `Assets/_KirkDem` yerinde kalsın | Sen + Masaüstü (`unity:new-unity-project`) | Sonnet 5.5 | Proje açılıyor, Console temiz |
| 26 Eki–1 Kas | Paketler: Input System, Cinemachine, Localization, Test Framework, Shader Graph | Masaüstü (`unity:unity-package-management`) | Sonnet 5.5 | Dört asmdef derleniyor; EditMode'da 45 test yeşil |
| | Oda prefab anatomisi (`03-mimari/oda-kiti.md`) gri kutu olarak | Masaüstü | Sonnet 5.5 | Boş bir oda prefab'ı tüm noktalarıyla |
| 2–8 Kas | Toprak R1-01…R1-03 ve Su, Gölge, Ayna gri kutu odaları için `RoomDefinition` varlıklarını `kirk-oda.md` tablosundan üreten Editor betiği | Bulut | Haiku 5.5 (üretim), Opus 5.5 (inceleme) | Betik tablodan 6 varlık üretiyor, `OnValidate` uyarısız |
| | Bekçi rig blokajları: dörtbacaklı, kuş (K-15) | Sen (Blender) | — | İki rig, silüet + ışıklı göz |
| 9–15 Kas | Kasaba bugün çağı ve kule içi blokajı | Sen (Blender) | — | Meydan, kapak, kule 7 kat, kahve, değirmen kutu düzeyinde |
| | **K0:** okuma dönüşleri; K-06 ve K-07 kesinleşir | Sen + Bulut (doküman güncellemesi) | Fable 5.1 (çapraz okuma) | Ad ve baba adı kesin; gerekiyorsa `inscriptionLetters` güncel |

## Faz 1 — Dikey dilim (8 hafta)

| Hafta | İş | Kim | Model | Bitti ölçütü |
| --- | --- | --- | --- | --- |
| 16–22 Kas | Dinleme: hareket kilidi, ses çizgisi (Shader Graph özel düğümü), fener ışığı, Toprak kamera kademesi | Masaüstü (`unity:shader-graph-create-custom-node`, `unity:urp-postprocessing`) | Opus 5.5 | Bir ses kaynağı dinlerken ince ışık çizgisi olarak görünüyor; yön veriyor, cevap vermiyor |
| 23–29 Kas | R1-01 tam kalite (öğretici, sözsüz); taşın üç kanalı: ses, titreşim, dalga çizgisi | Masaüstü + Sen (malzeme) | Opus 5.5 | Metinsiz ilk oda; perde değişince üç kanal birlikte değişiyor |
| 30 Kas–6 Ara | R1-02, R1-03; hâl kestirmesi; makam sayacı | Masaüstü | Sonnet 5.5 | Üç oda uçtan uca; uzun yol seçilince kulede nota asılı kalıyor |
| 7–13 Ara | Kasaba bugün çağı: dem takma, vakit gölgesi, sır söyleme eylemi ve ilk sırrın öğretilmesi (sistemler.md §4) | Masaüstü | Opus 5.5 | Toprak'tan çıkan oyuncu çobanı yolda buluyor; söyle/sakla iki yolu da çalışıyor |
| 14–20 Ara | Su gri kutu (`RoomTimeline` + `Tide`, R2-01) ve Gölge gri kutu (`ReverseRecorder`, R4-02) | Masaüstü + Bulut (Core ekleri) | Opus 5.5 (xhigh) | Geri sarma dalı kesiyor; gölgedeki saatçi oyuncunun kaydını tersten yürüyor |
| 21–27 Ara | Ayna gri kutu (`RecordLedger`, kitabe harfi, R5-04 geri alma); köpek ipucu zamanlayıcısı; kilometre taşı kaydı | Masaüstü | Sonnet 5.5 | Kayıt değişince kasabadaki nesne ve kitabe değişiyor; oyundan çıkıp girince odanın kilometre taşından devam |
| 28 Ara–3 Oca | Açılış (kule, çarklar, kapak, iniş); altyazı, titreşim, renk körlüğü kontrolü; cila | Masaüstü + Sen | Sonnet 5.5 | Yeni oyun → kule → kapak → R1-01 kesintisiz; altyazı ve titreşim açık/kapalı |
| 4–10 Oca | **K1:** beş oyuncu, ekran kaydı (OBS) ve form | Sen | Opus 5.5 (bulguların okunması) | Dinleme anlaşılıyor; 5 oyuncudan en az 4'ü S1'de söyleme eylemini fark etti; üç gri kutu çalışıyor; oda başına süre ≤ 3 dk |

## K1 sonrası

K1 ölçütleri sağlanırsa Şubat başında Steam sayfası açılır (K-11) ve halka üretimi Toprak'tan başlar. Sağlanmazsa yalnız başarısız ölçüt üzerinde iki haftalık düzeltme turu yapılır; takvimin geri kalanı iki hafta kayar, kapsam değişmez.

## Oturum başına kural

- Her oturum `CLAUDE.md` ile açılır ve bu tablodan tek bir satırı hedefler.
- Core'a dokunan her oturum `dotnet test kirk-dem/tools/core-tests` yeşil olmadan biter sayılmaz; PR'da CI aynı testi koşar.
- Bir satırın "bitti" ölçütü sağlanmadan bir sonraki satıra geçilmez.

# Kırk Dem — Claude için çalışma kuralları

Bu klasör Kırk Dem'in (Unity 6, URP, 5–8 saatlik anlatı-bulmaca) tek kaynağıdır. Buradaki her değişiklik önce `docs/00-dunya-kitabi.md` ile, sonra `docs/01-senaryo-kilidi/` ile uyumlu olmalıdır. Çelişkide dünya kitabı kazanır; dünya kitabını değiştiren bir karar önce orada yazılır.

## Bağlayıcı ilkeler (kodda, metinde, varlıkta)

- Oyun hiçbir şeyi kesinleştirmez. Bir cümle, bir sahne ya da bir kod yorumu olanların keramet mi, rüya mı, yorgun bir zihnin algısı mı olduğunu söylerse hatalıdır.
- Söylenmeyecekler listesi (dünya kitabı, "Senaryo omurgası" sonu) oyun içi metin, altyazı, başarım adı, Steam metni ve sinematik için mutlaktır.
- Kavram adları (nefs, hâl, makam, tayy, bast, ân, keramet) yalnız `docs/` içinde ve kod yorumlarında geçer; oyuncunun görebileceği hiçbir yerde geçmez. Kodda teknik adlar kullanılır (`FoldedSlow`, `Tidal`, `BreathHeld`…).
- Gerçek kişi, tarikat, veli, kam ya da efsane kahramanı adı hiçbir yerde kullanılmaz. Tek özel ad babanın adıdır (`DURSUN`, `docs/01-senaryo-kilidi/diyalog-ilkeleri.md`).
- Olmayanlar: savaş, ölüm ekranı, envanter, harita, görev listesi, başarım bildirimi, puan, seviye, yetenek ağacı. Bunlardan birini ekleyen bir öneri reddedilir.
- Her işitsel ipucunun görsel ve dokunsal eşi vardır (ADR 0007). Yalnız sese dayanan bir mekanik kabul edilmez.
- Yeni mekanik eklenmez; her halka tek fikri derinleştirir. Bir odanın bulmacası halkanın fikrine uymuyorsa oda yanlıştır, fikir değil.

## Kimlikler (değişmez)

Halkalar `toprak su nefes golge ayna sessizlik an`; odalar `R{halka}-{oda:00}` (R1-01…R7-01); kasabalılar `degirmenci degirmenci-kizi kahveci imam ebe coban muhtar`; çağlar `bugun bir-yil kirk-yil terk`; sırlar `S1..S7`; sonlar `donus kalis dagitis`. Tanım: `docs/03-mimari/veri-modeli.md`.

## Nerede ne var

| Konu | Dosya |
| --- | --- |
| Dünya, ilkeler, omurga | `docs/00-dunya-kitabi.md` |
| 40 oda, 7 kasabalı × 4 çağ, 7 sır, mısralar, diyalog | `docs/01-senaryo-kilidi/` |
| Palet, ışık, kamera, karakter, Flow üslup kitabı | `docs/02-sanat-kitabi/` |
| Sistemler, veri modeli, oda kiti, ses, ADR'ler | `docs/03-mimari/` |
| Çalışma yöntemi, model ve eklenti yönlendirmesi | `docs/04-calisma-yontemi.md` |
| Acımasız analiz: bulgular ve uygulananlar | `docs/05-acimasiz-analiz.md` |
| Karar kaydı: 17 karar, gerekçe ve geri dönüş tetikleyicisi | `docs/06-karar-kaydi.md` |
| Hassasiyet okuması brifi | `docs/07-hassasiyet-okumasi.md` |
| Çekirdek için Unity'siz test projesi | `tools/core-tests/` |
| Unity kod iskeleti (saf C# çekirdek + Unity kabuk + EditMode testleri) | `unity/Assets/_KirkDem/` |

## Kod kuralları

- `KirkDem.Core` UnityEngine'e bağımlı olamaz (`noEngineReferences: true`). Kural kararı Core'da verilir; MonoBehaviour'lar yalnız sunar ve iletir.
- Zincirleme etkilerin tek yeri `GameState`. Sır → kat → taş zinciri başka yerde tekrarlanmaz.
- Veri ScriptableObject'tedir; kodda sabit oda/kasabalı listesi yazılmaz (`RingCatalog` dışında).
- Core değişince `Tests/EditMode` testleri güncellenir ve `dotnet test kirk-dem/tools/core-tests` yeşil olmadan commit edilmez. Aynı testler GitHub Actions'ta her PR'da ve Unity Test Runner'da koşar. Core C# 9 ile sınırlıdır (Unity 6).
- Bir karar değişirse önce `docs/06-karar-kaydi.md` güncellenir, sonra ona bağlı dokümanlar ve kod.
- Türkçe: dokümanlar, yorumlar, commit mesajı gövdesi. İngilizce: tanımlayıcılar, dosya adları (kod), commit başlığı serbest.
- Model kimliği, oturum bağlantısı gibi şeyler commit'e, PR'a ya da varlığa yazılmaz.

## Çalışma biçimi

- Senaryo kilidinin kanonik yeri Claude Docs'taki "Senaryo kilidi" sekmesidir; `docs/01-senaryo-kilidi/` onun depo kopyası artı uygulama katmanıdır. Depoda alınan bir karar sekmeye taşınmadan kilit sayılmaz.
- Senaryo kilitlenmeden mekân modellenmez; dikey dilim beğenilmeden kırk oda yapılmaz (üretim planı sırası).
- Bir dokümanı değiştiren karar aynı commit'te ona bağlı dokümanları da günceller (örn. ad değişirse `diyalog-ilkeleri.md` + `GameRoot.inscriptionLetters` + sanat kitabı kitabe bölümü).
- Açık kararlar listesi (dünya kitabı sonu) kapatılmadan "kesin" diye yazılmaz; `[ ]` işareti korunur.
- Model ve eklenti seçimi için `docs/04-calisma-yontemi.md` tablosuna uyulur.

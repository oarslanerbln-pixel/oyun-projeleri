# Bu repoda çalışan Claude için

Ayrıntılı kurallar: `platform/docs/uretim-standardi.md`. Bu dosya her oturumun her adımında okunur, o yüzden kısa tutulur.

**Nerede ne var:** `HARITA.md` (repo ve `/mnt/project-files`). Klasör taramadan önce oraya bak; yeni teslim, final ya da şablon ekleyen thread oradaki satırı da günceller.

## Token disiplini (2026-10-19 ölçümü: harcamanın %69'u geçmişin yeniden okunması)

Her araç çağrısı thread'in bütün bağlamını yeniden okur. Bir thread ~130k token ile başlar ve 300k'yı geçince her adım iki kat pahalıdır. Maliyet ≈ adım sayısı × bağlam boyu; ikisini de küçük tut.

1. **Az adım.** Birbirine bağlı olmayan komutları tek Bash çağrısında `&&` ile birleştir; aynı dosyayı tekrar tekrar okuma, bir kez oku. Bekleme, durum sorgulama ve "bir bakayım" adımlarını birleştir.
2. **Kısa çıktı.** Uzun süren ya da çok yazan komutları `python3 platform/ortak/sessiz.py -- <komut>` ile çalıştır (tam log dosyaya, ekrana yalnız son satırlar ve hatalar). ffmpeg'e `-hide_banner -loglevel error`, Blender'a `> log 2>&1`. Büyük JSON'u (`get_session`, `list_events`, API cevapları) olduğu gibi okuma; `jq`/python ile gereken alanı çek.
3. **Görüntü yerine rapor.** Kareleri tek tek açma: `kalite.json` + tek kontakt sayfası, önizlemede yalnız `onizleme.png`.
4. **Thread'i büyütme.** Thread ~250k bağlama ya da ~12 cevaba ulaştıysa yeni tur başlatma: `platform/ortak/devir.py <klasör> --not "..."` ile `DEVIR.md` yaz, Atilla'ya "devam yeni thread'de" de ve koordinatörden yeni thread iste. Yeni thread yalnız `DEVIR.md` + brif okur.
5. **Alt ajan pahalıdır.** Her alt ajan ~60–70k token ile başlar. Yalnız gerçekten paralel ve ağır işte kullan; tek dosya okumak, birkaç komut çalıştırmak için kullanma.
6. **Uzun bekleme sonrası.** Render ya da Atilla'nın cevabı bir saatten uzun sürdüyse önbellek düşer ve bütün bağlam yeniden yazılır (en pahalı token türü). Büyük bir thread'e saatler sonra dönülecekse yeni thread + `DEVIR.md` daha ucuzdur.
7. **Sipariş tek komutla.** Video siparişinde `.claude/skills/siparis-uretimi/SKILL.md` adımlarını izle (`platform/ortak/uret.py siparis.json`); akışı elle yeniden kurma.

---
name: siparis-uretimi
description: Stüdyoda bir video siparişini (brif, panel siparişi, "yeni siparişi üret", revizyon) üretirken kullan; siparis.json yazıp platform/ortak/uret.py ile önizleme + animatik → onay → ses + render + kalite + DEVIR + katalog + maliyet akışını tek komutla yürütür, panel siparişinin durumunu panele geri yazar.
---

# Sipariş üretimi

Kurallar `platform/docs/uretim-standardi.md`'de; bu dosya yalnız komut sırasıdır. Yolu sıfırdan arama, şablon kodu okuma.

0. **Önce katalog.** Brif eski bir işe benziyorsa ("geçen ayki kahve videosu, Almanca") `python3 platform/ortak/katalog.py ara <kelime>`; bulunan kaydın `senaryo` ve `klasor` alanından başla.
1. **Panelden gelen sipariş** ("yeni siparişi üret", panel: https://claude.ai/artifact/Rpwozz6cNbi3XCHjQTDkxy):
   `ArtifactData query` (url = panel, collection `siparisler`, durum `yeni`) → en eskisini `get` ile al, sonucu bir JSON dosyasına yaz →
   `python3 platform/ortak/panel.py siparis <kayit.json>` → `PF/<is>/siparis.json`, `brif.md` ve (tarz seçildiyse) örnek senaryo hazır. 3. adımdan devam.
2. **Brifle gelen sipariş.** Klasör `/mnt/project-files/<is>/` (müşteri dosyaları repoya girmez). Stilin örneğini kopyala (`ornekler/*/<stil>.json`). `siparis.json`:
   ```json
   {"is": "<kısa-ad>", "baslik": "<Atilla'nın başlığı>",
    "senaryolar": [{"stil": "tek-cizgi", "senaryo": "tek-cizgi.json"}],
    "format": "9:16", "dil": "tr", "ses": {"ses": "<ses adı ya da id>"}, "musteri": "<varsa>", "notlar": ["brifteki kararlar"]}
   ```
   Atilla "direkt üret" dediyse `"direkt": true`.
3. **Senaryo:** örnek senaryonun metnini brife göre değiştir. Birden çok stil istendiyse her stil için bir senaryo.
4. **Önizleme:** `python3 platform/ortak/uret.py <klasör>/siparis.json` → `onizleme.png` + `animatik.mp4` (küçük, sessiz, ~3x hızlı hareket taslağı). Yalnız önizleme görüntüsüne bak; ikisini senaryo metniyle birlikte `attached_outputs` ile Atilla'ya gönder ve onay bekle. Komut burada durur.
5. **Onaydan sonra:** `python3 platform/ortak/uret.py <klasör>/siparis.json --onay [--stil <seçilen>]`. Ses (ElevenLabs; Piper yedeğine düşerse durur), yalnız siparişteki format, kalite kapısı, `DEVIR.md`, teslim kataloğu. Çıktı kısa: her video için GEÇTİ/KALDI, render süresi ve bulgular. `KALDI` teslim edilmez: senaryoyu düzelt, `--onay` yeniden.
6. **Teslim:** videoları ve kontakt sayfasını `attached_outputs` ile gönder; `uyarili` ise nedenini bir cümleyle yaz, harcanan ElevenLabs karakterini söyle.
7. **Kapanış:** `get_session` (oturum kimliği boş) → `external_metadata.usage` alanlarını jq/python ile çek, sonra
   `python3 platform/ortak/uret.py <klasör>/siparis.json --kapat --usd <usd> --cevap <n> --cikti-token <n> --okuma-token <n> [--revizyon <n>]`. Thread'i kapat.

**Panel durumu:** sipariş panelden geldiyse `uret.py` her aşamadan sonra `panel: ArtifactData update ...` satırını basar. 4., 5. ve 7. adımın sonunda o satırdaki gibi `ArtifactData update` (collection `siparisler`, doc_id, `file_path` = `<klasör>/panel-durum.json`) çağır; panelde durum yeni → onayını bekliyor → üretimde → hazır olarak ilerler ve Claude'un notu görünür.

Durum her an: `uret.py <siparis.json> --durum` (aşama `siparis-durum.json`'da). Revizyon yeni thread'de `DEVIR.md` + bu dosya ile başlar.
Render süreleri `/mnt/project-files/gelistirme/render-sureleri.csv`'ye ve her `kalite.json`'un `render` alanına, teslimler `/mnt/project-files/gelistirme/katalog.jsonl`'a yazılır.

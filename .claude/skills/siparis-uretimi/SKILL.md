---
name: siparis-uretimi
description: Stüdyoda bir video siparişini (brif, panel siparişi, revizyon) üretirken kullan; siparis.json yazıp platform/ortak/uret.py ile önizleme → onay → ses + render + kalite + DEVIR + maliyet akışını tek komutla yürütür.
---

# Sipariş üretimi

Kurallar `platform/docs/uretim-standardi.md`'de; bu dosya yalnız komut sırasıdır. Yolu sıfırdan arama, şablon kodu okuma.

1. **Klasör ve senaryo.** Teslim klasörü `/mnt/project-files/<is>/` (müşteri dosyaları repoya girmez). Stilin örneğini kopyala (`ornekler/*/<stil>.json`), metni brife göre değiştir. Birden çok stil istendiyse her stil için bir senaryo.
2. **siparis.json** (klasörde):
   ```json
   {"is": "<kısa-ad>", "baslik": "<Atilla'nın başlığı>",
    "senaryolar": [{"stil": "tek-cizgi", "senaryo": "tek-cizgi.json"}],
    "format": "9:16", "ses": {"ses": "<ses adı ya da id>"}, "notlar": ["brifteki kararlar"]}
   ```
   Atilla "direkt üret" dediyse `"direkt": true`.
3. **Önizleme:** `python3 platform/ortak/uret.py <klasör>/siparis.json` → `onizleme.png`. Yalnız bu görüntüye bak, Atilla'ya senaryo metniyle birlikte gönder ve onay bekle. Komut burada durur.
4. **Onaydan sonra:** `python3 platform/ortak/uret.py <klasör>/siparis.json --onay [--stil <seçilen>]`. Ses (ElevenLabs; Piper yedeğine düşerse durur), yalnız siparişteki format, kalite kapısı, `DEVIR.md`. Çıktı kısa: her video için GEÇTİ/KALDI, render süresi ve bulgular. `KALDI` teslim edilmez: senaryoyu düzelt, `--onay` yeniden.
5. **Teslim:** videoları ve kontakt sayfasını `attached_outputs` ile gönder; `uyarili` ise nedenini bir cümleyle yaz, harcanan ElevenLabs karakterini söyle.
6. **Kapanış:** `get_session` (oturum kimliği boş) → `external_metadata.usage` alanlarını jq/python ile çek, sonra
   `python3 platform/ortak/uret.py <klasör>/siparis.json --kapat --usd <usd> --cevap <n> --cikti-token <n> --okuma-token <n> [--revizyon <n>]`. Thread'i kapat.

Durum her an: `uret.py <siparis.json> --durum` (aşama `siparis-durum.json`'da). Revizyon yeni thread'de `DEVIR.md` + bu dosya ile başlar.
Render süreleri `/mnt/project-files/gelistirme/render-sureleri.csv`'ye ve her `kalite.json`'un `render` alanına yazılır.

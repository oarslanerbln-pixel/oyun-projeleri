# ADR-0005 — Kasabada zaman eylemle ölçülür, saniyeyle değil

**Durum:** Kabul edildi · 2026-10-16 (dış inceleme sonrası dünya kitabına işlenen karar)

## Bağlam
Kasabada zaman tek yönlü akar ve geri gelmez. Gerçek süreyle ölçülürse oyuncu bakmakla cezalandırılır ve bedel rastgele hissedilir; "zaman kuralı bulmaca değil, bedel olarak hissedilmelidir."

## Karar
`TownClock.Vakit` yalnız eylemle ilerler: her konuşma, her sır söyleme, her kor takma +1. Dolaşmak, bakmak, beklemek vakit ilerletmez. Çağ geçişi yalnız halka çıkışında olur. Vakit, kulenin meydana düşen gölgesiyle gösterilir (güneş saati); sayı hiçbir yerde yazılmaz.

## Sonuçlar
- Bedel deterministik ve oyuncunun eliyledir; kayıt da anında güvenlidir (her eylem kaydedilir).
- Kasaba sahnesinde `Update` tabanlı zaman yok; gün döngüsü yok.
- Bedel: "beklemek" kasabada anlamsızdır; bu dünya kitabıyla uyumludur (beklemek Toprak halkasının işidir).

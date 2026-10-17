# ADR-0007 — Ses → görsel → dokunsal: tek kaynak, üç kanal zorunlu

**Durum:** Kabul edildi · 2026-10-16

## Bağlam
Oyunun omurgası sestir; dinleme tek yetenektir. İşitme engelli ya da sessiz ortamda oynayan oyuncu için oyun oynanamaz hale gelmemeli. Erişilebilirlik dekor değil, dikey dilimden itibaren mekaniğin parçasıdır. Ayrıca Sessizlik halkası ses kanalını tasarım gereği tamamen kapatır; görsel ve dokunsal kanal zaten gereklidir.

## Karar
Her işitsel değer tek bir sayısal kaynaktan türetilir ve üç kanala **aynı fonksiyonla** eşlenir: `PitchMap.Frequency`, `PitchMap.HapticRate`, `PitchMap.RippleDensity`. Audio, Haptics ve Presentation kendi tablolarını tutmaz. Her `AudioEmitter`in `subtitleKey`i vardır. Bir ses ipucu eklenirken görsel ve dokunsal eşi olmadan PR kabul edilmez (kod incelemesi kuralı).

Ayarlar arayüzü "arayüz yok" ilkesinden muaftır; klasik ve okunurdur.

## Sonuçlar
- Sessizlik halkasının kanal devri (`ses-mimarisi.md §6`) ek sistem değil, aynı mimarinin doğal sonucudur.
- Renk tek başına bilgi taşımaz; halka vurgu renklerinin doku/şekil eşi sanat kitabında tanımlanır.
- Bedel: her emitter için üç varlık (clip, çizgi parametresi, altyazı anahtarı). Room Scaffold aracı bunları birlikte üretir.

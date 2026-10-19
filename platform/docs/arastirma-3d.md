# Gerçekçi 3D için hangi teknoloji? (2026-10-18)

Soru: React Three Fiber, WebGL (three.js), GSAP… gerçekçi 3D reklam videosu üretmek için hangisi mantıklı?
Ölçüt: bu bulut kapsayıcısında (4 CPU çekirdeği, GPU yok, başsız) **kare kare, deterministik** video render.

## Kısa cevap

**Gerçekçi 3D için Blender (Cycles, `pip install bpy`) kullanalım.** three.js'i (ve onun üstündeki R3F/Remotion'ı) hızlı, stilize 3D için tutalım. GSAP bir zamanlama kütüphanesi, render etmez.

## Karşılaştırma

| Araç | Ne işe yarar | Bu kapsayıcıda kuruluyor mu? | Ölçülen / beklenen maliyet | Gerçekçilik |
|---|---|---|---|---|
| **three.js (WebGL)** | Tarayıcıda gerçek zamanlı 3D; PBR malzeme, HDRI, gölge haritası, DOF son-işlemi | Evet (npm + Playwright Chromium, SwiftShader ile CPU'da WebGL) | Ölçüldü: **~1.6 sn/kare** 1080×1920 (ürün vitrini, PR #12) | Orta. Rasterleştirme: cam kırılması, yumuşak alan gölgesi, dolaylı ışık (GI) yaklaşık/sahte. "Güzel ama CG" görünür |
| three.js + three-gpu-pathtracer | three.js sahnesini WebGL2 shader'ında yol izleme (path tracing) | Teoride evet, ama SwiftShader (CPU'da taklit edilen GPU) üzerinde shader ile yol izleme çok yavaş | Ölçülmedi; CPU-WebGL'de Cycles'tan yavaş olması beklenir | Yüksek, ama kare başına çok örnek ister |
| **React Three Fiber (R3F)** | three.js için React sarmalayıcı (bileşen olarak sahne yazma) | Evet | three.js ile **aynı** (render motoru three.js); React katmanı küçük ek yük getirir | three.js ile aynı. Kod düzeni kazancı var, görüntü kazancı yok |
| **Remotion + @remotion/three** | React ile video kurgusu; R3F sahnesini `useCurrentFrame()` ile kareye bağlar, MP4'e render eder | Evet (npm + Chromium) | three.js ile aynı + Remotion çerçeve yükü. Ticari kullanımda şirket lisansı gerekebilir | three.js ile aynı |
| **GSAP** | Animasyon zamanlaması / easing / timeline | Evet (npm) | Yok denecek kadar az | **Render etmez.** Kamera/nesne koreografisi için kullanılabilir; biz aynı işi t'nin saf fonksiyonlarıyla zaten yapıyoruz |
| **Blender Cycles (bpy)** | Fiziksel tabanlı yol izleme: gerçek kırılma, alan ışığı yumuşak gölgeleri, GI, gerçek optik DOF, OpenImageDenoise | **Evet, test edildi**: `pip install bpy` (5.2.2 LTS, ~20 sn), ek paket gerekmedi | Ölçüldü: **~30–45 sn/kare** 1080×1920, 12 örnek + OIDN gürültü giderme (cam şişe sahnesi). 10 sn @24 fps ≈ 2,5–3 saat CPU | **En yüksek.** Ürün fotoğrafına en yakın sonuç |
| Blender EEVEE (bpy) | Blender'ın gerçek zamanlı (rasterleştirme) motoru | Evet ama Mesa/llvmpipe (`apt install libegl1 libegl-mesa0 libgl1-mesa-dri`) gerekiyor | Ölçüldü: basit sahne 540×960 tek kare 37 sn (CPU'da OpenGL taklidi, shader derlemesi dahil) | three.js'ten iyi, Cycles'tan düşük. CPU'da avantajı yok |

## Neden Blender Cycles?

1. **Görüntü farkı gerçek:** amber cam + serum + pipet üst üste kırılıyor, jaluzi gölgesi yumuşak geçişli, travertende dolaylı ışık var. three.js'te bunların hepsi sahte efektle taklit edilir ve göz farkı yakalar.
2. **Kurulum sorunsuz:** `pip install bpy` bu kapsayıcıda çalıştı. Sahne tamamen Python kodu (`kaynak/sahne.py`), mevcut numpy/ffmpeg hattımızla aynı dilde. Şablona dönüştürmek kolay.
3. **Ölçeklenir:** aynı kod GPU'lu makinede (NVIDIA OptiX/CUDA veya Apple Metal) 50–100 kat hızlı çalışır. Kare başı 40 sn → ~0,5 sn. Bulutta kiralık GPU ile 10 sn'lik video birkaç dakikada biter.
4. **3D model girdisi:** müşteri .glb/.fbx/.obj verirse Blender doğrudan içe aktarır (vitrin şablonu zaten .glb kabul ediyor).

Bedeli: CPU'da yavaş. Bu yüzden iş akışı **önce 3–4 önizleme karesi (yarım çözünürlük, ~15 sn/kare), onaydan sonra tek final render** olmalı. Hacim artınca GPU şart.

## Ne zaman hangisi

- **Gerçekçi ürün çekimi, kozmetik, içecek, cam/metal:** Blender Cycles.
- **Stilize 3D (oyuncak dünya, izometrik, ikon/logo animasyonu), hızlı teslim:** three.js (mevcut hat, ~1,6 sn/kare).
- **R3F / Remotion:** ekip React ile çalışacaksa ya da web sitesinde canlı 3D gösterilecekse anlamlı. Video kalitesine katkısı yok.
- **GSAP:** web/HTML animasyonlarında zamanlama için iyi; offline render hattımızda gerekmiyor.

## Bu testte kullanılan ayarlar (gerçekçi 3D)

Cycles CPU, 12 örnek + uyarlamalı örnekleme (eşik 0.03) + OpenImageDenoise, sabit tohum (titreme azaltır), kostikler kapalı, 16 bit PNG kareler, AgX renk dönüşümü, 24 fps, 1080×1920. Işık: Blender'ın kendi stüdyo HDRI'si (interior.exr, düşük güç) + güneş ve jaluzi (gobo) + iki alan ışığı + arkadan süpüren ince şerit ışık. Kamera: 100 mm f/2.4 yakın plandan 70 mm f/4 geniş plana kesintisiz Hermite eğrisiyle geçiş.

## Kaynaklar

- Blender as a Python Module (resmî belge): https://docs.blender.org/api/5.0/info_advanced_blender_as_bpy.html
- bpy PyPI paketi: https://pypi.org/project/bpy/ (bu kapsayıcıda kurulan sürüm 5.2.2)
- Remotion + React Three Fiber: https://www.remotion.dev/docs/three (render için Chromium'da ANGLE önerisi, `useCurrentFrame` ile kare bağlama)
- three-gpu-pathtracer: https://github.com/gkjohnson/three-gpu-pathtracer (WebGL2 shader'ında yol izleme)
- Ebru yöntemi: Jaffer & Lu, "Mathematical Marbling", IEEE Computer Graphics and Applications, 2012 (ebru testinde kullanıldı)
- Ölçümler: bu kapsayıcıda 2026-10-18'de yapıldı (Cycles, EEVEE/llvmpipe); three.js süresi ürün vitrini şablonundan (PR #12).

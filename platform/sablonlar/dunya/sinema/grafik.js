// Anlatım grafiği stilleri (ok, cephe, ülke, etiket, şehir, veri kartı, birlik, başlık, kutu).
// sahne.js bir stil nesnesi alır; stilde olmayan parça sahne.js'teki "belgesel" çizimine düşer.
// Stil seçimi: sahne JSON "grafik": "haber" | "gravur" | "istihbarat" | "kroki" | "editoryal" (varsayılan belgesel).
// Renk ve yazı değerleri marka.json -> grafikler.<ad>; burada yalnız biçim ve hareket (easing/zamanlama) var.
// Gerekçeler: platform/docs/harita-tasarim-dili.md §4c.

export function grafikKur(A) {
  const { M, T, SS, W, H, dil, hex, renk, fpx, eo, eoq, eio, ara, sinir, kirpYol, yolUzun, rng, desen, tuval } = A;
  const ad = M.grafik || "belgesel";
  // ---------- easing sözlüğü (motion tasarım temeli) ----------
  const backOut = (x, s = 1.70158) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
  const sio = (x) => -(Math.cos(Math.PI * x) - 1) / 2;
  const expo = (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x));
  const ust = (s) => String(s).toLocaleUpperCase(dil === "de" ? "de" : "tr");
  const sayi = (v, ond) => v.toLocaleString(dil === "de" ? "de-DE" : "tr-TR", { maximumFractionDigits: ond ?? 0, minimumFractionDigits: ond ?? 0 });
  const dikey = H > W;
  const G = M.guvenli, gx = (dikey ? G.dikey[0] : G.yatay[0]) * W * SS;
  const kiskac = (x, w) => sinir(x, gx, W * SS - gx - w);
  function aciklik(c) { const n = parseInt(c.slice(1), 16); return (0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255; }
  function genislik(g, met, aralik) { return g.measureText(met).width + aralik * met.length; }
  function yaz(g, met, x, y, aralik) { if ("letterSpacing" in g) { g.letterSpacing = `${aralik}px`; g.fillText(met, x, y); g.letterSpacing = "0px"; } else g.fillText(met, x, y); }
  function yazKontur(g, met, x, y, aralik) { if ("letterSpacing" in g) { g.letterSpacing = `${aralik}px`; g.strokeText(met, x, y); g.letterSpacing = "0px"; } else g.strokeText(met, x, y); }
  function sigdir(g, fontFn, boy, met, aralikOran, maxW) { g.font = fontFn(boy); const w = genislik(g, met, boy * aralikOran); return w > maxW ? boy * maxW / w : boy; }
  // harf harf çizim: alfa(i) her harfin görünürlüğü (mürekkep / daktilo açılışları)
  function harfHarf(g, met, x, y, aralik, alfa, kontur) {
    let cx = x; const a0 = g.globalAlpha;
    for (let i = 0; i < met.length; i++) { const ch = met[i], al = alfa(i); const w = g.measureText(ch).width;
      if (al > 0) { g.globalAlpha = a0 * al; if (kontur) g.strokeText(ch, cx, y); g.fillText(ch, cx, y); } cx += w + aralik; }
    g.globalAlpha = a0;
  }
  // yol boyunca eşit aralıklı noktalar: fn(x, y, dx, dy, s)
  function boyunca(yol, aralik, fn, bas = aralik / 2) {
    let acc = 0, s = bas;
    for (let i = 1; i < yol.length; i++) { const a = yol[i - 1], b = yol[i], l = Math.hypot(b[0] - a[0], b[1] - a[1]); if (!l) continue; const dx = (b[0] - a[0]) / l, dy = (b[1] - a[1]) / l;
      while (s - acc <= l) { const f = s - acc; fn(a[0] + dx * f, a[1] + dy * f, dx, dy, s); s += aralik; } acc += l; }
  }
  // inen gövdeli ok silueti (gövde + uç, istenirse çatallı kuyruk). y: kırpılmış yol (px)
  function okSekli(y, gen, o = {}) {
    const n = y.length; if (n < 2) return null;
    const bas = o.bas ?? 0.42, ucBoy = gen * (o.ucBoy ?? 2.3), ucGen = gen * (o.ucGen ?? 1.05), L = yolUzun(y);
    const yg = kirpYol(y, Math.max(0.0001, 1 - ucBoy * 0.55 / Math.max(1, L))), m = yg.length, sol = [], sag = [];
    let s = 0; const Lg = Math.max(1, yolUzun(yg));
    for (let i = 0; i < m; i++) { if (i) s += Math.hypot(yg[i][0] - yg[i - 1][0], yg[i][1] - yg[i - 1][1]);
      const a = yg[Math.max(0, i - 1)], b = yg[Math.min(m - 1, i + 1)]; let dx = b[0] - a[0], dy = b[1] - a[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
      const w = gen * (bas + (1 - bas) * (s / Lg)) / 2; sol.push([yg[i][0] - dy * w, yg[i][1] + dx * w]); sag.push([yg[i][0] + dy * w, yg[i][1] - dx * w]); }
    const u = y[n - 1], o_ = y[Math.max(0, n - 4)]; let dx = u[0] - o_[0], dy = u[1] - o_[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
    const taban = yg[m - 1], uc = [u[0] + dx * ucBoy * 0.45, u[1] + dy * ucBoy * 0.45];
    const b0 = yg[0], b1 = yg[Math.min(m - 1, 3)]; let ex = b1[0] - b0[0], ey = b1[1] - b0[1]; const el = Math.hypot(ex, ey) || 1; ex /= el; ey /= el;
    const ciz = (g) => { g.beginPath(); g.moveTo(...sol[0]); sol.forEach((q) => g.lineTo(...q));
      g.lineTo(taban[0] - dy * ucGen, taban[1] + dx * ucGen); g.lineTo(...uc); g.lineTo(taban[0] + dy * ucGen, taban[1] - dx * ucGen);
      for (let i = m - 1; i >= 0; i--) g.lineTo(...sag[i]);
      if (o.kuyruk) g.lineTo(b0[0] + ex * gen * bas * 0.7, b0[1] + ey * gen * bas * 0.7);
      g.closePath(); };
    ciz.uc = uc; ciz.yon = [dx, dy]; ciz.govde = yg; return ciz;
  }
  function cizgi(g, pts) { g.beginPath(); pts.forEach((q, i) => (i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1]))); }
  // el titremesi: yay uzunluğuna bağlı iki sinüs (kararlı); tohum değişince "boil"
  function titret(pts, amp, tohum) {
    const r = rng(1000 + tohum * 7919), f1 = r() * 6.28, f2 = r() * 6.28, l1 = 40 + r() * 30, l2 = 11 + r() * 8; let s = 0;
    return pts.map((q, i) => { if (i) s += Math.hypot(q[0] - pts[i - 1][0], q[1] - pts[i - 1][1]);
      const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)]; let dx = b[0] - a[0], dy = b[1] - a[1]; const l = Math.hypot(dx, dy) || 1;
      const o = amp * (0.7 * Math.sin(s / l1 + f1) + 0.3 * Math.sin(s / l2 + f2)); return [q[0] - dy / l * o, q[1] + dx / l * o]; });
  }
  const boil = () => Math.floor((G_.zaman || 0) * 8); // 8 fps el çizimi titreşimi
  function elDikdortgen(g, x, y, w, h, amp, tohum) { const p = [[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y + amp * 0.6]]; const ince = [];
    for (let i = 1; i < p.length; i++) for (let j = 0; j <= 10; j++) ince.push([p[i - 1][0] + (p[i][0] - p[i - 1][0]) * j / 10, p[i - 1][1] + (p[i][1] - p[i - 1][1]) * j / 10]);
    cizgi(g, titret(ince, amp, tohum)); }
  // tuval desenleri
  function noktaDesen(g, renk_, aralik, r_) { const p = tuval(Math.max(2, Math.round(aralik)), Math.max(2, Math.round(aralik))), x = p.getContext("2d"); x.fillStyle = renk_; x.beginPath(); x.arc(p.width / 2, p.height / 2, r_, 0, 7); x.fill(); return g.createPattern(p, "repeat"); }
  // NATO çerçeveli birlik işareti, parametrik
  function birlikP(g, x, y, k, a, o) {
    const r = renk(k.rol || "dost"), b = fpx(o.boy ?? 0.034), w = b * 1.5, h = b, dus = k.taraf === "dusman";
    g.save(); g.globalAlpha = a; g.translate(x, y); g.lineJoin = "round"; g.lineCap = "round";
    const sekil = () => { g.beginPath(); if (dus) { g.moveTo(0, -h * 0.85); g.lineTo(w * 0.62, 0); g.lineTo(0, h * 0.85); g.lineTo(-w * 0.62, 0); g.closePath(); }
      else if (o.el) elDikdortgen(g, -w / 2, -h / 2, w, h, b * 0.05, boil() + 3); else g.rect(-w / 2, -h / 2, w, h); };
    if (o.golge) { g.save(); g.translate(b * 0.1, b * 0.14); sekil(); g.fillStyle = o.golge; g.fill(); g.restore(); }
    if (o.parilti) { g.shadowColor = r.kontur; g.shadowBlur = b * 0.5; }
    sekil(); g.fillStyle = o.zemin ?? r.dolgu; g.fill(); g.shadowBlur = 0;
    if (o.bant) { g.save(); sekil(); g.clip(); g.fillStyle = hex(r.dolgu, 0.85); g.fillRect(-w / 2, -h / 2, w, h * 0.22); g.restore(); }
    g.lineWidth = Math.max(1.5, b * (o.kal ?? 0.08)); g.strokeStyle = o.kenar ?? "#fff"; sekil(); g.stroke();
    g.strokeStyle = o.ic ?? o.kenar ?? "#fff"; g.beginPath(); const iw = w * 0.32, ih = h * 0.26, s = k.sembol || "piyade", m = b * 0.08;
    if (s === "piyade" || s === "mekanize") { g.moveTo(-w / 2 + m, -h / 2 + m); g.lineTo(w / 2 - m, h / 2 - m); g.moveTo(w / 2 - m, -h / 2 + m); g.lineTo(-w / 2 + m, h / 2 - m); }
    if (s === "zirhli" || s === "mekanize") { g.moveTo(iw, 0); g.ellipse(0, 0, iw, ih, 0, 0, 7); }
    if (s === "suvari") { g.moveTo(-w / 2 + m, h / 2 - m); g.lineTo(w / 2 - m, -h / 2 + m); }
    g.stroke(); if (s === "topcu") { g.beginPath(); g.arc(0, 0, b * 0.12, 0, 7); g.fillStyle = o.ic ?? "#fff"; g.fill(); }
    g.textAlign = "center";
    if (k.kademe) { g.fillStyle = o.metin ?? "#fff"; g.font = `700 ${Math.round(b * 0.42)}px "${o.font2 ?? "Barlow Condensed"}"`; g.textBaseline = "bottom"; g.fillText(k.kademe, 0, -h / 2 - b * 0.08); }
    if (k.etiket) { g.font = o.font ?? `600 ${Math.round(b * 0.42)}px "Inter Tight"`; g.textBaseline = "top"; const met = o.buyuk ? ust(k.etiket) : k.etiket;
      if (o.kutu) { const tw = g.measureText(met).width + b * 0.4; g.fillStyle = o.kutu; g.fillRect(-tw / 2, h / 2 + b * 0.1, tw, b * 0.62); }
      g.save(); g.shadowColor = "rgba(0,6,14,0.85)"; g.shadowBlur = o.kutu ? 0 : 6 * SS; g.fillStyle = o.metin ?? "#fff"; g.fillText(met, 0, h / 2 + b * 0.16); g.restore(); }
    g.restore();
  }
  // kart bağlantı noktası ve bağlantı çizgisi (ortak geometri)
  function kartYeri(p, q, uzunOran) { const yonx = (q.yon ?? 1) * (dikey ? 0.6 : 1), uzun = fpx(uzunOran ?? (dikey ? 0.1 : 0.085));
    const ex = p.x + yonx * uzun * 0.7, ey = p.y - uzun, kx = ex + yonx * uzun * 0.45; return { yonx, uzun, ex, ey, kx }; }
  function kirikCizgi(g, p, ex, ey, kx, f) { const L1 = Math.hypot(ex - p.x, ey - p.y), L2 = Math.abs(kx - ex), top = (L1 + L2) * f; g.beginPath(); g.moveTo(p.x, p.y);
    if (top <= L1) g.lineTo(p.x + (ex - p.x) * top / L1, p.y + (ey - p.y) * top / L1); else { g.lineTo(ex, ey); g.lineTo(ex + (kx - ex) * (top - L1) / L2, ey); } g.stroke(); }
  // ---- yeni stillerin ortak yardımcıları ----
  const ALTIN = "#d9b26a", KIRMIZI = "#c8302c";
  function koyu(c, f) { const n = parseInt(c.slice(1), 16); return `rgb(${Math.round(((n >> 16) & 255) * f)},${Math.round(((n >> 8) & 255) * f)},${Math.round((n & 255) * f)})`; }
  function yuvarlak(g, x, y, w, h, r_) { r_ = Math.min(r_, w / 2, h / 2); g.beginPath(); g.moveTo(x + r_, y); g.arcTo(x + w, y, x + w, y + h, r_); g.arcTo(x + w, y + h, x, y + h, r_); g.arcTo(x, y + h, x, y, r_); g.arcTo(x, y, x + w, y, r_); g.closePath(); }
  function yuvarlakNokta(x, y, w, h, r_, f) { // yuvarlak dikdörtgen çevresinde f (0..1) konumu
    r_ = Math.min(r_, w / 2, h / 2); const kenar = [w - 2 * r_, h - 2 * r_], L = 2 * (kenar[0] + kenar[1]) + 2 * Math.PI * r_; let s = f * L;
    const parca = [[kenar[0], (u) => [x + r_ + u, y]], [Math.PI * r_ / 2, (u) => { const a_ = -Math.PI / 2 + u / r_; return [x + w - r_ + Math.cos(a_) * r_, y + r_ + Math.sin(a_) * r_]; }],
      [kenar[1], (u) => [x + w, y + r_ + u]], [Math.PI * r_ / 2, (u) => { const a_ = u / r_; return [x + w - r_ + Math.cos(a_) * r_, y + h - r_ + Math.sin(a_) * r_]; }],
      [kenar[0], (u) => [x + w - r_ - u, y + h]], [Math.PI * r_ / 2, (u) => { const a_ = Math.PI / 2 + u / r_; return [x + r_ + Math.cos(a_) * r_, y + h - r_ + Math.sin(a_) * r_]; }],
      [kenar[1], (u) => [x, y + h - r_ - u]], [Math.PI * r_ / 2, (u) => { const a_ = Math.PI + u / r_; return [x + r_ + Math.cos(a_) * r_, y + r_ + Math.sin(a_) * r_]; }]];
    for (const [l, fn] of parca) { if (s <= l) return fn(s); s -= l; } return [x + r_, y];
  }
  // cam yüzey: yukarıdan aşağı sönen beyaz örtü + ince kenar (bulanıklık filtresi yok: hız kuralı)
  function cam(g, x, y, w, h, r_) { yuvarlak(g, x, y, w, h, r_); const gr = g.createLinearGradient(0, y, 0, y + h); gr.addColorStop(0, "rgba(255,255,255,0.22)"); gr.addColorStop(1, "rgba(255,255,255,0.08)");
    g.fillStyle = "rgba(12,18,28,0.55)"; g.fill(); g.fillStyle = gr; g.fill(); g.strokeStyle = "rgba(255,255,255,0.55)"; g.lineWidth = Math.max(1, h * 0.02); g.stroke(); }
  function uzunGolge(g, met, x, y, ar, d, renk_) { const n = Math.max(1, Math.round(d / Math.max(1, SS))); g.save(); g.fillStyle = renk_; for (let i = n; i >= 1; i--) yaz(g, met, x + d * i / n * 0.6, y + d * i / n, ar); g.restore(); }
  // neon tüp: renkli hale katmanları + beyaza yakın çekirdek
  function tup(g, pts, w, c) { g.save(); g.lineCap = g.lineJoin = "round"; cizgi(g, pts); for (const [k, al] of [[5, 0.08], [3, 0.18], [1.7, 0.6]]) { g.strokeStyle = hex(c.startsWith("#") ? c : "#ffffff", al); g.lineWidth = w * k; g.stroke(); }
    g.strokeStyle = "rgba(255,252,255,0.95)"; g.lineWidth = w * 0.6; g.stroke(); g.restore(); }
  function neonYazi(g, met, x, y, ar, boy, c) { g.save(); g.shadowColor = c; g.shadowBlur = boy * 0.5; g.fillStyle = c; yaz(g, met, x, y, ar); g.shadowBlur = boy * 0.15; g.fillStyle = "rgba(255,250,255,0.95)"; yaz(g, met, x, y, ar); g.restore(); }
  // neon yanma: ilk 0.45 sn basamaklı titreşim, sonra sabit
  function tutus(z) { if (z <= 0) return 0; if (z >= 0.45) return 1; const k = Math.floor(z * 30); return [0.2, 0, 0.8, 0.1, 1, 0.3, 1, 1, 0.6, 1, 1, 1, 1, 1][k] ?? 1; }
  // fırça darbesi: basınç profili (ince başla, kalınlaş, sivri bitir) + kuru fırça kılları
  function fircaDarbe(g, yol, gen, c, tohum, kuru = 0.25) {
    const y = yol.length < 3 ? (() => { const o = []; for (let i = 0; i <= 12; i++) o.push(kirpYol(yol, i / 12).slice(-1)[0]); return o; })() : yol; const n = y.length; if (n < 2) return;
    const L = yolUzun(y), sol = [], sag = []; let s = 0;
    for (let i = 0; i < n; i++) { if (i) s += Math.hypot(y[i][0] - y[i - 1][0], y[i][1] - y[i - 1][1]); const f = s / (L || 1), a_ = y[Math.max(0, i - 1)], b_ = y[Math.min(n - 1, i + 1)];
      let dx = b_[0] - a_[0], dy = b_[1] - a_[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l; const w = gen / 2 * (0.35 + 0.65 * Math.sin(Math.min(1, f * 1.3 + 0.08) * Math.PI) ** 0.6);
      sol.push([y[i][0] - dy * w, y[i][1] + dx * w]); sag.push([y[i][0] + dy * w, y[i][1] - dx * w]); }
    g.save(); g.beginPath(); g.moveTo(...sol[0]); sol.forEach((q) => g.lineTo(...q)); for (let i = n - 1; i >= 0; i--) g.lineTo(...sag[i]); g.closePath(); g.fillStyle = c; g.fill();
    if (kuru > 0) { g.clip(); const rr = rng(tohum * 97 + 13); g.globalCompositeOperation = "destination-out"; g.lineCap = "round";
      for (let k = 0; k < 7; k++) { const o = (rr() - 0.5) * 0.9, bas = 0.35 + rr() * 0.5, pts = []; for (let i = Math.floor(n * bas); i < n; i++) pts.push([y[i][0] + (sol[i][0] - y[i][0]) * o * 2, y[i][1] + (sol[i][1] - y[i][1]) * o * 2]);
        if (pts.length > 1) { cizgi(g, pts); g.strokeStyle = `rgba(0,0,0,${kuru * (0.5 + rr() * 0.5)})`; g.lineWidth = gen * (0.03 + rr() * 0.05); g.stroke(); } } }
    g.restore();
  }
  // mürekkep yazı: harfler alfa ile belirmez; fırçanın geçtiği yönde yumuşak bir kenarla soldan sağa "sızar"
  function murekkepYazi(g, met, x, y, f, rgb = "251,247,239", al = 1) {
    if (f <= 0 || !met) return; const w = g.measureText(met).width, x0 = x - (g.textAlign === "center" ? w / 2 : g.textAlign === "right" ? w : 0);
    if (f >= 1) { g.fillStyle = `rgba(${rgb},${al})`; g.fillText(met, x, y); return; }
    const ken = Math.max(w * 0.35, 8 * SS), uc = x0 - ken + (w + ken * 1.02) * f, gr = g.createLinearGradient(uc, 0, uc + ken, 0);
    gr.addColorStop(0, `rgba(${rgb},${al})`); gr.addColorStop(1, `rgba(${rgb},0)`); g.fillStyle = gr; g.fillText(met, x, y);
  }
  // hanko mühür basışı: büyükten iner (0.22 sn, expo), hafif döner, oturunca bir kez açılan ince mürekkep çerçevesi; dokulu yüzey
  function damga(g, cx, cy, m, z, harf_ = null, aci = -0.06) {
    if (z <= 0) return; const p = expo(ara(z, 0, 0.22)), s = 1 + 0.9 * (1 - p);
    g.save(); g.translate(cx, cy); g.rotate(aci + 0.22 * (1 - p)); g.scale(s, s); g.globalAlpha *= ara(z, 0, 0.07);
    g.fillStyle = KIRMIZI; g.fillRect(-m / 2, -m / 2, m, m); const rr = rng(Math.round(m) * 7 + 5); g.fillStyle = "rgba(251,247,239,0.2)";
    for (let i = 0; i < 16; i++) { g.beginPath(); g.arc((rr() - 0.5) * m * 0.92, (rr() - 0.5) * m * 0.92, m * (0.008 + rr() * 0.03), 0, 7); g.fill(); }
    g.strokeStyle = "rgba(251,247,239,0.6)"; g.lineWidth = m * 0.05; g.strokeRect(-m * 0.36, -m * 0.36, m * 0.72, m * 0.72);
    if (harf_) { g.fillStyle = "#fbf7ef"; g.font = `700 ${Math.round(m * 0.46)}px "Cinzel"`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(harf_, 0, m * 0.04); }
    const h = ara(z, 0.2, 0.75); if (h > 0 && h < 1) { const k = m * (1 + eo(h) * 0.7); g.strokeStyle = hex(KIRMIZI, 0.55 * (1 - h)); g.lineWidth = m * 0.035; g.strokeRect(-k / 2, -k / 2, k, k); }
    g.restore();
  }
  // mürekkep sıçraması: fırça ucunun durduğu yerden ileri savrulan damlalar; uçarken uzun, otururken yuvarlak
  function sicrama(g, x, y, dx, dy, gen, f, c, tohum) {
    if (f <= 0) return; const rr = rng(tohum), yon = Math.atan2(dy, dx), e_ = expo(f); g.save(); g.fillStyle = c;
    for (let i = 0; i < 10; i++) { const an = yon + (rr() - 0.5) * 2.4, d = gen * (0.8 + rr() * 2.6) * e_, rad = gen * (0.05 + rr() * 0.15);
      g.save(); g.translate(x + Math.cos(an) * d, y + Math.sin(an) * d); g.rotate(an); g.scale(1 + 1.8 * (1 - e_), 1 - 0.3 * (1 - e_)); g.beginPath(); g.arc(0, 0, rad, 0, 7); g.fill(); g.restore(); }
    g.restore();
  }
  function deger(q, f) { return q.deger != null ? (q.onek || "") + sayi(q.deger * f, q.ondalik) + (q.birim ? " " + q.birim : "") : ""; }

  // =====================================================================================
  const STILLER = {
    // -------------------------------------------------------------------------------- HABER
    // Yayın/haber grafiği: düz renk, kalın koyu kontur, sert gölge, renkli etiket kutuları. Hızlı ve kararlı:
    // expo-out girişler 0.35–0.6 sn, kartta küçük taşma (back-out). Güçlü kontrast, telefonda bile okunur.
    haber: {
      hiz: 0.65, okEase: expo, cepheOlcek: 1.5, etiketSure: 0.55,
      ulkeDolgu(g, yol, f, r) { g.beginPath(); yol(f); g.fillStyle = hex(r.dolgu, r.alfa ?? 0.42); g.fill(); },
      ulkeKontur(g, yol, f, r, px) { g.lineJoin = "round"; g.beginPath(); yol(f); g.strokeStyle = "rgba(4,6,10,0.6)"; g.lineWidth = px(5.5); g.stroke(); g.strokeStyle = r.kontur; g.lineWidth = px(2.6); g.stroke(); },
      ok(g, yol, p, gen, r) {
        const y = kirpYol(yol, p); const sek = okSekli(y, gen * 1.1, { bas: 0.72, ucBoy: 2.0, ucGen: 1.2 }); if (!sek) return;
        g.save(); g.lineJoin = "miter"; g.miterLimit = 3;
        g.save(); g.translate(gen * 0.16, gen * 0.26); sek(g); g.fillStyle = "rgba(0,0,0,0.42)"; g.fill(); g.restore();
        sek(g); g.strokeStyle = "#06080c"; g.lineWidth = gen * 0.3; g.stroke(); g.fillStyle = r.dolgu; g.fill();
        g.save(); sek(g); g.clip(); cizgi(g, sek.govde); g.strokeStyle = "rgba(255,255,255,0.3)"; g.lineWidth = gen * 0.2; g.stroke(); g.restore();
        g.restore();
      },
      cephe(g, yol, gen, r, taraf) {
        g.save(); g.lineJoin = g.lineCap = "round"; cizgi(g, yol); g.strokeStyle = "#06080c"; g.lineWidth = gen * 2.1; g.stroke(); g.strokeStyle = r.kontur; g.lineWidth = gen * 1.3; g.stroke();
        boyunca(yol, gen * 5.5, (x, y, dx, dy) => { const nx = -dy * taraf, ny = dx * taraf; g.beginPath(); g.moveTo(x - dx * gen * 1.7, y - dy * gen * 1.7); g.lineTo(x + nx * gen * 2.8, y + ny * gen * 2.8); g.lineTo(x + dx * gen * 1.7, y + dy * gen * 1.7); g.closePath();
          g.lineWidth = gen * 0.55; g.strokeStyle = "#06080c"; g.stroke(); g.fillStyle = r.kontur; g.fill(); });
        g.restore();
      },
      ulkeEtiket(e, o) {
        const met = ust(o.met), boy = o.boy * 0.9, ar = boy * 0.05; e.font = `700 ${boy}px "Barlow Condensed"`; const tw = genislik(e, met, ar), pad = boy * 0.32, w = tw + pad * 2, h = boy * 1.22;
        const x = o.x - w / 2, y = o.y - h / 2; if (!o.yer_(x, y, w, h)) return; const g1 = expo(o.gir), zem = o.r ? o.r.dolgu : "#0b0f16";
        e.save(); e.globalAlpha = o.a; e.fillStyle = "rgba(0,0,0,0.4)"; e.fillRect(x + boy * 0.08, y + boy * 0.1, w * g1, h); e.fillStyle = zem; e.fillRect(x, y, w * g1, h);
        e.beginPath(); e.rect(x, y, w * g1, h); e.clip(); e.fillStyle = o.r && aciklik(zem) > 0.6 ? "#0b0f16" : "#fff"; e.textBaseline = "middle"; e.textAlign = "left";
        yaz(e, met, x + pad - (1 - g1) * boy * 1.2, o.y + boy * 0.04, ar); e.restore();
      },
      sehir(e, o) {
        const boy = o.boy * 0.95; e.font = `700 ${boy}px "Inter Tight"`; const met = ust(o.met), ar = boy * 0.04, tw = genislik(e, met, ar), pad = boy * 0.32, w = tw + pad * 2, h = boy * 1.45;
        const sag = o.yon > 0, x = sag ? o.x + boy * 0.7 : o.x - boy * 0.7 - w; if (!o.yer_(Math.min(o.x, x) - 4, o.y - h / 2, w + boy, h)) return; const g1 = expo(o.gir);
        e.save(); e.globalAlpha = o.a; const d = boy * (o.onem === 1 ? 0.6 : 0.42); e.fillStyle = "#fff"; e.strokeStyle = "#06080c"; e.lineWidth = boy * 0.14; e.beginPath(); e.rect(o.x - d / 2, o.y - d / 2, d, d); e.stroke(); e.fill();
        const wx = sag ? x : x + w * (1 - g1); e.fillStyle = "rgba(8,10,16,0.9)"; e.fillRect(wx, o.y - h / 2, w * g1, h); e.fillStyle = o.rk ?? M.roller.ana.dolgu; e.fillRect(sag ? wx : wx + w * g1 - boy * 0.14, o.y - h / 2, boy * 0.14 * g1, h);
        e.beginPath(); e.rect(wx, o.y - h / 2, w * g1, h); e.clip(); e.fillStyle = "#fff"; e.textBaseline = "middle"; yaz(e, met, x + pad, o.y + boy * 0.04, ar); e.restore();
      },
      kart(e, q, p, t, a) {
        const t0 = q.t?.[0] ?? 0, b = fpx(0.02), r = renk(q.rol || "ana"), uzun = fpx(dikey ? 0.1 : 0.09);
        const c1 = expo(ara(t, t0, t0 + 0.4)), c2 = ara(t, t0 + 0.22, t0 + 0.72), c3 = eoq(ara(t, t0 + 0.35, t0 + 1.5));
        e.save(); e.globalAlpha = a; e.strokeStyle = "#fff"; e.lineWidth = Math.max(2, b * 0.14); e.beginPath(); e.moveTo(p.x, p.y); e.lineTo(p.x, p.y - uzun * c1); e.stroke();
        e.beginPath(); e.arc(p.x, p.y, b * 0.4 * c1, 0, 7); e.fillStyle = r.dolgu; e.fill(); e.lineWidth = b * 0.14; e.strokeStyle = "#06080c"; e.stroke();
        if (c2 > 0) {
          const bas = ust(q.baslik || ""), vb = Math.round(b * 2.7); e.font = `700 ${vb}px "Barlow Condensed"`; const sw = e.measureText(deger(q, 1)).width;
          e.font = `700 ${b}px "Inter Tight"`; const bw = genislik(e, bas, b * 0.12); e.font = `500 ${Math.round(b * 0.95)}px "Inter Tight"`; const aw = e.measureText(q.alt || "").width;
          const pad = b * 0.95, w = Math.max(sw, bw, aw) + pad * 2, h = b * (q.alt ? 6.1 : 4.9), x = kiskac(p.x - w / 2 + (q.yon ?? 1) * w * 0.25, w), y0 = p.y - uzun - h;
          const s = backOut(c2, 1.4), y = y0 + (1 - s) * b * 2.2; e.globalAlpha = a * sinir(c2 * 3);
          e.fillStyle = "rgba(0,0,0,0.4)"; e.fillRect(x + b * 0.18, y + b * 0.24, w, h); e.fillStyle = "#f6f5f1"; e.fillRect(x, y, w, h); e.fillStyle = r.dolgu; e.fillRect(x, y, w, b * 0.42);
          e.textBaseline = "alphabetic"; e.textAlign = "left"; e.font = `700 ${b}px "Inter Tight"`; e.fillStyle = "#3a404a"; yaz(e, bas, x + pad, y + b * 0.42 + pad + b * 0.6, b * 0.12);
          e.font = `700 ${vb}px "Barlow Condensed"`; e.fillStyle = "#0b0f16"; e.fillText(deger(q, c3), x + pad, y + b * 0.42 + pad + b * 3.25);
          if (q.alt) { e.font = `500 ${Math.round(b * 0.95)}px "Inter Tight"`; e.fillStyle = "#4a515c"; e.fillText(q.alt, x + pad, y + b * 0.42 + pad + b * 4.55); }
        }
        e.restore();
      },
      birlik(g, x, y, k, a) { birlikP(g, x, y, k, a, { kenar: "#06080c", kal: 0.12, golge: "rgba(0,0,0,0.45)", ic: "#06080c", metin: "#fff", kutu: "rgba(8,10,16,0.9)", buyuk: true, font: `700 ${Math.round(fpx(0.034) * 0.4)}px "Inter Tight"` }); },
      baslik(e, o) {
        const { Y, t, a, b, x, ust: yUst, vurgu } = o; const out = 1 - ara(t, b - 0.4, b); if (out <= 0) return;
        const kb = fpx(0.022), maxW = W * SS - 2 * gx, bb0 = fpx(dikey ? 0.074 : 0.07), ab = fpx(0.027);
        const g1 = expo(ara(t, a, a + 0.5)), g2 = expo(ara(t, a + 0.12, a + 0.7)), g3 = expo(ara(t, a + 0.3, a + 0.9));
        e.save(); e.globalAlpha = out; e.textBaseline = "middle"; e.textAlign = "left"; let y = yUst;
        if (Y.ust) { const m = ust(Y.ust); e.font = `700 ${kb}px "Space Grotesk"`; const w = genislik(e, m, kb * 0.14) + kb * 1.2, h = kb * 1.9;
          e.fillStyle = vurgu; e.fillRect(x, y, w * g1, h); e.save(); e.beginPath(); e.rect(x, y, w * g1, h); e.clip(); e.fillStyle = "#0b0f16"; yaz(e, m, x + kb * 0.6, y + h / 2 + kb * 0.05, kb * 0.14); e.restore(); y += h; }
        const m2 = ust(Y.baslik); const bb = sigdir(e, (s) => `700 ${s}px "Barlow Condensed"`, bb0, m2, 0.02, maxW - bb0 * 0.8); e.font = `700 ${bb}px "Barlow Condensed"`;
        const w2 = genislik(e, m2, bb * 0.02) + bb * 0.7, h2 = bb * 1.22; e.fillStyle = "rgba(8,10,16,0.92)"; e.fillRect(x, y, w2 * g2, h2);
        e.save(); e.beginPath(); e.rect(x, y, w2 * g2, h2); e.clip(); e.fillStyle = "#fff"; yaz(e, m2, x + bb * 0.35, y + h2 / 2 + bb * 0.06 + (1 - g2) * h2, bb * 0.02); e.restore(); y += h2;
        if (Y.alt) { e.font = `600 ${ab}px "Inter Tight"`; const w3 = e.measureText(Y.alt).width + ab * 1.3, h3 = ab * 1.8; e.globalAlpha = out * g3; e.fillStyle = "rgba(246,245,241,0.95)"; e.fillRect(x, y, w3 * g3, h3);
          e.fillStyle = "#0b0f16"; e.save(); e.beginPath(); e.rect(x, y, w3 * g3, h3); e.clip(); e.fillText(Y.alt, x + ab * 0.65, y + h3 / 2); e.restore(); }
        e.restore(); return y + ab * 1.8 - yUst;
      },
      kutu(e, x, y, w, h, vurgu, f) { e.fillStyle = "rgba(8,10,16,0.92)"; e.fillRect(x, y, w * f, h); e.fillStyle = vurgu; e.fillRect(x, y, Math.max(4, h * 0.08), h); },
    },

    // -------------------------------------------------------------------------------- GRAVÜR
    // Eski atlas ve askerî tarih haritası: mürekkep konturu, ince tarama dolgu, sınırda renkli şerit (atlas kurdelesi),
    // içi taralı oyuk oklar ve çatallı kuyruk, yarım daireli cephe, Cinzel + EB Garamond, kâğıt kartuş. Yavaş ve ağırbaşlı:
    // sinüs ease-in-out 1.2–2 sn, harf harf mürekkep açılışı.
    gravur: {
      hiz: 1.25, okEase: sio, cepheOlcek: 1.7, etiketSure: 1.4,
      ulkeDolgu(g, yol, f, r, px) { g.beginPath(); yol(f); g.fillStyle = hex(r.dolgu, 0.16); g.fill(); g.fillStyle = desen(g, hex(r.kontur, 0.42), 45, Math.max(5, px(7)), Math.max(1, px(1.1))); g.fill();
        g.save(); g.clip(); g.strokeStyle = hex(r.dolgu, 0.62); g.lineWidth = px(15); g.stroke(); g.restore(); },
      ulkeKontur(g, yol, f, r, px) { g.lineJoin = "round"; g.beginPath(); yol(f); g.strokeStyle = "rgba(22,15,8,0.8)"; g.lineWidth = px(2.6); g.stroke(); g.strokeStyle = "rgba(241,230,204,0.9)"; g.lineWidth = px(0.9); g.stroke(); },
      ok(g, yol, p, gen, r) {
        const y = kirpYol(yol, p); const sek = okSekli(y, gen * 1.05, { bas: 0.62, ucBoy: 2.7, ucGen: 1.3, kuyruk: true }); if (!sek) return;
        g.save(); g.lineJoin = "miter"; g.miterLimit = 4; g.save(); g.translate(gen * 0.12, gen * 0.2); sek(g); g.fillStyle = "rgba(10,6,2,0.3)"; g.fill(); g.restore();
        sek(g); g.fillStyle = "rgba(241,230,204,0.4)"; g.fill(); g.fillStyle = desen(g, hex(r.kontur, 0.95), 45, Math.max(4, gen * 0.3), Math.max(1, gen * 0.08)); g.fill();
        sek(g); g.strokeStyle = "rgba(22,15,8,0.9)"; g.lineWidth = gen * 0.2; g.stroke(); g.strokeStyle = hex(r.kontur, 1); g.lineWidth = gen * 0.07; g.stroke(); g.restore();
      },
      cephe(g, yol, gen, r, taraf) {
        g.save(); g.lineJoin = g.lineCap = "round"; cizgi(g, yol); g.strokeStyle = "rgba(22,15,8,0.85)"; g.lineWidth = gen * 1.3; g.stroke(); g.strokeStyle = r.dolgu; g.lineWidth = gen * 0.65; g.stroke();
        boyunca(yol, gen * 6.5, (x, y, dx, dy) => { const th = Math.atan2(dy, dx); g.beginPath(); g.arc(x, y, gen * 1.55, th, th + Math.PI, taraf < 0); g.closePath();
          g.fillStyle = r.dolgu; g.fill(); g.lineWidth = gen * 0.38; g.strokeStyle = "rgba(22,15,8,0.85)"; g.stroke(); });
        g.restore();
      },
      ulkeEtiket(e, o) {
        const met = ust(o.met), boy = o.boy * 0.78, ar = boy * 0.32; e.font = `600 ${boy}px "Cinzel"`; const w = genislik(e, met, ar), h = boy;
        if (!o.yer_(o.x - w / 2, o.y - h / 2, w, h)) return; const n = met.length;
        e.save(); e.globalAlpha = o.a; e.textBaseline = "middle"; e.textAlign = "left"; e.lineJoin = "round"; e.strokeStyle = "rgba(22,15,8,0.82)"; e.lineWidth = boy * 0.2; e.fillStyle = o.r ? "#f6ead0" : "#e9dcc0";
        harfHarf(e, met, o.x - w / 2 + ar / 2, o.y, ar, (i) => sinir(o.gir * (n + 4) - i, 0, 4) / 4, true); e.restore();
      },
      sehir(e, o) {
        const boy = o.boy * 1.08; e.font = `italic 500 ${boy}px "EB Garamond"`; const w = e.measureText(o.met).width, sag = o.yon > 0, x = sag ? o.x + boy * 0.75 : o.x - boy * 0.75 - w;
        if (!o.yer_(Math.min(o.x, x) - 4, o.y - boy * 0.6, w + boy, boy * 1.2)) return;
        e.save(); e.globalAlpha = o.a; e.lineWidth = boy * 0.1; e.strokeStyle = "rgba(22,15,8,0.9)"; e.fillStyle = "#f1e6cc"; const R = boy * (o.onem === 1 ? 0.3 : 0.2);
        e.beginPath(); e.arc(o.x, o.y, R, 0, 7); e.fill(); e.stroke(); if (o.onem === 1) { e.beginPath(); e.arc(o.x, o.y, R * 0.4, 0, 7); e.fillStyle = "rgba(22,15,8,0.95)"; e.fill(); }
        e.textBaseline = "middle"; e.lineJoin = "round"; e.lineWidth = boy * 0.2; e.strokeStyle = "rgba(22,15,8,0.82)"; e.fillStyle = "#f6ead0"; e.globalAlpha = o.a * sio(o.gir);
        e.strokeText(o.met, x, o.y); e.fillText(o.met, x, o.y); e.restore();
      },
      kart(e, q, p, t, a) {
        const t0 = q.t?.[0] ?? 0, b = fpx(0.019), r = renk(q.rol || "ana"), { yonx, ex, ey, kx } = kartYeri(p, q);
        const c1 = sio(ara(t, t0, t0 + 0.9)), c2 = sio(ara(t, t0 + 0.6, t0 + 1.6)), c3 = eo(ara(t, t0 + 0.9, t0 + 2.6));
        e.save(); e.globalAlpha = a; e.lineWidth = Math.max(2, b * 0.1); e.strokeStyle = "rgba(22,15,8,0.7)"; e.lineWidth = b * 0.22; kirikCizgi(e, p, ex, ey, kx, c1); e.strokeStyle = "#efe4cb"; e.lineWidth = b * 0.08; kirikCizgi(e, p, ex, ey, kx, c1);
        e.beginPath(); e.arc(p.x, p.y, b * 0.3 * c1, 0, 7); e.fillStyle = "#efe4cb"; e.fill(); e.lineWidth = b * 0.1; e.strokeStyle = "rgba(22,15,8,0.9)"; e.stroke();
        if (c2 > 0) {
          const bas = ust(q.baslik || ""), vb = Math.round(b * 2.5); e.font = `600 ${Math.round(b * 0.9)}px "Cinzel"`; const bw = genislik(e, bas, b * 0.2); e.font = `600 ${vb}px "EB Garamond"`; const sw = e.measureText(deger(q, 1)).width;
          e.font = `italic 400 ${b}px "EB Garamond"`; const aw = e.measureText(q.alt || "").width; const pad = b * 1.2, w = Math.max(sw, bw, aw) + pad * 2, h = b * (q.alt ? 6.6 : 5.2);
          const x = kiskac(yonx > 0 ? kx : kx - w, w), y = ey - h / 2, yh = h * c2;
          e.save(); e.beginPath(); e.rect(x - b, y + h / 2 - yh / 2 - b * 0.4, w + 2 * b, yh + b * 0.8); e.clip();
          e.fillStyle = "rgba(10,6,2,0.35)"; e.fillRect(x + b * 0.2, y + b * 0.28, w, h); e.fillStyle = "#efe4cb"; e.fillRect(x, y, w, h);
          e.strokeStyle = "#2a1f12"; e.lineWidth = b * 0.12; e.strokeRect(x + b * 0.25, y + b * 0.25, w - b * 0.5, h - b * 0.5); e.lineWidth = b * 0.05; e.strokeRect(x + b * 0.45, y + b * 0.45, w - b * 0.9, h - b * 0.9);
          for (const [cx, cy] of [[x + b * 0.25, y + b * 0.25], [x + w - b * 0.25, y + b * 0.25], [x + b * 0.25, y + h - b * 0.25], [x + w - b * 0.25, y + h - b * 0.25]]) { e.beginPath(); e.moveTo(cx, cy - b * 0.32); e.lineTo(cx + b * 0.32, cy); e.lineTo(cx, cy + b * 0.32); e.lineTo(cx - b * 0.32, cy); e.closePath(); e.fillStyle = "#2a1f12"; e.fill(); }
          e.textAlign = "center"; e.textBaseline = "alphabetic"; e.fillStyle = "#2a1f12"; e.font = `600 ${Math.round(b * 0.9)}px "Cinzel"`; yaz(e, bas, x + w / 2 + b * 0.1, y + pad + b * 0.55, b * 0.2);
          e.fillStyle = r.dolgu; e.fillRect(x + w / 2 - b * 1.4, y + pad + b * 0.95, b * 2.8, Math.max(2, b * 0.1));
          e.fillStyle = "#1c140a"; e.font = `600 ${vb}px "EB Garamond"`; e.fillText(deger(q, c3), x + w / 2, y + pad + b * 3.35);
          if (q.alt) { e.font = `italic 400 ${b}px "EB Garamond"`; e.fillStyle = "#5a4a35"; e.fillText(q.alt, x + w / 2, y + pad + b * 4.65); }
          e.restore();
        }
        e.restore();
      },
      birlik(g, x, y, k, a) { birlikP(g, x, y, k, a, { zemin: "#efe4cb", kenar: "#22180c", ic: "#22180c", kal: 0.09, bant: true, golge: "rgba(10,6,2,0.35)", metin: "#f6ead0", font: `italic 500 ${Math.round(fpx(0.034) * 0.5)}px "EB Garamond"`, font2: "Cinzel" }); },
      baslik(e, o) {
        const { Y, t, a, b, x, ust: yUst, vurgu } = o; const out = 1 - ara(t, b - 0.6, b); if (out <= 0) return;
        const kb = fpx(0.028), maxW = W * SS - 2 * gx, bb0 = fpx(dikey ? 0.064 : 0.062), ab = fpx(0.03); const m2 = ust(Y.baslik);
        const bb = sigdir(e, (s) => `700 ${s}px "Cinzel"`, bb0, m2, 0.06, maxW);
        e.save(); e.globalAlpha = out; e.textBaseline = "alphabetic"; e.textAlign = "left"; let y = yUst + kb;
        if (Y.ust) { e.font = `italic 500 ${kb}px "EB Garamond"`; e.fillStyle = vurgu; e.globalAlpha = out * sio(ara(t, a, a + 1)); e.fillText(Y.ust, x, y); e.globalAlpha = out; }
        y += bb * 1.25; e.font = `700 ${bb}px "Cinzel"`; e.lineJoin = "round"; e.lineWidth = bb * 0.12; e.strokeStyle = "rgba(22,15,8,0.7)"; e.fillStyle = "#f6ead0";
        const f = ara(t, a + 0.2, a + 1.8); harfHarf(e, m2, x, y, bb * 0.06, (i) => sinir(f * (m2.length + 6) - i, 0, 6) / 6, true);
        const tw = genislik(e, m2, bb * 0.06), r1 = sio(ara(t, a + 0.5, a + 1.7)); e.fillStyle = "#e9dcc0"; e.fillRect(x, y + bb * 0.28, tw * r1, Math.max(2, bb * 0.035)); e.fillRect(x, y + bb * 0.38, tw * r1, Math.max(1, bb * 0.015));
        if (Y.alt) { y += bb * 0.4 + ab * 1.5; e.font = `italic 400 ${ab}px "EB Garamond"`; e.globalAlpha = out * sio(ara(t, a + 1.0, a + 2.0)); e.fillStyle = "#e9dcc0"; e.save(); e.shadowColor = "rgba(10,6,2,0.9)"; e.shadowBlur = 8 * SS; e.fillText(Y.alt, x, y); e.restore(); }
        e.restore(); return y + ab - yUst;
      },
      kutu(e, x, y, w, h, vurgu, f) { e.fillStyle = "rgba(239,228,203,0.95)"; e.fillRect(x, y, w * f, h); e.strokeStyle = "#2a1f12"; e.lineWidth = Math.max(1.5, h * 0.025); e.strokeRect(x + h * 0.06, y + h * 0.06, w * f - h * 0.12, h - h * 0.12); },
    },

    // -------------------------------------------------------------------------------- İSTİHBARAT
    // OSINT / komuta ekranı: ince ışıyan çizgiler, nokta ızgaralı dolgu, iz mermisi (tracer) gibi akan kesikli oklar,
    // nişangâh şehirler, köşe parantezli kartlar, daktilo ile yazılan mono etiketler ve karışıp oturan rakamlar.
    // Doğrusal/basamaklı zaman: 0.3–0.6 sn, harf harf yazım; makine hissi.
    istihbarat: {
      hiz: 0.8, okEase: (x) => x, cepheOlcek: 1.4, etiketSure: 0.9,
      ulkeDolgu(g, yol, f, r, px) { g.beginPath(); yol(f); g.fillStyle = hex(r.dolgu, 0.1); g.fill(); g.fillStyle = noktaDesen(g, hex(r.kontur, 0.55), Math.max(4, px(8)), Math.max(0.8, px(1.1))); g.fill(); },
      ulkeKontur(g, yol, f, r, px) { g.lineJoin = "round"; g.beginPath(); yol(f); g.strokeStyle = hex(r.kontur, 0.14); g.lineWidth = px(9); g.stroke(); g.strokeStyle = hex(r.kontur, 0.32); g.lineWidth = px(4); g.stroke(); g.strokeStyle = hex(r.kontur, 1); g.lineWidth = px(1.3); g.stroke(); },
      ok(g, yol, p, gen, r, z) {
        const y = kirpYol(yol, p); if (y.length < 2) return; const L = yolUzun(y), c = r.kontur;
        g.save(); g.lineCap = "butt"; g.lineJoin = "round"; cizgi(g, y); g.strokeStyle = hex(c, 0.12); g.lineWidth = gen * 0.7; g.stroke(); g.strokeStyle = hex(c, 0.25); g.lineWidth = gen * 0.3; g.stroke();
        g.setLineDash([gen * 0.75, gen * 0.45]); g.lineDashOffset = -z * gen * 3.2; g.strokeStyle = hex(c, 0.95); g.lineWidth = gen * 0.13; g.stroke(); g.setLineDash([]);
        const son = kirpYol(y, 1).slice(-Math.max(2, Math.round(y.length * 0.12))); cizgi(g, son); g.strokeStyle = "rgba(235,250,255,0.95)"; g.lineWidth = gen * 0.16; g.stroke();
        const u = y[y.length - 1], o_ = y[Math.max(0, y.length - 4)]; let dx = u[0] - o_[0], dy = u[1] - o_[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
        for (const [geri, al] of [[0, 1], [gen * 0.9, 0.45]]) { const ux = u[0] - dx * geri, uy = u[1] - dy * geri, k = gen * 1.1; g.beginPath(); g.moveTo(ux - dx * k - dy * k * 0.8, uy - dy * k + dx * k * 0.8); g.lineTo(ux, uy); g.lineTo(ux - dx * k + dy * k * 0.8, uy - dy * k - dx * k * 0.8);
          g.strokeStyle = hex(c, al); g.shadowColor = c; g.shadowBlur = gen * 0.6; g.lineWidth = gen * 0.16; g.stroke(); }
        g.shadowBlur = 0; const s0 = y[0], q = gen * 0.38; g.strokeStyle = hex(c, 0.95); g.lineWidth = gen * 0.1; g.strokeRect(s0[0] - q, s0[1] - q, q * 2, q * 2);
        g.restore(); void L;
      },
      cephe(g, yol, gen, r, taraf, z) {
        const c = r.kontur; g.save(); g.lineJoin = g.lineCap = "round"; cizgi(g, yol); g.strokeStyle = hex(c, 0.16); g.lineWidth = gen * 3; g.stroke(); g.strokeStyle = hex(c, 1); g.lineWidth = gen * 0.55; g.stroke();
        const ofs = yol.map((q, i) => { const a = yol[Math.max(0, i - 1)], b = yol[Math.min(yol.length - 1, i + 1)]; let dx = b[0] - a[0], dy = b[1] - a[1]; const l = Math.hypot(dx, dy) || 1; return [q[0] - dy / l * gen * 2.2 * taraf, q[1] + dx / l * gen * 2.2 * taraf]; });
        cizgi(g, ofs); g.setLineDash([gen * 1.2, gen * 0.9]); g.lineDashOffset = -z * gen * 2; g.strokeStyle = hex(c, 0.6); g.lineWidth = gen * 0.3; g.stroke(); g.setLineDash([]);
        boyunca(yol, gen * 3.2, (x, y, dx, dy) => { g.beginPath(); g.moveTo(x, y); g.lineTo(x - dy * taraf * gen * 1.6, y + dx * taraf * gen * 1.6); g.strokeStyle = hex(c, 0.9); g.lineWidth = gen * 0.3; g.stroke(); });
        g.restore();
      },
      ulkeEtiket(e, o) {
        const met = ust(o.met), boy = o.boy * 0.62, ar = boy * 0.12; e.font = `600 ${boy}px "IBM Plex Mono"`; const tw = genislik(e, met, ar), pad = boy * 0.6, w = tw + pad * 2, h = boy * 1.7;
        const x = o.x - w / 2, y = o.y - h / 2; if (!o.yer_(x, y, w, h)) return; const n = Math.floor(o.gir * (met.length + 1)), c = o.r ? o.r.kontur : "#9fdcff";
        e.save(); e.globalAlpha = o.a; e.fillStyle = "rgba(2,10,16,0.5)"; e.fillRect(x, y, w, h); e.strokeStyle = c; e.lineWidth = Math.max(1.5, boy * 0.09); const k = boy * 0.45;
        for (const [cx, cy, sx, sy] of [[x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1]]) { e.beginPath(); e.moveTo(cx, cy + sy * k); e.lineTo(cx, cy); e.lineTo(cx + sx * k, cy); e.stroke(); }
        e.textBaseline = "middle"; e.textAlign = "left"; e.fillStyle = "#e6f7ff"; yaz(e, met.slice(0, n), x + pad, o.y + boy * 0.04, ar);
        if (o.gir < 1) { e.font = `600 ${boy}px "IBM Plex Mono"`; const cx = x + pad + genislik(e, met.slice(0, n), ar); e.fillStyle = c; e.fillRect(cx, o.y - boy * 0.5, boy * 0.55, boy); }
        e.restore();
      },
      sehir(e, o) {
        const boy = o.boy * 0.82, met = ust(o.met); e.font = `600 ${boy}px "IBM Plex Mono"`; const w = genislik(e, met, boy * 0.06), sag = o.yon > 0, x = sag ? o.x + boy * 1.05 : o.x - boy * 1.05 - w;
        if (!o.yer_(Math.min(o.x, x) - 4, o.y - boy * 0.7, w + boy * 1.4, boy * 2.2)) return; const c = o.rk ?? "#9fdcff", R = boy * (o.onem === 1 ? 0.5 : 0.38), f = expo(o.gir);
        e.save(); e.globalAlpha = o.a; e.strokeStyle = c; e.lineWidth = Math.max(1.5, boy * 0.08); e.shadowColor = c; e.shadowBlur = 6 * SS;
        e.beginPath(); e.arc(o.x, o.y, R * (2 - f), 0, 7); e.stroke(); for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { e.beginPath(); e.moveTo(o.x + dx * R * 0.55, o.y + dy * R * 0.55); e.lineTo(o.x + dx * R * 1.5, o.y + dy * R * 1.5); e.stroke(); }
        e.shadowBlur = 0; e.fillStyle = "#e6f7ff"; e.beginPath(); e.arc(o.x, o.y, boy * 0.09, 0, 7); e.fill();
        e.textBaseline = "middle"; const n = Math.floor(o.gir * (met.length + 1)); e.fillStyle = "#e6f7ff"; yaz(e, met.slice(0, n), x, o.y - boy * 0.18, boy * 0.06);
        if (o.konum) { e.font = `400 ${Math.round(boy * 0.62)}px "IBM Plex Mono"`; e.fillStyle = hex(c.startsWith("#") ? c : "#9fdcff", 0.85); e.globalAlpha = o.a * ara(o.gir, 0.6, 1);
          const [lo, la] = o.konum; e.fillText(`${Math.abs(la).toFixed(2)}${la >= 0 ? "N" : "S"} ${Math.abs(lo).toFixed(2)}${lo >= 0 ? "E" : "W"}`, x, o.y + boy * 0.72); }
        e.restore();
      },
      kart(e, q, p, t, a) {
        const t0 = q.t?.[0] ?? 0, b = fpx(0.018), r = renk(q.rol || "ana"), c = r.kontur, { yonx, ex, ey, kx } = kartYeri(p, q);
        const c1 = ara(t, t0, t0 + 0.45), c2 = expo(ara(t, t0 + 0.35, t0 + 0.8)), c3 = ara(t, t0 + 0.6, t0 + 1.6);
        e.save(); e.globalAlpha = a; e.strokeStyle = c; e.lineWidth = Math.max(1.5, b * 0.08); e.shadowColor = c; e.shadowBlur = 6 * SS; kirikCizgi(e, p, ex, ey, kx, c1); e.shadowBlur = 0;
        const q_ = b * 0.35; e.strokeRect(p.x - q_, p.y - q_, q_ * 2, q_ * 2);
        if (c2 > 0) {
          const bas = "// " + ust(q.baslik || ""), vb = Math.round(b * 2.3); e.font = `600 ${b}px "IBM Plex Mono"`; const bw = genislik(e, bas, b * 0.05); e.font = `600 ${vb}px "IBM Plex Mono"`; const sw = e.measureText(deger(q, 1)).width;
          e.font = `400 ${Math.round(b * 0.85)}px "IBM Plex Mono"`; const aw = e.measureText(q.alt || "").width; const pad = b * 1.0, w = Math.max(sw, bw, aw) + pad * 2, h = b * (q.alt ? 5.6 : 4.4);
          const xm = kiskac(yonx > 0 ? kx : kx - w, w) + w / 2, ym = ey, ww = w * c2, hh = h * (0.25 + 0.75 * c2), x = xm - ww / 2, y = ym - hh / 2, k = b * 0.8;
          e.fillStyle = "rgba(2,10,16,0.62)"; e.fillRect(x, y, ww, hh); e.strokeStyle = c; e.lineWidth = Math.max(1.5, b * 0.1);
          for (const [cx, cy, sx, sy] of [[x, y, 1, 1], [x + ww, y, -1, 1], [x, y + hh, 1, -1], [x + ww, y + hh, -1, -1]]) { e.beginPath(); e.moveTo(cx, cy + sy * k); e.lineTo(cx, cy); e.lineTo(cx + sx * k, cy); e.stroke(); }
          if (c2 > 0.98) { const x0 = xm - w / 2, y0 = ym - h / 2; e.textAlign = "left"; e.textBaseline = "alphabetic"; e.fillStyle = c; e.font = `600 ${b}px "IBM Plex Mono"`; yaz(e, bas.slice(0, Math.ceil(bas.length * sinir(c3 * 3))), x0 + pad, y0 + pad + b * 0.7, b * 0.05);
            let v = deger(q, eo(c3)); if (c3 < 1) { const rr = rng(Math.floor(t * 30) + 17); v = v.replace(/\d/g, (d) => (rr() < (1 - c3) * 0.9 ? String(Math.floor(rr() * 10)) : d)); }
            e.font = `600 ${vb}px "IBM Plex Mono"`; e.fillStyle = "#eaf9ff"; e.fillText(v, x0 + pad, y0 + pad + b * 3.0);
            if (q.alt) { e.font = `400 ${Math.round(b * 0.85)}px "IBM Plex Mono"`; e.fillStyle = "rgba(200,232,248,0.75)"; e.fillText(q.alt, x0 + pad, y0 + pad + b * 4.2); } }
        }
        e.restore();
      },
      birlik(g, x, y, k, a) { const r = renk(k.rol || "dost"); birlikP(g, x, y, k, a, { zemin: hex(r.dolgu, 0.28), kenar: r.kontur, ic: r.kontur, kal: 0.07, parilti: true, metin: "#e6f7ff", buyuk: true, font: `500 ${Math.round(fpx(0.034) * 0.36)}px "IBM Plex Mono"`, font2: "IBM Plex Mono" }); },
      baslik(e, o) {
        const { Y, t, a, b, x, ust: yUst, vurgu } = o; const out = 1 - ara(t, b - 0.4, b); if (out <= 0) return;
        const kb = fpx(0.02), maxW = W * SS - 2 * gx, bb0 = fpx(dikey ? 0.066 : 0.064), ab = fpx(0.024); const m2 = ust(Y.baslik);
        const bb = sigdir(e, (s) => `700 ${s}px "Space Grotesk"`, bb0, m2, 0, maxW - bb0);
        e.save(); e.globalAlpha = out; e.textBaseline = "alphabetic"; e.textAlign = "left"; let y = yUst + kb;
        if (Y.ust) { const m = "// " + ust(Y.ust); e.font = `600 ${kb}px "IBM Plex Mono"`; e.fillStyle = vurgu; yaz(e, m.slice(0, Math.ceil(m.length * ara(t, a, a + 0.5))), x, y, kb * 0.12); }
        y += bb * 1.15; e.font = `700 ${bb}px "Space Grotesk"`; const f = ara(t, a + 0.3, a + 1.1), n = Math.floor(f * m2.length + 0.001), vis = m2.slice(0, n);
        e.save(); e.shadowColor = "rgba(0,8,16,0.9)"; e.shadowBlur = 12 * SS; e.fillStyle = "#eaf9ff"; e.fillText(vis, x, y); e.restore();
        if (Math.floor(t * 2.5) % 2 === 0 || f < 1) { const cx = x + e.measureText(vis).width + bb * 0.06; e.fillStyle = vurgu; e.fillRect(cx, y - bb * 0.72, bb * 0.08, bb * 0.78); }
        const lw = (maxW * 0.5) * expo(ara(t, a + 0.2, a + 1)); e.fillStyle = hex(vurgu.startsWith("#") ? vurgu : "#ffb347", 0.8); e.fillRect(x, y + bb * 0.22, lw, Math.max(1.5, bb * 0.02));
        if (Y.alt) { y += bb * 0.2 + ab * 1.7; e.font = `500 ${ab}px "IBM Plex Mono"`; const m3 = Y.alt; e.fillStyle = "rgba(210,236,250,0.88)"; yaz(e, m3.slice(0, Math.ceil(m3.length * ara(t, a + 0.9, a + 1.6))), x, y, 0); }
        e.restore(); return y + ab - yUst;
      },
      kutu(e, x, y, w, h, vurgu, f) { e.fillStyle = "rgba(2,10,16,0.62)"; e.fillRect(x, y, w * f, h); e.strokeStyle = vurgu; e.lineWidth = Math.max(1.5, h * 0.03); const k = h * 0.22, ww = w * f;
        for (const [cx, cy, sx, sy] of [[x, y, 1, 1], [x + ww, y, -1, 1], [x, y + h, 1, -1], [x + ww, y + h, -1, -1]]) { e.beginPath(); e.moveTo(cx, cy + sy * k); e.lineTo(cx, cy); e.lineTo(cx + sx * k, cy); e.stroke(); } },
    },

    // -------------------------------------------------------------------------------- KROKİ
    // Keçeli kalem krokisi: titreyen (8 fps "boil") el çizgisi, karalama tarama, iki vuruşlu açık ok ucu, el yazısı (Caveat),
    // altı çizilen adlar, bantlı yapışkan not kartları. Seyahat ve sosyoloji anlatısının sıcak, kişisel tonu.
    // Zaman: çizilerek gelir (ease-out), kartlar back-out ile hafif dönerek oturur.
    kroki: {
      hiz: 1.0, okEase: eo, cepheOlcek: 1.3, etiketSure: 0.9,
      ulkeDolgu(g, yol, f, r, px) { g.beginPath(); yol(f); g.fillStyle = hex(r.dolgu, 0.16); g.fill(); g.save(); g.clip();
        const [[x0, y0], [x1, y1]] = yol.bounds(f), ar = Math.max(6, px(11)), tohum = boil(); g.strokeStyle = hex(r.dolgu, 0.5); g.lineWidth = Math.max(1, px(2.2)); g.lineCap = "round";
        for (let s = x0 - (y1 - y0), i = 0; s < x1; s += ar, i++) { const pts = []; for (let j = 0; j <= 8; j++) { const f_ = j / 8; pts.push([s + (y1 - y0) * f_, y1 - (y1 - y0) * f_]); } cizgi(g, titret(pts, ar * 0.18, tohum + i)); g.stroke(); }
        g.restore(); },
      ulkeKontur(g, yol, f, r, px) { g.lineJoin = g.lineCap = "round"; const j = px(1.4), tohum = boil();
        for (const [dx, dy, al, w] of [[0, 0, 0.95, 2.8], [j * ((tohum % 3) - 1), j * (((tohum >> 1) % 3) - 1), 0.55, 1.6]]) { g.save(); g.translate(dx, dy); g.beginPath(); yol(f); g.strokeStyle = hex(r.kontur, al); g.lineWidth = px(w); g.stroke(); g.restore(); } },
      ok(g, yol, p, gen, r) {
        const ham = kirpYol(yol, p); if (ham.length < 2) return; const y = titret(ham, gen * 0.1, boil()), c = r.dolgu;
        g.save(); g.lineCap = g.lineJoin = "round"; g.save(); g.translate(gen * 0.08, gen * 0.14); cizgi(g, y); g.strokeStyle = "rgba(0,0,0,0.32)"; g.lineWidth = gen * 0.42; g.stroke(); g.restore();
        cizgi(g, y); g.strokeStyle = c; g.lineWidth = gen * 0.42; g.stroke(); cizgi(g, titret(ham, gen * 0.14, boil() + 9)); g.strokeStyle = hex(r.kontur, 0.55); g.lineWidth = gen * 0.16; g.stroke();
        const u = y[y.length - 1], o_ = y[Math.max(0, y.length - 6)]; let dx = u[0] - o_[0], dy = u[1] - o_[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
        const k = gen * 1.9 * backOut(sinir((p - 0.05) / 0.25)); for (const s of [1, -1]) { const ca = Math.cos(0.5 * s), sa = Math.sin(0.5 * s); const bx = -(dx * ca - dy * sa), by = -(dx * sa + dy * ca);
          cizgi(g, titret([[u[0], u[1]], [u[0] + bx * k * 0.5, u[1] + by * k * 0.5], [u[0] + bx * k, u[1] + by * k]], gen * 0.06, boil() + s)); g.strokeStyle = c; g.lineWidth = gen * 0.42; g.stroke(); }
        g.restore();
      },
      cephe(g, yol, gen, r, taraf) {
        const y = titret(yol, gen * 0.35, boil()); g.save(); g.lineCap = g.lineJoin = "round"; cizgi(g, y); g.strokeStyle = "rgba(0,0,0,0.3)"; g.lineWidth = gen * 1.6; g.stroke(); g.strokeStyle = r.kontur; g.lineWidth = gen * 1.05; g.stroke();
        boyunca(y, gen * 5, (x, yy, dx, dy, s) => { const nx = -dy * taraf, ny = dx * taraf, j = Math.sin(s * 0.7) * gen * 0.3; g.beginPath(); g.moveTo(x - dx * gen * 1.3, yy - dy * gen * 1.3); g.lineTo(x + nx * (gen * 2.3 + j), yy + ny * (gen * 2.3 + j)); g.lineTo(x + dx * gen * 1.3, yy + dy * gen * 1.3);
          g.strokeStyle = r.kontur; g.lineWidth = gen * 0.75; g.stroke(); });
        g.restore();
      },
      ulkeEtiket(e, o) {
        const boy = o.boy * 1.25; e.font = `700 ${boy}px "Caveat"`; const met = o.met, w = e.measureText(met).width, h = boy;
        if (!o.yer_(o.x - w / 2, o.y - h / 2, w, h * 1.2)) return; const f = eo(o.gir), c = o.r ? o.r.kontur : "#fff7e6";
        e.save(); e.globalAlpha = o.a; e.textAlign = "center"; e.textBaseline = "middle"; const rot = (((boil() * 7) % 5) - 2) * 0.002;
        e.translate(o.x, o.y); e.rotate(-0.03 + rot); e.save(); e.shadowColor = "rgba(0,0,0,0.7)"; e.shadowBlur = 8 * SS; e.fillStyle = "#fff7e6"; e.globalAlpha = o.a * sinir(f * 2); e.fillText(met, 0, 0); e.restore();
        if (o.r) { const pts = []; for (let j = 0; j <= 16; j++) pts.push([-w / 2 + w * 1.05 * (j / 16) * f, boy * 0.5 + Math.sin(j * 0.6) * boy * 0.04]); cizgi(e, titret(pts, boy * 0.03, boil())); e.strokeStyle = c; e.lineWidth = boy * 0.09; e.lineCap = "round"; e.stroke(); }
        e.restore();
      },
      sehir(e, o) {
        const boy = o.boy * 1.3; e.font = `600 ${boy}px "Caveat"`; const w = e.measureText(o.met).width, sag = o.yon > 0, x = sag ? o.x + boy * 0.75 : o.x - boy * 0.75 - w;
        if (!o.yer_(Math.min(o.x, x) - 4, o.y - boy * 0.6, w + boy, boy * 1.2)) return; const f = eo(o.gir);
        e.save(); e.globalAlpha = o.a; e.fillStyle = "#fff7e6"; e.beginPath(); e.arc(o.x, o.y, boy * 0.12, 0, 7); e.fill();
        const R = boy * (o.onem === 1 ? 0.42 : 0.3), pts = []; for (let j = 0; j <= 30 * f; j++) { const an = -1.2 + j / 30 * 7.4; pts.push([o.x + Math.cos(an) * R * (1 + 0.08 * Math.sin(j)), o.y + Math.sin(an) * R * 0.9]); }
        if (pts.length > 1) { cizgi(e, titret(pts, boy * 0.03, boil())); e.strokeStyle = o.rk ?? "#fff7e6"; e.lineWidth = boy * 0.08; e.lineCap = "round"; e.stroke(); }
        e.textBaseline = "middle"; e.shadowColor = "rgba(0,0,0,0.7)"; e.shadowBlur = 6 * SS; e.fillStyle = "#fff7e6"; e.globalAlpha = o.a * f; e.fillText(o.met, x, o.y); e.restore();
      },
      kart(e, q, p, t, a) {
        const t0 = q.t?.[0] ?? 0, b = fpx(0.021), r = renk(q.rol || "ana"), { yonx, ex, ey, kx } = kartYeri(p, q, dikey ? 0.12 : 0.1);
        const c1 = eo(ara(t, t0, t0 + 0.7)), c2 = ara(t, t0 + 0.45, t0 + 1.05), c3 = eo(ara(t, t0 + 0.7, t0 + 2.0));
        e.save(); e.globalAlpha = a; e.lineCap = e.lineJoin = "round";
        const pts = []; for (let j = 0; j <= 20 * c1; j++) { const f = j / 20; pts.push([p.x + (kx - p.x) * f + Math.sin(f * 3.1) * (ey - p.y) * -0.25 * yonx, p.y + (ey - p.y) * f]); }
        if (pts.length > 1) { cizgi(e, titret(pts, b * 0.08, boil())); e.strokeStyle = "#fff7e6"; e.lineWidth = b * 0.16; e.stroke(); }
        e.beginPath(); e.arc(p.x, p.y, b * 0.28, 0, 7); e.fillStyle = "#fff7e6"; e.fill();
        if (c2 > 0) {
          const vb = Math.round(b * 2.9); e.font = `700 ${Math.round(b * 1.35)}px "Caveat"`; const bw = e.measureText(q.baslik || "").width; e.font = `700 ${vb}px "Caveat"`; const sw = e.measureText(deger(q, 1)).width;
          e.font = `500 ${Math.round(b * 1.15)}px "Caveat"`; const aw = e.measureText(q.alt || "").width; const pad = b * 1.0, w = Math.max(sw, bw, aw) + pad * 2, h = b * (q.alt ? 6.2 : 4.9);
          const x = kiskac(yonx > 0 ? kx : kx - w, w), y = ey - h / 2, s = backOut(c2, 2.2), rot = (-0.045 + (1 - s) * -0.12) * (q.yon ?? 1);
          e.translate(x + w / 2, y + h / 2); e.rotate(rot); e.scale(0.6 + 0.4 * s, 0.6 + 0.4 * s); e.globalAlpha = a * sinir(c2 * 4);
          e.fillStyle = "rgba(0,0,0,0.38)"; e.fillRect(-w / 2 + b * 0.25, -h / 2 + b * 0.35, w, h); e.fillStyle = "#fbf3dc"; e.fillRect(-w / 2, -h / 2, w, h);
          e.fillStyle = "rgba(255,255,255,0.5)"; e.save(); e.rotate(0.06); e.fillRect(-b * 1.6, -h / 2 - b * 0.45, b * 3.2, b * 0.9); e.restore();
          e.textAlign = "left"; e.textBaseline = "alphabetic"; e.fillStyle = "#2b2620"; e.font = `700 ${Math.round(b * 1.35)}px "Caveat"`; e.fillText(q.baslik || "", -w / 2 + pad, -h / 2 + pad + b * 0.9);
          e.font = `700 ${vb}px "Caveat"`; e.fillStyle = "#1d1a16"; e.fillText(deger(q, c3), -w / 2 + pad, -h / 2 + pad + b * 3.45);
          const ul = []; for (let j = 0; j <= 12; j++) ul.push([-w / 2 + pad + sw * (j / 12) * c3, -h / 2 + pad + b * 3.8]); cizgi(e, titret(ul, b * 0.06, boil())); e.strokeStyle = r.dolgu; e.lineWidth = b * 0.2; e.stroke();
          if (q.alt) { e.font = `500 ${Math.round(b * 1.15)}px "Caveat"`; e.fillStyle = "#4a443b"; e.fillText(q.alt, -w / 2 + pad, -h / 2 + pad + b * 5.0); }
        }
        e.restore();
      },
      birlik(g, x, y, k, a) { birlikP(g, x, y, k, a, { el: true, kenar: "#fff7e6", ic: "#fff7e6", kal: 0.11, golge: "rgba(0,0,0,0.35)", metin: "#fff7e6", font: `700 ${Math.round(fpx(0.034) * 0.62)}px "Caveat"`, font2: "Caveat" }); },
      baslik(e, o) {
        const { Y, t, a, b, x, ust: yUst, vurgu } = o; const out = 1 - ara(t, b - 0.4, b); if (out <= 0) return;
        const kb = fpx(0.034), maxW = W * SS - 2 * gx, bb0 = fpx(dikey ? 0.092 : 0.09), ab = fpx(0.036); const m2 = Y.baslik;
        const bb = sigdir(e, (s) => `700 ${s}px "Caveat"`, bb0, m2, 0, maxW);
        e.save(); e.globalAlpha = out; e.textBaseline = "alphabetic"; e.textAlign = "left"; let y = yUst + kb;
        if (Y.ust) { e.font = `600 ${kb}px "Caveat"`; e.fillStyle = vurgu; e.globalAlpha = out * eo(ara(t, a, a + 0.5)); e.fillText(Y.ust, x, y); e.globalAlpha = out; }
        y += bb * 0.95; e.font = `700 ${bb}px "Caveat"`; const tw = e.measureText(m2).width, f = eo(ara(t, a + 0.15, a + 1.2));
        e.save(); e.beginPath(); e.rect(x - bb * 0.2, y - bb * 1.1, (tw + bb * 0.4) * f, bb * 1.5); e.clip(); e.shadowColor = "rgba(0,0,0,0.75)"; e.shadowBlur = 12 * SS; e.fillStyle = "#fff7e6"; e.fillText(m2, x, y); e.restore();
        const ul = [], g2 = eo(ara(t, a + 0.9, a + 1.6)); for (let j = 0; j <= 24; j++) ul.push([x + tw * 1.02 * (j / 24) * g2, y + bb * 0.2 - Math.sin(j / 24 * 3.1) * bb * 0.06]);
        if (g2 > 0) { cizgi(e, titret(ul, bb * 0.02, boil())); e.strokeStyle = vurgu; e.lineWidth = bb * 0.08; e.lineCap = "round"; e.stroke(); }
        if (Y.alt) { y += bb * 0.25 + ab * 1.3; e.font = `500 ${ab}px "Caveat"`; e.globalAlpha = out * eo(ara(t, a + 1.0, a + 1.6)); e.shadowColor = "rgba(0,0,0,0.75)"; e.shadowBlur = 8 * SS; e.fillStyle = "rgba(255,247,230,0.9)"; e.fillText(Y.alt, x, y); }
        e.restore(); return y + ab - yUst;
      },
      kutu(e, x, y, w, h, vurgu, f) { e.save(); e.fillStyle = "rgba(0,0,0,0.35)"; e.fillRect(x + h * 0.05, y + h * 0.07, w * f, h); e.fillStyle = "#fbf3dc"; e.fillRect(x, y, w * f, h); e.fillStyle = vurgu; e.fillRect(x, y, Math.max(4, h * 0.06), h); e.restore(); },
    },

    // -------------------------------------------------------------------------------- EDİTORYAL
    // Gazete veri haritası (İsviçre tipografisi): kıl çizgiler, gölgesiz düz dolgular, küçük dolu ok ucu, kılavuz çizgili
    // etiketler, kutusuz veri (büyük serif rakam + ince cetvel). Sakin ve kesin: cubic ease-out 0.7–0.9 sn, 80 ms kademeli girişler.
    editoryal: {
      hiz: 0.9, okEase: eo, cepheOlcek: 1.5, etiketSure: 0.8,
      ulkeDolgu(g, yol, f, r) { g.beginPath(); yol(f); g.fillStyle = hex(r.dolgu, r.alfa ?? 0.4); g.fill(); },
      ulkeKontur(g, yol, f, r, px) { g.lineJoin = "round"; g.beginPath(); yol(f); g.strokeStyle = "rgba(255,255,255,0.9)"; g.lineWidth = px(1.2); g.stroke(); },
      ok(g, yol, p, gen, r) {
        const y = kirpYol(yol, p); if (y.length < 2) return; const c = r.kontur, w = gen * 0.17, k = gen * 0.95;
        const u = y[y.length - 1], o_ = y[Math.max(0, y.length - 4)]; let dx = u[0] - o_[0], dy = u[1] - o_[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
        const gov = kirpYol(y, Math.max(0.001, 1 - k * 0.7 / Math.max(1, yolUzun(y))));
        g.save(); g.lineCap = "butt"; g.lineJoin = "round"; cizgi(g, gov); g.strokeStyle = "rgba(4,6,10,0.4)"; g.lineWidth = w + gen * 0.12; g.stroke(); g.strokeStyle = c; g.lineWidth = w; g.stroke();
        g.beginPath(); g.moveTo(u[0] + dx * k * 0.3, u[1] + dy * k * 0.3); g.lineTo(u[0] - dx * k * 0.7 - dy * k * 0.42, u[1] - dy * k * 0.7 + dx * k * 0.42); g.lineTo(u[0] - dx * k * 0.7 + dy * k * 0.42, u[1] - dy * k * 0.7 - dx * k * 0.42); g.closePath(); g.fillStyle = c; g.fill();
        g.beginPath(); g.arc(y[0][0], y[0][1], gen * 0.22, 0, 7); g.fill(); g.restore();
      },
      cephe(g, yol, gen, r, taraf) {
        g.save(); g.lineJoin = g.lineCap = "round"; cizgi(g, yol); g.strokeStyle = "rgba(4,6,10,0.4)"; g.lineWidth = gen * 0.9; g.stroke(); g.strokeStyle = r.kontur; g.lineWidth = gen * 0.5; g.stroke();
        boyunca(yol, gen * 3.4, (x, y, dx, dy) => { g.beginPath(); g.moveTo(x, y); g.lineTo(x - dy * taraf * gen * 1.4, y + dx * taraf * gen * 1.4); g.strokeStyle = r.kontur; g.lineWidth = gen * 0.4; g.stroke(); });
        g.restore();
      },
      ulkeEtiket(e, o) {
        const met = ust(o.met), boy = o.boy * 0.66, ar = boy * 0.16; e.font = `600 ${boy}px "Inter Tight"`; const w = genislik(e, met, ar), h = boy;
        if (!o.yer_(o.x - w / 2, o.y - h / 2, w, h)) return; const f = eo(o.gir);
        e.save(); e.globalAlpha = o.a * f; e.textBaseline = "middle"; e.textAlign = "left"; e.shadowColor = "rgba(0,6,14,0.75)"; e.shadowBlur = 8 * SS; e.fillStyle = "#fff"; yaz(e, met, o.x - w / 2 + ar / 2, o.y + (1 - f) * boy * 0.5, ar); e.restore();
      },
      sehir(e, o) {
        const boy = o.boy * 0.9; e.font = `500 ${boy}px "Inter Tight"`; const w = e.measureText(o.met).width, sag = o.yon > 0, L = boy * 1.1, lx = o.x + (sag ? 1 : -1) * L * 0.7, ly = o.y - L * 0.7;
        const x = sag ? lx + boy * 0.3 : lx - boy * 0.3 - w; if (!o.yer_(Math.min(o.x, x) - 4, ly - boy * 0.7, w + L + boy, boy * 1.4 + L)) return; const f = eo(o.gir);
        e.save(); e.globalAlpha = o.a; e.fillStyle = "#fff"; e.beginPath(); e.arc(o.x, o.y, boy * 0.16, 0, 7); e.fill(); if (o.onem === 1) { e.strokeStyle = "#fff"; e.lineWidth = boy * 0.06; e.beginPath(); e.arc(o.x, o.y, boy * 0.32, 0, 7); e.stroke(); }
        e.strokeStyle = "rgba(255,255,255,0.85)"; e.lineWidth = Math.max(1.2, boy * 0.05); e.beginPath(); e.moveTo(o.x, o.y); e.lineTo(o.x + (lx - o.x) * f, o.y + (ly - o.y) * f); e.stroke();
        e.globalAlpha = o.a * ara(o.gir, 0.4, 1); e.textBaseline = "middle"; e.shadowColor = "rgba(0,6,14,0.75)"; e.shadowBlur = 6 * SS; e.fillText(o.met, x, ly); e.restore();
      },
      kart(e, q, p, t, a) {
        const t0 = q.t?.[0] ?? 0, b = fpx(0.019), r = renk(q.rol || "ana"), uzun = fpx(dikey ? 0.1 : 0.09), yon = q.yon ?? 1;
        const c1 = eo(ara(t, t0, t0 + 0.6)), c2 = eo(ara(t, t0 + 0.4, t0 + 1.1)), c3 = eo(ara(t, t0 + 0.5, t0 + 1.9)), c4 = eo(ara(t, t0 + 0.65, t0 + 1.3));
        e.save(); e.globalAlpha = a; e.strokeStyle = "rgba(255,255,255,0.9)"; e.lineWidth = Math.max(1.2, b * 0.07); e.beginPath(); e.moveTo(p.x, p.y); e.lineTo(p.x, p.y - uzun * c1); e.stroke();
        e.fillStyle = "#fff"; e.beginPath(); e.arc(p.x, p.y, b * 0.26, 0, 7); e.fill();
        const vb = Math.round(b * 3.3), bas = ust(q.baslik || ""); e.font = `400 ${vb}px "Instrument Serif"`; const sw = e.measureText(deger(q, 1)).width; e.font = `600 ${Math.round(b * 0.85)}px "Inter Tight"`; const bw = genislik(e, bas, b * 0.14);
        e.font = `400 ${Math.round(b * 0.9)}px "Inter Tight"`; const aw = e.measureText(q.alt || "").width; const w = Math.max(sw, bw, aw), x = kiskac(yon > 0 ? p.x : p.x - w, w), cy = p.y - uzun;
        e.fillRect(yon > 0 ? x : x + w * (1 - c2), cy - Math.max(1, b * 0.035), w * c2, Math.max(2, b * 0.07));
        e.textAlign = "left"; e.textBaseline = "alphabetic"; e.shadowColor = "rgba(0,6,14,0.8)"; e.shadowBlur = 10 * SS;
        e.globalAlpha = a * c4; e.font = `400 ${vb}px "Instrument Serif"`; e.fillStyle = "#fff"; e.fillText(deger(q, c3), x, cy - b * 0.45 + (1 - c4) * b * 0.6);
        e.globalAlpha = a * eo(ara(t, t0 + 0.55, t0 + 1.2)); e.font = `600 ${Math.round(b * 0.85)}px "Inter Tight"`; e.fillStyle = r.kontur; yaz(e, bas, x, cy - b * 0.45 - vb * 0.82, b * 0.14);
        if (q.alt) { e.globalAlpha = a * eo(ara(t, t0 + 0.75, t0 + 1.4)); e.font = `400 ${Math.round(b * 0.9)}px "Inter Tight"`; e.fillStyle = "rgba(235,238,244,0.82)"; e.fillText(q.alt, x, cy + b * 1.35); }
        e.restore();
      },
      birlik(g, x, y, k, a) { birlikP(g, x, y, k, a, { boy: 0.028, kenar: "#fff", kal: 0.06, metin: "#fff" }); },
      baslik(e, o) {
        const { Y, t, a, b, x, ust: yUst, vurgu } = o; const out = 1 - ara(t, b - 0.5, b); if (out <= 0) return;
        const kb = fpx(0.019), maxW = W * SS - 2 * gx, bb0 = fpx(dikey ? 0.078 : 0.076), ab = fpx(0.027); const m2 = Y.baslik;
        const bb = sigdir(e, (s) => `400 ${s}px "Instrument Serif"`, bb0, m2, 0, maxW);
        e.save(); e.textBaseline = "alphabetic"; e.textAlign = "left"; let y = yUst + kb; const s1 = eo(ara(t, a, a + 0.8)), s2 = eo(ara(t, a + 0.08, a + 0.88)), s3 = eo(ara(t, a + 0.16, a + 0.96));
        if (Y.ust) { e.globalAlpha = out * s1; e.fillStyle = vurgu; e.fillRect(x, y - kb * 0.78, kb * 0.8, kb * 0.8); e.font = `600 ${kb}px "Inter Tight"`; e.fillStyle = "#fff"; yaz(e, ust(Y.ust), x + kb * 1.3, y, kb * 0.18); }
        y += bb * 1.05; e.globalAlpha = out * s2; e.font = `400 ${bb}px "Instrument Serif"`; e.save(); e.shadowColor = "rgba(0,6,14,0.75)"; e.shadowBlur = 14 * SS; e.fillStyle = "#fff"; e.fillText(m2, x, y + (1 - s2) * bb * 0.25); e.restore();
        if (Y.alt) { y += ab * 1.6; e.globalAlpha = out * s3; e.font = `400 ${ab}px "Inter Tight"`; e.save(); e.shadowColor = "rgba(0,6,14,0.75)"; e.shadowBlur = 8 * SS; e.fillStyle = "rgba(235,238,244,0.86)"; e.fillText(Y.alt, x, y + (1 - s3) * ab * 0.4); e.restore(); }
        e.globalAlpha = out; e.fillStyle = "rgba(255,255,255,0.7)"; e.fillRect(x, y + ab * 0.9, maxW * 0.18 * s3, Math.max(1, ab * 0.04));
        e.restore(); return y + ab - yUst;
      },
      kutu(e, x, y, w, h, vurgu, f) { e.fillStyle = "rgba(6,9,14,0.58)"; e.fillRect(x, y, w * f, h); e.fillStyle = vurgu; e.fillRect(x, y, w * f, Math.max(2, h * 0.03)); },
    },

    // -------------------------------------------------------------------------------- LÜKS
    // Lüks altın: siyah üstünde şampanya altını kıl çizgiler, çift raylı zarif ok ve ucunda kayan yıldız ışıltısı,
    // çok geniş harf aralıklı ince büyük harf (Inter Tight 300) + Instrument Serif. Yavaş, nefes alan: ease-out 1.2–1.8 sn,
    // harf aralığı daralarak oturur. Marka/premium anlatı, Atilla'nın "lüks, ortalanmış" çizgisi.
    luks: {
      hiz: 1.2, okEase: eio, cepheOlcek: 1.2, etiketSure: 1.5,
      ulkeDolgu(g, yol, f, r) { g.beginPath(); yol(f); g.fillStyle = hex(r.dolgu, r.alfa ?? 0.14); g.fill(); },
      ulkeKontur(g, yol, f, r, px) { g.lineJoin = "round"; g.beginPath(); yol(f); g.strokeStyle = hex(ALTIN, 0.28); g.lineWidth = px(5); g.stroke(); g.strokeStyle = hex(ALTIN, 0.95); g.lineWidth = px(1.1); g.stroke(); },
      ok(g, yol, p, gen, r) {
        const y = kirpYol(yol, p); if (y.length < 2) return; const sek = okSekli(y, gen * 0.9, { bas: 0.25, ucBoy: 2.4, ucGen: 0.85 }); if (!sek) return;
        g.save(); g.lineJoin = "miter"; sek(g); g.fillStyle = hex(r.dolgu, 0.45); g.fill(); g.strokeStyle = hex(ALTIN, 0.3); g.lineWidth = gen * 0.3; g.stroke(); g.strokeStyle = hex(ALTIN, 1); g.lineWidth = gen * 0.09; g.stroke();
        cizgi(g, sek.govde); g.strokeStyle = hex(ALTIN, 0.55); g.lineWidth = gen * 0.03; g.stroke();
        if (p < 1) { const [ux, uy] = sek.uc, k = gen * 1.1 * (1 - p * 0.6); g.fillStyle = "rgba(255,244,214,0.95)"; g.beginPath();
          for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4, rr = i % 2 ? k * 0.18 : k; g.lineTo(ux + Math.cos(a) * rr, uy + Math.sin(a) * rr); } g.closePath(); g.fill(); }
        g.restore();
      },
      cephe(g, yol, gen, r, taraf) {
        g.save(); cizgi(g, yol); g.strokeStyle = hex(ALTIN, 0.9); g.lineWidth = gen * 0.35; g.stroke();
        boyunca(yol, gen * 6, (x, y, dx, dy) => { const nx = -dy * taraf, ny = dx * taraf, k = gen * 1.1; g.beginPath(); g.moveTo(x + nx * k * 0.2, y + ny * k * 0.2);
          g.lineTo(x + dx * k * 0.6 + nx * k, y + dy * k * 0.6 + ny * k); g.lineTo(x + nx * k * 2, y + ny * k * 2); g.lineTo(x - dx * k * 0.6 + nx * k, y - dy * k * 0.6 + ny * k); g.closePath(); g.fillStyle = r.dolgu; g.fill(); g.strokeStyle = hex(ALTIN, 0.9); g.lineWidth = gen * 0.18; g.stroke(); });
        g.restore();
      },
      ulkeEtiket(e, o) {
        const met = ust(o.met), boy = o.boy * 0.58, f = eo(o.gir), ar = boy * (0.42 + 0.5 * (1 - f)); e.font = `300 ${boy}px "Inter Tight"`; const w = genislik(e, met, boy * 0.42), h = boy;
        if (!o.yer_(o.x - w / 2, o.y - h / 2, w, h)) return; const wc = genislik(e, met, ar);
        e.save(); e.globalAlpha = o.a * f; e.textBaseline = "middle"; e.textAlign = "left"; e.shadowColor = "rgba(0,0,0,0.9)"; e.shadowBlur = 8 * SS; e.fillStyle = o.r ? "#f3e2b8" : "rgba(240,232,214,0.85)"; yaz(e, met, o.x - wc / 2 + ar / 2, o.y, ar); e.restore();
      },
      sehir(e, o) {
        const boy = o.boy * 1.15; e.font = `italic 400 ${boy}px "Instrument Serif"`; const w = e.measureText(o.met).width, sag = o.yon > 0, x = sag ? o.x + boy * 0.7 : o.x - boy * 0.7 - w;
        if (!o.yer_(Math.min(o.x, x) - 4, o.y - boy * 0.6, w + boy, boy * 1.2)) return; const f = eo(o.gir), k = boy * (o.onem === 1 ? 0.3 : 0.22) * f;
        e.save(); e.globalAlpha = o.a; e.beginPath(); e.moveTo(o.x, o.y - k); e.lineTo(o.x + k, o.y); e.lineTo(o.x, o.y + k); e.lineTo(o.x - k, o.y); e.closePath(); e.fillStyle = ALTIN; e.fill();
        e.globalAlpha = o.a * f; e.textBaseline = "middle"; e.shadowColor = "rgba(0,0,0,0.9)"; e.shadowBlur = 8 * SS; e.fillStyle = "#f6eedb"; e.fillText(o.met, x, o.y); e.restore();
      },
      kart(e, q, p, t, a) {
        const t0 = q.t?.[0] ?? 0, b = fpx(0.019), { yonx, ex, ey, kx } = kartYeri(p, q);
        const c1 = eo(ara(t, t0, t0 + 0.9)), c2 = eio(ara(t, t0 + 0.6, t0 + 1.5)), c3 = eo(ara(t, t0 + 0.9, t0 + 2.4));
        e.save(); e.globalAlpha = a; e.strokeStyle = ALTIN; e.lineWidth = Math.max(1.2, b * 0.06); kirikCizgi(e, p, ex, ey, kx, c1);
        e.beginPath(); e.arc(p.x, p.y, b * 0.22, 0, 7); e.fillStyle = ALTIN; e.fill();
        if (c2 > 0) { const bas = ust(q.baslik || ""), vb = Math.round(b * 2.9); e.font = `300 ${Math.round(b * 0.8)}px "Inter Tight"`; const bw = genislik(e, bas, b * 0.4);
          e.font = `400 ${vb}px "Instrument Serif"`; const sw = e.measureText(deger(q, 1)).width; e.font = `italic 400 ${b}px "Instrument Serif"`; const aw = e.measureText(q.alt || "").width;
          const pad = b * 1.3, w = Math.max(sw, bw, aw) + pad * 2, h = b * (q.alt ? 6.4 : 5.0), x = kiskac(yonx > 0 ? kx : kx - w, w), y = ey - h / 2, xm = x + w / 2;
          e.fillStyle = "rgba(6,6,8,0.66)"; e.fillRect(xm - w / 2 * c2, y, w * c2, h); e.strokeStyle = ALTIN; e.lineWidth = Math.max(1, b * 0.05);
          e.beginPath(); e.moveTo(xm - w / 2 * c2, y); e.lineTo(xm + w / 2 * c2, y); e.moveTo(xm - w / 2 * c2, y + h); e.lineTo(xm + w / 2 * c2, y + h); e.stroke();
          e.globalAlpha = a * ara(c2, 0.6, 1); e.textAlign = "center"; e.textBaseline = "alphabetic"; e.font = `300 ${Math.round(b * 0.8)}px "Inter Tight"`; e.fillStyle = ALTIN; yaz(e, bas, xm + b * 0.2, y + pad + b * 0.3, b * 0.4);
          e.font = `400 ${vb}px "Instrument Serif"`; e.fillStyle = "#fbf6ea"; e.fillText(deger(q, c3), xm, y + pad + b * 3.0);
          if (q.alt) { e.font = `italic 400 ${b}px "Instrument Serif"`; e.fillStyle = "rgba(240,228,200,0.75)"; e.fillText(q.alt, xm, y + pad + b * 4.3); } }
        e.restore();
      },
      birlik(g, x, y, k, a) { birlikP(g, x, y, k, a, { boy: 0.03, zemin: "rgba(8,8,10,0.75)", kenar: ALTIN, ic: ALTIN, kal: 0.06, metin: "#f3e2b8", font: `300 ${Math.round(fpx(0.03) * 0.42)}px "Inter Tight"`, buyuk: true }); },
      baslik(e, o) {
        const { Y, t, a, b, x, ust: yUst } = o; const out = 1 - ara(t, b - 0.6, b); if (out <= 0) return;
        const kb = fpx(0.018), maxW = W * SS - 2 * gx, bb0 = fpx(dikey ? 0.08 : 0.08), ab = fpx(0.026), m2 = Y.baslik;
        const bb = sigdir(e, (s) => `400 ${s}px "Instrument Serif"`, bb0, m2, 0.02, maxW); const s1 = eo(ara(t, a, a + 1.4)), s2 = eo(ara(t, a + 0.25, a + 1.6)), s3 = eo(ara(t, a + 0.6, a + 1.8));
        e.save(); e.textBaseline = "alphabetic"; e.textAlign = "left"; let y = yUst + kb;
        if (Y.ust) { const m = ust(Y.ust), ar = kb * (0.5 + 0.6 * (1 - s1)); e.globalAlpha = out * s1; e.font = `300 ${kb}px "Inter Tight"`; e.fillStyle = ALTIN; yaz(e, m, x, y, ar); }
        y += bb * 1.1; e.globalAlpha = out * s2; e.font = `400 ${bb}px "Instrument Serif"`; e.save(); e.shadowColor = "rgba(0,0,0,0.85)"; e.shadowBlur = 14 * SS; e.fillStyle = "#fbf6ea"; yaz(e, m2, x, y, bb * 0.02); e.restore();
        const tw = genislik(e, m2, bb * 0.02); e.globalAlpha = out; e.fillStyle = ALTIN; e.fillRect(x, y + bb * 0.25, tw * s3, Math.max(1, bb * 0.012));
        if (Y.alt) { y += bb * 0.25 + ab * 1.6; e.globalAlpha = out * s3; e.font = `italic 400 ${ab}px "Instrument Serif"`; e.save(); e.shadowColor = "rgba(0,0,0,0.85)"; e.shadowBlur = 8 * SS; e.fillStyle = "rgba(240,228,200,0.88)"; e.fillText(Y.alt, x, y); e.restore(); }
        e.restore(); return y + ab - yUst;
      },
      kutu(e, x, y, w, h, vurgu, f) { e.fillStyle = "rgba(6,6,8,0.66)"; e.fillRect(x, y, w * f, h); e.strokeStyle = ALTIN; e.lineWidth = Math.max(1, h * 0.015); e.strokeRect(x + h * 0.05, y + h * 0.05, w * f - h * 0.1, h - h * 0.1); },
    },

    // -------------------------------------------------------------------------------- KÂĞIT
    // Kâğıt kesik (papercraft): her öğe kesilmiş renkli kâğıt; kalkık katman gölgesi, kalın düz şerit oklar, testere dişli
    // kâğıt cephe, eğik kâğıt etiketler, üst üste iki yapraklı kart, Fraunces. Stop-motion hissi: girişler back-out ile
    // "yapıştırılır", 0.4–0.7 sn; etiketler hafif açıyla durur.
    kagit: {
      hiz: 0.9, okEase: eoq, cepheOlcek: 1.3, etiketSure: 0.6,
      ulkeDolgu(g, yol, f, r, px) { g.save(); g.translate(px(3), px(5)); g.beginPath(); yol(f); g.fillStyle = "rgba(0,0,0,0.38)"; g.fill(); g.restore(); g.beginPath(); yol(f); g.fillStyle = hex(r.dolgu, r.alfa ?? 0.8); g.fill(); },
      ulkeKontur(g, yol, f, r, px) { g.lineJoin = "round"; g.beginPath(); yol(f); g.strokeStyle = "rgba(255,255,255,0.45)"; g.lineWidth = px(1.4); g.stroke(); },
      ok(g, yol, p, gen, r) {
        const y = kirpYol(yol, p); const sek = okSekli(y, gen * 0.85, { bas: 1, ucBoy: 2.2, ucGen: 1.25, kuyruk: true }); if (!sek) return;
        g.save(); g.lineJoin = "miter"; g.save(); g.translate(gen * 0.14, gen * 0.24); sek(g); g.fillStyle = "rgba(0,0,0,0.42)"; g.fill(); g.restore();
        sek(g); g.fillStyle = r.dolgu; g.fill(); g.save(); sek(g); g.clip(); const sol = sek.govde.map((q, i, A) => { const a_ = A[Math.max(0, i - 1)], b_ = A[Math.min(A.length - 1, i + 1)]; let dx = b_[0] - a_[0], dy = b_[1] - a_[1]; const l = Math.hypot(dx, dy) || 1; return [q[0] + dy / l * gen * 0.3, q[1] - dx / l * gen * 0.3]; });
        cizgi(g, sol); g.strokeStyle = "rgba(0,0,0,0.14)"; g.lineWidth = gen * 0.42; g.stroke(); g.restore(); sek(g); g.strokeStyle = "rgba(255,255,255,0.4)"; g.lineWidth = gen * 0.05; g.stroke(); g.restore();
      },
      cephe(g, yol, gen, r, taraf) {
        const ust_ = [], alt_ = []; boyunca(yol, gen * 1.6, (x, y, dx, dy, s) => { const nx = -dy * taraf, ny = dx * taraf, k = (Math.round(s / (gen * 1.6)) % 2) ? gen * 2.4 : gen * 0.9; ust_.push([x + nx * k, y + ny * k]); alt_.push([x - nx * gen * 0.7, y - ny * gen * 0.7]); }, 0);
        if (ust_.length < 2) return; const sek = (gg) => { cizgi(gg, ust_); for (let i = alt_.length - 1; i >= 0; i--) gg.lineTo(...alt_[i]); gg.closePath(); };
        g.save(); g.lineJoin = "miter"; g.save(); g.translate(gen * 0.5, gen * 0.8); sek(g); g.fillStyle = "rgba(0,0,0,0.4)"; g.fill(); g.restore(); sek(g); g.fillStyle = r.dolgu; g.fill(); g.strokeStyle = "rgba(255,255,255,0.4)"; g.lineWidth = gen * 0.15; g.stroke(); g.restore();
      },
      ulkeEtiket(e, o) {
        const met = o.met, boy = o.boy * 0.78; e.font = `700 ${boy}px "Fraunces"`; const tw = e.measureText(met).width, pad = boy * 0.4, w = tw + pad * 2, h = boy * 1.35;
        if (!o.yer_(o.x - w / 2, o.y - h / 2, w, h)) return; const s = backOut(sinir(o.gir), 2), rot = (((met.length * 37) % 7) - 3) * 0.012;
        e.save(); e.globalAlpha = o.a * sinir(o.gir * 4); e.translate(o.x, o.y); e.rotate(rot); e.scale(s, s); e.fillStyle = "rgba(0,0,0,0.4)"; e.fillRect(-w / 2 + boy * 0.1, -h / 2 + boy * 0.14, w, h);
        e.fillStyle = "#f7f1e3"; e.fillRect(-w / 2, -h / 2, w, h); e.fillStyle = o.r ? o.r.dolgu : "#9a948a"; e.fillRect(-w / 2, -h / 2, boy * 0.16, h);
        e.fillStyle = "#26211a"; e.textAlign = "center"; e.textBaseline = "middle"; e.fillText(met, boy * 0.08, boy * 0.05); e.restore();
      },
      sehir(e, o) {
        const boy = o.boy * 0.95; e.font = `600 ${boy}px "Fraunces"`; const w = e.measureText(o.met).width + boy * 0.6, sag = o.yon > 0, x = sag ? o.x + boy * 0.75 : o.x - boy * 0.75 - w, h = boy * 1.35;
        if (!o.yer_(Math.min(o.x, x) - 4, o.y - h / 2, w + boy, h)) return; const s = backOut(sinir(o.gir), 2);
        e.save(); e.globalAlpha = o.a * sinir(o.gir * 4); const R = boy * (o.onem === 1 ? 0.34 : 0.26) * s; e.fillStyle = "rgba(0,0,0,0.4)"; e.beginPath(); e.arc(o.x + boy * 0.06, o.y + boy * 0.1, R, 0, 7); e.fill();
        e.fillStyle = o.rk ?? "#f7f1e3"; e.beginPath(); e.arc(o.x, o.y, R, 0, 7); e.fill(); e.fillStyle = "#f7f1e3"; e.beginPath(); e.arc(o.x, o.y, R * 0.4, 0, 7); e.fill();
        e.translate(x + w / 2, o.y); e.rotate(sag ? -0.02 : 0.02); e.scale(s, s); e.fillStyle = "rgba(0,0,0,0.38)"; e.fillRect(-w / 2 + boy * 0.08, -h / 2 + boy * 0.12, w, h); e.fillStyle = "#f7f1e3"; e.fillRect(-w / 2, -h / 2, w, h);
        e.fillStyle = "#26211a"; e.textAlign = "center"; e.textBaseline = "middle"; e.fillText(o.met, 0, boy * 0.05); e.restore();
      },
      kart(e, q, p, t, a) {
        const t0 = q.t?.[0] ?? 0, b = fpx(0.02), r = renk(q.rol || "ana"), { yonx, ex, ey, kx } = kartYeri(p, q);
        const c1 = eo(ara(t, t0, t0 + 0.5)), c2 = ara(t, t0 + 0.3, t0 + 0.9), c3 = eo(ara(t, t0 + 0.5, t0 + 1.8));
        e.save(); e.globalAlpha = a; e.strokeStyle = "#f7f1e3"; e.lineWidth = b * 0.2; e.lineCap = "round"; e.setLineDash([b * 0.5, b * 0.4]); kirikCizgi(e, p, ex, ey, kx, c1); e.setLineDash([]);
        e.fillStyle = r.dolgu; e.beginPath(); e.arc(p.x, p.y, b * 0.4, 0, 7); e.fill();
        if (c2 > 0) { const vb = Math.round(b * 2.6); e.font = `600 ${Math.round(b * 0.95)}px "Fraunces"`; const bw = e.measureText(q.baslik || "").width; e.font = `700 ${vb}px "Fraunces"`; const sw = e.measureText(deger(q, 1)).width;
          e.font = `italic 600 ${Math.round(b * 0.9)}px "Fraunces"`; const aw = e.measureText(q.alt || "").width; const pad = b * 1.0, w = Math.max(sw, bw, aw) + pad * 2, h = b * (q.alt ? 6.0 : 4.8);
          const x = kiskac(yonx > 0 ? kx : kx - w, w), y = ey - h / 2, s = backOut(c2, 1.8); e.translate(x + w / 2, y + h / 2); e.scale(s, s); e.globalAlpha = a * sinir(c2 * 4);
          e.save(); e.rotate(0.05 * (q.yon ?? 1)); e.fillStyle = "rgba(0,0,0,0.35)"; e.fillRect(-w / 2 + b * 0.2, -h / 2 + b * 0.3, w, h); e.fillStyle = r.dolgu; e.fillRect(-w / 2, -h / 2, w, h); e.restore();
          e.rotate(-0.02 * (q.yon ?? 1)); e.fillStyle = "rgba(0,0,0,0.3)"; e.fillRect(-w / 2 + b * 0.15, -h / 2 + b * 0.22, w, h); e.fillStyle = "#f7f1e3"; e.fillRect(-w / 2, -h / 2, w, h);
          e.textAlign = "left"; e.textBaseline = "alphabetic"; e.fillStyle = "#6b5f4f"; e.font = `600 ${Math.round(b * 0.95)}px "Fraunces"`; e.fillText(q.baslik || "", -w / 2 + pad, -h / 2 + pad + b * 0.6);
          e.fillStyle = "#26211a"; e.font = `700 ${vb}px "Fraunces"`; e.fillText(deger(q, c3), -w / 2 + pad, -h / 2 + pad + b * 3.1);
          if (q.alt) { e.fillStyle = "#6b5f4f"; e.font = `italic 600 ${Math.round(b * 0.9)}px "Fraunces"`; e.fillText(q.alt, -w / 2 + pad, -h / 2 + pad + b * 4.35); } }
        e.restore();
      },
      birlik(g, x, y, k, a) { birlikP(g, x, y, k, a, { kenar: "#f7f1e3", ic: "#f7f1e3", kal: 0.1, golge: "rgba(0,0,0,0.45)", metin: "#26211a", kutu: "#f7f1e3", font: `600 ${Math.round(fpx(0.034) * 0.42)}px "Fraunces"` }); },
      baslik(e, o) {
        const { Y, t, a, b, x, ust: yUst, vurgu } = o; const out = 1 - ara(t, b - 0.4, b); if (out <= 0) return;
        const kb = fpx(0.024), maxW = W * SS - 2 * gx, bb0 = fpx(dikey ? 0.07 : 0.068), ab = fpx(0.027), m2 = Y.baslik;
        const bb = sigdir(e, (s) => `700 ${s}px "Fraunces"`, bb0, m2, 0, maxW - bb0); const s1 = backOut(ara(t, a, a + 0.5), 2), s2 = backOut(ara(t, a + 0.15, a + 0.7), 1.6), s3 = backOut(ara(t, a + 0.3, a + 0.85), 2);
        e.save(); e.globalAlpha = out; e.textBaseline = "middle"; e.textAlign = "left"; let y = yUst;
        const serit = (met, font, boy, zem, renk_, rot, s, padO) => { e.font = font; const w = e.measureText(met).width + boy * padO * 2, h = boy * 1.5; e.save(); e.translate(x + w / 2, y + h / 2); e.rotate(rot); e.scale(s, s);
          e.fillStyle = "rgba(0,0,0,0.4)"; e.fillRect(-w / 2 + boy * 0.08, -h / 2 + boy * 0.12, w, h); e.fillStyle = zem; e.fillRect(-w / 2, -h / 2, w, h); e.fillStyle = renk_; e.fillText(met, -w / 2 + boy * padO, boy * 0.05); e.restore(); y += h + boy * 0.12; };
        if (Y.ust && s1 > 0) serit(ust(Y.ust), `700 ${kb}px "Space Grotesk"`, kb, vurgu, "#26211a", -0.015, s1, 0.5);
        if (s2 > 0) serit(m2, `700 ${bb}px "Fraunces"`, bb, "#f7f1e3", "#26211a", 0.008, s2, 0.3);
        if (Y.alt && s3 > 0) serit(Y.alt, `italic 600 ${ab}px "Fraunces"`, ab, "#26211a", "#f7f1e3", -0.01, s3, 0.5);
        e.restore(); return y - yUst;
      },
      kutu(e, x, y, w, h, vurgu, f) { e.fillStyle = "rgba(0,0,0,0.38)"; e.fillRect(x + h * 0.05, y + h * 0.08, w * f, h); e.fillStyle = "#f7f1e3"; e.fillRect(x, y, w * f, h); e.fillStyle = vurgu; e.fillRect(x, y, Math.max(4, h * 0.07), h); },
    },

    // -------------------------------------------------------------------------------- FIRÇA
    // Mürekkep fırça (sumi-e): basınçla incelip kalınlaşan fırça darbesi oklar, kuru fırça kılları, mürekkep lekesi şehirler,
    // başlığın arkasında fırça "swash" vurgu, kırmızı mühür (hanko). Kaligrafik: hızlı darbe (expo-out 0.5–0.9 sn),
    // ardından durgunluk. Kültür, tarih, Doğu–Batı anlatıları.
    firca: {
      hiz: 0.75, okEase: expo, cepheOlcek: 1.3, etiketSure: 0.9,
      ulkeDolgu(g, yol, f, r, px) { g.beginPath(); yol(f); g.fillStyle = hex(r.dolgu, 0.2); g.fill(); g.save(); g.clip();
        for (const [d, al, w] of [[0, 0.32, 22], [px(3), 0.22, 12]]) { g.save(); g.translate(d, -d); g.beginPath(); yol(f); g.strokeStyle = hex(r.dolgu, al); g.lineWidth = px(w); g.stroke(); g.restore(); } g.restore(); },
      ulkeKontur(g, yol, f, r, px) { g.lineJoin = "round"; g.beginPath(); yol(f); g.strokeStyle = hex(r.kontur, 0.9); g.lineWidth = px(2.2); g.stroke(); g.save(); g.translate(px(1.5), px(1)); g.beginPath(); yol(f); g.strokeStyle = hex(r.kontur, 0.35); g.lineWidth = px(1); g.stroke(); g.restore(); },
      // ok: hızlı darbe (expo); ucunda ıslak mürekkep boncuğu, geçtiği yerde kâğıda yayılan açık hale, başı oturunca sıçrama
      ok(g, yol, p, gen, r) {
        const y = kirpYol(yol, p); if (y.length < 2) return; g.save(); g.lineCap = "round"; g.lineJoin = "round";
        const x_ = p >= 1 ? 1 : -Math.log2(1 - p) / 10; // expo'nun tersi: doğrusal ilerleme
        g.save(); g.translate(gen * 0.1, gen * 0.16); g.globalAlpha *= 0.35; fircaDarbe(g, y, gen * 0.85, "#000", 7); g.restore();
        const yay = eo(ara(x_, 0.05, 0.6)); fircaDarbe(g, y, gen * (0.95 + 0.45 * yay), hex(r.dolgu, 0.1 + 0.08 * yay), 7, 0);
        fircaDarbe(g, y, gen * 0.85, r.dolgu, 7);
        const u = y[y.length - 1], o_ = y[Math.max(0, y.length - 5)]; let dx = u[0] - o_[0], dy = u[1] - o_[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l; const k = gen * 1.6 * expo(ara(p, 0.85, 1));
        const bon = 1 - ara(x_, 0.22, 0.32); if (bon > 0) { g.fillStyle = koyu(r.dolgu, 0.55); g.globalAlpha *= 1; g.beginPath(); g.arc(u[0], u[1], gen * 0.42 * bon, 0, 7); g.fill(); }
        if (k > 0) for (const s of [1, -1]) { const ca = Math.cos(0.6 * s), sa = Math.sin(0.6 * s), bx = -(dx * ca - dy * sa), by = -(dx * sa + dy * ca); fircaDarbe(g, [[u[0] + bx * k, u[1] + by * k], [u[0] + bx * k * 0.5, u[1] + by * k * 0.5], [u[0], u[1]]], gen * 0.6, r.dolgu, 3 + s); }
        sicrama(g, u[0], u[1], dx, dy, gen, ara(x_, 0.27, 0.42), r.dolgu, Math.round(yolUzun(yol)) % 997);
        g.restore();
      },
      cephe(g, yol, gen, r, taraf) {
        fircaDarbe(g, yol, gen * 1.3, r.kontur, 11, 0.3);
        boyunca(yol, gen * 5, (x, y, dx, dy, s) => { const nx = -dy * taraf, ny = dx * taraf; fircaDarbe(g, [[x, y], [x + nx * gen * 1.4 + dx * gen * 0.3, y + ny * gen * 1.4 + dy * gen * 0.3], [x + nx * gen * 2.6 + dx * gen * 0.8, y + ny * gen * 2.6 + dy * gen * 0.8]], gen * 0.9, r.kontur, Math.round(s)); });
      },
      ulkeEtiket(e, o) {
        const met = o.met, boy = o.boy * 1.05; e.font = `italic 400 ${boy}px "Instrument Serif"`; const w = e.measureText(met).width, h = boy;
        if (!o.yer_(o.x - w / 2, o.y - h / 2, w, h * 1.2)) return; const f = expo(o.gir);
        e.save(); e.globalAlpha = o.a; if (o.r) { const pts = [[o.x - w * 0.55, o.y + boy * 0.42], [o.x, o.y + boy * 0.36], [o.x - w * 0.55 + w * 1.15 * f, o.y + boy * 0.3]]; fircaDarbe(e, kirpYol(pts, 1), boy * 0.22, o.r.dolgu, met.length); }
        e.globalAlpha = o.a; e.textAlign = "center"; e.textBaseline = "middle"; e.shadowColor = "rgba(0,0,0,0.85)"; e.shadowBlur = 8 * SS; murekkepYazi(e, met, o.x, o.y, ara(o.gir, 0.12, 1)); e.restore();
      },
      sehir(e, o) {
        const boy = o.boy * 1.1; e.font = `italic 400 ${boy}px "Instrument Serif"`; const w = e.measureText(o.met).width, sag = o.yon > 0, x = sag ? o.x + boy * 0.75 : o.x - boy * 0.75 - w;
        if (!o.yer_(Math.min(o.x, x) - 4, o.y - boy * 0.6, w + boy, boy * 1.2)) return; const f = expo(o.gir), rr = rng(o.met.length * 31 + 7);
        // mürekkep damlası: düşer (back-out), lekeler açılır, bir kez yayılan halka; isim fırçanın ardından sızar
        const d0 = backOut(ara(o.gir, 0, 0.32), 3), sp = expo(ara(o.gir, 0.06, 0.5)), rk = o.onem === 1 ? KIRMIZI : "#fbf7ef";
        e.save(); e.globalAlpha = o.a; e.fillStyle = rk; e.beginPath(); e.arc(o.x, o.y, boy * 0.24 * Math.max(0, d0), 0, 7); e.fill();
        for (let i = 0; i < 5; i++) { const an = rr() * 6.28, d = boy * (0.3 + rr() * 0.3) * sp; e.beginPath(); e.arc(o.x + Math.cos(an) * d, o.y + Math.sin(an) * d, boy * (0.03 + rr() * 0.05) * sp, 0, 7); e.fill(); }
        const h = ara(o.gir, 0.1, 1); if (h > 0 && h < 1) { e.strokeStyle = hex(rk, 0.55 * (1 - h)); e.lineWidth = boy * 0.05 * (1 - h * 0.6); e.beginPath(); e.arc(o.x, o.y, boy * (0.3 + 1.2 * eo(h)), 0, 7); e.stroke(); }
        e.textBaseline = "middle"; e.shadowColor = "rgba(0,0,0,0.85)"; e.shadowBlur = 8 * SS; murekkepYazi(e, o.met, x, o.y, ara(o.gir, 0.15, 1)); e.restore();
      },
      kart(e, q, p, t, a) {
        const t0 = q.t?.[0] ?? 0, b = fpx(0.02), r = renk(q.rol || "ana"), { yonx, ex, ey, kx } = kartYeri(p, q);
        const c1 = expo(ara(t, t0, t0 + 0.5)), c2 = expo(ara(t, t0 + 0.3, t0 + 0.9)), c3 = eo(ara(t, t0 + 0.5, t0 + 1.7));
        e.save(); e.globalAlpha = a; e.strokeStyle = "rgba(251,247,239,0.85)"; e.lineWidth = b * 0.1; kirikCizgi(e, p, ex, ey, kx, c1); e.fillStyle = "#fbf7ef"; e.beginPath(); e.arc(p.x, p.y, b * 0.28, 0, 7); e.fill();
        if (c2 > 0) { const vb = Math.round(b * 2.9); e.font = `400 ${vb}px "Instrument Serif"`; const sw = e.measureText(deger(q, 1)).width; e.font = `italic 400 ${Math.round(b * 1.05)}px "Instrument Serif"`; const bw = e.measureText(q.baslik || "").width, aw = e.measureText(q.alt || "").width;
          const pad = b * 0.9, w = Math.max(sw, bw, aw) + pad * 2, x = kiskac(yonx > 0 ? kx : kx - w, w), y0 = ey - b * 2.2;
          fircaDarbe(e, [[x, y0 + b * 0.6], [x + w * 0.5, y0 + b * 0.4], [x + w * c2, y0 + b * 0.5]], b * 3.2, hex(r.dolgu, 0.92), 5, 0.4);
          e.textAlign = "left"; e.textBaseline = "alphabetic"; e.shadowColor = "rgba(0,0,0,0.6)"; e.shadowBlur = 6 * SS; e.globalAlpha = a;
          e.font = `italic 400 ${Math.round(b * 1.05)}px "Instrument Serif"`; murekkepYazi(e, q.baslik || "", x + pad, y0 - b * 1.6, ara(t, t0 + 0.45, t0 + 1.0));
          e.font = `400 ${vb}px "Instrument Serif"`; murekkepYazi(e, deger(q, c3), x + pad, y0 + b * 1.45, ara(t, t0 + 0.5, t0 + 0.95));
          if (q.alt) { e.font = `italic 400 ${Math.round(b * 1.05)}px "Instrument Serif"`; murekkepYazi(e, q.alt, x + pad, y0 + b * 3.4, ara(t, t0 + 0.75, t0 + 1.4), "251,247,239", 0.8); }
          const m = b * 1.6; e.shadowBlur = 0; damga(e, x + w - m * 0.2, y0 - b * 2.4 + m / 2, m, t - (t0 + 0.8), ust((q.baslik || "?")[0])); }
        e.restore();
      },
      birlik(g, x, y, k, a) { birlikP(g, x, y, k, a, { el: true, kenar: "#fbf7ef", ic: "#fbf7ef", kal: 0.12, metin: "#fbf7ef", font: `italic 400 ${Math.round(fpx(0.034) * 0.55)}px "Instrument Serif"` }); },
      baslik(e, o) {
        const { Y, t, a, b, x, ust: yUst, vurgu } = o; const out = 1 - ara(t, b - 0.5, b); if (out <= 0) return;
        const kb = fpx(0.024), maxW = W * SS - 2 * gx, bb0 = fpx(dikey ? 0.085 : 0.085), ab = fpx(0.03), m2 = Y.baslik;
        const bb = sigdir(e, (s) => `400 ${s}px "Instrument Serif"`, bb0, m2, 0, maxW - bb0 * 0.5); e.font = `400 ${bb}px "Instrument Serif"`; const tw = e.measureText(m2).width;
        e.save(); e.globalAlpha = out; e.textBaseline = "alphabetic"; e.textAlign = "left"; let y = yUst + kb * 1.2;
        if (Y.ust) { const m = kb * 1.35; damga(e, x + m / 2, y - m * 0.45, m, t - a);
          e.font = `italic 400 ${kb}px "Instrument Serif"`; murekkepYazi(e, Y.ust, x + m * 1.4, y, ara(t, a + 0.2, a + 0.8)); }
        y += bb * 1.05; const s1 = expo(ara(t, a + 0.15, a + 0.75)); fircaDarbe(e, [[x - bb * 0.2, y + bb * 0.08], [x + tw * 0.5, y + bb * 0.02], [x - bb * 0.2 + (tw + bb * 0.5) * s1, y + bb * 0.06]], bb * 0.32, hex(vurgu, 0.9), 3, 0.35);
        e.font = `400 ${bb}px "Instrument Serif"`; e.save(); e.shadowColor = "rgba(0,0,0,0.7)"; e.shadowBlur = 10 * SS; murekkepYazi(e, m2, x, y, ara(t, a + 0.25, a + 1.0)); e.restore();
        if (Y.alt) { y += ab * 1.7; e.font = `italic 400 ${ab}px "Instrument Serif"`; e.save(); e.shadowColor = "rgba(0,0,0,0.8)"; e.shadowBlur = 8 * SS; murekkepYazi(e, Y.alt, x, y, ara(t, a + 0.75, a + 1.6), "251,247,239", 0.9); e.restore(); }
        e.restore(); return y + ab - yUst;
      },
      kutu(e, x, y, w, h, vurgu, f) { fircaDarbe(e, [[x, y + h / 2], [x + w * f * 0.5, y + h / 2 - h * 0.04], [x + w * f, y + h / 2]], h * 1.15, "rgba(8,8,10,0.82)", 9, 0.5); },
    },

    // -------------------------------------------------------------------------------- NEON
    // Neon tüp tabela: her çizgi bükülmüş cam tüp (renkli hale + beyaza yakın çekirdek), açık tüp ok ucu, tüp yazılar.
    // Giriş "yanıp tutuşma": 0.35 sn içinde birkaç kez titreşip sabitlenir (basamaklı zaman); sonra hafif uğultu titreşimi.
    // Gece hayatı, şehir sosyolojisi, gençlik kanalları.
    neon: {
      hiz: 0.85, okEase: eio, cepheOlcek: 1.3, etiketSure: 0.6,
      ulkeDolgu(g, yol, f, r) { g.beginPath(); yol(f); g.fillStyle = hex(r.dolgu, 0.08); g.fill(); },
      ulkeKontur(g, yol, f, r, px) { g.lineJoin = g.lineCap = "round"; for (const [w, al] of [[16, 0.07], [9, 0.16], [4.5, 0.55]]) { g.beginPath(); yol(f); g.strokeStyle = hex(r.kontur, al); g.lineWidth = px(w); g.stroke(); }
        g.beginPath(); yol(f); g.strokeStyle = "rgba(255,250,255,0.9)"; g.lineWidth = px(1.4); g.stroke(); },
      ok(g, yol, p, gen, r, z) {
        const y = kirpYol(yol, p); if (y.length < 2) return; const al = tutus(z); if (al <= 0) return; const u = y[y.length - 1], o_ = y[Math.max(0, y.length - 4)];
        let dx = u[0] - o_[0], dy = u[1] - o_[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l; const k = gen * 1.3;
        const bas = [[u[0] - dx * k - dy * k * 0.75, u[1] - dy * k + dx * k * 0.75], [u[0], u[1]], [u[0] - dx * k + dy * k * 0.75, u[1] - dy * k - dx * k * 0.75]];
        g.save(); g.globalAlpha *= al; tup(g, y, gen * 0.2, r.kontur); tup(g, bas, gen * 0.2, r.kontur); g.restore();
      },
      cephe(g, yol, gen, r, taraf, z) {
        g.save(); g.globalAlpha *= tutus(z); tup(g, yol, gen * 0.4, r.kontur);
        boyunca(yol, gen * 4, (x, y, dx, dy) => { const nx = -dy * taraf, ny = dx * taraf; tup(g, [[x - dx * gen, y - dy * gen], [x + nx * gen * 1.6, y + ny * gen * 1.6], [x + dx * gen, y + dy * gen]], gen * 0.28, r.kontur); }); g.restore();
      },
      ulkeEtiket(e, o) {
        const met = ust(o.met), boy = o.boy * 0.85, ar = boy * 0.12; e.font = `500 ${boy}px "Barlow Condensed"`; const w = genislik(e, met, ar), h = boy;
        if (!o.yer_(o.x - w / 2, o.y - h / 2, w, h)) return; const c = o.r ? o.r.kontur : "#cfe8ff";
        e.save(); e.globalAlpha = o.a * tutus(o.gir * 0.6); e.textAlign = "left"; e.textBaseline = "middle"; neonYazi(e, met, o.x - w / 2 + ar / 2, o.y, ar, boy, c); e.restore();
      },
      sehir(e, o) {
        const boy = o.boy * 0.95, met = o.met; e.font = `500 ${boy}px "Barlow Condensed"`; const w = genislik(e, met, boy * 0.06), sag = o.yon > 0, x = sag ? o.x + boy * 0.8 : o.x - boy * 0.8 - w;
        if (!o.yer_(Math.min(o.x, x) - 4, o.y - boy * 0.6, w + boy, boy * 1.2)) return; const c = o.rk ?? "#cfe8ff";
        e.save(); e.globalAlpha = o.a * tutus(o.gir * 0.6); const R = boy * (o.onem === 1 ? 0.3 : 0.2), pts = []; for (let i = 0; i <= 24; i++) pts.push([o.x + Math.cos(i / 24 * 6.283) * R, o.y + Math.sin(i / 24 * 6.283) * R]);
        tup(e, pts, boy * 0.07, c); e.textBaseline = "middle"; neonYazi(e, met, x, o.y, boy * 0.06, boy, "#e8f4ff"); e.restore();
      },
      kart(e, q, p, t, a) {
        const t0 = q.t?.[0] ?? 0, b = fpx(0.02), r = renk(q.rol || "ana"), c = r.kontur, { yonx, ex, ey, kx } = kartYeri(p, q);
        const c1 = eo(ara(t, t0, t0 + 0.5)), al = tutus((t - t0 - 0.4) * 1.0), c3 = eo(ara(t, t0 + 0.6, t0 + 1.8));
        e.save(); e.globalAlpha = a; const pts = []; for (let i = 0; i <= 12; i++) { const k = kirpYol([[p.x, p.y], [ex, ey], [kx, ey]], (i / 12) * c1); pts.push(k[k.length - 1]); } tup(e, pts, b * 0.1, c);
        if (al > 0) { const vb = Math.round(b * 2.6); e.font = `600 ${vb}px "Barlow Condensed"`; const sw = e.measureText(deger(q, 1)).width; e.font = `500 ${b}px "Barlow Condensed"`; const bw = genislik(e, ust(q.baslik || ""), b * 0.15), aw = e.measureText(q.alt || "").width;
          const pad = b * 1.1, w = Math.max(sw, bw, aw) + pad * 2, h = b * (q.alt ? 5.8 : 4.6), x = kiskac(yonx > 0 ? kx : kx - w, w), y = ey - h / 2, rr = b * 0.6;
          e.globalAlpha = a * al; e.fillStyle = "rgba(6,4,14,0.6)"; yuvarlak(e, x, y, w, h, rr); e.fill(); const cer = []; for (let i = 0; i <= 64; i++) cer.push(yuvarlakNokta(x, y, w, h, rr, i / 64)); tup(e, cer, b * 0.11, c);
          e.textAlign = "left"; e.textBaseline = "alphabetic"; e.font = `500 ${b}px "Barlow Condensed"`; neonYazi(e, ust(q.baslik || ""), x + pad, y + pad + b * 0.6, b * 0.15, b, c);
          e.font = `600 ${vb}px "Barlow Condensed"`; neonYazi(e, deger(q, c3), x + pad, y + pad + b * 3.0, 0, vb, "#fff2fb");
          if (q.alt) { e.font = `500 ${Math.round(b * 0.95)}px "Barlow Condensed"`; e.fillStyle = "rgba(230,220,255,0.8)"; e.fillText(q.alt, x + pad, y + pad + b * 4.2); } }
        e.restore();
      },
      birlik(g, x, y, k, a) { const r = renk(k.rol || "dost"); birlikP(g, x, y, k, a, { zemin: hex(r.dolgu, 0.18), kenar: r.kontur, ic: r.kontur, kal: 0.09, parilti: true, metin: "#f4ecff", font: `500 ${Math.round(fpx(0.034) * 0.45)}px "Barlow Condensed"` }); },
      baslik(e, o) {
        const { Y, t, a, b, x, ust: yUst, vurgu } = o; const out = 1 - ara(t, b - 0.4, b); if (out <= 0) return;
        const kb = fpx(0.024), maxW = W * SS - 2 * gx, bb0 = fpx(dikey ? 0.085 : 0.085), ab = fpx(0.028), m2 = ust(Y.baslik); const pembe = M.roller.karsi.kontur;
        const bb = sigdir(e, (s) => `500 ${s}px "Barlow Condensed"`, bb0, m2, 0.04, maxW - bb0 * 0.4);
        e.save(); e.globalAlpha = out; e.textBaseline = "alphabetic"; e.textAlign = "left"; let y = yUst + kb;
        if (Y.ust) { e.font = `500 ${kb}px "Barlow Condensed"`; e.globalAlpha = out * tutus(t - a); neonYazi(e, ust(Y.ust), x, y, kb * 0.25, kb, vurgu); }
        y += bb * 1.05; e.font = `500 ${bb}px "Barlow Condensed"`; e.globalAlpha = out * tutus(t - a - 0.3) * (0.92 + 0.08 * Math.sin(t * 23)); neonYazi(e, m2, x, y, bb * 0.04, bb, pembe);
        if (Y.alt) { y += ab * 1.7; e.font = `500 ${ab}px "Barlow Condensed"`; e.globalAlpha = out * tutus(t - a - 0.7); neonYazi(e, Y.alt, x, y, ab * 0.05, ab, "#cfe8ff"); }
        e.restore(); return y + ab - yUst;
      },
      kutu(e, x, y, w, h, vurgu, f) { e.fillStyle = "rgba(6,4,14,0.62)"; yuvarlak(e, x, y, w * f, h, h * 0.18); e.fill(); const p = []; for (let i = 0; i <= 48; i++) p.push(yuvarlakNokta(x, y, w * f, h, h * 0.18, i / 48)); tup(e, p, Math.max(1.5, h * 0.025), vurgu); },
    },

    // -------------------------------------------------------------------------------- ŞERİT (3D)
    // 3D şerit / kabartma: ülkeler zeminden kalkmış kalın levha (yan duvar + üst yüz), oklar kalınlığı olan şeritler
    // (koyu yan yüz, açık üst kenar ışığı), cephe duvarı, uzun gölgeli kabartma yazı, cam kart (yuvarlak köşe, ince beyaz kenar).
    // Modern motion grafik (After Effects 3D katman hissi): ease-out quint 0.6–1.0 sn, kartlar aşağıdan yükselir.
    serit: {
      hiz: 0.9, okEase: eoq, cepheOlcek: 1.3, etiketSure: 0.8,
      ulkeDolgu(g, yol, f, r, px) { const d = px(7); for (let i = 4; i >= 1; i--) { g.save(); g.translate(0, d * i / 4); g.beginPath(); yol(f); g.fillStyle = koyu(r.dolgu, 0.45); g.fill(); g.restore(); }
        g.beginPath(); yol(f); g.fillStyle = hex(r.dolgu, Math.max(0.55, r.alfa ?? 0.6)); g.fill(); },
      ulkeKontur(g, yol, f, r, px) { g.lineJoin = "round"; g.beginPath(); yol(f); g.strokeStyle = hex(r.kontur, 0.95); g.lineWidth = px(1.6); g.stroke(); },
      ok(g, yol, p, gen, r) {
        const y = kirpYol(yol, p); const sek = okSekli(y, gen, { bas: 0.8, ucBoy: 2.1, ucGen: 1.2 }); if (!sek) return; const d = gen * 0.42;
        g.save(); g.lineJoin = "round"; g.save(); g.translate(gen * 0.5, gen * 0.9); sek(g); g.fillStyle = "rgba(0,0,0,0.3)"; g.fill(); g.restore();
        for (let i = 6; i >= 1; i--) { g.save(); g.translate(0, d * i / 6); sek(g); g.fillStyle = koyu(r.dolgu, 0.5); g.fill(); g.restore(); }
        sek(g); g.fillStyle = r.dolgu; g.fill(); g.save(); sek(g); g.clip(); const sol = sek.govde.map((q, i, A) => { const a_ = A[Math.max(0, i - 1)], b_ = A[Math.min(A.length - 1, i + 1)]; let dx = b_[0] - a_[0], dy = b_[1] - a_[1]; const l = Math.hypot(dx, dy) || 1; return [q[0] + dy / l * gen * 0.45, q[1] - dx / l * gen * 0.45]; });
        cizgi(g, sol); g.strokeStyle = "rgba(255,255,255,0.35)"; g.lineWidth = gen * 0.3; g.stroke(); g.restore(); g.restore();
      },
      cephe(g, yol, gen, r, taraf) {
        const d = gen * 2.2; g.save(); g.lineJoin = g.lineCap = "round"; for (let i = 6; i >= 1; i--) { g.save(); g.translate(0, d * i / 6); cizgi(g, yol); g.strokeStyle = koyu(r.kontur, 0.45); g.lineWidth = gen * 1.1; g.stroke(); g.restore(); }
        cizgi(g, yol); g.strokeStyle = r.kontur; g.lineWidth = gen * 1.1; g.stroke(); cizgi(g, yol.map((q) => [q[0], q[1] - gen * 0.25])); g.strokeStyle = "rgba(255,255,255,0.45)"; g.lineWidth = gen * 0.3; g.stroke();
        boyunca(yol, gen * 5, (x, y, dx, dy) => { const nx = -dy * taraf, ny = dx * taraf; g.beginPath(); g.moveTo(x - dx * gen * 1.3, y - dy * gen * 1.3); g.lineTo(x + nx * gen * 2.3, y + ny * gen * 2.3); g.lineTo(x + dx * gen * 1.3, y + dy * gen * 1.3); g.closePath(); g.fillStyle = r.kontur; g.fill(); }); g.restore();
      },
      ulkeEtiket(e, o) {
        const met = ust(o.met), boy = o.boy * 0.85, ar = boy * 0.06; e.font = `700 ${boy}px "Space Grotesk"`; const w = genislik(e, met, ar), h = boy;
        if (!o.yer_(o.x - w / 2, o.y - h / 2, w, h * 1.3)) return; const f = eoq(o.gir), dy = (1 - f) * boy * 0.8;
        e.save(); e.globalAlpha = o.a * sinir(f * 2); e.textAlign = "left"; e.textBaseline = "middle"; const x0 = o.x - w / 2 + ar / 2;
        uzunGolge(e, met, x0, o.y + dy, ar, boy * 0.16 * f, o.r ? koyu(o.r.dolgu, 0.35) : "rgba(10,14,22,0.9)"); e.fillStyle = "#fff"; yaz(e, met, x0, o.y + dy, ar); e.restore();
      },
      sehir(e, o) {
        const boy = o.boy * 0.95; e.font = `600 ${boy}px "Space Grotesk"`; const w = e.measureText(o.met).width + boy * 0.9, h = boy * 1.6, sag = o.yon > 0, x = sag ? o.x + boy * 0.8 : o.x - boy * 0.8 - w;
        if (!o.yer_(Math.min(o.x, x) - 4, o.y - h / 2, w + boy, h)) return; const f = eoq(o.gir);
        e.save(); e.globalAlpha = o.a; const pinH = boy * 1.1 * f; e.strokeStyle = "rgba(255,255,255,0.85)"; e.lineWidth = boy * 0.08; e.beginPath(); e.moveTo(o.x, o.y); e.lineTo(o.x, o.y - pinH); e.stroke();
        e.fillStyle = o.rk ?? "#fff"; e.beginPath(); e.arc(o.x, o.y - pinH, boy * (o.onem === 1 ? 0.28 : 0.2), 0, 7); e.fill(); e.fillStyle = "rgba(0,0,0,0.35)"; e.beginPath(); e.ellipse(o.x, o.y, boy * 0.22, boy * 0.08, 0, 0, 7); e.fill();
        e.globalAlpha = o.a * f; const yy = o.y - pinH; cam(e, x, yy - h / 2 + (1 - f) * boy, w, h, h / 2); e.fillStyle = "#fff"; e.textBaseline = "middle"; e.fillText(o.met, x + boy * 0.45, yy + (1 - f) * boy + boy * 0.04); e.restore();
      },
      kart(e, q, p, t, a) {
        const t0 = q.t?.[0] ?? 0, b = fpx(0.02), r = renk(q.rol || "ana"), uzun = fpx(dikey ? 0.11 : 0.1);
        const c1 = eoq(ara(t, t0, t0 + 0.6)), c2 = eoq(ara(t, t0 + 0.3, t0 + 1.0)), c3 = eo(ara(t, t0 + 0.5, t0 + 1.7));
        e.save(); e.globalAlpha = a; const top = p.y - uzun * c1; e.strokeStyle = "rgba(255,255,255,0.9)"; e.lineWidth = b * 0.12; e.beginPath(); e.moveTo(p.x, p.y); e.lineTo(p.x, top); e.stroke();
        e.fillStyle = "rgba(0,0,0,0.4)"; e.beginPath(); e.ellipse(p.x, p.y, b * 0.6, b * 0.22, 0, 0, 7); e.fill(); e.fillStyle = r.dolgu; e.beginPath(); e.arc(p.x, p.y, b * 0.3, 0, 7); e.fill();
        if (c2 > 0) { const vb = Math.round(b * 2.6); e.font = `700 ${vb}px "Space Grotesk"`; const sw = e.measureText(deger(q, 1)).width; e.font = `600 ${Math.round(b * 0.9)}px "Inter Tight"`; const bw = genislik(e, ust(q.baslik || ""), b * 0.12), aw = e.measureText(q.alt || "").width;
          const pad = b * 1.05, w = Math.max(sw, bw, aw) + pad * 2, h = b * (q.alt ? 6.0 : 4.8), x = kiskac(p.x - w / 2, w), y = p.y - uzun - h + (1 - c2) * b * 2.5;
          e.globalAlpha = a * c2; e.fillStyle = "rgba(0,0,0,0.35)"; yuvarlak(e, x + b * 0.3, y + b * 0.6, w, h, b * 0.7); e.fill(); cam(e, x, y, w, h, b * 0.7);
          e.fillStyle = r.dolgu; yuvarlak(e, x + pad, y + pad * 0.7, b * 0.5, b * 0.5, b * 0.25); e.fill();
          e.textAlign = "left"; e.textBaseline = "alphabetic"; e.font = `600 ${Math.round(b * 0.9)}px "Inter Tight"`; e.fillStyle = "rgba(255,255,255,0.85)"; yaz(e, ust(q.baslik || ""), x + pad + b * 0.8, y + pad * 0.7 + b * 0.48, b * 0.12);
          e.font = `700 ${vb}px "Space Grotesk"`; e.fillStyle = "#fff"; e.fillText(deger(q, c3), x + pad, y + pad + b * 3.0);
          if (q.alt) { e.font = `500 ${Math.round(b * 0.9)}px "Inter Tight"`; e.fillStyle = "rgba(255,255,255,0.72)"; e.fillText(q.alt, x + pad, y + pad + b * 4.3); } }
        e.restore();
      },
      birlik(g, x, y, k, a) { birlikP(g, x, y, k, a, { kenar: "#fff", kal: 0.07, golge: "rgba(0,0,0,0.5)", metin: "#fff", font: `600 ${Math.round(fpx(0.034) * 0.4)}px "Space Grotesk"` }); },
      baslik(e, o) {
        const { Y, t, a, b, x, ust: yUst, vurgu } = o; const out = 1 - ara(t, b - 0.4, b); if (out <= 0) return;
        const kb = fpx(0.02), maxW = W * SS - 2 * gx, bb0 = fpx(dikey ? 0.075 : 0.074), ab = fpx(0.027), m2 = ust(Y.baslik);
        const bb = sigdir(e, (s) => `700 ${s}px "Space Grotesk"`, bb0, m2, 0, maxW - bb0 * 0.4); const s1 = eoq(ara(t, a, a + 0.7)), s2 = eoq(ara(t, a + 0.12, a + 0.9)), s3 = eoq(ara(t, a + 0.3, a + 1.05));
        e.save(); e.textBaseline = "alphabetic"; e.textAlign = "left"; let y = yUst;
        if (Y.ust) { e.font = `700 ${kb}px "Inter Tight"`; const m = ust(Y.ust), w = genislik(e, m, kb * 0.14) + kb * 1.6, h = kb * 2; e.globalAlpha = out * s1; e.fillStyle = vurgu; yuvarlak(e, x, y + (1 - s1) * kb, w, h, h / 2); e.fill();
          e.fillStyle = "#101418"; yaz(e, m, x + kb * 0.8, y + h * 0.68 + (1 - s1) * kb, kb * 0.14); y += h + kb * 0.4; }
        y += bb * 0.95; e.globalAlpha = out * s2; e.font = `700 ${bb}px "Space Grotesk"`; const yy = y + (1 - s2) * bb * 0.5; uzunGolge(e, m2, x, yy, 0, bb * 0.09 * s2, "rgba(10,14,22,0.92)"); e.fillStyle = "#fff"; e.fillText(m2, x, yy);
        if (Y.alt) { y += ab * 1.8; e.globalAlpha = out * s3; e.font = `500 ${ab}px "Inter Tight"`; e.save(); e.shadowColor = "rgba(0,0,0,0.8)"; e.shadowBlur = 8 * SS; e.fillStyle = "rgba(255,255,255,0.9)"; e.fillText(Y.alt, x, y + (1 - s3) * ab * 0.6); e.restore(); }
        e.restore(); return y + ab - yUst;
      },
      kutu(e, x, y, w, h, vurgu, f) { cam(e, x, y, w * f, h, h * 0.16); },
    },
  };
  const G_ = { ad, zaman: 0, ...(STILLER[ad] || {}) };
  return G_;
}

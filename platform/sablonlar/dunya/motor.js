// Dünya haritası motoru (tarayıcı tarafı). dunya.py sayfayı kurar, window.__VERI'yi doldurur ve her kare için
// window.ciz(saniye) çağırır. Çizim mantıksal W×H koordinatlarında yapılır, tuval SS kat büyüktür (süper örnekleme);
// küçültme Python/ffmpeg tarafında lanczos ile yapılır.
(function () {
  "use strict";
  const d3 = window.d3, topo = window.topojson, V = window.__VERI, S = V.sahne;
  const W = S.W, H = S.H, SS = S.ss;
  const cv = document.getElementById("c");
  cv.width = Math.round(W * SS); cv.height = Math.round(H * SS);
  const ctx = cv.getContext("2d");

  // ---------- yardımcılar ----------
  const kel = (x) => Math.max(0, Math.min(1, x));
  const ara = (u, a, b) => kel((u - a) / (b - a));
  const lerp = (a, b, x) => a + (b - a) * x;
  const eio = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  const eo = (x) => 1 - Math.pow(1 - x, 3);
  const esin = (x) => -(Math.cos(Math.PI * x) - 1) / 2;
  function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  const hex = (h, a = 1) => { const n = parseInt(h.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };

  // güvenli alan (9:16: üst %10, alt %22 platform arayüzü)
  const dikey = H > W;
  const G = dikey ? { x0: W * 0.07, y0: H * 0.11, x1: W * 0.93, y1: H * 0.77 } : { x0: W * 0.06, y0: H * 0.08, x1: W * 0.94, y1: H * 0.92 };
  const birim = Math.min(W, H) / 1080; // yazı ve çizgi ölçeği

  // ---------- geometri ----------
  const ULKELER = topo.feature(V.ulkeler, V.ulkeler.objects.countries).features;
  const SINIR = topo.mesh(V.ulkeler, V.ulkeler.objects.countries, (a, b) => a !== b);
  const KARA = topo.feature(V.kara, V.kara.objects.land);
  const KIYI = topo.mesh(V.kara, V.kara.objects.land);
  const KURE = { type: "Sphere" };
  const AG = d3.geoGraticule().step([15, 15])();
  const VURGU = (S.vurgu || []).map((v) => {
    const f = ULKELER.find((u) => u.properties.name === v.ad) || ULKELER.find((u) => v.nokta && d3.geoContains(u, v.nokta));
    return f ? { ...v, f } : null;
  }).filter(Boolean);
  const ROTA = S.rota || [];
  const NOKTALAR = S.noktalar || [];

  // rota: duraklar arası büyük daire, her noktada genel ilerleme s
  const rotaGeo = [];
  for (let i = 0; i + 1 < ROTA.length; i++) {
    const ip = d3.geoInterpolate([ROTA[i].lon, ROTA[i].lat], [ROTA[i + 1].lon, ROTA[i + 1].lat]);
    for (let j = 0; j <= 160; j++) if (j || !i) rotaGeo.push({ p: ip(j / 160), bolum: i, yerel: j / 160 });
  }
  rotaGeo.forEach((q, k) => (q.s = k / Math.max(1, rotaGeo.length - 1)));

  // ---------- projeksiyon ve kamera ----------
  const PROJ = {
    equalEarth: d3.geoEqualEarth, naturalEarth: d3.geoNaturalEarth1, robinson: d3.geoRobinson,
    ortho: d3.geoOrthographic, equirect: d3.geoEquirectangular, winkel: d3.geoWinkel3, mollweide: d3.geoMollweide,
  };
  let proj, yol, ekran = (x, y) => [x, y];
  const kuremi = () => ST.projeksiyon === "ortho";

  function kur(kam) {
    proj = PROJ[ST.projeksiyon]().precision(0.3);
    if (kuremi()) {
      proj.rotate([-kam.lon, -kam.lat, 0]).scale(Math.min(W, H) * 0.42 * kam.k).translate([W / 2 + kam.dx, H / 2 + kam.dy]).clipAngle(90);
    } else {
      const b = PROJ[ST.projeksiyon]().rotate([-kam.lon, 0]);
      b.fitExtent([[0, 0], [W * ST.dunyaGenislik, H * 0.86]], KURE);
      proj.rotate([-kam.lon, 0]).center([0, kam.lat]).scale(b.scale() * kam.k).translate([W / 2 + kam.dx, H / 2 + kam.dy]);
    }
    proj.clipExtent([[-W * 0.2, -H * 0.2], [W * 1.2, H * 1.2]]);
    yol = d3.geoPath(proj);
  }

  // bölge kadrajı: rota + noktalar + vurgu ülkeleri ekranın ortasına sığsın
  function bolgeKamerasi() {
    const pts = [...ROTA, ...NOKTALAR].map((p) => [p.lon, p.lat]);
    VURGU.forEach((v) => { const b = d3.geoBounds(v.f); pts.push(b[0], b[1], [b[0][0], b[1][1]], [b[1][0], b[0][1]]); });
    if (!pts.length) return ST.dunya;
    let kam = { lon: d3.mean(pts, (p) => p[0]), lat: d3.mean(pts, (p) => p[1]), k: 1, dx: 0, dy: 0 };
    for (let it = 0; it < 3; it++) {
      kur(kam);
      const xy = pts.map((p) => proj(p)).filter(Boolean);
      const x0 = d3.min(xy, (p) => p[0]), x1 = d3.max(xy, (p) => p[0]), y0 = d3.min(xy, (p) => p[1]), y1 = d3.max(xy, (p) => p[1]);
      const mer = proj.invert([(x0 + x1) / 2, (y0 + y1) / 2]);
      const ok = Math.min((W * ST.bolgeDolgu[0]) / Math.max(1, x1 - x0), (H * ST.bolgeDolgu[1]) / Math.max(1, y1 - y0));
      kam = { lon: mer[0], lat: mer[1], k: Math.min(kam.k * ok, ST.enFazlaZoom), dx: 0, dy: 0 };
    }
    kam.dx = dikey ? 0 : W * ST.bolgeKaydir; kam.dy = dikey ? -H * 0.05 : 0;
    return kam;
  }

  // ---------- kayıt bağlamı: d3 çizimini çoklu çizgiye çevirir ----------
  function cizgiler(geo) {
    const l = []; let cur = null;
    const r = {
      beginPath() {}, moveTo(x, y) { cur = [ekran(x, y)]; l.push(cur); }, lineTo(x, y) { cur.push(ekran(x, y)); },
      closePath() { if (cur && cur.length) { cur.push(cur[0].slice()); cur.kapali = true; } }, arc() {},
    };
    yol.context(r)(geo); yol.context(null);
    return l;
  }
  function izle(c, lines) { c.beginPath(); for (const l of lines) { c.moveTo(l[0][0], l[0][1]); for (let i = 1; i < l.length; i++) c.lineTo(l[i][0], l[i][1]); } }
  // çizgileri soldan sağa süpürerek kısmen çiz (f: 0..1)
  function kismi(lines, f, supur = 0.5) {
    if (f >= 1) return lines;
    const out = [];
    for (const l of lines) {
      const x = l[0][0] / W; const g = kel((f * (1 + supur) - x * supur));
      if (g <= 0) continue;
      if (g >= 1) { out.push(l); continue; }
      let L = 0; const d = [0];
      for (let i = 1; i < l.length; i++) { L += Math.hypot(l[i][0] - l[i - 1][0], l[i][1] - l[i - 1][1]); d.push(L); }
      const hedef = L * g, p = [l[0]];
      for (let i = 1; i < l.length; i++) {
        if (d[i] <= hedef) p.push(l[i]);
        else { const k = (hedef - d[i - 1]) / (d[i] - d[i - 1] || 1); p.push([lerp(l[i - 1][0], l[i][0], k), lerp(l[i - 1][1], l[i][1], k)]); break; }
      }
      if (p.length > 1) out.push(p);
    }
    return out;
  }
  function titret(lines, gen, tohum) { // el çizimi titremesi
    const r = rng(tohum); const fx = r() * 100, fy = r() * 100;
    return lines.map((l) => l.map((p, i) => [p[0] + gen * Math.sin(i * 0.21 + fx + p[1] * 0.013), p[1] + gen * Math.cos(i * 0.17 + fy + p[0] * 0.011)]));
  }

  // rota ekranda: düz haritada kavis, kürede yükseklik
  function rotaEkran() {
    if (!rotaGeo.length) return [];
    const out = [];
    for (let i = 0; i + 1 < ROTA.length; i++) {
      const parca = rotaGeo.filter((q) => q.bolum === i);
      const a = proj(parca[0].p), b = proj(parca[parca.length - 1].p);
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const nx = (a[1] - b[1]) / (L || 1), ny = (b[0] - a[0]) / (L || 1);
      const yon = ny > 0 ? -1 : 1; // kavis yukarı doğru
      for (const q of parca) {
        let p = proj(q.p);
        const h = Math.sin(Math.PI * q.yerel);
        if (kuremi()) { const c = proj.translate(); const k = 1 + 0.06 * h; p = [c[0] + (p[0] - c[0]) * k, c[1] + (p[1] - c[1]) * k]; }
        else p = [p[0] + yon * nx * L * ST.kavis * h, p[1] + yon * ny * L * ST.kavis * h];
        out.push({ x: p[0], y: p[1], s: q.s });
      }
    }
    return out;
  }
  function rotaKismi(pts, f) {
    const out = []; for (const p of pts) { if (p.s <= f) out.push([p.x, p.y]); else break; }
    return out;
  }
  const gorunur = (lon, lat) => !kuremi() || d3.geoDistance([lon, lat], proj.invert(proj.translate())) < Math.PI / 2 - 0.05;

  // ---------- doku: gren (bantlanmayı da kırar) ----------
  const grenler = {};
  function gren(ad, genlik, tohum = 7) {
    if (grenler[ad]) return grenler[ad];
    const c = document.createElement("canvas"); c.width = cv.width; c.height = cv.height;
    const g = c.getContext("2d"); const im = g.createImageData(c.width, c.height); const r = rng(tohum);
    for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() + r() - 1) * genlik; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
    g.putImageData(im, 0, 0); grenler[ad] = c; return c;
  }
  function grenUygula(ad, genlik, alfa, kip = "overlay") {
    const c = gren(ad, genlik); ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = kip; ctx.globalAlpha = alfa; ctx.drawImage(c, 0, 0); ctx.restore();
  }
  function katman() { const c = document.createElement("canvas"); c.width = cv.width; c.height = cv.height; const g = c.getContext("2d"); g.setTransform(SS, 0, 0, SS, 0, 0); return [c, g]; }
  let parlak = null;
  function parilti(cizim, blur, alfa = 1) { // ışıma: ayrı katmanda çiz, bulanıklaştırıp 'lighter' ile ekle
    if (!parlak) parlak = katman();
    const [c, g] = parlak; g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, c.width, c.height); g.restore();
    cizim(g);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = "lighter"; ctx.globalAlpha = alfa;
    ctx.filter = `blur(${blur * SS}px)`; ctx.drawImage(c, 0, 0); ctx.filter = "none"; ctx.drawImage(c, 0, 0); ctx.restore();
  }

  // zemin: düz haritada okyanus tüm ekran; kürede dış zemin + gölgeli küre
  function arkaplan(okyanus, dis, cizgi) {
    if (!kuremi()) { ctx.fillStyle = okyanus; ctx.fillRect(0, 0, W, H); return; }
    ctx.fillStyle = dis; ctx.fillRect(0, 0, W, H);
    const c = proj.translate(), R = proj.scale();
    ctx.save(); ctx.shadowColor = "rgba(0,0,0,0.28)"; ctx.shadowBlur = R * 0.08 * SS; ctx.shadowOffsetY = R * 0.03 * SS;
    ctx.fillStyle = okyanus; ctx.beginPath(); ctx.arc(c[0], c[1], R, 0, 7); ctx.fill(); ctx.restore();
    if (cizgi) { ctx.strokeStyle = cizgi; ctx.lineWidth = 1.2 * birim; ctx.beginPath(); ctx.arc(c[0], c[1], R, 0, 7); ctx.stroke(); }
  }


  // ---------- WebGL dokulu küre: gerçek arazi (gölgelendirme + derinlik) dokusu, ışık, kenar ----------
  // V.dokular = {dunya: url, bolge: {url, kutu}}; düz haritada kullanılmaz
  let GLK = null;
  async function dokuYukle() {
    if (!V.dokular || !V.dokular.dunya) return;
    const yukle = (url) => new Promise((ok, red) => { const im = new Image(); im.onload = () => ok(im); im.onerror = red; im.src = url; });
    const c = document.createElement("canvas"); c.width = cv.width; c.height = cv.height;
    const gl = c.getContext("webgl", { preserveDrawingBuffer: true, premultipliedAlpha: true, antialias: false, alpha: true });
    if (!gl) return;
    const vs = "attribute vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }";
    const fs = `precision highp float;
      uniform vec2 uC; uniform float uR; uniform vec2 uM; uniform vec2 uBoy;
      uniform sampler2D uD0; uniform sampler2D uD1; uniform vec4 uK1; uniform float uB1;
      uniform vec3 uL; uniform float uOrt, uYay, uParla, uAtm; uniform vec3 uAtmRenk;
      const float PI = 3.14159265;
      void main(){
        vec2 q = vec2(gl_FragCoord.x, uBoy.y - gl_FragCoord.y);
        float x = (q.x - uC.x) / uR, y = (uC.y - q.y) / uR; float r2 = x*x + y*y;
        if (r2 > 1.0) { gl_FragColor = vec4(0.0); return; }
        float z = sqrt(1.0 - r2); float sf = sin(uM.y), cf = cos(uM.y);
        float lat = asin(clamp(z*sf + y*cf, -1.0, 1.0));
        float lon = uM.x + atan(x, z*cf - y*sf);
        float dlon = degrees(lon), dlat = degrees(lat);
        dlon = mod(dlon + 180.0, 360.0) - 180.0;
        vec3 renk = texture2D(uD0, vec2((dlon + 180.0) / 360.0, (90.0 - dlat) / 180.0)).rgb;
        if (uB1 > 0.0) {
          vec2 t = vec2((dlon - uK1.x) / (uK1.z - uK1.x), (uK1.w - dlat) / (uK1.w - uK1.y));
          float kenar = min(min(t.x, 1.0 - t.x), min(t.y, 1.0 - t.y));
          float w = smoothstep(0.0, 0.04, kenar) * uB1;
          if (kenar > 0.0) renk = mix(renk, texture2D(uD1, t).rgb, w);
        }
        vec3 n = vec3(x, y, z);
        float dif = max(dot(n, normalize(uL)), 0.0);
        vec3 col = renk * (uOrt + uYay * dif);
        vec3 h = normalize(normalize(uL) + vec3(0.0, 0.0, 1.0));
        float deniz = step(renk.r + 0.02, renk.b) ;
        col += uParla * deniz * pow(max(dot(n, h), 0.0), 60.0);
        col = mix(col, uAtmRenk, uAtm * pow(1.0 - z, 2.2));
        float a = smoothstep(1.0, 1.0 - 1.6 / uR, sqrt(r2));
        gl_FragColor = vec4(col * a, a);
      }`;
    const derle = (tip, kaynak) => { const sh = gl.createShader(tip); gl.shaderSource(sh, kaynak); gl.compileShader(sh); if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh)); return sh; };
    const pr = gl.createProgram(); gl.attachShader(pr, derle(gl.VERTEX_SHADER, vs)); gl.attachShader(pr, derle(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(pr); gl.useProgram(pr);
    const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const lp = gl.getAttribLocation(pr, "p"); gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp, 2, gl.FLOAT, false, 0, 0);
    const doku = (im, birim, mip) => {
      const t = gl.createTexture(); gl.activeTexture(gl.TEXTURE0 + birim); gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, im);
      if (mip) { gl.generateMipmap(gl.TEXTURE_2D); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); }
      else gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, mip ? gl.REPEAT : gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    };
    doku(await yukle(V.dokular.dunya), 0, true);
    let bolge = null;
    if (V.dokular.bolge) { doku(await yukle(V.dokular.bolge.url), 1, false); bolge = V.dokular.bolge.kutu; } else doku(await yukle(V.dokular.dunya), 1, false);
    const U = (ad) => gl.getUniformLocation(pr, ad);
    gl.uniform1i(U("uD0"), 0); gl.uniform1i(U("uD1"), 1);
    GLK = { c, gl, U, bolge };
  }
  function dokuluKure(o) { // o: {ort, yay, parla, atm, atmRenk:[r,g,b], isik:[x,y,z], alfa}
    if (!GLK || !kuremi()) return false;
    const { c, gl, U, bolge } = GLK; const m = proj.rotate(), t = proj.translate();
    gl.viewport(0, 0, c.width, c.height); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform2f(U("uC"), t[0] * SS, t[1] * SS); gl.uniform1f(U("uR"), proj.scale() * SS); gl.uniform2f(U("uM"), (-m[0] * Math.PI) / 180, (-m[1] * Math.PI) / 180);
    gl.uniform2f(U("uBoy"), c.width, c.height);
    if (bolge) { gl.uniform4f(U("uK1"), ...bolge); gl.uniform1f(U("uB1"), kel((proj.scale() / (Math.min(W, H) * 0.42) - 1.6) / 1.2)); } else gl.uniform1f(U("uB1"), 0);
    gl.uniform3f(U("uL"), ...(o.isik || [-0.55, 0.6, 0.62])); gl.uniform1f(U("uOrt"), o.ort); gl.uniform1f(U("uYay"), o.yay); gl.uniform1f(U("uParla"), o.parla || 0);
    gl.uniform1f(U("uAtm"), o.atm || 0); gl.uniform3f(U("uAtmRenk"), ...(o.atmRenk || [0, 0, 0]));
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = o.alfa ?? 1; ctx.drawImage(c, 0, 0); ctx.restore();
    return true;
  }
  // ülke adı: marka yazı sistemi (geniş aralıklı büyük harf, ülkenin ortasında)
  function ulkeAdi(v, g, o) {
    if (g <= 0) return; const m = d3.geoCentroid(v.f); if (!gorunur(...m)) return;
    const ad = (v.etiket || v.ad).toLocaleUpperCase(S.dil === "de" ? "de" : "tr");
    const w = genislik(ad, o.font, o.aralik || "0.32em");
    // ilk ülke: içinde, merkezin altında; diğerleri: ülkenin üst kenarının üstünde (şehir etiketleriyle çakışmasın)
    let x, y; const b = yol.bounds(v.f);
    if (o.ust) { x = (b[0][0] + b[1][0]) / 2 - w / 2; y = b[0][1] - 12 * birim; }
    else { const p = proj(m); x = p[0] - w / 2; y = p[1] + (o.dy || 0); }
    x = Math.max(G.x0, Math.min(G.x1 - w, x)); y = Math.max(G.y0 + 20 * birim, y);
    yazi(ad, x, y, { font: o.font, renk: o.renk, alfa: g, aralik: o.aralik || "0.32em", hale: o.hale, haleGen: o.haleGen });
    yerlesik.push([x - 4, y - 20 * birim, x + w + 4, y + 6 * birim]);
  }

  // ---------- yazı ----------
  function yazi(t, x, y, o) {
    ctx.save();
    ctx.font = o.font; ctx.textAlign = o.hiza || "left"; ctx.textBaseline = o.taban || "alphabetic";
    if (o.aralik) ctx.letterSpacing = o.aralik;
    ctx.globalAlpha = o.alfa ?? 1;
    if (o.hale) { ctx.lineJoin = "round"; ctx.strokeStyle = o.hale; ctx.lineWidth = o.haleGen || 6 * birim; ctx.strokeText(t, x, y); }
    if (o.golge) { ctx.shadowColor = o.golge; ctx.shadowBlur = o.golgeBlur || 12; }
    ctx.fillStyle = o.renk; ctx.fillText(t, x, y);
    ctx.restore();
  }
  function genislik(t, font, aralik) { ctx.save(); ctx.font = font; if (aralik) ctx.letterSpacing = aralik; const w = ctx.measureText(t).width; ctx.restore(); return w; }
  // nokta etiketi: güvenli alan içinde kalsın, sağa sığmazsa sola
  // nokta etiketi: güvenli alan içinde, önceki etiketlerle çakışmadan (sağ, sol, üst, alt denenir)
  let yerlesik = [];
  function etiketYeri(x, y, w, h, pay) {
    const aday = [[x + pay, y, false], [x - pay - w, y, true], [x + pay * 0.6, y - h * 0.9, false], [x + pay * 0.6, y + h * 0.9, false], [x - pay * 0.6 - w, y - h * 0.9, true], [x - pay * 0.6 - w, y + h * 0.9, true]];
    let en = null;
    for (const [ax, ay, sol] of aday) {
      const tx = Math.max(G.x0, Math.min(G.x1 - w, ax)), ty = Math.max(G.y0 + h, Math.min(G.y1, ay));
      const r = [tx - 3, ty - h, tx + w + 3, ty + h * 0.25];
      const cak = yerlesik.reduce((a, q) => a + Math.max(0, Math.min(r[2], q[2]) - Math.max(r[0], q[0])) * Math.max(0, Math.min(r[3], q[3]) - Math.max(r[1], q[1])), 0);
      if (!en || cak < en[3]) en = [tx, ty, sol, cak, r];
      if (cak === 0) break;
    }
    yerlesik.push(en[4]);
    return [en[0], en[1], en[2]];
  }
  const sayi = (n) => Math.round(n).toLocaleString(S.dil === "de" ? "de-DE" : "tr-TR");
  const KM = S.km || 0;

  // ortak zaman çizelgesi (u = 0..1)
  const T = { giris: [0, 0.24], kamera: [0.16, 0.5], rota: [0.44, 0.74], nokta: [0.62, 0.88], baslik: [0.05, 0.2] };
  function kamera(u) {
    const e = eio(ara(u, ...T.kamera));
    const a = ST.dunya, b = ST.bolge;
    const k = Math.exp(lerp(Math.log(a.k), Math.log(b.k), e));
    let lon0 = a.lon; if (ST.giriDonus) lon0 = a.lon + ST.giriDonus * (1 - eo(ara(u, 0, T.kamera[0] + 0.1)));
    return { lon: lerp(lon0, b.lon, e), lat: lerp(a.lat, b.lat, e), k, dx: lerp(a.dx, b.dx, e), dy: lerp(a.dy, b.dy, e) };
  }

  // başlık bloğu (her stil kendi yazı tipleri ve renkleriyle)
  function baslikBlok(u, o) {
    const g = eo(ara(u, ...T.baslik)); if (g <= 0) return;
    const x = G.x0, y0 = G.y0 + (o.ust || 0);
    const kay = (1 - g) * 18 * birim;
    if (S.ust) yazi(S.ust, x, y0 + 26 * birim + kay, { font: o.ustFont, renk: o.ustRenk || o.renk, alfa: g, aralik: o.ustAralik || "0.18em" });
    if (S.baslik) yazi(S.baslik, x - 4 * birim, y0 + 26 * birim + o.baslikBoy + kay * 1.4, { font: o.baslikFont, renk: o.renk, alfa: g, hale: o.hale, haleGen: o.haleGen });
    if (S.altbaslik) yazi(S.altbaslik, x, y0 + 26 * birim + o.baslikBoy + o.altBoy + kay * 1.8, { font: o.altFont, renk: o.altRenk || o.renk, alfa: g, hale: o.hale, haleGen: o.haleGen });
  }
  function sayac(u, o) { // mesafe sayacı: rota çizilirken artar
    if (!KM) return;
    const f = eio(ara(u, ...T.rota)), g = ara(u, T.rota[0] - 0.02, T.rota[0] + 0.04); if (g <= 0) return;
    const y = dikey ? G.y1 : G.y1 - 4 * birim;
    yazi((o.onek || "") + sayi(KM * f) + " km", o.x ?? G.x0, y, { font: o.font, renk: o.renk, alfa: g, aralik: o.aralik, hale: o.hale, hiza: o.hiza });
    if (o.not) yazi(o.not, o.x ?? G.x0, y - o.notBoy, { font: o.notFont, renk: o.notRenk || o.renk, alfa: g * 0.8, aralik: "0.14em", hale: o.hale, hiza: o.hiza });
  }
  // duraklar ve noktalar: (u) -> [{x,y,ad,g,tip,veri}]
  function yerler(u) {
    const out = []; const fr = eio(ara(u, ...T.rota));
    ROTA.forEach((r, i) => {
      if (!gorunur(r.lon, r.lat)) return;
      const esik = ROTA.length > 1 ? i / (ROTA.length - 1) : 0;
      const g = i === 0 ? ara(u, T.rota[0] - 0.08, T.rota[0]) : ara(fr, esik - 0.02, esik + 0.0001) * ara(u, T.rota[0], T.rota[0] + 0.01);
      const p = proj([r.lon, r.lat]); if (g > 0 && p) out.push({ x: p[0], y: p[1], ad: r.etiket, g, tip: i === 0 ? "kaynak" : "hedef", r });
    });
    NOKTALAR.forEach((n, i) => {
      if (!gorunur(n.lon, n.lat)) return;
      const a = T.nokta[0] + (i / Math.max(1, NOKTALAR.length)) * (T.nokta[1] - T.nokta[0]) * 0.7;
      const g = ara(u, a, a + 0.06); const p = proj([n.lon, n.lat]);
      if (g > 0 && p) out.push({ x: p[0], y: p[1], ad: n.etiket, g, tip: "nokta", r: n });
    });
    return out;
  }

  // =====================================================================================
  // STİLLER
  // =====================================================================================
  const STILLER = {};

  // 1) Editoryal atlas: açık kâğıt, Equal Earth, ince tel ağ, terrakota vurgu, serif tipografi
  STILLER.atlas = {
    projeksiyon: "equalEarth", dunya: { lon: 12, lat: 4, k: 1, dx: 0, dy: H * 0.03 }, bolgeDolgu: [0.5, 0.62], bolgeKaydir: 0.1, kavis: 0.16, enFazlaZoom: 9, dunyaGenislik: 0.92,
    ciz(u) {
      const P = { kagit: "#F3EFE6", kara: "#DCD3C1", sinir: "#F3EFE6", kiyi: "#9A8C74", ag: "rgba(70,55,35,0.10)", vurgu: "#C4583A", murekkep: "#1E1B18", ikincil: "#7A6B55" };
      arkaplan(P.kagit, "#E7E1D4", "rgba(70,55,35,0.35)");
      const gK = eo(ara(u, 0.05, 0.22));
      const dokulu = dokuluKure({ ort: 0.86, yay: 0.2, atm: 0.22, atmRenk: [0.95, 0.93, 0.88], isik: [-0.5, 0.65, 0.6], alfa: lerp(0.35, 1, gK) });
      const gA = eio(ara(u, 0, 0.14));
      ctx.strokeStyle = P.ag; ctx.lineWidth = 0.7; izle(ctx, kismi(cizgiler(AG), gA, 0.6)); ctx.stroke();
      ctx.strokeStyle = "rgba(70,55,35,0.25)"; ctx.lineWidth = 0.9; izle(ctx, kismi(cizgiler(KURE), gA, 0.6)); ctx.stroke();
      ctx.save(); ctx.globalAlpha = gK; if (!dokulu) { izle(ctx, cizgiler(KARA)); ctx.fillStyle = P.kara; ctx.fill(); }
      ctx.strokeStyle = dokulu ? "rgba(255,252,244,0.85)" : P.sinir; ctx.lineWidth = dokulu ? 0.9 : 0.8; izle(ctx, cizgiler(SINIR)); ctx.stroke(); ctx.restore();
      ctx.strokeStyle = dokulu ? "rgba(110,92,66,0.55)" : P.kiyi; ctx.lineWidth = 0.7; izle(ctx, kismi(cizgiler(KIYI), eio(ara(u, 0.02, 0.2)))); ctx.stroke();
      VURGU.forEach((v, i) => { const g = eo(ara(u, 0.3 + i * 0.05, 0.42 + i * 0.05)); if (g <= 0) return; ctx.save(); ctx.globalAlpha = g; izle(ctx, cizgiler(v.f)); ctx.fillStyle = i ? hex(P.vurgu, 0.5) : hex(P.vurgu, dokulu ? 0.82 : 1); ctx.fill(); ctx.strokeStyle = P.kagit; ctx.lineWidth = 1; ctx.stroke(); ctx.restore(); });
      VURGU.forEach((v, i) => ulkeAdi(v, eo(ara(u, 0.4 + i * 0.05, 0.5 + i * 0.05)), { font: `600 ${(i ? 15 : 19) * birim}px "IBM Plex Mono"`, renk: i ? P.murekkep : "#FFF8EE", aralik: "0.4em", dy: 22 * birim, ust: i > 0, hale: i ? "rgba(243,239,230,0.85)" : null, haleGen: 5 * birim }));
      // rota: önce noktalı kılavuz, sonra kesintisiz mürekkep
      const r = rotaEkran(), f = eio(ara(u, ...T.rota));
      if (f > 0) {
        ctx.save(); ctx.setLineDash([2 * birim, 6 * birim]); ctx.strokeStyle = hex(P.murekkep, 0.35); ctx.lineWidth = 1.4 * birim; izle(ctx, [r.map((p) => [p.x, p.y])]); ctx.globalAlpha = ara(u, T.rota[0], T.rota[0] + 0.05); ctx.stroke(); ctx.restore();
        ctx.strokeStyle = P.murekkep; ctx.lineWidth = 2.6 * birim; ctx.lineCap = "round"; izle(ctx, [rotaKismi(r, f)]); ctx.stroke();
      }
      for (const y of yerler(u)) {
        const R = (y.tip === "nokta" ? 4 : 6.5) * birim * eo(y.g);
        if (y.tip !== "nokta") { const nab = (u * 6) % 1; ctx.strokeStyle = hex(P.vurgu, (1 - nab) * 0.6 * y.g); ctx.lineWidth = 1.5 * birim; ctx.beginPath(); ctx.arc(y.x, y.y, R + nab * 26 * birim, 0, 7); ctx.stroke(); }
        ctx.fillStyle = y.tip === "nokta" ? P.murekkep : P.kagit; ctx.strokeStyle = P.murekkep; ctx.lineWidth = 2 * birim; ctx.beginPath(); ctx.arc(y.x, y.y, R, 0, 7); ctx.fill(); ctx.stroke();
        const font = y.tip === "nokta" ? `500 ${17 * birim}px "IBM Plex Mono"` : `600 ${30 * birim}px Fraunces`;
        const ad = y.tip === "nokta" ? y.ad.toLocaleUpperCase("tr") : y.ad; const w = genislik(ad, font, y.tip === "nokta" ? "0.12em" : 0);
        const [tx, ty] = etiketYeri(y.x, y.y + 10 * birim, w, 30 * birim, 14 * birim);
        yazi(ad, tx, ty, { font, renk: P.murekkep, alfa: eo(y.g), aralik: y.tip === "nokta" ? "0.12em" : 0, hale: P.kagit, haleGen: 7 * birim });
      }
      baslikBlok(u, { ustFont: `500 ${18 * birim}px "IBM Plex Mono"`, ustRenk: P.vurgu, baslikFont: `400 ${120 * birim}px "Instrument Serif"`, baslikBoy: 112 * birim, altFont: `italic 400 ${44 * birim}px "Instrument Serif"`, altBoy: 52 * birim, renk: P.murekkep });
      sayac(u, { font: `500 ${30 * birim}px "IBM Plex Mono"`, renk: P.murekkep, not: S.sayacNot, notFont: `500 ${15 * birim}px "IBM Plex Mono"`, notBoy: 40 * birim, notRenk: P.ikincil, hale: P.kagit });
      grenUygula("atlas", 22, 0.18);
    },
  };

  // 2) Gece küresi: dönen 3D küre, atmosfer ışıması, amber vurgu, yükselen rota yayı
  STILLER.kure = {
    projeksiyon: "ortho", dunya: { lon: -40, lat: 22, k: 1.0, dx: 0, dy: 0 }, bolgeDolgu: [0.34, 0.4], bolgeKaydir: 0.08, kavis: 0, enFazlaZoom: 6, giriDonus: -70, dunyaGenislik: 1,
    yildiz: null,
    ciz(u) {
      const P = { uzay: "#05070F", okyanus1: "#0F2A4A", okyanus2: "#06142A", kara: "#1B3B5C", kiyi: "#79B4E8", sinir: "rgba(140,190,240,0.30)", vurgu: "#F2A541", yay: "#FFD08A", yazi: "#EAF2FF" };
      ctx.fillStyle = P.uzay; ctx.fillRect(0, 0, W, H);
      if (!this.yildiz) { const r = rng(3); this.yildiz = Array.from({ length: 420 }, () => [r() * W, r() * H, r() * r() * 1.4 + 0.3, r()]); }
      for (const [x, y, s, a] of this.yildiz) { ctx.fillStyle = `rgba(220,230,255,${0.15 + a * 0.5})`; ctx.fillRect(x, y, s, s); }
      const c = proj.translate(), R = proj.scale();
      const gG = eo(ara(u, 0, 0.12));
      // atmosfer
      parilti((g) => { g.strokeStyle = "rgba(90,160,255,0.55)"; g.lineWidth = R * 0.02; g.beginPath(); g.arc(c[0], c[1], R * 1.01, 0, 7); g.stroke(); }, R * 0.06, 0.45 * gG);
      ctx.save(); ctx.globalAlpha = gG;
      const dokulu = dokuluKure({ ort: 0.22, yay: 1.05, parla: 0.28, atm: 0.6, atmRenk: [0.32, 0.58, 1.0], isik: [-0.55, 0.55, 0.63], alfa: gG });
      if (!dokulu) {
        const og = ctx.createRadialGradient(c[0] - R * 0.35, c[1] - R * 0.4, R * 0.05, c[0], c[1], R);
        og.addColorStop(0, P.okyanus1); og.addColorStop(1, P.okyanus2);
        ctx.fillStyle = og; ctx.beginPath(); ctx.arc(c[0], c[1], R, 0, 7); ctx.fill();
        izle(ctx, cizgiler(KARA)); ctx.fillStyle = P.kara; ctx.fill();
      }
      ctx.strokeStyle = "rgba(120,170,255,0.07)"; ctx.lineWidth = 0.8; izle(ctx, cizgiler(AG)); ctx.stroke();
      ctx.strokeStyle = P.sinir; ctx.lineWidth = 0.6; izle(ctx, cizgiler(SINIR)); ctx.stroke();
      ctx.strokeStyle = P.kiyi; ctx.lineWidth = 0.8; izle(ctx, cizgiler(KIYI)); ctx.globalAlpha = 0.55 * gG; ctx.stroke();
      ctx.globalAlpha = 1;
      VURGU.forEach((v, i) => { const g = eo(ara(u, 0.32 + i * 0.05, 0.44 + i * 0.05)); if (g <= 0) return; const l = cizgiler(v.f); ctx.save(); ctx.globalAlpha = g * (i ? 0.6 : 0.9); izle(ctx, l); ctx.fillStyle = P.vurgu; ctx.fill(); ctx.restore(); parilti((gg) => { izle(gg, l); gg.strokeStyle = P.vurgu; gg.lineWidth = 2; gg.stroke(); }, 6, 0.6 * g); });
      VURGU.forEach((v, i) => ulkeAdi(v, eo(ara(u, 0.42 + i * 0.05, 0.52 + i * 0.05)), { font: `600 ${(i ? 15 : 19) * birim}px "Space Grotesk"`, renk: i ? "#FFE2B0" : "#1A1206", aralik: "0.42em", dy: 22 * birim, ust: i > 0, hale: i ? "rgba(5,7,15,0.7)" : null, haleGen: 6 * birim }));
      // kenar kararması + sağ üst ışık
      if (!dokulu) { const kg = ctx.createRadialGradient(c[0] - R * 0.3, c[1] - R * 0.35, R * 0.2, c[0], c[1], R * 1.02);
      kg.addColorStop(0, "rgba(255,255,255,0.06)"); kg.addColorStop(0.6, "rgba(0,0,0,0)"); kg.addColorStop(1, "rgba(0,0,10,0.55)");
      ctx.fillStyle = kg; ctx.beginPath(); ctx.arc(c[0], c[1], R, 0, 7); ctx.fill(); }
      ctx.restore();
      const r = rotaEkran(), f = eio(ara(u, ...T.rota));
      if (f > 0) {
        const k = rotaKismi(r, f);
        parilti((g) => { g.strokeStyle = P.yay; g.lineWidth = 3 * birim; g.lineCap = "round"; izle(g, [k]); g.stroke(); const h = k[k.length - 1]; if (h && f < 1) { g.fillStyle = "#fff"; g.beginPath(); g.arc(h[0], h[1], 5 * birim, 0, 7); g.fill(); } }, 8 * birim, 1);
      }
      for (const y of yerler(u)) {
        const R2 = (y.tip === "nokta" ? 3.5 : 6) * birim * eo(y.g);
        parilti((g) => { g.fillStyle = y.tip === "nokta" ? "#CFE3FF" : P.yay; g.beginPath(); g.arc(y.x, y.y, R2, 0, 7); g.fill(); }, 6 * birim, y.g);
        const font = y.tip === "nokta" ? `500 ${18 * birim}px "Space Grotesk"` : `600 ${28 * birim}px "Space Grotesk"`;
        const ad = y.ad.toLocaleUpperCase(S.dil === "de" ? "de" : "tr"); const w = genislik(ad, font, "0.08em");
        const [tx, ty] = etiketYeri(y.x, y.y + 9 * birim, w, 28 * birim, 14 * birim);
        yazi(ad, tx, ty, { font, renk: P.yazi, alfa: eo(y.g), aralik: "0.08em", golge: "rgba(0,0,0,0.9)", golgeBlur: 8 });
      }
      baslikBlok(u, { ustFont: `500 ${18 * birim}px "IBM Plex Mono"`, ustRenk: P.vurgu, baslikFont: `700 ${104 * birim}px "Space Grotesk"`, baslikBoy: 100 * birim, altFont: `400 ${38 * birim}px "Space Grotesk"`, altBoy: 52 * birim, renk: P.yazi, altRenk: "rgba(234,242,255,0.75)" });
      sayac(u, { font: `500 ${30 * birim}px "IBM Plex Mono"`, renk: P.yazi, not: S.sayacNot, notFont: `500 ${15 * birim}px "IBM Plex Mono"`, notBoy: 40 * birim, notRenk: P.vurgu });
      grenUygula("kure", 18, 0.12);
    },
  };

  // 3) Nokta matrisi: kara noktalardan, Türkiye'den yayılan dalga, sinyal turuncusu
  STILLER.nokta = {
    projeksiyon: "equalEarth", dunya: { lon: 12, lat: 4, k: 1, dx: 0, dy: H * 0.03 }, bolgeDolgu: [0.48, 0.6], bolgeKaydir: 0.1, kavis: 0.14, enFazlaZoom: 7, dunyaGenislik: 0.92,
    izgara: null,
    hazirla() {
      // eşdikdörtgen maske: kara + vurgu ülkeleri (kanal = sıra)
      const mw = 3600, mh = 1800, m = document.createElement("canvas"); m.width = mw; m.height = mh; const g = m.getContext("2d", { willReadFrequently: true });
      const p = d3.geoEquirectangular().scale(mw / (2 * Math.PI)).translate([mw / 2, mh / 2]); const pa = d3.geoPath(p, g);
      g.fillStyle = "#000"; g.fillRect(0, 0, mw, mh); g.fillStyle = "#fff"; g.beginPath(); pa(KARA); g.fill();
      VURGU.forEach((v, i) => { g.fillStyle = `rgb(255,${10 + i * 40},0)`; g.beginPath(); pa(v.f); g.fill(); });
      const im = g.getImageData(0, 0, mw, mh).data; const out = []; const adim = 0.72;
      const kay = ROTA.length ? [ROTA[0].lon, ROTA[0].lat] : [30, 40];
      for (let lat = -58; lat <= 82; lat += adim) {
        const dl = adim / Math.max(0.25, Math.cos((lat * Math.PI) / 180));
        for (let lon = -180 + (Math.round(lat / adim) % 2) * dl * 0.5; lon < 180; lon += dl) {
          const x = Math.floor(((lon + 180) / 360) * mw), y = Math.floor(((90 - lat) / 180) * mh), k = (y * mw + x) * 4;
          if (im[k + 2] < 128 && im[k] < 128) continue;
          const v = im[k] > 200 && im[k + 2] < 100 ? Math.round((im[k + 1] - 10) / 40) : -1;
          out.push({ lon, lat, v, d: d3.geoDistance([lon, lat], kay) });
        }
      }
      this.izgara = out;
    },
    ciz(u) {
      if (!this.izgara) this.hazirla();
      const P = { zemin: "#0C0C0E", nokta: "#3B3B42", vurgu: "#FF5A36", vurgu2: "#FFB199", yazi: "#F4F4F5", ikincil: "#8A8A93" };
      arkaplan("#131317", P.zemin, "rgba(255,255,255,0.08)");
      const s = proj.scale(), r0 = Math.max(1.1, Math.min(7.5 * birim, s * 0.0042));
      const dalga = ara(u, 0, 0.26) * 3.4, vurguG = ara(u, 0.3, 0.46);
      const gruplar = [[], [], []]; const merkez = proj.invert(proj.translate());
      for (const q of this.izgara) {
        const g = kel((dalga - q.d) * 3); if (g <= 0) continue;
        if (kuremi() && d3.geoDistance([q.lon, q.lat], merkez) > Math.PI / 2 - 0.02) continue;
        const p = proj([q.lon, q.lat]); if (!p || p[0] < -10 || p[0] > W + 10 || p[1] < -10 || p[1] > H + 10) continue;
        const sec = q.v >= 0 && vurguG > 0 ? (q.v === 0 ? 1 : 2) : 0;
        gruplar[sec].push([p[0], p[1], r0 * eo(g) * (sec ? lerp(1, 1.15, vurguG) : 1)]);
      }
      [[P.nokta, 1], [P.vurgu, vurguG], [P.vurgu2, vurguG]].forEach(([renk, a], i) => {
        if (i && !gruplar[i].length) return;
        if (i) { ctx.fillStyle = P.nokta; ctx.beginPath(); for (const [x, y, r] of gruplar[i]) { ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, 7); } ctx.fill(); }
        ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = renk; ctx.beginPath(); for (const [x, y, r] of gruplar[i]) { ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, 7); } ctx.fill(); ctx.restore();
      });
      // rota: noktalardan oluşan kesik çizgi
      const r = rotaEkran(), f = eio(ara(u, ...T.rota));
      if (f > 0) {
        const k = rotaKismi(r, f); let L = 0; const ad = Math.max(10 * birim, r0 * 3);
        ctx.fillStyle = P.yazi;
        for (let i = 1; i < k.length; i++) { const d = Math.hypot(k[i][0] - k[i - 1][0], k[i][1] - k[i - 1][1]); L += d; if (L >= ad) { L = 0; ctx.beginPath(); ctx.arc(k[i][0], k[i][1], Math.max(2.4 * birim, r0 * 0.75), 0, 7); ctx.fill(); } }
        const h = k[k.length - 1]; if (h && f < 1) parilti((g) => { g.fillStyle = P.vurgu; g.beginPath(); g.arc(h[0], h[1], 7 * birim, 0, 7); g.fill(); }, 8 * birim, 1);
      }
      for (const y of yerler(u)) {
        const R = (y.tip === "nokta" ? 4 : 7) * birim * eo(y.g);
        if (y.tip !== "nokta") for (let k = 0; k < 2; k++) { const nab = (u * 5 + k * 0.5) % 1; ctx.strokeStyle = hex(P.vurgu, (1 - nab) * 0.7 * y.g); ctx.lineWidth = 2 * birim; ctx.beginPath(); ctx.arc(y.x, y.y, R + nab * 34 * birim, 0, 7); ctx.stroke(); }
        ctx.fillStyle = y.tip === "nokta" ? P.yazi : P.vurgu; ctx.beginPath(); ctx.arc(y.x, y.y, R, 0, 7); ctx.fill();
        const font = y.tip === "nokta" ? `500 ${17 * birim}px "IBM Plex Mono"` : `600 ${30 * birim}px "Space Grotesk"`;
        const ad = y.ad.toLocaleUpperCase(S.dil === "de" ? "de" : "tr"); const w = genislik(ad, font, "0.1em");
        const [tx, ty] = etiketYeri(y.x, y.y + 10 * birim, w, 30 * birim, 16 * birim);
        yazi(ad, tx, ty, { font, renk: P.yazi, alfa: eo(y.g), aralik: "0.1em", hale: P.zemin, haleGen: 8 * birim });
      }
      baslikBlok(u, { ustFont: `500 ${18 * birim}px "IBM Plex Mono"`, ustRenk: P.vurgu, baslikFont: `700 ${110 * birim}px "Space Grotesk"`, baslikBoy: 104 * birim, altFont: `400 ${38 * birim}px "Space Grotesk"`, altBoy: 52 * birim, renk: P.yazi, altRenk: P.ikincil, hale: P.zemin, haleGen: 10 * birim });
      sayac(u, { font: `500 ${30 * birim}px "IBM Plex Mono"`, renk: P.yazi, not: S.sayacNot, notFont: `500 ${15 * birim}px "IBM Plex Mono"`, notBoy: 40 * birim, notRenk: P.vurgu, hale: P.zemin });
      grenUygula("nokta", 14, 0.1);
    },
  };

  // 4) Karakalem eskiz: kâğıt dokusu, titrek grafit kıyılar, tarama, el yazısı
  STILLER.karakalem = {
    projeksiyon: "naturalEarth", dunya: { lon: 12, lat: 4, k: 1, dx: 0, dy: H * 0.03 }, bolgeDolgu: [0.5, 0.6], bolgeKaydir: 0.1, kavis: 0.2, enFazlaZoom: 8, dunyaGenislik: 0.9,
    tarama(lines, aralik, aci, renk, kal, alfa, tohum, f = 1) {
      ctx.save(); izle(ctx, lines); ctx.clip();
      const r = rng(tohum); const ca = Math.cos(aci), sa = Math.sin(aci); const D = Math.hypot(W, H);
      ctx.strokeStyle = renk; ctx.lineWidth = kal; ctx.globalAlpha = alfa; ctx.beginPath();
      for (let o = -D; o < D; o += aralik * (0.8 + r() * 0.4)) {
        if (r() > f * 1.2) continue;
        const cx = W / 2 + -sa * o, cy = H / 2 + ca * o, j = (r() - 0.5) * 0.04;
        ctx.moveTo(cx - (ca + j) * D, cy - (sa - j) * D); ctx.lineTo(cx + (ca + j) * D, cy + (sa - j) * D);
      }
      ctx.stroke(); ctx.restore();
    },
    ciz(u, kare) {
      const P = { kagit: "#F2EEE6", grafit: "#2B2B2B", grafit2: "#5C5C5C", kirmizi: "#B5442E" };
      arkaplan(P.kagit, P.kagit, null); if (kuremi()) { ctx.strokeStyle = P.grafit; ctx.globalAlpha = 0.6; ctx.lineWidth = 1.4 * birim; izle(ctx, titret(kismi(cizgiler(KURE), eio(ara(u, 0, 0.12)), 0), 1.2 * birim, Math.floor(kare / 3))); ctx.stroke(); ctx.globalAlpha = 1; }
      const tohum = Math.floor(kare / 3); // "ikişerli" titreme
      const kara = cizgiler(KARA), kiyi = cizgiler(KIYI);
      const fT = ara(u, 0.12, 0.3);
      if (fT > 0) { ctx.save(); ctx.globalAlpha = 0.5 * fT; izle(ctx, kara); ctx.fillStyle = "#E6E0D4"; ctx.fill(); ctx.restore(); this.tarama(kara, 6 * birim, -0.78, P.grafit2, 0.9 * birim, 0.42, 11 + (tohum % 4), fT); }
      const fK = eio(ara(u, 0, 0.2));
      ctx.lineJoin = "round"; ctx.lineCap = "round";
      ctx.strokeStyle = P.grafit; ctx.globalAlpha = 0.75; ctx.lineWidth = 1.2 * birim; izle(ctx, titret(kismi(kiyi, fK), 0.7 * birim, tohum)); ctx.stroke();
      ctx.globalAlpha = 0.35; ctx.lineWidth = 0.8 * birim; izle(ctx, titret(kismi(kiyi, fK), 1.4 * birim, tohum + 99)); ctx.stroke();
      ctx.globalAlpha = 0.3 * ara(u, 0.15, 0.3); ctx.setLineDash([3 * birim, 4 * birim]); ctx.lineWidth = 0.8 * birim; izle(ctx, cizgiler(SINIR)); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
      VURGU.forEach((v, i) => { const g = ara(u, 0.3 + i * 0.06, 0.48 + i * 0.06); if (g <= 0) return; const l = cizgiler(v.f); this.tarama(l, (i ? 6 : 4) * birim, i ? 0.6 : -0.6, P.kirmizi, 1.1 * birim, 0.75, 21 + i + (tohum % 3), g); ctx.strokeStyle = P.kirmizi; ctx.globalAlpha = 0.8 * g; ctx.lineWidth = 1.4 * birim; izle(ctx, titret(l, 0.8 * birim, tohum + i)); ctx.stroke(); ctx.globalAlpha = 1; });
      const r = rotaEkran(), f = eio(ara(u, ...T.rota));
      if (f > 0) {
        const k = rotaKismi(r, f);
        ctx.strokeStyle = P.grafit; ctx.lineWidth = 2.4 * birim; izle(ctx, titret([k], 1.1 * birim, tohum + 5)); ctx.stroke();
        ctx.globalAlpha = 0.5; ctx.lineWidth = 1.2 * birim; izle(ctx, titret([k], 2.2 * birim, tohum + 6)); ctx.stroke(); ctx.globalAlpha = 1;
        if (k.length > 6) { const a = k[k.length - 1], b = k[k.length - 6]; const ang = Math.atan2(a[1] - b[1], a[0] - b[0]); const L = 18 * birim; ctx.lineWidth = 2.4 * birim; ctx.beginPath(); ctx.moveTo(a[0] - L * Math.cos(ang - 0.45), a[1] - L * Math.sin(ang - 0.45)); ctx.lineTo(a[0], a[1]); ctx.lineTo(a[0] - L * Math.cos(ang + 0.45), a[1] - L * Math.sin(ang + 0.45)); ctx.stroke(); }
      }
      for (const y of yerler(u)) {
        const R = (y.tip === "nokta" ? 4 : 7) * birim; const g = eo(y.g);
        ctx.strokeStyle = y.tip === "kaynak" || y.tip === "hedef" ? P.kirmizi : P.grafit; ctx.lineWidth = 1.8 * birim; ctx.globalAlpha = g;
        ctx.beginPath(); for (let a = 0; a <= 6.6 * g; a += 0.2) { const rr = R + Math.sin(a * 3 + tohum) * 0.8; ctx.lineTo(y.x + rr * Math.cos(a), y.y + rr * Math.sin(a)); } ctx.stroke(); ctx.globalAlpha = 1;
        const font = `${y.tip === "nokta" ? 600 : 700} ${(y.tip === "nokta" ? 30 : 44) * birim}px Caveat`;
        const w = genislik(y.ad, font); const [tx, ty] = etiketYeri(y.x, y.y + 12 * birim, w, 40 * birim, 14 * birim);
        yazi(y.ad, tx, ty, { font, renk: P.grafit, alfa: g, hale: P.kagit, haleGen: 6 * birim });
      }
      baslikBlok(u, { ustFont: `600 ${30 * birim}px Caveat`, ustRenk: P.kirmizi, ustAralik: "0.02em", baslikFont: `700 ${130 * birim}px Caveat`, baslikBoy: 110 * birim, altFont: `500 ${48 * birim}px Caveat`, altBoy: 54 * birim, renk: P.grafit, hale: P.kagit, haleGen: 10 * birim });
      sayac(u, { font: `700 ${44 * birim}px Caveat`, renk: P.grafit, onek: "≈ ", not: S.sayacNot, notFont: `600 ${26 * birim}px Caveat`, notBoy: 44 * birim, notRenk: P.kirmizi, hale: P.kagit });
      grenUygula("karakalem", 40, 0.32, "multiply");
      grenUygula("karakalem2", 26, 0.14);
    },
  };

  // 5) Eski harita: parşömen, kıyı su çizgileri, rüzgâr gülü ve kerte çizgileri, mürekkep rota
  STILLER.parsomen = {
    projeksiyon: "equirect", dunya: { lon: 12, lat: 8, k: 1.04, dx: 0, dy: H * 0.03 }, bolgeDolgu: [0.5, 0.6], bolgeKaydir: 0.1, kavis: 0.18, enFazlaZoom: 8, dunyaGenislik: 0.88,
    lekeler: null,
    ciz(u, kare) {
      const P = { parsomen: "#E9DBB8", kara: "#DCC596", murekkep: "#4A3520", su: "#6B5232", kirmizi: "#8E2A1E", yesil: "#4E6B3A" };
      ctx.fillStyle = P.parsomen; ctx.fillRect(0, 0, W, H);
      if (!this.lekeler) { const r = rng(9); this.lekeler = Array.from({ length: 14 }, () => [r() * W, r() * H, (0.05 + r() * 0.14) * W, r()]); }
      for (const [x, y, rr, a] of this.lekeler) { const g = ctx.createRadialGradient(x, y, 0, x, y, rr); g.addColorStop(0, `rgba(150,110,60,${0.05 + a * 0.06})`); g.addColorStop(1, "rgba(150,110,60,0)"); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
      const gG = eo(ara(u, 0, 0.18));
      // kerte çizgileri (Atlantik'te bir rüzgâr gülünden)
      const gul = gorunur(-32, 32) ? proj([-32, 32]) : null;
      if (kuremi()) { ctx.save(); ctx.strokeStyle = P.murekkep; ctx.lineWidth = 1.6 * birim; izle(ctx, cizgiler(KURE)); ctx.globalAlpha = gG; ctx.stroke(); ctx.restore(); }
      if (gul) {
        ctx.save(); ctx.globalAlpha = 0.35 * gG; ctx.lineWidth = 0.7 * birim; const D = Math.hypot(W, H) * 2;
        for (let i = 0; i < 32; i++) { const a = (i / 32) * Math.PI * 2; ctx.strokeStyle = i % 4 === 0 ? P.murekkep : i % 2 ? P.yesil : P.kirmizi; ctx.beginPath(); ctx.moveTo(gul[0], gul[1]); ctx.lineTo(gul[0] + D * Math.cos(a), gul[1] + D * Math.sin(a)); ctx.stroke(); }
        ctx.restore();
      }
      const kara = cizgiler(KARA);
      // su çizgileri: kıyıdan dışa eşmerkezli halkalar
      ctx.save(); ctx.lineJoin = "round"; ctx.globalAlpha = gG;
      const n = 6, ad = 5 * birim;
      for (let i = n; i >= 1; i--) { izle(ctx, kara); ctx.strokeStyle = hex(P.su, 0.22 * (1 - i / (n + 1)) + 0.05); ctx.lineWidth = i * ad * 2; ctx.stroke(); izle(ctx, kara); ctx.strokeStyle = P.parsomen; ctx.lineWidth = i * ad * 2 - 1.6 * birim; ctx.stroke(); }
      ctx.restore();
      ctx.save(); ctx.globalAlpha = gG; izle(ctx, kara); ctx.fillStyle = P.kara; ctx.fill(); ctx.restore();
      ctx.strokeStyle = P.murekkep; ctx.lineWidth = 1.3 * birim; izle(ctx, titret(kismi(cizgiler(KIYI), eio(ara(u, 0, 0.2))), 0.5 * birim, 3)); ctx.stroke();
      ctx.save(); ctx.globalAlpha = 0.55 * ara(u, 0.12, 0.26); ctx.setLineDash([1.5 * birim, 3.5 * birim]); ctx.strokeStyle = P.murekkep; ctx.lineWidth = 1.1 * birim; izle(ctx, cizgiler(SINIR)); ctx.stroke(); ctx.restore();
      VURGU.forEach((v, i) => { const g = eo(ara(u, 0.3 + i * 0.05, 0.44 + i * 0.05)); if (g <= 0) return; ctx.save(); ctx.globalAlpha = g * (i ? 0.35 : 0.5); izle(ctx, cizgiler(v.f)); ctx.fillStyle = P.kirmizi; ctx.fill(); ctx.restore(); });
      // rüzgâr gülü
      if (gul) {
        const R = 70 * birim * Math.min(1.6, Math.sqrt(proj.scale() / 300)); ctx.save(); ctx.translate(gul[0], gul[1]); ctx.globalAlpha = gG; ctx.rotate(-0.15 * (1 - gG));
        ctx.strokeStyle = P.murekkep; ctx.lineWidth = 1.2 * birim; ctx.beginPath(); ctx.arc(0, 0, R * 0.62, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.arc(0, 0, R * 0.56, 0, 7); ctx.stroke();
        for (let i = 0; i < 16; i++) { const a = (i / 16) * Math.PI * 2 - Math.PI / 2, L = i % 4 === 0 ? R : i % 2 ? R * 0.45 : R * 0.7, w = i % 4 === 0 ? 0.13 : 0.1;
          ctx.fillStyle = i % 2 ? P.murekkep : i % 4 === 0 ? P.kirmizi : P.yesil; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(L * w * Math.cos(a + 1.57), L * w * Math.sin(a + 1.57)); ctx.lineTo(L * Math.cos(a), L * Math.sin(a)); ctx.closePath(); ctx.fill(); ctx.stroke(); }
        yazi("N", 0, -R - 8 * birim, { font: `700 ${26 * birim}px Cinzel`, renk: P.murekkep, hiza: "center" });
        ctx.restore();
      }
      const r = rotaEkran(), f = eio(ara(u, ...T.rota));
      if (f > 0) { const k = rotaKismi(r, f); ctx.save(); ctx.setLineDash([10 * birim, 6 * birim]); ctx.strokeStyle = P.kirmizi; ctx.lineWidth = 3 * birim; ctx.lineCap = "round"; izle(ctx, titret([k], 0.6 * birim, 8)); ctx.stroke(); ctx.restore(); }
      for (const y of yerler(u)) {
        const g = eo(y.g), R = (y.tip === "nokta" ? 4 : 7) * birim * g;
        ctx.fillStyle = y.tip === "nokta" ? P.murekkep : P.kirmizi; ctx.strokeStyle = P.murekkep; ctx.lineWidth = 1.5 * birim;
        if (y.tip === "nokta") { ctx.beginPath(); ctx.arc(y.x, y.y, R, 0, 7); ctx.fill(); }
        else { ctx.beginPath(); for (let k = 0; k < 10; k++) { const rr = k % 2 ? R * 0.45 : R * 1.5, a = (k / 10) * Math.PI * 2 - Math.PI / 2; ctx.lineTo(y.x + rr * Math.cos(a), y.y + rr * Math.sin(a)); } ctx.closePath(); ctx.fill(); ctx.stroke(); }
        const font = y.tip === "nokta" ? `italic 400 ${28 * birim}px "EB Garamond"` : `600 ${32 * birim}px Cinzel`;
        const w = genislik(y.ad, font); const [tx, ty] = etiketYeri(y.x, y.y + 11 * birim, w, 32 * birim, 16 * birim);
        yazi(y.ad, tx, ty, { font, renk: P.murekkep, alfa: g, hale: hex(P.parsomen, 0.85), haleGen: 6 * birim });
      }
      // çerçeve
      ctx.save(); ctx.strokeStyle = P.murekkep; ctx.globalAlpha = 0.8 * gG; const m = Math.min(W, H) * 0.03;
      ctx.lineWidth = 2.2 * birim; ctx.strokeRect(m, m, W - 2 * m, H - 2 * m); ctx.lineWidth = 0.8 * birim; ctx.strokeRect(m + 7 * birim, m + 7 * birim, W - 2 * m - 14 * birim, H - 2 * m - 14 * birim); ctx.restore();
      baslikBlok(u, { ust: 10 * birim, ustFont: `italic 400 ${28 * birim}px "EB Garamond"`, ustRenk: P.kirmizi, ustAralik: "0.04em", baslikFont: `700 ${104 * birim}px Cinzel`, baslikBoy: 100 * birim, altFont: `italic 400 ${44 * birim}px "EB Garamond"`, altBoy: 52 * birim, renk: P.murekkep, hale: hex(P.parsomen, 0.9), haleGen: 10 * birim });
      sayac(u, { font: `600 ${30 * birim}px Cinzel`, renk: P.murekkep, not: S.sayacNot, notFont: `italic 400 ${24 * birim}px "EB Garamond"`, notBoy: 38 * birim, notRenk: P.kirmizi, hale: hex(P.parsomen, 0.9) });
      // kenar yanığı
      const v = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.35, W / 2, H / 2, Math.hypot(W, H) * 0.6); v.addColorStop(0, "rgba(90,55,20,0)"); v.addColorStop(1, "rgba(90,55,20,0.38)"); ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
      grenUygula("parsomen", 44, 0.3, "multiply"); grenUygula("parsomen2", 24, 0.22);
    },
  };

  // 6) Neon ağ: koyu zemin, ışıyan sınırlar, dünyaya açılan uçuş yayları, sıcak ana rota
  STILLER.neon = {
    projeksiyon: "naturalEarth", dunya: { lon: 18, lat: 8, k: 1, dx: 0, dy: H * 0.03 }, bolgeDolgu: [0.5, 0.6], bolgeKaydir: 0.1, kavis: 0.2, enFazlaZoom: 8, dunyaGenislik: 0.92,
    ciz(u) {
      const P = { zemin: "#04050A", kara: "#0A1222", cizgi: "#2EC8FF", ana: "#FF2E88", yazi: "#F2F6FF", ikincil: "#7FA7C9" };
      arkaplan("#070B16", P.zemin, "rgba(46,200,255,0.35)");
      const gG = eo(ara(u, 0, 0.18));
      izle(ctx, cizgiler(KARA)); ctx.fillStyle = P.kara; ctx.globalAlpha = gG; ctx.fill(); ctx.globalAlpha = 1;
      const kiyi = kismi(cizgiler(KIYI), eio(ara(u, 0, 0.2))), sinir = cizgiler(SINIR);
      parilti((g) => { g.strokeStyle = hex(P.cizgi, 0.55); g.lineWidth = 1 * birim; izle(g, kiyi); g.stroke(); g.strokeStyle = hex(P.cizgi, 0.16 * gG); g.lineWidth = 0.6 * birim; izle(g, sinir); g.stroke(); }, 4 * birim, 1);
      // uçuş yayları: kaynaktan dünyaya (giriş bölümünde), sonra söner
      const kay = ROTA[0]; const yG = ara(u, 0.04, 0.3) * (1 - ara(u, 0.42, 0.56));
      if (kay && yG > 0 && S.yaylar) {
        parilti((g) => {
          S.yaylar.forEach((h, i) => {
            const ip = d3.geoInterpolate([kay.lon, kay.lat], [h[0], h[1]]); const t0 = (i * 0.137) % 0.5, f = kel((ara(u, 0.04, 0.34) - t0) / 0.5); if (f <= 0) return;
            if (!gorunur(kay.lon, kay.lat)) return; const a = proj([kay.lon, kay.lat]), b = proj(h); if (!a || !b) return; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); const nx = (a[1] - b[1]) / L, ny = (b[0] - a[0]) / L, yon = ny > 0 ? -1 : 1;
            const pts = []; for (let j = 0; j <= 60 * f; j++) { const s = j / 60, q = ip(s); if (!gorunur(q[0], q[1])) continue; const p = proj(q); if (!p) continue; const hh = Math.sin(Math.PI * s) * L * 0.22; pts.push([p[0] + yon * nx * hh, p[1] + yon * ny * hh]); }
            if (pts.length < 2) return; g.globalAlpha = yG; g.strokeStyle = i % 3 ? hex(P.cizgi, 0.8) : hex(P.ana, 0.8); g.lineWidth = 1.4 * birim; izle(g, [pts]); g.stroke();
            const e = pts[pts.length - 1]; g.fillStyle = "#fff"; g.beginPath(); g.arc(e[0], e[1], 2.4 * birim, 0, 7); g.fill(); g.globalAlpha = 1;
          });
        }, 6 * birim, 1);
      }
      VURGU.forEach((v, i) => { const g = eo(ara(u, 0.32 + i * 0.05, 0.46 + i * 0.05)); if (g <= 0) return; const l = cizgiler(v.f); ctx.save(); ctx.globalAlpha = g * 0.22; izle(ctx, l); ctx.fillStyle = P.ana; ctx.fill(); ctx.restore(); parilti((gg) => { izle(gg, l); gg.strokeStyle = P.ana; gg.lineWidth = 1.6 * birim; gg.stroke(); }, 7 * birim, g); });
      const r = rotaEkran(), f = eio(ara(u, ...T.rota));
      if (f > 0) { const k = rotaKismi(r, f); parilti((g) => { g.lineCap = "round"; g.strokeStyle = P.ana; g.lineWidth = 4 * birim; izle(g, [k]); g.stroke(); g.strokeStyle = "#FFE3F0"; g.lineWidth = 1.4 * birim; g.stroke(); const h = k[k.length - 1]; if (h && f < 1) { g.fillStyle = "#fff"; g.beginPath(); g.arc(h[0], h[1], 5 * birim, 0, 7); g.fill(); } }, 10 * birim, 1); }
      for (const y of yerler(u)) {
        const R = (y.tip === "nokta" ? 3.5 : 6) * birim * eo(y.g), renk = y.tip === "nokta" ? P.cizgi : P.ana;
        parilti((g) => { g.fillStyle = renk; g.beginPath(); g.arc(y.x, y.y, R, 0, 7); g.fill(); if (y.tip !== "nokta") { const nab = (u * 5) % 1; g.strokeStyle = hex(renk, 1 - nab); g.lineWidth = 2 * birim; g.beginPath(); g.arc(y.x, y.y, R + nab * 30 * birim, 0, 7); g.stroke(); } }, 6 * birim, y.g);
        const font = y.tip === "nokta" ? `500 ${18 * birim}px "Space Grotesk"` : `600 ${28 * birim}px "Space Grotesk"`;
        const ad = y.ad.toLocaleUpperCase(S.dil === "de" ? "de" : "tr"); const w = genislik(ad, font, "0.12em");
        const [tx, ty] = etiketYeri(y.x, y.y + 9 * birim, w, 28 * birim, 14 * birim);
        yazi(ad, tx, ty, { font, renk: P.yazi, alfa: eo(y.g), aralik: "0.12em", golge: hex(renk, 0.9), golgeBlur: 14 });
      }
      baslikBlok(u, { ustFont: `500 ${18 * birim}px "IBM Plex Mono"`, ustRenk: P.ana, baslikFont: `700 ${110 * birim}px "Space Grotesk"`, baslikBoy: 104 * birim, altFont: `400 ${38 * birim}px "Space Grotesk"`, altBoy: 52 * birim, renk: P.yazi, altRenk: P.ikincil, hale: hex(P.zemin, 0.8), haleGen: 10 * birim });
      sayac(u, { font: `500 ${30 * birim}px "IBM Plex Mono"`, renk: P.yazi, not: S.sayacNot, notFont: `500 ${15 * birim}px "IBM Plex Mono"`, notBoy: 40 * birim, notRenk: P.ana, hale: hex(P.zemin, 0.8) });
      grenUygula("neon", 16, 0.1);
    },
  };

  // 7) Katmanlı kâğıt: derinlik bantları, gölgeli kâğıt kara, yükselen vurgu ülkeleri, dikiş rota
  STILLER.kagit = {
    projeksiyon: "robinson", dunya: { lon: 12, lat: 4, k: 1, dx: 0, dy: H * 0.03 }, bolgeDolgu: [0.5, 0.6], bolgeKaydir: 0.1, kavis: 0.16, enFazlaZoom: 8, dunyaGenislik: 0.9,
    ciz(u) {
      const P = { derin: "#2F6670", bantlar: ["#3B7782", "#4E8B92", "#68A2A3", "#87B9B3"], kara: "#F4EBDA", vurgu: "#E46F4B", vurgu2: "#F0A27E", dikis: "#7A2E1F", yazi: "#1F2D30" };
      arkaplan(P.derin, "#EDE4D3", null);
      const kara = cizgiler(KARA), gG = eo(ara(u, 0, 0.2));
      const s = Math.min(1.8, Math.max(0.7, Math.sqrt(proj.scale() / 330)));
      const dokulu = dokuluKure({ ort: 0.9, yay: 0.14, atm: 0.12, atmRenk: [1, 1, 1], isik: [-0.5, 0.65, 0.6], alfa: lerp(0.4, 1, gG) });
      ctx.save(); ctx.lineJoin = "round";
      if (!dokulu) P.bantlar.forEach((renk, i) => {
        const gen = (P.bantlar.length - i) * 14 * birim * s * lerp(0.4, 1, gG);
        ctx.shadowColor = "rgba(0,20,25,0.35)"; ctx.shadowBlur = 10 * birim * SS; ctx.shadowOffsetY = 3 * birim * SS;
        izle(ctx, kara); ctx.strokeStyle = renk; ctx.lineWidth = gen; ctx.stroke(); ctx.fillStyle = renk; ctx.fill();
      });
      ctx.shadowColor = "rgba(0,20,25,0.45)"; ctx.shadowBlur = 14 * birim * SS; ctx.shadowOffsetY = 5 * birim * SS;
      if (!dokulu) { izle(ctx, kara); ctx.fillStyle = P.kara; ctx.fill(); } ctx.restore();
      ctx.strokeStyle = "rgba(120,100,70,0.25)"; ctx.lineWidth = 0.7 * birim; izle(ctx, cizgiler(SINIR)); ctx.stroke();
      VURGU.forEach((v, i) => {
        const g = eio(ara(u, 0.3 + i * 0.06, 0.46 + i * 0.06)); if (g <= 0) return; const l = cizgiler(v.f); const kalk = 8 * birim * g;
        ctx.save(); ctx.translate(0, -kalk); ctx.shadowColor = "rgba(60,20,10,0.45)"; ctx.shadowBlur = (4 + 14 * g) * birim * SS; ctx.shadowOffsetY = kalk * 0.9 * SS;
        izle(ctx, l); ctx.fillStyle = i ? P.vurgu2 : P.vurgu; ctx.globalAlpha = kel(g * 1.5); ctx.fill(); ctx.restore();
      });
      VURGU.forEach((v, i) => ulkeAdi(v, eo(ara(u, 0.42 + i * 0.05, 0.52 + i * 0.05)), { font: `700 ${(i ? 15 : 18) * birim}px Fraunces`, renk: i ? P.yazi : "#FFF6EC", aralik: "0.36em", dy: 14 * birim, ust: i > 0, hale: i ? "rgba(255,253,248,0.9)" : null, haleGen: 5 * birim }));
      const r = rotaEkran(), f = eio(ara(u, ...T.rota));
      if (f > 0) { const k = rotaKismi(r, f); ctx.save(); ctx.setLineDash([9 * birim, 7 * birim]); ctx.lineCap = "round"; ctx.strokeStyle = "rgba(0,0,0,0.25)"; ctx.lineWidth = 3.2 * birim; ctx.translate(0, 2 * birim); izle(ctx, [k]); ctx.stroke(); ctx.translate(0, -2 * birim); ctx.strokeStyle = P.dikis; ctx.lineWidth = 3.2 * birim; izle(ctx, [k]); ctx.stroke(); ctx.restore(); }
      for (const y of yerler(u)) {
        const g = eo(y.g), R = (y.tip === "nokta" ? 5 : 8) * birim * g;
        ctx.save(); ctx.shadowColor = "rgba(0,0,0,0.35)"; ctx.shadowBlur = 6 * birim * SS; ctx.shadowOffsetY = 2 * birim * SS;
        ctx.fillStyle = y.tip === "nokta" ? "#FFFFFF" : P.dikis; ctx.beginPath(); ctx.arc(y.x, y.y, R, 0, 7); ctx.fill();
        // etiket kartı
        const font = y.tip === "nokta" ? `600 ${20 * birim}px Fraunces` : `700 ${28 * birim}px Fraunces`, w = genislik(y.ad, font), ph = (y.tip === "nokta" ? 34 : 44) * birim, pw = w + 26 * birim;
        let [tx, ty] = etiketYeri(y.x, y.y + ph / 2, pw, ph, 16 * birim); const kk = (1 - g) * 10 * birim;
        ctx.globalAlpha = g; ctx.fillStyle = "#FFFDF8"; ctx.beginPath(); ctx.roundRect(tx, ty - ph + kk, pw, ph, 6 * birim); ctx.fill(); ctx.restore();
        yazi(y.ad, tx + 13 * birim, ty - ph / 2 + kk + 1 * birim, { font, renk: P.yazi, alfa: g, taban: "middle" });
      }
      // başlık kartı
      const bg = eo(ara(u, ...T.baslik));
      if (bg > 0 && S.baslik) {
        const bw = Math.max(genislik(S.baslik, `700 ${92 * birim}px Fraunces`), genislik(S.altbaslik || "", `500 ${34 * birim}px Fraunces`)) + 64 * birim, bh = (S.altbaslik ? 210 : 160) * birim;
        ctx.save(); ctx.globalAlpha = bg; ctx.shadowColor = "rgba(0,20,25,0.4)"; ctx.shadowBlur = 18 * birim * SS; ctx.shadowOffsetY = 6 * birim * SS; ctx.fillStyle = "#FFFDF8"; ctx.beginPath(); ctx.roundRect(G.x0, G.y0 + (1 - bg) * 20 * birim, bw, bh, 10 * birim); ctx.fill(); ctx.restore();
        baslikBlok(u, { ust: 0, ustFont: `600 ${17 * birim}px "IBM Plex Mono"`, ustRenk: P.vurgu, baslikFont: `700 ${92 * birim}px Fraunces`, baslikBoy: 92 * birim, altFont: `500 ${34 * birim}px Fraunces`, altBoy: 50 * birim, renk: P.yazi });
      }
      sayac(u, { font: `700 ${32 * birim}px Fraunces`, renk: "#FFFDF8", not: S.sayacNot, notFont: `600 ${15 * birim}px "IBM Plex Mono"`, notBoy: 40 * birim, notRenk: "#FFE1D3" });
      grenUygula("kagit", 30, 0.2, "overlay");
    },
  };
  // başlık kartında yazılar kartın içine girsin

  // 8) İzometrik veri kuleleri: eğik düzlem, kalın kara levhası, yükselen ülkeler, şehir nüfus sütunları
  STILLER.izometrik = {
    kureUyumlu: false, projeksiyon: "equirect", dunya: { lon: 14, lat: 10, k: 1.02, dx: 0, dy: H * 0.05 }, bolgeDolgu: [0.5, 0.5], bolgeKaydir: 0.08, kavis: 0.3, enFazlaZoom: 7, dunyaGenislik: 0.9,
    ciz(u) {
      const P = { zemin1: "#EEF1F5", zemin2: "#DDE3EA", ust: "#FFFFFF", yan: "#B9C3CF", sinir: "#D5DCE5", vurgu: "#3D5AFE", vurguYan: "#2A3FB8", vurgu2: "#7C8CFF", vurgu2Yan: "#5563C9", sutun: "#FF6B3D", sutunYan: "#C9502B", yazi: "#141A26", ikincil: "#5B6576" };
      const zg = ctx.createLinearGradient(0, 0, 0, H); zg.addColorStop(0, P.zemin1); zg.addColorStop(1, P.zemin2); ctx.fillStyle = zg; ctx.fillRect(0, 0, W, H);
      const egim = lerp(1, 0.58, eio(ara(u, 0.02, 0.24))), cy = H * 0.55;
      ekran = (x, y) => [x, cy + (y - cy) * egim];
      const kara = cizgiler(KARA), kal = 7 * birim * Math.min(2.2, Math.sqrt(proj.scale() / 300)) * (1 - egim) / 0.42;
      ctx.save(); ctx.translate(0, kal); izle(ctx, kara); ctx.fillStyle = P.yan; ctx.fill(); ctx.restore();
      for (let i = kal; i > 0; i -= 1.2) { ctx.save(); ctx.translate(0, i); izle(ctx, kara); ctx.fillStyle = P.yan; ctx.fill(); ctx.restore(); }
      izle(ctx, kara); ctx.fillStyle = P.ust; ctx.fill();
      ctx.strokeStyle = P.sinir; ctx.lineWidth = 0.8 * birim; izle(ctx, cizgiler(SINIR)); ctx.stroke();
      // vurgu ülkeleri yükselir
      VURGU.map((v, i) => ({ v, i, l: cizgiler(v.f), y: (proj(d3.geoCentroid(v.f)) || [0, 0])[1] })).sort((a, b) => a.y - b.y).forEach(({ v, i, l }) => {
        const g = eio(ara(u, 0.3 + i * 0.06, 0.5 + i * 0.06)); if (g <= 0) return; const h = (v.yukseklik || (i ? 26 : 40)) * birim * g * Math.min(2, Math.sqrt(proj.scale() / 300));
        for (let k = 0; k <= h; k += 1) { ctx.save(); ctx.translate(0, -k); izle(ctx, l); ctx.fillStyle = i ? P.vurgu2Yan : P.vurguYan; ctx.fill(); ctx.restore(); }
        ctx.save(); ctx.translate(0, -h); izle(ctx, l); ctx.fillStyle = i ? P.vurgu2 : P.vurgu; ctx.fill(); ctx.strokeStyle = "rgba(255,255,255,0.5)"; ctx.lineWidth = 1 * birim; ctx.stroke(); ctx.restore();
      });
      const r = rotaEkran(), f = eio(ara(u, ...T.rota));
      if (f > 0) { const k = rotaKismi(r, f); ctx.save(); ctx.lineCap = "round"; ctx.strokeStyle = "rgba(20,26,38,0.18)"; ctx.lineWidth = 3 * birim; izle(ctx, [k.map((p, j) => [p[0], p[1]])]); ctx.stroke(); ctx.strokeStyle = P.yazi; ctx.lineWidth = 3 * birim; ctx.setLineDash([1, 8 * birim]); ctx.lineWidth = 4 * birim; izle(ctx, [k]); ctx.stroke(); ctx.restore(); }
      // şehir sütunları (nüfus) - arkadan öne
      const enb = Math.max(1, ...NOKTALAR.map((n) => n.nufus || 0), ...ROTA.map((n) => n.nufus || 0));
      const ys = yerler(u).map((y) => ({ ...y, p: ekran(y.x, y.y) })).sort((a, b) => a.p[1] - b.p[1]);
      for (const y of ys) {
        const g = eo(y.g), [x, yy] = y.p, hmax = 150 * birim * Math.sqrt((y.r.nufus || enb * 0.2) / enb), h = hmax * g, w = 9 * birim;
        const renk = y.tip === "nokta" ? P.sutun : P.yazi, yan = y.tip === "nokta" ? P.sutunYan : "#000";
        ctx.fillStyle = yan; ctx.beginPath(); ctx.ellipse(x, yy, w, w * 0.58, 0, 0, 7); ctx.fill();
        ctx.fillStyle = renk; ctx.fillRect(x - w, yy - h, w * 2, h); ctx.fillStyle = yan; ctx.globalAlpha = 0.35; ctx.fillRect(x, yy - h, w, h); ctx.globalAlpha = 1;
        ctx.fillStyle = renk; ctx.beginPath(); ctx.ellipse(x, yy - h, w, w * 0.58, 0, 0, 7); ctx.fill(); ctx.fillStyle = "rgba(255,255,255,0.35)"; ctx.beginPath(); ctx.ellipse(x, yy - h, w, w * 0.58, 0, 0, 7); ctx.fill();
        const font = `600 ${22 * birim}px "Space Grotesk"`, ad = y.ad, w2 = genislik(ad, font);
        const [tx, ty] = etiketYeri(x, yy - h - 6 * birim, w2, 24 * birim, 12 * birim);
        yazi(ad, tx, ty, { font, renk: P.yazi, alfa: g, hale: "rgba(255,255,255,0.9)", haleGen: 6 * birim });
        if (y.r.nufus) yazi(sayi(y.r.nufus), tx, ty + 22 * birim, { font: `500 ${15 * birim}px "IBM Plex Mono"`, renk: P.ikincil, alfa: g, hale: "rgba(255,255,255,0.9)", haleGen: 5 * birim });
      }
      ekran = (x, y) => [x, y];
      baslikBlok(u, { ustFont: `500 ${18 * birim}px "IBM Plex Mono"`, ustRenk: P.vurgu, baslikFont: `700 ${104 * birim}px "Space Grotesk"`, baslikBoy: 100 * birim, altFont: `400 ${36 * birim}px "Space Grotesk"`, altBoy: 50 * birim, renk: P.yazi, altRenk: P.ikincil });
      sayac(u, { font: `500 ${28 * birim}px "IBM Plex Mono"`, renk: P.yazi, not: S.veriNot || S.sayacNot, notFont: `500 ${15 * birim}px "IBM Plex Mono"`, notBoy: 38 * birim, notRenk: P.vurgu });
      grenUygula("izometrik", 10, 0.08);
    },
  };

  const ST = STILLER[S.stil];
  if (!ST) throw new Error("bilinmeyen stil: " + S.stil);
  if (S.kure !== false && ST.kureUyumlu !== false && ST.projeksiyon !== "ortho") {
    Object.assign(ST, { projeksiyon: "ortho", dunya: { lon: -25, lat: 24, k: 1, dx: 0, dy: 0 }, giriDonus: -60, enFazlaZoom: 6, bolgeDolgu: [0.34, 0.4] });
  }
  ST.bolge = { lon: 0, lat: 0, k: 1, dx: 0, dy: 0 };
  window.hazir = (async () => {
    await document.fonts.ready;
    try { await dokuYukle(); } catch (e) { console.error('doku', e); GLK = null; }
    ST.bolge = S.bolge || bolgeKamerasi();
    return true;
  })();
  window.ciz = (sn, kare = 0) => {
    const u = kel(sn / S.sure);
    yerlesik = []; ctx.setTransform(SS, 0, 0, SS, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over"; ctx.setLineDash([]); ctx.filter = "none";
    kur(kamera(u)); ST.ciz(u, kare);
    // kapanış: son %4'te hafif kararma yok; döngü için sabit kalır
    return true;
  };
  window.STILLER = Object.keys(STILLER);
})();

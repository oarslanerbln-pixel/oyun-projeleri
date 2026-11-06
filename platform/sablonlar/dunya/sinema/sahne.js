// Sinematik küre: three.js perspektif kamera, gerçek arazi, bulut, gece ışıkları, atmosfer, post FX,
// yere yapışık katmanlar (ülke, tarama, ok, cephe, menzil, nabız) + ekran katmanı (etiket, birlik, marka yazıları).
// Her kare kendi zamanından hesaplanır (deterministik). window.ciz(t) -> PNG dataURL (W×H).
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { grafikKur } from "./grafik.js";

const V = window.__VERI, S = V.sahne, M = V.marka, SS = S.ss;
const W = S.W, H = S.H, PW = Math.round(W * SS), PH = Math.round(H * SS);
const R2D = 180 / Math.PI, D2R = Math.PI / 180;
const kisa = Math.min(W, H);

// ---------------- yardımcılar ----------------
const sinir = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const ara = (t, a, b) => sinir((t - a) / Math.max(1e-6, b - a));
const eio = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const eo = (x) => 1 - Math.pow(1 - x, 3);
const eoq = (x) => 1 - Math.pow(1 - x, 5);
const rng = (s) => () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
function v3(lon, lat, r = 1) { const a = lon * D2R, b = lat * D2R; return new THREE.Vector3(r * Math.cos(b) * Math.cos(a), r * Math.sin(b), -r * Math.cos(b) * Math.sin(a)); }
function lonlat(v) { const n = v.clone().normalize(); return [Math.atan2(-n.z, n.x) * R2D, Math.asin(sinir(n.y, -1, 1)) * R2D]; }
function hex(c, a = 1) { const n = parseInt(c.slice(1), 16); return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`; }
const renk = (rol) => (M.roller[rol] || M.roller.notr);
// pencere [a,b] içinde görünürlük: giriş/çıkış yumuşak
function gor(k, t, gir = 0.6, cik = 0.5) { const [a, b] = k.t || [0, 1e9]; return Math.min(eo(ara(t, a, a + gir)), 1 - ara(t, b - cik, b)); }

// ---------------- WebGL ----------------
const cv = document.getElementById("gl"); cv.width = PW; cv.height = PH;
const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: false, preserveDrawingBuffer: true, alpha: false, powerPreference: "high-performance" });
renderer.setPixelRatio(1); renderer.setSize(PW, PH, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = S.pozlama ?? 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;
const sahne = new THREE.Scene();
sahne.background = new THREE.Color(M.uzay);
const kisaFov = 30;
const kam = new THREE.PerspectiveCamera(1, W / H, 0.001, 100);
kam.fov = W >= H ? kisaFov : 2 * Math.atan(Math.tan(kisaFov * D2R / 2) * H / W) * R2D; kam.updateProjectionMatrix();
const genFov = 2 * Math.atan(Math.tan(kam.fov * D2R / 2) * Math.max(1, W / H)); // yatay görüş açısı (rad)

const yukle = new THREE.TextureLoader();
const aniz = Math.min(4, renderer.capabilities.getMaxAnisotropy());
function doku(url, srgb) {
  return new Promise((ok, red) => yukle.load(url, (t) => { t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace; t.anisotropy = aniz;
    t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.wrapS = THREE.RepeatWrapping; ok(t); }, undefined, red));
}
const ISIK = { gece: "kure", gunduz: "gunduz", alacakaranlik: "gunduz", atlas: "atlas" }[S.isik] || "kure";
const [tRenk, tGece, tNormal, tSu, tBulut, tYuk] = await Promise.all([
  doku(V.dokular[ISIK], true), doku(V.dokular.gece), doku(V.dokular.normal), doku(V.dokular.su), doku(V.dokular.bulut), doku(V.dokular.yukseklik)]);

// yere yapışık katman tuvalleri: dünya (4096×2048) + odak bölgesi (≤4096², keskin)
function tuval(w, h) { const c = document.createElement("canvas"); c.width = w; c.height = h; c.getContext("2d", { willReadFrequently: true }); return c; }
const ustW = tuval(4096, 2048), ustWt = new THREE.CanvasTexture(ustW);
const BK = S.odak; // [lon0, lat0, lon1, lat1]
const bw = 4096, bh = Math.min(4096, Math.round(4096 * (BK[3] - BK[1]) / ((BK[2] - BK[0]) * Math.cos(((BK[1] + BK[3]) / 2) * D2R))));
const ustR = tuval(bw, Math.max(256, bh)), ustRt = new THREE.CanvasTexture(ustR);
for (const t of [ustWt, ustRt]) { t.colorSpace = THREE.SRGBColorSpace; t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; }

const U = {
  tRenk: { value: tRenk }, tGece: { value: tGece }, tNormal: { value: tNormal }, tSu: { value: tSu }, tBulut: { value: tBulut }, tYuk: { value: tYuk },
  tUstW: { value: ustWt }, tUstR: { value: ustRt }, bolge: { value: new THREE.Vector4(...BK) },
  gunes: { value: new THREE.Vector3(1, 0, 0) }, kamPos: { value: new THREE.Vector3() },
  abart: { value: 0.0 }, bulutY: { value: 0 }, bulutKay: { value: 0 }, geceGuc: { value: 0 }, geceSabit: { value: 0 },
  ortam: { value: 0.1 }, isikKarisim: { value: 1 }, normalGuc: { value: 1 }, parlama: { value: 0.5 },
  atmRenk: { value: new THREE.Color(M.atmosfer) }, geceRenk: { value: new THREE.Color(M.sehirIsigi) }, gunesRenk: { value: new THREE.Color(1.0, 0.97, 0.92) },
  ustIsik: { value: 0.35 }, ustSoluk: { value: 0 }, soluk: { value: new THREE.Color(M.soluk || "#0b1220") },
};
const ORTAK_GLSL = `
uniform sampler2D tRenk, tGece, tNormal, tSu, tBulut, tYuk, tUstW, tUstR; uniform vec4 bolge;
uniform vec3 gunes, kamPos, atmRenk, geceRenk, gunesRenk, soluk; uniform float abart, bulutY, bulutKay, geceGuc, geceSabit, ortam, isikKarisim, normalGuc, parlama, ustIsik, ustSoluk;
`;
const yerMat = new THREE.ShaderMaterial({
  uniforms: U,
  vertexShader: ORTAK_GLSL + `
  varying vec2 vUv; varying vec3 vN, vP;
  void main(){ vUv = uv; vec3 n = normalize(position); float h = texture2D(tYuk, uv).r; h = h*h*0.00139*abart;
    vec3 p = n*(1.0+h); vN = n; vP = p; gl_Position = projectionMatrix*modelViewMatrix*vec4(p,1.0); }`,
  fragmentShader: ORTAK_GLSL + `
  varying vec2 vUv; varying vec3 vN, vP;
  void main(){
    vec3 nG = normalize(vN); vec3 Vv = normalize(kamPos - vP);
    vec3 nT = normalize(texture2D(tNormal, vUv).xyz*2.0-1.0); nT = normalize(mix(nG, nT, normalGuc));
    float mu = dot(nG, gunes); float gun = smoothstep(-0.10, 0.22, mu);
    float dif = max(dot(nT, gunes), 0.0);
    vec3 alb = texture2D(tRenk, vUv).rgb;
    float bs = texture2D(tBulut, vUv + vec2(bulutKay + 0.0015, -0.001)).r * bulutY;
    float isik = mix(1.0, dif * (1.0 - 0.55*bs), isikKarisim);
    vec3 c = alb * (isik * gunesRenk + ortam);
    float su = texture2D(tSu, vUv).r; vec3 Hh = normalize(gunes + Vv);
    c += gunesRenk * pow(max(dot(nG, Hh), 0.0), 140.0) * su * parlama * gun * (1.0 - bs);
    float g = texture2D(tGece, vUv).r; float gece = mix(1.0 - gun, 1.0, geceSabit);
    c += geceRenk * (g*g*1.6 + g*0.35) * gece * geceGuc * (1.0 - 0.7*bs);
    // yere yapışık katmanlar: odak bölgesi içinde keskin tuval, dışında dünya tuvali
    float lon = vUv.x*360.0-180.0, lat = vUv.y*180.0-90.0;
    vec2 ub = vec2((lon-bolge.x)/(bolge.z-bolge.x), (lat-bolge.y)/(bolge.w-bolge.y));
    vec4 ow = texture2D(tUstW, vUv);
    vec4 orr = texture2D(tUstR, ub);
    float ic = step(0.0, ub.x)*step(ub.x, 1.0)*step(0.0, ub.y)*step(ub.y, 1.0);
    vec4 o = mix(ow, orr, ic * smoothstep(0.0, 0.01, min(min(ub.x, 1.0-ub.x), min(ub.y, 1.0-ub.y))));
    c = mix(c, soluk, ustSoluk * (1.0 - o.a));
    vec3 oc = o.rgb * mix(1.0, 0.55 + 0.6*dif, ustIsik);
    c = mix(c, oc, o.a);
    float fr = pow(1.0 - max(dot(nG, Vv), 0.0), 2.6);
    c += atmRenk * fr * (0.18 + 0.9*smoothstep(-0.2, 0.5, mu));
    gl_FragColor = vec4(c, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`,
});
yerMat.toneMapped = true;
const SEG = S.kalite === "taslak" ? [256, 128] : [1024, 512];
const yer = new THREE.Mesh(new THREE.SphereGeometry(1, SEG[0], SEG[1]), yerMat); sahne.add(yer);

const bulutMat = new THREE.ShaderMaterial({
  uniforms: U, transparent: true, depthWrite: false,
  vertexShader: `varying vec2 vUv; varying vec3 vN; void main(){ vUv = uv; vN = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: ORTAK_GLSL + `varying vec2 vUv; varying vec3 vN;
  void main(){ float b = texture2D(tBulut, vUv + vec2(bulutKay, 0.0)).r; float a = smoothstep(0.22, 0.95, b) * bulutY * 0.9;
    float mu = dot(normalize(vN), gunes); float l = mix(1.0, smoothstep(-0.15, 0.35, mu), isikKarisim);
    gl_FragColor = vec4(vec3(0.86, 0.88, 0.92) * (0.06 + 0.94*l) * gunesRenk, a * (0.25 + 0.75*l)); }`,
});
const bulut = new THREE.Mesh(new THREE.SphereGeometry(1.0075, 256, 128), bulutMat); sahne.add(bulut);

// atmosfer: kabuk üzerinde ışın-küre en yakın yaklaşımından ölçek yüksekliği; gündüz mavi, terminatör turuncu
const atmMat = new THREE.ShaderMaterial({
  uniforms: U, transparent: true, depthWrite: false, side: THREE.BackSide, blending: THREE.AdditiveBlending,
  vertexShader: `varying vec3 vP; void main(){ vP = (modelMatrix*vec4(position,1.0)).xyz; gl_Position = projectionMatrix*viewMatrix*vec4(vP,1.0); }`,
  fragmentShader: ORTAK_GLSL + `varying vec3 vP; uniform float atmGuc;
  void main(){ vec3 d = normalize(vP - kamPos); float tc = -dot(kamPos, d); vec3 q = kamPos + d*tc; float b = length(q);
    if (tc < 0.0) { q = kamPos; b = length(kamPos); }
    float yog = exp(-max(b - 1.0, 0.0) / 0.018) * smoothstep(1.075, 1.0, b);
    float mu = dot(normalize(q), gunes);
    float gun = smoothstep(-0.35, 0.35, mu); float ter = exp(-pow(mu/0.18, 2.0));
    vec3 c = atmRenk * gun + vec3(1.0, 0.42, 0.16) * ter * 0.55 * isikKarisim;
    c = mix(atmRenk*0.55, c, isikKarisim);
    gl_FragColor = vec4(c * yog * atmGuc, 1.0); }`,
});
atmMat.uniforms.atmGuc = { value: 1.0 };
const atm = new THREE.Mesh(new THREE.SphereGeometry(1.08, 192, 96), atmMat); sahne.add(atm);

// yıldızlar (sabit tohum)
{
  const r = rng(7), n = 2600, pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { const u = r() * 2 - 1, a = r() * Math.PI * 2, s = Math.sqrt(1 - u * u); pos.set([40 * s * Math.cos(a), 40 * u, 40 * s * Math.sin(a)], i * 3);
    const p = Math.pow(r(), 6) * 0.9 + 0.08; col.set([p * 0.92, p * 0.95, p], i * 3); }
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const m = new THREE.PointsMaterial({ size: 1.4 * SS, sizeAttenuation: false, vertexColors: true, transparent: true, opacity: S.yildiz ?? 0.85, depthWrite: false });
  sahne.add(new THREE.Points(g, m));
}

// post: bloom (şehir ışıkları, atmosfer) -> ton eşleme -> vinyet + ince gren
const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(PW, PH, { type: THREE.HalfFloatType, samples: S.msaa ?? 0 }));
composer.setPixelRatio(1); composer.setSize(PW, PH);
composer.addPass(new RenderPass(sahne, kam));
const bloom = new UnrealBloomPass(new THREE.Vector2(PW / 2, PH / 2), M.bloom?.[0] ?? 0.55, M.bloom?.[1] ?? 0.5, M.bloom?.[2] ?? 0.82);
composer.addPass(bloom);
composer.addPass(new OutputPass());
const son = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, vin: { value: M.vinyet ?? 0.32 }, gren: { value: M.gren ?? 0.018 }, tohum: { value: 0 }, oran: { value: W / H } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float vin, gren, tohum, oran; varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233)) + tohum) * 43758.5453); }
    void main(){ vec2 q = vUv - 0.5; q.x *= oran; float r = length(q) / length(vec2(0.5*oran, 0.5));
      vec3 c = texture2D(tDiffuse, vUv).rgb; c *= 1.0 - vin * smoothstep(0.35, 1.05, r);
      c += (h(vUv*1000.0) - 0.5) * gren; gl_FragColor = vec4(c, 1.0); }`,
});
composer.addPass(son);

// ---------------- kamera dili ----------------
// anahtar kare: {t, hedef:[lon,lat], irtifa (yarıçap), egim (°, 0 = tepeden), yon (°, 0 = kuzey yukarı), kayX, kayY (kadraj kaydırma)}
const AK = S.kamera;
function slerp(a, b, f) { const om = Math.acos(sinir(a.dot(b), -1, 1)); if (om < 1e-5) return a.clone(); const s = Math.sin(om);
  return a.clone().multiplyScalar(Math.sin((1 - f) * om) / s).add(b.clone().multiplyScalar(Math.sin(f * om) / s)); }
const GENIS = 2 * Math.tan(genFov / 2); // yer genişliği = irtifa * GENIS
function vanWijk(w0, w1, d, s) { // d3.interpolateZoom (rho = sqrt2) tek eksende: [u, w]
  const rho = Math.SQRT2, r2 = 2, r4 = 4;
  if (d < 1e-6) { const S_ = Math.log(w1 / w0) / rho; return [0, w0 * Math.exp(rho * s * S_)]; }
  const b0 = (w1 * w1 - w0 * w0 + r4 * d * d) / (2 * w0 * r2 * d), b1 = (w1 * w1 - w0 * w0 - r4 * d * d) / (2 * w1 * r2 * d);
  const r0 = Math.log(Math.sqrt(b0 * b0 + 1) - b0), r1 = Math.log(Math.sqrt(b1 * b1 + 1) - b1), S_ = (r1 - r0) / rho;
  const ss = s * S_, cs = Math.cosh(r0), u = w0 / (r2 * d) * (cs * Math.tanh(rho * ss + r0) - Math.sinh(r0));
  return [u * d, w0 * cs / Math.cosh(rho * ss + r0)];
}
function kameraDurum(t) {
  let i = 0; while (i < AK.length - 2 && t > AK[i + 1].t) i++;
  const a = AK[i], b = AK[Math.min(i + 1, AK.length - 1)];
  const f = b === a ? 0 : (a.egri === "dogrusal" ? ara(t, a.t, b.t) : eio(ara(t, a.t, b.t)));
  const pa = v3(...a.hedef), pb = v3(...b.hedef), d = Math.acos(sinir(pa.dot(pb), -1, 1));
  let alt, s;
  if (d > 0.02 && b.ucus !== false) { const [u, w] = vanWijk(a.irtifa * GENIS, b.irtifa * GENIS, d, f); s = u / d; alt = w / GENIS; }
  else { s = f; alt = Math.exp(Math.log(a.irtifa) * (1 - f) + Math.log(b.irtifa) * f); }
  const yon = a.yon + (b.yon - a.yon) * f + (S.yorunge || 0) * t, egim = a.egim + (b.egim - a.egim) * f;
  return { p: slerp(pa, pb, sinir(s)), alt, egim, yon, kayX: a.kayX + (b.kayX - a.kayX) * f, kayY: a.kayY + (b.kayY - a.kayY) * f };
}
function kameraKur(t) {
  const k = kameraDurum(t), N = k.p.clone().normalize(), [lo, la] = lonlat(N);
  const E = new THREE.Vector3(-Math.sin(lo * D2R), 0, -Math.cos(lo * D2R));
  const No = new THREE.Vector3(-Math.sin(la * D2R) * Math.cos(lo * D2R), Math.cos(la * D2R), Math.sin(la * D2R) * Math.sin(lo * D2R));
  const h = k.yon * D2R, e = sinir(k.egim, 0, 80) * D2R;
  const f = No.clone().multiplyScalar(Math.cos(h)).add(E.clone().multiplyScalar(Math.sin(h)));
  const hedef = N.clone();
  const poz = hedef.clone().add(N.clone().multiplyScalar(Math.cos(e) * k.alt)).add(f.clone().multiplyScalar(-Math.sin(e) * k.alt));
  kam.position.copy(poz); kam.up.copy(f.clone().multiplyScalar(Math.cos(e)).add(N.clone().multiplyScalar(Math.sin(e))));
  kam.lookAt(hedef);
  kam.near = Math.max(0.0005, k.alt * 0.05); kam.far = poz.length() + 50;
  // kadraj kaydırma: konu ekranın üçte birine (yazıya yer)
  if (k.kayX || k.kayY) kam.setViewOffset(W, H, -k.kayX * W, -k.kayY * H, W, H); else kam.clearViewOffset();
  kam.updateProjectionMatrix(); kam.updateMatrixWorld();
  return k;
}

// ışık modu: güneş kameraya göre (sol üst) ya da gerçek alt güneş noktası
function isikKur(t, k) {
  const ileri = new THREE.Vector3(), sag = new THREE.Vector3(), ust = new THREE.Vector3();
  kam.getWorldDirection(ileri); sag.crossVectors(ileri, kam.up).normalize(); ust.crossVectors(sag, ileri).normalize();
  const mod = S.isik;
  const ac = { gece: [-0.55, 0.55, -0.62], gunduz: [-0.5, 0.45, -0.75], alacakaranlik: [0.95, 0.25, 0.18], atlas: [-0.45, 0.5, -0.75] }[mod] || [-0.5, 0.5, -0.7];
  let g = sag.clone().multiplyScalar(ac[0]).add(ust.clone().multiplyScalar(ac[1])).add(ileri.clone().multiplyScalar(ac[2]));
  if (S.gunes) g = v3(S.gunes[0] + (S.gunesHiz || 0) * t, S.gunes[1]);
  U.gunes.value.copy(g.normalize()); U.kamPos.value.copy(kam.position);
  const yakin = 1 - ara(k.alt, 0.25, 1.6);
  U.abart.value = (S.kabartma ?? 1) * (6 + 22 * yakin);
  const P = {
    gece: { isikKarisim: 0.55, ortam: 0.16, geceGuc: 1.25, geceSabit: 1, normalGuc: 0.9, parlama: 0.0, ustIsik: 0.25 },
    gunduz: { isikKarisim: 1, ortam: 0.06, geceGuc: 0, geceSabit: 0, normalGuc: 1, parlama: 0.3, ustIsik: 0.35 },
    alacakaranlik: { isikKarisim: 1, ortam: 0.025, geceGuc: 1.35, geceSabit: 0, normalGuc: 1, parlama: 0.35, ustIsik: 0.45 },
    atlas: { isikKarisim: 0.6, ortam: 0.25, geceGuc: 0, geceSabit: 0, normalGuc: 0.8, parlama: 0.0, ustIsik: 0.2 },
  }[mod] || {};
  for (const [a, b] of Object.entries(P)) U[a].value = b;
  // bulut: tam dünya anlarında görünür, bölgeye inerken açılır (katmanlar okunur kalsın)
  const by = S.bulut ?? (mod === "gece" || mod === "atlas" ? 0 : 0.85);
  U.bulutY.value = by * ara(k.alt, 1.3, 3.2);
  U.bulutKay.value = t * 0.0006;
  atmMat.uniforms.atmGuc.value = M.atmGuc ?? 1.0;
  // odak: bölgeye inildiğinde katmanlar dışındaki dünya hafif söner (dikkat konuda)
  U.ustSoluk.value = (S.sondur ?? 0.0) * (1 - ara(k.alt, 0.6, 2.0));
}

// ---------------- yere yapışık katmanlar (Canvas 2D, eşdikdörtgen) ----------------
const topo = V.topo;
// sınır görüşü: uluslararası tanınan sınırlar (world-atlas/Natural Earth Kırım'ı Rusya'ya bağlar -> Ukrayna'ya taşı)
(function kirim() { const G = topo.objects.countries.geometries, ru = G.find((g) => g.properties.name === "Russia"), ua = G.find((g) => g.properties.name === "Ukraine");
  if (!ru || !ua || ru.type !== "MultiPolygon") return;
  const i = ru.arcs.findIndex((poly) => d3.geoContains(topojson.feature(topo, { type: "Polygon", arcs: poly }), [34.0, 45.2])); if (i < 0) return;
  const [poly] = ru.arcs.splice(i, 1); if (ua.type === "Polygon") { ua.type = "MultiPolygon"; ua.arcs = [ua.arcs]; } ua.arcs.push(poly); })();
const ulkeler = topojson.feature(topo, topo.objects.countries).features;
const sinirlar = topojson.mesh(topo, topo.objects.countries, (a, b) => a !== b);
const ULKE = new Map(ulkeler.map((f) => [f.properties.name, f]));
function ulkeGeo(k) { if (ULKE.has(k.geo)) return ULKE.get(k.geo); if (k.halkalar) { const f = { type: "Feature", geometry: { type: "MultiPolygon", coordinates: k.halkalar.map((h) => [h]) } };
  if (d3.geoArea(f) > 2 * Math.PI) f.geometry.coordinates.forEach((p) => p[0].reverse()); return f; } return null; }
const KATMAN = S.katmanlar.map((k) => ({ ...k, f: k.tip === "ulke" || k.tip === "bolge" ? (k.ulkeler || [k]).map(ulkeGeo).filter(Boolean) : null }));
function projeksiyon(c, kutu) {
  const [a, b, cc, d] = kutu, sx = c.width / ((cc - a) * D2R), sy = c.height / ((d - b) * D2R);
  return d3.geoTransform({ point(lon, lat) { this.stream.point((lon - a) * D2R * sx, (d - lat) * D2R * sy); } });
}
function projW(c) { return d3.geoEquirectangular().scale(c.width / (2 * Math.PI)).translate([c.width / 2, c.height / 2]).precision(0.1); }
function desen(g, renk_, aci = 45, aralik = 14, kal = 4) {
  const p = tuval(aralik * 4, aralik * 4), x = p.getContext("2d"); x.strokeStyle = renk_; x.lineWidth = kal;
  for (let i = -4; i < 8; i++) { x.beginPath(); x.moveTo(i * aralik, 0); x.lineTo(i * aralik + p.height, p.height); x.stroke(); }
  return g.createPattern(p, "repeat");
}
// Catmull-Rom ile yumuşak yol (ekran/tuval koordinatlarında)
function yumusak(pts, n = 24) {
  if (pts.length < 3) { const out = []; for (let i = 0; i <= n; i++) { const f = i / n; out.push([pts[0][0] + (pts[1][0] - pts[0][0]) * f, pts[0][1] + (pts[1][1] - pts[0][1]) * f]); } return out; }
  const out = [], P = [pts[0], ...pts, pts[pts.length - 1]];
  for (let i = 1; i < P.length - 2; i++) for (let j = 0; j < n; j++) { const t = j / n, t2 = t * t, t3 = t2 * t;
    out.push([0, 1].map((k) => 0.5 * (2 * P[i][k] + (-P[i - 1][k] + P[i + 1][k]) * t + (2 * P[i - 1][k] - 5 * P[i][k] + 4 * P[i + 1][k] - P[i + 2][k]) * t2 + (-P[i - 1][k] + 3 * P[i][k] - 3 * P[i + 1][k] + P[i + 2][k]) * t3))); }
  out.push(pts[pts.length - 1]); return out;
}
function kirpYol(yol, p) { // yay uzunluğuna göre ilk p kısmı
  const L = [0]; for (let i = 1; i < yol.length; i++) L.push(L[i - 1] + Math.hypot(yol[i][0] - yol[i - 1][0], yol[i][1] - yol[i - 1][1]));
  const hedef = L[L.length - 1] * p, out = [yol[0]];
  for (let i = 1; i < yol.length; i++) { if (L[i] <= hedef) { out.push(yol[i]); continue; } const f = (hedef - L[i - 1]) / (L[i] - L[i - 1] || 1);
    out.push([yol[i - 1][0] + (yol[i][0] - yol[i - 1][0]) * f, yol[i - 1][1] + (yol[i][1] - yol[i - 1][1]) * f]); break; }
  return out;
}
// askeri harita oku: incelen gövde, beyaz kontur, gölge, keskin uç
function okCiz(g, yol, p, gen, renk_) {
  if (p <= 0.001 || yol.length < 2) return;
  const y = kirpYol(yol, p); if (y.length < 2) return;
  const n = y.length, sol = [], sag = [];
  const ucBoy = gen * 2.3;
  for (let i = 0; i < n; i++) { const a = y[Math.max(0, i - 1)], b = y[Math.min(n - 1, i + 1)]; let dx = b[0] - a[0], dy = b[1] - a[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
    const w = gen * (0.42 + 0.58 * (i / (n - 1))) / 2; sol.push([y[i][0] - dy * w, y[i][1] + dx * w]); sag.push([y[i][0] + dy * w, y[i][1] - dx * w]); }
  const u = y[n - 1], o = y[Math.max(0, n - 4)]; let dx = u[0] - o[0], dy = u[1] - o[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
  // gövdeyi uç tabanında bitir
  const yolG = kirpYol(y, Math.max(0, 1 - ucBoy * 0.55 / Math.max(1, yolUzun(y))));
  const m = yolG.length, sol2 = sol.slice(0, m), sag2 = sag.slice(0, m);
  const taban = yolG[m - 1];
  const sekil = (gg) => { gg.beginPath(); gg.moveTo(...sol2[0]); sol2.forEach((q) => gg.lineTo(...q));
    gg.lineTo(taban[0] - dy * gen * 1.05, taban[1] + dx * gen * 1.05); gg.lineTo(u[0] + dx * ucBoy * 0.45, u[1] + dy * ucBoy * 0.45);
    gg.lineTo(taban[0] + dy * gen * 1.05, taban[1] - dx * gen * 1.05); for (let i = m - 1; i >= 0; i--) gg.lineTo(...sag2[i]); gg.closePath(); };
  for (const [o, al] of [[0.42, 0.12], [0.3, 0.16], [0.18, 0.2]]) { g.save(); g.translate(gen * o, gen * o * 1.3); sekil(g); g.fillStyle = `rgba(0,0,0,${al})`; g.fill(); g.restore(); }
  g.save(); sekil(g); const gr = g.createLinearGradient(y[0][0], y[0][1], u[0], u[1]); gr.addColorStop(0, hex(renk_, 0.55)); gr.addColorStop(0.4, hex(renk_, 0.92)); gr.addColorStop(1, hex(renk_, 1));
  g.fillStyle = gr; g.fill(); g.lineJoin = "round"; g.strokeStyle = "rgba(255,255,255,0.9)"; g.lineWidth = gen * 0.09; g.stroke();
  // akış: gövde içinde ilerleyen ince şevronlar (hareket yönü), uca doğru sönen
  sekil(g); g.clip(); const L = yolUzun(yolG), ad = gen * 1.6, kay = (okZaman * gen * 2.2) % ad;
  g.strokeStyle = "rgba(255,255,255,0.32)"; g.lineWidth = gen * 0.12; g.lineCap = "round";
  for (let s_ = kay; s_ < L - gen * 0.5; s_ += ad) { const k1 = kirpYol(yolG, s_ / L), q = k1[k1.length - 1], k0 = kirpYol(yolG, Math.max(0, s_ - 4) / L), o = k0[k0.length - 1];
    let ux = q[0] - o[0], uy = q[1] - o[1]; const ul = Math.hypot(ux, uy) || 1; ux /= ul; uy /= ul; const w = gen * (0.42 + 0.58 * s_ / L) * 0.32;
    g.globalAlpha = 0.25 + 0.75 * (s_ / L); g.beginPath(); g.moveTo(q[0] - ux * w - uy * w, q[1] - uy * w + ux * w); g.lineTo(q[0], q[1]); g.lineTo(q[0] - ux * w + uy * w, q[1] - uy * w - ux * w); g.stroke(); }
  g.restore();
  if (p < 1) { const ux_ = u[0] + dx * ucBoy * 0.45, uy_ = u[1] + dy * ucBoy * 0.45, rg = g.createRadialGradient(ux_, uy_, 0, ux_, uy_, gen * 0.9); rg.addColorStop(0, "rgba(255,255,255,0.7)"); rg.addColorStop(1, "rgba(255,255,255,0)");
    g.save(); g.globalAlpha = (1 - p) * 0.9; g.fillStyle = rg; g.beginPath(); g.arc(ux_, uy_, gen * 0.9, 0, 7); g.fill(); g.restore(); }
}
let okZaman = 0;
function yolUzun(y) { let s = 0; for (let i = 1; i < y.length; i++) s += Math.hypot(y[i][0] - y[i - 1][0], y[i][1] - y[i - 1][1]); return s; }
function cepheCiz(g, yol, gen, renk_, taraf = 1) {
  if (yol.length < 2) return; g.save(); g.lineJoin = g.lineCap = "round";
  g.beginPath(); yol.forEach((q, i) => (i ? g.lineTo(...q) : g.moveTo(...q))); g.strokeStyle = "rgba(0,0,0,0.35)"; g.lineWidth = gen * 1.6; g.stroke();
  g.strokeStyle = renk_; g.lineWidth = gen; g.stroke();
  // dişler: ilerleme yönüne üçgenler
  const ad = gen * 5; let acc = 0; g.fillStyle = renk_;
  for (let i = 1; i < yol.length; i++) { const a = yol[i - 1], b = yol[i], l = Math.hypot(b[0] - a[0], b[1] - a[1]); if (!l) continue; const dx = (b[0] - a[0]) / l, dy = (b[1] - a[1]) / l;
    let s = ad - acc; while (s < l) { const x = a[0] + dx * s, y = a[1] + dy * s, nx = -dy * taraf, ny = dx * taraf;
      g.beginPath(); g.moveTo(x - dx * gen * 1.4, y - dy * gen * 1.4); g.lineTo(x + nx * gen * 2.2, y + ny * gen * 2.2); g.lineTo(x + dx * gen * 1.4, y + dy * gen * 1.4); g.fill(); s += ad; }
    acc = (acc + l) % ad; }
  g.restore();
}
function yeniden(yol, n) { const L = yolUzun(yol), out = []; for (let i = 0; i <= n; i++) { const k = kirpYol(yol, i / n); out.push(k[k.length - 1]); } return out; }

let sonAnahtar = { W: "", R: "" };
function katmanCiz(c, kutu, t, olcek, dunya, hareketli = true) {
  const g = c.getContext("2d"); g.clearRect(0, 0, c.width, c.height);
  const pr = dunya ? projW(c) : projeksiyon(c, kutu), yol = d3.geoPath(pr, g);
  const xy = (p) => (dunya ? pr(p) : (() => { let q; pr.stream({ point(x, y) { q = [x, y]; } }).point(p[0], p[1]); return q; })());
  const px = (v) => v * olcek; // ekran pikseli -> tuval pikseli
  // ülke dolguları ve taramalar
  for (const k of KATMAN) {
    if (!k.f) continue; const a = gor(k, t, 0.8, 0.6); if (a <= 0) continue; const r = renk(k.rol || "ana");
    const t0 = k.t?.[0] ?? 0, acil = eoq(ara(t, t0, t0 + 1.5)), iz = eio(ara(t, t0, t0 + 1.9));
    const merkez = k.etiketKonum ? xy(k.etiketKonum) : null;
    for (const f of k.f) {
      g.save(); g.globalAlpha = a;
      if (merkez && acil < 1) { const kb = d3.geoBounds(f), c1 = xy([kb[0][0], kb[0][1]]), c2 = xy([kb[1][0], kb[1][1]]);
        const R = Math.max(...[c1, c2, [c1[0], c2[1]], [c2[0], c1[1]]].map((q) => Math.hypot(q[0] - merkez[0], q[1] - merkez[1]))) * 1.05;
        g.beginPath(); g.arc(merkez[0], merkez[1], Math.max(1, R * acil), 0, 7); g.clip(); }
      const stilDolgu = G.ulkeDolgu && k.desen !== "tarama"; // tarama (tartışmalı alan) her stilde aynı anlamı taşır
      if (stilDolgu) G.ulkeDolgu(g, yol, f, r, px); else { g.beginPath(); yol(f); }
      if (stilDolgu) { /* stil çizdi */ }
      else if (k.desen === "tarama") { g.fillStyle = hex(r.dolgu, 0.18); g.fill(); g.fillStyle = desen(g, hex(r.dolgu, 0.85), 45, Math.max(6, px(9)), Math.max(1.5, px(2.2))); g.fill(); }
      else { g.fillStyle = hex(r.dolgu, k.yogunluk ?? r.alfa ?? 0.32); g.fill();
        g.save(); g.clip(); for (const [w_, al] of [[18, 0.12], [11, 0.16], [5, 0.22]]) { g.strokeStyle = hex(r.kontur, al); g.lineWidth = px(w_); g.stroke(); } g.restore(); }
      g.restore(); g.save(); g.globalAlpha = a; g.beginPath(); yol(f);
      if (iz < 1) { const L = d3.geoLength(f) * c.width / (dunya ? 2 * Math.PI : (kutu[2] - kutu[0]) * D2R) * 1.3; g.setLineDash([L * iz, L * 2]); }
      if (G.ulkeKontur) G.ulkeKontur(g, yol, f, r, px);
      else { g.lineJoin = g.lineCap = "round"; g.strokeStyle = hex(r.kontur, 0.35 * a); g.lineWidth = px(6); g.stroke();
        g.strokeStyle = hex(r.kontur, 0.95); g.lineWidth = px(1.6); g.stroke(); }
      g.restore();
    }
  }
  // tüm sınırlar (ince)
  g.save(); g.beginPath(); yol(sinirlar); g.strokeStyle = M.sinir; g.lineWidth = px(M.sinirKalin ?? 0.9); g.stroke(); g.restore();
  // menzil halkaları (jeodezik daire)
  for (const k of (hareketli ? KATMAN : []).filter((k) => k.tip === "menzil")) { const a = gor(k, t, 1.0, 0.6); if (a <= 0) continue; const r = renk(k.rol || "karsi");
    const p = eoq(ara(t, k.t?.[0] ?? 0, (k.t?.[0] ?? 0) + 1.6)); const ci = d3.geoCircle().center(k.konum).radius((k.km / 6371) * R2D * p).precision(1)();
    g.save(); g.globalAlpha = a; g.beginPath(); yol(ci); g.fillStyle = hex(r.dolgu, 0.12); g.fill(); g.setLineDash([px(8), px(6)]); g.strokeStyle = hex(r.kontur, 0.95); g.lineWidth = px(2); g.stroke(); g.restore(); }
  // cepheler (durumlar arası biçim değiştirir)
  for (const k of (hareketli ? KATMAN : []).filter((k) => k.tip === "cephe")) { const a = gor(k, t); if (a <= 0) continue; const ds = k.durumlar; let i = 0; while (i < ds.length - 2 && t > ds[i + 1].t) i++;
    const A = ds[i], B = ds[Math.min(i + 1, ds.length - 1)], f = B === A ? 0 : eio(ara(t, A.t, B.t));
    const pa = yeniden(yumusak(A.yol.map(xy), 12), 200), pb = yeniden(yumusak(B.yol.map(xy), 12), 200);
    const y = pa.map((q, j) => [q[0] + (pb[j][0] - q[0]) * f, q[1] + (pb[j][1] - q[1]) * f]);
    const ci = eio(ara(t, k.t?.[0] ?? 0, (k.t?.[0] ?? 0) + 1.6)); g.save(); g.globalAlpha = a; const yc = ci < 1 ? kirpYol(y, ci) : y;
    if (k.yikama && f + i > 0) { // ilk hat ile bugünkü hat arasındaki alan: kazanılan toprak (mürekkep yıkaması)
      const p0 = yeniden(yumusak(ds[0].yol.map(xy), 12), 200), alan = p0.concat(y.slice().reverse()), r = renk(k.rol || "karsi");
      if (G.yikama) G.yikama(g, alan, r, px, t); else { g.beginPath(); alan.forEach((q, j) => (j ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1]))); g.closePath(); g.fillStyle = hex(r.dolgu, 0.22); g.fill(); } }
    if (G.cephe) G.cephe(g, yc, px(3.2) * (G.cepheOlcek ?? 1), renk(k.rol || "karsi"), k.taraf || 1, t); else cepheCiz(g, yc, px(3.2), renk(k.rol || "karsi").kontur, k.taraf || 1); g.restore(); }
  // oklar
  for (const k of (hareketli ? KATMAN : []).filter((k) => k.tip === "ok")) { const [a0, b0] = k.t || [0, 1]; const p = (G.okEase || eio)(ara(t, a0, a0 + (k.cizim ?? 2.2) * (G.hiz ?? 1))); const a = gor(k, t, 0.01, 0.6); if (a <= 0 || p <= 0) continue;
    okZaman = t - a0; g.save(); g.globalAlpha = a; const yy = yumusak(k.yol.map(xy), 30);
    if (G.ok) G.ok(g, yy, p, px(k.kalin ?? 26), renk(k.rol || "karsi"), t - a0, px); else okCiz(g, yy, p, px(k.kalin ?? 26), renk(k.rol || "karsi").dolgu); g.restore(); }
  // rotalar (yer üstü kesikli, ilerleyen)
  for (const k of (hareketli ? KATMAN : []).filter((k) => k.tip === "rota")) { const [a0] = k.t || [0]; const p = eio(ara(t, a0, a0 + (k.cizim ?? 3))); const a = gor(k, t, 0.01, 0.6); if (a <= 0 || p <= 0) continue;
    const gc = { type: "LineString", coordinates: d3.range(0, 101).map((i) => d3.geoInterpolate(k.yol[0], k.yol[k.yol.length - 1])(i / 100)) };
    const pts = gc.coordinates.map(xy); const y = kirpYol(pts, p);
    g.save(); g.globalAlpha = a; g.lineCap = "round"; g.beginPath(); y.forEach((q, i) => (i ? g.lineTo(...q) : g.moveTo(...q))); g.strokeStyle = "rgba(0,0,0,0.35)"; g.lineWidth = px(6); g.stroke();
    g.setLineDash([px(14), px(9)]); g.strokeStyle = renk(k.rol || "ana").kontur; g.lineWidth = px(3.2); g.stroke(); g.restore(); }
  // nabız halkaları
  for (const k of (hareketli ? KATMAN : []).filter((k) => k.tip === "nabiz")) { const a = gor(k, t); if (a <= 0) continue; const q = xy(k.konum), r = renk(k.rol || "ana");
    for (let j = 0; j < 2; j++) { const f = ((t - (k.t?.[0] ?? 0)) / 2.4 + j / 2) % 1; if (f < 0) continue; g.beginPath(); g.arc(q[0], q[1], px(6 + 56 * eoq(f)), 0, 7); g.strokeStyle = hex(r.kontur, Math.pow(1 - f, 1.6) * 0.85 * a); g.lineWidth = px(1.6); g.stroke(); }
    g.beginPath(); g.arc(q[0], q[1], px(4), 0, 7); g.fillStyle = hex(r.kontur, a); g.fill(); }
}

// ---------------- ekran katmanı: etiketler, birlikler, marka ----------------
const ek = document.getElementById("ek"); ek.width = PW; ek.height = PH; const e = ek.getContext("2d");
const son2 = document.getElementById("son"); son2.width = W; son2.height = H; const s2 = son2.getContext("2d");
const ara1 = tuval(Math.round(PW / 2), Math.round(PH / 2)), a1 = ara1.getContext("2d");
function ekrana(lon, lat, h = 0.002) {
  const p = v3(lon, lat, 1 + h), q = p.clone().project(kam);
  const N = p.clone().normalize(), Vv = kam.position.clone().sub(p).normalize();
  return { x: (q.x * 0.5 + 0.5) * PW, y: (-q.y * 0.5 + 0.5) * PH, yuz: N.dot(Vv), z: q.z };
}
function harf(g, metin, x, y, aralik) { // harf aralıklı metin (letterSpacing desteği yoksa)
  if ("letterSpacing" in g) { g.letterSpacing = `${aralik}px`; g.fillText(metin, x, y); g.letterSpacing = "0px"; return; }
  g.fillText(metin, x, y);
}
const T = M.yazi; // marka tipografisi
const fpx = (oran) => Math.round(oran * kisa * SS); // kısa kenara oranla piksel
function golgeli(g, fn, bulan = 10) { g.save(); g.shadowColor = "rgba(0,8,20,0.85)"; g.shadowBlur = bulan * SS; fn(); g.restore(); fn(); }
// anlatım grafiği stili (grafik.js); stilde olmayan parça aşağıdaki belgesel çizimine düşer
const G = grafikKur({ M, T, SS, W, H, dil: S.dil, hex, renk, fpx, eo, eoq, eio, ara, sinir, kirpYol, yolUzun, rng, desen, tuval });

function birlikCiz(g, x, y, k, a) {
  const r = renk(k.rol || "dost"), b = fpx(0.034), w = b * 1.5, h = b;
  g.save(); g.globalAlpha = a; g.translate(x, y); g.lineWidth = Math.max(2, b * 0.08); g.strokeStyle = "#fff"; g.fillStyle = r.dolgu;
  g.shadowColor = "rgba(0,0,0,0.6)"; g.shadowBlur = b * 0.4; g.shadowOffsetY = b * 0.1;
  g.beginPath();
  if (k.taraf === "dusman") { g.moveTo(0, -h * 0.85); g.lineTo(w * 0.62, 0); g.lineTo(0, h * 0.85); g.lineTo(-w * 0.62, 0); g.closePath(); }
  else g.rect(-w / 2, -h / 2, w, h);
  g.fill(); g.shadowColor = "transparent"; g.stroke();
  g.beginPath(); const iw = w * 0.32, ih = h * 0.26;
  const s = k.sembol || "piyade";
  if (s === "piyade" || s === "mekanize") { g.moveTo(-w / 2 + 3, -h / 2 + 3); g.lineTo(w / 2 - 3, h / 2 - 3); g.moveTo(w / 2 - 3, -h / 2 + 3); g.lineTo(-w / 2 + 3, h / 2 - 3); }
  if (s === "zirhli" || s === "mekanize") { g.ellipse(0, 0, iw, ih, 0, 0, 7); }
  if (s === "topcu") { g.moveTo(b * 0.12, 0); g.arc(0, 0, b * 0.12, 0, 7); g.fillStyle = "#fff"; g.fill(); }
  if (s === "suvari") { g.moveTo(-w / 2 + 3, h / 2 - 3); g.lineTo(w / 2 - 3, -h / 2 + 3); }
  g.stroke();
  if (k.kademe) { g.fillStyle = "#fff"; g.font = `700 ${Math.round(b * 0.42)}px "Barlow Condensed"`; g.textAlign = "center"; g.textBaseline = "bottom"; g.fillText(k.kademe, 0, -h / 2 - b * 0.08); }
  if (k.etiket) { g.font = `600 ${Math.round(b * 0.42)}px "Inter Tight"`; g.textAlign = "center"; g.textBaseline = "top"; golgeli(g, () => { g.fillStyle = "#fff"; g.fillText(k.etiket, 0, h / 2 + b * 0.14); }, 6); }
  g.restore();
}
function noktaYol(yol, p) { const k = kirpYol(yol, p); return k[k.length - 1]; }

function etiketler(t, k) {
  const kutular = [];
  const yer_ = (x, y, w, h) => { for (const b of kutular) if (x < b[0] + b[2] && x + w > b[0] && y < b[1] + b[3] && y + h > b[1]) return false; kutular.push([x, y, w, h]); return true; };
  const ol = [...KATMAN].filter((q) => q.etiket).sort((a, b) => (b.oncelik ?? 0) - (a.oncelik ?? 0));
  for (const q of ol) {
    const a0 = gor(q, t, 0.7, 0.5); if (a0 <= 0) continue;
    const [lo, la] = q.etiketKonum || q.konum || [0, 0]; const p = ekrana(lo, la); if (p.z > 1) continue;
    const a = a0 * sinir((p.yuz - 0.12) / 0.25); if (a <= 0.01) continue;
    if (q.tip === "ulke" || q.tip === "bolge") {
      // boyut: ülkenin ekrandaki genişliği
      const gk = q.genislik || 6; const p2 = ekrana(lo + gk / 2, la), p1 = ekrana(lo - gk / 2, la); const gen = Math.hypot(p2.x - p1.x, p2.y - p1.y);
      const boy = sinir(gen * 0.085, fpx(0.016), fpx(0.05)); if (gen < fpx(0.06) && !q.rol) continue;
      if (G.ulkeEtiket) { const t0 = q.t?.[0] ?? 0; G.ulkeEtiket(e, { met: q.etiket, x: p.x, y: p.y, boy, a, r: q.rol ? renk(q.rol) : null, gir: ara(t, t0 + 0.5, t0 + 0.5 + (G.etiketSure ?? 1.1)), yer_ }); continue; }
      e.font = `${T.ulke.agirlik} ${boy}px "${T.ulke.aile}"`; const met = q.etiket.toLocaleUpperCase(S.dil === "de" ? "de" : "tr");
      const gir = eo(ara(t, (q.t?.[0] ?? 0) + 0.5, (q.t?.[0] ?? 0) + 1.6)); const aralik = boy * T.ulke.aralik * (1 + 1.4 * (1 - gir)); const w = e.measureText(met).width + aralik * met.length, h = boy;
      if (!yer_(p.x - w / 2, p.y - h / 2, w, h)) continue;
      e.save(); e.globalAlpha = a; e.textAlign = "center"; e.textBaseline = "middle";
      golgeli(e, () => { e.fillStyle = q.rol ? M.etiketVurgu : M.etiket; harf(e, met, p.x + aralik / 2, p.y, aralik); }, 12); e.restore();
    } else if (q.tip === "sehir" || q.tip === "nabiz" || q.tip === "birlik_yok") {
      const boy = fpx(T.sehir.boy * (q.onem === 1 ? 1.15 : 1));
      if (G.sehir) { const t0 = q.t?.[0] ?? 0; G.sehir(e, { met: q.etiket, x: p.x, y: p.y, boy, a, onem: q.onem, yon: q.yon ?? 1, rk: q.rol ? renk(q.rol).kontur : undefined, gir: ara(t, t0, t0 + (G.etiketSure ?? 1)), yer_, konum: q.konum }); continue; }
      e.font = `${T.sehir.agirlik} ${boy}px "${T.sehir.aile}"`;
      const w = e.measureText(q.etiket).width; const sag = (q.yon ?? 1) > 0;
      const x = sag ? p.x + boy * 0.75 : p.x - boy * 0.75 - w;
      if (!yer_(Math.min(p.x, x) - 4, p.y - boy * 0.6, w + boy, boy * 1.2)) continue;
      e.save(); e.globalAlpha = a; e.textBaseline = "middle";
      e.beginPath(); if (q.onem === 1) e.rect(p.x - boy * 0.24, p.y - boy * 0.24, boy * 0.48, boy * 0.48); else e.arc(p.x, p.y, boy * 0.2, 0, 7);
      e.fillStyle = "#fff"; e.shadowColor = "rgba(0,0,0,0.8)"; e.shadowBlur = 6 * SS; e.fill(); e.shadowBlur = 0; e.lineWidth = boy * 0.08; e.strokeStyle = renk(q.rol || "notr").kontur; e.stroke();
      golgeli(e, () => { e.fillStyle = M.etiket; e.fillText(q.etiket, x, p.y); }, 10); e.restore();
    } else if (q.tip === "deniz") {
      const boy = fpx(T.deniz.boy); e.font = `${T.deniz.italik === false ? "" : "italic "}${T.deniz.agirlik} ${boy}px "${T.deniz.aile}"`; const aralik = boy * T.deniz.aralik;
      const w = e.measureText(q.etiket).width + aralik * q.etiket.length; if (!yer_(p.x - w / 2, p.y - boy / 2, w, boy)) continue;
      e.save(); e.globalAlpha = a * 0.92; e.textAlign = "center"; e.textBaseline = "middle"; e.fillStyle = M.deniz; harf(e, q.etiket, p.x + aralik / 2, p.y, aralik); e.restore();
    }
  }
  // birlikler (yol boyunca ilerler)
  for (const q of KATMAN.filter((q) => q.tip === "birlik")) {
    const a0 = gor(q, t, 0.5, 0.5); if (a0 <= 0) continue; let lo, la;
    if (q.yol) { const [t0, t1] = q.hareket || q.t || [0, 1]; [lo, la] = noktaYolGeo(q.yol, eio(ara(t, t0, t1))); } else [lo, la] = q.konum;
    const p = ekrana(lo, la); const a = a0 * sinir((p.yuz - 0.12) / 0.25); if (a <= 0.01) continue;
    if (q.yol) { const [t0, t1] = q.hareket || q.t || [0, 1]; const pr = eio(ara(t, t0, t1)); if (pr > 0) { const iz = kirpYol(q.yol.map((z) => [z[0], z[1]]), pr);
      e.save(); e.globalAlpha = a * 0.8; e.setLineDash([3 * SS, 7 * SS]); e.lineCap = "round"; e.strokeStyle = renk(q.rol || "dost").kontur; e.lineWidth = 2.2 * SS; e.beginPath();
      d3.range(0, 41).forEach((i) => { const z = kirpYol(iz, i / 40), zz = z[z.length - 1], sp = ekrana(zz[0], zz[1]); i ? e.lineTo(sp.x, sp.y) : e.moveTo(sp.x, sp.y); }); e.stroke(); e.restore(); } }
    const gi = ara(t, (q.t?.[0] ?? 0), (q.t?.[0] ?? 0) + 0.7), geri = 1 + 2.2 * Math.pow(gi - 1, 3) + 1.2 * Math.pow(gi - 1, 2);
    e.save(); e.translate(p.x, p.y); e.scale(geri, geri); (G.birlik || birlikCiz)(e, 0, 0, q, a * eo(gi)); e.restore();
  }
}
function kartCiz(t) {
  for (const q of KATMAN.filter((q) => q.tip === "kart")) {
    const t0 = q.t?.[0] ?? 0, a0 = gor(q, t, 0.01, 0.5); if (a0 <= 0) continue;
    const p = ekrana(...q.konum); const a = a0 * sinir((p.yuz - 0.12) / 0.25); if (a <= 0.01) continue;
    if (G.kart) { G.kart(e, q, p, t, a); continue; }
    const dikey = H > W, yonx = (q.yon ?? 1) * (dikey ? 0.6 : 1), b = fpx(0.019), uzun = fpx(dikey ? 0.1 : 0.085);
    const c1 = eio(ara(t, t0, t0 + 0.55)), c2 = eoq(ara(t, t0 + 0.4, t0 + 1.05)), c3 = eo(ara(t, t0 + 0.5, t0 + 2.2));
    const ex = p.x + yonx * uzun * 0.7, ey = p.y - uzun, kx = ex + yonx * uzun * 0.45;
    e.save(); e.globalAlpha = a; const r = renk(q.rol || "ana");
    e.fillStyle = "#fff"; e.beginPath(); e.arc(p.x, p.y, b * 0.28 * eo(ara(t, t0, t0 + 0.3)), 0, 7); e.fill();
    e.strokeStyle = "rgba(255,255,255,0.85)"; e.lineWidth = Math.max(1.5, b * 0.08); e.beginPath(); e.moveTo(p.x, p.y);
    const L1 = Math.hypot(ex - p.x, ey - p.y), L2 = Math.abs(kx - ex), top = (L1 + L2) * c1;
    if (top <= L1) e.lineTo(p.x + (ex - p.x) * top / L1, p.y + (ey - p.y) * top / L1); else { e.lineTo(ex, ey); e.lineTo(ex + (kx - ex) * (top - L1) / L2, ey); } e.stroke();
    if (c2 > 0) {
      const deger = q.deger != null ? (q.deger * c3).toLocaleString(S.dil === "de" ? "de-DE" : "tr-TR", { maximumFractionDigits: q.ondalik ?? 0 }) : "";
      e.font = `700 ${Math.round(b * 2.4)}px "Barlow Condensed"`; const sw = e.measureText((q.onek || "") + (q.deger != null ? (q.deger).toLocaleString("tr-TR", { maximumFractionDigits: q.ondalik ?? 0 }) : "") + (q.birim ? " " + q.birim : "")).width;
      e.font = `700 ${b}px "Inter Tight"`; const bw = e.measureText((q.baslik || "").toLocaleUpperCase("tr")).width + b * 0.2 * (q.baslik || "").length;
      e.font = `500 ${Math.round(b * 0.95)}px "Inter Tight"`; const aw = e.measureText(q.alt || "").width;
      const pad = b * 0.9, w = Math.max(sw, bw, aw) + pad * 2, h = b * (q.alt ? 5.6 : 4.4), gk = (dikey ? M.guvenli.dikey[0] : M.guvenli.yatay[0]) * W * SS, x = sinir(yonx > 0 ? kx : kx - w, gk, W * SS - gk - w), y = ey - h / 2; // güvenli alana kıstır
      e.save(); e.beginPath(); e.rect(yonx > 0 ? x : x + w * (1 - c2), y, w * c2, h); e.clip();
      e.fillStyle = M.cipZemin; e.fillRect(x, y, w, h); e.fillStyle = r.kontur; e.fillRect(yonx > 0 ? x : x + w - Math.max(3, b * 0.16), y, Math.max(3, b * 0.16), h);
      e.globalAlpha = a * eo(ara(t, t0 + 0.6, t0 + 1.2)); e.textBaseline = "alphabetic"; e.textAlign = "left";
      e.font = `700 ${b}px "Inter Tight"`; e.fillStyle = r.kontur; harf(e, (q.baslik || "").toLocaleUpperCase("tr"), x + pad, y + pad + b * 0.8, b * 0.2);
      e.font = `700 ${Math.round(b * 2.4)}px "Barlow Condensed"`; e.fillStyle = M.metin; e.fillText((q.onek || "") + deger + (q.birim ? " " + q.birim : ""), x + pad, y + pad + b * 3.3);
      if (q.alt) { e.font = `500 ${Math.round(b * 0.95)}px "Inter Tight"`; e.fillStyle = M.metin2; e.fillText(q.alt, x + pad, y + pad + b * 4.55); }
      e.restore();
    }
    e.restore();
  }
}
function noktaYolGeo(yol, p) { const pts = yol.map((q) => [q[0], q[1]]); const k = kirpYol(pts, p); return k[k.length - 1]; }

// yol yazısı: metin coğrafi bir yol boyunca harf harf dizilir (ok, cephe ya da sınır boyunca anlatım); yön soldan sağa okunur
function yolYaziCiz(t) {
  for (const q of KATMAN.filter((q) => q.tip === "yolyazi")) {
    const a0 = gor(q, t, 0.01, 0.5); if (a0 <= 0) continue;
    const ps = d3.range(0, 49).map((i) => { const z = noktaYolGeo(q.yol, i / 48); return ekrana(z[0], z[1]); }); if (ps.some((p) => p.z > 1)) continue;
    const a = a0 * sinir((Math.min(...ps.map((p) => p.yuz)) - 0.12) / 0.25); if (a <= 0.01) continue;
    let P = ps.map((p) => [p.x, p.y]); for (let k = 0; k < 3; k++) P = P.map((p, i) => (i && i < P.length - 1 ? [(P[i - 1][0] + 2 * p[0] + P[i + 1][0]) / 4, (P[i - 1][1] + 2 * p[1] + P[i + 1][1]) / 4] : p));
    if (P[P.length - 1][0] < P[0][0]) P.reverse();
    const st = G.yolYazi || { font: (b) => `600 ${b}px "Inter Tight"`, renk: "251,247,239", golge: "rgba(0,8,20,0.85)" };
    const boy = fpx(q.boy ?? 0.03), t0 = q.t?.[0] ?? 0, f = ara(t, t0, t0 + (q.sure ?? 1.4));
    e.save(); e.globalAlpha = a; e.font = st.font(boy); e.textAlign = "center"; e.textBaseline = "middle"; e.shadowColor = st.golge; e.shadowBlur = 8 * SS;
    const met = q.metin, ar = boy * (q.aralik ?? 0.06), ws = [...met].map((c) => e.measureText(c).width + ar), top = ws.reduce((x, y) => x + y, 0);
    const L = [0]; for (let i = 1; i < P.length; i++) L.push(L[i - 1] + Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]));
    const n = met.length, ofs = boy * (q.ofset ?? -0.9), bos = Math.max(0, L[L.length - 1] - top);
    const dz = H > W, gk = M.guvenli[dz ? "dikey" : "yatay"], kx0 = gk[0] * W * SS + boy * 0.6, kx1 = W * SS - kx0, ky0 = gk[1] * H * SS + boy * 0.6, ky1 = H * SS - gk[2] * H * SS - boy * 0.6;
    const dizi = (hz) => { let s = bos * hz; return [...met].map((c, i) => { const m = s + ws[i] / 2; s += ws[i]; let j = 1; while (j < L.length - 1 && L[j] < m) j++;
      const u = sinir((m - L[j - 1]) / ((L[j] - L[j - 1]) || 1)), an = Math.atan2(P[j][1] - P[j - 1][1], P[j][0] - P[j - 1][0]);
      return { c, an, x: P[j - 1][0] + (P[j][0] - P[j - 1][0]) * u - Math.sin(an) * ofs, y: P[j - 1][1] + (P[j][1] - P[j - 1][1]) * u + Math.cos(an) * ofs }; }); };
    const icinde = (d) => d.every((g_) => g_.x > kx0 && g_.x < kx1 && g_.y > ky0 && g_.y < ky1); // güvenli alan: yazı yarıda kesilmez
    const h0 = q.hiza ?? 0.5; let gl = null; for (let k = 0; k <= 100 && !gl; k++) for (const hz of [h0 - k * 0.01, h0 + k * 0.01]) if (hz >= 0 && hz <= 1) { const d = dizi(hz); if (icinde(d)) { gl = d; break; } }
    if (!gl) { e.restore(); continue; }
    gl.forEach((g_, i) => { const al = sinir((f * (n + 8) - i) / 8); if (al <= 0) return;
      e.save(); e.translate(g_.x, g_.y); e.rotate(g_.an); e.fillStyle = `rgba(${st.renk},${al})`; e.fillText(g_.c, 0, 0); e.restore(); });
    e.restore();
  }
}
// anlatım notu: ekranda kısa anlatı cümlesi (alt şerit ya da bölüm kartı); stil yoksa sade kutu
const ROMA = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
function notCiz(t) {
  KATMAN.filter((q) => q.tip === "not").forEach((q, i) => { const [t0, t1] = q.t || [0, 3]; if (t < t0) return; const out = 1 - ara(t, t1 - 0.45, t1); if (out <= 0) return;
    const no = ROMA[(q.no ?? i + 1) - 1] || String(q.no ?? i + 1);
    if (G.not) { G.not(e, q, t - t0, out, no); return; }
    const dikey = H > W, gx = (dikey ? M.guvenli.dikey[0] : M.guvenli.yatay[0]) * W * SS, alt = H * SS - (dikey ? M.guvenli.dikey[2] : M.guvenli.yatay[2]) * H * SS;
    const b = fpx(0.034); e.save(); e.globalAlpha = out * eo(ara(t, t0, t0 + 0.5)); e.font = `600 ${b}px "Inter Tight"`; const w = e.measureText(q.metin).width + b * 1.6;
    e.fillStyle = M.cipZemin; e.fillRect(gx, alt - b * 2.2, w, b * 2); e.fillStyle = M.metin; e.textBaseline = "middle"; e.fillText(q.metin, gx + b * 0.8, alt - b * 1.2); e.restore(); });
}

// marka yazıları (ekran uzayı, güvenli alan içinde)
function markaCiz(t) {
  const Y = S.yazi || {}, g = e, dikey = H > W;
  const gx = (dikey ? M.guvenli.dikey[0] : M.guvenli.yatay[0]) * W * SS, ust = (dikey ? M.guvenli.dikey[1] : M.guvenli.yatay[1]) * H * SS, alt = H * SS - (dikey ? M.guvenli.dikey[2] : M.guvenli.yatay[2]) * H * SS;
  const vurgu = M.roller.ana.kontur;
  // başlık bloğu
  let baslikH = null;
  if (Y.baslik && G.baslik) { const [a, b] = Y.baslikZaman || [0.4, S.sure - 0.6]; baslikH = G.baslik(e, { Y, t, a, b, x: gx, ust, dikey, vurgu }) ?? null; }
  else if (Y.baslik) {
    const [a, b] = Y.baslikZaman || [0.4, S.sure - 0.6]; const g1 = eoq(ara(t, a, a + 0.9)), g2 = 1 - ara(t, b - 0.5, b); const al = Math.min(g1, g2);
    if (al > 0) {
      g.save(); g.globalAlpha = al; g.textBaseline = "alphabetic";
      const kb = fpx(T.ust.boy), bb = fpx(dikey ? T.baslik.boy * 1.05 : T.baslik.boy), ab = fpx(T.alt.boy);
      let y = ust + kb; const x = gx;
      // ince vurgu çizgisi soldan büyür
      g.fillStyle = vurgu; g.fillRect(x, y - kb * 1.9, kb * 2.2 * eoq(ara(t, a, a + 0.7)), Math.max(2, kb * 0.14));
      if (Y.ust) { g.font = `${T.ust.agirlik} ${kb}px "${T.ust.aile}"`; g.fillStyle = vurgu; harf(g, Y.ust.toLocaleUpperCase("tr"), x, y, kb * T.ust.aralik); }
      y += bb * 1.12; const maske = eoq(ara(t, a + 0.1, a + 1.0));
      g.save(); g.beginPath(); g.rect(x - 10, y - bb * 1.1, W * SS, bb * 1.35); g.clip();
      g.font = `${T.baslik.agirlik} ${bb}px "${T.baslik.aile}"`; golgeli(g, () => { g.fillStyle = M.metin; harf(g, Y.baslik, x, y + bb * 1.1 * (1 - maske), bb * T.baslik.aralik); }, 16); g.restore();
      if (Y.alt) { y += ab * 1.7; g.font = `${T.alt.agirlik} ${ab}px "${T.alt.aile}"`; g.globalAlpha = al * eo(ara(t, a + 0.45, a + 1.2)); golgeli(g, () => { g.fillStyle = M.metin2; g.fillText(Y.alt, x, y); }, 10); }
      g.restore();
    }
  }
  // tarih damgası (sağ üst; 9:16'da başlığın altına değil sağ üst köşe)
  if (Y.tarih) {
    let tx = null; for (const d of [].concat(Y.tarih)) if (typeof d === "string") tx = d; else if (t >= d.t) tx = d.metin;
    if (tx) { const db = fpx(T.tarih.boy); g.save(); g.font = `${T.tarih.agirlik} ${db}px "${T.tarih.aile}"`; g.textAlign = "right"; g.textBaseline = "alphabetic";
      g.globalAlpha = eo(ara(t, 0.6, 1.4)); g.textAlign = dikey ? "left" : "right"; const x = dikey ? gx : W * SS - gx, y = dikey ? (baslikH != null ? ust + baslikH + db * 1.4 : ust + fpx(T.ust.boy) + fpx(T.baslik.boy * 1.05) * 1.12 + fpx(T.alt.boy) * 1.7 + db * 1.25) : ust + db * 0.9;
      golgeli(g, () => { g.fillStyle = M.metin; harf(g, tx, x, y, db * T.tarih.aralik); }, 12);
      g.fillStyle = vurgu; g.fillRect(dikey ? x : x - db * 1.2, y + db * 0.22, db * 1.2, Math.max(2, db * 0.06)); g.restore(); }
  }
  // konum çipi (sol alt): yer adı + koordinat
  if (Y.konum) {
    const [a, b] = Y.konumZaman || [S.sure * 0.45, S.sure - 0.4]; const al = Math.min(eo(ara(t, a, a + 0.6)), 1 - ara(t, b - 0.4, b));
    if (al > 0) { const cb = fpx(T.cip.boy); const k = kameraDurum(t), [lo, la] = lonlat(k.p);
      const koor = `${Math.abs(la).toFixed(2)}°${la >= 0 ? "K" : "G"}  ${Math.abs(lo).toFixed(2)}°${lo >= 0 ? "D" : "B"}`;
      g.save(); g.globalAlpha = al; g.font = `${T.cip.agirlik} ${cb}px "${T.cip.aile}"`; const met = Y.konum.toLocaleUpperCase("tr"); const w1 = g.measureText(met).width + cb * T.cip.aralik * met.length;
      g.font = `500 ${Math.round(cb * 0.82)}px "IBM Plex Mono"`; const w2 = g.measureText(koor).width;
      const pad = cb * 0.7, w = Math.max(w1, w2) + pad * 2, h = cb * 3.1, x = gx, y = alt - h;
      if (G.kutu) G.kutu(g, x, y, w, h, vurgu, eoq(ara(t, a, a + 0.5))); else { g.fillStyle = M.cipZemin; g.fillRect(x, y, w * eoq(ara(t, a, a + 0.5)), h); g.fillStyle = vurgu; g.fillRect(x, y, Math.max(3, cb * 0.16), h); }
      g.fillStyle = M.cipMetin ?? M.metin; g.textBaseline = "alphabetic"; g.font = `${T.cip.agirlik} ${cb}px "${T.cip.aile}"`; harf(g, met, x + pad, y + cb * 1.35, cb * T.cip.aralik);
      g.fillStyle = M.cipMetin2 ?? M.metin2; g.font = `500 ${Math.round(cb * 0.82)}px "IBM Plex Mono"`; g.fillText(koor, x + pad, y + cb * 2.55); g.restore(); }
  }
  // lejant (sağ alt)
  if (Y.lejant && Y.lejant.length) {
    const [a] = Y.lejantZaman || [S.sure * 0.3]; const al = eo(ara(t, a, a + 0.7)) * (1 - ara(t, S.sure - 0.5, S.sure));
    if (al > 0) { const lb = fpx(T.lejant.boy), satir = lb * 1.75, pad = lb * 0.9; g.save(); g.font = `${T.lejant.agirlik} ${lb}px "${T.lejant.aile}"`;
      const w = Math.max(...Y.lejant.map((l) => g.measureText(l.ad).width)) + lb * 2.6 + pad * 2, h = satir * Y.lejant.length + pad * 1.2;
      const x = W * SS - gx - w, y = alt - h; g.globalAlpha = al; if (G.kutu) G.kutu(g, x, y, w, h, vurgu, 1); else { g.fillStyle = M.cipZemin; g.fillRect(x, y, w, h); }
      Y.lejant.forEach((l, i) => { const yy = y + pad * 0.6 + satir * i + satir / 2, r = renk(l.rol);
        g.globalAlpha = al * eo(ara(t, a + 0.15 * i, a + 0.15 * i + 0.6));
        if (l.desen === "tarama") { g.fillStyle = desen(g, r.dolgu, 45, lb * 0.35, lb * 0.12); } else g.fillStyle = r.dolgu;
        g.fillRect(x + pad, yy - lb * 0.45, lb * 1.4, lb * 0.9); g.strokeStyle = r.kontur; g.lineWidth = Math.max(1, lb * 0.06); g.strokeRect(x + pad, yy - lb * 0.45, lb * 1.4, lb * 0.9);
        g.fillStyle = M.cipMetin ?? M.metin; g.textBaseline = "middle"; g.fillText(l.ad, x + pad + lb * 2.1, yy); });
      g.restore(); }
  }
  // kaynak / künye (en alt, küçük)
  if (Y.kaynak) { const kb = fpx(T.kaynak.boy); g.save(); g.globalAlpha = 0.75 * eo(ara(t, 1, 2)); g.font = `${T.kaynak.agirlik} ${kb}px "${T.kaynak.aile}"`;
    g.fillStyle = M.metin2; g.textBaseline = "alphabetic"; g.textAlign = dikey ? "left" : "right"; const y = dikey ? H * SS * 0.045 : H * SS - kb * 1.4;
    g.fillText(Y.kaynak, dikey ? gx : W * SS - gx, Math.max(kb * 1.5, y)); g.restore(); }
}

// ---------------- kare ----------------
window.ciz = async (t, no = 0) => {
  G.zaman = t; const k = kameraKur(t); isikKur(t, k);
  // katman tuvallerinin çözünürlüğü: ekran pikseli başına tuval pikseli
  const yerGen = k.alt * GENIS * 6371, kmPx = yerGen / W; // ekran pikseli başına km (yaklaşık, merkezde)
  const kmW = 40075 / ustW.width, latc = (BK[1] + BK[3]) / 2, kmR = (BK[2] - BK[0]) * 111.32 * Math.cos(latc * D2R) / ustR.width;
  const olcW = kmPx / kmW, olcR = kmPx / kmR;
  const anahtar = (o) => [Math.round(o * 20), ...KATMAN.map((q) => (q.t ? Math.round(sinir((t - q.t[0]) * 30, -1, 9999)) : 0) * (t < (q.t?.[1] ?? 1e9) + 1 ? 1 : 0))].join(",");
  const hW = k.alt > 1.2; const aw = hW ? anahtar(olcW) : "duragan" + Math.round(olcW * 20) + KATMAN.filter((q) => q.f).map((q) => Math.round(gor(q, t, 0.8, 0.6) * 30)).join(","), ar = anahtar(olcR);
  const _t0 = performance.now();
  if (aw !== sonAnahtar.W) { katmanCiz(ustW, null, t, olcW, true, hW); ustWt.needsUpdate = true; sonAnahtar.W = aw; }
  if (ar !== sonAnahtar.R) { katmanCiz(ustR, BK, t, olcR, false); ustRt.needsUpdate = true; sonAnahtar.R = ar; }
  const _t1 = performance.now();
  son.uniforms.tohum.value = (no % 97) * 1.37;
  composer.render(); renderer.getContext().finish();
  const _t2 = performance.now();
  e.clearRect(0, 0, PW, PH); etiketler(t, k); yolYaziCiz(t); kartCiz(t); markaCiz(t); notCiz(t);
  // birleştir ve kutu filtresiyle W×H'ye indir (SS=2 için tam yarıya: temiz kenar)
  a1.clearRect(0, 0, ara1.width, ara1.height); a1.imageSmoothingQuality = "high";
  a1.drawImage(cv, 0, 0, ara1.width, ara1.height); a1.drawImage(ek, 0, 0, ara1.width, ara1.height);
  s2.imageSmoothingQuality = "high"; s2.drawImage(ara1, 0, 0, W, H);
  const _t3 = performance.now(); const url = son2.toDataURL("image/png");
  window.__sure = [_t1 - _t0, _t2 - _t1, _t3 - _t2, performance.now() - _t3].map(Math.round);
  return url;
};
window.hazir = true;

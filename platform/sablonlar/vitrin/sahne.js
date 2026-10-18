// 3D ürün vitrini: ürün stüdyo ışığında döner, özellikleri sırayla belirir, marka ve çağrıyla biter.
// Her kare t'nin saf fonksiyonu: window.kare(t) sahneyi kurar, çizer, yazıları üstüne basar ve PNG (base64) döndürür.
// Ayarlar vitrin.py'den window.VITRIN olarak gelir (renkler marka.json'dan, zamanlar müzik ızgarasına oturtulmuş).
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const A = window.VITRIN;
const { W, H } = A;
const R = A.renk;

// ---------- yardımcılar ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, p) => a + (b - a) * p;
const prog = (t, t0, d) => clamp((t - t0) / d);
const outCubic = p => 1 - (1 - p) ** 3;
const inOutCubic = p => (p < .5 ? 4 * p ** 3 : 1 - (-2 * p + 2) ** 3 / 2);
const outBack = (p, s = 1.6) => { p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2; };
const smooth = p => p * p * (3 - 2 * p);
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
const D2R = Math.PI / 180;
const renk = h => new THREE.Color(h);
const karis = (a, b, p) => renk(a).lerp(renk(b), p);
const hex = c => '#' + c.getHexString();

// ---------- yerleşim: dikeyde ürün üstte, yazı altta; yatayda ürün solda, yazı sağda ----------
const DIKEY = W / H < 1;
const URUN_EKRAN = DIKEY ? { x: 0.5, y: W / H > 0.7 ? 0.42 : 0.40 } : { x: 0.36, y: 0.5 };
const U = Math.min(W, H) / 1080; // yazı ölçeği

// ---------- renderer ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.outputColorSpace = THREE.SRGBColorSpace;
// kitap kapağı bir baskı: ACES renkleri kaydırır, Neutral tonları korur
renderer.toneMapping = A.urun.tur === 'kitap' && !A.urun.model ? THREE.NeutralToneMapping : THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.35;

// en dar görüş açısı 30°: her oranda aynı mesafe ürünü aynı büyüklükte çerçeveler
const ASPECT = W / H, MIN_FOV = 30;
const vfov = ASPECT >= 1 ? MIN_FOV : 2 * Math.atan(Math.tan(MIN_FOV / 2 * D2R) / ASPECT) / D2R;
const camera = new THREE.PerspectiveCamera(vfov, ASPECT, 0.05, 200);
// ürünü ekranın merkezinden kaydır (görüntü kaydırma: perspektif bozulmaz)
camera.setViewOffset(W, H, (0.5 - URUN_EKRAN.x) * W, (0.5 - URUN_EKRAN.y) * H, W, H);
const fitDist = r => r / Math.sin(MIN_FOV / 2 * D2R);

// ---------- stüdyo: degrade fon, kaide, ışıklar ----------
const fonMat = new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, fog: false,
  uniforms: { ust: { value: karis(R.ana, '#000000', 0.55) }, alt: { value: karis(R.ana, R.isik, 0.18) }, isik: { value: 0 } },
  vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ',
  // titreşim (dither): 8 bit çıktıda yumuşak degrade halka halka bantlaşmasın
  fragmentShader: `uniform vec3 ust; uniform vec3 alt; uniform float isik; varying vec3 vP;
    float h12(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    void main(){ float k = smoothstep(-0.15, 0.55, vP.y); vec3 c = mix(alt, ust, k);
      float hale = exp(-pow(length(vP.xy - vec2(0.0, 0.12)) * 2.2, 2.0)); c += alt * hale * (0.35 + 0.5 * isik);
      gl_FragColor = vec4(c, 1.0);\n#include <colorspace_fragment>\n
      gl_FragColor.rgb += (h12(gl_FragCoord.xy) + h12(gl_FragCoord.yx + 7.1) - 1.0) / 255.0; }`,
});
scene.add(new THREE.Mesh(new THREE.SphereGeometry(90, 48, 24), fonMat));
scene.fog = new THREE.Fog(karis(R.ana, '#000000', 0.35), 14, 40);

const zemin = new THREE.Mesh(new THREE.CircleGeometry(60, 64),
  new THREE.MeshStandardMaterial({ color: karis(R.ana, '#000000', 0.15), roughness: 0.9, metalness: 0.0, envMapIntensity: 0.2 }));
zemin.rotation.x = -Math.PI / 2; zemin.position.y = -0.36; zemin.receiveShadow = true; scene.add(zemin);

const KAIDE_R = 2.1;
const kaide = new THREE.Mesh(new THREE.CylinderGeometry(KAIDE_R, KAIDE_R + 0.05, 0.36, 96),
  new THREE.MeshPhysicalMaterial({ color: karis(R.ana, R.anaUstu, 0.12), roughness: 0.45, clearcoat: 0.6, clearcoatRoughness: 0.3, envMapIntensity: 0.35 }));
kaide.position.y = -0.18; kaide.receiveShadow = true; kaide.castShadow = true; scene.add(kaide);
const halkaMat = new THREE.MeshBasicMaterial({ color: renk(R.vurgu), transparent: true, opacity: 0, toneMapped: false });
const halka = new THREE.Mesh(new THREE.TorusGeometry(KAIDE_R + 0.03, 0.018, 8, 160), halkaMat);
halka.rotation.x = Math.PI / 2; halka.position.y = 0.0; scene.add(halka);

const hemi = new THREE.HemisphereLight(renk(R.anaUstu), renk(R.ana), 0.35);
scene.add(hemi);
const anahtar = new THREE.SpotLight(renk(R.isik), 0, 30, 28 * D2R, 0.65, 1.2);
anahtar.position.set(-4.5, 7.5, 6.5); anahtar.target.position.set(0, 1.4, 0);
anahtar.castShadow = true; anahtar.shadow.mapSize.set(1024, 1024); anahtar.shadow.bias = -0.0004; anahtar.shadow.radius = 5;
scene.add(anahtar, anahtar.target);
const kontur = new THREE.DirectionalLight(renk(R.anaUstu), 0); // arkadan kenar ışığı
kontur.position.set(5, 5, -6); scene.add(kontur);
const kontur2 = new THREE.DirectionalLight(renk(R.isik), 0);
kontur2.position.set(-6, 3, -5); scene.add(kontur2);
const tarama = new THREE.PointLight('#ffffff', 0, 6, 1.6); // ürünün önünden geçen parlama
scene.add(tarama);

// toz/buhar zerreleri
const zerre = (() => {
  const r = rng(11), n = 90, pos = new Float32Array(n * 3), tohum = [];
  for (let i = 0; i < n; i++) tohum.push([lerp(-5, 5, r()), lerp(-0.2, 6, r()), lerp(-4, 2, r()), r() * 6.28, lerp(0.05, 0.18, r())]);
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const x = c.getContext('2d'), gr = x.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = gr; x.fillRect(0, 0, 64, 64);
  const m = new THREE.PointsMaterial({ size: 0.07, map: new THREE.CanvasTexture(c), color: renk(R.isik), transparent: true, opacity: 0.0,
    depthWrite: false, blending: THREE.AdditiveBlending });
  const p = new THREE.Points(g, m); scene.add(p);
  return { p, pos, tohum, m };
})();

// ---------- ürün ----------
const urun = new THREE.Group();
scene.add(urun);
let OLCU = { w: 2.0, h: 3.2, d: 1.1 };
let ODAK = {};

function etiketDokusu(gen, yuk, kenar) {
  // ön yüz baskısı: marka renkleri, logo, ürün adı, alt satır. Çizim ölçüsü yüzün oranında.
  const s = 1024 / Math.max(gen, yuk), cw = Math.round(gen * s), ch = Math.round(yuk * s);
  const c = document.createElement('canvas'); c.width = cw; c.height = ch;
  const x = c.getContext('2d');
  x.fillStyle = A.urun.govde || R.ana; x.fillRect(0, 0, cw, ch);
  const r = rng(3); // ince doku
  for (let i = 0; i < 2600; i++) { x.fillStyle = `rgba(255,255,255,${r() * 0.035})`; x.fillRect(r() * cw, r() * ch, 2, 2); }
  const e = A.urun;
  const lx = cw * 0.12, lw = cw * 0.76, ly = ch * (kenar ? 0.30 : 0.24), lh = ch * 0.52;
  x.fillStyle = R.anaUstu; x.fillRect(lx, ly, lw, lh);
  x.fillStyle = R.vurgu; x.fillRect(lx, ly + lh - ch * 0.035, lw, ch * 0.035);
  x.fillStyle = R.ana; x.textAlign = 'center'; x.textBaseline = 'alphabetic';
  const sig = (metin, boy, ag, y, renk_ = R.ana, aralik = 0) => {
    x.font = `${ag} ${boy}px Vitrin`; x.fillStyle = renk_;
    if ('letterSpacing' in x) x.letterSpacing = `${aralik}px`;
    let b = boy; while (x.measureText(metin).width > lw * 0.86 && b > 8) { b *= 0.95; x.font = `${ag} ${b}px Vitrin`; }
    x.fillText(metin, cw / 2, y);
  };
  if (e.ust) sig(e.ust, cw * 0.05, 500, ly + lh * 0.17, R.ana, cw * 0.012);
  sig(e.etiket, cw * 0.17, 800, ly + lh * 0.47, R.ana, cw * 0.004);
  x.fillStyle = R.vurgu; x.fillRect(cw / 2 - lw * 0.12, ly + lh * 0.56, lw * 0.24, ch * 0.006);
  if (e.alt) sig(e.alt, cw * 0.045, 500, ly + lh * 0.72, R.ana, cw * 0.002);
  if (e.agirlik) sig(e.agirlik, cw * 0.05, 800, ch * 0.92, R.anaUstu, cw * 0.006);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
}

function paketKur() {
  // ayakta duran kahve paketi: altı körüklü, üste doğru incelip kaynak bandında kapanan yastık form
  const { w, h, d } = OLCU;
  const g = new THREE.BoxGeometry(w, h, d, 32, 48, 16);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    let x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const u = y / h + 0.5, nx = x / (w / 2), nz = z / (d / 2);
    const kapan = 1 - 0.93 * smooth(clamp((u - 0.5) / 0.47));  // üste doğru derinlik kapanır
    const yastik = (1 - nx * nx) * Math.sin(Math.PI * clamp(u * 0.98 + 0.02)) * 0.09; // ön/arka yüz şişkinliği
    z = nz * (d / 2) * kapan + Math.sign(nz) * Math.abs(nz) ** 4 * yastik;
    const kenarYuvarla = 1 - 0.06 * Math.abs(nz) ** 2 * (1 - u * 0.6); // köşeler yumuşak
    x *= kenarYuvarla * (1 + 0.015 * Math.sin(Math.PI * u));
    if (u < 0.04) { const k = 1 - u / 0.04; x *= 1 - 0.03 * k; z *= 1 - 0.05 * k; }
    p.setXYZ(i, x, y + h / 2, z);
  }
  g.computeVertexNormals();
  const govde = new THREE.MeshPhysicalMaterial({ color: renk(A.urun.govde || R.ana), roughness: 0.62, clearcoat: 0.25, clearcoatRoughness: 0.5 });
  const on = new THREE.MeshPhysicalMaterial({ map: etiketDokusu(w, h), roughness: 0.5, clearcoat: 0.45, clearcoatRoughness: 0.35 });
  const arka = new THREE.MeshPhysicalMaterial({ map: etiketDokusu(w, h, true), roughness: 0.5, clearcoat: 0.45, clearcoatRoughness: 0.35 });
  const m = new THREE.Mesh(g, [govde, govde, govde, govde, on, arka]); // BoxGeometry yüz sırası: +x -x +y -y +z -z
  m.castShadow = true; m.receiveShadow = true; urun.add(m);
  // üst kaynak bandı (tırtıklı)
  const bant = new THREE.Mesh(new THREE.BoxGeometry(w * 1.0, h * 0.075, 0.07, 1, 24, 1),
    new THREE.MeshPhysicalMaterial({ color: renk(A.urun.govde || R.ana).multiplyScalar(0.92), roughness: 0.55, clearcoat: 0.3 }));
  const bp = bant.geometry.attributes.position; // yatay kaynak çizgileri
  for (let i = 0; i < bp.count; i++) bp.setZ(i, bp.getZ(i) + Math.sign(bp.getZ(i)) * 0.006 * Math.sin(bp.getY(i) * 160));
  bant.geometry.computeVertexNormals();
  bant.position.y = h * 0.985; bant.castShadow = true; urun.add(bant);
  // aroma valfi
  const valf = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.06, 40),
    new THREE.MeshPhysicalMaterial({ color: renk(R.vurgu), roughness: 0.3, metalness: 0.2, clearcoat: 1 }));
  const vy = h * 0.83, vz = zOn(0.25, 0.83) + 0.01;
  const egim = (zOn(0.25, 0.84) - zOn(0.25, 0.82)) / (0.02 * h); // yüzey eğimi: valf yüzeye yaslanır
  valf.rotation.x = Math.atan2(1, -egim); valf.position.set(w * 0.25, vy, vz); urun.add(valf);
  ODAK = { on: [0, h * 0.5, zOn(0, 0.5)], ust: [w * 0.25, vy, vz + 0.02], yan: [w / 2, h * 0.22, 0], alt: [0, h * 0.06, d / 2] };
  function zOn(nx, u) { // ön yüzün (nx, u) noktasındaki z'si (deformasyonla aynı)
    const kapan = 1 - 0.93 * smooth(clamp((u - 0.5) / 0.47));
    return (d / 2) * kapan + (1 - nx * nx) * Math.sin(Math.PI * clamp(u * 0.98 + 0.02)) * 0.09;
  }
}

function kutuKur() {
  const { w, h, d } = OLCU = { w: 2.0, h: 2.8, d: 1.2 };
  const g = new RoundedBoxGeometry(w, h, d, 6, 0.06);
  g.translate(0, h / 2, 0);
  const govde = new THREE.MeshPhysicalMaterial({ color: renk(A.urun.govde || R.ana), roughness: 0.5, clearcoat: 0.5 });
  const m = new THREE.Mesh(g, govde); m.castShadow = true; m.receiveShadow = true; urun.add(m);
  const on = new THREE.Mesh(new THREE.PlaneGeometry(w * 0.98, h * 0.98),
    new THREE.MeshPhysicalMaterial({ map: etiketDokusu(w, h), roughness: 0.45, clearcoat: 0.5 }));
  on.position.set(0, h / 2, d / 2 + 0.002); urun.add(on);
  ODAK = { on: [0, h * 0.5, d / 2], ust: [0, h, 0], yan: [w / 2, h * 0.5, 0], alt: [0, h * 0.08, d / 2] };
}

// ---------- kitap: sert kapaklı, kapak görseli önde, sırt yuvarlak, sayfa bloğu krem; ön kapak sırttan açılır ----------
const KITAP = { kapak: null, yapraklar: [] };
const SAYFA = A.urun.sayfa || '#F3EDE1';

function gorselYukle(yol) {
  return new Promise((ok, red) => new THREE.TextureLoader().load(yol, ok, undefined, () => red(new Error(`kapak yüklenemedi: ${yol}`))));
}

function uretilmisKapak(gen, yuk) {
  // kapak görseli verilmezse marka renkleriyle düz bir kapak: başlık, ince vurgu çizgisi, alt satır
  const s = 1600 / yuk, cw = Math.round(gen * s), ch = 1600;
  const c = document.createElement('canvas'); c.width = cw; c.height = ch;
  const x = c.getContext('2d'), e = A.urun;
  x.fillStyle = e.govde || R.ana; x.fillRect(0, 0, cw, ch);
  x.textAlign = 'center'; x.fillStyle = R.anaUstu;
  const sig = (metin, boy, ag, y, renk_) => {
    if (!metin) return; x.font = `${ag} ${boy}px Vitrin`; x.fillStyle = renk_;
    let b = boy; while (x.measureText(metin).width > cw * 0.8 && b > 8) { b *= 0.95; x.font = `${ag} ${b}px Vitrin`; }
    x.fillText(metin, cw / 2, y);
  };
  sig(e.ust, cw * 0.05, 500, ch * 0.16, R.vurgu);
  sig(e.etiket, cw * 0.14, 800, ch * 0.44, R.anaUstu);
  x.fillStyle = R.vurgu; x.fillRect(cw * 0.42, ch * 0.48, cw * 0.16, ch * 0.006);
  sig(e.alt, cw * 0.045, 500, ch * 0.56, R.anaUstu);
  return new THREE.CanvasTexture(c);
}

function sayfaKenari(boyuna) {
  // sayfa bloğunun kesik kenarı: krem zemin üstünde ince yaprak çizgileri (kalınlık yönünde)
  const c = document.createElement('canvas'); c.width = boyuna ? 64 : 1024; c.height = boyuna ? 1024 : 64;
  const x = c.getContext('2d'); x.fillStyle = SAYFA; x.fillRect(0, 0, c.width, c.height);
  const r = rng(9), n = boyuna ? c.width : c.height;
  for (let i = 0; i < n; i += 2) {
    x.fillStyle = `rgba(90,70,40,${0.05 + r() * 0.07})`;
    if (boyuna) x.fillRect(i, 0, 1, c.height); else x.fillRect(0, i, c.width, 1);
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

function icSayfa(gen, yuk) {
  // kapak açılınca görünen ilk sayfa: başlık ve satır izleri (okunur metin değil, sayfa hissi)
  const s = 1024 / yuk, cw = Math.round(gen * s), ch = 1024;
  const c = document.createElement('canvas'); c.width = cw; c.height = ch;
  const x = c.getContext('2d'); x.fillStyle = SAYFA; x.fillRect(0, 0, cw, ch);
  x.fillStyle = 'rgba(40,32,24,0.78)'; x.fillRect(cw * 0.16, ch * 0.14, cw * 0.46, ch * 0.022);
  x.fillStyle = R.vurgu; x.fillRect(cw * 0.16, ch * 0.185, cw * 0.1, ch * 0.006);
  const r = rng(21);
  for (let y = ch * 0.25; y < ch * 0.88; y += ch * 0.032) {
    if (r() < 0.1) { y += ch * 0.02; continue; } // paragraf boşluğu
    x.fillStyle = 'rgba(40,32,24,0.22)'; x.fillRect(cw * 0.16, y, cw * (0.6 + r() * 0.08), ch * 0.008);
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

async function kitapKur() {
  let doku = null;
  if (A.urun.kapak) doku = await gorselYukle(A.urun.kapak);
  const oran = doku ? doku.image.width / doku.image.height : 0.68;
  const h = 3.1, w = h * oran, d = 0.44, kal = 0.045, tas = 0.04; // kalınlık, kapak taşması
  OLCU = { w, h, d };
  if (!doku) doku = uretilmisKapak(w, h);
  doku.colorSpace = THREE.SRGBColorSpace; doku.anisotropy = 16;
  doku.minFilter = THREE.LinearMipmapLinearFilter; doku.generateMipmaps = true;
  const sirtRenk = A.urun.govde ? renk(A.urun.govde) : kenarRengi(doku);
  const karton = new THREE.MeshPhysicalMaterial({ color: sirtRenk, roughness: 0.55, clearcoat: 0.25, clearcoatRoughness: 0.5 });
  const ic = new THREE.MeshStandardMaterial({ color: renk(SAYFA).multiplyScalar(0.97), roughness: 0.9 });
  const onYuz = new THREE.MeshPhysicalMaterial({ map: doku, roughness: 0.42, clearcoat: 0.35, clearcoatRoughness: 0.4 });
  const sayfaYan = new THREE.MeshStandardMaterial({ map: sayfaKenari(true), roughness: 0.95 });
  const sayfaUst = new THREE.MeshStandardMaterial({ map: sayfaKenari(false), roughness: 0.95 });
  const sayfaOn = new THREE.MeshStandardMaterial({ map: icSayfa(w - tas * 2, h - tas * 2), roughness: 0.92 });
  const kitap = new THREE.Group(); urun.add(kitap);
  const x0 = -w / 2; // sırt çizgisi

  // arka kapak
  const arka = new THREE.Mesh(new RoundedBoxGeometry(w, h, kal, 2, 0.012), karton);
  arka.position.set(0, h / 2, -d / 2 + kal / 2); arka.castShadow = arka.receiveShadow = true; kitap.add(arka);
  // sayfa bloğu (sırttan biraz içeride, kapaklardan taşmaz)
  const bw = w - tas - 0.03, bh = h - tas * 2, bd = d - kal * 2 - 0.004;
  const blok = new THREE.Mesh(new THREE.BoxGeometry(bw, bh, bd), [sayfaYan, karton, sayfaUst, sayfaUst, ic, ic]);
  blok.position.set(x0 + 0.03 + bw / 2, h / 2, 0); blok.castShadow = blok.receiveShadow = true; kitap.add(blok);
  // yuvarlak sırt
  const sirt = new THREE.Mesh(new THREE.CylinderGeometry(d / 2, d / 2, h, 40, 1, true, Math.PI, Math.PI), karton);
  sirt.position.set(x0, h / 2, 0); sirt.scale.set(0.45, 1, 1); sirt.castShadow = true; kitap.add(sirt);

  // ön kapak: sırttan menteşeli; dış yüzde kapak görseli, iç yüzde krem forza
  const mentese = new THREE.Group(); mentese.position.set(x0, 0, d / 2 - kal / 2); kitap.add(mentese);
  const kapak = new THREE.Mesh(new RoundedBoxGeometry(w, h, kal, 2, 0.012), [karton, karton, karton, karton, karton, ic]);
  kapak.position.set(w / 2, h / 2, 0); kapak.castShadow = kapak.receiveShadow = true; mentese.add(kapak);
  const baski = new THREE.Mesh(new THREE.PlaneGeometry(w - 0.012, h - 0.012), onYuz);
  baski.position.set(w / 2, h / 2, kal / 2 + 0.0015); mentese.add(baski);
  KITAP.kapak = mentese;
  // kapakla birlikte hafifçe kalkan birkaç yaprak
  for (let i = 0; i < 1; i++) {
    const y = new THREE.Group(); y.position.set(x0 + 0.03, 0, d / 2 - kal - 0.004 - i * 0.003); kitap.add(y);
    const yp = new THREE.Mesh(new THREE.PlaneGeometry(bw, bh), i === 0
      ? new THREE.MeshStandardMaterial({ map: sayfaOn.map, roughness: 0.92, side: THREE.DoubleSide })
      : new THREE.MeshStandardMaterial({ color: renk(SAYFA), roughness: 0.92, side: THREE.DoubleSide }));
    yp.position.set(bw / 2, h / 2, 0); yp.castShadow = true; y.add(yp); y.visible = false;
    KITAP.yapraklar.push(y);
  }
  ODAK = { on: [0, h * 0.5, d / 2], ust: [0, h, 0], yan: [w / 2, h * 0.5, 0], alt: [0, h * 0.08, d / 2],
           ic: [x0 + 0.03 + bw * 0.5, h * 0.55, d / 2 - kal] };
}

function kenarRengi(doku) {
  // kapak görselinin sol kenarından sırt rengi: kitap sırtı kapakla aynı renkte görünür
  const img = doku.image, c = document.createElement('canvas'); c.width = 8; c.height = 64;
  const x = c.getContext('2d'); x.drawImage(img, 0, 0, Math.max(1, img.width * 0.04), img.height, 0, 0, 8, 64);
  const v = x.getImageData(0, 0, 8, 64).data; let r = 0, g = 0, b = 0;
  for (let i = 0; i < v.length; i += 4) { r += v[i]; g += v[i + 1]; b += v[i + 2]; }
  const n = v.length / 4;
  return new THREE.Color().setRGB(r / n / 255, g / n / 255, b / n / 255, THREE.SRGBColorSpace);
}

function kitapAc(t) {
  // "ic" odaklı özellik boyunca kapak sırttan açılır, yapraklar arkasından kalkar; sonra kapanır
  if (!KITAP.kapak) return;
  let a = 0;
  for (const o of ozellikler) {
    if (o.odak !== 'ic') continue;
    a = Math.max(a, inOutCubic(prog(t, o.bas - 0.2, 0.9)) * (1 - inOutCubic(prog(t, o.son - 0.55, 0.7))));
  }
  KITAP.kapak.rotation.y = -118 * D2R * a;
  for (const [i, y] of KITAP.yapraklar.entries()) {
    const p = clamp(a * 1.25 - i * 0.12); // öndeki yaprak en çok kalkar
    y.visible = p > 0.001; y.rotation.y = -(22 - i * 10) * D2R * smooth(p);
  }
}

async function modelKur(yol) {
  // dışarıdan glTF/GLB: tabanı kaideye oturur, yüksekliği 3.2 birime ölçeklenir
  const gltf = await new GLTFLoader().loadAsync(yol);
  const kok = gltf.scene;
  kok.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  const kutu = new THREE.Box3().setFromObject(kok), boy = new THREE.Vector3(), mer = new THREE.Vector3();
  kutu.getSize(boy); kutu.getCenter(mer);
  const s = (A.urun.model_boy || 3.2) / boy.y;
  kok.scale.setScalar(s);
  kok.position.set(-mer.x * s, -kutu.min.y * s, -mer.z * s);
  urun.add(kok);
  OLCU = { w: boy.x * s, h: boy.y * s, d: boy.z * s };
  const { w, h, d } = OLCU;
  ODAK = { on: [0, h * 0.5, d / 2], ust: [0, h * 0.92, d * 0.3], yan: [w / 2, h * 0.4, 0], alt: [0, h * 0.1, d / 2] };
}

// kahve çekirdekleri (süs)
const cekirdekler = [];
function cekirdekKur() {
  const r = rng(5);
  const g = new THREE.SphereGeometry(0.11, 20, 14); g.scale(1, 0.62, 1.35);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) { const x = p.getX(i), y = p.getY(i); if (y > 0) p.setY(i, y - 0.03 * Math.exp(-(x * x) / 0.0006)); }
  g.computeVertexNormals();
  const m = new THREE.MeshPhysicalMaterial({ color: '#3a2216', roughness: 0.35, clearcoat: 0.7 });
  for (let i = 0; i < 16; i++) {
    const a = r() * Math.PI * 2, rr = lerp(1.35, 1.95, r());
    if (Math.abs(Math.sin(a)) > 0.9 && Math.sin(a) > 0) continue; // önü boş kalsın
    const b = new THREE.Mesh(g, m); b.castShadow = true;
    b.position.set(Math.cos(a) * rr, 0.06, Math.sin(a) * rr * 0.9);
    b.rotation.set(0, r() * 6.28, (r() - 0.5) * 0.4);
    b.userData = { y: 0.06, faz: r() * 6.28, gec: r() * 0.5 };
    scene.add(b); cekirdekler.push(b);
  }
}

// ---------- kamera pozları ----------
// [azimut°, yükseklik°, uzaklık çarpanı, hedef yüksekliği (ürün boyuna oran)]
const POZ = {
  giris: [-28, 4, 1.32, 0.45], acilis: [-12, 9, 1.0, 0.47],
  on: [16, 4, 0.88, 0.50], ust: [-24, 17, 0.86, 0.56], yan: [50, 6, 0.92, 0.46], alt: [-8, 1, 0.90, 0.40],
  ic: [22, 10, 1.42, 0.50], // açık kitap iki kat geniş: kamera geri çekilir
  final: [0, 7, 1.0, 0.47],
};
const ozellikler = A.ozellikler;
const F = A.final;
function kameraPoz(t) {
  const anlar = [[0, POZ.giris], [A.giris_son * 0.85, POZ.acilis]];
  for (const o of ozellikler) anlar.push([o.bas - 0.15, POZ[o.odak] || POZ.on]);
  anlar.push([F.bas - 0.25, POZ.final]);
  let a, b, p;
  if (t < anlar[1][0]) { a = POZ.giris; b = POZ.acilis; p = inOutCubic(prog(t, 0, anlar[1][0])); }
  else {
    let i = 1; while (i + 1 < anlar.length && t >= anlar[i + 1][0]) i++;
    a = anlar[i - 1][1]; b = anlar[i][1]; p = i === 1 ? 1 : inOutCubic(prog(t, anlar[i][0], 0.95));
  }
  const k = a.map((v, i) => lerp(v, b[i], p));
  const kayma = 1.6 * Math.sin(t * 0.35); // her pozda hafif süzülme
  return { az: (k[0] + kayma) * D2R, el: k[1] * D2R, uz: k[2], hy: k[3] };
}

// ---------- yazı katmanı (2B, WebGL karesinin üstüne) ----------
const tuval = document.createElement('canvas'); tuval.width = W; tuval.height = H;
const cx = tuval.getContext('2d');

function yaz(metin, boy, ag, x, y, renk_, hiza = 'left', aralik = 0, azami = Infinity) {
  cx.font = `${ag} ${boy}px Vitrin`; cx.fillStyle = renk_; cx.textAlign = hiza; cx.textBaseline = 'alphabetic';
  cx.shadowColor = 'rgba(0,0,0,0.45)'; cx.shadowBlur = 18 * U; cx.shadowOffsetY = 3 * U; // açık zemin üstünde de okunur
  if ('letterSpacing' in cx) cx.letterSpacing = `${aralik}px`;
  let b = boy; while (cx.measureText(metin).width > azami && b > 8) { b *= 0.96; cx.font = `${ag} ${b}px Vitrin`; }
  cx.fillText(metin, x, y);
  cx.shadowColor = 'transparent';
  return cx.measureText(metin).width;
}

function ekranda(v) { // dünya noktası → piksel
  const p = v.clone().project(camera);
  return [(p.x * 0.5 + 0.5) * W, (-p.y * 0.5 + 0.5) * H];
}

function ozellikCiz(t) {
  for (const [i, o] of ozellikler.entries()) {
    const gir = outCubic(prog(t, o.bas, 0.5)), cik = 1 - inOutCubic(prog(t, o.son - 0.32, 0.32));
    const g = Math.min(gir, cik);
    if (g <= 0.001) continue;
    // odak noktası: ürün üstünde yanıp sönen halka
    const od = ODAK[o.odak] || ODAK.on;
    const [px, py] = ekranda(urun.localToWorld(new THREE.Vector3(...od)));
    const nab = (t - o.bas) * 2.2 % 1;
    cx.globalAlpha = g;
    cx.strokeStyle = R.vurgu; cx.lineWidth = 3 * U;
    cx.beginPath(); cx.arc(px, py, (10 + 22 * nab) * U * outBack(prog(t, o.bas + 0.1, 0.4)), 0, Math.PI * 2);
    cx.globalAlpha = g * (1 - nab); cx.stroke();
    cx.globalAlpha = g; cx.fillStyle = R.vurgu;
    cx.beginPath(); cx.arc(px, py, 7 * U * outBack(prog(t, o.bas + 0.05, 0.35)), 0, Math.PI * 2); cx.fill();

    const no = String(i + 1).padStart(2, '0');
    const kay = (1 - gir) * 40 * U - (1 - cik) * 18 * U;
    if (DIKEY) {
      const y = H * (W / H > 0.7 ? 0.83 : 0.80) + kay;
      yaz(no, 30 * U, 800, W / 2, y - 92 * U, R.vurgu, 'center', 6 * U);
      yaz(o.metin, 78 * U, 800, W / 2, y, R.anaUstu, 'center', -1 * U, W * 0.86);
      if (o.alt) { cx.globalAlpha = g * 0.75; yaz(o.alt, 34 * U, 500, W / 2, y + 56 * U, R.anaUstu, 'center', 1 * U, W * 0.8); }
    } else {
      const x = W * 0.60, y = H * 0.52 + kay;
      // odaktan yazıya ince çizgi
      const uc = x - 28 * U, ciz = outCubic(prog(t, o.bas + 0.05, 0.45));
      cx.globalAlpha = g * 0.8; cx.strokeStyle = R.vurgu; cx.lineWidth = 2 * U;
      cx.beginPath(); cx.moveTo(px, py); const ox = lerp(px, uc, ciz), oy = lerp(py, y - 30 * U, ciz); cx.lineTo(ox, oy); cx.stroke();
      cx.globalAlpha = g;
      yaz(no, 30 * U, 800, x, y - 92 * U, R.vurgu, 'left', 6 * U);
      yaz(o.metin, 84 * U, 800, x, y, R.anaUstu, 'left', -1 * U, W * 0.36);
      if (o.alt) { cx.globalAlpha = g * 0.75; yaz(o.alt, 34 * U, 500, x, y + 58 * U, R.anaUstu, 'left', 1 * U, W * 0.34); }
    }
    cx.globalAlpha = 1;
  }
}

function girisCiz(t) {
  // açılış sorusu: ışık açılmadan önce büyük, kısa bir cümle; ürün yükselirken söner
  if (!A.giris) return;
  const gs = A.giris_son, g = Math.min(outCubic(prog(t, 0.2, 0.45)), 1 - inOutCubic(prog(t, gs - 0.25, 0.45)));
  if (g <= 0.001) return;
  const y = DIKEY ? H * (W / H > 0.7 ? 0.83 : 0.80) : H * 0.52;
  const x = DIKEY ? W / 2 : W * 0.66;
  cx.globalAlpha = g;
  yaz(A.giris, 92 * U * (0.94 + 0.06 * g), 800, x, y + (1 - g) * 24 * U, R.anaUstu, 'center', -1 * U, DIKEY ? W * 0.88 : W * 0.5);
  cx.fillStyle = R.vurgu; const cw_ = 120 * U * outCubic(prog(t, 0.45, 0.5));
  cx.fillRect(x - cw_ / 2, y + 36 * U, cw_, 5 * U);
  cx.globalAlpha = 1;
}

function finalCiz(t) {
  const g1 = outCubic(prog(t, F.bas + 0.15, 0.6)), g2 = outCubic(prog(t, F.bas + 0.55, 0.55)), g3 = outBack(prog(t, F.bas + 0.9, 0.5), 1.4);
  if (g1 <= 0) return;
  const x = DIKEY ? W / 2 : W * 0.66, hiza = DIKEY ? 'center' : 'center';
  const y0 = DIKEY ? H * (W / H > 0.7 ? 0.76 : 0.755) : H * 0.40;
  cx.globalAlpha = g1;
  const lw = yaz(F.logo, 120 * U, 800, x, y0 + (1 - g1) * 30 * U, R.anaUstu, hiza, 10 * U, DIKEY ? W * 0.84 : W * 0.5);
  cx.fillStyle = R.vurgu; cx.fillRect(x - lw * 0.5 * g2, y0 + 34 * U, lw * g2, 4 * U);
  if (F.cagri) {
    cx.globalAlpha = clamp(g3);
    cx.font = `800 44px Vitrin`; // ölç
    cx.font = `800 ${44 * U}px Vitrin`; if ('letterSpacing' in cx) cx.letterSpacing = `${2 * U}px`;
    const bw = cx.measureText(F.cagri).width + 96 * U, bh = 100 * U, by = y0 + 82 * U;
    const s = 0.9 + 0.1 * g3;
    cx.save(); cx.translate(x, by + bh / 2); cx.scale(s, s);
    cx.fillStyle = R.vurgu; cx.fillRect(-bw / 2, -bh / 2, bw, bh); // köşeler kare
    cx.restore();
    yaz(F.cagri, 44 * U * s, 800, x, by + bh / 2 + 16 * U * s, R.vurguUstu, 'center', 2 * U);
    if (F.alt) { cx.globalAlpha = clamp(g3) * 0.7; yaz(F.alt, 32 * U, 500, x, by + bh + 58 * U, R.anaUstu, 'center', 2 * U); }
  }
  cx.globalAlpha = 1;
}

// ±1–2 düzeylik sabit gren: kenar kararmasının 8 bit degradesi halka halka bantlaşmasın
const GREN = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const x = c.getContext('2d'), v = x.createImageData(256, 256), r = rng(77);
  for (let i = 0; i < v.data.length; i += 4) { const k = r() < 0.5 ? 0 : 255; v.data[i] = v.data[i + 1] = v.data[i + 2] = k; v.data[i + 3] = Math.round(r() * 4); }
  x.putImageData(v, 0, 0); return cx.createPattern(c, 'repeat');
})();

function vinyet() {
  const g = cx.createRadialGradient(W * URUN_EKRAN.x, H * URUN_EKRAN.y, Math.min(W, H) * 0.3, W / 2, H / 2, Math.hypot(W, H) * 0.62);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.42)');
  cx.fillStyle = g; cx.fillRect(0, 0, W, H);
  cx.fillStyle = GREN; cx.fillRect(0, 0, W, H);
}

// ---------- kare ----------
function kare(t) {
  const S = A.sure, gs = A.giris_son;
  // ışık: karanlıktan açılış, finalde parlama
  const ac = smooth(prog(t, 0.05, gs * 0.9)), fin = smooth(prog(t, F.bas, 0.8));
  anahtar.intensity = 170 * ac + 40 * fin;
  kontur.intensity = 2.4 * smooth(prog(t, 0.0, gs * 0.6)) + 0.6 * fin;
  kontur2.intensity = 1.2 * ac;
  hemi.intensity = 0.3 + 0.45 * ac;
  scene.environmentIntensity = 0.12 + 0.28 * ac;
  fonMat.uniforms.isik.value = ac * 0.6 + fin * 0.4;
  halkaMat.opacity = 0.85 * smooth(prog(t, gs * 0.6, 0.6)) * (0.75 + 0.25 * Math.sin(t * 3));
  renderer.toneMappingExposure = 0.95 + 0.12 * fin;

  // ürün: aşağıdan yükselir ve döner; özelliklerde yavaş salınır; finalde öne döner
  const yuksel = outCubic(prog(t, 0.1, gs * 0.95));
  urun.position.y = lerp(-0.9, 0, yuksel) + 0.03 * Math.sin(t * 1.4) * yuksel;
  const donus = lerp(-220, -18, inOutCubic(prog(t, 0.0, gs + 0.4)));
  const salin = ozellikler.length ? 22 * Math.sin((t - gs) * 0.55) * smooth(prog(t, gs, 1.2)) : 0;
  const finD = inOutCubic(prog(t, F.bas - 0.3, 1.1));
  urun.rotation.y = lerp(donus + salin, 360 * Math.round((donus + salin) / 360), finD) * D2R;
  urun.scale.setScalar(lerp(0.92, 1, yuksel));
  kitapAc(t);

  // parlama taraması: girişte ve finalde ürünün önünden soldan sağa
  const tar = (t0, d) => { const p = prog(t, t0, d); return p > 0 && p < 1 ? [p, Math.sin(Math.PI * p)] : null; };
  const tr = tar(gs * 0.5, 1.0) || tar(F.bas + 0.2, 1.1);
  if (tr) { tarama.intensity = 9 * tr[1]; tarama.position.set(lerp(-2.6, 2.6, tr[0]), OLCU.h * 0.6, 2.2); } else tarama.intensity = 0;

  for (const b of cekirdekler) {
    const p = outBack(prog(t, gs * 0.7 + b.userData.gec, 0.5), 1.8);
    b.position.y = lerp(1.2, b.userData.y, clamp(p)) + 0.008 * Math.sin(t * 2 + b.userData.faz);
    b.scale.setScalar(clamp(p * 1.2));
  }
  for (const [i, s] of zerre.tohum.entries()) {
    zerre.pos[i * 3] = s[0] + 0.25 * Math.sin(t * s[4] * 3 + s[3]);
    zerre.pos[i * 3 + 1] = ((s[1] + t * s[4]) % 6.2) - 0.2;
    zerre.pos[i * 3 + 2] = s[2];
  }
  zerre.p.geometry.attributes.position.needsUpdate = true;
  zerre.m.opacity = 0.55 * ac;

  const k = kameraPoz(t), R0 = Math.max(OLCU.h, OLCU.w * 1.3) * 0.62;
  const uz = fitDist(R0) * k.uz * (DIKEY ? 1 : 1.22); // yatayda yazıya yer kalsın
  const hedef = new THREE.Vector3(0, OLCU.h * k.hy, 0);
  camera.position.set(Math.sin(k.az) * Math.cos(k.el) * uz, hedef.y + Math.sin(k.el) * uz, Math.cos(k.az) * Math.cos(k.el) * uz);
  camera.lookAt(hedef);
  camera.updateMatrixWorld(); urun.updateMatrixWorld(true);
  renderer.render(scene, camera);

  cx.globalAlpha = 1; cx.clearRect(0, 0, W, H);
  cx.drawImage(renderer.domElement, 0, 0);
  vinyet();
  girisCiz(t);
  ozellikCiz(t);
  finalCiz(t);
  // açılış ve kapanışta kısa karartma
  const kar = 1 - smooth(prog(t, 0, 0.35)) + smooth(prog(t, S - 0.25, 0.25));
  if (kar > 0) { cx.fillStyle = `rgba(0,0,0,${clamp(kar)})`; cx.fillRect(0, 0, W, H); }
}

window.kare = t => { kare(t); return tuval.toDataURL('image/png').split(',')[1]; };

(async () => {
  for (const [ag, yol] of Object.entries(A.fontlar)) {
    const f = new FontFace('Vitrin', `url(${yol})`, { weight: ag });
    document.fonts.add(await f.load());
  }
  if (A.urun.model) await modelKur(A.urun.model);
  else if (A.urun.tur === 'kutu') kutuKur();
  else if (A.urun.tur === 'kitap') await kitapKur();
  else paketKur();
  if (A.urun.sus === 'kahve-cekirdegi') cekirdekKur();
  kare(0);
  window.hazir = true;
})().catch(e => { window.hata = String(e && e.stack || e); });

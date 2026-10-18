// Oyuncak şablonu: pastel 3D "oyuncak dünya" (three.js). Her kare t'nin saf fonksiyonudur:
// window.kare(t) sahneyi kurar, çizer ve PNG (base64) döndürür. Ayarlar window.OYUNCAK'tan gelir
// (oyuncak.py yazar: W, H, palet, kolonlar, c = zaman.cizelge()).
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';
import { TTFLoader } from 'three/addons/loaders/TTFLoader.js';
import { Font } from 'three/addons/loaders/FontLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const A = window.OYUNCAK;
const { W, H, c: Z } = A;
const P = A.palet;

// ---------- yardımcılar ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, p) => a + (b - a) * p;
const prog = (t, t0, d) => clamp((t - t0) / d);
const inOutCubic = p => (p < .5 ? 4 * p ** 3 : 1 - (-2 * p + 2) ** 3 / 2);
const outBack = (p, s = 1.7) => { p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2; };
const smooth = p => p * p * (3 - 2 * p);
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
const v3 = (x, y, z) => new THREE.Vector3(x, y, z);
const D2R = Math.PI / 180;
const ZIPLA = 0.42, KUTLA = 0.36;

// ---------- zaman çizelgesi (zaman.py'den) ----------
const BUYUME = Z.kosu[0] - 0.15;
const DORUK = Z.doruk;
const KARSI = Z.karsitlik;                    // null olabilir
const KAPANIS = Z.kapanis;                    // null olabilir
const SON = A.sure;
const KAPANIS_BAS = KAPANIS ? KAPANIS.bas : SON;
const BUYUME_SON = KARSI ? KARSI.bas : KAPANIS_BAS;

// ---------- renderer ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.45;

// en dar görüş açısı 30°: her formatta aynı mesafe aynı çerçeveyi verir, dikey format yukarı/aşağı fazlasını görür
const ASPECT = W / H, MIN_FOV = 30;
const vfov = ASPECT >= 1 ? MIN_FOV : 2 * Math.atan(Math.tan(MIN_FOV / 2 * D2R) / ASPECT) / D2R;
const camera = new THREE.PerspectiveCamera(vfov, ASPECT, 0.05, 400);
const fitDist = R => R / Math.sin(MIN_FOV / 2 * D2R);
const YATAY = ASPECT > 1;

const C = {
  gokUst: new THREE.Color(P.gok_ust), gokAlt: new THREE.Color(P.gok_alt),
  gokUstSon: new THREE.Color(P.gok_ust_son), gokAltSon: new THREE.Color(P.gok_alt_son),
  kolon0: new THREE.Color(P.kolon_bas), kolon1: new THREE.Color(P.kolon_orta), kolon2: new THREE.Color(P.kolon_son),
};
const koyu = (hex, k) => new THREE.Color(hex).multiplyScalar(k);

// gökyüzü: dikey degrade küre
const gokMat = new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, fog: false,
  uniforms: { ust: { value: C.gokUst.clone() }, alt: { value: C.gokAlt.clone() } },
  vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader: 'uniform vec3 ust; uniform vec3 alt; varying vec3 vP;\nvoid main(){ float k = smoothstep(-0.25, 0.6, vP.y); gl_FragColor = vec4(mix(alt, ust, k), 1.0);\n#include <colorspace_fragment>\n}',
});
const gok = new THREE.Mesh(new THREE.SphereGeometry(300, 32, 16), gokMat);
gok.renderOrder = -1;
scene.add(gok);
scene.fog = new THREE.Fog(C.gokAlt.clone(), 30, 95);

// ışıklar
const hemi = new THREE.HemisphereLight('#FFF6EA', koyu(P.gok_alt, 1.0), 1.15);
scene.add(hemi);
const gunes = new THREE.DirectionalLight('#FFF0DC', 2.3);
gunes.position.set(-9, 16, 11);
gunes.castShadow = true;
gunes.shadow.mapSize.set(2048, 2048);
Object.assign(gunes.shadow.camera, { left: -14, right: 14, top: 16, bottom: -12, near: 1, far: 60 });
gunes.shadow.bias = -0.0004; gunes.shadow.normalBias = 0.02; gunes.shadow.radius = 4;
scene.add(gunes);
const dolgu = new THREE.DirectionalLight('#C9DCFF', 0.5); // soğuk arka kontur
dolgu.position.set(8, 6, -10);
scene.add(dolgu);

const mat = (renk, o = {}) => new THREE.MeshPhysicalMaterial({ color: renk, roughness: 0.42, clearcoat: 0.6, clearcoatRoughness: 0.35, ...o });

// ---------- ada ----------
const adaR = 9.6, T0 = 120 * D2R;
const ada = new THREE.Mesh(new THREE.CylinderGeometry(adaR, adaR - 0.5, 0.7, 96, 1), mat(P.ada, { roughness: 0.8, clearcoat: 0 }));
ada.position.y = -0.35; ada.receiveShadow = true; scene.add(ada);
const kenar = new THREE.Mesh(new THREE.TorusGeometry(adaR - 0.02, 0.12, 12, 120), mat(koyu(P.ada, 0.93), { roughness: 0.7, clearcoat: 0 }));
kenar.rotation.x = Math.PI / 2; kenar.position.y = -0.04; kenar.receiveShadow = true; scene.add(kenar);
const zemin = new THREE.Mesh(new THREE.CircleGeometry(200, 64), new THREE.MeshStandardMaterial({ color: koyu(P.gok_alt, 1.02), roughness: 1 }));
zemin.rotation.x = -Math.PI / 2; zemin.position.y = -4; zemin.receiveShadow = true; scene.add(zemin);

// süs: yuvarlak çalılar ve uzakta süzülen bulutlar
const sus = [];
{
  const r = rng(7);
  const calMat = [mat('#8ED6A8', { roughness: 0.6 }), mat('#B5E5A0', { roughness: 0.6 }), mat('#F6A6B8', { roughness: 0.55 })];
  for (let i = 0; i < 14; i++) {
    const a = r() * Math.PI * 2;
    const fark = b => Math.abs(Math.atan2(Math.sin(a - b), Math.cos(a - b)));
    if (fark(Math.PI / 2) < 0.75 || fark(T0) < 0.6) continue; // ön boşluk ve ilk adım temiz
    const rr = lerp(8.2, 9.0, r()), g = new THREE.Group();
    const k = 1 + r() * 2;
    for (let j = 0; j < k; j++) {
      const s = new THREE.Mesh(new THREE.SphereGeometry(lerp(0.28, 0.5, r()), 24, 16), calMat[Math.floor(r() * 3)]);
      s.position.set((r() - .5) * 0.6, 0.2, (r() - .5) * 0.6); s.castShadow = true; s.receiveShadow = true; g.add(s);
    }
    g.position.set(Math.cos(a) * rr, 0, Math.sin(a) * rr); scene.add(g);
  }
  const bulutMat = mat('#FFFFFF', { transparent: true, opacity: 0.92, roughness: 0.9, clearcoat: 0 });
  for (let i = 0; i < 9; i++) {
    const g = new THREE.Group();
    for (let j = 0; j < 4; j++) {
      const s = new THREE.Mesh(new THREE.SphereGeometry(lerp(1.2, 2.2, r()), 24, 16), bulutMat);
      s.position.set(j * 1.6 - 2.4, (r() - .3) * 0.8, (r() - .5) * 1.2); g.add(s);
    }
    const a = (i / 9) * Math.PI * 2 + r();
    g.position.set(Math.cos(a) * lerp(30, 45, r()), lerp(4, 16, r()), Math.sin(a) * lerp(30, 45, r()));
    g.userData = { y: g.position.y, hiz: 0.2 + r() * 0.3, faz: r() * 6 };
    scene.add(g); sus.push(g);
  }
}

// ---------- kolonlar: spiral üzerinde, yükseklik üstel artar (son / ilk = oran) ----------
const N = A.kolonlar.adet, H0 = 0.3, GEN = Math.min(0.56, 0.6 * 52 / N + 0.1);
const DT = (300 / (N - 1)) * D2R;
const kolonlar = [];
for (let i = 0; i < N; i++) {
  const a = T0 + i * DT, r = lerp(7.0, 4.4, i / (N - 1));
  const h = H0 * Math.pow(A.kolonlar.oran, i / (N - 1));
  const u = i / (N - 1);
  const renk = u < 0.5 ? C.kolon0.clone().lerp(C.kolon1, u * 2) : C.kolon1.clone().lerp(C.kolon2, (u - .5) * 2);
  const m = new THREE.Mesh(new RoundedBoxGeometry(GEN, 1, GEN, 3, Math.min(0.09, GEN * 0.16)), mat(renk, { roughness: 0.38 }));
  m.castShadow = true; m.receiveShadow = true;
  m.position.set(Math.cos(a) * r, 0, Math.sin(a) * r);
  m.rotation.y = -a;
  scene.add(m);
  kolonlar.push({ m, h, a, r, bas: Z.kolon_bas[i] });
}
const tepe = i => { const k = kolonlar[i]; return v3(k.m.position.x, k.h, k.m.position.z); };
const kolonBoy = (k, t) => { const p = prog(t, k.bas, 0.38); return p <= 0 ? 0 : p >= 1 ? 1 : outBack(p, 1.6); };
const SON_ADIM = Z.adim_sayisi - 1;
const DIS = v3(Math.cos(T0), 0, Math.sin(T0));   // ilk kolondan adanın dışına

// ---------- kahraman (yuvarlak oyuncak karakter) ----------
const TR = 0.2;
const topi = new THREE.Group(), govde = new THREE.Group();
topi.add(govde);
{
  const g = new THREE.Mesh(new THREE.SphereGeometry(TR, 48, 32), mat(P.kahraman, { roughness: 0.32, clearcoat: 0.9, clearcoatRoughness: 0.15, sheen: 0.4, sheenColor: new THREE.Color('#FFD0C8') }));
  g.position.y = TR; g.castShadow = true; govde.add(g);
  const gozMat = mat('#1E1A2E', { roughness: 0.15, clearcoat: 1 });
  const parlak = new THREE.MeshBasicMaterial({ color: '#FFFFFF' });
  const yanakMat = mat(new THREE.Color(P.kahraman).lerp(new THREE.Color('#FFFFFF'), 0.35), { roughness: 0.6, clearcoat: 0 });
  for (const s of [-1, 1]) {
    const goz = new THREE.Group();
    const e = new THREE.Mesh(new THREE.SphereGeometry(0.032, 20, 14), gozMat);
    e.scale.set(1, 1.35, 0.8); goz.add(e);
    const p = new THREE.Mesh(new THREE.SphereGeometry(0.010, 10, 8), parlak);
    p.position.set(0.010, 0.018, 0.024); goz.add(p);
    goz.position.set(s * 0.068, TR + 0.045, TR * 0.9);
    goz.name = 'goz'; govde.add(goz);
    const y = new THREE.Mesh(new THREE.SphereGeometry(0.03, 16, 10), yanakMat);
    y.scale.set(1.3, 0.7, 0.4); y.position.set(s * 0.12, TR - 0.01, TR * 0.86); govde.add(y);
    const ayak = new THREE.Mesh(new THREE.SphereGeometry(0.06, 20, 12), mat(koyu(P.kahraman, 0.85), { roughness: 0.4 }));
    ayak.scale.set(1, 0.55, 1.35); ayak.position.set(s * 0.085, 0.025, 0.03); ayak.castShadow = true; topi.add(ayak);
  }
  const agiz = new THREE.Mesh(new THREE.TorusGeometry(0.03, 0.008, 8, 20, Math.PI), gozMat);
  agiz.rotation.z = Math.PI; agiz.position.set(0, TR - 0.02, TR * 0.97); govde.add(agiz);
}
scene.add(topi);
const gozler = govde.children.filter(c => c.name === 'goz');

// zıplama: A'dan B'ye, t0'da kalkış, d süre, yükseklik hz; sq: + basık, - uzamış
function zipla(t, A_, B_, t0, d, hz) {
  const p = clamp((t - t0) / d);
  const pos = A_.clone().lerp(B_, p); pos.y += Math.sin(Math.PI * p) * hz;
  let sq;
  if (t < t0) sq = 0.25 * smooth(prog(t, t0 - 0.12, 0.12));         // hazırlık çömelmesi
  else if (p < 1) sq = -0.22 * Math.sin(Math.PI * Math.min(1, p * 1.6));
  else sq = 0.32 * Math.exp(-(t - t0 - d) * 9) * Math.cos((t - t0 - d) * 26);  // iniş yaylanması
  return { pos, sq };
}

// ---------- 3D yazılar (genişlik sınırına sığdırılır) ----------
function yazi(font, metin, boy, yuz, yan, enGenis, derinlik = 0.35) {
  const g = new TextGeometry(metin, { font, size: boy, depth: boy * derinlik, curveSegments: 10, bevelEnabled: true, bevelThickness: boy * 0.06, bevelSize: boy * 0.035, bevelSegments: 4 });
  g.computeBoundingBox(); const b = g.boundingBox;
  g.translate(-(b.max.x + b.min.x) / 2, -(b.max.y + b.min.y) / 2, -(b.max.z + b.min.z) / 2);
  const gen = b.max.x - b.min.x;
  if (gen > enGenis) g.scale(enGenis / gen, enGenis / gen, enGenis / gen);
  const m = new THREE.Mesh(g, [mat(yuz, { roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.1 }), mat(yan, { roughness: 0.4 })]);
  m.castShadow = true; m.visible = false; scene.add(m); return m;
}
const yazilar = {};

// ---------- konfeti ----------
const KN = 220, konfeti = new THREE.InstancedMesh(new THREE.BoxGeometry(0.11, 0.022, 0.07), mat('#ffffff', { roughness: 0.5, clearcoat: 0.3 }), KN);
konfeti.castShadow = true;
const kParca = [];
{
  const r = rng(37), renkler = [P.kahraman, P.doruk_yuz, P.kolon_bas, P.kolon_orta, '#F6A6B8', '#FFFFFF'];
  for (let i = 0; i < KN; i++) {
    const a = r() * Math.PI * 2, hiz = lerp(3, 7.5, r()), yuk = lerp(0.35, 1, r());
    kParca.push({ v: v3(Math.cos(a) * hiz * (1 - yuk * 0.5), hiz * yuk * 1.3, Math.sin(a) * hiz * (1 - yuk * 0.5)),
      w: v3(r() * 12 - 6, r() * 12 - 6, r() * 12 - 6), gec: r() * 0.12, sal: r() * 6 });
    konfeti.setColorAt(i, new THREE.Color(renkler[i % renkler.length]));
  }
  scene.add(konfeti);
}
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _e = new THREE.Euler(), _s = v3(1, 1, 1), _p = v3(0, 0, 0);
function konfetiGuncelle(t, kaynak) {
  for (let i = 0; i < KN; i++) {
    const k = kParca[i], tau = t - DORUK - k.gec;
    if (tau <= 0) { _m.makeScale(0, 0, 0); konfeti.setMatrixAt(i, _m); continue; }
    // hava sürtünmeli atış: hız üstel söner, yerçekimi sabit son hıza yaklaşır
    const c = 1.6, ex = (1 - Math.exp(-c * tau)) / c;
    _p.set(kaynak.x + k.v.x * ex + Math.sin(tau * 3 + k.sal) * 0.25 * tau, kaynak.y + k.v.y * ex - 2.2 * (tau - ex), kaynak.z + k.v.z * ex);
    if (_p.y < 0.02) _p.y = 0.02;
    _e.set(k.w.x * tau, k.w.y * tau, k.w.z * tau); _q.setFromEuler(_e);
    _s.setScalar(tau > 3.2 ? Math.max(0, 1 - (tau - 3.2) * 2) : 1);
    _m.compose(_p, _q, _s); konfeti.setMatrixAt(i, _m);
  }
  konfeti.instanceMatrix.needsUpdate = true;
}

// ---------- kamera planları ----------
function yorunge(hedef, az, el, mesafe) {   // az: hedeften kameraya yön (xz düzleminde, derece)
  return hedef.clone().add(v3(Math.cos(az * D2R) * Math.cos(el * D2R), Math.sin(el * D2R), Math.sin(az * D2R) * Math.cos(el * D2R)).multiplyScalar(mesafe));
}
const R_ADIM = 0.35 * Math.max(0, SON_ADIM - 2);   // ikiden fazla adım: çerçeve genişler
function kameraPlani(t, topiPos) {
  const c0 = tepe(0), cA = tepe(SON_ADIM), cN = tepe(N - 1);
  if (t < BUYUME) {                                       // adımlar: yakın, sakin, yavaş yaklaşma
    const p = smooth(prog(t, 0, BUYUME));
    const hedef = c0.clone().lerp(cA, SON_ADIM > 2 ? 0.5 + 0.1 * p : 0.45 + 0.25 * p); hedef.y = lerp(0.62, 0.7, p) + (YATAY ? 0.18 : 0);
    return { hedef, pos: yorunge(hedef, lerp(98, 108, p), lerp(9, 13, p), fitDist(lerp(1.15, 0.95, p) + R_ADIM)) };
  }
  if (t < BUYUME_SON) {                                   // büyüme: vinç geri çekilir, kahramanla döner, doruğa varır
    const p = inOutCubic(prog(t, BUYUME, DORUK + 0.2 - BUYUME));
    const doruk = cN.clone().lerp(v3(0, 3, 0), 0.4); doruk.y = cN.y - (YATAY ? 1.3 : 2.2);
    const hedef = topiPos.clone().add(v3(0, 0.3, 0)).lerp(doruk, smooth(prog(t, BUYUME + 0.4, DORUK - 0.2 - BUYUME)));
    const son = prog(t, DORUK, BUYUME_SON - DORUK);
    const az = lerp(108, 28, p) - 10 * son, el = lerp(13, 7, p);
    const pos = yorunge(hedef, az, el, fitDist(lerp(1.3 + R_ADIM, 4.6, p) + 0.5 * son));
    const sar = t > DORUK ? Math.exp(-(t - DORUK) * 6) : 0;     // doruk sarsıntısı
    pos.add(v3(Math.sin(t * 61) * 0.12 * sar, Math.cos(t * 53) * 0.12 * sar, 0));
    return { hedef, pos };
  }
  if (t < KAPANIS_BAS) {                                  // karşıtlık: küçük adım → büyük fark (vinç yukarı)
    const p = inOutCubic(prog(t, KARSI.vinc_t, 0.9));
    const kucuk = c0.clone(); kucuk.y = 0.22;
    const pos0 = yorunge(kucuk, 112, 7, fitDist(0.95)).add(v3(-0.05 * prog(t, KARSI.bas, 0.6), 0, 0));
    const buyuk = cN.clone(); buyuk.y += 0.3;
    const pos1 = yorunge(buyuk, 96, -6, fitDist(2.4));
    const hedef = kucuk.clone().lerp(buyuk, p);
    const pos = pos0.clone().lerp(pos1, p);
    pos.y += Math.sin(Math.PI * p) * 1.5;
    return { hedef, pos };
  }
  const p = smooth(prog(t, KAPANIS_BAS, SON - KAPANIS_BAS));   // kapanış: açık, sıcak, ilk adımın önü
  const hedef = c0.clone(); hedef.y = lerp(0.55, 0.75, p);
  hedef.add(DIS.clone().multiplyScalar(0.35));
  return { hedef, pos: yorunge(hedef, 112 + 6 * p, lerp(10, 7, p), fitDist(lerp(1.25, 1.05, p))) };
}

// ---------- kahramanın hali ----------
function topiDurum(t) {
  let pos = tepe(0), sq = 0, yon = 0, bak = true;   // yon: y ekseni (radyan); bak: kameraya dön
  if (t < Z.kosu[0]) {
    Z.ziplamalar.forEach((z, k) => {
      if (t >= z - 0.12) { const r = zipla(t, tepe(k), tepe(k + 1), z, ZIPLA, 0.3); pos = r.pos; sq = r.sq; }
    });
  } else if (t < DORUK) {
    // dalganın arkasından tepe tepe koşu
    const p = prog(t, Z.kosu[0], DORUK - Z.kosu[0]);
    const u = SON_ADIM + (N - 1 - SON_ADIM) * (p * p * (1.6 - 0.6 * p));
    const i = Math.min(N - 2, Math.floor(u)), f = u - i;
    const A_ = tepe(i), B_ = tepe(i + 1);
    pos = A_.clone().lerp(B_, f);
    pos.y = lerp(A_.y, B_.y, smooth(f)) + Math.sin(Math.PI * f) * (0.16 + Math.abs(B_.y - A_.y) * 0.6);
    sq = -0.15; bak = false;
    yon = -(T0 + u * DT) - Math.PI;   // ilerleme yönü (teğet)
  } else if (t < KAPANIS_BAS) {
    pos = tepe(N - 1);
    sq = 0.32 * Math.exp(-(t - DORUK) * 8) * Math.cos((t - DORUK) * 24);
    for (const z of Z.kutlama) {
      const p = prog(t, z, KUTLA);
      if (p > 0 && p < 1) pos.y += Math.sin(Math.PI * p) * 0.35;
      if (t > z + KUTLA) sq += 0.25 * Math.exp(-(t - z - KUTLA) * 10) * Math.cos((t - z - KUTLA) * 26);
    }
  } else {
    // kapanış: gökten iner, ilk kolona zıplar
    const yer = tepe(0).add(DIS.clone().multiplyScalar(0.62)); yer.y = 0;
    const { inis_t, zipla_t } = KAPANIS;
    if (t < inis_t) { const p = prog(t, KAPANIS_BAS, inis_t - KAPANIS_BAS); pos = yer.clone(); pos.y = lerp(3.2, 0, p * p); sq = -0.25; }
    else if (t < zipla_t - 0.12) { pos = yer; sq = 0.45 * Math.exp(-(t - inis_t) * 9) * Math.cos((t - inis_t) * 24); }
    else { const r = zipla(t, yer, tepe(0), zipla_t, 0.4, 0.45); pos = r.pos; sq = r.sq; }
  }
  return { pos, sq, yon, bak };
}

// ---------- kare ----------
function kare(t) {
  for (const k of kolonlar) {
    const s = kolonBoy(k, t);
    k.m.visible = s > 0.001;
    k.m.scale.y = Math.max(0.001, s * k.h);
    k.m.position.y = s * k.h / 2;
  }
  const d = topiDurum(t);
  topi.position.copy(d.pos);
  const sq = d.sq + 0.03 * Math.sin(t * 5.5);   // nefes
  govde.scale.set(1 + sq * 0.5, 1 - sq, 1 + sq * 0.5);
  const kam = kameraPlani(t, d.pos);
  topi.rotation.y = d.bak ? Math.atan2(kam.pos.x - d.pos.x, kam.pos.z - d.pos.z) * 0.85 : d.yon;
  let kirp = 1;   // göz kırpma: her ~1,8 sn'de bir, sabit desen
  for (let z = 0.55; z < SON; z += 1.75) { const p = prog(t, z, 0.16); if (p > 0 && p < 1) kirp = 1 - Math.sin(Math.PI * p) * 0.9; }
  gozler.forEach(g => g.scale.y = kirp);

  const yuzle = (m, s) => { m.lookAt(kam.pos.x, m.position.y, kam.pos.z); m.scale.setScalar(Math.max(0.0001, s)); m.visible = s > 0.002; };
  if (yazilar.adim) {
    const y = Z.yazilar.adim, c = tepe(0).lerp(tepe(SON_ADIM), 0.5);   // adımların ortasının üstü
    yazilar.adim.position.set(c.x, c.y + 1.08 + 0.03 * Math.sin(t * 3), c.z);
    const s = outBack(prog(t, y.t, 0.5), 2.2) * (1 - inOutCubic(prog(t, y.son_t, 0.25)));
    yuzle(yazilar.adim, s); yazilar.adim.rotation.z = 0.12 * Math.sin(t * 2.4) * s;
  }
  if (yazilar.doruk) {
    const y = Z.yazilar.doruk, c = tepe(N - 1);
    yazilar.doruk.position.set(c.x, c.y + 2.05 + 0.08 * Math.sin(t * 2.2), c.z);
    yuzle(yazilar.doruk, outBack(prog(t, y.t, 0.55), 2.4) * (t < y.son_t ? 1 : 0));
  }
  if (yazilar.kapanis) {
    const c = tepe(0);
    yazilar.kapanis.position.set(c.x + DIS.x * 0.3, 1.25 + 0.025 * Math.sin(t * 3), c.z + DIS.z * 0.3);
    yuzle(yazilar.kapanis, outBack(prog(t, Z.yazilar.kapanis.t, 0.5), 2.0));
  }
  konfetiGuncelle(t, tepe(N - 1).add(v3(0, 0.6, 0)));

  // atmosfer: kapanışta gökyüzü aydınlanır, dorukta ışık parlar
  const ac = KAPANIS ? smooth(prog(t, KAPANIS_BAS, 0.9)) : 0;
  gokMat.uniforms.ust.value.copy(C.gokUst).lerp(C.gokUstSon, ac);
  gokMat.uniforms.alt.value.copy(C.gokAlt).lerp(C.gokAltSon, ac);
  scene.fog.color.copy(gokMat.uniforms.alt.value);
  const flas = t > DORUK ? Math.exp(-(t - DORUK) * 5) : 0;
  hemi.intensity = 1.15 + 0.25 * ac + 0.6 * flas;
  renderer.toneMappingExposure = 1.05 + 0.1 * ac;
  for (const g of sus) { g.position.y = g.userData.y + Math.sin(t * g.userData.hiz + g.userData.faz) * 0.5; g.rotation.y = t * 0.02; }

  camera.position.copy(kam.pos); camera.lookAt(kam.hedef);
  renderer.render(scene, camera);
}

window.kare = t => { kare(t); return renderer.domElement.toDataURL('image/png').split(',')[1]; };

new TTFLoader().load('/font', json => {
  try {
    const font = new Font(json), Y = Z.yazilar;
    if (Y.adim) yazilar.adim = yazi(font, Y.adim.metin, 0.36, P.yazi_yuz, P.yazi_yan, 1.3);
    if (Y.doruk) yazilar.doruk = yazi(font, Y.doruk.metin, 1.5, P.doruk_yuz, P.doruk_yan, 3.6);
    if (Y.kapanis) yazilar.kapanis = yazi(font, Y.kapanis.metin, 0.2, P.yazi_yuz, P.yazi_yan, YATAY ? 1.9 : 1.45, 0.4);
    kare(0);
    window.hazir = true;
  } catch (e) { window.hata = String(e); }
}, undefined, e => { window.hata = 'yazı tipi yüklenemedi: ' + e; });

// sahne.js'i başsız Chromium'da (SwiftShader WebGL; GPU varsa onu) kare kare çizer, ffmpeg'e PNG akışı olarak verir.
// oyuncak.py çağırır:
//   node render.mjs AYAR.json video SESSIZ.mp4
//   node render.mjs AYAR.json kare CIKTI.png t [t ...]
// AYAR.json: W, H, fps, sure, palet, kolonlar, c (zaman.cizelge) ve font (yerel yazı tipi yolu).
// three ve playwright bu klasörün node_modules'ünden gelir (npm install); NODE_MODULES başka bir yer gösterebilir.
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const BURADA = path.dirname(fileURLToPath(import.meta.url));
const NM = process.env.NODE_MODULES || path.join(BURADA, 'node_modules');
const [, , ayarYolu, kip, cikti, ...ts] = process.argv;
const A = JSON.parse(await readFile(ayarYolu, 'utf8'));
const { W, H, fps, sure } = A;
const TUR = { '.js': 'text/javascript', '.html': 'text/html', '.ttf': 'font/ttf', '.otf': 'font/otf' };

const tarayici = await chromium.launch({
  executablePath: process.env.CHROMIUM || undefined,
  args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const sayfa = await tarayici.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
sayfa.on('pageerror', e => { console.error('sayfa hatası:', e.message); process.exit(1); });
sayfa.on('console', m => { if (m.type() === 'error') console.error('konsol:', m.text()); });
await sayfa.addInitScript(a => { window.OYUNCAK = a; }, A);
await sayfa.route('http://yerel/**', async r => {
  const yol = decodeURIComponent(new URL(r.request().url()).pathname);
  const dosya = yol === '/font' ? A.font : yol.startsWith('/node_modules/') ? path.join(NM, yol.slice(14)) : path.join(BURADA, yol);
  try { await r.fulfill({ body: await readFile(dosya), contentType: TUR[path.extname(dosya).toLowerCase()] || 'application/octet-stream' }); }
  catch { await r.fulfill({ status: 404, body: 'yok' }); }
});
await sayfa.goto('http://yerel/sahne.html');
await sayfa.waitForFunction(() => window.hazir === true || window.hata, null, { timeout: 180000 });
const hata = await sayfa.evaluate(() => window.hata);
if (hata) { console.error('sahne kurulamadı:', hata); process.exit(1); }

if (kip === 'kare') {
  for (const t of ts) {
    const b64 = await sayfa.evaluate(t => window.kare(t), +t);
    const ad = ts.length > 1 ? cikti.replace(/\.png$/, `-${(+t).toFixed(2)}.png`) : cikti;
    await writeFile(ad, Buffer.from(b64, 'base64'));
  }
} else {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'png', '-framerate', String(fps), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', cikti], { stdio: ['pipe', 'inherit', 'inherit'] });
  const n = Math.round(fps * sure), bas = Date.now();
  for (let i = 0; i < n; i++) {
    const b64 = await sayfa.evaluate(t => window.kare(t), i / fps);
    if (!ff.stdin.write(Buffer.from(b64, 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
    if (i % fps === 0) console.error(`${W}x${H} kare ${i}/${n} (${((Date.now() - bas) / 1000).toFixed(0)} sn)`);
  }
  ff.stdin.end();
  const kod = await new Promise(r => ff.on('close', r));
  if (kod) { console.error('ffmpeg başarısız'); process.exit(1); }
}
await tarayici.close();

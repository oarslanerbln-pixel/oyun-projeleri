"""Cycles karelerine (16 bit PNG) ince film greni + marka yazılarını bindirir, müzikle MP4 yapar.

  python3 bindir.py KARE_KLASÖRÜ MUZIK.wav ÇIKTI.mp4 [--kapak KAPAK.png]
Gren aynı zamanda 16 bit -> 8 bit geçişinde dither görevi görür (düz fonda bant oluşmaz).
"""
import glob, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BURADA = os.path.dirname(os.path.abspath(__file__))
FPS = 24


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x


def font(ad, px, agirlik):
    f = ImageFont.truetype(os.path.join(BURADA, 'fonts', ad), px)
    try: f.set_variation_by_axes([agirlik] if 'Cormorant' in ad else [14, agirlik])
    except Exception: pass
    return f


F1 = font('CormorantGaramond.ttf', 132, 600)
F2 = font('CormorantGaramond.ttf', 58, 500)
F3 = font('Inter.ttf', 30, 500)


def ortali(d, metin, f, cx, y, renk, aralik=0):
    gen = sum(f.getlength(c) for c in metin) + aralik * (len(metin) - 1); x = cx - gen / 2
    for c in metin: d.text((x, y), c, font=f, fill=renk); x += f.getlength(c) + aralik


def kare(yol, t, rng):
    a = np.asarray(Image.open(yol), dtype=np.float32)
    a = a / (65535.0 if a.max() > 255 else 255.0)
    a = a + rng.normal(0, 0.9 / 255, a.shape).astype(np.float32)
    im = Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)).convert('RGBA')
    kat = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(kat)
    W = im.size[0]
    a1, a2, a3 = clamp((t - 7.0) / 0.7), clamp((t - 7.7) / 0.6), clamp((t - 8.3) / 0.6)
    if a1 > 0: ortali(d, 'LÉVA', F1, W / 2, 250 + 14 * (1 - a1), (58, 40, 30, int(255 * a1)), aralik=34)
    if a2 > 0: ortali(d, 'Işığını içeriden al.', F2, W / 2, 400 + 8 * (1 - a2), (110, 62, 34, int(255 * a2)))
    if a3 > 0: ortali(d, 'HYALURON SERUM  ·  30 ml', F3, W / 2, 490, (70, 52, 40, int(255 * a3)), aralik=6)
    return Image.alpha_composite(im, kat).convert('RGB')


def main():
    kd, muzik, cikti = sys.argv[1:4]
    kapak = sys.argv[sys.argv.index('--kapak') + 1] if '--kapak' in sys.argv else None
    kareler = sorted(glob.glob(os.path.join(kd, '[0-9]*.png')))
    w, h = Image.open(kareler[0]).size
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(FPS), '-i', '-',
                           '-i', muzik, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p',
                           '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', cikti], stdin=subprocess.PIPE)
    rng = np.random.default_rng(1)
    for i, yol in enumerate(kareler):
        im = kare(yol, i / FPS, rng)
        if kapak and i == int(9.5 * FPS): im.save(kapak)
        ff.stdin.write(im.tobytes())
    ff.stdin.close(); ff.wait()


if __name__ == '__main__':
    main()

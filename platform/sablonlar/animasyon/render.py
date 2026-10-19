"""Render: çekim listesinden teslime hazır MP4 (mimari §5.1, animatik → üretim → master).

Animatiğin zaman çizelgesini ve yerleşimini birebir kullanır; değişen yalnız
arka plandır. Her çekimin arka planı sırayla:

  1. `sinif=C` ise yapay zekâ kaydındaki (`yz-kaydi.csv`) en son video çıktısı,
  2. `anahtar_kare` görseli (kamera hareketiyle),
  3. marka renklerinden yer tutucu (C çekiminde köşede "YZ bekleniyor" etiketi).

Yazı, logo, CTA ve altyazı satırı animatikteki SVG karesinin saydam katmanıdır
(`cizim.cekim_svg(katman=True)`), ffmpeg'in librsvg çözücüsüyle basılır. Geçişler
(`erime`, `kayma`) xfade, kamera notu (`itme`/`çekme`) arka planda %6 ölçek
hareketidir. Ses: verilen müzik ön ayarın `lufs` değerine çekilir; yoksa sessiz
iz. Altyazılar her dil için ayrı yumuşak iz (mov_text) olarak gömülür.

Yalnız Python standart kitaplığı ve ffmpeg (librsvg ile derlenmiş; Ubuntu paketi öyledir).
"""

from __future__ import annotations

import csv
import json
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import _yollar  # noqa: F401
import cizim
from cekimler import Zamanli, zaman_cizelgesi
from metin import HATA, UYARI, Bulgu
from proje import Kurgu, Proje
from teslim import OnAyar
from turev import kirpma, olc

VIDEO = (".mp4", ".mov", ".webm", ".mkv", ".m4v")
GORSEL = (".png", ".jpg", ".jpeg", ".webp")
HAREKET_OLCEK = 0.06   # animatikle aynı: itme 1 → 1.06, çekme 1.06 → 1
PERDE = 0.35           # görüntü üstünde yazı okunsun diye zemin renginde örtü
VARSAYILAN_GIRIS = 0.4
ISO639 = {"tr": "tur", "en": "eng", "de": "deu", "fr": "fra", "es": "spa", "ar": "ara", "ru": "rus"}
KLIP, KARE, YER_TUTUCU = "klip", "kare", "yer-tutucu"


@dataclass(frozen=True)
class Kaynak:
    tur: str            # klip | kare | yer-tutucu
    yol: Path | None = None
    lisans: str = ""


@dataclass(frozen=True)
class Parca:
    z: Zamanli
    kaynak: Kaynak
    gecis: float        # bu çekime giriş geçişinin süresi (sn); kesmede 0
    kuyruk: int         # sonraki çekimin geçişi için fazladan kare


def sure_sn(deger: object, varsayilan: float = VARSAYILAN_GIRIS) -> float:
    """DTCG süre belirteci ('400ms', '0.4s', 400) → saniye."""
    if isinstance(deger, (int, float)):
        return float(deger) / 1000
    m = re.fullmatch(r"\s*([\d.]+)\s*(ms|s)?\s*", str(deger or ""))
    if not m:
        return varsayilan
    return float(m.group(1)) / (1 if m.group(2) == "s" else 1000)


def kayit_yolu(p: Proje, kok: Path) -> Path:
    data = json.loads((p.klasor / "proje.json").read_text(encoding="utf-8"))
    return kok / data["yz_kaydi"] if data.get("yz_kaydi") else p.klasor / "yz-kaydi.csv"


def kayitlar(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def kaynak_bul(kurgu: str, z: Zamanli, kayit: list[dict], kok: Path) -> Kaynak:
    c = z.cekim
    if c.sinif == "C":
        for r in reversed(kayit):  # en son üretilen kazanır
            yol = kok / r.get("dosya", "")
            if (r.get("kullanildigi_yer") == f"{kurgu}/{c.cekim}" and yol.suffix.lower() in VIDEO
                    and yol.is_file()):
                return Kaynak(KLIP, yol, r.get("lisans", ""))
    if c.anahtar_kare and (kok / c.anahtar_kare).is_file():
        return Kaynak(KARE, kok / c.anahtar_kare)
    return Kaynak(YER_TUTUCU)


def parcalar(p: Proje, k: Kurgu, kok: Path, kayit: list[dict]) -> list[Parca]:
    tl = zaman_cizelgesi(list(k.cekimler), k.fps)
    giris = sure_sn(p.marka.hareket.get("giris"))
    # Animatikle aynı süre: markanın giriş süresi, çekimin üçte birini geçmeden; kareye yuvarlı.
    gecisler = [0.0 if z.cekim.gecis == "kesme" else round(min(giris, (z.son - z.bas) / 3) * k.fps) / k.fps
                for z in tl]
    out = []
    for i, z in enumerate(tl):
        kuyruk = round(gecisler[i + 1] * k.fps) if i + 1 < len(tl) else 0
        out.append(Parca(z, kaynak_bul(k.ad, z, kayit, kok), gecisler[i], kuyruk))
    return out


def _renk(hex_: str, alfa: float | None = None) -> str:
    return "0x" + hex_.lstrip("#") + (f"@{alfa:g}" if alfa is not None else "")


def _karistir(a: str, b: str, t: float) -> str:
    x = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    y = [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(u + (v - u) * t):02x}" for u, v in zip(x, y))


def katman_svg(pa: Parca, a: OnAyar, p: Proje, dil: str) -> str:
    """Yazı katmanı; yer tutucu C çekiminde köşeye etiket eklenir ki taslak teslime kaçmasın."""
    svg = cizim.cekim_svg(pa.z, a, p, dil, katman=True)
    if pa.kaynak.tur == YER_TUTUCU and pa.z.cekim.sinif == "C":
        c, body = pa.z.cekim, p.marka.yazi["govde"]
        size = min(a.genislik, a.yukseklik) * 0.022
        fg = p.marka.renk_al(c.on)
        label = cizim._text([f"YZ {c.cekim} · yer tutucu"], size, a.yukseklik * a.guvenli_ust - size,
                            size, fg, body.aile, body.agirlik, anchor="start", extra=' fill-opacity=".55"')
        svg = svg.replace("</svg>", label + "</svg>")
    return svg


def arka_plan(pa: Parca, a: OnAyar, p: Proje, fps: int) -> tuple[list[str], str]:
    """Arka planın ffmpeg girdisi ve süzgeci: ([girdi argümanları], '[0:v]…[bg]')."""
    c, w, h = pa.z.cekim, a.genislik, a.yukseklik
    kareler = pa.z.kareler + pa.kuyruk
    sure = kareler / fps
    zemin = p.marka.renk_al(c.zemin)
    if pa.kaynak.tur == YER_TUTUCU:
        isik = p.marka.renk.get("isik.sicak") or p.marka.renk.get("vurgu") or zemin
        c1 = _karistir(zemin, isik, 0.22)
        # Işık odak tarafındaki üst kenardan karşı alt köşeye yayılır; yavaşça döner.
        x0 = round(c.odak_x * w)
        girdi = ["-f", "lavfi", "-i",
                 f"gradients=s={w}x{h}:c0={_renk(c1)}:c1={_renk(zemin)}:x0={x0}:y0=0:"
                 f"x1={w - x0}:y1={h}:nb_colors=2:speed=0.004:r={fps}:d={sure:.6f}"]
        sahne = "[0:v]"
    else:
        iw, ih, _ = olc(pa.kaynak.yol)
        cw, ch, cx, cy = kirpma(iw, ih, w, h, c.odak_x, c.odak_y)
        if pa.kaynak.tur == KLIP:
            girdi = ["-stream_loop", "-1", "-i", str(pa.kaynak.yol)]
        else:
            girdi = ["-loop", "1", "-framerate", str(fps), "-i", str(pa.kaynak.yol)]
        sahne = f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={w}:{h}:flags=lanczos,setsar=1,fps={fps},"
    hareket = cizim.hareket(c.kamera)
    if hareket != "sabit":
        d = f"{sure:.6f}"
        olcek = (f"(1+{HAREKET_OLCEK}*min(t/{d},1))" if hareket == "yaklas"
                 else f"(1+{HAREKET_OLCEK}*(1-min(t/{d},1)))")
        sahne += (f"scale=w='trunc({w}*{olcek}/2)*2':h='trunc({h}*{olcek}/2)*2':eval=frame:flags=bicubic,"
                  f"crop={w}:{h}:x='(iw-{w})*{c.odak_x}':y='(ih-{h})*{c.odak_y}',")
    if pa.kaynak.tur != YER_TUTUCU and (c.ekran or c.metin_anahtari or c.cagri or c.logo):
        sahne += f"drawbox=c={_renk(zemin, PERDE)}:t=fill,"
    sahne += f"format=yuv420p,trim=end_frame={kareler},setpts=PTS-STARTPTS[bg]"
    return girdi, sahne


def parca_komutu(pa: Parca, a: OnAyar, p: Proje, fps: int, katman_png: Path, cikti: Path) -> list[str]:
    girdi, sahne = arka_plan(pa, a, p, fps)
    giris = sure_sn(p.marka.hareket.get("giris"))
    kareler = pa.z.kareler + pa.kuyruk
    graf = (f"{sahne};[1:v]format=rgba,fade=in:st=0:d={giris:g}:alpha=1[yazi];"
            f"[bg][yazi]overlay=format=auto:shortest=0:eof_action=repeat,format=yuv420p,"
            f"trim=end_frame={kareler}[v]")
    return (["ffmpeg", "-v", "error", "-y", *girdi, "-loop", "1", "-framerate", str(fps), "-i", str(katman_png),
             "-filter_complex", graf, "-map", "[v]", "-frames:v", str(kareler), "-r", str(fps),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-an", str(cikti)])


def birlestir_grafi(parcalar_: list[Parca], fps: int) -> str:
    """Parçaları zaman çizelgesine dizer: kesme concat, erime fade, kayma slideleft.
    Her parça bir sonraki geçiş kadar uzun olduğundan toplam süre çekim listesiyle aynı kalır."""
    zincir = [f"[{i}:v]fps={fps},settb=AVTB,format=yuv420p,setsar=1[p{i}]" for i in range(len(parcalar_))]
    onceki = "[p0]"
    if parcalar_ and parcalar_[0].gecis:  # ilk çekimde geçiş: zeminden açılış
        zincir.append(f"[p0]fade=in:st=0:d={parcalar_[0].gecis:g}[a0]")
        onceki = "[a0]"
    for i, pa in enumerate(parcalar_[1:], start=1):
        hedef = f"[x{i}]"
        if pa.gecis:
            tur = "slideleft" if pa.z.cekim.gecis == "kayma" else "fade"
            zincir.append(f"{onceki}[p{i}]xfade=transition={tur}:duration={pa.gecis:g}:"
                          f"offset={pa.z.bas_kare / fps:.6f}{hedef}")
        else:
            zincir.append(f"{onceki}[p{i}]concat=n=2:v=1:a=0{hedef}")
        onceki = hedef
    zincir.append(f"{onceki}format=yuv420p[v]")
    return ";".join(zincir)


def son_komut(parca_dosyalari: list[Path], parcalar_: list[Parca], k: Kurgu, a: OnAyar,
              altyazilar: list[tuple[str, Path]], muzik: Path | None, cikti: Path) -> list[str]:
    fps = k.fps
    toplam = parcalar_[-1].z.son_kare / fps
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for f in parca_dosyalari:
        cmd += ["-i", str(f)]
    n = len(parca_dosyalari)
    graf = birlestir_grafi(parcalar_, fps)
    harita = ["-map", "[v]"]
    if a.lufs is not None:
        if muzik:
            cmd += ["-i", str(muzik)]
            sonu = max(toplam - 1.0, 0)
            graf += (f";[{n}:a]atrim=0:{toplam:.6f},asetpts=PTS-STARTPTS,afade=t=in:d=0.3,"
                     f"afade=t=out:st={sonu:.6f}:d={min(1.0, toplam):g},"
                     f"loudnorm=I={a.lufs:g}:TP=-1:LRA=11,aresample=48000[a]")
        else:
            cmd += ["-f", "lavfi", "-t", f"{toplam:.6f}", "-i", "anullsrc=r=48000:cl=stereo"]
            graf += f";[{n}:a]anull[a]"
        harita += ["-map", "[a]"]
        n += 1
    for i, (dil, yol) in enumerate(altyazilar):
        cmd += ["-i", str(yol)]
        harita += ["-map", f"{n + i}:s"]
    cmd += ["-filter_complex", graf, *harita, "-t", f"{toplam:.6f}", "-r", str(fps),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
            "-movflags", "+faststart"]
    if a.lufs is not None:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    if altyazilar:
        cmd += ["-c:s", "mov_text"]
        for i, (dil, _) in enumerate(altyazilar):
            cmd += [f"-metadata:s:s:{i}", f"language={ISO639.get(dil, dil)}"]
    return cmd + [str(cikti)]


def _calistir(cmd: list[str], yazdir: bool) -> None:
    if yazdir:
        print(shlex.join(cmd))
        return
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"ffmpeg başarısız ({r.returncode}): {r.stderr.strip()[-2000:]}\n{shlex.join(cmd)}")


def olcum(dosya: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height,r_frame_rate,nb_frames",
                          "-of", "json", str(dosya)], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def render(p: Proje, kok: Path, out: Path, kurgu: str | None = None, teslim: str | None = None,
           dil: str | None = None, muzik: Path | None = None, yazdir: bool = False) -> tuple[list[Path], list[Bulgu]]:
    """Seçilen kurgu × ön ayar için MP4 yazar. Döner: (yazılan dosyalar, bulgular)."""
    dil = dil or p.diller[0]
    b: list[Bulgu] = []
    if dil not in p.diller:
        return [], [Bulgu(HATA, "render", f"dil {dil!r} projede yok; {', '.join(p.diller)}")]
    if muzik and not muzik.is_file():
        return [], [Bulgu(HATA, "render", f"müzik dosyası yok: {muzik}")]
    kurgular = [k for k in p.kurgular if kurgu in (None, k.ad)
                and any(teslim in (None, a.ad) for a in k.teslim)]
    if not kurgular:
        return [], [Bulgu(HATA, "render", f"kurgu {kurgu or '*'!r} × ön ayar {teslim or '*'!r} yok; "
                                          + "; ".join(f"{k.ad}: {', '.join(a.ad for a in k.teslim)}"
                                                      for k in p.kurgular))]
    kayit = kayitlar(kayit_yolu(p, kok))
    yazilan: list[Path] = []
    for k in kurgular:
        ayarlar = [a for a in k.teslim if teslim in (None, a.ad)]
        pl = parcalar(p, k, kok, kayit)
        for pa in pl:
            c = pa.z.cekim
            if c.sinif == "C" and pa.kaynak.tur != KLIP:
                b.append(Bulgu(UYARI, f"{k.ad}:{c.cekim}", "YZ klibi yok, yer tutucu kullanıldı; "
                                                           "bu render taslaktır, teslim edilmez"))
            if pa.kaynak.tur == KLIP and pa.kaynak.lisans != "ticari":
                b.append(Bulgu(UYARI, f"{k.ad}:{c.cekim}", f"klip lisansı {pa.kaynak.lisans or 'boş'!r}; "
                                                           "ticari teslimden önce uretim.py denetle"))
        with tempfile.TemporaryDirectory(prefix="render-") as tmp:
            tmp = Path(tmp)
            altyazilar = []
            if any(c.metin_anahtari for c in k.cekimler):
                for d in p.diller:
                    yol = tmp / f"altyazi.{d}.srt"
                    yol.write_text(cizim.altyazi(p, k, d), encoding="utf-8")
                    altyazilar.append((d, yol))
            for a in ayarlar:
                hedef = out / k.ad / a.ad / f"{p.kimlik}-{k.ad}-{a.ad}-{dil}.mp4"
                hedef.parent.mkdir(parents=True, exist_ok=True)
                dosyalar = []
                for i, pa in enumerate(pl):
                    svg = tmp / f"{a.ad}-{i:02d}.svg"
                    png = svg.with_suffix(".png")
                    svg.write_text(katman_svg(pa, a, p, dil), encoding="utf-8")
                    _calistir(["ffmpeg", "-v", "error", "-y", "-i", str(svg), "-frames:v", "1", str(png)], yazdir)
                    parca = tmp / f"{a.ad}-{i:02d}.mp4"
                    _calistir(parca_komutu(pa, a, p, k.fps, png, parca), yazdir)
                    dosyalar.append(parca)
                _calistir(son_komut(dosyalar, pl, k, a, altyazilar, muzik, hedef), yazdir)
                if not yazdir:
                    yazilan.append(hedef)
    return yazilan, b

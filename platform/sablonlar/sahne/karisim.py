"""Stil karışımı ve stil geçişi: bir videoda sahneler farklı stillerde, stil değişirken imza geçişi.

Senaryoda sahneye `"stil": "piksel"` yazılırsa o sahne (ve stil yazmayan sonrakiler) o stilde çizilir; stil değiştiği
an eski stil yeni stile fırça ya da mürekkep maskesiyle dönüşür. `"donustur": "origami"` (ya da
`{"stil": "origami", "an": 0.5, "sure": 0.9}`) sahnenin ortasında aynı sahneyi yeni stile çevirir; sonraki sahneler
yeni stilde sürer. Geçişin biçimi senaryo düzeyinde: `"stil_gecisi": {"tur": "firca" | "murekkep", "sure": 0.8}`.

Kare kare çizildiği için yalnız kaplama stilleri (kinetik, kagit-kesik, izometrik, hamur, piksel, origami ...)
karışır. Çeviricili stiller (vitray, çini, VHS ...) ve ayrı şablonlar (karakalem) arasında imza geçiş uzun video
kurgusunda: `kurgu.json` sahnesinde `"gecis": {"tur": "firca"}`.
"""

from __future__ import annotations

import math

TURLER = ("firca", "murekkep")
VARSAYILAN = {"tur": "firca", "sure": 0.8}


def var_mi(s: dict) -> bool:
    return any("stil" in sh or "donustur" in sh for sh in s.get("sahneler", []))


def _donustur(sh: dict) -> dict | None:
    d = sh.get("donustur")
    if d is None:
        return None
    return {"stil": d} if isinstance(d, str) else d


def gecis(s: dict) -> dict:
    return {**VARSAYILAN, **(s.get("stil_gecisi") or {})}


def plan(s: dict, ana: str) -> list[tuple[str, str]]:
    """her sahne için (başladığı stil, bittiği stil); stil yazmayan sahne bir öncekinin bittiği stilde sürer"""
    out, simdiki = [], ana
    for sh in s["sahneler"]:
        bas = sh.get("stil", simdiki)
        d = _donustur(sh)
        simdiki = d["stil"] if d else bas
        out.append((bas, simdiki))
    return out


def denetle(s: dict, ana: str | None, kaplama_stilleri: list[str]) -> list[str]:
    h = []
    g = s.get("stil_gecisi")
    if g is not None:
        if not isinstance(g, dict) or g.get("tur", "firca") not in TURLER:
            h.append(f"stil_gecisi: tur {', '.join(TURLER)} olmalı")
        elif not 0.2 <= float(g.get("sure", 0.8)) <= 2.0:
            h.append("stil_gecisi: sure 0.2–2.0 sn olmalı")
    if not var_mi(s):
        return h
    if ana and ana not in kaplama_stilleri:
        h.append(f"stil karışımı yalnız kaplama stilleriyle olur ({', '.join(kaplama_stilleri)}); "
                 f"{ana} için uzun video kurgusunda `\"gecis\": {{\"tur\": \"firca\"}}` kullanın")
    for i, sh in enumerate(s["sahneler"]):
        ad = f"sahneler[{i}]"
        if "stil" in sh and sh["stil"] not in kaplama_stilleri:
            h.append(f"{ad}.stil: {sh['stil']} karışamaz; kaplama stilleri: {', '.join(kaplama_stilleri)}")
        d = sh.get("donustur")
        if d is None:
            continue
        if not isinstance(d, (str, dict)) or (isinstance(d, dict) and "stil" not in d):
            h.append(f'{ad}.donustur: "stil" ya da {{"stil": ..., "an": 0.5}} olmalı')
            continue
        d = _donustur(sh)
        if d["stil"] not in kaplama_stilleri:
            h.append(f"{ad}.donustur: {d['stil']} karışamaz; kaplama stilleri: {', '.join(kaplama_stilleri)}")
        if not 0.15 <= float(d.get("an", 0.5)) <= 0.85:
            h.append(f"{ad}.donustur.an: sahnenin 0.15–0.85 arası oranı olmalı")
        if sh["tip"] == "gecis":
            h.append(f"{ad}: geçiş kartında donustur kullanılmaz")
    return h


# ---------- maske ----------
def _dalga(y: float, tohum: float) -> float:
    """-1..1 arası fırça kenarı dalgası (deterministik, birkaç sinüsün toplamı)"""
    return (0.55 * math.sin(y * 8.17 + 1.1 + tohum) + 0.3 * math.sin(y * 23.2 + 0.4 + tohum * 2)
            + 0.15 * math.sin(y * 57.2 + tohum * 3))


def maske(W: float, H: float, p: float, tur: str, tohum: float = 0.0):
    """yeni stilin göründüğü bölge (skia.Path) ve kenar noktaları (mürekkep çizgisi için)"""
    import skia
    yol = skia.Path()
    if tur == "murekkep":
        R = math.hypot(W, H) * 0.62 * p
        cx, cy = W * 0.5, H * 0.46
        n = 160
        nok = []
        for k in range(n + 1):
            a = 2 * math.pi * k / n
            r = R * (1 + 0.10 * math.sin(5 * a + tohum) + 0.05 * math.sin(11 * a + 1.3 + tohum) + 0.025 * math.sin(23 * a))
            nok.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        yol.addPoly([skia.Point(*q) for q in nok], True)
        return yol, nok
    gen = W * 0.08  # dalga genliği
    egim = W * 0.22  # üst kenar önde: çapraz fırça darbesi
    n = 96
    nok = []
    for k in range(n + 1):
        y = H * k / n
        x = p * (W + 2 * gen + egim) - gen - egim * (y / H) + gen * _dalga(y / H, tohum)
        nok.append((x, y))
    yol.addPoly([skia.Point(-4, -4), *[skia.Point(*q) for q in nok], skia.Point(-4, H + 4)], True)
    return yol, nok


class Karisim:
    """Sahne sahne farklı kaplamalar. sahne.py'deki render / kontakt / kare bunu tek kaplama gibi kullanır."""

    POZ = None  # her stil kendi pozunu kendisi uygular

    def __init__(self, s: dict, ana: str, siniflar: dict[str, type]):
        self.s = s
        self.plan = plan(s, ana)
        self.kap = {st: siniflar[st](s) for st in {ana, *[x for p in self.plan for x in p]}}
        a = self.kap[ana]
        self.ad, self.MUZIK, self.SFX, self.p = ana, a.MUZIK, a.SFX, a.p
        g = gecis(s)
        self.tur, self.sure = g["tur"], float(g["sure"])

    def poz(self, t):
        return t

    def _donusum(self, i: int):
        """sahnenin ortasındaki dönüşümün başlangıcı ve süresi"""
        sh = self.s["sahneler"][i]
        d = _donustur(sh)
        if not d:
            return None
        u = sh["son"] - sh["bas"]
        sure = min(float(d.get("sure", self.sure)), u * 0.5)
        return sh["bas"] + u * float(d.get("an", 0.5)) - sure / 2, sure

    def sahne_sirasi(self, t):
        shs = self.s["sahneler"]
        for i in range(len(shs) - 1, -1, -1):
            if t >= shs[i]["bas"]:
                return i
        return 0

    def kare(self, cv, t, W, H, fmt):
        t = min(t, self.s["sure"] - 1e-3)
        i = self.sahne_sirasi(t)
        sh = self.s["sahneler"][i]
        bas, son = self.plan[i]
        if i and self.plan[i - 1][1] != bas and t - sh["bas"] < self.sure:
            # sahne sınırında stil değişiyor: eski stil önceki sahnenin son halinde durur, yeni stil maskeyle gelir;
            # yeni stilin kendi sahne geçişi kapatılır (iki geçiş üst üste binmesin)
            eski = self.kap[self.plan[i - 1][1]]
            return self._karistir(cv, W, H, fmt, (t - sh["bas"]) / self.sure,
                                  lambda: eski.kare(cv, sh["bas"] - 1e-3, W, H, fmt), self.kap[bas], t, i)
        d = self._donusum(i)
        if d and t >= d[0]:
            p = (t - d[0]) / d[1]
            if p >= 1:
                return self.kap[son].kare(cv, t, W, H, fmt)
            return self._karistir(cv, W, H, fmt, p, lambda: self.kap[bas].kare(cv, t, W, H, fmt), self.kap[son], t, i)
        return self.kap[bas].kare(cv, t, W, H, fmt)

    def _karistir(self, cv, W, H, fmt, p, eski_ciz, yeni, t, i):
        import skia
        from kaplama import alfa, in_out
        e = in_out(p)
        eski_ciz()
        yol, nok = maske(W, H, e, self.tur, tohum=i * 1.7)
        cv.save()
        cv.clipPath(yol, skia.ClipOp.kIntersect, True)
        yeni.GECIS = 0  # örnek düzeyinde: yalnız bu çizimde sahne geçişi yok
        try:
            yeni.kare(cv, t, W, H, fmt)
        finally:
            del yeni.GECIS
            cv.restore()
        # imza: maskenin kenarında yeni stilin mürekkep renginde ince fırça çizgisi (ortada en kalın)
        u = min(W, H) / 1080
        kalin = 7 * u * math.sin(math.pi * e)
        if kalin > 0.4:
            cizgi = skia.Path()
            cizgi.addPoly([skia.Point(*q) for q in nok], self.tur == "murekkep")
            cv.drawPath(cizgi, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=kalin,
                                          StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join,
                                          Color=alfa(yeni.p["murekkep"], 0.9)))

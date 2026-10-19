"""Ağız senkronu: seslendirme satırı → her an için ağız açıklığı (0..1) ve biçimi.

Önce ElevenLabs'in harf zamanları (`<id>.hizalama.json`, platform/ses yazar): her harf bir ağız biçimine
düşer (a → geniş açık, o/u → yuvarlak, m/b/p → kapalı...). Harf zamanı yoksa (Piper yedeği ya da zamanlar
eklenmeden önce önbelleğe girmiş satır) açıklık ses dosyasının genliğinden çıkar. Her iki yolda sonuç
100 Hz'lik bir eğridir; atak/bırakma yumuşatması ağzın kare kare titremesini önler.
"""

from __future__ import annotations

import json
import math
import wave
from pathlib import Path

HZ = 100
# harf → (açıklık, biçim). Türkçe ve Almanca harfleri kapsar; listede olmayan harf "orta" sayılır.
HARFLER = {}
for h in "aâá": HARFLER[h] = (1.0, "A")
for h in "eäéıiîy": HARFLER[h] = (0.62, "E")
for h in "oöóuüûú": HARFLER[h] = (0.72, "O")
for h in "mbp": HARFLER[h] = (0.0, "M")
for h in "fvw": HARFLER[h] = (0.18, "F")
ORTA = (0.32, "E")
ATAK, BIRAK = 0.035, 0.07   # sn: ağız hızlı açılır, biraz daha yavaş kapanır


def _yumusat(hedef: list[float]) -> list[float]:
    out, y = [], 0.0
    ka, kb = 1 - math.exp(-1 / (ATAK * HZ)), 1 - math.exp(-1 / (BIRAK * HZ))
    for x in hedef:
        y += (x - y) * (ka if x > y else kb)
        out.append(y)
    return out


def harflerden(hizalama: dict, sure: float) -> tuple[list[float], list[str]]:
    n = max(1, int(math.ceil(sure * HZ)) + 1)
    hedef, bicim = [0.0] * n, ["M"] * n
    for h, b, s in zip(hizalama["karakterler"], hizalama["bas"], hizalama["son"]):
        if not h.strip() or not h.isalpha():
            continue
        acik, bc = HARFLER.get(h.lower(), ORTA)
        i0, i1 = int(b * HZ), max(int(b * HZ) + 1, int(s * HZ))
        for i in range(max(0, i0), min(n, i1)):
            hedef[i], bicim[i] = acik, bc
    return _yumusat(hedef), bicim


def genlikten(wav: Path) -> tuple[list[float], list[str]]:
    with wave.open(str(wav), "rb") as w:
        sr, kanal, gen = w.getframerate(), w.getnchannels(), w.getsampwidth()
        ham = w.readframes(w.getnframes())
    import array
    a = array.array("h", ham[: len(ham) - len(ham) % 2]) if gen == 2 else array.array("h")
    if kanal > 1:
        a = a[::kanal]
    pencere = max(1, sr // HZ)
    rms = []
    for i in range(0, len(a), pencere):
        p = a[i:i + pencere]
        rms.append(math.sqrt(sum(x * x for x in p) / max(1, len(p))) / 32768)
    tepe = sorted(rms)[int(len(rms) * 0.92)] if rms else 1.0
    hedef, bicim = [], []
    for i, r in enumerate(rms):
        x = min(1.0, r / max(tepe, 1e-6))
        x = 0.0 if x < 0.12 else min(1.0, (x - 0.12) / 0.75) ** 0.8
        hedef.append(x)
        bicim.append("A" if x > 0.7 else "O" if x > 0.45 and (i // 9) % 2 else "E" if x > 0.15 else "M")
    return _yumusat(hedef), bicim


class Agiz:
    """Bir videodaki bütün konuşma satırları; `an(t)` → (açıklık, biçim, konuşuyor mu)."""

    def __init__(self):
        self.satirlar = []   # (t0, sure, acik[], bicim[])

    def ekle(self, t0: float, wav: Path | None, hizalama: Path | None) -> str:
        """Satırı ekler; dönüş kullanılan kaynak: "harf", "genlik" ya da "yok"."""
        sure = 0.0
        if wav and Path(wav).exists():
            with wave.open(str(wav), "rb") as w:
                sure = w.getnframes() / w.getframerate()
        if hizalama and Path(hizalama).exists():
            h = json.loads(Path(hizalama).read_text(encoding="utf-8"))
            sure = max(sure, max(h["son"], default=0.0))
            self.satirlar.append((t0, sure, *harflerden(h, sure)))
            return "harf"
        if sure:
            self.satirlar.append((t0, sure, *genlikten(Path(wav))))
            return "genlik"
        return "yok"

    def an(self, t: float) -> tuple[float, str, bool]:
        for t0, sure, acik, bicim in self.satirlar:
            if t0 <= t < t0 + sure + BIRAK * 3:
                i = min(len(acik) - 1, max(0, int((t - t0) * HZ)))
                return acik[i], bicim[i], t < t0 + sure
        return 0.0, "M", False

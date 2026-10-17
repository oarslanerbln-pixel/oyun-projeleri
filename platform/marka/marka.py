#!/usr/bin/env python3
"""Marka kiti: şema, doğrulayıcı ve dışa aktarıcılar (mimari §4.1).

`marka.json` W3C Design Tokens biçimindedir (`$type`, `$value`). Bölümler:
`renk` (iç içe gruplar olabilir: `isik.sicak`), `ciftler` (erişilebilirlik
çiftleri), `yazi`, `logo`, `hareket`, `ses`, `prompt`. Rollere ad verilir,
araçlar adı okur; marka değişince tek dosya değişir.

Kullanım:
  marka.py denetle <marka.json>
  marka.py aktar <css|figma|unity-uss|unity-json|prompt> <marka.json>

Yalnız Python standart kitaplığı.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HATA = "HATA"
UYARI = "UYARI"

REQUIRED_COLORS = ("zemin", "metin")
REQUIRED_TYPE = ("baslik", "govde")
CONTRAST_TEXT = 4.5   # WCAG 2.1 AA gövde metni
CONTRAST_LARGE = 3.0  # WCAG 2.1 AA büyük metin
_HEX = re.compile(r"^#([0-9a-fA-F]{6})$")
_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_DURATION = re.compile(r"^\d+(\.\d+)?(ms|s)$")


@dataclass(frozen=True)
class Bulgu:
    seviye: str
    yer: str
    mesaj: str

    def __str__(self) -> str:
        return f"{self.seviye} {self.yer}: {self.mesaj}"


def has_errors(bulgular) -> bool:
    return any(b.seviye == HATA for b in bulgular)


# --- renk -------------------------------------------------------------------

def is_hex(value: object) -> bool:
    return isinstance(value, str) and _HEX.match(value) is not None


def to_rgb(value: str) -> tuple[int, int, int]:
    m = _HEX.match(value)
    if not m:
        raise ValueError(f"#RRGGBB biçiminde değil: {value!r}")
    h = m.group(1)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def relative_luminance(value: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# --- model ------------------------------------------------------------------

@dataclass(frozen=True)
class YaziStili:
    aile: str
    agirlik: int = 400


@dataclass(frozen=True)
class Marka:
    kimlik: str
    ad: str
    renk: dict[str, str]                  # düzleştirilmiş ad → #rrggbb
    yazi: dict[str, YaziStili]
    ciftler: tuple[tuple[str, str, float], ...] = ()
    hareket: dict[str, object] = field(default_factory=dict)
    ton: tuple[str, ...] = ()
    yasak: tuple[str, ...] = ()
    logo_metin: str = ""
    logo_dosya: str = ""
    prompt_uslup: str = ""
    prompt_negatif: tuple[str, ...] = ()

    def renk_al(self, ad: str) -> str:
        return self.renk[ad]


def _tokens(group: dict, prefix: str = ""):
    """İç içe grupları `ad.alt` biçiminde düzleştirir; `$` ile başlayan anahtarlar meta veridir."""
    for key, value in group.items():
        if key.startswith("$"):
            continue
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and "$value" in value:
            yield name, value
        elif isinstance(value, dict):
            yield from _tokens(value, name)
        else:
            yield name, value


def denetle(data: object, kok: Path | None = None) -> list[Bulgu]:
    """`kok`: logo dosyasının göreli yolu için marka.json'un klasörü."""
    if not isinstance(data, dict):
        return [Bulgu(HATA, "marka", "nesne olmalı")]
    b: list[Bulgu] = []

    if not isinstance(data.get("kimlik"), str) or not _ID.match(data["kimlik"]):
        b.append(Bulgu(HATA, "marka.kimlik", "küçük harf, rakam ve tire olmalı (örn. demli-kahve)"))
    if not isinstance(data.get("ad"), str) or not data["ad"].strip():
        b.append(Bulgu(HATA, "marka.ad", "boş olamaz"))

    renk_raw = data.get("renk")
    renk: dict[str, str] = {}
    if not isinstance(renk_raw, dict):
        b.append(Bulgu(HATA, "marka.renk", "nesne olmalı"))
    else:
        for name, tok in _tokens(renk_raw):
            yer = f"marka.renk.{name}"
            if not isinstance(tok, dict) or tok.get("$type", "color") != "color":
                b.append(Bulgu(HATA, yer, '{"$type": "color", "$value": "#rrggbb"} olmalı'))
            elif not is_hex(tok.get("$value")):
                b.append(Bulgu(HATA, yer, f"#RRGGBB olmalı, {tok.get('$value')!r} geldi"))
            else:
                renk[name] = tok["$value"].lower()
        for name in REQUIRED_COLORS:
            if name not in renk and not any(f"marka.renk.{name}" == x.yer for x in b):
                b.append(Bulgu(HATA, f"marka.renk.{name}", "zorunlu renk eksik"))

    ciftler = data.get("ciftler", [])
    if not isinstance(ciftler, list):
        b.append(Bulgu(HATA, "marka.ciftler", "liste olmalı"))
        ciftler = []
    has_text_pair = False
    for i, c in enumerate(ciftler):
        yer = f"marka.ciftler[{i}]"
        if not isinstance(c, dict) or not isinstance(c.get("on"), str) or not isinstance(c.get("zemin"), str):
            b.append(Bulgu(HATA, yer, '{"on": <renk>, "zemin": <renk>} olmalı'))
            continue
        en_az = c.get("en_az", CONTRAST_TEXT)
        if not isinstance(en_az, (int, float)) or isinstance(en_az, bool) or en_az < CONTRAST_LARGE:
            b.append(Bulgu(HATA, yer, f"en_az en az {CONTRAST_LARGE} olmalı"))
            continue
        missing = [r for r in (c["on"], c["zemin"]) if r not in renk]
        if missing:
            b.append(Bulgu(HATA, yer, f"tanımsız renk: {', '.join(missing)}"))
            continue
        ratio = contrast_ratio(renk[c["on"]], renk[c["zemin"]])
        if ratio < en_az:
            b.append(Bulgu(HATA, yer, f"{c['zemin']} üstünde {c['on']} kontrastı {ratio:.2f}, en az {en_az:g}"))
        has_text_pair |= (c["on"], c["zemin"]) == ("metin", "zemin")
    if all(r in renk for r in REQUIRED_COLORS) and not has_text_pair:
        ratio = contrast_ratio(renk["metin"], renk["zemin"])
        if ratio < CONTRAST_TEXT:
            b.append(Bulgu(HATA, "marka.renk", f"zemin üstünde metin kontrastı {ratio:.2f}, en az {CONTRAST_TEXT}"))

    yazi = data.get("yazi")
    if not isinstance(yazi, dict):
        b.append(Bulgu(HATA, "marka.yazi", "nesne olmalı"))
        yazi = {}
    for name in REQUIRED_TYPE:
        if name not in yazi:
            b.append(Bulgu(HATA, f"marka.yazi.{name}", "zorunlu yazı rolü eksik"))
    for name, stil in yazi.items():
        if name.startswith("$"):
            continue
        yer = f"marka.yazi.{name}"
        aile = stil.get("aile", {}).get("$value") if isinstance(stil, dict) and isinstance(stil.get("aile"), dict) else None
        if not isinstance(aile, str) or not aile.strip():
            b.append(Bulgu(HATA, yer, 'aile {"$type": "fontFamily", "$value": "..."} olmalı'))
        agirlik = stil.get("agirlik", {}).get("$value", 400) if isinstance(stil, dict) and isinstance(stil.get("agirlik"), dict) else 400
        if not isinstance(agirlik, int) or isinstance(agirlik, bool) or agirlik % 100 or not 100 <= agirlik <= 900:
            b.append(Bulgu(HATA, yer, f"agirlik 100–900 arası yüzlük olmalı, {agirlik!r} geldi"))

    hareket = data.get("hareket", {})
    if not isinstance(hareket, dict):
        b.append(Bulgu(HATA, "marka.hareket", "nesne olmalı"))
    else:
        for name, tok in _tokens(hareket):
            yer = f"marka.hareket.{name}"
            t = tok.get("$type") if isinstance(tok, dict) else None
            v = tok.get("$value") if isinstance(tok, dict) else None
            if t == "duration" and not (isinstance(v, str) and _DURATION.match(v)):
                b.append(Bulgu(HATA, yer, f"süre '400ms' ya da '0.4s' olmalı, {v!r} geldi"))
            elif t == "cubicBezier" and not (isinstance(v, list) and len(v) == 4
                                             and all(isinstance(x, (int, float)) for x in v)
                                             and 0 <= v[0] <= 1 and 0 <= v[2] <= 1):
                b.append(Bulgu(HATA, yer, "cubicBezier dört sayı olmalı, x değerleri 0–1"))
            elif t not in ("duration", "cubicBezier"):
                b.append(Bulgu(HATA, yer, "$type duration ya da cubicBezier olmalı"))

    ses = data.get("ses", {})
    if not isinstance(ses, dict):
        b.append(Bulgu(HATA, "marka.ses", "nesne olmalı"))
    else:
        for key in ("ton", "yasak"):
            v = ses.get(key, [])
            if not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
                b.append(Bulgu(HATA, f"marka.ses.{key}", "boş olmayan metinlerden oluşan liste olmalı"))
        if not ses.get("ton"):
            b.append(Bulgu(UYARI, "marka.ses.ton", "marka sesi tanımsız; metin neye göre yazılacak?"))

    logo = data.get("logo", {})
    if not isinstance(logo, dict):
        b.append(Bulgu(HATA, "marka.logo", "nesne olmalı"))
    elif logo.get("dosya"):
        path = (kok or Path(".")) / logo["dosya"]
        if not path.exists():
            b.append(Bulgu(HATA, "marka.logo.dosya", f"dosya yok: {logo['dosya']}"))
    elif not logo.get("metin"):
        b.append(Bulgu(UYARI, "marka.logo", "ne dosya ne metin var; animatikte logo görünmez"))

    prompt = data.get("prompt", {})
    if not isinstance(prompt, dict):
        b.append(Bulgu(HATA, "marka.prompt", "nesne olmalı"))
    return b


def ayristir(data: dict) -> Marka:
    """`denetle` HATA vermediyse çağrılır."""
    renk = {n: t["$value"].lower() for n, t in _tokens(data["renk"])}
    yazi = {n: YaziStili(s["aile"]["$value"], s.get("agirlik", {}).get("$value", 400))
            for n, s in data["yazi"].items() if not n.startswith("$")}
    ses, logo, prompt = data.get("ses", {}), data.get("logo", {}), data.get("prompt", {})
    return Marka(
        kimlik=data["kimlik"],
        ad=data["ad"],
        renk=renk,
        yazi=yazi,
        ciftler=tuple((c["on"], c["zemin"], c.get("en_az", CONTRAST_TEXT)) for c in data.get("ciftler", [])),
        hareket={n: t["$value"] for n, t in _tokens(data.get("hareket", {}))},
        ton=tuple(ses.get("ton", [])),
        yasak=tuple(ses.get("yasak", [])),
        logo_metin=logo.get("metin", ""),
        logo_dosya=logo.get("dosya", ""),
        prompt_uslup=prompt.get("uslup", ""),
        prompt_negatif=tuple(prompt.get("negatif", [])),
    )


def yukle(path: str | Path) -> tuple[Marka | None, list[Bulgu]]:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [Bulgu(HATA, str(path), "dosya yok")]
    except json.JSONDecodeError as e:
        return None, [Bulgu(HATA, str(path), f"geçersiz JSON (satır {e.lineno}): {e.msg}")]
    bulgular = denetle(data, path.parent)
    return (None if has_errors(bulgular) else ayristir(data)), bulgular


# --- dışa aktarıcılar ---------------------------------------------------------

def _css_name(name: str) -> str:
    return name.replace(".", "-").replace("_", "-")


def _css_value(value: object) -> str:
    if isinstance(value, list):
        return "cubic-bezier(" + ", ".join(f"{x:g}" for x in value) + ")"
    return str(value)


def _vars(m: Marka) -> list[tuple[str, str]]:
    out = [(f"renk-{_css_name(n)}", v) for n, v in m.renk.items()]
    for n, s in m.yazi.items():
        out.append((f"yazi-{_css_name(n)}-aile", json.dumps(s.aile, ensure_ascii=False)))
        out.append((f"yazi-{_css_name(n)}-agirlik", str(s.agirlik)))
    out += [(f"hareket-{_css_name(n)}", _css_value(v)) for n, v in m.hareket.items()]
    return out


def to_css(m: Marka) -> str:
    """Web, HTML şablonları, Orshot."""
    lines = [f"/* {m.ad} · platform/marka tarafından üretildi, elle düzenlemeyin. */", ":root {"]
    lines += [f"  --{k}: {v};" for k, v in _vars(m)]
    return "\n".join(lines + ["}"]) + "\n"


def to_unity_uss(m: Marka) -> str:
    """Unity UI Toolkit: USS özel özellikleri. Unity yalnız renk ve sayıyı okur."""
    lines = [f"/* {m.ad} · platform/marka tarafından üretildi, elle düzenlemeyin. */", ":root {"]
    lines += [f"  --{k}: {v};" for k, v in _vars(m) if not k.startswith("hareket-")]
    return "\n".join(lines + ["}"]) + "\n"


def to_unity_json(m: Marka) -> str:
    """`BrandTokens.asset` için veri: renkler 0–1 aralığında RGBA."""
    doc = {
        "kimlik": m.kimlik,
        "renk": {n: [round(c / 255, 4) for c in to_rgb(v)] + [1.0] for n, v in m.renk.items()},
        "yazi": {n: {"aile": s.aile, "agirlik": s.agirlik} for n, s in m.yazi.items()},
        "hareket": m.hareket,
    }
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def to_figma(m: Marka) -> str:
    """Figma değişkenleri / Tokens Studio: W3C DTCG belgesi."""
    def nest(target: dict, dotted: str, token: dict) -> None:
        *parents, leaf = dotted.split(".")
        for p in parents:
            target = target.setdefault(p, {})
        target[leaf] = token

    doc: dict = {"$description": f"{m.ad} · platform/marka"}
    for n, v in m.renk.items():
        nest(doc.setdefault("renk", {}), n, {"$type": "color", "$value": v})
    for n, s in m.yazi.items():
        doc.setdefault("yazi", {})[n] = {"aile": {"$type": "fontFamily", "$value": s.aile},
                                         "agirlik": {"$type": "fontWeight", "$value": s.agirlik}}
    for n, v in m.hareket.items():
        nest(doc.setdefault("hareket", {}), n,
             {"$type": "cubicBezier" if isinstance(v, list) else "duration", "$value": v})
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def to_prompt(m: Marka) -> str:
    """Flow / Imagen / Veo için ortak üslup bloğu."""
    lines = []
    if m.prompt_uslup:
        lines.append(m.prompt_uslup.strip())
    lines.append("Palet: " + ", ".join(f"{n} {v}" for n, v in m.renk.items()) + ".")
    if m.ton:
        lines.append("Ton: " + ", ".join(m.ton) + ".")
    if m.prompt_negatif:
        lines.append("Kaçın: " + ", ".join(m.prompt_negatif) + ".")
    return "\n".join(lines) + "\n"


EXPORTERS = {
    "css": to_css,
    "figma": to_figma,
    "unity-uss": to_unity_uss,
    "unity-json": to_unity_json,
    "prompt": to_prompt,
}
EXPORT_FILES = {"css": "tokens.css", "figma": "figma.json", "unity-uss": "unity.uss",
                "unity-json": "unity.json", "prompt": "prompt.txt"}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 2 and args[0] == "denetle":
        _, bulgular = yukle(args[1])
        for x in bulgular:
            print(x)
        print(f"HATA: {sum(x.seviye == HATA for x in bulgular)} · UYARI: {sum(x.seviye == UYARI for x in bulgular)}")
        return 1 if has_errors(bulgular) else 0
    if len(args) == 3 and args[0] == "aktar" and args[1] in EXPORTERS:
        m, bulgular = yukle(args[2])
        if m is None:
            for x in bulgular:
                print(x, file=sys.stderr)
            return 1
        sys.stdout.write(EXPORTERS[args[1]](m))
        return 0
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

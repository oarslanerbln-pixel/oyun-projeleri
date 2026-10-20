"""Ortak sahne dilinden kendi senaryo biçimi olan stillere çevirici (desen: vitray, linol, çini, teknik çizim;
ekran: kalkış tabelası, VHS, akış alanı). Zamanlama ve seslendirme satırları aynı kalır (aynı kimlikler, aynı
önbellek); yalnız ekran yazıları hedefin alanlarına yerleşir. Yazı hedefe sığmıyorsa kesilmez, hata döner.

Geçiş sahneleri bir önceki sahneye katılır. Sahneye özel ayar: `"stiller": {"vitray": {"motif": "kalp"}}`.
"""

from __future__ import annotations

from pathlib import Path

DESEN = ("vitray", "linol", "cini", "teknik-cizim")
EKRAN = ("kalkis-tabelasi", "vhs", "akis-alani")
STILLER = DESEN + EKRAN
MOTIF = {"baslik": "gunes", "liste": "yaprak", "sayi": "ampul", "alinti": "kalp", "karsilastirma": "dag",
         "urun": "fincan", "cta": "yildiz", "grafik": "dag", "harita": "dag"}


def _vurgu(metin: str) -> str:
    """Son sözcüğü vurgular (ekran stillerinde vurgulu öbek bölünmez; tek sözcük tabelaya sığar)."""
    k = metin.rsplit(" ", 1)
    return f"{k[0]} *{k[1]}*" if len(k) == 2 else f"*{metin}*"


def _yazilar(sh: dict) -> tuple[str, str, str]:
    """(ana yazı, alt satır, vurgulu ana yazı) — ekran stillerinde *...* vurgudur."""
    t = sh["tip"]
    if t == "baslik":
        return sh["metin"], sh.get("alt", ""), sh["metin"]
    if t == "liste":  # desen: başlık + maddeler alt satırda; ekran: maddeler alt alta, başlık alt satırda
        bas = sh.get("baslik") or sh["maddeler"][0]
        alt = " · ".join(sh["maddeler"] if sh.get("baslik") else sh["maddeler"][1:])
        return bas, alt, "\n".join(sh["maddeler"])
    if t == "sayi":
        return sh["deger"], sh.get("etiket", ""), f"*{sh['deger']}*" + (f" {sh['ust']}" if sh.get("ust") else "")
    if t == "alinti":
        return sh["metin"], sh.get("kaynak", ""), sh["metin"]
    if t == "karsilastirma":
        sag = sh.get("sag_deger") or sh["sag"]
        sol = f"{sh['sol_deger']} {sh['sol']}" if sh.get("sol_deger") else sh["sol"]
        return sag, f"{sol} → {sh['sag']}" if sh.get("sag_deger") else sol + " →", f"{sh['sol']}\n{_vurgu(sh['sag'])}"
    if t == "urun":
        alt = " · ".join(x for x in (sh.get("ozellik"), sh.get("fiyat")) if x)
        return sh["ad"], alt, _vurgu(sh["ad"])
    if t == "cta":
        return sh["metin"], sh.get("alt", ""), _vurgu(sh["metin"])
    if t == "grafik":  # desen/ekran stilleri grafik çizmez: en yüksek değer başlık olur
        from dil import bicim, veri_oku
        e, v = max(veri_oku(sh, sh.get("_klasor", ".")), key=lambda r: r[1])
        deger = bicim(v, sh.get("birim", ""))
        return deger, f"{e} · {sh['baslik']}" if sh.get("baslik") else e, f"*{deger}* {e}"
    if t == "harita":  # desen/ekran stilleri harita çizmez: rota yazıyla, ilk ve son durak başlıkta
        ad = [d if isinstance(d, str) else d.get("etiket", d["ad"]) for d in sh["duraklar"]]
        ad = [x.split(",")[0].strip() for x in ad]
        bas = sh.get("baslik") or f"{ad[0]} → {ad[-1]}"
        return bas, " · ".join(ad), f"*{ad[0]}* → {ad[-1]}"
    return sh.get("metin", ""), "", sh.get("metin", "")


def cevir(z: dict, stil: str) -> dict:
    """z: dil.zamanla() çıktısı. Hedef stilin senaryosu (sözlük); `_klasor` çağıran yazar."""
    if stil not in STILLER:
        raise ValueError(f"çevirici yok: {stil} ({', '.join(STILLER)})")
    klasor = Path(z.get("_klasor", "."))
    shs = [{**sh, "_klasor": str(klasor)} for sh in z["sahneler"] if sh["tip"] != "gecis"]
    ana = {"kimlik": f"{z.get('kimlik', 'sahne')}-{stil}", "stil": stil, "sure": z["sure"], "fps": z.get("fps", 30),
           "seslendirme": z["seslendirme"]}
    if z.get("format"):
        f = z["format"]
        ana["format"] = f.replace(":", "x") if isinstance(f, str) else [x.replace(":", "x") for x in f]
    if stil in DESEN:
        out = []
        for sh in shs:
            bas, alt, _ = _yazilar(sh)
            x = {"t": sh["bas"], "motif": (sh.get("stiller") or {}).get(stil, {}).get("motif", MOTIF[sh["tip"]]), "baslik": bas}
            if alt:
                x["alt"] = alt
            out.append(x)
        out[0]["t"] = 0
        ana["sahneler"] = out
        logo = (z.get("marka") or {}).get("logo")
        if logo:
            ana["gorsel"] = {"dosya": str((klasor / logo).resolve())}
        if (z.get("marka") or {}).get("ad"):
            ana["imza"] = z["marka"]["ad"][:24]
    else:
        out = []
        for sh in shs:
            _, alt, vurgulu = _yazilar(sh)
            if sh["tip"] == "liste":
                alt = sh.get("baslik", "")
            elif sh["tip"] == "karsilastirma":
                alt = f"{sh['sol_deger']} / {sh['sag_deger']}" if sh.get("sol_deger") and sh.get("sag_deger") else ""
            x = {"bas": sh["bas"], "metin": vurgulu}
            if alt:
                x["alt"] = alt
            out.append(x)
        out[0]["bas"] = 0
        ana["sahneler"] = out
        if stil == "kalkis-tabelasi":
            ana["baslik"] = (z.get("marka") or {}).get("ad", "Kalkış")
    return ana


def yaz(z: dict, stil: str, hedef: Path) -> Path:
    """Çevrilen senaryoyu `hedef` dosyasına yazar (görsel yolları mutlak, böylece hedef her klasörde çalışır)."""
    import json
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps(cevir(z, stil), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return hedef


def modul_klasoru(stil: str) -> Path:
    return Path(__file__).resolve().parents[1] / ("desen" if stil in DESEN else "ekran")


def denetle(z: dict, stil: str) -> list[str]:
    """Çevrilen senaryoyu hedefin kendi denetimiyle sınar (seslendirme dosyası gerekmez)."""
    import importlib.util
    import sys
    import tempfile
    d = modul_klasoru(stil)
    sys.path.insert(0, str(d))
    try:
        sp = importlib.util.spec_from_file_location(f"_{d.name}_zaman", d / "zaman.py")
        m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as g:
            s = m.yukle(yaz(z, stil, Path(g) / "s.json"))
            return [f"{stil}: {x}" for x in m.denetle(s, {})]
    finally:
        sys.path.remove(str(d))

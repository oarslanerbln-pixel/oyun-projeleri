"""Sayfa kapısı: panel, açılış sayfası ya da HTML teslimini gerçek tarayıcıda açıp makine kontrol eder.

Sayfa iki ekranda açılır (telefon 390×844 @3x, masaüstü 1440×900 @2x, açık tema) ve her ekranda
bakılır: yatay kaydırma, ekrandan taşan öğe, kutusuna sığmayıp kesilen yazı, düşük kontrast,
telefonda çok küçük yazı ve dokunma hedefi, kırık ya da büyütülüp bulanıklaşan görsel, konsol
hataları ve yüklenemeyen dosyalar. Sonunda tek kontakt sayfası çıkar: iki ekranın tam sayfa görüntüsü,
sorunlu öğeler kırmızı (hata) ya da turuncu kesikli (uyarı) çerçeveli.

    python3 platform/ortak/sayfa.py panel.html [https://… ...] [--kontakt k.png] [--bekle 800] [--json]

Dosya verilince yanına `<ad>.sayfa.json` ve `<ad>.sayfa.png` yazılır (`--kontakt` başka yol seçer).
Çıkış kodu: 0 geçti (uyarı olabilir), 1 en az bir hata var. Gerekenler: Python Playwright ve Chromium
(bulut oturumlarında hazır; CI `ci.json` ile kurar), Pillow (kontakt sayfası için).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EKRANLAR = {
    "telefon": {"genislik": 390, "yukseklik": 844, "dpr": 3, "mobil": True},
    "masaustu": {"genislik": 1440, "yukseklik": 900, "dpr": 2, "mobil": False},
}
ESIK = {
    "kontrast": 4.5,            # WCAG AA, normal yazı; altı uyarı
    "kontrast_buyuk": 3.0,      # 24 px ya da 18.66 px kalın üstü yazı
    "kontrast_hata": 2.0,       # altı okunmaz: hata
    "yazi_px": 12,              # telefonda bunun altı uyarı
    "dokunma_px": 44,           # Apple HIG; telefonda dokunma hedefinin kısa kenarı
    "gorsel_kat": 1.5,          # görselin doğal genişliği / ekrandaki genişlik (CSS px) bunun altında: bulanık
}
ORNEK = 6                       # her kontrolde rapora yazılan en çok örnek
KONTAKT = {"telefon": 450, "masaustu": 1000, "azami_yukseklik": 2600, "zemin": (247, 243, 232)}

# Sayfanın içinde koşan kontrol. Sorunlu öğeye data-sayfa-sorun yazar; kontakt görüntüsü onu çerçeveler.
OLCUM_JS = r"""
(esik) => {
  // yerleşim genişliği: telefon taklidinde taşan sayfa uzaklaşınca innerWidth büyür, clientWidth büyümez
  const W = document.documentElement.clientWidth, H = innerHeight, mobil = esik.mobil;
  const bul = {};
  const ekle = (kontrol, seviye, el, ayrinti) => {
    (bul[kontrol] ||= {seviye, sayi: 0, ornekler: []});
    const b = bul[kontrol];
    if (seviye === "hata") b.seviye = "hata";
    b.sayi++;
    if (b.ornekler.length < esik.ornek) b.ornekler.push(tarif(el) + (ayrinti ? " — " + ayrinti : ""));
    if (el && el.setAttribute && el !== document.documentElement && el !== document.body) {
      if (el.getAttribute("data-sayfa-sorun") !== "hata") el.setAttribute("data-sayfa-sorun", seviye);
    }
  };
  const tarif = (el) => {
    if (!el || !el.tagName) return "sayfa";
    let s = el.tagName.toLowerCase();
    if (el.id) s += "#" + el.id;
    else if (typeof el.className === "string" && el.className.trim()) s += "." + el.className.trim().split(/\s+/)[0];
    const t = (el.innerText || el.getAttribute("alt") || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ");
    return t ? `${s} "${t.slice(0, 40)}${t.length > 40 ? "…" : ""}"` : s;
  };
  const gorunur = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    return el.checkVisibility ? el.checkVisibility({opacityProperty: true, visibilityProperty: true}) : true;
  };
  const kendiYazisi = (el) => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
  const kirpar = (el, eksen) => {
    const cs = getComputedStyle(el);
    const o = eksen === "x" ? cs.overflowX : cs.overflowY;
    return o !== "visible";
  };

  // 1. yatay kaydırma
  const sw = Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0);
  if (sw > W + 1) ekle("yatay_kaydirma", "hata", null, `sayfa ${sw} px, ekran ${W} px`);

  // 2. kontrol edilecek öğeler: kendi yazısı olanlar ve görsel/denetim öğeleri
  const hepsi = [...document.querySelectorAll("body *")].filter(el =>
    !["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "HEAD", "META", "LINK", "BR"].includes(el.tagName));
  const yazili = [], ogeler = [];
  for (const el of hepsi) {
    if (!gorunur(el)) continue;
    const y = kendiYazisi(el);
    if (y) yazili.push(el);
    if (y || ["IMG", "SVG", "VIDEO", "CANVAS", "BUTTON", "INPUT", "SELECT", "TEXTAREA", "IFRAME"].includes(el.tagName.toUpperCase())) ogeler.push(el);
  }

  // 3. ekrandan taşan öğe (kaydırılabilir ya da kırpan bir kabın içindekiler sayılmaz)
  for (const el of ogeler) {
    const r = el.getBoundingClientRect();
    if (r.right <= W + 1 && r.left >= -1) continue;
    let kap = false;
    for (let a = el.parentElement; a && a !== document.body && a !== document.documentElement; a = a.parentElement)
      if (kirpar(a, "x")) { kap = true; break; }
    if (!kap) ekle("ekrandan_tasan", "hata", el, `${Math.round(r.left)}…${Math.round(r.right)} px, ekran ${W} px`);
  }

  // 4. kutusuna sığmayıp kesilen yazı
  for (const el of yazili) {
    const cs = getComputedStyle(el);
    if (cs.textOverflow === "ellipsis" && el.scrollWidth > el.clientWidth + 1) {
      ekle("kesilen_yazi", "uyari", el, "üç noktayla kısaltılmış"); continue;
    }
    const r = el.getBoundingClientRect();
    for (let a = el; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
      const ar = a === el ? null : a.getBoundingClientRect();
      if (a === el) {
        if ((kirpar(el, "x") && el.scrollWidth > el.clientWidth + 1) || (kirpar(el, "y") && el.scrollHeight > el.clientHeight + 1)) {
          ekle("kesilen_yazi", "uyari", el, "kendi kutusuna sığmıyor"); break;
        }
        continue;
      }
      const tx = kirpar(a, "x") && (r.left < ar.left - 1 || r.right > ar.right + 1);
      const ty = kirpar(a, "y") && (r.top < ar.top - 1 || r.bottom > ar.bottom + 1);
      if (tx || ty) {
        const cs2 = getComputedStyle(a);
        // kaydırılabilen kap (liste, tablo) kesmez; gizleyen kap keser
        const kayar = (tx && ["auto", "scroll"].includes(cs2.overflowX)) || (ty && ["auto", "scroll"].includes(cs2.overflowY));
        if (!kayar) ekle("kesilen_yazi", "uyari", el, "kabı yazıyı kesiyor: " + tarif(a).split(" ")[0]);
        break;
      }
    }
  }

  // 5. kontrast: renk 1×1 tuvalde sRGB'ye çevrilir (oklch, color-mix vb. de çalışsın)
  const tuval = document.createElement("canvas"); tuval.width = tuval.height = 1;
  const cx = tuval.getContext("2d", {willReadFrequently: true});
  const rgba = (s) => { cx.clearRect(0, 0, 1, 1); cx.fillStyle = "#000"; cx.fillStyle = s; cx.fillRect(0, 0, 1, 1);
    const d = cx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  const ust = (on, alt) => { const a = on[3]; return [on[0] * a + alt[0] * (1 - a), on[1] * a + alt[1] * (1 - a), on[2] * a + alt[2] * (1 - a), 1]; };
  const zemin = (el) => {
    const katman = [];
    for (let a = el; a; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (cs.backgroundImage && cs.backgroundImage !== "none") return null;   // degrade/görsel zemin: ölçülmez
      const c = rgba(cs.backgroundColor);
      if (c[3] > 0) { katman.push(c); if (c[3] >= 0.999) break; }
    }
    let z = [255, 255, 255, 1];
    for (let i = katman.length - 1; i >= 0; i--) z = ust(katman[i], z);
    return z;
  };
  const isik = (c) => { const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  for (const el of yazili) {
    const cs = getComputedStyle(el);
    const z = zemin(el);
    if (!z) continue;
    const y = ust(rgba(cs.color), z);
    const L1 = isik(y), L2 = isik(z);
    const oran = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const px = parseFloat(cs.fontSize), kalin = parseInt(cs.fontWeight) >= 700;
    const buyuk = px >= 24 || (px >= 18.66 && kalin);
    const sinir = buyuk ? esik.kontrast_buyuk : esik.kontrast;
    if (oran < esik.kontrast_hata) ekle("kontrast", "hata", el, `oran ${oran.toFixed(1)}:1`);
    else if (oran < sinir) ekle("kontrast", "uyari", el, `oran ${oran.toFixed(1)}:1, en az ${sinir}:1`);
  }

  // 6. telefonda küçük yazı ve dokunma hedefi
  if (mobil) {
    for (const el of yazili) {
      const px = parseFloat(getComputedStyle(el).fontSize);
      if (px < esik.yazi_px) ekle("kucuk_yazi", "uyari", el, `${px} px`);
    }
    const hedefler = document.querySelectorAll("button, select, textarea, input:not([type=hidden]), [role=button], a[href]");
    for (const el of hedefler) {
      if (!gorunur(el)) continue;
      if (el.tagName === "A" && getComputedStyle(el).display === "inline") continue;   // yazı içi bağlantı
      const r = el.getBoundingClientRect();
      if (Math.min(r.width, r.height) < esik.dokunma) ekle("dokunma_hedefi", "uyari", el, `${Math.round(r.width)}×${Math.round(r.height)} px`);
    }
  }

  // 7. görseller: kırık ya da ekranda büyütülmüş
  for (const img of document.images) {
    if (!gorunur(img)) continue;
    const src = img.currentSrc || img.src || "";
    if (img.complete && img.naturalWidth === 0) { ekle("kirik_gorsel", "hata", img, src.slice(-60)); continue; }
    if (/\.svg($|\?)|^data:image\/svg/i.test(src)) continue;
    const r = img.getBoundingClientRect();
    if (img.naturalWidth && img.naturalWidth < r.width * esik.gorsel_kat)
      ekle("dusuk_cozunurluk", "uyari", img, `doğal ${img.naturalWidth} px, ekranda ${Math.round(r.width)} px`);
  }

  return {genislik: W, yukseklik: H, sayfa_yukseklik: document.documentElement.scrollHeight, bulgular: bul};
}
"""

ISARET_CSS = """
[data-sayfa-sorun=hata] { outline: 3px solid #e5242b !important; outline-offset: -1px !important; }
[data-sayfa-sorun=uyari] { outline: 3px dashed #f08c00 !important; outline-offset: -1px !important; }
"""

ADLAR = {
    "yatay_kaydirma": "yatay kaydırma",
    "ekrandan_tasan": "ekrandan taşan öğe",
    "kesilen_yazi": "kesilen yazı",
    "kontrast": "kontrast",
    "kucuk_yazi": "küçük yazı",
    "dokunma_hedefi": "küçük dokunma hedefi",
    "kirik_gorsel": "kırık görsel",
    "dusuk_cozunurluk": "düşük çözünürlüklü görsel",
    "konsol": "konsol hatası",
    "yuklenemeyen": "yüklenemeyen dosya",
}


def _adres(hedef: str) -> str:
    if "://" in hedef:
        return hedef
    return Path(hedef).resolve().as_uri()


def _bul(seviye: str, kontrol: str, mesaj: str, ekran: str, ornekler: list[str] | None = None) -> dict:
    return {"seviye": seviye, "kontrol": kontrol, "ekran": ekran, "mesaj": mesaj, "ornekler": ornekler or []}


def ekran_denetle(tarayici, adres: str, ekran: str, bekle_ms: int) -> tuple[list[dict], dict, bytes]:
    e = EKRANLAR[ekran]
    bag = tarayici.new_context(viewport={"width": e["genislik"], "height": e["yukseklik"]},
                               device_scale_factor=e["dpr"], is_mobile=e["mobil"], has_touch=e["mobil"],
                               color_scheme="light", locale="tr-TR")
    sayfa = bag.new_page()
    konsol: list[str] = []
    yuklenemeyen: list[str] = []
    # "Failed to load resource" satırları yüklenemeyen dosyalarda zaten sayılır
    sayfa.on("console", lambda m: konsol.append(m.text[:160])
             if m.type == "error" and not m.text.startswith("Failed to load resource") else None)
    sayfa.on("pageerror", lambda h: konsol.append(str(h)[:160]))
    sayfa.on("requestfailed", lambda r: yuklenemeyen.append(f"{r.url[:90]} ({r.failure})"))
    sayfa.on("response", lambda r: yuklenemeyen.append(f"{r.url[:90]} (HTTP {r.status})") if r.status >= 400 else None)
    try:
        sayfa.goto(adres, wait_until="load", timeout=30_000)
        sayfa.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
        sayfa.wait_for_timeout(bekle_ms)
        olcum = sayfa.evaluate(OLCUM_JS, {**ESIK, "mobil": e["mobil"], "ornek": ORNEK,
                                          "dokunma": ESIK["dokunma_px"]})
        sayfa.add_style_tag(content=ISARET_CSS)
        goruntu = sayfa.screenshot(full_page=True, animations="disabled")
    finally:
        bag.close()
    bulgular = []
    for kontrol, b in olcum.pop("bulgular").items():
        bulgular.append(_bul(b["seviye"], kontrol, f"{b['sayi']} öğe" if kontrol != "yatay_kaydirma" else "sayfa yana kayıyor", ekran, b["ornekler"]))
    if konsol:
        bulgular.append(_bul("uyari", "konsol", f"{len(konsol)} hata", ekran, konsol[:ORNEK]))
    if yuklenemeyen:
        bulgular.append(_bul("uyari", "yuklenemeyen", f"{len(yuklenemeyen)} dosya (ağ izni kapalı olabilir)", ekran,
                             sorted(set(yuklenemeyen))[:ORNEK]))
    return bulgular, olcum, goruntu


def kontakt_yaz(goruntuler: dict[str, bytes], hedef: Path, baslik: str) -> Path | None:
    try:
        import io
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    try:
        yazi = ImageFont.load_default(size=22)
    except TypeError:  # Pillow < 10.1
        yazi = ImageFont.load_default()
    paneller = []
    for ekran, veri in goruntuler.items():
        im = Image.open(io.BytesIO(veri)).convert("RGB")
        w = KONTAKT[ekran]
        h = max(1, round(im.height * w / im.width))
        im = im.resize((w, h), Image.LANCZOS)
        if h > KONTAKT["azami_yukseklik"]:
            im = im.crop((0, 0, w, KONTAKT["azami_yukseklik"]))
        paneller.append((ekran, im, h))
    bosluk, ust = 32, 84
    W = sum(p[1].width for p in paneller) + bosluk * (len(paneller) + 1)
    H = max(p[1].height for p in paneller) + ust + bosluk
    sayfa = Image.new("RGB", (W, H), KONTAKT["zemin"])
    d = ImageDraw.Draw(sayfa)
    d.text((bosluk, 12), baslik, fill=(20, 20, 20), font=yazi)
    x = bosluk
    for ekran, im, h in paneller:
        e = EKRANLAR[ekran]
        not_ = f"{ekran} {e['genislik']}x{e['yukseklik']} @{e['dpr']}x" + (" (kesildi)" if h > im.height else "")
        d.text((x, ust - 30), not_, fill=(90, 90, 90), font=yazi)
        sayfa.paste(im, (x, ust))
        d.rectangle((x - 1, ust - 1, x + im.width, ust + im.height), outline=(200, 195, 180))
        x += im.width + bosluk
    hedef.parent.mkdir(parents=True, exist_ok=True)
    sayfa.save(hedef, optimize=True)
    return hedef


def denetle(hedef: str, kontakt: str | Path | None = None, bekle_ms: int = 800,
            ekranlar: tuple[str, ...] = tuple(EKRANLAR)) -> dict:
    from playwright.sync_api import sync_playwright
    adres = _adres(hedef)
    bulgular: list[dict] = []
    olcum: dict = {}
    goruntuler: dict[str, bytes] = {}
    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        try:
            for ekran in ekranlar:
                b, o, g = ekran_denetle(tarayici, adres, ekran, bekle_ms)
                bulgular += b
                olcum[ekran] = o
                goruntuler[ekran] = g
        finally:
            tarayici.close()
    k = kontakt_yaz(goruntuler, Path(kontakt), Path(hedef).name if "://" not in hedef else hedef) if kontakt else None
    sev = {x["seviye"] for x in bulgular}
    sonuc = "kaldi" if "hata" in sev else ("uyarili" if "uyari" in sev else "gecti")
    return {"dosya": hedef, "sonuc": sonuc, "olcum": olcum, "bulgular": bulgular, "kontakt": str(k) if k else None}


ETIKET = {"gecti": "GEÇTİ", "uyarili": "GEÇTİ (uyarılı)", "kaldi": "KALDI"}
ISARET = {"hata": "HATA ", "uyari": "UYARI"}


def ozet(r: dict) -> str:
    satir = [f"{ETIKET[r['sonuc']]}: {r['dosya']}"]
    for x in sorted(r["bulgular"], key=lambda b: (b["seviye"] != "hata", b["ekran"])):
        satir.append(f"  {ISARET[x['seviye']]} {x['ekran']}, {ADLAR.get(x['kontrol'], x['kontrol'])}: {x['mesaj']}")
        satir += [f"        {o}" for o in x["ornekler"][:3]]
    if r.get("kontakt"):
        satir.append(f"  kontakt sayfası: {r['kontakt']}")
    return "\n".join(satir)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("sayfa", nargs="+", help="HTML dosyası ya da adres")
    ap.add_argument("--kontakt", help="kontakt sayfası yolu (birden çok sayfada klasör)")
    ap.add_argument("--bekle", type=int, default=800, help="yüklemeden sonra bekleme, ms (giriş animasyonları için)")
    ap.add_argument("--ekran", nargs="+", choices=list(EKRANLAR), default=list(EKRANLAR))
    ap.add_argument("--json", action="store_true", help="raporu JSON bas, dosya yazma")
    a = ap.parse_args(argv)
    kod = 0
    raporlar = []
    for s in a.sayfa:
        dosya = "://" not in s
        ad = Path(s).stem if dosya else "sayfa"
        if a.kontakt:
            k = Path(a.kontakt) / f"{ad}.sayfa.png" if len(a.sayfa) > 1 else Path(a.kontakt)
        elif dosya and not a.json:
            k = Path(s).with_suffix(".sayfa.png")
        else:
            k = None
        r = denetle(s, k, a.bekle, tuple(a.ekran))
        raporlar.append(r)
        if dosya and not a.json:
            Path(s).with_suffix(".sayfa.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        if not a.json:
            print(ozet(r))
        if r["sonuc"] == "kaldi":
            kod = 1
    if a.json:
        print(json.dumps(raporlar if len(raporlar) > 1 else raporlar[0], ensure_ascii=False, indent=1))
    return kod


if __name__ == "__main__":
    sys.exit(main())

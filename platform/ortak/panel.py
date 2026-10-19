"""Stüdyo paneli ile sipariş akışı arasındaki bağ (beyin fırtınası 4.2).

Panel (https://claude.ai/artifact/Rpwozz6cNbi3XCHjQTDkxy) siparişleri kendi veritabanında tutar
(`siparisler` koleksiyonu). Thread siparişi `ArtifactData` aracıyla okur, bu komut onu sipariş klasörüne
çevirir; `uret.py` her aşamada klasöre `panel-durum.json` yazar, thread onu aynı araçla panele geri yazar.

    python3 platform/ortak/panel.py siparis kayit.json        # panel kaydı → PF/<is>/siparis.json + brif.md (+ örnek senaryo)
    python3 platform/ortak/panel.py durum PF/<is>/siparis.json  # panele yazılacak alanlar (panel-durum.json)

`kayit.json`, `ArtifactData get` (collection "siparisler") sonucunun kendisidir: baslik, detay, tur, format,
tarz, dil, ses, muzik, sure, kime, teslim alanları ve belge kimliği (`id`, `_id` ya da `--id`).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

BURADA = Path(__file__).resolve().parent
DEPO = BURADA.parents[1]
PANEL_URL = "https://claude.ai/artifact/Rpwozz6cNbi3XCHjQTDkxy"
KOLEKSIYON = "siparisler"
DOSYA = "panel-durum.json"

# panelin tarz kimliği → şablon stili (aynı olanlar yazılmaz)
TARZ_STIL = {"3d": "oyuncak", "analiz": "analiz"}
DIL = {"türkçe": "tr", "turkce": "tr", "almanca": "de", "deutsch": "de", "ingilizce": "en", "english": "en"}
SURE_VARSAYILAN = {"kisa": 30, "reklam": 15, "uzun": 300}

# uret.py aşaması → panel durumu (panelin SDURUM listesi) ve kısa not
ASAMA = {
    "onizleme": ("onay", "Senaryo ve önizleme hazır, onayını bekliyor."),
    "senaryo-hatali": ("senaryo", "Senaryo düzeltiliyor."),
    "onizleme-hatali": ("senaryo", "Önizleme çizilemedi, senaryo düzeltiliyor."),
    "onaylandi": ("uretimde", "Onaylandı: ses ve render sürüyor."),
    "ses-hatali": ("uretimde", "Seslendirmede sorun var, Claude düzeltiyor."),
    "ses-yedek": ("uretimde", "ElevenLabs'e ulaşılamadı; yedek ses teslim edilmez, bekliyor."),
    "render-hatali": ("uretimde", "Render hata verdi, Claude düzeltiyor."),
    "kaldi": ("uretimde", "Kalite kapısından geçmedi, düzeltiliyor."),
    "teslim": ("hazir", "Teslim edildi."),
    "kapandi": ("hazir", "Teslim edildi."),
}


def kisa_ad(metin: str) -> str:
    katla = str.maketrans("çğıöşüâîûÇĞİÖŞÜÂÎÛ", "cgiosuaiuCGIOSUAIU")
    s = re.sub(r"[^a-z0-9]+", "-", metin.translate(katla).lower()).strip("-")
    return "-".join(s.split("-")[:5]) or "siparis"


def ornek_senaryo(stil: str) -> Path | None:
    """`ornekler/*/<stil>.json` (ilk bulunan; ortak sahne dili `sahne.json` hariç)."""
    adlar = {stil, stil.replace("-", "_")}
    for p in sorted((DEPO / "ornekler").glob("*/*.json")):
        if p.stem in adlar:
            return p
    return None


def siparis_yaz(kayit: dict, kok: Path, belge_id: str | None = None) -> Path:
    belge_id = belge_id or kayit.get("id") or kayit.get("_id")
    if not belge_id:
        raise ValueError("panel belge kimliği yok (kayıtta id/_id ya da --id)")
    is_adi = kisa_ad(kayit.get("baslik") or belge_id)
    klasor = kok / is_adi
    klasor.mkdir(parents=True, exist_ok=True)
    tarz = (kayit.get("tarz") or "").strip()
    stil = TARZ_STIL.get(tarz, tarz)
    dil = DIL.get(str(kayit.get("dil") or "").strip().lower(), "tr")
    ses = (kayit.get("ses") or "").strip()
    notlar = [f"panel siparişi {belge_id}"]
    for alan, etiket in (("tur", "tür"), ("muzik", "müzik"), ("kime", "kanal/müşteri"), ("teslim", "teslim tarihi")):
        if kayit.get(alan):
            notlar.append(f"{etiket}: {kayit[alan]}")
    s = {"is": is_adi, "baslik": kayit.get("baslik") or is_adi, "format": kayit.get("format") or "9:16",
         "dil": dil, "panel": {"url": PANEL_URL, "koleksiyon": KOLEKSIYON, "id": belge_id}, "notlar": notlar}
    if ses and ses not in ("yok", "var"):
        s["ses"] = {"ses": ses}
    if kayit.get("kime") and not re.match(r"(?i)kanal", str(kayit["kime"])):
        s["musteri"] = kayit["kime"]
    yazilan = []
    if stil:
        kaynak = ornek_senaryo(stil)
        if kaynak:
            hedef = klasor / f"{stil}.json"
            if not hedef.exists():  # thread'in düzenlediği senaryoyu ezme
                shutil.copy(kaynak, hedef)
                yazilan.append(f"{hedef.name} ← {kaynak.relative_to(DEPO)} (metni brife göre değiştir)")
        s["senaryolar"] = [{"stil": stil, "senaryo": f"{stil}.json"}]
    sure = kayit.get("sure") or SURE_VARSAYILAN.get(kayit.get("tur") or "", None)
    brif = [f"# {s['baslik']}", "", f"Panel siparişi `{belge_id}` ({time.strftime('%Y-%m-%d %H:%M')}).", "",
            kayit.get("detay") or "(detay yok)", "",
            f"- Tür: {kayit.get('tur') or '?'} · süre: {sure or 'otomatik'} sn · format: {s['format']}",
            f"- Tarz: {stil or 'Claude seçsin'} · dil: {dil} · ses: {ses or 'varsayılan'} · müzik: {kayit.get('muzik') or '?'}",
            *(f"- {n}" for n in notlar[1:])]
    (klasor / "brif.md").write_text("\n".join(brif) + "\n", encoding="utf-8")
    p = klasor / "siparis.json"
    if p.exists():  # yeniden çalıştırmada thread'in eklediği senaryoları koru
        eski = json.loads(p.read_text(encoding="utf-8"))
        s = {**s, **{k: v for k, v in eski.items() if k in ("senaryolar", "senaryo", "ses", "direkt")}}
    p.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"sipariş: {p}")
    for y in yazilan:
        print(f"senaryo: {y}")
    if not stil:
        print('tarz seçilmemiş: stili sen seç, senaryoyu klasöre yaz ve siparis.json\'a "senaryolar" ekle')
    return p


def durum(d: dict) -> dict:
    """uret.py durum kaydı → panel belgesine yazılacak alanlar."""
    asama = d.get("asama") or ""
    pdurum, not_ = ASAMA.get(asama, ("uretimde", asama))
    alanlar = {"durum": pdurum, "claude_notu": not_, "asama": asama,
               "guncellendi": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if d.get("onizleme"):
        alanlar["onizleme"] = d["onizleme"]
    if d.get("animatik"):
        alanlar["animatik"] = [a["dosya"] for a in d["animatik"] if a.get("dosya")]
    if pdurum == "hazir":
        alanlar["teslim_dosyalari"] = [v["dosya"] for v in d.get("videolar") or [] if v.get("sonuc") != "kaldi"]
    return alanlar


def durum_yaz(s: dict, d: dict) -> Path | None:
    """Sipariş panelden geldiyse klasöre panel-durum.json yazar (uret.py her aşamada çağırır)."""
    if not (s.get("panel") or {}).get("id"):
        return None
    p = Path(s["_klasor"]) / DOSYA
    p.write_text(json.dumps(durum(d), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return p


def hatirlatma(s: dict) -> str:
    pn = s.get("panel") or {}
    return (f"panel: ArtifactData update url={pn.get('url', PANEL_URL)} collection={pn.get('koleksiyon', KOLEKSIYON)} "
            f"doc_id={pn.get('id')} file_path={Path(s['_klasor']) / DOSYA}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    a_s = alt.add_parser("siparis", help="panel kaydını sipariş klasörüne çevirir")
    a_s.add_argument("kayit")
    a_s.add_argument("--id")
    a_s.add_argument("--kok", default="/mnt/project-files")
    a_d = alt.add_parser("durum", help="panele yazılacak alanları gösterir ve panel-durum.json yazar")
    a_d.add_argument("siparis")
    a = ap.parse_args(argv)
    if a.komut == "siparis":
        dis = json.loads(Path(a.kayit).read_text(encoding="utf-8"))
        kayit = dis["data"] if isinstance(dis.get("data"), dict) else dis  # ArtifactData sonucu ya da yalın belge
        try:
            siparis_yaz(kayit, Path(a.kok), a.id or dis.get("doc_id") or dis.get("id"))
        except ValueError as e:
            print(f"HATA: {e}", file=sys.stderr)
            return 2
        return 0
    yol = Path(a.siparis).resolve()
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str((yol.parent / s.get("klasor", ".")).resolve())
    dj = Path(s["_klasor"]) / "siparis-durum.json"
    d = json.loads(dj.read_text(encoding="utf-8")) if dj.exists() else {"asama": "yeni"}
    print(json.dumps(durum(d), ensure_ascii=False, indent=1))
    if durum_yaz(s, d):
        print(hatirlatma(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())

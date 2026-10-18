"""YZ video sağlayıcı bağdaştırıcıları (`saglayicilar.json`).

Her bağdaştırıcı aynı imzayı taşır: `uret(is_, hedef, ayar, ag) -> Path`. `is_`
planın bir satırıdır (prompt, kare, süre, tohum); `hedef` uzantısız çıktı yoludur;
`ag` HTTP katmanıdır ve testlerde sahtesiyle değiştirilir. Bağdaştırıcı dosyayı
yazar ve yazdığı yolu döndürür; başarısızlıkta `SaglayiciHatasi` atar.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
import urllib.request
from pathlib import Path

DOSYA = Path(__file__).resolve().parent / "saglayicilar.json"
FAL_KUYRUK = "https://queue.fal.run/"
BEKLEME_SN = 5
ZAMAN_ASIMI_SN = 15 * 60


class SaglayiciHatasi(RuntimeError):
    pass


def yukle(path: str | Path = DOSYA) -> dict[str, dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["saglayicilar"]


def http(method: str, url: str, body: dict | None = None, headers: dict | None = None) -> bytes:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        **({"Content-Type": "application/json"} if data else {}), **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _kuru(is_: dict, hedef: Path, ayar: dict, ag) -> Path:
    out = hedef.with_suffix(".kuru.json")
    out.write_text(json.dumps(is_, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def _data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def fal_kuyruk(model: str, body: dict, ag, anahtar: str = "FAL_KEY") -> dict:
    """fal.ai kuyruk API'si: isteği bırakır, bitene kadar bekler, sonuç JSON'unu döndürür."""
    key = os.environ.get(anahtar, "")
    if not key:
        raise SaglayiciHatasi(f"{anahtar} ortam değişkeni yok")
    auth = {"Authorization": f"Key {key}"}
    try:
        kuyruk = json.loads(ag("POST", FAL_KUYRUK + model, body, auth))
        bitis = time.monotonic() + ZAMAN_ASIMI_SN
        while True:
            durum = json.loads(ag("GET", kuyruk["status_url"], None, auth)).get("status")
            if durum == "COMPLETED":
                break
            if durum not in ("IN_QUEUE", "IN_PROGRESS"):
                raise SaglayiciHatasi(f"fal.ai durumu {durum!r}")
            if time.monotonic() > bitis:
                raise SaglayiciHatasi("fal.ai zaman aşımı")
            time.sleep(BEKLEME_SN)
        return json.loads(ag("GET", kuyruk["response_url"], None, auth))
    except (OSError, KeyError, ValueError) as e:
        raise SaglayiciHatasi(f"fal.ai: {e}") from e


def _fal(is_: dict, hedef: Path, ayar: dict, ag) -> Path:
    body = {"prompt": is_["prompt"], "duration": f"{is_['faturali_sn']:g}"}
    if is_["negatif"]:
        body["negative_prompt"] = is_["negatif"]
    if is_["kare"]:
        body["image_url"] = _data_uri(Path(is_["kare"]))
    if ayar.get("tohum"):
        body["seed"] = is_["tohum"]
    sonuc = fal_kuyruk(ayar["model"], body, ag, ayar.get("anahtar", "FAL_KEY"))
    try:
        url = sonuc["video"]["url"]
        out = hedef.with_suffix(".mp4")
        out.write_bytes(ag("GET", url, None, None))
    except (OSError, KeyError, ValueError) as e:
        raise SaglayiciHatasi(f"fal.ai: {e}") from e
    return out


BAGDASTIRICILAR = {"kuru": _kuru, "fal": _fal}


def uret(is_: dict, hedef: Path, ayar: dict, ag=http) -> Path:
    fn = BAGDASTIRICILAR.get(ayar["tur"])
    if fn is None:
        raise SaglayiciHatasi(f"'{ayar['tur']}' türü için bağdaştırıcı yok")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    return fn(is_, hedef, ayar, ag)

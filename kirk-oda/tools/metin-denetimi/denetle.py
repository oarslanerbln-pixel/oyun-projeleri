#!/usr/bin/env python3
"""Kırk Oda — oyuncu metni denetimi (karar K-19).

Oyuncunun gördüğü her metin yasak sözcük listesine karşı denetlenir. HATA bulunursa
çıkış kodu 1 olur ve CI düşer; UYARI yalnız yazdırılır.

Kullanım:
  denetle.py                       # varsayılan: localization/oyuncu-metni.csv
  denetle.py dosya.csv dosya.md    # CSV (anahtar,tr,en,...,izin) ya da düz metin/Markdown
  denetle.py --self-test           # denetleyicinin kendi testleri

CSV'de "izin" sütunu, o satırda bilerek izin verilen desen kimliklerini (virgülle) taşır.
Her izin karar kaydında gerekçelendirilir.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LEXICON = os.path.join(HERE, "yasak-sozcukler.tsv")
DEFAULT = os.path.join(ROOT, "localization", "oyuncu-metni.csv")
LETTERS = "A-Za-z0-9ÇĞİÖŞÜçğıöşüÂâÎîÛû"


def tr_lower(text):
    return text.replace("I", "ı").replace("İ", "i").lower()


def load_lexicon(path=LEXICON):
    rules = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            ident, level, lang, pattern, reason = line.split("\t")
            rx = re.compile(r"(?<![%s])(?:%s)(?![%s])" % (LETTERS, pattern, LETTERS))
            rules.append((ident, level, lang, rx, reason))
    return rules


def check_text(text, lang, rules, allowed=()):
    found = []
    low = tr_lower(text)
    for ident, level, rlang, rx, reason in rules:
        if rlang != lang and lang != "*":
            continue
        if ident in allowed:
            continue
        for m in rx.finditer(low):
            found.append((ident, level, m.group(0), reason))
    return found


def check_csv(path, rules):
    findings = []
    with open(path, encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            allowed = {a.strip() for a in (row.get("izin") or "").split(",") if a.strip()}
            for lang in ("tr", "en"):
                for hit in check_text(row.get(lang) or "", lang, rules, allowed):
                    findings.append((path, i, row.get("anahtar", "?"), lang) + hit)
    return findings


def check_plain(path, rules):
    findings = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            for hit in check_text(line, "*", rules):
                findings.append((path, i, "-", "*") + hit)
    return findings


def run(paths):
    rules = load_lexicon()
    findings = []
    for p in paths:
        findings += check_csv(p, rules) if p.endswith(".csv") else check_plain(p, rules)
    errors = [f for f in findings if f[5] == "HATA"]
    for path, line, key, lang, ident, level, word, reason in findings:
        rel = os.path.relpath(path, ROOT)
        print(f"{level}: {rel}:{line} [{key}/{lang}] '{word}' ({ident}) — {reason}")
    print(f"Denetlenen dosya: {len(paths)} · HATA: {len(errors)} · UYARI: {len(findings) - len(errors)}")
    return 1 if errors else 0


def self_test():
    rules = load_lexicon()
    def hits(text, lang="tr"):
        return {h[0] for h in check_text(text, lang, rules)}
    cases = [
        ("Kırk Dem", "tr", {"TR-DEM"}),
        ("KIRK DEMLERİ", "tr", {"TR-DEM"}),          # Türkçe büyük harf: İ → i
        ("Ne demek istedin, demir kapı", "tr", set()),  # demek, demir yakalanmaz
        ("Kırklar Cemi", "tr", {"TR-KIRKLAR", "TR-CEM"}),
        ("cemaat değil kalabalık", "tr", {"TR-KURUM"}),
        ("Kırk oda, kırk makam", "tr", {"TR-KIRKMAKAM", "TR-KAVRAM2"}),
        ("Defterindeki günler yanlış değil", "tr", set()),
        ("Ali", "tr", {"TR-AD"}),
        ("kalıyor", "tr", set()),                     # "ali" sözcük içinde yakalanmaz
        ("Forty Rooms", "en", set()),
        ("the forty saints", "en", {"EN-SUFI"}),
        ("A dervish walked", "en", {"EN-SUFI"}),
        ("demonstration", "en", set()),
    ]
    failed = 0
    for text, lang, expected in cases:
        got = hits(text, lang)
        if got != expected:
            failed += 1
            print(f"BAŞARISIZ: {text!r} ({lang}) beklenen {sorted(expected)}, bulunan {sorted(got)}")
    print(f"Öz test: {len(cases) - failed}/{len(cases)} geçti")
    return 1 if failed else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--self-test"]:
        sys.exit(self_test())
    sys.exit(run(args or [DEFAULT]))

"""QA gate: ricontrolla che ogni citazione letterale compaia davvero nella pagina fonte.

Per ogni statement con `quote` rifà lo scrape di `source_url` (Serper) e cerca la citazione
(normalizzata: minuscole, spazi, virgolette/apostrofi tipografici, accenti invariati).
Match esatto -> OK. Altrimenti cerca il frammento più lungo (>= 60% delle parole consecutive) -> PARZIALE.
Niente -> NON TROVATA. Pagina bloccata -> BLOCCATA (resta da verificare a mano / snippet).

Uso:  py scripts/verify_quotes.py                 -> tutti i partiti
      py scripts/verify_quotes.py --party pp      -> un partito
      py scripts/verify_quotes.py --only-new 2026-10-08   -> solo righe con added_at >= data
Scrive: output/verify_quotes.json (cache: le URL già scrapate non si riscaricano)
Costo: 1 credito Serper per URL unica.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from serper import post, SCRAPE_URL  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "output" / "verify_cache.json"


def norm(s):
    s = unicodedata.normalize("NFC", s or "").lower()
    s = s.replace("“", '"').replace("”", '"').replace("«", '"').replace("»", '"')
    s = s.replace("‘", "'").replace("’", "'").replace("…", "...").replace(" ", " ")
    s = re.sub(r"[\"']", "", s)
    s = re.sub(r"-\s*\n\s*", "", s)              # sillabazione PDF: "ELIMI-\nNAREMOS"
    s = re.sub(r"[^\x00-\x7f]", " ", s)          # lo scrape Serper a volte sostituisce gli accenti con uno spazio
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:")


def best_fragment(quote, text):
    words = quote.split(" ")
    n = len(words)
    for size in range(n, max(3, int(n * 0.6)) - 1, -1):
        for i in range(0, n - size + 1):
            if " ".join(words[i:i + size]) in text:
                return size / n
    return 0.0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--party")
    ap.add_argument("--only-new")
    a = ap.parse_args()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    results = []
    for f in sorted((ROOT / "data" / "statements").glob("*.json")):
        if a.party and f.stem != a.party:
            continue
        for s in json.loads(f.read_text(encoding="utf-8")).get("statements", []):
            if not s.get("quote"):
                continue
            if a.only_new and (s.get("added_at") or "") < a.only_new:
                continue
            url = s["source_url"]
            if url not in cache:
                try:
                    d = post(SCRAPE_URL, {"url": url})
                    t = d.get("text") or ""
                    cache[url] = None if ("Client Challenge" in t[:200] or not t.strip()) else t
                except SystemExit:
                    cache[url] = None
                CACHE.parent.mkdir(parents=True, exist_ok=True)
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            text = cache[url]
            if text is None:
                status, score = "BLOCCATA", None
            else:
                q, t = norm(s["quote"]), norm(text)
                if q in t:
                    status, score = "OK", 1.0
                else:
                    score = best_fragment(q, t)
                    status = "PARZIALE" if score >= 0.6 else "NON TROVATA"
            results.append({"party": f.stem, "id": s["id"], "status": status, "score": score,
                             "declared": s.get("verified"), "url": url, "quote": s["quote"][:120]})
    out = ROOT / "output" / "verify_quotes.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    c = Counter(r["status"] for r in results)
    print(f"Citazioni controllate: {len(results)} -> " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
    for r in results:
        if r["status"] != "OK":
            extra = f" ({r['score']:.0%} parole)" if r["score"] else ""
            print(f"  {r['status']}{extra} [{r['party']}] {r['id']} (dichiarato: {r['declared']})\n      «{r['quote']}»\n      {r['url']}")


if __name__ == "__main__":
    main()

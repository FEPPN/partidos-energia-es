"""Serper helper for research agents (direct API, key fallback).

Usage:
  py serper.py search "query" [--gl es] [--hl es] [--num 10] [--tbs qdr:y]
  py serper.py scrape "https://url"
Prints JSON to stdout (search: organic + peopleAlsoAsk + relatedSearches; scrape: text truncated to 15000 chars).
"""
import json
import sys
import urllib.request
from pathlib import Path

KEY_FILE = Path(__file__).resolve().parents[2] / "ZZ_file ENV" / "Keys" / "scraper"
SEARCH_URL = "https://google.serper.dev/search"
SCRAPE_URL = "https://scrape.serper.dev"


def keys():
    return [l.strip() for l in KEY_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]


def post(url, payload):
    last = None
    for k in keys():
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers={"X-API-KEY": k, "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
    raise SystemExit(f"All Serper keys failed: {last}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    mode, arg = sys.argv[1], sys.argv[2]
    opts = dict(zip(sys.argv[3::2], sys.argv[4::2]))
    if mode == "search":
        payload = {"q": arg, "gl": opts.get("--gl", "es"), "hl": opts.get("--hl", "es"), "num": int(opts.get("--num", 10))}
        if "--tbs" in opts:
            payload["tbs"] = opts["--tbs"]
        d = post(SEARCH_URL, payload)
        out = {
            "organic": [{k: o.get(k) for k in ("title", "link", "date", "snippet")} for o in d.get("organic", [])],
            "peopleAlsoAsk": [p.get("question") for p in d.get("peopleAlsoAsk", [])],
            "relatedSearches": [r.get("query") for r in d.get("relatedSearches", [])],
        }
    else:
        d = post(SCRAPE_URL, {"url": arg})
        text = d.get("text", "") or ""
        out = {"url": arg, "blocked": "Client Challenge" in text[:200] or not text.strip(), "text": text[:15000]}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

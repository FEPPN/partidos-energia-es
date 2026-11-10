"""Unisce i 'new_statements' trovati dalle ricerche per domanda (data/answers/*.json) nei file dei partiti
(data/statements/<slug>.json), così compaiono nella timeline e passano dalla verifica citazioni.
Idempotente: gli id già presenti vengono saltati. Uso: py scripts/merge_answers.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parties = {p["key"]: p["slug"] for p in json.loads((DATA / "parties.json").read_text(encoding="utf-8"))["parties"]}
    slug_to_key = {v: k for k, v in parties.items()}
    added = {}
    for f in sorted((DATA / "answers").glob("*.json")):
        for s in json.loads(f.read_text(encoding="utf-8")).get("new_statements", []):
            slug = s["id"].split("-")[0]
            if slug not in slug_to_key:
                print(f"⚠️  id senza partito riconoscibile: {s['id']}")
                continue
            pf = DATA / "statements" / f"{slug}.json"
            doc = json.loads(pf.read_text(encoding="utf-8"))
            if any(x["id"] == s["id"] for x in doc["statements"]):
                continue
            s.setdefault("added_at", "2026-10-08")
            doc["statements"].append(s)
            pf.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            added[slug] = added.get(slug, 0) + 1
    print("Aggiunte:", added or "nessuna (già unite)")


if __name__ == "__main__":
    main()

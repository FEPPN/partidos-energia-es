"""Riassunto compatto dei modelli Excel di Oscar (Termómetro) senza caricare tutte le celle nel contesto.

Per ogni file .xlsx in data/oscar_models/:
- schede, dimensioni, righe di intestazione
- celle di INPUT (valori costanti con etichetta a sinistra/sopra)
- formule raggruppate per "schema" (riferimenti di riga normalizzati: =B5*C5 e =B6*C6 contano come una)
- nomi definiti
Scrive data/oscar_models/_summary.md e stampa una versione breve.

Uso: py scripts/inspect_models.py [--sheet NOME] [--max 25]
"""
import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "oscar_models"


def pattern(f):
    return re.sub(r"(\$?[A-Z]{1,3})\$?\d+", r"\1#", f)


def label_for(ws, cell):
    """Etichetta testuale più vicina a sinistra (stessa riga) o sopra (stessa colonna)."""
    r, c = cell.row, cell.column
    for cc in range(c - 1, max(0, c - 4), -1):
        v = ws.cell(r, cc).value
        if isinstance(v, str) and v.strip():
            return v.strip()[:60]
    for rr in range(r - 1, max(0, r - 4), -1):
        v = ws.cell(rr, c).value
        if isinstance(v, str) and v.strip():
            return v.strip()[:60]
    return ""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet")
    ap.add_argument("--max", type=int, default=25)
    a = ap.parse_args()
    out = []
    files = sorted(DIR.glob("*.xlsx"))
    if not files:
        print(f"Nessun .xlsx in {DIR}")
        return
    for f in files:
        wb_f = openpyxl.load_workbook(f, data_only=False)
        wb_v = openpyxl.load_workbook(f, data_only=True)
        out.append(f"# {f.name}")
        if wb_f.defined_names:
            out.append("Nomi definiti: " + ", ".join(f"{n}={wb_f.defined_names[n].attr_text}" for n in list(wb_f.defined_names)[:30]))
        for ws in wb_f.worksheets:
            if a.sheet and ws.title != a.sheet:
                continue
            wv = wb_v[ws.title]
            out.append(f"\n## [{ws.title}] {ws.max_row}×{ws.max_column}")
            # intestazioni: prime 3 righe non vuote
            shown = 0
            for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 12)):
                vals = [str(c.value)[:28] for c in row if c.value not in (None, "")]
                if vals:
                    out.append(f"  r{row[0].row}: " + " | ".join(vals[:12]))
                    shown += 1
                if shown >= 4:
                    break
            pats, examples, inputs = Counter(), {}, []
            for row in ws.iter_rows():
                for c in row:
                    v = c.value
                    if isinstance(v, str) and v.startswith("="):
                        p = pattern(v)
                        pats[p] += 1
                        if p not in examples:
                            examples[p] = (c.coordinate, v[:160], wv[c.coordinate].value, label_for(ws, c))
                    elif isinstance(v, (int, float)) and not isinstance(v, bool):
                        lab = label_for(ws, c)
                        if lab:
                            inputs.append((c.coordinate, lab, v))
            if inputs:
                out.append(f"  INPUT costanti ({len(inputs)}), prime {min(len(inputs), a.max)}:")
                for coord, lab, v in inputs[:a.max]:
                    out.append(f"    {coord:<6} {lab} = {v}")
            if pats:
                out.append(f"  FORMULE: {sum(pats.values())} celle, {len(pats)} schemi. Principali:")
                for p, n in pats.most_common(a.max):
                    coord, ex, val, lab = examples[p]
                    out.append(f"    x{n:<4} {coord:<6} [{lab}] {ex}  -> {val}")
    text = "\n".join(out)
    (DIR / "_summary.md").write_text(text, encoding="utf-8")
    print(text[:20000])


if __name__ == "__main__":
    main()

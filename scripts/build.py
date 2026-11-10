"""Genera gli HTML WordPress-ready del tool partiti × energia (papernest.es).

Legge:   data/config.json, data/parties.json, data/topics.json, data/source_tiers.json, data/statements/*.json
Scrive:  output/hub/codice_intro.html + codice_testo.html
         output/<slug>/codice_intro.html + codice_testo.html   (una cartella per partito)
         output/preview/*.html                                 (anteprima browser, NON da incollare in WP)
         output/badges.json                                    (stato badge, serve per il diff al giro dopo)

Uso:     py scripts/build.py                 -> valida, calcola badge, genera, stampa report diff
         py scripts/build.py --check         -> solo validazione + report, non scrive nulla
         py scripts/build.py --statements-dir <dir>   -> usa un'altra cartella dati (test)
"""
import argparse
import html
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "output"

MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]
MONTHS_SHORT = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]

BADGE = {
    "a_favor": ("A favor", "favor"),
    "en_contra": ("En contra", "contra"),
    "ambiguo": ("Ambiguo", "ambiguo"),
    "sin_declaraciones": ("Sin declaraciones", "sin"),
    "sin_badge": ("Solo declaraciones", "nobadge"),
}
TYPE_LABEL = {"declaracion": "Declaración", "voto": "Votación", "programa": "Programa electoral",
              "reportada": "Declaración reportada"}  # reportada = parafrasi del giornalista, mai tra virgolette

ICON_REPEAT = ('<svg class="ppe-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="m17 2 4 4-4 4"/>'
               '<path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/></svg>')
ICON_EXT = ('<svg class="ppe-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 3h6v6"/><path d="M10 14 21 3"/>'
            '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>')
ICON_SPLIT = ('<svg class="ppe-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M16 3h5v5"/><path d="M8 3H3v5"/>'
              '<path d="M12 22v-8.3a4 4 0 0 0-1.172-2.872L3 3"/><path d="m15 9 6-6"/></svg>')

e = html.escape


# ----------------------------------------------------------------- load + validate

def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def domain(url):
    d = urlparse(url).netloc.lower()
    return d[4:] if d.startswith("www.") else d


def in_list(d, domains):
    return any(d == x or d.endswith("." + x) for x in domains)


def validate(statements_by_party, parties, topics, tiers):
    errors, warnings = [], []
    topic_keys = {t["key"]: t for t in topics}
    seen_ids = set()
    for pkey, doc in statements_by_party.items():
        for s in doc.get("statements", []):
            sid = s.get("id", "?")
            where = f"[{pkey}] {sid}"
            for f in ("id", "topic", "type", "date", "person", "role", "level", "stance", "source_name", "source_url", "tier"):
                if s.get(f) in (None, ""):
                    errors.append(f"{where}: campo mancante '{f}'")
            if sid in seen_ids:
                errors.append(f"{where}: id duplicato")
            seen_ids.add(sid)
            t = topic_keys.get(s.get("topic"))
            if not t:
                errors.append(f"{where}: topic sconosciuto '{s.get('topic')}'")
                continue
            if s.get("type") not in TYPE_LABEL:
                errors.append(f"{where}: type non valido '{s.get('type')}'")
            if s.get("type") == "declaracion" and not (s.get("quote") or "").strip():
                errors.append(f"{where}: declaracion senza quote")
            if s.get("type") == "reportada" and s.get("quote"):
                errors.append(f"{where}: 'reportada' non può avere quote (è una parafrasi)")
            if s.get("type") in ("voto", "programa", "reportada") and not (s.get("quote") or s.get("context")):
                errors.append(f"{where}: {s.get('type')} senza quote né context")
            try:
                datetime.strptime(s.get("date", ""), "%Y-%m-%d")
            except ValueError:
                errors.append(f"{where}: data non valida '{s.get('date')}'")
            if s.get("tier") not in (1, 2):
                errors.append(f"{where}: tier deve essere 1 o 2")
            d = domain(s.get("source_url", ""))
            if in_list(d, tiers["tier3"]["domains"]):
                errors.append(f"{where}: fonte tier3 ({d})")
            elif not (in_list(d, tiers["tier1"]["domains"]) or in_list(d, tiers["tier2"]["domains"])):
                warnings.append(f"{where}: dominio non in source_tiers.json ({d}) -> verificare e aggiungere")
            if s.get("level") not in ("nacional", "regional"):
                errors.append(f"{where}: level non valido")
            if t["proposition"] is None and s.get("stance") != "na":
                warnings.append(f"{where}: tema senza proposition, stance forzata a 'na'")
                s["stance"] = "na"
            if t["proposition"] is not None and s.get("stance") not in ("a_favor", "en_contra", "ambiguo"):
                errors.append(f"{where}: stance non valida '{s.get('stance')}'")
            if s.get("verified") == "snippet":
                warnings.append(f"{where}: citazione solo da snippet (pagina non letta)")
    return errors, warnings


# ----------------------------------------------------------------- badge logic

def d(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def compute_badge(items, topic, party_key, cfg):
    """items = statements of one party on one topic. Returns dict with badge + change info."""
    if topic["proposition"] is None:
        return {"badge": "sin_badge", "change": None, "historic_change": None, "evolution": None, "dice_vota": False}
    min_date = d(cfg.get("party_min_date", {}).get(party_key, cfg["legislature_start"]))
    valid = sorted([s for s in items if s["level"] == "nacional" and s["tier"] in (1, 2)
                    and s["stance"] in ("a_favor", "en_contra", "ambiguo") and d(s["date"]) >= min_date],
                   key=lambda s: s["date"])
    if not valid:
        return {"badge": "sin_declaraciones", "change": None, "historic_change": None, "evolution": None, "dice_vota": False}
    latest = d(valid[-1]["date"])
    window_start = latest - timedelta(days=cfg["current_window_days"])
    current = [s for s in valid if d(s["date"]) >= window_start]
    older = [s for s in valid if d(s["date"]) < window_start]
    stances = {s["stance"] for s in current}
    dice_vota = False
    if "a_favor" in stances and "en_contra" in stances:
        badge = "ambiguo"
        types_fav = {s["type"] for s in current if s["stance"] == "a_favor"}
        types_con = {s["type"] for s in current if s["stance"] == "en_contra"}
        dice_vota = ("voto" in types_fav and "declaracion" in types_con) or ("voto" in types_con and "declaracion" in types_fav)
    elif "a_favor" in stances:
        badge = "a_favor"
    elif "en_contra" in stances:
        badge = "en_contra"
    else:
        badge = "ambiguo"
    opposite = {"a_favor": "en_contra", "en_contra": "a_favor"}.get(badge)
    change = None
    if opposite:
        before = [s for s in older if s["stance"] == opposite]
        after = [s for s in current if s["stance"] == badge]
        if before and after:
            change = {"before": before[-1], "after": after[-1]}
    historic_change = None
    if opposite and not change:
        hist = sorted([s for s in items if d(s["date"]) < min_date and s["stance"] == opposite], key=lambda s: s["date"])
        after = [s for s in current if s["stance"] == badge]
        if hist and after:
            historic_change = {"before": hist[-1], "after": after[-1]}
    evolution = None
    if not change and not historic_change:
        # cambio non netto (es. ambiguo -> a favor, a favor -> ambiguo): popup informativo, il badge non cambia
        earlier = sorted([s for s in items if s["level"] == "nacional" and s["stance"] in ("a_favor", "en_contra", "ambiguo")
                          and d(s["date"]) < window_start and s["stance"] != badge
                          and not (s["type"] == "voto" and s["stance"] == "ambiguo")],  # voti ambigui = decreti omnibus, non un'evoluzione
                         key=lambda s: s["date"])
        after = [s for s in current if s["stance"] == badge] or current
        if earlier and after:
            evolution = {"before": earlier[-1], "after": after[-1]}
    return {"badge": badge, "change": change, "historic_change": historic_change, "evolution": evolution, "dice_vota": dice_vota}


# ----------------------------------------------------------------- html helpers

def fdate(s, short=False):
    x = s if isinstance(s, date) else d(s)
    return f"{x.day} {MONTHS_SHORT[x.month - 1]} {x.year}" if short else f"{x.day} de {MONTHS[x.month - 1]} de {x.year}"


def party_url(cfg, p, topic_key=None):
    u = f"{cfg['base_path']}{p['slug']}/"
    return u + (f"#{topic_key}" if topic_key else "")


COMPACT = {"sin_declaraciones": "Sin datos", "sin_badge": "Ver citas"}


def badge_html(b, extra="", compact=False):
    label, mod = BADGE[b["badge"]]
    if compact:
        label = COMPACT.get(b["badge"], label)
    marks = ""
    if b.get("change"):
        marks += f'<span class="ppe-mark" title="Cambió de posición">{ICON_REPEAT}</span>'
    if b.get("dice_vota"):
        marks += f'<span class="ppe-mark" title="Lo que dice no coincide con lo que vota">{ICON_SPLIT}</span>'
    return f'<span class="ppe-badge ppe-badge--{mod}"{extra}>{e(label)}{marks}</span>'


def source_link(s):
    return (f'<a class="ppe-src" href="{e(s["source_url"])}" target="_blank" rel="noopener">'
            f'{e(s["source_name"])}{ICON_EXT}</a>')


def change_popover(b, party, detail_url=None):
    out = []
    ch = b.get("change") or b.get("historic_change") or b.get("evolution")
    if ch:
        title = ("Cambió de posición" if b.get("change") else
                 "Antes de esta legislatura decía otra cosa" if b.get("historic_change") else
                 "Su posición ha evolucionado")
        bef, aft = ch["before"], ch["after"]
        out.append(
            f'<details class="ppe-pop"><summary>{ICON_REPEAT}<span>{e(title)}</span></summary>'
            f'<div class="ppe-pop__body">'
            f'<p class="ppe-pop__step"><span class="ppe-pop__when">{e(fdate(bef["date"], True))} · {e(BADGE[bef["stance"]][0])}</span>'
            f'{quote_or_context(bef)}<span class="ppe-pop__who">{e(bef["person"])} · {source_link(bef)}</span></p>'
            f'<p class="ppe-pop__step"><span class="ppe-pop__when">{e(fdate(aft["date"], True))} · {e(BADGE[aft["stance"]][0])}</span>'
            f'{quote_or_context(aft)}<span class="ppe-pop__who">{e(aft["person"])} · {source_link(aft)}</span></p>'
            f'</div></details>')
    if b.get("dice_vota"):
        out.append('<p class="ppe-note">' + ICON_SPLIT + '<span>En los últimos meses, lo que '
                   f'{e(party["label_article"])} declara y lo que vota en el Congreso no coinciden. '
                   + (f'<a class="ppe-src" href="{e(detail_url)}">Ver el detalle</a>' if detail_url else 'Lo ves en la cronología de abajo.')
                   + '</span></p>')
    return "".join(out)


def quote_or_context(s):
    if s.get("quote"):
        return f'<q class="ppe-q">{e(s["quote"])}</q>'
    return f'<span class="ppe-ctx">{e(s.get("context") or "")}</span>'


def statement_li(s, min_date):
    tags = [TYPE_LABEL[s["type"]]]
    if s["level"] == "regional":
        tags.append("Voz regional")
    if d(s["date"]) < min_date:
        tags.append("Histórico")
    stance = BADGE[s["stance"]][0] if s["stance"] in BADGE else ""
    tag_html = "".join(f'<span class="ppe-tag">{e(t)}</span>' for t in tags)
    stance_html = f'<span class="ppe-tag ppe-tag--{BADGE[s["stance"]][1]}">{e(stance)}</span>' if s["stance"] in BADGE else ""
    body = f'<blockquote class="ppe-quote">«{e(s["quote"])}»</blockquote>' if s.get("quote") else ""
    ctx = f'<p class="ppe-context">{e(s["context"])}</p>' if s.get("context") else ""
    return (f'<li class="ppe-item ppe-item--{BADGE.get(s["stance"], ("", "na"))[1]}" id="{e(s["id"])}">'
            f'<div class="ppe-item__date"><time datetime="{e(s["date"])}">{e(fdate(s["date"], True))}</time></div>'
            f'<div class="ppe-item__main"><div class="ppe-item__tags">{tag_html}{stance_html}</div>'
            f'{body}{ctx}'
            f'<p class="ppe-item__who"><strong>{e(s["person"])}</strong> · {e(s["role"])} · {source_link(s)}</p>'
            f'</div></li>')


CSS = """
.ppe-root{--ppe-p:#5a52ff;--ppe-p50:#f6f5ff;--ppe-p100:#f1f0ff;--ppe-p200:#ceccff;--ppe-p700:#3e38b2;--ppe-t50:#f2fcfb;--ppe-t100:#e0f8f6;--ppe-t500:#02c5ae;--ppe-t800:#016559;--ppe-navy:#212430;--ppe-txt2:#383c4c;--ppe-muted:#63697f;--ppe-subtle:#81859a;--ppe-s50:#fafaf9;--ppe-s100:#f5f5f4;--ppe-s200:#e7e5e4;--ppe-s300:#d6d3d1;--ppe-s500:#79716b;color:var(--ppe-navy);font-family:inherit;line-height:1.5;max-width:100%;box-sizing:border-box}
.ppe-root *,.ppe-root *::before,.ppe-root *::after{box-sizing:border-box}
.ppe-root h2{font-size:24px;line-height:32px;font-weight:800;margin:0 0 8px;color:var(--ppe-navy)}
.ppe-root h3{font-size:18px;line-height:24.6px;font-weight:800;margin:0;color:var(--ppe-navy)}
.ppe-updated{font-size:14px;color:var(--ppe-muted);margin:0 0 24px}
.ppe-ico{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;flex:none;vertical-align:-3px}
.ppe-filters{display:flex;flex-direction:column;gap:12px;margin:0 0 24px;padding:16px;background:var(--ppe-p50);border-radius:8px}
.ppe-filter{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.ppe-filter__label{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:var(--ppe-muted);margin-right:4px}
.ppe-chip{font:inherit;font-size:14px;font-weight:500;padding:6px 14px;border-radius:9999px;border:1px solid var(--ppe-p200);background:#fff;color:var(--ppe-navy);cursor:pointer;line-height:20px}
.ppe-chip:hover{border-color:var(--ppe-p)}
.ppe-chip[aria-pressed="true"]{background:var(--ppe-p);border-color:var(--ppe-p);color:#fff}
.ppe-tablewrap{overflow-x:auto;border-radius:8px;border:1px solid var(--ppe-s200);margin:0 0 16px;-webkit-overflow-scrolling:touch}
.ppe-table{border-collapse:collapse;width:100%;min-width:680px;font-size:14px}
.ppe-table th,.ppe-table td{padding:8px 6px;text-align:center;border-bottom:1px solid var(--ppe-s200);vertical-align:middle}
.ppe-table thead th{background:var(--ppe-navy);color:#fff;font-weight:800}
.ppe-table thead th a{color:#fff;text-decoration:none}
.ppe-table thead th a:hover{text-decoration:underline}
.ppe-table tbody tr:nth-child(even){background:var(--ppe-p50)}
.ppe-table th[scope=row]{text-align:left;font-weight:500;position:sticky;left:0;background:inherit;min-width:150px;padding-left:12px}
.ppe-table tbody tr th[scope=row]{background:#fff}
.ppe-table tbody tr:nth-child(even) th[scope=row]{background:var(--ppe-p50)}
.ppe-table th[scope=row] a{color:var(--ppe-navy);text-decoration:none}
.ppe-table th[scope=row] a:hover{color:var(--ppe-p)}
.ppe-table td a{text-decoration:none}
.ppe-group-row th{background:var(--ppe-p100)!important;text-align:left;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:var(--ppe-p700)}
.ppe-badge{display:inline-flex;align-items:center;gap:4px;font-size:13px;font-weight:800;line-height:18px;padding:4px 10px;border-radius:6px;white-space:nowrap}
.ppe-badge--favor{background:var(--ppe-t100);color:var(--ppe-t800)}
.ppe-badge--contra{background:var(--ppe-p100);color:var(--ppe-p700)}
.ppe-badge--ambiguo{background:var(--ppe-s100);color:var(--ppe-txt2);background-image:repeating-linear-gradient(135deg,transparent 0 6px,rgba(121,113,107,.12) 6px 8px)}
.ppe-badge--sin{background:#fff;color:var(--ppe-subtle);border:1px dashed var(--ppe-s300);font-weight:500}
.ppe-badge--nobadge{background:#fff;color:var(--ppe-muted);border:1px solid var(--ppe-s200);font-weight:500}
.ppe-mark{display:inline-flex}
.ppe-legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:13px;color:var(--ppe-muted);margin:0 0 48px;align-items:center}
.ppe-legend span{display:inline-flex;align-items:center;gap:6px}
.ppe-topic{margin:0 0 64px;scroll-margin-top:96px}
.ppe-prop{margin:0 0 20px;padding:12px 16px;border-left:4px solid var(--ppe-p);background:var(--ppe-p50);border-radius:0 8px 8px 0;font-size:15px;color:var(--ppe-txt2)}
.ppe-prop strong{color:var(--ppe-navy)}
.ppe-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.ppe-card{background:#fff;border:1px solid var(--ppe-s200);border-radius:8px;border-top-left-radius:18px;border-bottom-right-radius:18px;padding:16px;display:flex;flex-direction:column;gap:10px;box-shadow:0 1px 3px rgba(0,0,0,.10),0 1px 2px rgba(0,0,0,.06)}
.ppe-card__head{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.ppe-card__quote{margin:0;font-size:15px;line-height:22px;color:var(--ppe-navy)}
.ppe-card__meta{margin:0;font-size:13px;color:var(--ppe-muted)}
.ppe-card__more{margin-top:auto;font-size:14px;font-weight:800;color:var(--ppe-p);text-decoration:none}
.ppe-card__more:hover{color:var(--ppe-p700);text-decoration:underline}
.ppe-empty{margin:0;font-size:14px;color:var(--ppe-subtle);font-style:italic}
.ppe-src{color:var(--ppe-p);text-decoration:none;font-weight:500;display:inline-flex;align-items:center;gap:3px}
.ppe-src:hover{text-decoration:underline}
.ppe-src .ppe-ico{width:12px;height:12px;vertical-align:0}
.ppe-pop{position:relative;font-size:13px}
.ppe-pop summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-weight:800;color:var(--ppe-navy);padding:4px 10px;border:1px solid var(--ppe-navy);border-radius:9999px;background:#fff}
.ppe-pop summary::-webkit-details-marker{display:none}
.ppe-pop[open] summary{background:var(--ppe-navy);color:#fff}
.ppe-pop__body{margin-top:8px;padding:12px;border-radius:8px;background:#fff;border:1px solid var(--ppe-s200);box-shadow:0 10px 15px rgba(0,0,0,.10),0 4px 6px rgba(0,0,0,.05);display:flex;flex-direction:column;gap:12px}
.ppe-pop__step{margin:0;display:flex;flex-direction:column;gap:4px;padding-left:12px;border-left:3px solid var(--ppe-s300)}
.ppe-pop__step+.ppe-pop__step{border-left-color:var(--ppe-p)}
.ppe-pop__when{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.03em;color:var(--ppe-muted)}
.ppe-pop__who{font-size:12px;color:var(--ppe-muted)}
.ppe-q{font-size:14px;color:var(--ppe-navy)}
.ppe-ctx{font-size:14px;color:var(--ppe-txt2)}
.ppe-note{display:flex;gap:8px;align-items:flex-start;font-size:13px;color:var(--ppe-txt2);margin:0;padding:8px 12px;background:var(--ppe-s50);border-radius:6px}
.ppe-summary{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px;margin:0 0 32px;padding:0;list-style:none}
.ppe-summary a{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 12px;border:1px solid var(--ppe-s200);border-radius:8px;text-decoration:none;color:var(--ppe-navy);font-size:14px;font-weight:500;background:#fff}
.ppe-summary a:hover{border-color:var(--ppe-p)}
.ppe-ptopic{margin:0 0 56px;scroll-margin-top:96px}
.ppe-ptopic__head{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin:0 0 12px}
.ppe-ptopic__head h2{margin:0}
.ppe-timeline{list-style:none;margin:16px 0 0;padding:0;display:flex;flex-direction:column;gap:12px}
.ppe-item{display:grid;grid-template-columns:88px 1fr;gap:12px;padding:12px 16px 12px 12px;background:#fff;border:1px solid var(--ppe-s200);border-left:4px solid var(--ppe-s300);border-radius:8px}
.ppe-item--favor{border-left-color:var(--ppe-t500)}
.ppe-item--contra{border-left-color:var(--ppe-p)}
.ppe-item__date{font-size:13px;font-weight:800;color:var(--ppe-muted);padding-top:2px}
.ppe-item__main{display:flex;flex-direction:column;gap:6px;min-width:0}
.ppe-item__tags{display:flex;flex-wrap:wrap;gap:6px}
.ppe-tag{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.03em;padding:2px 8px;border-radius:6px;background:var(--ppe-s100);color:var(--ppe-txt2)}
.ppe-tag--favor{background:var(--ppe-t100);color:var(--ppe-t800)}
.ppe-tag--contra{background:var(--ppe-p100);color:var(--ppe-p700)}
.ppe-quote{margin:0;padding:0;border:0;font-size:16px;line-height:24px;font-weight:800;color:var(--ppe-navy);overflow-wrap:anywhere}
.ppe-context{margin:0;font-size:14px;color:var(--ppe-txt2)}
.ppe-item__who{margin:0;font-size:13px;color:var(--ppe-muted)}
.ppe-item__who strong{color:var(--ppe-navy)}
.ppe-others{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 48px}
.ppe-others a{font-size:14px;font-weight:500;padding:6px 14px;border-radius:9999px;border:1px solid var(--ppe-p200);text-decoration:none;color:var(--ppe-navy)}
.ppe-others a:hover{border-color:var(--ppe-p);color:var(--ppe-p)}
.ppe-method{border:1px solid var(--ppe-s200);border-radius:8px;padding:0 16px;margin:0 0 16px;background:var(--ppe-s50)}
.ppe-method summary{cursor:pointer;font-weight:800;padding:14px 0}
.ppe-method[open] summary{border-bottom:1px solid var(--ppe-s200);margin-bottom:12px}
.ppe-method p,.ppe-method li{font-size:14px;color:var(--ppe-txt2)}
.ppe-hidden{display:none!important}
@media (max-width:640px){.ppe-item{grid-template-columns:1fr;gap:4px}.ppe-root h2{font-size:20px;line-height:28px}.ppe-filters{padding:12px}.ppe-filter{flex-wrap:nowrap;overflow-x:auto;padding-bottom:4px;-webkit-overflow-scrolling:touch}.ppe-chip{flex:none}.ppe-filter__label{flex:none}}
"""

JS = """
<script>
setTimeout(function(){try{
  var root=document.getElementById('%(root_id)s'); if(!root) return;
  var state={party:'all',topic:'all'};
  function apply(){
    root.querySelectorAll('[data-ppe-party]').forEach(function(el){
      var ok=state.party==='all'||el.getAttribute('data-ppe-party')===state.party;
      el.classList.toggle('ppe-hidden',!ok);
    });
    root.querySelectorAll('[data-ppe-topic]').forEach(function(el){
      var ok=state.topic==='all'||el.getAttribute('data-ppe-topic')===state.topic;
      el.classList.toggle('ppe-hidden',!ok);
    });
  }
  root.querySelectorAll('.ppe-chip').forEach(function(btn){
    btn.addEventListener('click',function(){
      var kind=btn.getAttribute('data-filter'), val=btn.getAttribute('data-value');
      state[kind]=val;
      root.querySelectorAll('.ppe-chip[data-filter="'+kind+'"]').forEach(function(b){b.setAttribute('aria-pressed',b===btn?'true':'false');});
      apply();
    });
  });
}catch(err){if(window.console){console.warn('ppe filters',err);}}},300);
</script>
"""


def legend_html():
    return ('<div class="ppe-legend">'
            f'<span>{badge_html({"badge": "a_favor"})}</span>'
            f'<span>{badge_html({"badge": "en_contra"})}</span>'
            f'<span>{badge_html({"badge": "ambiguo"})} declaraciones o votos contradictorios en el mismo periodo</span>'
            f'<span>{badge_html({"badge": "sin_declaraciones"}, compact=True)} sin declaraciones desde agosto de 2023</span>'
            f'<span>{badge_html({"badge": "sin_badge"}, compact=True)} tema sin proposición de sí o no</span>'
            f'<span>{ICON_REPEAT} cambió de posición</span>'
            f'<span>{ICON_SPLIT} dice una cosa y vota otra</span>'
            '<span>Los colores no indican si una posición es buena o mala.</span>'
            '</div>')


def methodology_html(cfg):
    return f"""<details class="ppe-method"><summary>Cómo funciona {e(cfg['tool_name'])} (metodología)</summary>
<p>{e(cfg['tool_name'])} no evalúa los programas ni recomienda el voto: recopila lo que han dicho y votado los partidos sobre energía, con la fecha y la fuente de cada declaración.</p>
<ul>
<li><strong>Qué cuenta para la posición:</strong> votaciones nominales en el Congreso y declaraciones de la dirección nacional de cada partido (candidato, líder, portavoces en el Congreso y en energía y, en el caso de los partidos del Gobierno, ministros). Las declaraciones de cargos autonómicos aparecen marcadas como «Voz regional» y no cuentan para la posición.</li>
<li><strong>Periodo:</strong> desde el inicio de la legislatura (17 de agosto de 2023). Si un partido ha cambiado de opinión, mostramos su posición más reciente y lo indicamos con «Cambió de posición». Las declaraciones anteriores aparecen como «Histórico». Si la posición no se ha invertido pero sí ha cambiado (por ejemplo, de ambigua a favorable), lo señalamos con «Su posición ha evolucionado», sin modificar la etiqueta.</li>
<li><strong>Ambiguo:</strong> en los últimos {cfg['current_window_days']} días con declaraciones, el partido ha dicho o votado cosas opuestas.</li>
<li><strong>Proposición:</strong> cada tema se mide respecto a una proposición concreta, inspirada en iniciativas debatidas en el Congreso. «A favor» o «En contra» se refiere solo a esa proposición.</li>
<li><strong>Fuentes:</strong> solo fuentes oficiales (Congreso, BOE, Gobierno, webs y cuentas oficiales de los partidos), agencias y medios de comunicación. Citamos siempre el texto literal y enlazamos la fuente.</li>
<li><strong>Correcciones:</strong> si detectas un error o una declaración que falta, escríbenos a {e(cfg['corrections_email'])}. Revisamos cada aviso.</li>
</ul></details>"""


def wrap_testo(inner, root_id):
    return ("<!-- wp:html -->\n"
            f'<div class="ppe-root" id="{root_id}">\n<style>{CSS}</style>\n{inner}\n</div>\n'
            + (JS % {"root_id": root_id}) +
            "<!-- /wp:html -->\n")


def wrap_intro(h1, paragraphs):
    out = ['<!-- wp:heading {"level":1} -->', f'<h1 class="wp-block-heading">{h1}</h1>', "<!-- /wp:heading -->", ""]
    for p in paragraphs:
        out += ["<!-- wp:paragraph -->", f"<p>{p}</p>", "<!-- /wp:paragraph -->", ""]
    return "\n".join(out)


def topic_title_hub(t):
    return f"¿Qué dicen los partidos sobre {t['title_label']}?"


def de(p):
    """'de' + nome partito con articolo: 'del PSOE', 'de Vox'."""
    a = p["label_article"]
    return "del " + a[3:] if a.startswith("el ") else "de " + a


def cap(s):
    return s[0].upper() + s[1:]


# ----------------------------------------------------------------- pages

def build_hub(cfg, parties, topics, groups, stmts, badges, today):
    rows = []
    for gkey, glabel in groups.items():
        rows.append(f'<tr class="ppe-group-row" data-ppe-topic-group="{gkey}"><th colspan="{len(parties) + 1}" scope="colgroup">{e(glabel)}</th></tr>')
        for t in [t for t in topics if t["group"] == gkey]:
            cells = "".join(
                f'<td data-ppe-party="{p["slug"]}"><a href="{e(party_url(cfg, p, t["key"]))}">{badge_html(badges[(p["key"], t["key"])], compact=True)}</a></td>'
                for p in parties)
            rows.append(f'<tr data-ppe-topic="{t["key"]}"><th scope="row"><a href="#{t["key"]}">{e(t["label_short"])}</a></th>{cells}</tr>')
    head = "".join(f'<th scope="col" data-ppe-party="{p["slug"]}"><a href="{e(party_url(cfg, p))}">{e(p["label"])}</a></th>' for p in parties)
    table = (f'<div class="ppe-tablewrap"><table class="ppe-table"><caption class="ppe-hidden">Posición de cada partido por tema</caption>'
             f'<thead><tr><th scope="col">Tema</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')

    chips_p = ['<button type="button" class="ppe-chip" data-filter="party" data-value="all" aria-pressed="true">Todos</button>'] + [
        f'<button type="button" class="ppe-chip" data-filter="party" data-value="{p["slug"]}" aria-pressed="false">{e(p["label"])}</button>' for p in parties]
    chips_t = ['<button type="button" class="ppe-chip" data-filter="topic" data-value="all" aria-pressed="true">Todos</button>'] + [
        f'<button type="button" class="ppe-chip" data-filter="topic" data-value="{t["key"]}" aria-pressed="false">{e(t["label_short"])}</button>' for t in topics]
    filters = (f'<div class="ppe-filters"><div class="ppe-filter" role="group" aria-label="Filtrar por partido"><span class="ppe-filter__label">Partido</span>{"".join(chips_p)}</div>'
               f'<div class="ppe-filter" role="group" aria-label="Filtrar por tema"><span class="ppe-filter__label">Tema</span>{"".join(chips_t)}</div></div>')

    sections = []
    for t in topics:
        cards = []
        for p in parties:
            items = sorted([s for s in stmts.get(p["key"], []) if s["topic"] == t["key"]], key=lambda s: s["date"], reverse=True)
            b = badges[(p["key"], t["key"])]
            nat = [s for s in items if s["level"] == "nacional"] or items
            # nella card dell'hub: prima la citazione letterale più recente (più incisiva), poi qualsiasi voce
            nat_q = [s for s in nat if s.get("quote") and d(s["date"]) >= d(cfg["legislature_start"])]
            if nat:
                s = (nat_q or nat)[0]
                body = (f'<p class="ppe-card__quote">{quote_or_context(s)}</p>'
                        f'<p class="ppe-card__meta">{e(s["person"])}{" (voz regional)" if s["level"] == "regional" else ""} · {e(fdate(s["date"], True))} · {source_link(s)}</p>')
                more = f'<a class="ppe-card__more" href="{e(party_url(cfg, p, t["key"]))}">Ver las {len(items)} declaraciones y votos {e(de(p))} →</a>' if len(items) > 1 else \
                       f'<a class="ppe-card__more" href="{e(party_url(cfg, p, t["key"]))}">Ver en la página {e(de(p))} →</a>'
            else:
                body = '<p class="ppe-empty">No hemos encontrado declaraciones ni votaciones de la dirección nacional sobre este tema desde agosto de 2023.</p>'
                more = ""
            cards.append(f'<article class="ppe-card" data-ppe-party="{p["slug"]}"><div class="ppe-card__head"><h3>{e(p["label"])}</h3>{badge_html(b)}</div>'
                         f'{change_popover(b, p, party_url(cfg, p, t["key"]))}{body}{more}</article>')
        prop = (f'<p class="ppe-prop"><strong>Proposición analizada:</strong> «{e(t["proposition"])}»</p>' if t["proposition"]
                else '<p class="ppe-prop">En este tema no hay una proposición única de sí o no: mostramos las declaraciones de cada partido.</p>')
        sections.append(f'<section class="ppe-topic" id="{t["key"]}" data-ppe-topic="{t["key"]}"><h2>{e(topic_title_hub(t))}</h2>{prop}<div class="ppe-cards">{"".join(cards)}</div></section>')

    inner = (f'<p class="ppe-updated">Última actualización: {e(fdate(today))} · {e(cfg["election_label"])}</p>'
             f'{filters}{table}{legend_html()}{"".join(sections)}{methodology_html(cfg)}')
    h1 = f'{e(cfg["tool_name"])}: qué dicen los partidos sobre la luz, el gas y la energía'
    intro = wrap_intro(h1, [
        f'¿Qué piensan PSOE, PP, Vox, Sumar, Podemos y SALF sobre el precio de la luz, el IVA de la factura, las nucleares o el bono social? '
        f'Hemos reunido sus declaraciones y votaciones sobre {len(topics)} temas de energía, cada una con su fecha y su fuente.',
        'No valoramos los programas: mostramos qué dice y qué vota cada partido, y cuándo ha cambiado de opinión. '
        'Elige un partido o un tema para filtrar.'])
    return intro, wrap_testo(inner, "ppe-hub")


def build_party(cfg, p, parties, topics, stmts, badges, today):
    min_date = d(cfg.get("party_min_date", {}).get(p["key"], cfg["legislature_start"]))
    items_all = stmts.get(p["key"], [])
    summary = "".join(f'<li data-ppe-topic="{t["key"]}"><a href="#{t["key"]}"><span>{e(t["label_short"])}</span>{badge_html(badges[(p["key"], t["key"])])}</a></li>' for t in topics)
    chips_t = ['<button type="button" class="ppe-chip" data-filter="topic" data-value="all" aria-pressed="true">Todos los temas</button>'] + [
        f'<button type="button" class="ppe-chip" data-filter="topic" data-value="{t["key"]}" aria-pressed="false">{e(t["label_short"])}</button>' for t in topics]
    sections = []
    for t in topics:
        items = sorted([s for s in items_all if s["topic"] == t["key"]], key=lambda s: s["date"], reverse=True)
        b = badges[(p["key"], t["key"])]
        prop = (f'<p class="ppe-prop"><strong>Proposición analizada:</strong> «{e(t["proposition"])}»</p>' if t["proposition"]
                else '<p class="ppe-prop">En este tema no hay una proposición única de sí o no: mostramos las declaraciones.</p>')
        tl = (f'<ol class="ppe-timeline">{"".join(statement_li(s, min_date) for s in items)}</ol>' if items
              else '<p class="ppe-empty">No hemos encontrado declaraciones ni votaciones de la dirección nacional sobre este tema desde agosto de 2023.</p>')
        sections.append(f'<section class="ppe-ptopic" id="{t["key"]}" data-ppe-topic="{t["key"]}"><div class="ppe-ptopic__head"><h2>{e(cap(p["label_article"]))} y {e(t["title_label"])}</h2>{badge_html(b)}</div>'
                        f'{prop}{change_popover(b, p)}{tl}</section>')
    others = "".join(f'<a href="{e(party_url(cfg, o))}">{e(o["label"])}</a>' for o in parties if o["key"] != p["key"])
    inner = (f'<p class="ppe-updated">Última actualización: {e(fdate(today))} · {e(cfg["election_label"])} · '
             f'<a class="ppe-src" href="{e(cfg["base_path"])}">Ver todos los partidos en {e(cfg["tool_name"])}</a></p>'
             f'<h2>La posición {e(de(p))} en {len(topics)} temas</h2><ul class="ppe-summary">{summary}</ul>{legend_html()}'
             f'<div class="ppe-filters"><div class="ppe-filter" role="group" aria-label="Filtrar por tema"><span class="ppe-filter__label">Tema</span>{"".join(chips_t)}</div></div>'
             f'{"".join(sections)}<h2>Qué dicen los demás partidos</h2><div class="ppe-others">{others}</div>{methodology_html(cfg)}')
    if p.get("h1_person"):
        h1 = f'¿Qué piensan {e(p["h1_person"])} y {e(p["label_article"])} sobre la energía?'
    else:
        h1 = f'¿Qué piensa {e(p["label_article"])} sobre la energía?'
    n_items = len([s for s in items_all if d(s["date"]) >= min_date])
    intro = wrap_intro(h1, [
        f'Precio de la luz, IVA de la factura, nucleares, renovables, bono social: reunimos lo que {e(p["label_long_article"])} ha dicho y votado sobre energía '
        f'desde el inicio de la legislatura ({n_items} declaraciones y votaciones), cada una con su fecha y su fuente.',
        f'Forma parte de {e(cfg["tool_name"])}, que compara las posiciones de todos los partidos.'])
    return intro, wrap_testo(inner, f"ppe-{p['slug']}")


def preview(intro, testo, title):
    body = intro.replace("<!-- wp:", "<!-- ").replace("<!-- /wp:", "<!-- /") + testo
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><style>body{{margin:0;padding:24px 16px;font-family:Avenir,"Avenir Next","Nunito Sans",Inter,system-ui,sans-serif;color:#212430;background:#fff}}'
            f'.wrap{{max-width:1040px;margin:0 auto}}h1{{font-size:36px;line-height:40px;font-weight:800;margin:0 0 16px}}</style></head>'
            f'<body><div class="wrap">{body}</div></body></html>')


# ----------------------------------------------------------------- main

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--statements-dir", default=str(DATA / "statements"))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    cfg = load_json(DATA / "config.json")
    parties = load_json(DATA / "parties.json")["parties"]
    tdoc = load_json(DATA / "topics.json")
    topics, groups = tdoc["topics"], tdoc["groups"]
    tiers = load_json(DATA / "source_tiers.json")
    sdir = Path(a.statements_dir)
    by_party = {}
    for p in parties:
        f = sdir / f"{p['slug']}.json"
        by_party[p["key"]] = load_json(f) if f.exists() else {"statements": []}

    errors, warnings = validate(by_party, parties, topics, tiers)
    stmts = {k: v.get("statements", []) for k, v in by_party.items()}
    badges = {(p["key"], t["key"]): compute_badge([s for s in stmts[p["key"]] if s["topic"] == t["key"]], t, p["key"], cfg)
              for p in parties for t in topics}

    # ---- report
    per_party = ", ".join("%s %d" % (p["label"], len(stmts[p["key"]])) for p in parties)
    print(f"Dichiarazioni caricate: {sum(len(v) for v in stmts.values())} ({per_party})")
    missing = [p["slug"] for p in parties if not (sdir / f"{p['slug']}.json").exists()]
    if missing:
        print(f"⚠️  File dati mancanti: {', '.join(missing)}")
    for w in warnings:
        print(f"⚠️  {w}")
    for er in errors:
        print(f"⛔ {er}")
    out = Path(a.out)
    prev_f = out / "badges.json"
    prev = load_json(prev_f) if prev_f.exists() else {}
    cur = {f"{pk}|{tk}": {"badge": b["badge"], "change": bool(b["change"]), "dice_vota": b["dice_vota"]} for (pk, tk), b in badges.items()}
    changed = [(k, prev.get(k), v) for k, v in cur.items() if prev and prev.get(k) != v]
    print("\nMatrice badge:")
    for t in topics:
        cells = []
        for p in parties:
            b = badges[(p["key"], t["key"])]
            cells.append("%s:%s%s" % (p["label"][:7], BADGE[b["badge"]][0][:9], "↻" if b["change"] else ""))
        print(f"  {t['label_short'][:22]:<22} " + " | ".join(cells))
    if prev:
        print(f"\n🔄 Badge cambiati rispetto al build precedente: {len(changed)}")
        for k, old, new in changed:
            print(f"  - {k}: {old} -> {new}   (possibile gancio PR)")
    if errors:
        print("\n⛔ Errori di validazione: correggere i dati prima di generare. Nessun file scritto.")
        sys.exit(1)
    if a.check:
        return

    today = date.today()
    pages = [("hub", "Hub", *build_hub(cfg, parties, topics, groups, stmts, badges, today))]
    for p in parties:
        pages.append((p["slug"], p["label"], *build_party(cfg, p, parties, topics, stmts, badges, today)))
    (out / "preview").mkdir(parents=True, exist_ok=True)
    for slug, title, intro, testo in pages:
        pdir = out / slug
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "codice_intro.html").write_text(intro, encoding="utf-8")
        (pdir / "codice_testo.html").write_text(testo, encoding="utf-8")
        (out / "preview" / f"{slug}.html").write_text(preview(intro, testo, title), encoding="utf-8")
    prev_f.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n📝 Generati {len(pages)} pagine in {out} (codice_intro.html + codice_testo.html per pagina, anteprime in output/preview/)")


if __name__ == "__main__":
    main()

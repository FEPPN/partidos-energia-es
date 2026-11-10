"""5 proposte visuali per la pagina HUB (prototipi standalone con i dati reali).

Vincoli dati da Diego (8 ott 2026): niente Design System CAT, solo font papernest (Avenir) + colore primario #5a52ff.
Riferimenti: diretta SkyTG24 (timeline live) + 29nov.es (domanda da completare, colonne partito, fonte come chip).

Uso:   py scripts/hub_proposals.py
Output: output/proposte_hub/01-directo.html ... 05-portada.html  (+ index.html scritto a parte con l'analisi UX)
"""
import html
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402

OUT = B.ROOT / "output" / "proposte_hub"
e = html.escape

PARTY_COLOR = {  # colori identificativi approssimativi, da verificare con i brand book dei partiti
    "PSOE": "#e30613", "PP": "#1d5fae", "VOX": "#5bbf21", "SUMAR": "#e5307a", "PODEMOS": "#6b2d7b", "SALF": "#1f1f1f"}
ANS = {  # risposta in forma Sí/No rispetto alla domanda del tema
    "a_favor": ("Sí", "si"), "en_contra": ("No", "no"), "ambiguo": ("Ambiguo", "amb"),
    "sin_declaraciones": ("Sin datos", "nd"), "sin_badge": ("Ver citas", "cit"), "na": ("", "na")}


# ----------------------------------------------------------------- data

def load():
    cfg = B.load_json(B.DATA / "config.json")
    parties = B.load_json(B.DATA / "parties.json")["parties"]
    tdoc = B.load_json(B.DATA / "topics.json")
    topics, groups = tdoc["topics"], tdoc["groups"]
    stmts, feed = {}, []
    for p in parties:
        f = B.DATA / "statements" / f"{p['slug']}.json"
        stmts[p["key"]] = B.load_json(f)["statements"] if f.exists() else []
        for s in stmts[p["key"]]:
            feed.append({**s, "_party": p})
    tmap = {t["key"]: t for t in topics}
    for s in feed:
        s["_topic"] = tmap[s["topic"]]
    feed.sort(key=lambda s: s["date"], reverse=True)
    badges = {(p["key"], t["key"]): B.compute_badge([s for s in stmts[p["key"]] if s["topic"] == t["key"]], t, p["key"], cfg)
              for p in parties for t in topics}
    changes = []
    for (pk, tk), b in badges.items():
        for kind in ("change", "historic_change", "evolution"):
            if b.get(kind):
                changes.append({"party": next(p for p in parties if p["key"] == pk), "topic": tmap[tk], "kind": kind,
                                "badge": b["badge"], **b[kind]})
    changes.sort(key=lambda c: c["after"]["date"], reverse=True)
    today = date(2026, 10, 8) if date.today() < date(2026, 10, 8) else date.today()
    election = date(2026, 11, 29)
    return {"cfg": cfg, "parties": parties, "topics": topics, "groups": groups, "stmts": stmts, "feed": feed,
            "badges": badges, "changes": changes, "today": today, "days_left": (election - today).days,
            "n": len(feed)}


def rel(ds, today):
    n = (today - B.d(ds)).days
    if n <= 0:
        return "hoy"
    if n == 1:
        return "ayer"
    if n < 7:
        return f"hace {n} días"
    if n < 31:
        w = n // 7
        return f"hace {w} semana{'s' if w > 1 else ''}"
    if n < 365:
        m = n // 30
        return f"hace {m} mes{'es' if m > 1 else ''}"
    y = n // 365
    return f"hace {y} año{'s' if y > 1 else ''}"


def ans_pill(stance_or_badge, big=False):
    label, mod = ANS.get(stance_or_badge, ("", "na"))
    if not label:
        return ""
    return f'<span class="hp-ans hp-ans--{mod}{" hp-ans--big" if big else ""}">{e(label)}</span>'


def pchip(p, short=True):
    return (f'<span class="hp-pchip" style="--pc:{PARTY_COLOR[p["key"]]}"><i></i>{e(p["label"] if short else p["label_long"])}</span>')


def src(s):
    return (f'<a class="hp-src" href="{e(s["source_url"])}" target="_blank" rel="noopener">{e(s["source_name"])} · '
            f'{e(B.fdate(s["date"], True))}</a>')


def short(text, n=110):
    text = (text or "").strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def headline(s, compact=False):
    """Titolo: la citazione letterale (come Sky). Per voti senza citazione: 'Votó Sí: <iniziativa>' accorciato se compact."""
    if s.get("quote"):
        return f"«{e(short(s['quote'], 220) if compact else s['quote'])}»"
    if s["type"] == "voto":
        lab = ANS.get(s["stance"], ("", ""))[0]
        verb = {"Sí": "Votó a favor", "No": "Votó en contra", "Ambiguo": "Votación"}.get(lab, "Votación")
        ctx = s.get("context") or ""
        return e(f"{verb}: {short(ctx.split('. ')[0], 120) if compact else ctx}")
    return e(short(s.get("context"), 160) if compact else (s.get("context") or ""))


def best_item(D, p, t):
    items = [s for s in D["stmts"][p["key"]] if s["topic"] == t["key"]]
    items.sort(key=lambda s: s["date"], reverse=True)
    nat = [s for s in items if s["level"] == "nacional"]
    q = [s for s in nat if s.get("quote") and s["date"] >= D["cfg"]["legislature_start"]]
    return (q or nat or items or [None])[0], items


def pick_latest(feed, n=5, max_votes=2, max_per_party=2):
    """'Lo último': voci nazionali più recenti; max 2 voti (le citazioni leggono meglio) e max 2 per partito (pluralità)."""
    out, votes, per = [], 0, {}
    for s in feed:
        if s["level"] != "nacional" or per.get(s["_party"]["key"], 0) >= max_per_party:
            continue
        if not s.get("quote"):
            if votes >= max_votes:
                continue
            votes += 1
        k = s["_party"]["key"]
        per[k] = per.get(k, 0) + 1
        out.append(s)
        if len(out) == n:
            break
    return out


def change_text(c):
    kind = {"change": "Cambió de posición", "historic_change": "Antes de esta legislatura decía otra cosa",
            "evolution": "Su posición ha evolucionado"}[c["kind"]]
    return kind


BASE_CSS = """
:root{--hp-p:#5a52ff;--hp-p-dark:#3d36d1;--hp-p-soft:#eeedff;--hp-ink:#15151f;--hp-ink2:#3c3d4f;--hp-mute:#6d6f82;--hp-line:#e4e4ec;--hp-bg:#f6f6fa;
--hp-si:#14a05a;--hp-si-bg:#e3f6ec;--hp-no:#e0383e;--hp-no-bg:#fde8e8;--hp-amb:#d99100;--hp-amb-bg:#fff4dc;--hp-nd:#9a9cae}
*{box-sizing:border-box}
body{margin:0;font-family:Avenir,"Avenir Next","Nunito Sans","Segoe UI",system-ui,sans-serif;color:var(--hp-ink);background:#fff;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:var(--hp-p)}
.hp-wrap{max-width:1180px;margin:0 auto;padding:0 16px}
.hp-ans{display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;letter-spacing:.02em;padding:3px 10px;border-radius:999px;white-space:nowrap;line-height:18px}
.hp-ans--si{background:var(--hp-si-bg);color:#0b6d3c}.hp-ans--no{background:var(--hp-no-bg);color:#a8161c}
.hp-ans--amb{background:var(--hp-amb-bg);color:#8a5a00}.hp-ans--nd{background:#fff;color:var(--hp-nd);border:1px dashed #cfd0dc;font-weight:500}
.hp-ans--cit{background:#fff;color:var(--hp-mute);border:1px solid var(--hp-line);font-weight:500}
.hp-ans--big{font-size:15px;padding:6px 14px}
.hp-pchip{display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:13px;color:var(--hp-ink)}
.hp-pchip i{width:10px;height:10px;border-radius:50%;background:var(--pc);display:inline-block}
.hp-src{font-size:12px;color:var(--hp-mute);text-decoration:none;border:1px solid var(--hp-line);border-radius:6px;padding:2px 8px;display:inline-block}
.hp-src:hover{color:var(--hp-p);border-color:var(--hp-p)}
.hp-tag{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:var(--hp-mute)}
.hp-btn{font:inherit;font-size:14px;font-weight:800;border:1px solid var(--hp-line);background:#fff;color:var(--hp-ink);border-radius:999px;padding:7px 14px;cursor:pointer}
.hp-btn[aria-pressed=true],.hp-btn.is-on{background:var(--hp-p);border-color:var(--hp-p);color:#fff}
.hp-hide{display:none!important}
.hp-countdown{font-weight:800}
.hp-proto{position:fixed;right:12px;bottom:12px;z-index:50;background:var(--hp-ink);color:#fff;font-size:12px;padding:6px 10px;border-radius:8px;opacity:.85}
"""


def page(title, css, body, js=""):
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title><style>{BASE_CSS}{css}</style></head><body>{body}'
            f'<div class="hp-proto">Prototipo · {e(title)}</div>'
            f'<script>setTimeout(function(){{try{{{js}}}catch(err){{console.warn(err)}}}},300);</script></body></html>')


# ================================================================= 01 DIRECTO (SkyTG24)

def v1_directo(D):
    P, T, today = D["parties"], D["topics"], D["today"]
    # "En evidencia": fatti calcolati, nessuna opinione
    nuc = [D["badges"][(p["key"], "nucleares")]["badge"] for p in P]
    latest = next(s for s in D["feed"] if s["level"] == "nacional")
    pinned = [
        f'<li><b>Última actualización:</b> {e(latest["person"])} ({e(latest["_party"]["label"])}) sobre {e(latest["_topic"]["title_label"])}, {e(rel(latest["date"], today))}.</li>',
        f'<li><b>Nucleares:</b> {nuc.count("a_favor")} partidos a favor de derogar el calendario de cierre, {nuc.count("en_contra")} en contra.</li>',
        f'<li><b>{len(D["changes"])} cambios de posición</b> detectados desde 2019 en {len({c["party"]["key"] for c in D["changes"]})} partidos.</li>']
    items = []
    for i, s in enumerate(D["feed"]):
        p, t = s["_party"], s["_topic"]
        hidden = " hp-more" if i >= 15 else ""
        reg = '<span class="hp-tag">Voz regional</span>' if s["level"] == "regional" else ""
        items.append(
            f'<li class="d-item{hidden}" data-party="{p["slug"]}" data-topic="{t["key"]}">'
            f'<div class="d-time"><b>{e(rel(s["date"], today))}</b><span>{e(B.fdate(s["date"], True))}</span></div>'
            f'<article class="d-card" style="--pc:{PARTY_COLOR[p["key"]]}">'
            f'<div class="d-top">{pchip(p)}<span class="hp-tag">{e(t["label_short"])}</span>{ans_pill(s["stance"])}{reg}</div>'
            f'<h3 class="d-h">{headline(s, compact=True)}</h3>'
            + (f'<details class="d-ctx"><summary>Contexto</summary><p>{e(s["context"])}</p></details>' if s.get("context") else "") +
            f'<p class="d-meta"><b>{e(s["person"])}</b> · {e(s["role"])}</p>'
            f'<p class="d-src">{src(s)}</p></article></li>')
    side_rows = "".join(
        f'<tr data-topic="{t["key"]}"><th>{e(t["label_short"])}</th>' +
        "".join(f'<td title="{e(p["label"])}: {e(ANS[D["badges"][(p["key"], t["key"])]["badge"]][0])}"><i class="dot dot--{ANS[D["badges"][(p["key"], t["key"])]["badge"]][1]}"></i></td>' for p in P) + "</tr>"
        for t in T)
    side_head = "".join(f'<th><span style="color:{PARTY_COLOR[p["key"]]}">●</span><br>{e(p["label"][:6])}</th>' for p in P)
    pchips = "".join(f'<button class="hp-btn" data-f="party" data-v="{p["slug"]}" aria-pressed="false">{e(p["label"])}</button>' for p in P)
    topts = "".join(f'<option value="{t["key"]}">{e(t["label_short"])}</option>' for t in T)
    body = f"""
<header class="d-bar"><div class="hp-wrap d-bar__in"><b class="d-logo">[NOMBRE TOOL]</b><span class="d-live"><i></i>EN DIRECTO</span>
<span>Elecciones 29N · <span class="hp-countdown">Faltan {D['days_left']} días</span></span><span class="d-upd">{D['n']} declaraciones y votos verificados</span></div></header>
<main class="hp-wrap d-grid">
<div>
<h1 class="d-h1">Energía y elecciones: lo que dicen los partidos, en directo</h1>
<p class="d-lead">Cada declaración y cada votación sobre la luz, el gas y la energía de PSOE, PP, Vox, Sumar, Podemos y SALF, con su fecha y su fuente. Sin opiniones: solo lo que han dicho y votado.</p>
<section class="d-pin"><h2>📌 En evidencia</h2><ul>{''.join(pinned)}</ul></section>
<div class="d-filters"><button class="hp-btn" data-f="party" data-v="all" aria-pressed="true">Todos</button>{pchips}
<select class="d-sel" aria-label="Tema"><option value="all">Todos los temas</option>{topts}</select></div>
<div class="d-livebar">LIVE</div>
<ol class="d-feed">{''.join(items)}</ol>
<button class="hp-btn d-loadmore">Cargar más declaraciones</button>
</div>
<aside class="d-side"><div class="d-side__box"><h2>La foto de hoy</h2><p>¿Qué responde cada partido? Pulsa un tema para filtrar el directo.</p>
<table class="d-mini"><thead><tr><th></th>{side_head}</tr></thead><tbody>{side_rows}</tbody></table>
<p class="d-legend"><i class="dot dot--si"></i>Sí <i class="dot dot--no"></i>No <i class="dot dot--amb"></i>Ambiguo <i class="dot dot--nd"></i>Sin datos <i class="dot dot--cit"></i>Sin pregunta sí/no</p></div></aside>
</main>"""
    css = """
.d-bar{background:var(--hp-ink);color:#fff;font-size:13px;position:sticky;top:0;z-index:10}
.d-bar__in{display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding-top:10px;padding-bottom:10px}
.d-logo{font-size:15px}.d-upd{margin-left:auto;color:#c9c9d6}
.d-live{display:inline-flex;align-items:center;gap:6px;background:var(--hp-p);padding:3px 10px;border-radius:4px;font-weight:800;font-size:12px;letter-spacing:.06em}
.d-live i{width:8px;height:8px;border-radius:50%;background:#fff;animation:pulse 1.4s infinite}
@keyframes pulse{0%{opacity:1}50%{opacity:.25}100%{opacity:1}}
.d-grid{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:40px;padding-top:32px;padding-bottom:64px}
.d-h1{font-size:40px;line-height:44px;font-weight:800;margin:0 0 12px;letter-spacing:-.01em}
.d-lead{font-size:17px;color:var(--hp-ink2);margin:0 0 24px;max-width:680px}
.d-pin{border:1px solid var(--hp-line);border-radius:10px;overflow:hidden;margin-bottom:24px}
.d-pin h2{margin:0;background:var(--hp-ink);color:#fff;font-size:13px;text-transform:uppercase;letter-spacing:.08em;padding:8px 16px}
.d-pin ul{margin:0;padding:14px 16px 14px 34px;display:flex;flex-direction:column;gap:6px;font-size:15px}
.d-filters{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:16px}
.d-sel{font:inherit;font-size:14px;padding:7px 12px;border-radius:999px;border:1px solid var(--hp-line);background:#fff}
.d-livebar{background:var(--hp-p);color:#fff;text-align:center;font-weight:800;letter-spacing:.1em;font-size:13px;padding:6px;border-radius:6px 6px 0 0}
.d-feed{list-style:none;margin:0;padding:16px 0 0 0;position:relative}
.d-feed:before{content:"";position:absolute;left:110px;top:0;bottom:0;width:2px;background:var(--hp-line)}
.d-item{display:grid;grid-template-columns:96px 1fr;gap:28px;margin-bottom:16px;position:relative}
.d-item:before{content:"";position:absolute;left:105px;top:8px;width:12px;height:12px;border-radius:50%;background:#fff;border:3px solid var(--hp-p)}
.d-item:first-child:before{background:var(--hp-p);box-shadow:0 0 0 4px var(--hp-p-soft)}
.d-time{text-align:right;font-size:13px;color:var(--hp-mute);display:flex;flex-direction:column;padding-top:4px}
.d-time b{color:var(--hp-ink)}
.d-card{background:#fff;border:1px solid var(--hp-line);border-left:4px solid var(--pc);border-radius:8px;padding:14px 16px;box-shadow:0 1px 2px rgba(20,20,40,.04)}
.d-top{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
.d-h{margin:0 0 6px;font-size:18px;line-height:25px;font-weight:800}
.d-meta{margin:0 0 8px;font-size:13px;color:var(--hp-ink2)}.d-src{margin:0}
.d-loadmore{display:block;margin:8px auto 0}
.hp-more{display:none}.d-feed.is-all .hp-more{display:grid}
.d-side{position:relative}.d-side__box{position:sticky;top:64px;border:1px solid var(--hp-line);border-radius:12px;padding:16px;background:var(--hp-bg)}
.d-side h2{margin:0 0 4px;font-size:18px}.d-side p{margin:0 0 12px;font-size:13px;color:var(--hp-mute)}
.d-mini{width:100%;border-collapse:collapse;font-size:12px}
.d-mini th{font-weight:800;text-align:left;padding:5px 4px;font-size:11px}.d-mini thead th{text-align:center;line-height:13px}
.d-mini td{text-align:center;padding:5px 2px;border-top:1px solid var(--hp-line)}
.d-mini tbody tr{cursor:pointer}.d-mini tbody tr:hover{background:#fff}.d-mini tbody tr.is-on{background:var(--hp-p-soft)}
.dot{display:inline-block;width:14px;height:14px;border-radius:50%;vertical-align:middle}
.d-ctx{font-size:13px;color:var(--hp-ink2);margin:0 0 8px}.d-ctx summary{cursor:pointer;color:var(--hp-mute);font-weight:800}.d-ctx p{margin:4px 0 0}
.dot--si{background:var(--hp-si)}.dot--no{background:var(--hp-no)}.dot--amb{background:var(--hp-amb)}
.dot--nd{border:2px dashed #c4c5d3}.dot--cit{background:#d9dae6;width:8px;height:8px}
.d-legend{margin-top:10px!important;display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center}
@media(max-width:900px){.d-grid{grid-template-columns:1fr}.d-side{order:-1}.d-side__box{position:static}.d-h1{font-size:30px;line-height:34px}
.d-feed:before{left:8px}.d-item{grid-template-columns:1fr;gap:4px;padding-left:28px}.d-item:before{left:3px}.d-time{text-align:left;flex-direction:row;gap:8px}.d-upd{display:none}}
"""
    js = """
var st={party:'all',topic:'all'};var feed=document.querySelector('.d-feed');
function apply(){document.querySelectorAll('.d-item').forEach(function(li){var ok=(st.party==='all'||li.dataset.party===st.party)&&(st.topic==='all'||li.dataset.topic===st.topic);li.classList.toggle('hp-hide',!ok)});
 var filtered=st.party!=='all'||st.topic!=='all';feed.classList.toggle('is-all',filtered);
 document.querySelectorAll('.d-mini tbody tr').forEach(function(tr){tr.classList.toggle('is-on',tr.dataset.topic===st.topic)})}
document.querySelectorAll('[data-f=party]').forEach(function(b){b.addEventListener('click',function(){st.party=b.dataset.v;document.querySelectorAll('[data-f=party]').forEach(function(x){x.setAttribute('aria-pressed',x===b)});apply()})});
var sel=document.querySelector('.d-sel');sel.addEventListener('change',function(){st.topic=sel.value;apply()});
document.querySelectorAll('.d-mini tbody tr').forEach(function(tr){tr.addEventListener('click',function(){st.topic=(st.topic===tr.dataset.topic)?'all':tr.dataset.topic;sel.value=st.topic;apply();feed.scrollIntoView({behavior:'smooth'})})});
document.querySelector('.d-loadmore').addEventListener('click',function(e){feed.classList.add('is-all');e.target.remove()});
"""
    return page("01 · Directo", css, body, js)


# ================================================================= 02 RELLENA EL HUECO (29nov.es)

def v2_hueco(D):
    P, T = D["parties"], D["topics"]
    chips = ""
    for gk, gl in D["groups"].items():
        chips += f'<span class="h-glab">{e(gl)}</span>' + "".join(
            f'<button class="h-topic" data-t="{t["key"]}">{e(t["label_short"].lower() if t["key"] not in ("data_center",) else "centros de datos")}</button>'
            for t in T if t["group"] == gk)
    pchips = "".join(f'<button class="hp-btn is-on" data-p="{p["slug"]}" style="--pc:{PARTY_COLOR[p["key"]]}">{e(p["label"])}</button>' for p in P)
    panels = []
    for i, t in enumerate(T):
        cols = []
        for p in P:
            b = D["badges"][(p["key"], t["key"])]
            s, items = best_item(D, p, t)
            ch = next((c for c in D["changes"] if c["party"]["key"] == p["key"] and c["topic"]["key"] == t["key"]), None)
            chx = (f'<details class="h-ch"><summary>↻ {e(change_text(ch))}</summary><p><b>{e(B.fdate(ch["before"]["date"], True))}</b> · {e(ANS[ch["before"]["stance"]][0])}: {headline(ch["before"])}</p>'
                   f'<p><b>{e(B.fdate(ch["after"]["date"], True))}</b> · {e(ANS[ch["after"]["stance"]][0])}: {headline(ch["after"])}</p></details>') if ch else ""
            body = (f'<p class="h-q">{headline(s, True)}</p><p class="h-who">{e(s["person"])}{" · voz regional" if s["level"] == "regional" else ""}</p><p>{src(s)}</p>'
                    if s else '<p class="h-empty">Sin declaraciones de la dirección nacional desde agosto de 2023.</p>')
            more = ""
            if len(items) > 1:
                more = '<details class="h-more"><summary>Ver las ' + str(len(items)) + ' declaraciones y votos</summary><ol>' + "".join(
                    f'<li><b>{e(B.fdate(x["date"], True))}</b> {ans_pill(x["stance"])} {headline(x)} <span class="h-who">— {e(x["person"])}</span> {src(x)}</li>' for x in items) + "</ol></details>"
            cols.append(f'<article class="h-col" data-p="{p["slug"]}" style="--pc:{PARTY_COLOR[p["key"]]}"><header><h3>{e(p["label"])}</h3>{ans_pill(b["badge"], True)}</header>{chx}{body}{more}</article>')
        prop = (f'<p class="h-prop"><span>La pregunta</span>{e(t["question_short"])}</p>' if t["proposition"]
                else f'<p class="h-prop"><span>Sin pregunta de sí o no</span>Mostramos lo último que ha dicho cada partido.</p>')
        panels.append(f'<section class="h-panel{"" if i == 0 else " hp-hide"}" id="{t["key"]}" data-t="{t["key"]}"><h2>{e(t["label"])}</h2>{prop}<div class="h-cols">{"".join(cols)}</div></section>')
    body = f"""
<header class="h-top"><div class="hp-wrap h-top__in"><b>[NOMBRE TOOL]</b><span>Elecciones generales del 29 de noviembre</span><span class="h-sep">|</span><span>Faltan {D['days_left']} días</span><span class="h-r">por papernest</span></div></header>
<section class="hp-wrap h-hero"><h1>¿Qué dicen los partidos sobre <span class="h-slot" aria-live="polite">{e(T[0]["title_label"])}</span>?</h1>
<p class="h-sub">Declaraciones y votaciones desde 2023, con sus propias palabras y la fuente de cada una. Actualizado el {e(B.fdate(D['today']))}.</p>
<div class="h-chips">{chips}</div></section>
<div class="h-cmp"><div class="hp-wrap h-cmp__in"><span>Partidos que comparas:</span>{pchips}</div></div>
<main class="hp-wrap h-main">{''.join(panels)}</main>"""
    css = """
.h-top{border-bottom:1px solid var(--hp-line);font-size:13px;color:var(--hp-mute)}.h-top__in{display:flex;gap:10px;align-items:center;padding-top:12px;padding-bottom:12px}
.h-top b{color:var(--hp-ink);font-size:16px}.h-r{margin-left:auto;color:var(--hp-p);font-weight:800}.h-sep{color:var(--hp-line)}
.h-hero{padding-top:56px;padding-bottom:32px}
.h-hero h1{font-size:52px;line-height:58px;font-weight:800;margin:0 0 12px;max-width:900px;letter-spacing:-.02em}
.h-slot{color:var(--hp-p);border-bottom:4px solid var(--hp-p);white-space:normal}
.h-sub{color:var(--hp-ink2);font-size:17px;margin:0 0 24px}
.h-chips{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.h-glab{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--hp-mute);margin:0 4px 0 8px}.h-glab:first-child{margin-left:0}
.h-topic{font:inherit;font-weight:800;font-size:14px;border:1px solid var(--hp-ink);background:#fff;border-radius:6px;padding:6px 12px;cursor:pointer}
.h-topic.is-on{background:var(--hp-p);border-color:var(--hp-p);color:#fff}
.h-cmp{background:var(--hp-bg);border-top:1px solid var(--hp-line);border-bottom:1px solid var(--hp-line);position:sticky;top:0;z-index:5}
.h-cmp__in{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding-top:10px;padding-bottom:10px;font-size:14px;color:var(--hp-mute)}
.h-cmp .hp-btn.is-on{background:#fff;color:var(--hp-ink);border-color:var(--pc);box-shadow:inset 0 -3px 0 var(--pc)}
.h-cmp .hp-btn:not(.is-on){opacity:.45}
.h-main{padding-top:32px;padding-bottom:80px}
.h-panel h2{font-size:30px;margin:0 0 12px}
.h-prop{font-size:20px;font-weight:800;margin:0 0 24px;display:flex;flex-direction:column;gap:2px}
.h-prop span{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--hp-p)}
.h-cols{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.h-col{border-top:4px solid var(--pc);background:#fff;border-left:1px solid var(--hp-line);border-right:1px solid var(--hp-line);border-bottom:1px solid var(--hp-line);padding:16px;display:flex;flex-direction:column;gap:8px}
.h-col header{display:flex;justify-content:space-between;align-items:center}.h-col h3{margin:0;font-size:18px}
.h-q{font-family:Georgia,"Times New Roman",serif;font-size:16px;line-height:24px;margin:0;color:var(--hp-ink)}
.h-who{font-size:13px;color:var(--hp-mute);margin:0}.h-col p{margin:0}
.h-empty{font-style:italic;color:var(--hp-mute)}
.h-ch{font-size:13px;background:var(--hp-p-soft);border-radius:6px;padding:6px 10px}.h-ch summary{cursor:pointer;font-weight:800;color:var(--hp-p-dark)}
.h-more{font-size:13px;border-top:1px solid var(--hp-line);padding-top:8px;margin-top:auto}.h-more summary{cursor:pointer;font-weight:800;color:var(--hp-ink)}
.h-more ol{padding-left:18px;display:flex;flex-direction:column;gap:8px}
@media(max-width:700px){.h-hero h1{font-size:34px;line-height:40px}.h-top__in span:not(.h-r):not(:nth-child(4)){display:none}}
"""
    js = """
var slot=document.querySelector('.h-slot');var labels=%s;
function show(k){document.querySelectorAll('.h-panel').forEach(function(p){p.classList.toggle('hp-hide',p.dataset.t!==k)});
 document.querySelectorAll('.h-topic').forEach(function(b){b.classList.toggle('is-on',b.dataset.t===k)});slot.textContent=labels[k]}
document.querySelectorAll('.h-topic').forEach(function(b){b.addEventListener('click',function(){show(b.dataset.t)})});
document.querySelectorAll('.h-cmp .hp-btn').forEach(function(b){b.addEventListener('click',function(){b.classList.toggle('is-on');
 var on=b.classList.contains('is-on');document.querySelectorAll('.h-col[data-p='+b.dataset.p+']').forEach(function(c){c.classList.toggle('hp-hide',!on)})})});
show('%s');
""" % (json.dumps({t["key"]: t["title_label"] for t in T}, ensure_ascii=False), T[0]["key"])
    return page("02 · Rellena el hueco", css, body, js)


# ================================================================= 03 TABLERO (marcador del Congreso)

def v3_tablero(D):
    P, T = D["parties"], D["topics"]
    head = "".join(f'<th style="--pc:{PARTY_COLOR[p["key"]]}"><span>{e(p["label"])}</span></th>' for p in P)
    rows, details = [], []
    for gk, gl in D["groups"].items():
        rows.append(f'<tr class="t-group"><th colspan="{len(P) + 2}">{e(gl)}</th></tr>')
        for t in [x for x in T if x["group"] == gk]:
            cells, tally = [], {"a_favor": 0, "en_contra": 0}
            for p in P:
                b = D["badges"][(p["key"], t["key"])]
                tally[b["badge"]] = tally.get(b["badge"], 0) + 1
                mark = '<em title="Cambio de posición">↻</em>' if any(c["party"]["key"] == p["key"] and c["topic"]["key"] == t["key"] for c in D["changes"]) else ""
                lab, mod = ANS[b["badge"]]
                cid = f"c-{p['slug']}-{t['key']}"
                cells.append(f'<td><button class="t-cell t-cell--{mod}" data-c="{cid}" aria-label="{e(p["label"])}: {e(lab)}"><span class="t-disc"></span><small>{e(lab)}</small>{mark}</button></td>')
                s, items = best_item(D, p, t)
                lis = "".join(f'<li><span class="t-d">{e(B.fdate(x["date"], True))}</span>{ans_pill(x["stance"])}<div><p class="t-hq">{headline(x)}</p><p class="t-who">{e(x["person"])} · {e(x["role"])} · {src(x)}</p></div></li>' for x in items) \
                    or '<li><p class="t-who">Sin declaraciones de la dirección nacional desde agosto de 2023.</p></li>'
                details.append(f'<div class="t-detail hp-hide" id="{cid}"><div class="t-detail__h">{pchip(p)}<b>{e(t["question_short"])}</b>{ans_pill(b["badge"], True)}</div><ol>{lis}</ol></div>')
            bar = (f'<div class="t-bar"><i style="flex:{tally.get("a_favor", 0)}" class="b-si"></i><i style="flex:{tally.get("en_contra", 0)}" class="b-no"></i>'
                   f'<i style="flex:{tally.get("ambiguo", 0)}" class="b-amb"></i><i style="flex:{tally.get("sin_declaraciones", 0)}" class="b-nd"></i></div>') if t["proposition"] else '<span class="t-who">sin pregunta sí/no</span>'
            rows.append(f'<tr><th class="t-q"><a href="#{t["key"]}">{e(t["question_short"])}</a></th>{"".join(cells)}<td class="t-tally">{bar}</td></tr>')
    chg = "".join(
        f'<article class="t-chg" style="--pc:{PARTY_COLOR[c["party"]["key"]]}"><p class="hp-tag">{e(change_text(c))}</p><h3>{pchip(c["party"])} · {e(c["topic"]["label_short"])}</h3>'
        f'<p class="t-step"><b>{e(str(B.d(c["before"]["date"]).year))}</b> {ans_pill(c["before"]["stance"])} {headline(c["before"], True)}</p>'
        f'<p class="t-step"><b>{e(str(B.d(c["after"]["date"]).year))}</b> {ans_pill(c["after"]["stance"])} {headline(c["after"], True)}</p></article>' for c in D["changes"])
    body = f"""
<section class="t-hero"><div class="hp-wrap">
<p class="t-kicker">[NOMBRE TOOL] · Elecciones 29N · Faltan {D['days_left']} días</p>
<h1>El marcador energético de los partidos</h1>
<p class="t-lead">11 preguntas sobre la luz, el gas y la energía. Lo que responde cada partido según lo que ha dicho y votado desde 2023. Pulsa cualquier casilla para ver las pruebas.</p>
<div class="t-boardwrap"><table class="t-board"><thead><tr><th></th>{head}<th class="t-tally">Reparto</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="t-legend"><span class="t-cell t-cell--si"><span class="t-disc"></span></span>Sí <span class="t-cell t-cell--no"><span class="t-disc"></span></span>No <span class="t-cell t-cell--amb"><span class="t-disc"></span></span>Ambiguo <span class="t-cell t-cell--nd"><span class="t-disc"></span></span>Sin datos · ↻ cambio de posición · Colores como en el marcador de votaciones del Congreso.</p>
</div></section>
<section class="hp-wrap t-detailwrap"><div class="t-placeholder">↑ Pulsa una casilla del marcador para ver aquí todas las declaraciones y votos, con su fuente.</div>{''.join(details)}</section>
<section class="hp-wrap t-chgs"><h2>Han cambiado de posición</h2><div class="t-chgrow">{chg}</div></section>"""
    css = """
.t-hero{background:#101024;color:#fff;padding:40px 0 32px}
.t-kicker{color:#a9a6ff;font-weight:800;font-size:13px;letter-spacing:.06em;text-transform:uppercase;margin:0 0 8px}
.t-hero h1{font-size:46px;line-height:50px;margin:0 0 10px;letter-spacing:-.02em}
.t-lead{color:#c9c9dc;font-size:17px;max-width:720px;margin:0 0 24px}
.t-boardwrap{overflow-x:auto;border-radius:14px;background:#17173a;border:1px solid #2a2a5a}
.t-board{border-collapse:collapse;width:100%;min-width:860px}
.t-board thead th{padding:14px 6px;font-size:14px;position:relative}
.t-board thead th span{display:inline-block;padding-bottom:6px;border-bottom:3px solid var(--pc)}
.t-board td,.t-board th{text-align:center;border-top:1px solid #26264f}
.t-q{text-align:left!important;padding:10px 14px;font-weight:500;font-size:14px;max-width:300px}.t-q a{color:#fff;text-decoration:none}.t-q a:hover{color:#a9a6ff}
.t-group th{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#a9a6ff;padding:12px 14px 6px;background:#13132e}
.t-cell{background:none;border:0;cursor:pointer;display:inline-flex;flex-direction:column;align-items:center;gap:2px;padding:6px;color:#fff;font:inherit;position:relative;border-radius:8px}
.t-cell:hover,.t-cell.is-on{background:#2a2a5a}
.t-cell small{font-size:11px;color:#b9b9d0}
.t-cell em{position:absolute;top:2px;right:4px;font-style:normal;color:#ffd166;font-size:13px}
.t-disc{width:26px;height:26px;border-radius:50%;display:block;box-shadow:inset 0 -3px 0 rgba(0,0,0,.25)}
.t-cell--si .t-disc{background:#1fbf6b}.t-cell--no .t-disc{background:#f0454b}.t-cell--amb .t-disc{background:#f2b01e}
.t-cell--nd .t-disc{border:2px dashed #55557d;box-shadow:none}.t-cell--cit .t-disc{background:#3a3a6a;width:14px;height:14px;margin:6px}
.t-tally{width:140px;padding:0 14px}.t-bar{display:flex;height:8px;border-radius:4px;overflow:hidden;background:#26264f}
.b-si{background:#1fbf6b}.b-no{background:#f0454b}.b-amb{background:#f2b01e}.b-nd{background:#3a3a6a}
.t-legend{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;font-size:13px;color:#b9b9d0;margin:14px 0 0}
.t-legend .t-cell{padding:0;cursor:default}.t-legend .t-disc{width:14px;height:14px}
.t-detailwrap{padding-top:24px}
.t-placeholder{border:2px dashed var(--hp-line);border-radius:12px;padding:20px;color:var(--hp-mute);text-align:center}
.t-detail{border:1px solid var(--hp-line);border-radius:12px;padding:20px;box-shadow:0 10px 30px rgba(20,20,60,.08)}
.t-detail__h{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:18px;margin-bottom:12px}
.t-detail ol{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
.t-detail li{display:grid;grid-template-columns:90px 80px 1fr;gap:12px;align-items:start;border-top:1px solid var(--hp-line);padding-top:12px}
.t-d{font-weight:800;font-size:13px;color:var(--hp-mute)}.t-hq{margin:0 0 4px;font-weight:800}.t-who{margin:0;font-size:13px;color:var(--hp-mute)}
.t-chgs{padding:48px 16px 80px}.t-chgs h2{font-size:28px;margin:0 0 16px}
.t-chgrow{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.t-chg{border:1px solid var(--hp-line);border-top:4px solid var(--pc);border-radius:10px;padding:16px}
.t-chg h3{margin:4px 0 10px;font-size:16px}.t-step{margin:0 0 8px;font-size:14px}.t-step b{color:var(--hp-p)}
@media(max-width:700px){.t-hero h1{font-size:32px;line-height:36px}.t-detail li{grid-template-columns:1fr}
.t-board{min-width:0}.t-board thead tr,.t-board tbody tr{display:grid;grid-template-columns:repeat(6,1fr)}
.t-board thead th:first-child,.t-board .t-tally{display:none}.t-board thead th{font-size:11px;padding:10px 2px}
.t-q{grid-column:1/-1;max-width:none;border-top:1px solid #26264f;padding:12px 12px 2px!important}.t-board td{border-top:0;padding-bottom:8px}
.t-group th{grid-column:1/-1}.t-disc{width:22px;height:22px}.t-cell small{font-size:10px}}
"""
    js = """
var cur=null;document.querySelectorAll('.t-board .t-cell').forEach(function(b){b.addEventListener('click',function(){
 document.querySelectorAll('.t-detail').forEach(function(d){d.classList.add('hp-hide')});document.querySelectorAll('.t-cell').forEach(function(x){x.classList.remove('is-on')});
 document.querySelector('.t-placeholder').classList.add('hp-hide');var d=document.getElementById(b.dataset.c);d.classList.remove('hp-hide');b.classList.add('is-on');
 d.scrollIntoView({behavior:'smooth',block:'nearest'})})});
"""
    return page("03 · Marcador", css, body, js)


# ================================================================= 04 CARA A CARA

def v4_caraacara(D):
    P, T = D["parties"], D["topics"]
    opts = lambda sel: "".join(f'<option value="{p["slug"]}"{" selected" if p["slug"] == sel else ""}>{e(p["label_long"])}</option>' for p in P)
    rows = []
    for t in T:
        sides = {}
        for side in ("a", "b"):
            blocks = []
            for p in P:
                b = D["badges"][(p["key"], t["key"])]
                s, items = best_item(D, p, t)
                body = (f'<p class="c-q">{headline(s, True)}</p><p class="c-who">{e(s["person"])} · {src(s)}</p>' if s
                        else '<p class="c-who"><i>Sin declaraciones de la dirección nacional.</i></p>')
                blocks.append(f'<div class="c-blk" data-side="{side}" data-p="{p["slug"]}" data-ans="{b["badge"]}" style="--pc:{PARTY_COLOR[p["key"]]}">'
                              f'<div class="c-bh">{pchip(p)}{ans_pill(b["badge"], True)}</div>{body}</div>')
            sides[side] = "".join(blocks)
        rows.append(f'<section class="c-row" data-t="{t["key"]}"><h2>{e(t["question_short"])}</h2><div class="c-grid"><div class="c-side">{sides["a"]}</div>'
                    f'<div class="c-mid"><span class="c-verdict"></span></div><div class="c-side">{sides["b"]}</div></div></section>')
    body = f"""
<section class="c-hero"><div class="hp-wrap">
<p class="c-kicker">[NOMBRE TOOL] · Faltan {D['days_left']} días para el 29N</p>
<h1>Cara a cara energético</h1><p class="c-lead">Elige dos partidos y compara qué responden a las 11 preguntas clave sobre la energía.</p>
<div class="c-pick"><select id="pa" aria-label="Partido A">{opts('psoe')}</select><span class="c-vs">VS</span><select id="pb" aria-label="Partido B">{opts('pp')}</select></div>
<p class="c-score" aria-live="polite"></p></div></section>
<main class="hp-wrap c-main">{''.join(rows)}</main>"""
    css = """
.c-hero{background:linear-gradient(135deg,#5a52ff,#2b2580);color:#fff;padding:44px 0 36px;text-align:center}
.c-kicker{margin:0 0 6px;font-weight:800;font-size:13px;letter-spacing:.06em;text-transform:uppercase;opacity:.8}
.c-hero h1{font-size:48px;line-height:52px;margin:0 0 8px}.c-lead{margin:0 0 20px;opacity:.9;font-size:17px}
.c-pick{display:flex;justify-content:center;align-items:center;gap:16px;flex-wrap:wrap}
.c-pick select{font:inherit;font-weight:800;font-size:17px;padding:12px 16px;border-radius:12px;border:0;min-width:260px}
.c-vs{font-weight:800;font-size:22px;background:#fff;color:var(--hp-p);width:52px;height:52px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center}
.c-score{margin:18px 0 0;font-size:18px;font-weight:800}
.c-main{padding-top:24px;padding-bottom:80px}
.c-row{border-bottom:1px solid var(--hp-line);padding:24px 0}.c-row h2{text-align:center;font-size:22px;margin:0 0 16px}
.c-grid{display:grid;grid-template-columns:1fr 120px 1fr;gap:12px;align-items:stretch}
.c-blk{display:none;background:#fff;border:1px solid var(--hp-line);border-top:4px solid var(--pc);border-radius:10px;padding:14px;height:100%}
.c-blk.is-on{display:block}.c-bh{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.c-q{margin:0 0 8px;font-size:15px;line-height:22px}.c-who{margin:0;font-size:12px;color:var(--hp-mute)}
.c-mid{display:flex;align-items:center;justify-content:center}
.c-verdict{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;padding:6px 10px;border-radius:999px;text-align:center}
.c-verdict.is-eq{background:var(--hp-si-bg);color:#0b6d3c}.c-verdict.is-ne{background:var(--hp-no-bg);color:#a8161c}.c-verdict.is-na{background:var(--hp-bg);color:var(--hp-mute)}
@media(max-width:760px){.c-grid{grid-template-columns:1fr}.c-mid{order:-1}.c-hero h1{font-size:34px;line-height:38px}}
"""
    js = """
var A=document.getElementById('pa'),Bq=document.getElementById('pb');
function upd(){var eq=0,tot=0;document.querySelectorAll('.c-row').forEach(function(r){
 var a=r.querySelector('.c-blk[data-side=a][data-p='+A.value+']'),b=r.querySelector('.c-blk[data-side=b][data-p='+Bq.value+']');
 r.querySelectorAll('.c-blk').forEach(function(x){x.classList.remove('is-on')});a.classList.add('is-on');b.classList.add('is-on');
 var x=a.dataset.ans,y=b.dataset.ans,v=r.querySelector('.c-verdict');var clear=function(s){return s==='a_favor'||s==='en_contra'};
 if(clear(x)&&clear(y)){tot++;if(x===y){eq++;v.textContent='Coinciden';v.className='c-verdict is-eq'}else{v.textContent='Discrepan';v.className='c-verdict is-ne'}}
 else{v.textContent=(x==='sin_badge')?'Ver citas':'Sin comparación clara';v.className='c-verdict is-na'}});
 document.querySelector('.c-score').textContent='Coinciden en '+eq+' de '+tot+' preguntas con respuesta clara de ambos';}
A.addEventListener('change',upd);Bq.addEventListener('change',upd);upd();
"""
    return page("04 · Cara a cara", css, body, js)


# ================================================================= 05 PORTADA (ibrido raccomandato)

def v5_portada(D):
    P, T, today = D["parties"], D["topics"], D["today"]
    live = "".join(
        f'<li style="--pc:{PARTY_COLOR[s["_party"]["key"]]}"><span class="p-t">{e(rel(s["date"], today))}</span>{pchip(s["_party"])}'
        f'<span class="hp-tag">{e(s["_topic"]["label_short"])}</span>{ans_pill(s["stance"])}<p>{headline(s, True)}</p><span class="p-who">{e(s["person"])} · {src(s)}</span></li>'
        for s in pick_latest(D["feed"]))
    chg = "".join(
        f'<article class="p-chg" style="--pc:{PARTY_COLOR[c["party"]["key"]]}"><p class="hp-tag">↻ {e(change_text(c))}</p>'
        f'<h3>{pchip(c["party"])} sobre {e(c["topic"]["title_label"])}</h3>'
        f'<div class="p-steps"><div><b>{B.d(c["before"]["date"]).year}</b>{ans_pill(c["before"]["stance"])}</div><span>→</span><div><b>{B.d(c["after"]["date"]).year}</b>{ans_pill(c["after"]["stance"])}</div></div>'
        f'<a href="#{c["topic"]["key"]}">Ver las pruebas</a></article>' for c in D["changes"][:4])
    head = "".join(f'<th><span style="--pc:{PARTY_COLOR[p["key"]]}">{e(p["label"])}</span></th>' for p in P)
    rows = []
    for gk, gl in D["groups"].items():
        rows.append(f'<tr class="p-g"><th colspan="{len(P) + 1}">{e(gl)}</th></tr>')
        for t in [x for x in T if x["group"] == gk]:
            rows.append(f'<tr><th class="p-q"><a href="#{t["key"]}">{e(t["question_short"])}</a></th>' +
                        "".join(f'<td>{ans_pill(D["badges"][(p["key"], t["key"])]["badge"])}</td>' for p in P) + "</tr>")
    topics = []
    for t in T:
        cards = []
        for p in P:
            b = D["badges"][(p["key"], t["key"])]
            s, items = best_item(D, p, t)
            cards.append(f'<div class="p-tc" style="--pc:{PARTY_COLOR[p["key"]]}"><div class="p-tch">{pchip(p)}{ans_pill(b["badge"])}</div>' +
                         (f'<p>{headline(s, True)}</p><span class="p-who">{e(s["person"])} · {src(s)}</span>' if s else '<p class="p-who"><i>Sin declaraciones desde agosto de 2023.</i></p>') +
                         f'<a class="p-more" href="{e(B.party_url(D["cfg"], p, t["key"]))}">{len(items)} declaraciones y votos →</a></div>')
        q = e(t["question_short"]) if t["proposition"] else e(t["label"])
        topics.append(f'<details class="p-topic" id="{t["key"]}"><summary><span>{q}</span><span class="p-sum">' +
                      "".join(f'<i class="p-dot p-dot--{ANS[D["badges"][(p["key"], t["key"])]["badge"]][1]}" title="{e(p["label"])}"></i>' for p in P) +
                      f'</span></summary><div class="p-tgrid">{"".join(cards)}</div></details>')
    cite = f"[NOMBRE TOOL] de papernest, «Qué dicen los partidos sobre la energía», actualizado el {B.fdate(today)}. papernest.es{D['cfg']['base_path']}"
    body = f"""
<header class="p-top"><div class="hp-wrap p-top__in"><b>[NOMBRE TOOL]</b><span class="p-live"><i></i>Actualizado hoy</span><span>Elecciones 29N · <b>Faltan {D['days_left']} días</b></span><span class="p-n">{D['n']} declaraciones y votos verificados</span></div></header>
<main class="hp-wrap">
<section class="p-intro"><h1>¿Qué dicen los partidos sobre la luz, el gas y la energía?</h1>
<p>Todas las declaraciones y votaciones de PSOE, PP, Vox, Sumar, Podemos y SALF desde 2023, con fecha y fuente. No opinamos: lo recopilamos y lo verificamos.</p></section>
<section class="p-row1">
<div class="p-live-box"><h2><span class="p-dotlive"></span>Lo último</h2><ol class="p-live-list">{live}</ol><a class="p-all" href="#directo">Ver todo el directo →</a></div>
<div class="p-chg-box"><h2>Han cambiado de posición</h2><div class="p-chgs">{chg}</div></div>
</section>
<section class="p-board"><h2>La foto: qué responde cada partido</h2><p class="p-sub">Según lo que ha dicho y votado su dirección nacional. Pulsa una pregunta para ver las pruebas.</p>
<div class="p-tw"><table class="p-table"><thead><tr><th></th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section class="p-topics"><h2>Tema a tema</h2>{''.join(topics)}</section>
<section class="p-cite"><div><h2>¿Eres periodista?</h2><p>Puedes citar esta página. Cada dato enlaza a su fuente original y lo actualizamos varias veces por semana hasta el 29N.</p>
<p class="p-citebox"><code>{e(cite)}</code><button class="hp-btn p-copy">Copiar cita</button></p></div>
<div><h2>Cómo lo hacemos</h2><p>Solo declaraciones de la dirección nacional y votaciones en el Congreso, desde agosto de 2023. Texto literal y fuente en cada dato. ¿Un error? Escríbenos a [EMAIL CORRECCIONES].</p></div></section>
<section id="directo" class="p-directo"><h2>El directo completo</h2><p class="p-sub">El prototipo 01 muestra cómo sería esta sección (timeline con filtros).</p></section>
</main>"""
    css = """
.p-top{background:#fff;border-bottom:1px solid var(--hp-line);position:sticky;top:0;z-index:10;font-size:13px}
.p-top__in{display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding-top:10px;padding-bottom:10px}.p-top__in>b{font-size:15px}
.p-live{display:inline-flex;gap:6px;align-items:center;color:var(--hp-p);font-weight:800}.p-live i,.p-dotlive{width:8px;height:8px;border-radius:50%;background:var(--hp-p);display:inline-block;animation:pp 1.4s infinite}
@keyframes pp{50%{opacity:.25}}.p-n{margin-left:auto;color:var(--hp-mute)}
.p-intro{padding:40px 0 24px;max-width:820px}.p-intro h1{font-size:44px;line-height:48px;margin:0 0 12px;letter-spacing:-.02em}.p-intro p{font-size:18px;color:var(--hp-ink2);margin:0}
.p-row1{display:grid;grid-template-columns:1.15fr 1fr;gap:24px;margin-bottom:48px}
.p-row1 h2,.p-board h2,.p-topics h2,.p-directo h2{font-size:22px;margin:0 0 12px;display:flex;align-items:center;gap:8px}
.p-live-box{border:1px solid var(--hp-line);border-radius:14px;padding:18px}
.p-live-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.p-live-list li{border-left:3px solid var(--pc);padding:8px 0 8px 12px;margin-bottom:8px;display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center}
.p-live-list p{flex-basis:100%;margin:0;font-weight:800;font-size:15px;line-height:21px}
.p-t{font-size:12px;font-weight:800;color:var(--hp-p);min-width:70px}.p-who{font-size:12px;color:var(--hp-mute)}
.p-all{font-weight:800;text-decoration:none}
.p-chg-box{background:var(--hp-p-soft);border-radius:14px;padding:18px}
.p-chgs{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.p-chg{background:#fff;border-radius:10px;padding:12px;border-top:3px solid var(--pc)}
.p-chg h3{margin:4px 0 8px;font-size:14px;line-height:19px}.p-chg a{font-size:13px;font-weight:800;text-decoration:none}
.p-steps{display:flex;align-items:center;gap:8px;margin-bottom:6px}.p-steps div{display:flex;flex-direction:column;gap:2px;align-items:flex-start}.p-steps b{font-size:12px;color:var(--hp-mute)}
.p-board{margin-bottom:48px}.p-sub{color:var(--hp-mute);margin:-6px 0 14px;font-size:14px}
.p-tw{overflow-x:auto;border:1px solid var(--hp-line);border-radius:14px}
.p-table{width:100%;min-width:760px;border-collapse:collapse;font-size:14px}
.p-table th,.p-table td{padding:10px 8px;border-top:1px solid var(--hp-line);text-align:center}
.p-table thead th{border-top:0;font-size:14px}.p-table thead span{border-bottom:3px solid var(--pc);padding-bottom:4px}
.p-q{text-align:left!important;font-weight:500;position:sticky;left:0;background:#fff;min-width:260px}.p-q a{color:var(--hp-ink);text-decoration:none}.p-q a:hover{color:var(--hp-p)}
.p-g th{text-align:left;background:var(--hp-bg);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--hp-p);padding:8px 12px}
.p-topics{margin-bottom:48px}
.p-topic{border:1px solid var(--hp-line);border-radius:12px;margin-bottom:10px;overflow:hidden}
.p-topic summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 18px;font-weight:800;font-size:17px}
.p-topic summary::-webkit-details-marker{display:none}.p-topic[open] summary{background:var(--hp-bg)}
.p-sum{display:flex;gap:4px}.p-dot{width:12px;height:12px;border-radius:50%;display:inline-block}
.p-dot--si{background:var(--hp-si)}.p-dot--no{background:var(--hp-no)}.p-dot--amb{background:var(--hp-amb)}.p-dot--nd{border:2px dashed #c4c5d3}.p-dot--cit{background:#d9dae6}
.p-tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;padding:16px}
.p-tc{border-left:3px solid var(--pc);padding:4px 0 4px 12px;display:flex;flex-direction:column;gap:6px}
.p-tch{display:flex;justify-content:space-between;align-items:center}.p-tc p{margin:0;font-size:14px;line-height:20px}
.p-more{font-size:13px;font-weight:800;text-decoration:none;margin-top:auto}
.p-cite{display:grid;grid-template-columns:1.3fr 1fr;gap:24px;background:var(--hp-ink);color:#fff;border-radius:16px;padding:28px;margin-bottom:48px}
.p-cite h2{margin:0 0 8px;font-size:20px}.p-cite p{color:#d2d2e0;font-size:14px}
.p-citebox{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.p-citebox code{background:#2a2b3d;padding:10px 12px;border-radius:8px;font-size:12px;color:#fff;flex:1;min-width:240px}
.p-directo{border-top:1px solid var(--hp-line);padding:32px 0 80px}
@media(max-width:900px){.p-row1,.p-cite{grid-template-columns:1fr}.p-chgs{grid-template-columns:1fr}.p-intro h1{font-size:32px;line-height:36px}.p-n{display:none}}
"""
    js = """
var b=document.querySelector('.p-copy');b.addEventListener('click',function(){var t=document.querySelector('.p-citebox code').textContent;
 if(navigator.clipboard){navigator.clipboard.writeText(t)}b.textContent='¡Copiada!';setTimeout(function(){b.textContent='Copiar cita'},1600)});
document.querySelectorAll('.p-q a').forEach(function(a){a.addEventListener('click',function(){var d=document.getElementById(a.getAttribute('href').slice(1));if(d)d.open=true})});
document.querySelectorAll('.p-chg a').forEach(function(a){a.addEventListener('click',function(){var d=document.getElementById(a.getAttribute('href').slice(1));if(d)d.open=true})});
"""
    return page("05 · Portada (híbrido)", css, body, js)


# ================================================================= 05 v2 PORTADA (feedback Diego 8 ott)
# + titolo che cambia e risposta immediata (da 02), filtro partiti "a urna" (da 02) che vale per tutta la pagina,
# + "La foto" con i dischi cliccabili del Marcador (da 03), + modulo Cara a cara (da 04) prima di "¿Eres periodista?"

def disc_cell(D, p, t, clickable=True):
    b = D["badges"][(p["key"], t["key"])]
    lab, mod = ANS[b["badge"]]
    mark = '<em title="Cambio de posición">↻</em>' if any(c["party"]["key"] == p["key"] and c["topic"]["key"] == t["key"] for c in D["changes"]) else ""
    tag = "button" if clickable else "span"
    attrs = f' data-c="c-{p["slug"]}-{t["key"]}" aria-label="{e(p["label"])}: {e(lab)}"' if clickable else ""
    return f'<{tag} class="q-cell q-cell--{mod}"{attrs}><span class="q-disc"></span><small>{e(lab)}</small>{mark}</{tag}>'


def v5b_portada(D):
    P, T, today = D["parties"], D["topics"], D["today"]
    # --- hero: titolo che cambia + risposta immediata per tema
    chips = "".join(f'<button class="q-topic" data-t="{t["key"]}">{e(t["label_short"])}</button>' for t in T)
    quick = []
    for t in T:
        ballots = "".join(
            f'<a class="q-ballot" data-p="{p["slug"]}" href="#c-{p["slug"]}-{t["key"]}" style="--pc:{PARTY_COLOR[p["key"]]}"><b>{e(p["label"])}</b>{disc_cell(D, p, t, False)}</a>'
            for p in P)
        q = e(t["question_short"]) if t["proposition"] else "No hay una pregunta de sí o no: mira lo que ha dicho cada partido."
        quick.append(f'<div class="q-quick hp-hide" data-t="{t["key"]}"><p class="q-qq">{q}</p><div class="q-ballots">{ballots}</div>'
                     f'<a class="q-go" href="#{t["key"]}">Ver las pruebas sobre {e(t["title_label"])} →</a></div>')
    # --- filtro "urna"
    urna = "".join(f'<button class="q-urn is-on" data-p="{p["slug"]}" style="--pc:{PARTY_COLOR[p["key"]]}" aria-pressed="true"><i></i>{e(p["label"])}</button>' for p in P)
    # --- lo último (12 renderizzati, JS ne mostra 5 visibili dopo il filtro)
    live = "".join(
        f'<li data-p="{s["_party"]["slug"]}" style="--pc:{PARTY_COLOR[s["_party"]["key"]]}"><span class="p-t">{e(rel(s["date"], today))}</span>{pchip(s["_party"])}'
        f'<span class="hp-tag">{e(s["_topic"]["label_short"])}</span>{ans_pill(s["stance"])}<p>{headline(s, True)}</p><span class="p-who">{e(s["person"])} · {src(s)}</span></li>'
        for s in pick_latest(D["feed"], n=12, max_votes=2, max_per_party=2))
    chg = "".join(
        f'<article class="p-chg" data-p="{c["party"]["slug"]}" style="--pc:{PARTY_COLOR[c["party"]["key"]]}"><p class="hp-tag">↻ {e(change_text(c))}</p>'
        f'<h3>{pchip(c["party"])} sobre {e(c["topic"]["title_label"])}</h3>'
        f'<div class="p-steps"><div><b>{B.d(c["before"]["date"]).year}</b>{ans_pill(c["before"]["stance"])}</div><span>→</span><div><b>{B.d(c["after"]["date"]).year}</b>{ans_pill(c["after"]["stance"])}</div></div>'
        f'<a href="#c-{c["party"]["slug"]}-{c["topic"]["key"]}" class="q-open">Ver las pruebas</a></article>' for c in D["changes"])
    # --- la foto con dischi
    head = "".join(f'<th data-p="{p["slug"]}"><span style="--pc:{PARTY_COLOR[p["key"]]}">{e(p["label"])}</span></th>' for p in P)
    rows, details = [], []
    for gk, gl in D["groups"].items():
        rows.append(f'<tr class="q-g"><th colspan="{len(P) + 2}">{e(gl)}</th></tr>')
        for t in [x for x in T if x["group"] == gk]:
            tally = {}
            for p in P:
                tally[D["badges"][(p["key"], t["key"])]["badge"]] = tally.get(D["badges"][(p["key"], t["key"])]["badge"], 0) + 1
                s, items = best_item(D, p, t)
                b = D["badges"][(p["key"], t["key"])]
                lis = "".join(f'<li><span class="t-d">{e(B.fdate(x["date"], True))}</span>{ans_pill(x["stance"])}<div><p class="t-hq">{headline(x)}</p>'
                              f'<p class="t-who">{e(x["person"])} · {e(x["role"])}{" · voz regional" if x["level"] == "regional" else ""} · {src(x)}</p></div></li>' for x in items) \
                    or '<li><p class="t-who">Sin declaraciones de la dirección nacional desde agosto de 2023.</p></li>'
                details.append(f'<div class="q-detail hp-hide" id="c-{p["slug"]}-{t["key"]}"><div class="q-detail__h">{pchip(p)}<b>{e(t["question_short"])}</b>{ans_pill(b["badge"], True)}'
                               f'<button class="q-close" aria-label="Cerrar">×</button></div><ol>{lis}</ol></div>')
            bar = (f'<div class="t-bar"><i style="flex:{tally.get("a_favor", 0)}" class="b-si"></i><i style="flex:{tally.get("en_contra", 0)}" class="b-no"></i>'
                   f'<i style="flex:{tally.get("ambiguo", 0)}" class="b-amb"></i><i style="flex:{tally.get("sin_declaraciones", 0)}" class="b-nd"></i></div>') if t["proposition"] else '<span class="p-who">sin pregunta sí/no</span>'
            rows.append(f'<tr><th class="q-q"><a href="#{t["key"]}">{e(t["question_short"])}</a></th>' +
                        "".join(f'<td data-p="{p["slug"]}">{disc_cell(D, p, t)}</td>' for p in P) + f'<td class="q-tally">{bar}</td></tr>')
    # --- tema a tema
    topics = []
    for t in T:
        cards = []
        for p in P:
            b = D["badges"][(p["key"], t["key"])]
            s, items = best_item(D, p, t)
            cards.append(f'<div class="p-tc" data-p="{p["slug"]}" style="--pc:{PARTY_COLOR[p["key"]]}"><div class="p-tch">{pchip(p)}{ans_pill(b["badge"])}</div>' +
                         (f'<p>{headline(s, True)}</p><span class="p-who">{e(s["person"])} · {src(s)}</span>' if s else '<p class="p-who"><i>Sin declaraciones desde agosto de 2023.</i></p>') +
                         f'<a class="p-more" href="{e(B.party_url(D["cfg"], p, t["key"]))}">{len(items)} declaraciones y votos →</a></div>')
        q = e(t["question_short"]) if t["proposition"] else e(t["label"])
        topics.append(f'<details class="p-topic" id="{t["key"]}"><summary><span>{q}</span><span class="p-sum">' +
                      "".join(f'<i class="p-dot p-dot--{ANS[D["badges"][(p["key"], t["key"])]["badge"]][1]}" data-p="{p["slug"]}" title="{e(p["label"])}"></i>' for p in P) +
                      f'</span></summary><div class="p-tgrid">{"".join(cards)}</div></details>')
    # --- cara a cara (modulo compatto)
    opts = lambda sel: "".join(f'<option value="{p["slug"]}"{" selected" if p["slug"] == sel else ""}>{e(p["label"])}</option>' for p in P)
    cc_rows = []
    for t in [x for x in T if x["proposition"]]:
        sides = {}
        for side in ("a", "b"):
            sides[side] = "".join(
                f'<div class="cc-blk" data-side="{side}" data-cp="{p["slug"]}" data-ans="{D["badges"][(p["key"], t["key"])]["badge"]}">'
                f'{disc_cell(D, p, t, False)}<p>{headline(best_item(D, p, t)[0], True) if best_item(D, p, t)[0] else "<i>Sin declaraciones</i>"}</p></div>'
                for p in P)
        cc_rows.append(f'<div class="cc-row"><div class="cc-side cc-a">{sides["a"]}</div><div class="cc-mid"><p>{e(t["question_short"])}</p><span class="cc-v"></span></div>'
                       f'<div class="cc-side cc-b">{sides["b"]}</div></div>')
    cite = f"[NOMBRE TOOL] de papernest, «Qué dicen los partidos sobre la energía», actualizado el {B.fdate(today)}. papernest.es{D['cfg']['base_path']}"
    body = f"""
<header class="p-top"><div class="hp-wrap p-top__in"><b>[NOMBRE TOOL]</b><span class="p-live"><i></i>Actualizado hoy</span><span>Elecciones 29N · <b>Faltan {D['days_left']} días</b></span><span class="p-n">{D['n']} declaraciones y votos verificados</span></div></header>
<section class="hp-wrap q-hero">
<h1>¿Qué dicen los partidos sobre <span class="q-slot">la energía</span>?</h1>
<p class="q-sub">Todas las declaraciones y votaciones de PSOE, PP, Vox, Sumar, Podemos y SALF desde 2023, con fecha y fuente. No opinamos: lo recopilamos y lo verificamos.</p>
<div class="q-topics"><span class="hp-tag">Elige un tema</span>{chips}</div>
{''.join(quick)}
</section>
<div class="q-urnbar"><div class="hp-wrap q-urnbar__in"><span>Partidos que comparas:</span>{urna}</div></div>
<main class="hp-wrap">
<section class="p-row1">
<div class="p-live-box"><h2><span class="p-dotlive"></span>Lo último</h2><ol class="p-live-list">{live}</ol><a class="p-all" href="#directo">Ver todo el directo →</a></div>
<div class="p-chg-box"><h2>Han cambiado de posición</h2><div class="p-chgs">{chg}</div></div>
</section>
<section class="q-board" id="foto"><h2>La foto: qué responde cada partido</h2><p class="p-sub">Según lo que ha dicho y votado su dirección nacional. Pulsa una casilla para ver las pruebas.</p>
<div class="q-tw"><table class="q-table"><thead><tr><th></th>{head}<th class="q-tally">Reparto</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="q-legend"><span class="q-cell q-cell--si"><span class="q-disc"></span></span>Sí <span class="q-cell q-cell--no"><span class="q-disc"></span></span>No <span class="q-cell q-cell--amb"><span class="q-disc"></span></span>Ambiguo <span class="q-cell q-cell--nd"><span class="q-disc"></span></span>Sin datos · ↻ cambio de posición</p>
<div class="q-details">{''.join(details)}</div></section>
<section class="p-topics"><h2>Tema a tema</h2>{''.join(topics)}</section>
<section class="cc" id="cara-a-cara"><div class="cc-head"><h2>Cara a cara</h2><p>Elige dos partidos y compara sus respuestas.</p>
<div class="cc-pick"><select id="cca" aria-label="Partido A">{opts('psoe')}</select><span class="cc-vs">VS</span><select id="ccb" aria-label="Partido B">{opts('pp')}</select></div>
<p class="cc-score" aria-live="polite"></p></div>{''.join(cc_rows)}</section>
<section class="p-cite"><div><h2>¿Eres periodista?</h2><p>Puedes citar esta página. Cada dato enlaza a su fuente original y lo actualizamos varias veces por semana hasta el 29N.</p>
<p class="p-citebox"><code>{e(cite)}</code><button class="hp-btn p-copy">Copiar cita</button></p></div>
<div><h2>Cómo lo hacemos</h2><p>Solo declaraciones de la dirección nacional y votaciones en el Congreso, desde agosto de 2023. Texto literal y fuente en cada dato. ¿Un error? Escríbenos a [EMAIL CORRECCIONES].</p></div></section>
<section id="directo" class="p-directo"><h2>El directo completo</h2><p class="p-sub">Aquí va la timeline completa con filtros del prototipo 01.</p></section>
</main>"""
    css = """
.p-top{background:#fff;border-bottom:1px solid var(--hp-line);font-size:13px}
.p-top__in{display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding-top:10px;padding-bottom:10px}.p-top__in>b{font-size:15px}
.p-live{display:inline-flex;gap:6px;align-items:center;color:var(--hp-p);font-weight:800}.p-live i,.p-dotlive{width:8px;height:8px;border-radius:50%;background:var(--hp-p);display:inline-block;animation:pp 1.4s infinite}
@keyframes pp{50%{opacity:.25}}.p-n{margin-left:auto;color:var(--hp-mute)}
/* hero da 02 */
.q-hero{padding-top:48px;padding-bottom:28px}
.q-hero h1{font-size:50px;line-height:56px;font-weight:800;margin:0 0 12px;max-width:940px;letter-spacing:-.02em;min-height:112px}
.q-slot{color:var(--hp-p);border-bottom:4px solid var(--hp-p);transition:opacity .25s}.q-slot.is-fade{opacity:0}
.q-sub{color:var(--hp-ink2);font-size:17px;margin:0 0 20px;max-width:820px}
.q-topics{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.q-topics .hp-tag{margin-right:4px}
.q-topic{font:inherit;font-weight:800;font-size:14px;border:1px solid var(--hp-ink);background:#fff;border-radius:6px;padding:6px 12px;cursor:pointer}
.q-topic.is-on{background:var(--hp-p);border-color:var(--hp-p);color:#fff}
.q-quick{margin-top:20px;background:var(--hp-bg);border-radius:14px;padding:18px 20px}
.q-qq{margin:0 0 12px;font-size:20px;font-weight:800}
.q-ballots{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}
.q-ballot{background:#fff;border:1px solid var(--hp-line);box-shadow:inset 0 -4px 0 var(--pc);border-radius:8px;padding:10px 6px 12px;display:flex;flex-direction:column;align-items:center;gap:6px;text-decoration:none;color:var(--hp-ink)}
.q-ballot:hover{border-color:var(--pc)}.q-ballot b{font-size:14px}
.q-go{display:inline-block;margin-top:12px;font-weight:800;text-decoration:none}
/* filtro urna da 02 */
.q-urnbar{background:var(--hp-bg);border-top:1px solid var(--hp-line);border-bottom:1px solid var(--hp-line);position:sticky;top:0;z-index:10}
.q-urnbar__in{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding-top:10px;padding-bottom:10px;font-size:14px;color:var(--hp-mute)}
.q-urn{font:inherit;font-weight:800;font-size:14px;cursor:pointer;background:#fff;color:var(--hp-ink);border:1px solid var(--pc);box-shadow:inset 0 -3px 0 var(--pc);border-radius:999px;padding:6px 14px 7px;display:inline-flex;gap:6px;align-items:center}
.q-urn i{width:14px;height:14px;border-radius:3px;border:2px solid var(--pc);display:inline-block;position:relative}
.q-urn.is-on i:after{content:"";position:absolute;left:3px;top:0;width:4px;height:8px;border:solid var(--pc);border-width:0 2px 2px 0;transform:rotate(45deg)}
.q-urn:not(.is-on){opacity:.45;box-shadow:none}
/* row1 */
.p-row1{display:grid;grid-template-columns:1.15fr 1fr;gap:24px;margin:32px 0 48px}
.p-row1 h2,.q-board h2,.p-topics h2,.p-directo h2,.cc h2{font-size:24px;margin:0 0 12px;display:flex;align-items:center;gap:8px}
.p-live-box{border:1px solid var(--hp-line);border-radius:14px;padding:18px}
.p-live-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.p-live-list li{border-left:3px solid var(--pc);padding:8px 0 8px 12px;margin-bottom:8px;display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center}
.p-live-list li.is-over{display:none}
.p-live-list p{flex-basis:100%;margin:0;font-weight:800;font-size:15px;line-height:21px}
.p-t{font-size:12px;font-weight:800;color:var(--hp-p);min-width:70px}.p-who{font-size:12px;color:var(--hp-mute)}
.p-all{font-weight:800;text-decoration:none}
.p-chg-box{background:var(--hp-p-soft);border-radius:14px;padding:18px}
.p-chgs{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-height:520px;overflow:auto}
.p-chg{background:#fff;border-radius:10px;padding:12px;border-top:3px solid var(--pc)}
.p-chg h3{margin:4px 0 8px;font-size:14px;line-height:19px}.p-chg a{font-size:13px;font-weight:800;text-decoration:none}
.p-steps{display:flex;align-items:center;gap:8px;margin-bottom:6px}.p-steps div{display:flex;flex-direction:column;gap:2px;align-items:flex-start}.p-steps b{font-size:12px;color:var(--hp-mute)}
/* la foto con dischi (da 03, versione chiara) */
.q-board{margin-bottom:48px;scroll-margin-top:70px}.p-sub{color:var(--hp-mute);margin:-6px 0 14px;font-size:14px}
.q-tw{border:1px solid var(--hp-line);border-radius:14px;overflow:hidden}
.q-table{width:100%;border-collapse:collapse}
.q-table thead th{padding:14px 4px;font-size:14px;background:#fff}.q-table thead span{display:inline-block;padding-bottom:5px;border-bottom:3px solid var(--pc)}
.q-table td,.q-table th{text-align:center;border-top:1px solid var(--hp-line)}
.q-q{text-align:left!important;padding:10px 16px;font-weight:500;font-size:15px;width:34%}.q-q a{color:var(--hp-ink);text-decoration:none}.q-q a:hover{color:var(--hp-p)}
.q-g th{text-align:left;background:var(--hp-bg);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--hp-p);padding:8px 16px}
.q-cell{background:none;border:0;display:inline-flex;flex-direction:column;align-items:center;gap:3px;padding:6px 8px;font:inherit;position:relative;border-radius:10px;color:var(--hp-ink)}
button.q-cell{cursor:pointer}button.q-cell:hover,button.q-cell.is-on{background:var(--hp-p-soft)}
.q-cell small{font-size:11px;color:var(--hp-mute);font-weight:500}
.q-cell em{position:absolute;top:1px;right:3px;font-style:normal;color:var(--hp-p);font-weight:800;font-size:13px}
.q-disc{width:26px;height:26px;border-radius:50%;display:block;box-shadow:inset 0 -3px 0 rgba(0,0,0,.18)}
.q-cell--si .q-disc{background:#1fbf6b}.q-cell--no .q-disc{background:#f0454b}.q-cell--amb .q-disc{background:#f2b01e}
.q-cell--nd .q-disc{border:2px dashed #c4c5d3;box-shadow:none}.q-cell--cit .q-disc{background:#dcdcea;width:14px;height:14px;margin:6px;box-shadow:none}
.q-tally{width:130px;padding:0 14px}.t-bar{display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--hp-line)}
.b-si{background:#1fbf6b}.b-no{background:#f0454b}.b-amb{background:#f2b01e}.b-nd{background:#e4e4ec}
.q-legend{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;font-size:13px;color:var(--hp-mute);margin:12px 0 0}
.q-legend .q-cell{padding:0}.q-legend .q-disc{width:14px;height:14px}
.q-details{margin-top:16px}
.q-detail{border:1px solid var(--hp-line);border-radius:14px;padding:20px;box-shadow:0 10px 30px rgba(20,20,60,.08);scroll-margin-top:70px}
.q-detail__h{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:18px;margin-bottom:12px}
.q-close{margin-left:auto;font:inherit;font-size:22px;line-height:1;border:0;background:none;cursor:pointer;color:var(--hp-mute)}
.q-detail ol{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
.q-detail li{display:grid;grid-template-columns:90px 80px 1fr;gap:12px;align-items:start;border-top:1px solid var(--hp-line);padding-top:12px}
.t-d{font-weight:800;font-size:13px;color:var(--hp-mute)}.t-hq{margin:0 0 4px;font-weight:800}.t-who{margin:0;font-size:13px;color:var(--hp-mute)}
/* tema a tema */
.p-topics{margin-bottom:48px}
.p-topic{border:1px solid var(--hp-line);border-radius:12px;margin-bottom:10px;overflow:hidden;scroll-margin-top:70px}
.p-topic summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 18px;font-weight:800;font-size:17px}
.p-topic summary::-webkit-details-marker{display:none}.p-topic[open] summary{background:var(--hp-bg)}
.p-sum{display:flex;gap:4px}.p-dot{width:12px;height:12px;border-radius:50%;display:inline-block}
.p-dot--si{background:#1fbf6b}.p-dot--no{background:#f0454b}.p-dot--amb{background:#f2b01e}.p-dot--nd{border:2px dashed #c4c5d3}.p-dot--cit{background:#dcdcea}
.p-tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;padding:16px}
.p-tc{border-left:3px solid var(--pc);padding:4px 0 4px 12px;display:flex;flex-direction:column;gap:6px}
.p-tch{display:flex;justify-content:space-between;align-items:center}.p-tc p{margin:0;font-size:14px;line-height:20px}
.p-more{font-size:13px;font-weight:800;text-decoration:none;margin-top:auto}
/* cara a cara (da 04) */
.cc{margin-bottom:48px;border-radius:16px;overflow:hidden;border:1px solid var(--hp-line)}
.cc-head{background:linear-gradient(135deg,#5a52ff,#2b2580);color:#fff;text-align:center;padding:28px 16px 22px}
.cc-head h2{justify-content:center;color:#fff;margin-bottom:4px}.cc-head p{margin:0 0 14px;opacity:.9}
.cc-pick{display:flex;justify-content:center;align-items:center;gap:12px;flex-wrap:wrap}
.cc-pick select{font:inherit;font-weight:800;font-size:16px;padding:10px 14px;border-radius:10px;border:0;min-width:180px}
.cc-vs{font-weight:800;background:#fff;color:var(--hp-p);width:44px;height:44px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center}
.cc-score{margin:14px 0 0!important;font-weight:800;font-size:17px;opacity:1!important}
.cc-row{display:grid;grid-template-columns:1fr 220px 1fr;gap:12px;align-items:center;padding:14px 18px;border-top:1px solid var(--hp-line)}
.cc-row:nth-child(even){background:var(--hp-bg)}
.cc-blk{display:none;align-items:center;gap:12px}.cc-blk.is-on{display:flex}.cc-b .cc-blk{flex-direction:row-reverse;text-align:right}
.cc-blk p{margin:0;font-size:13px;line-height:19px;color:var(--hp-ink2)}
.cc-mid{text-align:center}.cc-mid p{margin:0 0 6px;font-weight:800;font-size:14px;line-height:19px}
.cc-v{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;padding:4px 10px;border-radius:999px;display:inline-block}
.cc-v.is-eq{background:var(--hp-si-bg);color:#0b6d3c}.cc-v.is-ne{background:var(--hp-no-bg);color:#a8161c}.cc-v.is-na{background:#fff;color:var(--hp-mute);border:1px solid var(--hp-line)}
/* cita */
.p-cite{display:grid;grid-template-columns:1.3fr 1fr;gap:24px;background:var(--hp-ink);color:#fff;border-radius:16px;padding:28px;margin-bottom:48px}
.p-cite h2{margin:0 0 8px;font-size:20px}.p-cite p{color:#d2d2e0;font-size:14px}
.p-citebox{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.p-citebox code{background:#2a2b3d;padding:10px 12px;border-radius:8px;font-size:12px;color:#fff;flex:1;min-width:240px}
.p-directo{border-top:1px solid var(--hp-line);padding:32px 0 80px}
@media(max-width:900px){.p-row1,.p-cite{grid-template-columns:1fr}.p-chgs{grid-template-columns:1fr}.p-n{display:none}
.q-hero h1{font-size:32px;line-height:38px;min-height:0}.q-ballots{grid-template-columns:repeat(3,1fr)}
.q-table thead tr,.q-table tbody tr{display:flex;flex-wrap:wrap}.q-table thead th{flex:1}.q-table thead th:first-child,.q-table .q-tally{display:none}
.q-table td{flex:1;border-top:0;padding-bottom:8px}.q-q{flex-basis:100%;width:auto;border-top:1px solid var(--hp-line)!important;padding:12px 12px 2px!important}
.q-g th{flex-basis:100%}.q-disc{width:22px;height:22px}.q-cell small{font-size:10px}.q-cell{padding:4px 2px}
.q-detail li{grid-template-columns:1fr}
.cc-row{grid-template-columns:1fr 1fr}.cc-mid{grid-column:1/-1;order:-1}.cc-b .cc-blk{flex-direction:column;text-align:left;align-items:flex-start}.cc-a .cc-blk{flex-direction:column;align-items:flex-start}}
"""
    js = """
var labels=%s, keys=Object.keys(labels), slot=document.querySelector('.q-slot'), picked=false, i=0;
function setSlot(txt){slot.classList.add('is-fade');setTimeout(function(){slot.textContent=txt;slot.classList.remove('is-fade')},250)}
function showTopic(k){setSlot(labels[k]);document.querySelectorAll('.q-topic').forEach(function(x){x.classList.toggle('is-on',x.dataset.t===k)});
 document.querySelectorAll('.q-quick').forEach(function(q){q.classList.toggle('hp-hide',q.dataset.t!==k)})}
/* finché l'utente non sceglie, titolo e risposte ruotano insieme (si ferma al passaggio del mouse) */
var hero=document.querySelector('.q-hero'),hover=false;hero.addEventListener('mouseenter',function(){hover=true});hero.addEventListener('mouseleave',function(){hover=false});
showTopic(keys[0]);i=1;
var rot=setInterval(function(){if(picked||hover)return;showTopic(keys[i%%keys.length]);i++},4500);
document.querySelectorAll('.q-topic').forEach(function(b){b.addEventListener('click',function(){picked=true;clearInterval(rot);showTopic(b.dataset.t)})});
/* filtro urna: vale per tutti gli elementi con data-p */
function applyUrn(){var on={};document.querySelectorAll('.q-urn').forEach(function(u){on[u.dataset.p]=u.classList.contains('is-on')});
 document.querySelectorAll('[data-p]').forEach(function(el){if(el.classList.contains('q-urn'))return;el.classList.toggle('hp-hide',on[el.dataset.p]===false)});
 var n=0;document.querySelectorAll('.p-live-list li').forEach(function(li){var vis=!li.classList.contains('hp-hide');li.classList.toggle('is-over',vis&&n>=5);if(vis)n++})}
document.querySelectorAll('.q-urn').forEach(function(u){u.addEventListener('click',function(){u.classList.toggle('is-on');u.setAttribute('aria-pressed',u.classList.contains('is-on'));applyUrn()})});
applyUrn();
/* dischi -> pannello prove */
function openDetail(id){document.querySelectorAll('.q-detail').forEach(function(d){d.classList.add('hp-hide')});document.querySelectorAll('button.q-cell').forEach(function(x){x.classList.toggle('is-on',x.dataset.c===id)});
 var d=document.getElementById(id);if(d){d.classList.remove('hp-hide');d.scrollIntoView({behavior:'smooth',block:'nearest'})}}
document.querySelectorAll('button.q-cell').forEach(function(b){b.addEventListener('click',function(){openDetail(b.dataset.c)})});
document.querySelectorAll('.q-ballot,.q-open').forEach(function(a){a.addEventListener('click',function(ev){ev.preventDefault();openDetail(a.getAttribute('href').slice(1))})});
document.querySelectorAll('.q-close').forEach(function(b){b.addEventListener('click',function(){b.closest('.q-detail').classList.add('hp-hide');document.querySelectorAll('button.q-cell').forEach(function(x){x.classList.remove('is-on')})})});
document.querySelectorAll('.q-q a,.q-go').forEach(function(a){a.addEventListener('click',function(){var d=document.getElementById(a.getAttribute('href').slice(1));if(d)d.open=true})});
/* cara a cara */
var A=document.getElementById('cca'),Bs=document.getElementById('ccb');
function cc(){var eq=0,tot=0;document.querySelectorAll('.cc-row').forEach(function(r){
 r.querySelectorAll('.cc-blk').forEach(function(x){x.classList.remove('is-on')});
 var a=r.querySelector('.cc-blk[data-side=a][data-cp='+A.value+']'),b=r.querySelector('.cc-blk[data-side=b][data-cp='+Bs.value+']');a.classList.add('is-on');b.classList.add('is-on');
 var x=a.dataset.ans,y=b.dataset.ans,v=r.querySelector('.cc-v'),clear=function(s){return s==='a_favor'||s==='en_contra'};
 if(clear(x)&&clear(y)){tot++;if(x===y){eq++;v.textContent='Coinciden';v.className='cc-v is-eq'}else{v.textContent='Discrepan';v.className='cc-v is-ne'}}else{v.textContent='Sin comparación clara';v.className='cc-v is-na'}});
 document.querySelector('.cc-score').textContent='Coinciden en '+eq+' de '+tot+' preguntas con respuesta clara de ambos'}
A.addEventListener('change',cc);Bs.addEventListener('change',cc);cc();
var cp=document.querySelector('.p-copy');cp.addEventListener('click',function(){var t=document.querySelector('.p-citebox code').textContent;if(navigator.clipboard){navigator.clipboard.writeText(t)}cp.textContent='¡Copiada!';setTimeout(function(){cp.textContent='Copiar cita'},1600)});
""" % json.dumps({t["key"]: t["title_label"] for t in T}, ensure_ascii=False)
    return page("05 v2 · Portada", css, body, js)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    D = load()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("01-directo", v1_directo), ("02-rellena-el-hueco", v2_hueco), ("03-marcador", v3_tablero),
                     ("04-cara-a-cara", v4_caraacara), ("05-portada", v5_portada), ("05-portada-v2", v5b_portada)):
        (OUT / f"{name}.html").write_text(fn(D), encoding="utf-8")
        print("scritto", name)


if __name__ == "__main__":
    main()

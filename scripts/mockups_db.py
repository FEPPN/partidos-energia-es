"""Mockup "database senza cifre" (grill 3 nov 2026): 5 idee di pagina generate dai dati veri.

Applica le decisioni del grill sui dati SENZA toccare data/:
- 5 partiti: Frente Amplio (storico Sumar) al posto di Sumar, SALF fuori
- 10 temi: TUR gas -> Precio luz y gas, Autoconsumo -> Renovables; Centros de datos e Coche eléctrico solo timeline
- badge = "Última posición registrada" (regole di build.compute_badge)

Output: output/mockups_db/index.html + 01..05 (anteprime da browser, NON pronte per WordPress).
"""
import json
import sys
from collections import Counter
from datetime import date

import build as B

e = B.e
OUT = B.OUT / "mockups_db"

MERGE = {"tur_gas": "precio_luz_gas", "autoconsumo": "renovables"}
TIMELINE_ONLY = {"data_center", "coche_electrico"}
DROP_PARTIES = {"SALF"}
RENAME = {"SUMAR": ("Frente Amplio", "Hasta oct. 2026 como Sumar")}
PARTY_COLOR = {"PSOE": "#e30613", "PP": "#1d84ce", "VOX": "#5ac035", "SUMAR": "#e5007d", "PODEMOS": "#6b2d83"}
STANCE = {"a_favor": ("A favor", "fav"), "en_contra": ("En contra", "con"), "ambiguo": ("Ambiguo", "amb"),
          "na": ("Sin posición", "na")}


def load():
    cfg = B.load_json(B.DATA / "config.json")
    parties = [p for p in B.load_json(B.DATA / "parties.json")["parties"] if p["key"] not in DROP_PARTIES]
    for p in parties:
        p["note"] = None  # la note di parties.json è interna, non va in pagina
        if p["key"] in RENAME:
            p["label"], p["note"] = RENAME[p["key"]]
    topics = []
    for t in B.load_json(B.DATA / "topics.json")["topics"]:
        if t["key"] in MERGE:
            continue
        if t["key"] in TIMELINE_ONLY:
            t = {**t, "proposition": None}
        topics.append(t)
    tlabel = {t["key"]: t["label_short"] for t in B.load_json(B.DATA / "topics.json")["topics"]}
    stmts = []
    for p in parties:
        for s in B.load_json(B.DATA / "statements" / f"{p['slug']}.json")["statements"]:
            s = dict(s, party=p["key"])
            if s["topic"] in MERGE:
                s["subtopic"] = tlabel[s["topic"]]
                s["topic"] = MERGE[s["topic"]]
            stmts.append(s)
    badges = {}
    for p in parties:
        for t in topics:
            items = [s for s in stmts if s["party"] == p["key"] and s["topic"] == t["key"]]
            b = B.compute_badge(items, t, p["key"], cfg)
            valid = sorted([s for s in items if s["level"] == "nacional"], key=lambda s: s["date"])
            b["last_date"] = valid[-1]["date"] if valid else None
            b["n"] = len(items)
            badges[(p["key"], t["key"])] = b
    return cfg, parties, topics, stmts, badges


def js_data(parties, topics, stmts):
    keep = ("id", "party", "topic", "subtopic", "type", "date", "person", "role", "level", "quote", "context",
            "stance", "source_name", "source_url")
    return json.dumps({
        "parties": [{"key": p["key"], "label": p["label"], "note": p.get("note"), "color": PARTY_COLOR[p["key"]]} for p in parties],
        "topics": [{"key": t["key"], "label": t["label_short"], "prop": t["proposition"]} for t in topics],
        "stmts": [{k: s.get(k) for k in keep} for s in sorted(stmts, key=lambda s: s["date"], reverse=True)],
    }, ensure_ascii=False)


CSS = """
:root{--p:#5a52ff;--p50:#f6f5ff;--p100:#f1f0ff;--p200:#ceccff;--p700:#3e38b2;--t100:#e0f8f6;--t500:#02c5ae;--t800:#016559;
--navy:#212430;--txt2:#383c4c;--muted:#63697f;--subtle:#81859a;--s50:#fafaf9;--s100:#f5f5f4;--s200:#e7e5e4;--s300:#d6d3d1;--s500:#79716b}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--navy);font-family:Avenir,"Avenir Next","Segoe UI",system-ui,sans-serif;line-height:1.5}
.wrap{max-width:1120px;margin:0 auto;padding:32px 16px 80px}
.mock{font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--p);margin:0 0 6px}
h1{font-size:32px;line-height:40px;font-weight:800;margin:0 0 8px}
h2{font-size:22px;line-height:30px;font-weight:800;margin:32px 0 8px}
.lead{font-size:17px;color:var(--txt2);margin:0 0 20px;max-width:760px}
.meta{font-size:13px;color:var(--muted)}
.why{background:var(--p50);border-left:4px solid var(--p);border-radius:0 8px 8px 0;padding:12px 16px;margin:0 0 28px;font-size:14px;color:var(--txt2)}
.why b{color:var(--navy)}
.stats{display:flex;flex-wrap:wrap;gap:12px;margin:0 0 24px}
.stat{background:var(--s50);border:1px solid var(--s200);border-radius:8px;padding:10px 14px;min-width:120px}
.stat b{display:block;font-size:24px;line-height:30px;font-family:Exo,inherit}
.stat span{font-size:12px;color:var(--muted)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}
.chip{font:inherit;font-size:14px;font-weight:500;padding:6px 14px;border-radius:9999px;border:1px solid var(--p200);background:#fff;color:var(--navy);cursor:pointer}
.chip[aria-pressed=true]{background:var(--p);border-color:var(--p);color:#fff}
.bdg{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:800;padding:3px 9px;border-radius:6px;white-space:nowrap}
.bdg.fav{background:var(--t100);color:var(--t800)}
.bdg.con{background:var(--p100);color:var(--p700)}
.bdg.amb{background:var(--s100);color:var(--txt2);background-image:repeating-linear-gradient(135deg,transparent 0 6px,rgba(121,113,107,.14) 6px 8px)}
.bdg.na,.bdg.sin{background:#fff;color:var(--subtle);border:1px dashed var(--s300);font-weight:500}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;flex:none}
.dot.fav{background:var(--t500)}.dot.con{background:var(--p)}.dot.amb{background:var(--s500)}.dot.na{background:#fff;border:1.5px solid var(--s300)}
.pty{display:inline-flex;align-items:center;gap:6px;font-weight:800}
.pty i{width:10px;height:10px;border-radius:3px;display:inline-block}
.card{background:#fff;border:1px solid var(--s200);border-radius:8px;border-top-left-radius:18px;border-bottom-right-radius:18px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.q{margin:6px 0;font-size:15px;line-height:22px}
.q.ctx{color:var(--txt2);font-style:italic}
a{color:var(--p)}
.src{font-size:13px;font-weight:500;text-decoration:none}
.src:hover{text-decoration:underline}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;color:var(--muted);margin:8px 0 24px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.back{font-size:14px;font-weight:800;text-decoration:none;display:inline-block;margin:0 0 20px}
.sub{font-size:12px;color:var(--subtle);font-weight:500}
"""

COMMON_JS = r"""
const M=["ene","feb","mar","abr","may","jun","jul","ago","sept","oct","nov","dic"];
const ST={a_favor:["A favor","fav"],en_contra:["En contra","con"],ambiguo:["Ambiguo","amb"],na:["Sin posición","na"]};
const TY={declaracion:"Declaración",voto:"Votación",programa:"Programa",reportada:"Reportada"};
const fd=s=>{const[y,m,d]=s.split("-");return `${+d} ${M[m-1]} ${y}`};
const esc=s=>(s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const P=Object.fromEntries(D.parties.map(p=>[p.key,p]));
const T=Object.fromEntries(D.topics.map(t=>[t.key,t]));
const pty=k=>`<span class="pty"><i style="background:${P[k].color}"></i>${esc(P[k].label)}</span>`;
const bdg=st=>`<span class="bdg ${ST[st][1]}">${ST[st][0]}</span>`;
const text=s=>s.quote?`<p class="q">«${esc(s.quote)}»</p>`:`<p class="q ctx">${esc(s.context)}</p>`;
const item=s=>`<div class="card"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap">${pty(s.party)} ${bdg(s.stance)}</div>
${text(s)}<div class="meta">${esc(s.person)} · ${TY[s.type]} · ${fd(s.date)}${s.subtopic?" · "+esc(s.subtopic):""} · <a class="src" href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.source_name)}</a></div></div>`;
"""


def page(n, title, why, body, data, js, extra_css=""):
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} — mockup {n}</title><style>{CSS}{extra_css}</style></head><body><div class="wrap">
<a class="back" href="index.html">← Los 5 mockups</a>
<p class="mock">Mockup {n} de 5 · datos reales al 8 oct 2026</p>
{body.replace("{{WHY}}", f'<div class="why">{why}</div>')}
</div><script>const D={data};{COMMON_JS}
setTimeout(function(){{try{{{js}}}catch(err){{console.error(err)}}}},50);</script></body></html>"""


def sb(st):
    lab, mod = STANCE[st]
    return f'<span class="bdg {mod}">{lab}</span>'


def header(h1, lead):
    return f'<h1>{e(h1)}</h1><p class="lead">{lead}</p>{{{{WHY}}}}'


def counts(stmts, badges):
    c = Counter(s["type"] for s in stmts)
    evo = sum(1 for b in badges.values() if b["evolution"])
    chg = sum(1 for b in badges.values() if b["change"] or b["historic_change"])
    dv = sum(1 for b in badges.values() if b["dice_vota"])
    return c, evo, chg, dv


def stats_html(items):
    return '<div class="stats">' + "".join(f'<div class="stat"><b>{v}</b><span>{e(k)}</span></div>' for k, v in items) + "</div>"


# ---------------------------------------------------------------- 01 tablero

def m1(cfg, parties, topics, stmts, badges, data):
    c, evo, chg, dv = counts(stmts, badges)
    head = "".join(f'<th scope="col">{e(p["label"])}' + (f'<br><span class="sub" style="color:#ceccff">{e(p["note"])}</span>' if p.get("note") else "") + "</th>" for p in parties)
    rows = ""
    for t in topics:
        cells = ""
        for p in parties:
            b = badges[(p["key"], t["key"])]
            if b["badge"] == "sin_badge":
                inner = f'<span class="bdg sin">{b["n"]} citas</span>'
            elif b["badge"] == "sin_declaraciones":
                inner = '<span class="bdg sin">Sin datos</span>'
            else:
                lab, mod = STANCE[b["badge"]]
                mark = ""
                if b["change"] or b["historic_change"]:
                    mark = ' <span title="Cambió de posición">↻</span>'
                elif b["evolution"]:
                    mark = ' <span title="Su posición ha evolucionado">↗</span>'
                if b["dice_vota"]:
                    mark += ' <span title="Lo que dice no coincide con lo que vota">⇄</span>'
                inner = f'<span class="bdg {mod}">{lab}{mark}</span><span class="cd">{B.fdate(b["last_date"], short=True)}</span>'
            cells += f'<td><button class="cell" data-p="{p["key"]}" data-t="{t["key"]}">{inner}</button></td>'
        prop = f'<span class="sub">{e(t["proposition"])}</span>' if t["proposition"] else '<span class="sub">Solo declaraciones, sin posición</span>'
        rows += f'<tr><th scope="row">{e(t["label_short"])}<br>{prop}</th>{cells}</tr>'
    body = header("Qué dicen los partidos sobre la energía",
                  "Todas las declaraciones, votaciones y programas de los 5 grandes partidos sobre luz, gas y modelo energético, con su fuente. Pulsa una casilla para ver las pruebas.")
    body += stats_html([("declaraciones", c["declaracion"] + c["reportada"]), ("votaciones en el Congreso", c["voto"]),
                        ("puntos de programa", c["programa"]), ("partidos", len(parties)), ("temas", len(topics))])
    body += f"""<div class="legend"><span><span class="bdg fav">A favor</span></span><span><span class="bdg con">En contra</span></span>
<span><span class="bdg amb">Ambiguo</span></span><span>↻ cambió de posición</span><span>↗ su posición ha evolucionado</span><span>⇄ dice una cosa y vota otra</span>
<span>Fecha = última prueba registrada</span></div>
<div class="tw"><table class="tb"><thead><tr><th scope="col">Tema · ¿está a favor de…?</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>
<div id="drawer" hidden></div>"""
    css = """.tw{overflow-x:auto;border:1px solid var(--s200);border-radius:8px}.tb{border-collapse:collapse;width:100%;min-width:760px;font-size:14px}
.tb th,.tb td{padding:8px;border-bottom:1px solid var(--s200);text-align:center;vertical-align:middle}.tb thead th{background:var(--navy);color:#fff;font-weight:800}
.tb th[scope=row]{text-align:left;font-weight:800;min-width:220px;position:sticky;left:0;background:#fff}.tb tbody tr:nth-child(even) td{background:var(--p50)}
.cell{all:unset;cursor:pointer;display:inline-flex;flex-direction:column;align-items:center;gap:2px;padding:4px;border-radius:6px}.cell:hover,.cell.on{outline:2px solid var(--p)}
.cd{font-size:11px;color:var(--subtle)}#drawer{margin-top:20px;padding:20px;background:var(--s50);border-radius:12px}#drawer .list{display:grid;gap:12px}"""
    js = """const dr=document.getElementById("drawer");
document.querySelectorAll(".cell").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll(".cell.on").forEach(x=>x.classList.remove("on"));b.classList.add("on");
const L=D.stmts.filter(s=>s.party===b.dataset.p&&s.topic===b.dataset.t);
dr.hidden=false;dr.innerHTML=`<h2 style="margin-top:0">${esc(P[b.dataset.p].label)} · ${esc(T[b.dataset.t].label)}</h2><p class="meta">${L.length} pruebas, de la más reciente a la más antigua</p><div class="list">${L.map(item).join("")||"<p class='meta'>Sin declaraciones encontradas.</p>"}</div>`;
dr.scrollIntoView({behavior:"smooth",block:"start"})}));"""
    why = ("<b>Idea:</b> è la v1 ripulita, cioè una matrice 5 partiti × 10 temi con l'ultima posizione registrata e la data. "
           "Cliccando una casella si apre il cassetto con tutte le prove. <b>Per chi:</b> il lettore che vuole il quadro in 10 secondi. "
           "<b>Rischio:</b> la tabella sembra un giudizio, quindi le date e le prove a portata di click sono la nostra difesa.")
    return page(1, "Tablero", why, body, data, js, css)


# ---------------------------------------------------------------- 02 giros

def m2(cfg, parties, topics, stmts, badges, data):
    c, evo, chg, dv = counts(stmts, badges)
    tl = {t["key"]: t for t in topics}
    cards = []
    for (pk, tk), b in badges.items():
        for kind, lab in (("change", "Cambió de posición"), ("historic_change", "Antes de esta legislatura decía otra cosa"),
                          ("evolution", "Su posición ha evolucionado")):
            x = b.get(kind)
            if not x:
                continue
            bf, af = x["before"], x["after"]
            q = lambda s: f'«{e(s["quote"])}»' if s.get("quote") else f'<i>{e(s["context"])}</i>'
            cards.append((af["date"], pk, f"""<article class="card giro" data-p="{pk}" data-k="{kind}">
<div class="gh">{''}<span class="pty"><i style="background:{PARTY_COLOR[pk]}"></i>{e(next(p['label'] for p in parties if p['key']==pk))}</span>
<span class="sub">{e(tl[tk]['label_short'])}</span><span class="tag {kind}">{lab}</span></div>
<div class="ba"><div><span class="when">Antes · {B.fdate(bf['date'], short=True)}</span>{sb(bf['stance'])}
<p class="q">{q(bf)}</p><p class="meta">{e(bf['person'])} · <a class="src" href="{e(bf['source_url'])}" target="_blank" rel="noopener">{e(bf['source_name'])}</a></p></div>
<div class="arr">→</div>
<div><span class="when">Después · {B.fdate(af['date'], short=True)}</span>{sb(af['stance'])}
<p class="q">{q(af)}</p><p class="meta">{e(af['person'])} · <a class="src" href="{e(af['source_url'])}" target="_blank" rel="noopener">{e(af['source_name'])}</a></p></div></div></article>"""))
    cards.sort(key=lambda x: x[0], reverse=True)
    chips = '<button class="chip" aria-pressed="true" data-p="">Todos</button>' + "".join(
        f'<button class="chip" aria-pressed="false" data-p="{p["key"]}">{e(p["label"])}</button>' for p in parties)
    body = header("Cuando los partidos cambian de idea sobre la energía",
                  "Cada tarjeta compara lo que un partido decía antes con lo que dice ahora, con las dos fuentes. Lo actualizamos cada 2-3 días durante la campaña.")
    body += stats_html([("cambios de posición netos", chg), ("evoluciones de matiz", evo), ("dice ≠ vota", dv),
                        ("pruebas analizadas", len(stmts))])
    body += f'<div class="chips">{chips}</div><div class="feed">{"".join(x[2] for x in cards)}</div>'
    css = """.feed{display:grid;gap:16px}.gh{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:12px}
.tag{font-size:12px;font-weight:800;padding:3px 9px;border-radius:9999px;background:var(--s100);color:var(--txt2)}.tag.change,.tag.historic_change{background:#fff4e5;color:#9a5b00}
.ba{display:grid;grid-template-columns:1fr 32px 1fr;gap:12px;align-items:start}.arr{font-size:22px;color:var(--p);text-align:center;padding-top:24px}
.when{display:block;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-bottom:4px}
@media(max-width:640px){.ba{grid-template-columns:1fr}.arr{transform:rotate(90deg);padding:0}}"""
    js = """document.querySelectorAll(".chip").forEach(c=>c.addEventListener("click",()=>{document.querySelectorAll(".chip").forEach(x=>x.setAttribute("aria-pressed",x===c));
document.querySelectorAll(".giro").forEach(g=>{g.hidden=!!c.dataset.p&&g.dataset.p!==c.dataset.p})}));"""
    why = (f"<b>Idea:</b> il gancio PR senza cifre, cioè solo i cambi di opinione, in un formato prima → dopo con due fonti. "
           f"<b>⚠️ Coi dati di oggi:</b> {chg} cambio netto (solo Vox, rispetto a prima della legislatura), {evo} evoluzioni morbide, {dv} casi dice ≠ vota. "
           "Per avere un feed vivo serve l'aggiornamento di ottobre e novembre più i programmi 2026, oppure regole meno strette (vedi la nota finale).")
    return page(2, "Giros", why, body, data, js, css)


# ---------------------------------------------------------------- 03 dice vota promete

def m3(cfg, parties, topics, stmts, badges, data):
    chips = "".join(f'<button class="chip" aria-pressed="{str(i == 0).lower()}" data-t="{t["key"]}">{e(t["label_short"])}</button>'
                    for i, t in enumerate(topics))
    body = header("Lo que prometen, lo que dicen y lo que votan",
                  "Para cada tema, ponemos en fila el programa de 2023, las declaraciones de esta legislatura, las votaciones en el Congreso y el programa de 2026.")
    body += f'<div class="chips">{chips}</div><p id="prop" class="why" style="margin-bottom:16px"></p><div id="grid"></div>'
    body += '<div class="legend"><span><span class="dot fav"></span>A favor</span><span><span class="dot con"></span>En contra</span><span><span class="dot amb"></span>Ambiguo</span><span><span class="dot na"></span>Sin posición</span></div>'
    css = """#grid{display:grid;gap:12px}.row{display:grid;grid-template-columns:140px repeat(4,1fr);gap:8px;align-items:stretch}
.hd{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);padding:0 8px}
.col{background:var(--s50);border:1px solid var(--s200);border-radius:8px;padding:10px;font-size:13px;min-height:84px}
.col.pend{border-style:dashed;color:var(--subtle);display:flex;align-items:center;justify-content:center;text-align:center}
.col .n{display:flex;align-items:center;gap:6px;font-weight:800;margin-bottom:4px}.col p{margin:0;color:var(--txt2);display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.flag{display:inline-block;margin-top:6px;font-size:11px;font-weight:800;color:#9a5b00;background:#fff4e5;border-radius:4px;padding:1px 6px}
@media(max-width:760px){.row{grid-template-columns:1fr 1fr}.row .pn{grid-column:1/-1}.hdr{display:none}}"""
    js = """const g=document.getElementById("grid"),pr=document.getElementById("prop");
function col(L,label){if(!L.length)return `<div class="col pend">Nada registrado</div>`;const s=L[0];
const stances=[...new Set(L.map(x=>x.stance))];
return `<div class="col"><div class="n">${stances.map(x=>`<span class="dot ${ST[x][1]}" title="${ST[x][0]}"></span>`).join("")} ${L.length} ${label}</div>
<p>${s.quote?"«"+esc(s.quote)+"»":esc(s.context)}</p><span class="meta">${fd(s.date)} · <a class="src" href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.source_name)}</a></span></div>`}
function draw(t){pr.innerHTML=T[t].prop?`<b>Pregunta:</b> ${esc(T[t].prop)}`:"<b>Tema sin pregunta cerrada:</b> solo recogemos lo que dicen.";
let h=`<div class="row hdr"><span></span><span class="hd">Programa 2023</span><span class="hd">Dice (declaraciones)</span><span class="hd">Vota (Congreso)</span><span class="hd">Programa 2026</span></div>`;
D.parties.forEach(p=>{const L=D.stmts.filter(s=>s.party===p.key&&s.topic===t);
const prog=L.filter(s=>s.type==="programa"&&s.date<"2025-01-01"),dice=L.filter(s=>s.type==="declaracion"||s.type==="reportada"),vota=L.filter(s=>s.type==="voto");
const dv=dice.length&&vota.length&&dice[0].stance!=="ambiguo"&&vota[0].stance!=="ambiguo"&&dice[0].stance!==vota[0].stance;
h+=`<div class="row"><div class="pn">${pty(p.key)}${p.note?`<div class="sub">${esc(p.note)}</div>`:""}${dv?`<span class="flag">⇄ dice ≠ vota</span>`:""}</div>
${col(prog,"puntos")}${col(dice,"declaraciones")}${col(vota,"votaciones")}<div class="col pend">Pendiente<br>(se publica 10-13 nov)</div></div>`});
g.innerHTML=h}
document.querySelectorAll(".chip").forEach(c=>c.addEventListener("click",()=>{document.querySelectorAll(".chip").forEach(x=>x.setAttribute("aria-pressed",x===c));draw(c.dataset.t)}));
draw(D.topics[0].key);"""
    why = ("<b>Idea:</b> mette in colonna le 4 fonti di uno stesso partito (promette 2023 → dice → vota → promette 2026). "
           "Le contraddizioni si vedono da sole, senza che siamo noi a dirle, e il flag ⇄ si accende solo quando l'ultima dichiarazione e l'ultimo voto sono opposti. "
           "<b>Per chi:</b> il giornalista. <b>Limite:</b> oggi ci sono pochi programmi 2023 (19 voci in totale) e i programmi 2026 non sono ancora usciti.")
    return page(3, "Dice, vota, promete", why, body, data, js, css)


# ---------------------------------------------------------------- 04 cronologia

def m4(cfg, parties, topics, stmts, badges, data):
    chips = "".join(f'<button class="chip" aria-pressed="{str(i == 0).lower()}" data-t="{t["key"]}">{e(t["label_short"])}</button>'
                    for i, t in enumerate(topics))
    body = header("La línea del tiempo de cada partido",
                  "Cada punto es una prueba: una declaración, una votación o un programa. El color indica la posición, la forma el tipo de prueba. Pulsa un punto para leerlo.")
    body += f'<div class="chips">{chips}</div><div class="tw"><svg id="tl" role="img" aria-label="Cronología"></svg></div><div id="pick"></div>'
    body += """<div class="legend"><span><span class="dot fav"></span>A favor</span><span><span class="dot con"></span>En contra</span><span><span class="dot amb"></span>Ambiguo</span>
<span>● Declaración</span><span>■ Votación</span><span>◆ Programa</span><span>Banda gris = antes de la legislatura</span></div>"""
    css = """.tw{overflow-x:auto;border:1px solid var(--s200);border-radius:8px;background:#fff}#tl{display:block;min-width:820px;width:100%}
#tl .pt{cursor:pointer;stroke:#fff;stroke-width:1.5}#tl .pt:hover,#tl .pt.on{stroke:var(--navy);stroke-width:2.5}#pick{margin-top:16px;max-width:640px}
#tl text{font-family:inherit}"""
    js = """const sv=document.getElementById("tl"),pk=document.getElementById("pick");
const C={a_favor:"#02c5ae",en_contra:"#5a52ff",ambiguo:"#79716b",na:"#d6d3d1"};
const t0=new Date("2023-01-01"),t1=new Date("2026-12-01"),W=1080,L=150,R=20,RH=56,TOP=36;
const x=d=>L+(new Date(d)-t0)/(t1-t0)*(W-L-R);
function draw(t){const H=TOP+RH*D.parties.length+10;sv.setAttribute("viewBox",`0 0 ${W} ${H}`);
let h=`<rect x="${L}" y="${TOP-8}" width="${x("2023-08-17")-L}" height="${H-TOP}" fill="#f5f5f4"/>`;
for(let y=2023;y<=2026;y++){const X=x(y+"-01-01");h+=`<line x1="${X}" x2="${X}" y1="${TOP-8}" y2="${H}" stroke="#e7e5e4"/><text x="${X+4}" y="20" font-size="12" fill="#63697f">${y}</text>`}
const E=x("2026-11-29");h+=`<line x1="${E}" x2="${E}" y1="${TOP-8}" y2="${H}" stroke="#5a52ff" stroke-dasharray="4 3"/><text x="${E-4}" y="20" font-size="12" fill="#5a52ff" text-anchor="end" font-weight="800">29-N</text>`;
D.parties.forEach((p,i)=>{const cy=TOP+RH*i+RH/2;h+=`<line x1="${L}" x2="${W-R}" y1="${cy}" y2="${cy}" stroke="#e7e5e4"/><rect x="8" y="${cy-6}" width="10" height="10" rx="2" fill="${p.color}"/><text x="24" y="${cy+4}" font-size="14" font-weight="800" fill="#212430">${esc(p.label)}</text>`;
D.stmts.filter(s=>s.party===p.key&&s.topic===t&&s.date>="2023-01-01").forEach((s,j)=>{const X=x(s.date),Y=cy+((j%5)-2)*7,c=C[s.stance],a=`class="pt" data-id="${s.id}" fill="${c}"`;
h+=s.type==="voto"?`<rect ${a} x="${X-6}" y="${Y-6}" width="12" height="12"/>`:s.type==="programa"?`<path ${a} d="M${X} ${Y-8}L${X+8} ${Y}L${X} ${Y+8}L${X-8} ${Y}Z"/>`:`<circle ${a} cx="${X}" cy="${Y}" r="6"/>`})});
sv.innerHTML=h;pk.innerHTML="";
sv.querySelectorAll(".pt").forEach(el=>el.addEventListener("click",()=>{sv.querySelectorAll(".pt.on").forEach(z=>z.classList.remove("on"));el.classList.add("on");pk.innerHTML=item(D.stmts.find(s=>s.id===el.dataset.id))}))}
document.querySelectorAll(".chip").forEach(c=>c.addEventListener("click",()=>{document.querySelectorAll(".chip").forEach(z=>z.setAttribute("aria-pressed",z===c));draw(c.dataset.t)}));
draw(D.topics[0].key);"""
    why = ("<b>Idea:</b> i cambi di opinione si vedono come un cambio di colore lungo la riga del partito, quindi la timeline mostra anche quello che le regole del badge non contano. "
           "<b>Per chi:</b> il lettore curioso e i social (un singolo tema diventa uno screenshot pronto). "
           "<b>Limite:</b> su mobile la timeline va scrollata, quindi serve una vista a lista come alternativa.")
    return page(4, "Cronología", why, body, data, js, css)


# ---------------------------------------------------------------- 05 hemeroteca

def m5(cfg, parties, topics, stmts, badges, data):
    sel = lambda name, opts: f'<select id="{name}"><option value="">Todos</option>' + "".join(f'<option value="{k}">{e(v)}</option>' for k, v in opts) + "</select>"
    body = header("Hemeroteca energética del 29-N",
                  "Busca cualquier frase dicha, votada o escrita en un programa por los partidos sobre energía. Cada resultado se puede copiar con su fuente o descargar en CSV.")
    body += f"""<div class="bar"><input id="q" type="search" placeholder="Busca: «IVA», «nucleares», «Feijóo», «bono social»…">
<label>Partido {sel('fp', [(p['key'], p['label']) for p in parties])}</label>
<label>Tema {sel('ft', [(t['key'], t['label_short']) for t in topics])}</label>
<label>Tipo {sel('fy', [('declaracion', 'Declaración'), ('voto', 'Votación'), ('programa', 'Programa'), ('reportada', 'Reportada')])}</label>
<label>Posición {sel('fs', [('a_favor', 'A favor'), ('en_contra', 'En contra'), ('ambiguo', 'Ambiguo')])}</label></div>
<div class="rb"><span id="n" class="meta"></span><button id="csv" class="chip">Descargar CSV</button></div><div id="res"></div>"""
    css = """.bar{display:grid;grid-template-columns:2fr repeat(4,1fr);gap:8px;margin:0 0 12px;padding:16px;background:var(--p50);border-radius:8px}
.bar input,.bar select{font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--p200);border-radius:8px;background:#fff;width:100%}
.bar label{font-size:12px;font-weight:800;color:var(--muted);display:flex;flex-direction:column;gap:4px}.bar input{align-self:end}
.rb{display:flex;justify-content:space-between;align-items:center;margin:0 0 12px}#res{display:grid;gap:12px}
.cp{font:inherit;font-size:12px;font-weight:800;color:var(--p);background:none;border:1px solid var(--p200);border-radius:6px;padding:3px 8px;cursor:pointer;margin-top:8px}
mark{background:#fff4c2}@media(max-width:760px){.bar{grid-template-columns:1fr 1fr}.bar input{grid-column:1/-1}}"""
    js = """const $=id=>document.getElementById(id);let cur=[];
function hl(s,q){s=esc(s);if(!q)return s;return s.replace(new RegExp("("+q.replace(/[.*+?^${}()|[\\]\\\\]/g,"\\\\$&")+")","gi"),"<mark>$1</mark>")}
function run(){const q=$("q").value.trim().toLowerCase(),fp=$("fp").value,ft=$("ft").value,fy=$("fy").value,fs=$("fs").value;
cur=D.stmts.filter(s=>(!fp||s.party===fp)&&(!ft||s.topic===ft)&&(!fy||s.type===fy)&&(!fs||s.stance===fs)&&(!q||[s.quote,s.context,s.person,s.role,s.source_name].join(" ").toLowerCase().includes(q)));
$("n").textContent=`${cur.length} resultados de ${D.stmts.length}`;
$("res").innerHTML=cur.slice(0,60).map(s=>`<div class="card"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap">${pty(s.party)}<span class="sub">${esc(T[s.topic].label)} · ${TY[s.type]}</span>${bdg(s.stance)}</div>
<p class="q${s.quote?"":" ctx"}">${s.quote?"«"+hl(s.quote,q)+"»":hl(s.context,q)}</p><div class="meta">${hl(s.person,q)}, ${esc(s.role)} · ${fd(s.date)} · <a class="src" href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.source_name)}</a></div>
<button class="cp" data-id="${s.id}">Copiar cita con fuente</button></div>`).join("")+(cur.length>60?`<p class="meta">Mostrando 60 de ${cur.length}. Afina la búsqueda.</p>`:"")}
["q","fp","ft","fy","fs"].forEach(id=>$(id).addEventListener("input",run));
$("res").addEventListener("click",ev=>{const b=ev.target.closest(".cp");if(!b)return;const s=D.stmts.find(x=>x.id===b.dataset.id);
const t=`${s.quote?"«"+s.quote+"»":s.context} (${s.person}, ${s.role}, ${fd(s.date)}). Fuente: ${s.source_name}, ${s.source_url}. Vía papernest.es`;
navigator.clipboard.writeText(t).then(()=>{b.textContent="✓ Copiada"})});
$("csv").addEventListener("click",()=>{const k=["party","topic","type","date","person","role","stance","quote","context","source_name","source_url"];
const csv=[k.join(",")].concat(cur.map(s=>k.map(f=>'"'+String(s[f]??"").replace(/"/g,'""')+'"').join(","))).join("\\n");
const a=document.createElement("a");a.href=URL.createObjectURL(new Blob(["\\ufeff"+csv],{type:"text/csv"}));a.download="hemeroteca-energia-29n.csv";a.click()});
run();"""
    why = ("<b>Idea:</b> un database \"puro\" per i giornalisti, con ricerca libera, filtri, \"Copia citazione con fonte\" (che porta la firma <i>Vía papernest.es</i>, quindi backlink e menzioni) ed export in CSV. "
           "Nessuna sintesi, quindi è la versione più difendibile. <b>Limite:</b> per il lettore comune è freddo, e funziona meglio come seconda vista sotto il mockup 1 o il 3.")
    return page(5, "Hemeroteca", why, body, data, js, css)


IDEAS = [
    ("01-tablero.html", "Tablero", "Matrice 5 partiti × 10 temi con l'ultima posizione registrata e la data; il click apre le prove.", "Lettore: quadro in 10 secondi"),
    ("02-giros.html", "Giros", "Feed solo dei cambi di opinione, prima → dopo, con due fonti per scheda.", "PR: il gancio senza cifre"),
    ("03-dice-vota-promete.html", "Dice · Vota · Promete", "Per tema: programma 2023 | dichiarazioni | voti | programma 2026, affiancati per partito.", "Giornalista: le contraddizioni si vedono da sole"),
    ("04-cronologia.html", "Cronología", "Timeline per partito: ogni prova è un punto colorato per posizione e con una forma per tipo.", "Social e curiosi: screenshot per tema"),
    ("05-hemeroteca.html", "Hemeroteca", "Ricerca libera e filtri, con copia della citazione e della fonte ed export CSV.", "Giornalista: database puro, il più difendibile"),
]


def index(stmts, badges):
    c, evo, chg, dv = counts(stmts, badges)
    cards = "".join(f'<a class="card ix" href="{f}"><span class="mock">Mockup {i + 1}</span><h2 style="margin:0 0 6px">{e(n)}</h2>'
                    f'<p class="q">{e(d)}</p><p class="meta">{e(w)}</p></a>' for i, (f, n, d, w) in enumerate(IDEAS))
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Database partiti × energia — 5 mockup</title><style>{CSS}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}}
.ix{{text-decoration:none;color:inherit;display:block}}.ix:hover{{outline:2px solid var(--p)}}</style></head><body><div class="wrap">
<p class="mock">papernest.es · elezioni 29-N · grill 3 nov 2026</p><h1>Database partiti × energia: 5 mockup</h1>
<p class="lead">Niente cifre in bolletta: solo dichiarazioni, voti, programmi e cambi di opinione, con le fonti. Tutti i mockup usano i dati veri ({len(stmts)} prove, raccolte all'8 ott) già accorpati come deciso nel grill: 5 partiti (Frente Amplio con lo storico Sumar, senza SALF) e 10 temi (8 con posizione, 2 solo timeline).</p>
{stats_html([("prove", len(stmts)), ("cambi netti", chg), ("evoluzioni", evo), ("dice ≠ vota", dv)])}
<div class="grid">{cards}</div></div></body></html>"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg, parties, topics, stmts, badges = load()
    data = js_data(parties, topics, stmts)
    OUT.mkdir(parents=True, exist_ok=True)
    for (f, *_), fn in zip(IDEAS, (m1, m2, m3, m4, m5)):
        (OUT / f).write_text(fn(cfg, parties, topics, stmts, badges, data), encoding="utf-8")
    (OUT / "index.html").write_text(index(stmts, badges), encoding="utf-8")
    c, evo, chg, dv = counts(stmts, badges)
    print(f"{len(stmts)} prove · {len(parties)} partiti · {len(topics)} temi · cambi netti {chg} · evoluzioni {evo} · dice≠vota {dv}")
    print(f"Mockup in {OUT}")


if __name__ == "__main__":
    main()

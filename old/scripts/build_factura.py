"""Genera la pagina "La factura en juego | Elecciones 29N" (papernest.es), pronta per WordPress.

Blocchi (grill 8 ott 2026):
 1. Titolo "Tu voto vale hasta X €" (hogar tipo) + hogar vulnerable + contatori veri
 2. Tabella € : Impuestos / Bono social / TUR × partiti + hogares afectados, "¿Cómo lo calculamos?" per cella
 3. Tabella domande (Sí/No/Ambiguo/—) copiabile (HTML + CSV)
 4. Cara a cara in €
 5. Timeline dichiarazioni con etichetta € quando la dichiarazione alimenta una cifra
 + metodologia

Uso: py scripts/build_factura.py   (rilancia anche scripts/calc.py)
Output: output/factura/codice_intro.html, codice_testo.html (WordPress) + output/factura/preview.html (browser)
Vincoli WP: classi prefisso .lfj-, JS con addEventListener dentro setTimeout(300)+try/catch, niente font esterni,
contenuto nel markup (il JS serve solo per filtri, cara a cara, copia).
"""
import csv
import html
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402
import calc  # noqa: E402

ROOT, DATA = B.ROOT, B.DATA
OUT = ROOT / "output" / "factura"
e = html.escape

PARTY_COLOR = {"PSOE": "#e30613", "PP": "#1d5fae", "VOX": "#5bbf21", "SUMAR": "#e5307a", "PODEMOS": "#6b2d7b", "SALF": "#1f1f1f"}
EURO_ROWS = [  # (topic, profilo mostrato nel blocco 2, etichetta, sottoetichetta)
    ("impuestos_factura", "hogar_tipo", "Impuestos en la factura", "IVA de la luz y el gas + impuesto eléctrico · hogar tipo"),
    ("bono_social", "hogar_vulnerable", "Bono social eléctrico", "Descuento en la luz · hogar vulnerable"),
    ("tur_gas", "hogar_tipo", "Tarifa regulada del gas (TUR)", "Tope a la subida de la TUR · hogar con gas en TUR"),
    ("precio_luz_gas", "hogar_tipo", "Tope al gas («excepción ibérica»)", "Referencia: lo que ahorró en 2022 · hogar en PVPC"),
]
IMPACTED_KEY = {"precio_luz_gas": "pvpc"}  # riga -> chiave in impacted.json se diversa dal tema
ANS_LABEL = {"si": ("Sí", "si"), "no": ("No", "no"), "ambiguo": ("Ambiguo", "amb"), "sin_datos": ("—", "nd")}
BADGE_TO_ANS = {"a_favor": "si", "en_contra": "no", "ambiguo": "amb", "sin_declaraciones": "nd", "sin_badge": "cit"}
Q_TOPIC_FROM_BADGE = {  # domande dei temi non-€ che coincidono con la proposition del tema (posizioni già calcolate)
    "excepcion_iberica": "precio_luz_gas", "nucleares_calendario": "nucleares", "renovables_acelerar": "renovables",
    "impuesto_energeticas": "impuesto_energeticas", "carburantes_impuestos": "carburantes", "coche_2035": "coche_electrico",
    "autoconsumo_ayudas": "autoconsumo"}


def eur(x, sign=True):
    s = f"{abs(x):,.0f}".replace(",", ".")
    if not sign:
        return f"{s} €"
    return ("−" if x < 0 else "+" if x > 0 else "") + f"{s} €"


def millones(n):
    if n is None:
        return "—"
    return f"{n / 1e6:.1f}".replace(".", ",") + " M" if n >= 1e6 else f"{n:,.0f}".replace(",", ".")


def load_all():
    calc.main()
    M = B.load_json(DATA / "euro_matrix.json")
    parties = [p for p in B.load_json(DATA / "parties.json")["parties"] if not p.get("hidden")]
    tdoc = B.load_json(DATA / "topics.json")
    topics = {t["key"]: t for t in tdoc["topics"]}
    qs = B.load_json(DATA / "questions.json")["questions"]
    cfg = B.load_json(DATA / "config.json")
    stmts, by_id = {}, {}
    for p in parties:
        doc = B.load_json(DATA / "statements" / f"{p['slug']}.json")
        stmts[p["key"]] = doc["statements"]
        for s in doc["statements"]:
            by_id[s["id"]] = {**s, "_party": p}
    answers = {}
    for f in sorted((DATA / "answers").glob("*.json")):
        for a in B.load_json(f).get("answers", []):
            answers[(a["party"], a["question"])] = a
    badges = {(p["key"], k): B.compute_badge([s for s in stmts[p["key"]] if s["topic"] == k], t, p["key"], cfg)
              for p in parties for k, t in topics.items()}
    cache = B.load_json(ROOT / "output" / "verify_cache.json") if (ROOT / "output" / "verify_cache.json").exists() else {}
    return {"M": M, "parties": parties, "topics": topics, "qs": qs, "cfg": cfg, "stmts": stmts, "by_id": by_id,
            "answers": answers, "badges": badges, "n_docs": len(cache), "today": date.today()}


# ----------------------------------------------------------------- celle €

def cell_html(D, pk, topic, prof):
    c = D["M"]["cells"].get(f"{pk}|{topic}|{prof}")
    if not c or c["effect"] is None:
        return '<td class="lfj-c lfj-c--nd"><b>—</b><small>sin propuesta cuantificada</small></td>', None
    f, eff = set(c["flags"]), c["effect"]
    approx = "≈ " if c["level"] == 2 else ""
    if "sin_tope" in f:
        main, sub, mod = f"{eur(eff)} en 2027", f"{eur(c['y2028_eur'])} en 2028 · sin tope: pagas antes, sin deuda", "cost"
    elif "aplazado" in f:
        main, sub, mod = "0 €", f"como la ley: tope y ~{eur(c['aplazado_eur'], False)} aplazados a 2028", "def"
        if "tur_formula_completa_necesaria" in f:
            sub += " · propone un tope más bajo (5%): no calculable"
        elif "sin_propuesta" in f:
            sub += " · sin propuesta: sigue el tope de la ley"
    elif "sin_propuesta" in f:
        hint = c.get("answer_hint")
        main, sub, mod = "0 €", ("posición ambigua, sin cifra: se aplica la ley de 2027" if hint == "ambiguo"
                                 else "sin propuesta: se aplica la ley de 2027"), "law"
    elif "expira_antes_2027" in f and abs(eff) < 0.5:
        main, sub, mod = "0 €", "su medida acaba en diciembre", "zero"
    elif "referencia_2022" in f and eff < 0:
        main, sub, mod = approx + eur(eff), "la última vez que se aplicó (jun-dic 2022) · hoy el efecto sería menor", "save"
    elif "rechaza" in f:
        main, sub, mod = "0 €", "rechaza la medida", "zero"
    else:
        main, sub, mod = approx + eur(eff * calc.HORIZON_YEARS), f"en 4 años · {eur(eff)}/año", "save" if eff < 0 else "cost" if eff > 0 else "zero"
    notes = []
    if "duracion_no_definida" in f:
        notes.append("duración no especificada")
    if "propuesta_antigua" in f:
        ds = [D["by_id"][i]["date"] for u in c["used"] for i in u["evidence"] if i in D["by_id"]]
        notes.append(f"propuesta de {B.fdate(max(ds), True)} · fuera del titular" if ds else "propuesta antigua · fuera del titular")
    if "condicionada" in f and "expira_antes_2027" not in f:
        notes.append("condicionada")
    # come lo calcoliamo
    prof_label = D["M"].get("_profiles", {}).get(prof, prof)
    params = "".join(f'<li>{e(u["value_note"] or u["question"])}{" (acaba antes de 2027: no cuenta)" if u.get("expired") else ""}</li>' for u in c["used"])
    srcs = []
    for u in c["used"]:
        for i in u["evidence"]:
            s = D["by_id"].get(i)
            if s:
                srcs.append(f'<a href="{e(s["source_url"])}" target="_blank" rel="noopener">{e(s["source_name"])} · {e(B.fdate(s["date"], True))}</a>')
    pop ='<details class="lfj-how"><summary>Cómo se calcula</summary><div class="lfj-pop"><button type="button" class="lfj-x" aria-label="Cerrar">×</button>'
    if not c["used"]:
        body = (f'<p>Factura anual del {e(prof_label)} con la ley vigente el 1/1/2027: <b>{eur(c["ref_eur"], False)}</b>. '
                f'Sin una propuesta cuantificada del partido, la factura es la misma.</p>')
    else:
        body = (f'<p>Factura anual del {e(prof_label)} con la ley vigente el 1/1/2027: <b>{eur(c["ref_eur"], False)}</b>. '
                f'Con la propuesta: <b>{eur(c["new_eur"], False)}</b>.</p><ul>{params}</ul>'
                f'<p class="lfj-srcs">{" · ".join(dict.fromkeys(srcs))}</p>')
    note_html = f'<small class="lfj-note">{e(" · ".join(notes))}</small>' if notes else ""
    text = f"{main} ({sub}{'; ' + '; '.join(notes) if notes else ''})"
    return f'<td class="lfj-c lfj-c--{mod}"><b>{e(main)}</b><small>{e(sub)}</small>{note_html}{pop}{body}</div></details></td>', text


# ----------------------------------------------------------------- blocchi

def block_hero(D):
    H = D["M"]["headline"]
    x_t, x_v = H["hogar_tipo"].get("x_eur"), H["hogar_vulnerable"].get("x_eur")
    n_prog = len({s["source_url"] for v in D["stmts"].values() for s in v if s["type"] == "programa"})
    n_st = sum(len(v) for v in D["stmts"].values())
    counters = [(str(len(D["parties"])), "partidos"), (str(n_prog), "programas analizados"), (str(n_st), "declaraciones y votos verificados"),
                (str(D["n_docs"]), "documentos revisados"), ("hoy", "última actualización")]
    cnt = "".join(f'<li><b>{e(a)}</b><span>{e(b)}</span></li>' for a, b in counters)
    vul = (f'<p class="lfj-vul">Hogar vulnerable con bono social: <b>hasta {eur(x_v, False)}</b> en la legislatura.</p>' if x_v else "")
    hog = D["M"].get("impacted", {}).get("impuestos_factura", {}).get("hogares") or 0
    nat = H["hogar_tipo"].get("x_eur_year", 0) * hog / 1e6
    vul += (f'<p class="lfj-vul">Para el conjunto de los hogares: <b>hasta {nat:,.0f} millones de euros al año</b> de diferencia.</p>'.replace(",", ".") if nat else "")
    title = f"Tu voto vale hasta {eur(x_t, False)} en la factura de la luz y el gas" if x_t else "Tu voto, en la factura de la luz y el gas"
    return title, f"""<section class="lfj-hero">
{vul}<ul class="lfj-count">{cnt}</ul></section>"""


def block_euro(D):
    P = D["parties"]
    imp = D["M"].get("impacted", {})
    head = "".join(f'<th scope="col" style="--pc:{PARTY_COLOR[p["key"]]}"><span>{e(p["label"])}</span></th>' for p in P)
    rows, csv_rows = [], [["Tema", "Hogar"] + [p["label"] for p in P] + ["Hogares afectados"]]
    for topic, prof, lab, sub in EURO_ROWS:
        cells = [cell_html(D, p["key"], topic, prof) for p in P]
        tds = "".join(h for h, _ in cells)
        csv_rows.append([lab, sub] + [t for _, t in cells] + [millones(imp.get(IMPACTED_KEY.get(topic, topic), {}).get("hogares"))])
        r = imp.get(IMPACTED_KEY.get(topic, topic), {})
        pers = r.get("personas_official") or r.get("personas_estimate")
        pers_lab = "personas" if r.get("personas_official") else "≈ personas (estimación)"
        unit = {"impuestos_factura": "hogares", "bono_social": "hogares con bono social", "tur_gas": "suministros en TUR"}.get(topic, "suministros en PVPC")
        src = f'<a href="{e(r["source"])}" target="_blank" rel="noopener">fuente</a>' if r.get("source") else ""
        aff = f'<td class="lfj-aff"><b>{millones(r.get("hogares"))}</b><small>{unit}</small>{f"<small>{millones(pers)} {pers_lab}</small>" if pers else ""}{src}</td>'
        rows.append(f'<tr><th scope="row"><b>{e(lab)}</b><small>{e(sub)}</small></th>{tds}{aff}</tr>')
    return f"""<section class="lfj-sec" id="cuanto">
<h2>¿Cuánto vale cada propuesta en tu factura?</h2>
{tools("lfj-et", "la-factura-en-juego-euros.csv", csv_rows)}
<div class="lfj-tw"><table class="lfj-t lfj-teur" id="lfj-et"><thead><tr><th></th>{head}<th scope="col" class="lfj-aff">Hogares afectados</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
</section>"""


def tools(table_id, filename, csv_rows):
    """Pulsanti Copiar tabla + Descargar CSV (riusati da tabella € e tabella domande)."""
    buf = io.StringIO()
    csv.writer(buf).writerows(csv_rows)
    href = "data:text/csv;charset=utf-8," + __import__("urllib.parse").parse.quote("﻿" + buf.getvalue())
    return (f'<div class="lfj-tools"><button type="button" class="lfj-btn" data-lfj-copy="{table_id}">Copiar tabla</button>'
            f'<a class="lfj-btn lfj-btn--ghost" download="{filename}" href="{href}">Descargar CSV</a><span class="lfj-copied" aria-live="polite"></span></div>')


def q_answer(D, q, p):
    a = D["answers"].get((p["key"], q["key"]))
    if a:
        lab, mod = ANS_LABEL.get(a["answer"], ("—", "nd"))
        val = ""
        if a.get("value") is not None and q.get("euro") and a["answer"] == "si":
            val = f' {a["value"]:g}%'.replace(".", ",")
        return lab + val, mod, a.get("rationale", "")
    if q["key"] in Q_TOPIC_FROM_BADGE:
        b = D["badges"][(p["key"], Q_TOPIC_FROM_BADGE[q["key"]])]["badge"]
        mod = BADGE_TO_ANS[b]
        return {"si": "Sí", "no": "No", "amb": "Ambiguo", "nd": "—", "cit": "—"}[mod], mod, ""
    return "—", "nd", ""


def block_questions(D):
    P, T = D["parties"], D["topics"]
    qs = [q for q in D["qs"] if q.get("binary", True) is not False and (q["topic"] in ("impuestos_factura", "bono_social", "tur_gas") or q["key"] in Q_TOPIC_FROM_BADGE)]
    head = "".join(f'<th scope="col">{e(p["label"])}</th>' for p in P)
    rows, csv_rows, cur = [], [["Tema", "Pregunta"] + [p["label"] for p in P]], None
    for q in qs:
        if q["topic"] != cur:
            cur = q["topic"]
            n = sum(1 for x in qs if x["topic"] == cur)
            rows.append(f'<tr class="lfj-tg"><th colspan="{len(P) + 1}" scope="colgroup">{e(T[cur]["label"])}'
                        f'<small>{n} pregunta{"s" if n > 1 else ""}</small></th></tr>')
        cells, crow = [], [T[q["topic"]]["label"], q["text"]]
        for p in P:
            lab, mod, why = q_answer(D, q, p)
            cells.append(f'<td class="lfj-a lfj-a--{mod}" title="{e(why)}">{e(lab)}</td>')
            crow.append(lab)
        eur_tag = '<span class="lfj-eurq" title="Alimenta el cálculo de la factura">€</span>' if q.get("euro") else ""
        rows.append(f'<tr class="lfj-qr"><th scope="row">{e(q["text"])}{eur_tag}</th>{"".join(cells)}</tr>')
        csv_rows.append(crow)
    return f"""<section class="lfj-sec" id="preguntas">
<h2>Todas las respuestas, pregunta a pregunta</h2>
<p class="lfj-lead">{len(qs)} preguntas sobre energía y lo que responde cada partido según sus declaraciones y votaciones desde 2023. Las preguntas marcadas con <span class="lfj-eurq">€</span> alimentan el cálculo de la factura.</p>
{tools("lfj-qt", "la-factura-en-juego-preguntas.csv", csv_rows)}
<div class="lfj-tw"><table class="lfj-t lfj-tq" id="lfj-qt"><thead><tr><th scope="col">Pregunta</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="lfj-foot">Fuente: La factura en juego (papernest), actualizado el {e(B.fdate(D['today']))}.</p>
</section>"""


def block_cara(D):
    P = D["parties"]
    # cifre sulla legislatura (4 anni), come il titolo; la TUR resta l'effetto 2027 (fuori dal totale perché aplazado)
    data = {p["key"]: {f"{t}|{pr}": (D["M"]["cells"][f'{p["key"]}|{t}|{pr}']["effect"] * (1 if t in ("tur_gas", "precio_luz_gas") else calc.HORIZON_YEARS))
                       for t, pr, _, _ in EURO_ROWS} for p in P}
    flags = {p["key"]: {f"{t}|{pr}": (D["M"]["cells"].get(f'{p["key"]}|{t}|{pr}') or {}).get("flags", []) for t, pr, _, _ in EURO_ROWS} for p in P}
    opts = lambda sel: "".join(f'<option value="{p["key"]}"{" selected" if p["key"] == sel else ""}>{e(p["label"])}</option>' for p in P)
    rows = "".join(f'<tr data-k="{t}|{pr}"><th scope="row">{e(lab)}<small>{e(sub)}</small></th><td class="lfj-ca"></td><td class="lfj-cb"></td><td class="lfj-cd"></td></tr>'
                   for t, pr, lab, sub in EURO_ROWS)
    return f"""<section class="lfj-sec lfj-cara" id="cara-a-cara">
<h2>Cara a cara: ¿cuánto cambia tu factura según a quién votes?</h2>
<div class="lfj-pick"><select id="lfj-ca" aria-label="Partido A">{opts("PSOE")}</select><span class="lfj-vs">VS</span><select id="lfj-cb" aria-label="Partido B">{opts("PP")}</select></div>
<div class="lfj-tw"><table class="lfj-t lfj-tcara"><thead><tr><th></th><th class="lfj-ha"></th><th class="lfj-hb"></th><th>Diferencia en 4 años</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="lfj-total" aria-live="polite"></p>
<p class="lfj-foot" style="text-align:center">* Duración no especificada o propuesta de hace más de 12 meses: se muestra, pero no cuenta para el titular.</p>
<script type="application/json" id="lfj-cara-data">{json.dumps({"eff": data, "flags": flags, "labels": {p["key"]: p["label"] for p in P}}, ensure_ascii=False)}</script>
</section>"""


def block_timeline(D):
    # mappa prova -> cifra € (prima cella che la usa)
    tag = {}
    for k, c in D["M"]["cells"].items():
        if c.get("effect") is None:
            continue
        pk, topic, prof = k.split("|")
        if (topic, prof) not in [(t, pr) for t, pr, _, _ in EURO_ROWS]:
            continue
        for u in c["used"]:
            for i in u["evidence"]:
                if "aplazado" in c["flags"]:
                    tag.setdefault(i, f"0 € hoy · ~{eur(c['aplazado_eur'], False)} aplazados")
                elif not u.get("expired"):
                    tag.setdefault(i, f"{'≈ ' if c['level'] == 2 else ''}{eur(c['effect'])}/año")
    # prima le citazioni (si leggono meglio), poi voti e programmi; ordine cronologico dentro la lista finale
    nat = [s for s in D["by_id"].values() if s["level"] == "nacional"]
    quotes = sorted([s for s in nat if s.get("quote")], key=lambda s: s["date"], reverse=True)[:30]
    others = sorted([s for s in nat if not s.get("quote")], key=lambda s: s["date"], reverse=True)[:10]
    items = sorted(quotes + others, key=lambda s: (s["date"], bool(s.get("quote"))), reverse=True)
    lis = []
    for n, s in enumerate(items):
        p = s["_party"]
        if s.get("quote"):
            body = f'<p class="lfj-q">«{e(s["quote"])}»</p>'
        else:
            ctx = (s.get("context") or "").split(". ")[0]
            ctx = ctx if len(ctx) <= 150 else ctx[:150].rsplit(" ", 1)[0] + "…"
            lab = {"voto": "Votación en el Congreso", "programa": "Programa electoral", "reportada": "Declaración reportada"}.get(s["type"], "")
            body = f'<p class="lfj-q lfj-q--ctx" title="{e(s.get("context") or "")}"><b>{e(lab)}:</b> {e(ctx)}</p>'
        t = tag.get(s["id"])
        lis.append(f'<li class="{"lfj-more" if n >= 12 else ""}" data-p="{p["key"]}" style="--pc:{PARTY_COLOR[p["key"]]}"><div class="lfj-when">{e(B.fdate(s["date"], True))}</div>'
                   f'<div class="lfj-what"><p class="lfj-meta"><b>{e(p["label"])}</b> · {e(D["topics"][s["topic"]]["label_short"])}'
                   f'{f" <span class=lfj-eur>{e(t)}</span>" if t else ""}</p>{body}'
                   f'<p class="lfj-who">{e(s["person"])} · <a href="{e(s["source_url"])}" target="_blank" rel="noopener">{e(s["source_name"])}</a></p></div></li>')
    return f"""<section class="lfj-sec" id="declaraciones">
<h2>Las últimas declaraciones</h2>
<div class="lfj-chips" role="group" aria-label="Filtrar por partido"><button type="button" class="lfj-chip" data-tp="all" aria-pressed="true">Todos</button>{"".join(f'<button type="button" class="lfj-chip" data-tp="{p["key"]}" aria-pressed="false" style="--pc:{PARTY_COLOR[p["key"]]}">{e(p["label"])}</button>' for p in D["parties"])}</div>
<ol class="lfj-tl">{''.join(lis)}</ol><button type="button" class="lfj-btn lfj-btn--ghost lfj-showmore">Ver más declaraciones</button></section>"""


def block_method(D):
    bl = D["M"]["baseline"]
    return f"""<section class="lfj-sec lfj-method" id="metodologia"><details><summary>Metodología y fuentes</summary>
<ul>
<li><b>Qué calculamos:</b> el efecto directo de cada propuesta sobre una factura anual, con todo lo demás igual, frente a la ley vigente el 1 de enero de 2027 (IVA de la luz y el gas {bl["iva_luz_pct"]:g}%, impuesto eléctrico {str(round(bl["iee_pct"], 2)).replace(".", ",")}%, bono social {bl["bono_dto_vulnerable_pct"]:g}% para hogares vulnerables). No es una predicción de la factura futura.</li>
<li><b>Hogares:</b> hogar tipo con luz y gas en tarifa regulada; hogar vulnerable: el mismo hogar con bono social. Precios: media real del PVPC de 2021 a 2026. Las cifras grandes suman los cuatro años de legislatura (2027-2030).</li>
<li><b>Cifras:</b> sin símbolo = cifra dada por el partido; «≈» = derivada de una medida existente (por ejemplo, prorrogar un decreto). Sin propuesta cuantificada, se aplica la ley: 0 €. Si un partido rechaza expresamente una medida, vale 0 €. Las medidas que acaban antes de 2027 valen 0 €. El tope al gas muestra lo que ahorró la «excepción ibérica» en 2022.</li>
<li><b>Titular:</b> diferencia entre la propuesta más favorable y la menos favorable para el hogar tipo, solo con propuestas de los últimos 12 meses y sin ahorros aplazados (el tope de la TUR genera una deuda que se paga más adelante).</li>
<li><b>Quién cuenta:</b> declaraciones de la dirección nacional de cada partido y votaciones en el Congreso. Cada dato enlaza a su fuente original.</li>
<li><b>Correcciones:</b> {e(D["cfg"]["corrections_email"])}. Antes de publicar enviamos a cada partido sus cifras.</li>
</ul></details></section>"""


CSS = """
/* stile editoriale (tipo sezione dati di un quotidiano): serif nei titoli, sans neutro, cifre tabulari, filetti sottili */
.lfj-root{--p:#4a43d6;--ink:#111318;--ink2:#3a3d47;--mute:#6b6f7b;--line:#dcdde3;--rule:#111318;--bg:#f5f5f2;--save:#0b7a45;--cost:#b42318;
--serif:Montserrat,"Helvetica Neue",Arial,system-ui,sans-serif;--sans:Montserrat,"Helvetica Neue",Arial,system-ui,sans-serif;
color:var(--ink);font-family:var(--sans);line-height:1.5;font-variant-numeric:tabular-nums}
.lfj-root *{box-sizing:border-box}
.lfj-root h2{font-family:var(--serif);font-size:28px;line-height:34px;font-weight:700;margin:0 0 6px;letter-spacing:-.005em;padding-top:14px;border-top:3px solid var(--rule)}
.lfj-sec{margin:0 0 72px;scroll-margin-top:90px}
.lfj-lead{color:var(--ink2);margin:0 0 18px;max-width:760px;font-size:15px}
.lfj-hero{margin:0 0 64px}
.lfj-def{font-family:var(--serif);font-size:19px;line-height:28px;color:var(--ink2);max-width:760px;margin:0 0 18px}
.lfj-vul{font-size:17px;margin:0 0 8px;color:var(--ink2)}.lfj-vul b{color:#5a52ff;font-weight:800;font-size:26px;letter-spacing:-.01em}
.lfj-count{list-style:none;margin:22px 0 0;padding:14px 0 0;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:10px 40px}
.lfj-count li{display:flex;flex-direction:column}.lfj-count b{font-size:26px;line-height:30px;font-weight:700;letter-spacing:-.01em}
.lfj-count span{font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.06em}
.lfj-tw{overflow-x:auto;-webkit-overflow-scrolling:touch;border-top:2px solid var(--rule);border-bottom:1px solid var(--rule)}
.lfj-t{width:100%;border-collapse:collapse;font-size:14px;min-width:760px}
.lfj-t th,.lfj-t td{padding:12px 10px;border-top:1px solid var(--line);text-align:right;vertical-align:top}
.lfj-t thead th{border-top:0;background:#fff;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);vertical-align:bottom}
.lfj-teur thead th span{display:inline-block;border-bottom:2px solid var(--pc);padding-bottom:3px;color:var(--ink)}
.lfj-t tbody th{text-align:left;font-weight:400;min-width:210px;background:#fff;position:sticky;left:0}
.lfj-t tbody th b{font-weight:600}
.lfj-t tbody th small{display:block;color:var(--mute);font-size:12px}
.lfj-c b{display:block;font-size:19px;line-height:24px;font-weight:600;white-space:nowrap}
.lfj-c small{display:block;font-size:11px;line-height:15px;color:var(--mute)}
.lfj-c--save b{color:var(--save)}.lfj-c--cost b{color:var(--cost)}.lfj-c--zero b,.lfj-c--def b{color:var(--ink2)}.lfj-c--law b{color:#9a9ca6;font-weight:400}
.lfj-note{display:block!important;font-style:italic;color:var(--ink2)!important;margin-top:2px}
.lfj-how{margin-top:6px;font-size:11px}.lfj-how summary{cursor:pointer;color:var(--mute);list-style:none;display:inline-block;text-decoration:underline;text-underline-offset:2px}
.lfj-how summary:hover{color:var(--p)}.lfj-how summary::-webkit-details-marker{display:none}
.lfj-how[open]::before{content:"";position:fixed;inset:0;background:rgba(17,19,24,.45);z-index:9998}
.lfj-pop{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:min(480px,92vw);max-height:80vh;overflow:auto;background:#fff;border-top:3px solid var(--rule);padding:22px 24px 16px;z-index:9999;text-align:left;font-size:14px;line-height:1.55;color:var(--ink);box-shadow:0 18px 48px rgba(17,19,24,.25)}
.lfj-pop b{display:inline;font-size:inherit;line-height:inherit;color:inherit;font-weight:600;white-space:normal}
.lfj-pop p,.lfj-pop ul{margin:0 0 10px}.lfj-pop ul{padding-left:18px}.lfj-srcs{font-size:12px;color:var(--mute)}.lfj-srcs a{color:var(--p)}
.lfj-x{position:absolute;top:6px;right:10px;border:0;background:none;font-size:22px;line-height:1;cursor:pointer;color:var(--mute)}
.lfj-aff{min-width:150px;border-left:1px solid var(--line)}.lfj-aff b{display:block;font-size:17px;font-weight:600}.lfj-aff small{display:block;font-size:11px;color:var(--mute)}.lfj-aff a{font-size:11px;color:var(--mute)}
.lfj-tools{display:flex;gap:16px;align-items:center;margin:0 0 10px;flex-wrap:wrap;justify-content:flex-end}
.lfj-btn{font:inherit;font-size:13px;font-weight:600;border:1px solid var(--ink);background:#fff;color:var(--ink);border-radius:2px;padding:6px 12px;cursor:pointer;text-decoration:none;display:inline-block}
.lfj-btn:hover{background:var(--ink);color:#fff}.lfj-btn--ghost{border-color:var(--line)}.lfj-copied{font-size:12px;color:var(--save)}
.lfj-tq td{text-align:center}
.lfj-tg th{background:var(--bg)!important;text-align:left;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--ink);padding:10px 12px!important;position:static!important;border-top:1px solid var(--rule)!important}
.lfj-tg th small{font-weight:400;text-transform:none;letter-spacing:0;color:var(--mute);margin-left:10px}
.lfj-qr th[scope=row]{padding-left:28px!important}
.lfj-eurq{display:inline-block;margin-left:6px;border:1px solid var(--ink2);color:var(--ink2);border-radius:2px;font-size:10px;font-weight:600;padding:0 4px;line-height:15px;vertical-align:1px}
.lfj-a{font-size:13px;font-weight:600}.lfj-a--si{color:var(--save)}.lfj-a--no{color:var(--cost)}.lfj-a--amb{color:#8a6100}.lfj-a--nd{color:#a3a5ae;font-weight:400}
.lfj-foot{font-size:12px;color:var(--mute)}
.lfj-cara{border-bottom:1px solid var(--line);padding-bottom:20px}
.lfj-pick{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin:10px 0 18px}
.lfj-pick select{font:inherit;font-weight:600;font-size:16px;padding:8px 12px;border-radius:2px;border:1px solid var(--ink);background:#fff;min-width:170px}
.lfj-vs{color:var(--mute);font-size:13px;text-transform:uppercase}
.lfj-tcara{min-width:560px}.lfj-tcara td{font-size:17px;font-weight:600}
.lfj-tcara .lfj-neg{color:var(--save)}.lfj-tcara .lfj-pos{color:var(--cost)}.lfj-tcara .lfj-cd{font-size:14px;font-weight:400;color:var(--ink2)}
.lfj-total{font-size:19px;font-weight:700;margin:16px 0 4px}
.lfj-chips{display:flex;flex-wrap:wrap;gap:0;margin:0 0 18px;border-bottom:1px solid var(--line)}
.lfj-chip{font:inherit;font-size:13px;font-weight:600;padding:8px 14px;border:0;border-bottom:2px solid transparent;background:none;cursor:pointer;color:var(--mute);margin-bottom:-1px}
.lfj-chip[aria-pressed=true]{color:var(--ink);border-bottom-color:var(--pc,var(--ink))}
.lfj-tl{list-style:none;margin:0;padding:0}
.lfj-tl li{display:grid;grid-template-columns:96px 1fr;gap:18px;padding:14px 0;border-top:1px solid var(--line)}
.lfj-tl li.lfj-more{display:none}.lfj-tl.is-all li.lfj-more{display:grid}.lfj-tl li.lfj-off{display:none!important}
.lfj-when{font-size:12px;color:var(--mute);padding-top:3px;text-transform:uppercase;letter-spacing:.04em}
.lfj-meta{margin:0 0 4px;font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.05em}
.lfj-meta b{color:var(--ink);border-left:3px solid var(--pc);padding-left:6px}
.lfj-eur{display:inline-block;border:1px solid var(--ink2);color:var(--ink);padding:0 6px;font-weight:600;margin-left:8px;text-transform:none;letter-spacing:0}
.lfj-q{margin:0 0 4px;font-family:var(--serif);font-size:18px;line-height:26px}.lfj-q--ctx{font-family:var(--sans);font-size:14px;line-height:21px;color:var(--ink2)}
.lfj-who{margin:0;font-size:12px;color:var(--mute)}.lfj-who a{color:var(--mute)}
.lfj-showmore{margin:14px 0 0}
.lfj-method details{border-top:1px solid var(--rule);border-bottom:1px solid var(--line);padding:0}
.lfj-method summary{cursor:pointer;font-weight:600;padding:14px 0}.lfj-method li{font-size:14px;color:var(--ink2);margin-bottom:6px}
@media(max-width:700px){.lfj-root h2{font-size:23px;line-height:29px}.lfj-tl li{grid-template-columns:1fr;gap:2px}.lfj-c b{font-size:17px}.lfj-def{font-size:17px;line-height:25px}}
"""

JS = """<script>
setTimeout(function(){try{
var root=document.getElementById('lfj-root');if(!root)return;
/* copia tabella (HTML + testo) */
root.querySelectorAll('[data-lfj-copy]').forEach(function(b){b.addEventListener('click',function(){
 var t=document.getElementById(b.getAttribute('data-lfj-copy')),msg=b.parentNode.querySelector('.lfj-copied');
 var htmlT=t.outerHTML+'<p>Fuente: La factura en juego (papernest.es)</p>',txt=t.innerText;
 try{if(window.ClipboardItem&&navigator.clipboard&&navigator.clipboard.write){navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([htmlT],{type:'text/html'}),'text/plain':new Blob([txt],{type:'text/plain'})})])}
 else{var r=document.createRange();r.selectNode(t);var s=window.getSelection();s.removeAllRanges();s.addRange(r);document.execCommand('copy');s.removeAllRanges()}
 if(msg){msg.textContent='Tabla copiada';setTimeout(function(){msg.textContent=''},2000)}}catch(err){}})});
/* cara a cara */
var D=JSON.parse(document.getElementById('lfj-cara-data').textContent),A=document.getElementById('lfj-ca'),Bs=document.getElementById('lfj-cb');
function f(v){if(v===null||v===undefined)return'—';var a=Math.abs(Math.round(v));return (v<0?'−':v>0?'+':'')+String(a).replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.')+' €'}
function star(fl){return (fl||[]).some(function(x){return x==='duracion_no_definida'||x==='propuesta_antigua'})?' *':''}
function cara(){var a=A.value,b=Bs.value,tot=0,ok=0;root.querySelector('.lfj-ha').textContent=D.labels[a];root.querySelector('.lfj-hb').textContent=D.labels[b];
 root.querySelectorAll('.lfj-tcara tbody tr').forEach(function(tr){var k=tr.getAttribute('data-k'),va=D.eff[a][k],vb=D.eff[b][k];
  [['.lfj-ca',va,a],['.lfj-cb',vb,b]].forEach(function(x){var td=tr.querySelector(x[0]);td.textContent=f(x[1])+star(D.flags[x[2]][k]);
   td.className=x[0].slice(1)+(x[1]<-0.5?' lfj-neg':x[1]>0.5?' lfj-pos':'')});
  var ex=function(fl){return (fl||[]).some(function(x){return x==='aplazado'||x==='referencia_2022'||x==='sin_tope'})};
  var defer=ex(D.flags[a][k])||ex(D.flags[b][k]); /* TUR e riferimento 2022: mostrati, fuori dal totale */
  if(va===null||vb===null||va===undefined||vb===undefined){tr.querySelector('.lfj-cd').textContent='no comparable'}
  else{var d=vb-va; /* d>0: con B pagas más -> A es más barato */
   tr.querySelector('.lfj-cd').textContent=Math.round(d)===0?'igual':(f(Math.abs(d)).replace(/^[−+]/,'')+' menos con '+(d>0?D.labels[a]:D.labels[b]));
   if(!defer){tot+=d;ok++}}});
 var p=root.querySelector('.lfj-total');p.textContent=ok?('En total, '+(tot===0?'la misma factura':(f(Math.abs(tot)).replace(/^[−+]/,'')+' menos en la legislatura con '+(tot>0?D.labels[a]:D.labels[b])))+' (solo partidas comparables, sin ahorros aplazados).'):'No hay partidas comparables entre estos dos partidos.'}
A.addEventListener('change',cara);Bs.addEventListener('change',cara);cara();
var tl=root.querySelector('.lfj-tl'),sm=root.querySelector('.lfj-showmore');
if(sm){sm.addEventListener('click',function(){tl.classList.add('is-all');sm.remove()})}
/* filtro partiti nelle dichiarazioni: filtrando si mostrano tutte quelle del partito */
root.querySelectorAll('.lfj-chip').forEach(function(c){c.addEventListener('click',function(){var v=c.getAttribute('data-tp');
 root.querySelectorAll('.lfj-chip').forEach(function(x){x.setAttribute('aria-pressed',x===c?'true':'false')});
 tl.querySelectorAll('li').forEach(function(li){li.classList.toggle('lfj-off',v!=='all'&&li.getAttribute('data-p')!==v)});
 if(v!=='all'){tl.classList.add('is-all');if(sm)sm.style.display='none'}})});
/* popup "Cómo se calcula": uno alla volta, chiusura con ×, clic fuori o Esc */
var hows=root.querySelectorAll('.lfj-how');function closeAll(ex){hows.forEach(function(d){if(d!==ex)d.removeAttribute('open')})}
hows.forEach(function(d){d.addEventListener('toggle',function(){if(d.open)closeAll(d)});d.querySelector('.lfj-x').addEventListener('click',function(){d.removeAttribute('open')})});
document.addEventListener('click',function(ev){if(!ev.target.closest('.lfj-pop')&&!ev.target.closest('.lfj-how summary'))closeAll(null)});
document.addEventListener('keydown',function(ev){if(ev.key==='Escape')closeAll(null)});
}catch(err){if(window.console)console.warn('lfj',err)}},300);
</script>"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    D = load_all()
    D["M"]["_profiles"] = {"hogar_tipo": "hogar tipo", "hogar_vulnerable": "hogar vulnerable"}
    title, hero = block_hero(D)
    inner = hero + block_euro(D) + block_questions(D) + block_cara(D) + block_timeline(D) + block_method(D)
    testo = f'<!-- wp:html -->\n<div class="lfj-root" id="lfj-root"><style>{CSS}</style>\n{inner}\n</div>\n{JS}\n<!-- /wp:html -->\n'
    intro = (f'<!-- wp:paragraph -->\n<p class="lfj-kicker-wp" style="font-size:13px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#5a52ff;margin:0 0 8px">'
             f'La factura en juego · Elecciones 29N</p>\n<!-- /wp:paragraph -->\n\n'
             f'<!-- wp:heading {{"level":1}} -->\n<h1 class="wp-block-heading">{re.sub(r"(\d[\d.]* €)", r'<strong><mark style="background-color:rgba(0,0,0,0);color:#5a52ff" class="has-inline-color">\1</mark></strong>', e(title), count=1)}</h1>\n<!-- /wp:heading -->\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "codice_intro.html").write_text(intro, encoding="utf-8")
    (OUT / "codice_testo.html").write_text(testo, encoding="utf-8")
    prev = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap"><title>La factura en juego</title>'
            f'<style>body{{margin:0;padding:32px 16px;font-family:Montserrat,"Helvetica Neue",Arial,system-ui,sans-serif;background:#fff;color:#111318}}'
            f'.wrap{{max-width:1120px;margin:0 auto}}h1{{font-family:Montserrat,"Helvetica Neue",Arial,system-ui,sans-serif;font-size:46px;line-height:52px;font-weight:700;margin:0 0 14px;letter-spacing:-.01em;max-width:900px}}'
            f'@media(max-width:700px){{h1{{font-size:32px;line-height:36px}}}}</style></head><body><div class="wrap">'
            f'{intro.replace("<!-- wp:", "<!-- ").replace("<!-- /wp:", "<!-- /")}{testo}</div></body></html>')
    (OUT / "preview.html").write_text(prev, encoding="utf-8")
    print(f"📝 {title}\n   output/factura/codice_intro.html + codice_testo.html + preview.html")


if __name__ == "__main__":
    main()

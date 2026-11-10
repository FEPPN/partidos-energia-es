"""5 concept visuali "liberi" per la pagina HUB (round 2, 8 ott 2026).

Diego: "piena libertà, mi interessa UX/UI e grafica". Unici punti fermi: dati reali, neutralità (citazione letterale
+ fonte sempre raggiungibile), niente foto dei politici (diritti), font papernest.

06 Tira y afloja   - ogni domanda è un tiro alla fune: i partiti tirano verso Sí o No
07 Revista          - magazine editoriale, scrollytelling con domanda sticky e pull-quote giganti
08 Stories          - formato Instagram: copertine 9:16 per tema, player a tutto schermo
09 Cronograma       - data art: tutte le dichiarazioni nel tempo, corsie per partito, filtro tema
10 Afinidad         - chi somiglia a chi: rete + mappa di calore delle coincidenze

Uso:   py scripts/hub_proposals_free.py
"""
import json
import math
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402
from hub_proposals import ANS, PARTY_COLOR, OUT, best_item, e, headline, load, page, src  # noqa: E402

LABEL_ON_DARK = {"PODEMOS": "#c08ad6", "SALF": "#e8e8f5", "PP": "#5b9be6"}  # colori partito schiariti per fondi scuri

MIN_N = 3  # sotto 3 domande confrontabili non mostriamo un'affinità
ABBR = {"PSOE": "PSOE", "PP": "PP", "VOX": "VOX", "SUMAR": "SUM", "PODEMOS": "POD", "SALF": "SALF"}
SI, NO, AMB = "#16a864", "#ea4249", "#f0a91b"


def stance_color(s):
    return {"a_favor": SI, "en_contra": NO, "ambiguo": AMB}.get(s, "#9a9cae")


def proof_html(D, p, t, limit=None):
    s, items = best_item(D, p, t)
    items = items[:limit] if limit else items
    if not items:
        return '<p class="pf-empty">Sin declaraciones de la dirección nacional desde agosto de 2023.</p>'
    return "".join(f'<div class="pf"><span class="pf-d">{e(B.fdate(x["date"], True))}</span><p class="pf-q">{headline(x, True)}</p>'
                   f'<p class="pf-w">{e(x["person"])} · {src(x)}</p></div>' for x in items)


PROOF_CSS = """
.pf{padding:8px 0;border-top:1px solid rgba(0,0,0,.08)}.pf:first-child{border-top:0}
.pf-d{font-size:11px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;opacity:.6}
.pf-q{margin:2px 0 4px;font-weight:800;font-size:14px;line-height:20px}.pf-w{margin:0;font-size:12px;opacity:.75}
.pf-empty{margin:0;font-size:13px;font-style:italic;opacity:.7}
"""


# ================================================================= 06 TIRA Y AFLOJA

def v6_tira(D):
    P, T = D["parties"], D["topics"]
    rows = []
    for t in T:
        groups = {"en_contra": [], "ambiguo": [], "a_favor": [], "bench": []}
        for p in P:
            b = D["badges"][(p["key"], t["key"])]["badge"]
            groups[b if b in ("en_contra", "ambiguo", "a_favor") else "bench"].append(p)
        zones = {"en_contra": (2, 31), "ambiguo": (36, 64), "a_favor": (69, 98)}
        tokens = []
        for z, (x0, x1) in zones.items():
            ps = groups[z]
            for k, p in enumerate(ps):
                x = x0 + (k + 1) * (x1 - x0) / (len(ps) + 1)
                tokens.append(f'<button class="ty-tok{" ty-tok--up" if k % 2 == 0 and len(ps) > 1 else " ty-tok--down" if len(ps) > 1 else ""}" style="--x:{x:.1f}%;--pc:{PARTY_COLOR[p["key"]]}" data-pop="pop-{p["slug"]}-{t["key"]}">{e(ABBR[p["key"]])}</button>'
                              f'<div class="ty-pop hp-hide" id="pop-{p["slug"]}-{t["key"]}" style="--x:{min(max(x, 18), 82):.1f}%"><div class="ty-pop__h"><b>{e(p["label"])}</b>'
                              f'<span class="ty-ans ty-ans--{ANS[z][1]}">{e(ANS[z][0])}</span></div>{proof_html(D, p, t, 3)}</div>')
        bench = "".join(f'<button class="ty-bench" style="--pc:{PARTY_COLOR[p["key"]]}" data-pop="pop-{p["slug"]}-{t["key"]}">{e(ABBR[p["key"]])}</button>'
                        f'<div class="ty-pop ty-pop--b hp-hide" id="pop-{p["slug"]}-{t["key"]}" style="--x:50%"><div class="ty-pop__h"><b>{e(p["label"])}</b></div>{proof_html(D, p, t, 3)}</div>'
                        for p in groups["bench"])
        if t["proposition"]:
            n_no, n_si = len(groups["en_contra"]), len(groups["a_favor"])
            lead = "si" if n_si > n_no else "no" if n_no > n_si else "eq"
            rows.append(f'''<section class="ty-row" id="{t["key"]}" data-lead="{lead}">
<h2>{e(t["question_short"])}</h2>
<div class="ty-arena"><span class="ty-end ty-end--no"><b>{n_no}</b>NO</span>
<div class="ty-track"><div class="ty-rope"></div><div class="ty-knot"></div><span class="ty-zl" style="left:16%">en contra</span><span class="ty-zl" style="left:50%">ambiguo</span><span class="ty-zl" style="left:84%">a favor</span>{"".join(tokens)}</div>
<span class="ty-end ty-end--si"><b>{n_si}</b>SÍ</span></div>
{f'<div class="ty-benchrow"><span>En el banquillo (sin declaraciones):</span>{bench}</div>' if groups["bench"] else ""}
</section>''')
        else:
            allp = "".join(f'<button class="ty-bench" style="--pc:{PARTY_COLOR[p["key"]]}" data-pop="pop-{p["slug"]}-{t["key"]}">{e(ABBR[p["key"]])}</button>'
                           f'<div class="ty-pop ty-pop--b hp-hide" id="pop-{p["slug"]}-{t["key"]}" style="--x:50%"><div class="ty-pop__h"><b>{e(p["label"])}</b></div>{proof_html(D, p, t, 3)}</div>'
                           for p in P)
            rows.append(f'<section class="ty-row ty-row--free" id="{t["key"]}"><h2>{e(t["question_short"])}</h2><p class="ty-free">Aquí no hay cuerda: no es una pregunta de sí o no. Pulsa un partido para leer lo que ha dicho.</p><div class="ty-benchrow">{allp}</div></section>')
    body = f"""
<header class="ty-top"><div class="hp-wrap"><b>[NOMBRE TOOL]</b> · Elecciones 29N · <b>Faltan {D['days_left']} días</b></div></header>
<section class="ty-hero hp-wrap"><p class="ty-k">Energía y elecciones</p><h1>Tira y afloja</h1>
<p class="ty-lead">11 preguntas sobre la luz, el gas y la energía. En cada una, los partidos tiran hacia el <b class="c-si">sí</b> o hacia el <b class="c-no">no</b> según lo que han dicho y votado desde 2023. Pulsa una ficha para ver las pruebas.</p></section>
<main class="hp-wrap">{''.join(rows)}</main>
<footer class="ty-foot hp-wrap">Solo dirección nacional y votaciones en el Congreso, desde agosto de 2023 · Texto literal y fuente en cada dato · {D['n']} datos verificados</footer>"""
    css = PROOF_CSS + f"""
body{{background:#f6f2ea}}
.ty-top{{font-size:13px;padding:12px 0;border-bottom:1px solid #e4dccd;color:#5b5446}}
.ty-hero{{padding-top:48px;padding-bottom:16px;text-align:center}}
.ty-k{{text-transform:uppercase;letter-spacing:.2em;font-weight:800;font-size:12px;color:var(--hp-p);margin:0}}
.ty-hero h1{{font-size:96px;line-height:96px;margin:8px 0 16px;letter-spacing:-.04em;font-weight:900}}
.ty-lead{{max-width:640px;margin:0 auto;font-size:18px;color:#4a4436}}.c-si{{color:{SI}}}.c-no{{color:{NO}}}
.ty-row{{background:#fffdf8;border:1px solid #e9e1d1;border-radius:24px;padding:28px 28px 22px;margin:28px 0;box-shadow:0 2px 0 #e9e1d1}}
.ty-row h2{{text-align:center;font-size:24px;line-height:30px;margin:0 0 22px}}
.ty-arena{{display:grid;grid-template-columns:72px 1fr 72px;align-items:center;gap:8px}}
.ty-end{{display:flex;flex-direction:column;align-items:center;font-weight:900;font-size:13px;letter-spacing:.12em}}
.ty-end b{{font-size:44px;line-height:44px;letter-spacing:0}}
.ty-end--no{{color:{NO}}}.ty-end--si{{color:{SI}}}
.ty-track{{position:relative;height:120px;border-radius:60px;background:linear-gradient(90deg,{NO}14 0 33%,{AMB}14 33% 67%,{SI}14 67% 100%)}}
.ty-rope{{position:absolute;left:0;right:0;top:50%;height:6px;margin-top:-3px;background:repeating-linear-gradient(45deg,#b89b6a 0 6px,#d9bf8f 6px 12px);border-radius:3px}}
.ty-knot{{position:absolute;top:50%;left:50%;width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;background:var(--hp-p);transition:left .9s cubic-bezier(.2,.8,.2,1)}}
.ty-row[data-lead=si].is-in .ty-knot{{left:58%}}.ty-row[data-lead=no].is-in .ty-knot{{left:42%}}
.ty-zl{{position:absolute;bottom:8px;transform:translateX(-50%);font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:#8a8170;font-weight:800}}
.ty-tok{{position:absolute;top:50%;left:50%;width:54px;height:54px;margin:-27px 0 0 -27px;border-radius:50%;border:4px solid var(--pc);background:#fff;font:inherit;font-weight:900;font-size:12px;cursor:pointer;
  box-shadow:0 6px 14px rgba(60,40,10,.18);transition:left .9s cubic-bezier(.2,.8,.2,1),transform .15s;z-index:2}}
.ty-row.is-in .ty-tok{{left:var(--x)}}.ty-tok:hover,.ty-tok.is-on{{transform:scale(1.12)}}.ty-tok.is-on{{background:var(--pc);color:#fff}}
.ty-pop{{position:relative;left:var(--x);transform:translateX(-50%);width:min(380px,92%);background:#fff;border:1px solid #e4dccd;border-radius:16px;padding:14px 16px;margin-top:14px;box-shadow:0 18px 40px rgba(60,40,10,.15)}}
.ty-pop--b{{left:50%}}
.ty-pop__h{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
.ty-ans{{font-weight:900;font-size:12px;padding:3px 10px;border-radius:999px;color:#fff}}.ty-ans--si{{background:{SI}}}.ty-ans--no{{background:{NO}}}.ty-ans--amb{{background:{AMB}}}
.ty-benchrow{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:center;margin-top:16px;font-size:13px;color:#8a8170}}
.ty-bench{{font:inherit;font-weight:900;font-size:11px;padding:6px 10px;border-radius:999px;border:2px dashed var(--pc);background:transparent;cursor:pointer;opacity:.75}}
.ty-bench.is-on{{opacity:1;border-style:solid}}
.ty-free{{text-align:center;color:#8a8170;margin:-10px 0 0}}
.ty-foot{{text-align:center;font-size:13px;color:#8a8170;padding:24px 16px 80px}}
@media(max-width:700px){{.ty-hero h1{{font-size:56px;line-height:56px}}.ty-arena{{grid-template-columns:40px 1fr 40px}}.ty-end b{{font-size:28px;line-height:28px}}
.ty-tok{{width:36px;height:36px;margin:-18px 0 0 -18px;font-size:8px;border-width:3px}}.ty-track{{height:140px}}.ty-tok--up{{top:30%}}.ty-tok--down{{top:70%}}.ty-row{{padding:20px 12px}}.ty-row h2{{font-size:19px;line-height:25px}}.ty-zl{{display:none}}}}
"""
    js = """
var io=new IntersectionObserver(function(es){es.forEach(function(en){if(en.isIntersecting){en.target.classList.add('is-in');io.unobserve(en.target)}})},{threshold:.35});
document.querySelectorAll('.ty-row').forEach(function(r){io.observe(r)});
/* fallback: se l'osservatore non scatta (iframe, browser vecchi, plugin), posiziona comunque le fiche */
setTimeout(function(){if(!document.querySelector('.ty-row.is-in')){document.querySelectorAll('.ty-row').forEach(function(r){r.classList.add('is-in')})}},1500);
document.querySelectorAll('[data-pop]').forEach(function(b){b.addEventListener('click',function(){var row=b.closest('.ty-row'),pop=document.getElementById(b.dataset.pop),was=!pop.classList.contains('hp-hide');
 row.querySelectorAll('.ty-pop').forEach(function(x){x.classList.add('hp-hide')});row.querySelectorAll('[data-pop]').forEach(function(x){x.classList.remove('is-on')});
 if(!was){pop.classList.remove('hp-hide');b.classList.add('is-on')}})});
"""
    return page("06 · Tira y afloja", css, body, js)


# ================================================================= 07 REVISTA

def v7_revista(D):
    P, T, today = D["parties"], D["topics"], D["today"]
    toc = "".join(f'<li><a href="#{t["key"]}"><span class="rv-n">{i:02d}</span><span class="rv-tt">{e(t["label_short"])}</span>'
                  f'<span class="rv-dots">' + "".join(f'<i style="background:{stance_color(D["badges"][(p["key"], t["key"])]["badge"])}"></i>' for p in P) + '</span></a></li>'
                  for i, t in enumerate(T, 1))
    spreads = []
    for i, t in enumerate(T, 1):
        tally = {}
        for p in P:
            tally[D["badges"][(p["key"], t["key"])]["badge"]] = tally.get(D["badges"][(p["key"], t["key"])]["badge"], 0) + 1
        quotes = []
        for p in P:
            b = D["badges"][(p["key"], t["key"])]["badge"]
            s, items = best_item(D, p, t)
            if not s:
                quotes.append(f'<figure class="rv-q rv-q--empty"><figcaption><b style="color:{PARTY_COLOR[p["key"]]}">{e(p["label_long"])}</b></figcaption><p>Sin declaraciones de su dirección nacional desde agosto de 2023.</p></figure>')
                continue
            body_q = f'<blockquote>{e(s["quote"])}</blockquote>' if s.get("quote") else f'<blockquote class="rv-ctx">{headline(s, True)}</blockquote>'
            tag = f'<span class="rv-tag" style="background:{stance_color(b)}">{e(ANS[b][0])}</span>' if t["proposition"] and b in ("a_favor", "en_contra", "ambiguo") else ""
            quotes.append(f'<figure class="rv-q"><figcaption><b style="color:{PARTY_COLOR[p["key"]]}">{e(p["label_long"])}</b>{tag}</figcaption>{body_q}'
                          f'<p class="rv-by">— {e(s["person"])}, {e(s["role"])}. {src(s)}</p></figure>')
        tal = (f'<p class="rv-tally"><b style="color:{SI}">{tally.get("a_favor", 0)} sí</b> · <b style="color:{NO}">{tally.get("en_contra", 0)} no</b> · '
               f'<b style="color:{AMB}">{tally.get("ambiguo", 0)} ambiguo</b></p>') if t["proposition"] else '<p class="rv-tally">Tema abierto: sin pregunta de sí o no</p>'
        spreads.append(f'''<section class="rv-spread{" rv-spread--alt" if i % 2 == 0 else ""}" id="{t["key"]}"><div class="rv-in">
<div class="rv-side"><div class="rv-sticky"><span class="rv-big">{i:02d}</span><p class="rv-cat">{e(D["groups"][t["group"]])}</p><h2>{e(t["question_short"])}</h2>{tal}</div></div>
<div class="rv-quotes">{"".join(quotes)}</div></div></section>''')
    body = f"""
<header class="rv-mast"><div class="rv-in rv-mast__in"><span>[NOMBRE TOOL]</span><span>Edición 29N · {e(B.fdate(today))}</span><span>Faltan {D['days_left']} días</span></div></header>
<section class="rv-cover"><div class="rv-in"><p class="rv-kick">Especial elecciones generales</p>
<h1>Lo que dicen.<br><em>Lo que votan.</em></h1>
<p class="rv-deck">Las posiciones de PSOE, PP, Vox, Sumar, Podemos y SALF sobre la luz, el gas y la energía, contadas con sus propias palabras. {D['n']} declaraciones y votaciones, cada una con su fuente.</p></div></section>
<nav class="rv-toc"><div class="rv-in"><h3>En este número</h3><ol>{toc}</ol>
<p class="rv-leg"><i style="background:{SI}"></i>sí <i style="background:{NO}"></i>no <i style="background:{AMB}"></i>ambiguo <i style="background:#9a9cae"></i>sin datos o sin pregunta</p></div></nav>
{''.join(spreads)}
<footer class="rv-colo"><div class="rv-in"><h3>Colofón</h3><p>Recopilamos declaraciones de la dirección nacional de cada partido y sus votaciones en el Congreso desde el 17 de agosto de 2023. Citamos siempre el texto literal y enlazamos la fuente. No valoramos programas ni recomendamos el voto. Correcciones: [EMAIL CORRECCIONES].</p></div></footer>"""
    css = PROOF_CSS + f"""
body{{background:#fbfaf6;color:#111}}
.rv-in{{max-width:1180px;margin:0 auto;padding:0 20px}}
.rv-mast{{border-bottom:3px double #111;font-size:12px;text-transform:uppercase;letter-spacing:.14em;font-weight:800}}
.rv-mast__in{{display:flex;justify-content:space-between;padding-top:12px;padding-bottom:10px;gap:12px;flex-wrap:wrap}}
.rv-cover{{padding:72px 0 56px;border-bottom:1px solid #111}}
.rv-kick{{font-size:13px;text-transform:uppercase;letter-spacing:.2em;font-weight:800;color:var(--hp-p);margin:0 0 12px}}
.rv-cover h1{{font-family:Georgia,"Times New Roman",serif;font-weight:400;font-size:112px;line-height:.95;letter-spacing:-.03em;margin:0 0 28px}}
.rv-cover h1 em{{color:var(--hp-p)}}
.rv-deck{{font-family:Georgia,serif;font-size:22px;line-height:32px;max-width:760px;margin:0;color:#333}}
.rv-toc{{padding:40px 0;border-bottom:1px solid #111}}.rv-toc h3{{font-size:12px;text-transform:uppercase;letter-spacing:.16em;margin:0 0 16px}}
.rv-toc ol{{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,1fr);gap:0 32px}}
.rv-toc a{{display:grid;grid-template-columns:40px 1fr auto;gap:10px;align-items:center;padding:10px 0;border-top:1px solid #ddd;color:#111;text-decoration:none}}
.rv-toc a:hover .rv-tt{{color:var(--hp-p)}}
.rv-n{{font-family:Georgia,serif;font-size:22px;color:var(--hp-p)}}.rv-tt{{font-weight:800}}
.rv-dots{{display:flex;gap:3px}}.rv-dots i,.rv-leg i{{width:9px;height:9px;border-radius:50%;display:inline-block}}
.rv-leg{{font-size:12px;color:#666;display:flex;gap:6px 10px;align-items:center;flex-wrap:wrap;margin:16px 0 0}}
.rv-spread{{padding:72px 0;border-bottom:1px solid #111}}.rv-spread--alt{{background:#111;color:#f3f1ea}}
.rv-spread .rv-in{{display:grid;grid-template-columns:400px 1fr;gap:56px}}
.rv-sticky{{position:sticky;top:32px}}
.rv-big{{font-family:Georgia,serif;font-size:140px;line-height:1;color:var(--hp-p);display:block}}
.rv-cat{{text-transform:uppercase;letter-spacing:.16em;font-size:12px;font-weight:800;margin:8px 0}}
.rv-side h2{{font-family:Georgia,serif;font-weight:400;font-size:36px;line-height:42px;margin:0 0 16px}}
.rv-tally{{font-size:15px}}
.rv-q{{margin:0 0 44px;padding:0 0 32px;border-bottom:1px solid rgba(127,127,127,.3)}}
.rv-q figcaption{{display:flex;gap:10px;align-items:center;font-size:13px;text-transform:uppercase;letter-spacing:.12em;margin-bottom:10px}}
.rv-tag{{color:#fff;font-weight:900;padding:2px 10px;border-radius:999px;letter-spacing:.06em}}
.rv-q blockquote{{font-family:Georgia,serif;font-size:30px;line-height:40px;margin:0 0 12px;position:relative;padding-left:36px}}
.rv-q blockquote:before{{content:"“";position:absolute;left:0;top:-14px;font-size:72px;color:var(--hp-p);line-height:1}}
.rv-q blockquote.rv-ctx{{font-size:20px;line-height:28px;font-style:italic}}
.rv-by{{font-size:14px;opacity:.75;margin:0}}.rv-spread--alt .hp-src{{color:#ccc;border-color:#444}}
.rv-q--empty p{{font-family:Georgia,serif;font-style:italic;font-size:18px;opacity:.6;margin:0}}
.rv-colo{{padding:48px 0 80px}}.rv-colo h3{{font-size:12px;text-transform:uppercase;letter-spacing:.16em}}.rv-colo p{{font-family:Georgia,serif;font-size:17px;max-width:760px}}
@media(max-width:900px){{.rv-cover h1{{font-size:58px}}.rv-toc ol{{grid-template-columns:1fr}}.rv-spread .rv-in{{grid-template-columns:1fr;gap:16px}}
.rv-sticky{{position:static}}.rv-big{{font-size:80px}}.rv-q blockquote{{font-size:22px;line-height:30px}}.rv-side h2{{font-size:28px;line-height:34px}}}}
"""
    return page("07 · Revista", css, body, "")


# ================================================================= 08 STORIES

def v8_stories(D):
    P, T = D["parties"], D["topics"]
    covers, data = [], {}
    grad = {"factura": "linear-gradient(160deg,#5a52ff,#2a1f8f)", "modelo": "linear-gradient(160deg,#141433,#3b2f9e)"}
    for t in T:
        dots = "".join(f'<i style="background:{stance_color(D["badges"][(p["key"], t["key"])]["badge"])}"></i>' for p in P)
        covers.append(f'<button class="st-cover" data-t="{t["key"]}" style="background:{grad[t["group"]]}"><span class="st-cat">{e(D["groups"][t["group"]])}</span>'
                      f'<span class="st-q">{e(t["question_short"])}</span><span class="st-dots">{dots}</span><span class="st-play">▶ Ver</span></button>')
        frames = []
        for p in P:
            b = D["badges"][(p["key"], t["key"])]["badge"]
            s, items = best_item(D, p, t)
            frames.append({"party": p["label_long"], "color": PARTY_COLOR[p["key"]],
                           "ans": ANS[b][0] if t["proposition"] else "", "ansColor": stance_color(b),
                           "quote": (s.get("quote") or headline(s, True)) if s else "Sin declaraciones de su dirección nacional desde agosto de 2023.",
                           "isQuote": bool(s and s.get("quote")),
                           "who": f'{s["person"]} · {B.fdate(s["date"], True)}' if s else "", "src": s["source_name"] if s else "", "url": s["source_url"] if s else ""})
        data[t["key"]] = {"q": t["question_short"], "frames": frames}
    rail = "".join(f'<button class="st-ring" data-t="{t["key"]}"><span style="background:{grad[t["group"]]}">{e(t["label_short"][:2].upper())}</span><small>{e(t["label_short"])}</small></button>' for t in T)
    body = f"""
<header class="st-top"><div class="hp-wrap st-top__in"><b>[NOMBRE TOOL]</b><span>Faltan {D['days_left']} días para el 29N</span></div></header>
<div class="st-rail hp-wrap">{rail}</div>
<section class="hp-wrap st-hero"><h1>La energía, en stories</h1><p>Una pregunta por story. Seis partidos. Lo que han dicho, con su fuente. Toca una portada para empezar.</p></section>
<main class="hp-wrap st-grid">{''.join(covers)}</main>
<div class="st-player hp-hide" role="dialog" aria-modal="true"><div class="st-phone">
<div class="st-bars"></div><button class="st-x" aria-label="Cerrar">×</button>
<div class="st-frame"><p class="st-fq"></p><p class="st-party"></p><p class="st-ans"></p><blockquote class="st-quote"></blockquote><p class="st-who"></p><a class="st-src" target="_blank" rel="noopener"></a></div>
<button class="st-nav st-prev" aria-label="Anterior"></button><button class="st-nav st-next" aria-label="Siguiente"></button></div></div>
<noscript><p class="hp-wrap">Activa JavaScript para ver las stories.</p></noscript>"""
    css = """
body{background:#0c0c1d;color:#fff}
.st-top{font-size:13px;color:#b9b8d9}.st-top__in{display:flex;justify-content:space-between;padding-top:14px;padding-bottom:14px}.st-top b{color:#fff}
.st-rail{display:flex;gap:14px;overflow-x:auto;padding-bottom:12px;scrollbar-width:none}
.st-ring{background:none;border:0;color:#fff;font:inherit;display:flex;flex-direction:column;align-items:center;gap:6px;cursor:pointer;flex:none;width:76px}
.st-ring span{width:66px;height:66px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:18px;
 box-shadow:0 0 0 3px #0c0c1d,0 0 0 6px #ff4fd8;background-clip:padding-box}
.st-ring small{font-size:11px;color:#cfcde8;text-align:center;line-height:13px}
.st-hero{padding-top:28px;padding-bottom:20px}.st-hero h1{font-size:64px;line-height:64px;margin:0 0 10px;letter-spacing:-.03em;
 background:linear-gradient(90deg,#fff,#a9a6ff,#ff8be7);-webkit-background-clip:text;background-clip:text;color:transparent}
.st-hero p{color:#b9b8d9;font-size:18px;margin:0}
.st-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;padding-top:16px;padding-bottom:80px}
.st-cover{aspect-ratio:9/16;border:0;border-radius:22px;color:#fff;font:inherit;text-align:left;padding:18px;display:flex;flex-direction:column;cursor:pointer;
 position:relative;overflow:hidden;transition:transform .2s,box-shadow .2s;box-shadow:0 10px 30px rgba(0,0,0,.4)}
.st-cover:hover{transform:translateY(-4px) rotate(-.5deg);box-shadow:0 18px 40px rgba(90,82,255,.45)}
.st-cover:after{content:"";position:absolute;right:-40px;top:-40px;width:160px;height:160px;border-radius:50%;background:rgba(255,255,255,.08)}
.st-cat{font-size:11px;text-transform:uppercase;letter-spacing:.14em;font-weight:800;opacity:.8}
.st-q{font-weight:900;font-size:22px;line-height:27px;margin-top:auto}
.st-dots{display:flex;gap:5px;margin:14px 0 10px}.st-dots i{width:14px;height:14px;border-radius:50%;box-shadow:0 0 0 2px rgba(255,255,255,.3)}
.st-play{font-size:13px;font-weight:800;opacity:.85}
.st-player{position:fixed;inset:0;background:rgba(5,5,15,.88);backdrop-filter:blur(6px);display:flex;align-items:center;justify-content:center;z-index:100}
.st-phone{position:relative;width:min(420px,100vw);height:min(760px,100vh);border-radius:28px;overflow:hidden;background:var(--fc,#333);transition:background .4s}
.st-phone:before{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.15),rgba(0,0,0,.55))}
.st-bars{position:absolute;top:12px;left:12px;right:52px;display:flex;gap:4px;z-index:3}
.st-bars i{flex:1;height:3px;border-radius:2px;background:rgba(255,255,255,.35);overflow:hidden}.st-bars i b{display:block;height:100%;width:0;background:#fff}
.st-bars i.done b{width:100%}.st-bars i.run b{animation:fill 6s linear forwards}@keyframes fill{to{width:100%}}
.st-x{position:absolute;top:4px;right:10px;z-index:4;background:none;border:0;color:#fff;font-size:34px;cursor:pointer}
.st-frame{position:absolute;inset:0;padding:56px 28px 32px;display:flex;flex-direction:column;z-index:2}
.st-fq{font-size:14px;font-weight:800;opacity:.85;margin:0}
.st-party{font-size:38px;line-height:40px;font-weight:900;margin:auto 0 8px}
.st-ans{font-size:88px;line-height:80px;font-weight:900;margin:0 0 18px;letter-spacing:-.04em}
.st-quote{font-family:Georgia,serif;font-size:22px;line-height:30px;margin:0 0 14px}
.st-who{font-size:13px;opacity:.85;margin:0 0 8px}.st-src{color:#fff;font-size:13px;font-weight:800}
.st-nav{position:absolute;top:0;bottom:0;width:35%;background:none;border:0;cursor:pointer;z-index:3}.st-prev{left:0}.st-next{right:0}
@media(max-width:600px){.st-hero h1{font-size:40px;line-height:42px}.st-grid{grid-template-columns:repeat(2,1fr)}.st-q{font-size:17px;line-height:22px}.st-phone{border-radius:0}}
"""
    js = """
var DATA=%s,keys=Object.keys(DATA),cur=null,idx=0,timer=null;
var pl=document.querySelector('.st-player'),ph=document.querySelector('.st-phone'),bars=document.querySelector('.st-bars');
function render(){var f=DATA[cur].frames[idx];ph.style.setProperty('--fc',f.color);
 document.querySelector('.st-fq').textContent=DATA[cur].q;document.querySelector('.st-party').textContent=f.party;
 var a=document.querySelector('.st-ans');a.textContent=f.ans;a.style.color=f.ans?'#fff':'';a.style.textShadow=f.ans?'0 0 0 #000, 0 6px 0 '+f.ansColor:'';
 var q=document.querySelector('.st-quote');q.textContent=f.isQuote?('«'+f.quote+'»'):f.quote;
 document.querySelector('.st-who').textContent=f.who;var s=document.querySelector('.st-src');s.textContent=f.src?('Fuente: '+f.src+' ↗'):'';if(f.url){s.href=f.url}else{s.removeAttribute('href')}
 bars.innerHTML='';DATA[cur].frames.forEach(function(_,i){var el=document.createElement('i');el.innerHTML='<b></b>';if(i<idx)el.className='done';if(i===idx)el.className='run';bars.appendChild(el)});
 clearTimeout(timer);timer=setTimeout(next,6000)}
function open(k){cur=k;idx=0;pl.classList.remove('hp-hide');render()}
function close(){pl.classList.add('hp-hide');clearTimeout(timer)}
function next(){if(idx<DATA[cur].frames.length-1){idx++;render()}else{var n=keys.indexOf(cur)+1;if(n<keys.length){open(keys[n])}else{close()}}}
function prev(){if(idx>0){idx--;render()}else{var n=keys.indexOf(cur)-1;if(n>=0){cur=keys[n];idx=DATA[cur].frames.length-1;render()}}}
document.querySelectorAll('[data-t]').forEach(function(b){b.addEventListener('click',function(){open(b.dataset.t)})});
document.querySelector('.st-next').addEventListener('click',next);document.querySelector('.st-prev').addEventListener('click',prev);
document.querySelector('.st-x').addEventListener('click',close);
document.addEventListener('keydown',function(ev){if(pl.classList.contains('hp-hide'))return;if(ev.key==='ArrowRight')next();if(ev.key==='ArrowLeft')prev();if(ev.key==='Escape')close()});
/* link diretto a una story: #story-<tema> (condivisibile sui social) */
var h=location.hash.replace('#story-','');if(DATA[h]){open(h)}
""" % json.dumps(data, ensure_ascii=False)
    return page("08 · Stories", css, body, js)


# ================================================================= 09 CRONOGRAMA

def v9_crono(D):
    P, T = D["parties"], D["topics"]
    W, LANE, X0, X1 = 1100, 78, 150, 1080
    d0, d1 = date(2023, 6, 1), date(2026, 12, 15)
    span = (d1 - d0).days

    def xpos(ds):
        dd = B.d(ds)
        if dd < d0:
            return X0 - 70 + (dd.year - 2019) * 10  # "antes": colonna compressa a sinistra
        return X0 + (dd - d0).days / span * (X1 - X0)
    H = 70 + LANE * len(P) + 30
    parts = [f'<rect x="0" y="0" width="{W}" height="{H}" fill="none"/>']
    # griglia anni/mesi
    for y in (2024, 2025, 2026):
        x = xpos(f"{y}-01-01")
        parts.append(f'<line x1="{x:.1f}" y1="40" x2="{x:.1f}" y2="{H - 20}" stroke="#2c2c58" stroke-width="1"/><text x="{x + 4:.1f}" y="34" class="cr-yr">{y}</text>')
    parts.append(f'<text x="{X0 - 70}" y="34" class="cr-yr">antes</text><line x1="{X0 - 12}" y1="40" x2="{X0 - 12}" y2="{H - 20}" stroke="#2c2c58" stroke-dasharray="3 4"/>')
    events = [("2023-08-17", "Inicio legislatura"), ("2025-04-28", "Apagón"), ("2026-02-28", "Guerra con Irán"), ("2026-10-05", "Convocatoria 29N")]
    for ds, lab in events:
        x = xpos(ds)
        parts.append(f'<line x1="{x:.1f}" y1="48" x2="{x:.1f}" y2="{H - 20}" stroke="#ff8be7" stroke-width="1" stroke-dasharray="2 3" opacity=".7"/>'
                     f'<text x="{x + 4:.1f}" y="{H - 8}" class="cr-ev">{e(lab)}</text>')
    x29 = xpos("2026-11-29")
    parts.append(f'<rect x="{x29 - 2:.1f}" y="44" width="4" height="{H - 64}" fill="var(--hp-p)"/><text x="{x29 - 6:.1f}" y="34" class="cr-yr" text-anchor="end" fill="#a9a6ff">29N</text>')
    tips = []
    for li, p in enumerate(P):
        y = 70 + li * LANE + LANE / 2
        parts.append(f'<line x1="{X0 - 70}" y1="{y:.1f}" x2="{X1}" y2="{y:.1f}" stroke="#23234a" stroke-width="{LANE - 18}" stroke-linecap="round" opacity=".55"/>'
                     f'<text x="8" y="{y + 5:.1f}" class="cr-lane" fill="{LABEL_ON_DARK.get(p["key"], PARTY_COLOR[p["key"]])}">{e(p["label"])}</text>')
        seen = {}
        for s in sorted(D["stmts"][p["key"]], key=lambda s: s["date"]):
            x = xpos(s["date"])
            bucket = round(x / 9)
            k = seen.get(bucket, 0)
            seen[bucket] = k + 1
            yy = y + ((k % 5) - 2) * 10
            col = stance_color(s["stance"])
            sid = f'tip-{s["id"]}'
            shape = (f'<rect x="{x - 6:.1f}" y="{yy - 6:.1f}" width="12" height="12" rx="2"' if s["type"] == "voto"
                     else f'<path d="M{x:.1f} {yy - 8:.1f} L{x + 8:.1f} {yy:.1f} L{x:.1f} {yy + 8:.1f} L{x - 8:.1f} {yy:.1f} Z"' if s["type"] == "programa"
                     else f'<circle cx="{x:.1f}" cy="{yy:.1f}" r="7"')
            parts.append(f'{shape} fill="{col}" stroke="#0c0c22" stroke-width="2" class="cr-dot" data-t="{s["topic"]}" data-p="{p["slug"]}" data-tip="{sid}"/>')
            tips.append(f'<div class="cr-tip hp-hide" id="{sid}"><p class="cr-tip__h"><b style="color:{PARTY_COLOR[p["key"]]}">{e(p["label"])}</b> · {e(s["_topic"]["label_short"] if "_topic" in s else s["topic"])} · '
                        f'<span style="color:{col}">{e(ANS.get(s["stance"], ("", ""))[0] or "—")}</span></p><p class="cr-tip__q">{headline(s, True)}</p>'
                        f'<p class="cr-tip__w">{e(s["person"])} · {e(B.fdate(s["date"], True))}{" · voz regional" if s["level"] == "regional" else ""} · {src(s)}</p></div>')
    svg = f'<svg class="cr-svg" viewBox="0 0 {W} {H}" role="img" aria-label="Cronograma de declaraciones y votos por partido">{"".join(parts)}</svg>'
    chips = '<button class="cr-chip is-on" data-t="all">Todos los temas</button>' + "".join(f'<button class="cr-chip" data-t="{t["key"]}">{e(t["label_short"])}</button>' for t in T)
    body = f"""
<header class="cr-top"><div class="hp-wrap"><b>[NOMBRE TOOL]</b> · <span>Faltan {D['days_left']} días para el 29N</span></div></header>
<section class="hp-wrap cr-hero"><p class="cr-k">Cronograma</p><h1>Tres años de energía, punto por punto</h1>
<p class="cr-lead">Cada punto es una declaración o una votación. Su color dice si es un <b style="color:{SI}">sí</b>, un <b style="color:{NO}">no</b> o <b style="color:{AMB}">ambiguo</b> a la pregunta del tema. Elige un tema y mira cómo se mueve cada partido.</p></section>
<div class="hp-wrap"><div class="cr-chips">{chips}</div><p class="cr-q" aria-live="polite"></p>
<div class="cr-box">{svg}<div class="cr-tips">{''.join(tips)}</div></div>
<p class="cr-leg"><svg width="14" height="14"><circle cx="7" cy="7" r="6" fill="#ccc"/></svg> declaración <svg width="14" height="14"><rect x="1" y="1" width="12" height="12" rx="2" fill="#ccc"/></svg> votación en el Congreso <svg width="16" height="16"><path d="M8 1 L15 8 L8 15 L1 8 Z" fill="#ccc"/></svg> programa electoral · Pulsa un punto para leerlo</p></div>
<footer class="hp-wrap cr-foot">{D['n']} datos verificados · Fuente y texto literal en cada punto · Solo dirección nacional cuenta para la posición; las voces regionales aparecen marcadas</footer>"""
    css = f"""
body{{background:#0c0c22;color:#e8e8f5}}
.cr-top{{font-size:13px;color:#a7a7c7;padding:14px 0}}.cr-top b{{color:#fff}}
.cr-hero{{padding-top:24px;padding-bottom:12px}}.cr-k{{color:#ff8be7;text-transform:uppercase;letter-spacing:.2em;font-weight:800;font-size:12px;margin:0}}
.cr-hero h1{{font-size:56px;line-height:58px;margin:8px 0 12px;letter-spacing:-.03em;max-width:900px}}
.cr-lead{{color:#b9b9d6;font-size:18px;max-width:760px;margin:0}}
.cr-chips{{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0 8px}}
.cr-chip{{font:inherit;font-size:13px;font-weight:800;padding:7px 14px;border-radius:999px;border:1px solid #34346a;background:#15153a;color:#d7d7f0;cursor:pointer}}
.cr-chip.is-on{{background:var(--hp-p);border-color:var(--hp-p);color:#fff}}
.cr-q{{min-height:28px;font-size:20px;font-weight:800;margin:6px 0 10px;color:#fff}}
.cr-box{{background:#101030;border:1px solid #23234a;border-radius:20px;padding:12px;position:relative;overflow-x:auto}}
.cr-svg{{width:100%;min-width:900px;display:block}}
.cr-yr{{fill:#7d7db0;font-size:13px;font-weight:800}}.cr-ev{{fill:#ff8be7;font-size:11px}}.cr-lane{{font-size:15px;font-weight:900}}
.cr-dot{{cursor:pointer;transition:opacity .35s, transform .2s;transform-box:fill-box;transform-origin:center}}
.cr-dot:hover{{transform:scale(1.5)}}.cr-dot.is-dim{{opacity:.08}}.cr-dot.is-on{{stroke:#fff;stroke-width:3}}
.cr-tips{{margin-top:8px}}
.cr-tip{{background:#fff;color:#15151f;border-radius:14px;padding:14px 16px;max-width:620px;box-shadow:0 20px 40px rgba(0,0,0,.4)}}
.cr-tip__h{{margin:0 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:.06em;font-weight:800}}
.cr-tip__q{{margin:0 0 6px;font-weight:800;font-size:16px;line-height:22px}}.cr-tip__w{{margin:0;font-size:12px;color:#555}}
.cr-leg{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;color:#a7a7c7;font-size:13px}}
.cr-foot{{color:#7d7db0;font-size:13px;padding-top:20px;padding-bottom:80px}}
@media(max-width:700px){{.cr-hero h1{{font-size:34px;line-height:38px}}}}
"""
    js = """
var Q=%s;
function setTopic(k){document.querySelectorAll('.cr-chip').forEach(function(c){c.classList.toggle('is-on',c.dataset.t===k)});
 document.querySelectorAll('.cr-dot').forEach(function(d){d.classList.toggle('is-dim',k!=='all'&&d.dataset.t!==k)});
 document.querySelector('.cr-q').textContent=k==='all'?'':Q[k]}
document.querySelectorAll('.cr-chip').forEach(function(c){c.addEventListener('click',function(){setTopic(c.dataset.t)})});
var box=document.querySelector('.cr-box');box.scrollLeft=box.scrollWidth; /* su mobile parte dai dati recenti */
document.querySelectorAll('.cr-dot').forEach(function(d){d.addEventListener('click',function(){
 document.querySelectorAll('.cr-tip').forEach(function(t){t.classList.add('hp-hide')});document.querySelectorAll('.cr-dot').forEach(function(x){x.classList.remove('is-on')});
 d.classList.add('is-on');document.getElementById(d.dataset.tip).classList.remove('hp-hide')})});
""" % json.dumps({t["key"]: t["question_short"] for t in T}, ensure_ascii=False)
    return page("09 · Cronograma", css, body, js)


# ================================================================= 10 AFINIDAD

def v10_afinidad(D):
    P, T = D["parties"], [t for t in D["topics"] if t["proposition"]]
    clear = ("a_favor", "en_contra")
    pair = {}
    for a in P:
        for b in P:
            same, tot, rows = 0, 0, []
            for t in T:
                x, y = D["badges"][(a["key"], t["key"])]["badge"], D["badges"][(b["key"], t["key"])]["badge"]
                if x in clear and y in clear:
                    tot += 1
                    same += x == y
                    rows.append((t, x, y, "eq" if x == y else "ne"))
                else:
                    rows.append((t, x, y, "na"))
            pair[(a["key"], b["key"])] = (same, tot, rows)
    # rete
    W, H, R, cx, cy = 560, 520, 190, 280, 265
    pos = {p["key"]: (cx + R * math.cos(-math.pi / 2 + i * 2 * math.pi / len(P)), cy + R * math.sin(-math.pi / 2 + i * 2 * math.pi / len(P))) for i, p in enumerate(P)}
    edges = []
    for i, a in enumerate(P):
        for b in P[i + 1:]:
            same, tot, _ = pair[(a["key"], b["key"])]
            if tot == 0:
                continue
            r = same / tot
            (x1, y1), (x2, y2) = pos[a["key"]], pos[b["key"]]
            lx, ly = x1 + (x2 - x1) * .36, y1 + (y2 - y1) * .36  # etichetta fuori centro: le diagonali si incrociano a metà
            if tot < MIN_N:  # pochi confronti: non è un'affinità, solo un indizio
                edges.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#b9b9cc" stroke-width="1.5" stroke-dasharray="4 5" '
                             f'class="af-e" data-a="{a["slug"]}" data-b="{b["slug"]}"/>')
                continue
            edges.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="var(--hp-p)" stroke-width="{1 + r * 16:.1f}" stroke-linecap="round" '
                         f'opacity="{.12 + r * .7:.2f}" class="af-e" data-a="{a["slug"]}" data-b="{b["slug"]}"/>'
                         f'<text x="{lx:.1f}" y="{ly + 4:.1f}" class="af-el" data-a="{a["slug"]}" data-b="{b["slug"]}">{same}/{tot}</text>')
    nodes = "".join(f'<g class="af-n" data-p="{p["slug"]}"><circle cx="{pos[p["key"]][0]:.1f}" cy="{pos[p["key"]][1]:.1f}" r="34" fill="#fff" stroke="{PARTY_COLOR[p["key"]]}" stroke-width="6"/>'
                    f'<text x="{pos[p["key"]][0]:.1f}" y="{pos[p["key"]][1] + 5:.1f}" text-anchor="middle" class="af-nl">{e(ABBR[p["key"]])}</text></g>' for p in P)
    net = f'<svg viewBox="0 0 {W} {H}" class="af-net" role="img" aria-label="Red de coincidencias entre partidos">{"".join(edges)}{nodes}</svg>'
    # mappa di calore
    head = "".join(f'<th><span style="border-color:{PARTY_COLOR[p["key"]]}">{e(ABBR[p["key"]])}</span></th>' for p in P)
    trs, panels = [], []
    for a in P:
        tds = []
        for b in P:
            same, tot, rows = pair[(a["key"], b["key"])]
            if a["key"] == b["key"]:
                tds.append('<td class="af-self">—</td>')
                continue
            r = same / tot if tot >= MIN_N else None
            bg = f"rgba(90,82,255,{0.08 + 0.85 * r:.2f})" if r is not None else "repeating-linear-gradient(135deg,#f1f1f6 0 6px,#e8e8f0 6px 12px)"
            fg = "#fff" if (r or 0) > .55 else "#15151f"
            pid = f"pr-{min(a['slug'], b['slug'])}-{max(a['slug'], b['slug'])}"
            tds.append(f'<td><button class="af-cell" style="background:{bg};color:{fg}" data-pr="{pid}"><b>{same}/{tot}</b><small>{"pocos datos" if r is None else f"{round(r * 100)}%"}</small></button></td>')
            if a["key"] < b["key"]:
                lis = "".join(f'<li class="af-{st}"><span>{e(t["question_short"])}</span><em style="background:{stance_color(x)}">{e(ANS[x][0])}</em><em style="background:{stance_color(y)}">{e(ANS[y][0])}</em></li>'
                              for t, x, y, st in rows)
                panels.append(f'<div class="af-panel hp-hide" id="{pid}"><h3><span style="color:{PARTY_COLOR[a["key"]]}">{e(a["label"])}</span> y <span style="color:{PARTY_COLOR[b["key"]]}">{e(b["label"])}</span>: coinciden en {same} de {tot}</h3>'
                              f'<p class="af-ph"><span></span><b>{e(a["label"])}</b><b>{e(b["label"])}</b></p><ul>{lis}</ul></div>')
        trs.append(f'<tr><th>{e(ABBR[a["key"]])}</th>{"".join(tds)}</tr>')
    body = f"""
<header class="af-top"><div class="hp-wrap"><b>[NOMBRE TOOL]</b> · Elecciones 29N · <b>Faltan {D['days_left']} días</b></div></header>
<section class="hp-wrap af-hero"><h1>¿Quién se parece a quién<br>en energía?</h1>
<p>Comparamos las respuestas de cada pareja de partidos a las {len(T)} preguntas de sí o no. Cuanto más gruesa la línea, más coinciden. Solo cuentan las preguntas en las que ambos tienen una posición clara; con menos de {MIN_N}, la línea es discontinua (pocos datos). <b>No es una predicción de pactos.</b></p></section>
<main class="hp-wrap af-grid"><div class="af-card">{net}<p class="af-hint">Pulsa un partido para ver sus afinidades</p></div>
<div class="af-card"><table class="af-heat"><thead><tr><th></th>{head}</tr></thead><tbody>{''.join(trs)}</tbody></table>
<p class="af-hint">Pulsa una casilla para ver en qué coinciden y en qué no</p></div></main>
<section class="hp-wrap af-panels">{''.join(panels)}</section>
<footer class="hp-wrap af-foot">Posiciones calculadas a partir de {D['n']} declaraciones y votaciones con fuente · «Ambiguo» y «Sin datos» no cuentan para la afinidad</footer>"""
    css = f"""
body{{background:#f7f7fb}}
.af-top{{font-size:13px;padding:14px 0;color:var(--hp-mute)}}
.af-hero{{padding-top:32px;padding-bottom:12px}}.af-hero h1{{font-size:64px;line-height:64px;letter-spacing:-.035em;margin:0 0 14px}}
.af-hero p{{max-width:760px;font-size:18px;color:var(--hp-ink2)}}
.af-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding-top:12px}}
.af-card{{background:#fff;border-radius:24px;padding:20px;box-shadow:0 20px 50px rgba(40,30,120,.08)}}
.af-net{{width:100%;display:block}}.af-nl{{font-weight:900;font-size:14px}}.af-el{{font-size:12px;font-weight:800;fill:var(--hp-p-dark);text-anchor:middle;paint-order:stroke;stroke:#fff;stroke-width:4px}}
.af-n{{cursor:pointer}}.af-n:hover circle{{fill:#f1f0ff}}
.af-e,.af-el{{transition:opacity .3s}}.af-net.has-sel .af-e{{opacity:.05!important}}.af-net.has-sel .af-el{{opacity:0}}
.af-net.has-sel .af-e.is-on{{opacity:.9!important}}.af-net.has-sel .af-el.is-on{{opacity:1}}
.af-hint{{text-align:center;font-size:13px;color:var(--hp-mute);margin:8px 0 0}}
.af-heat{{width:100%;border-collapse:separate;border-spacing:6px;table-layout:fixed}}.af-heat th:first-child{{width:72px}}
.af-heat th{{font-size:13px;font-weight:900;text-align:center}}.af-heat tbody th{{text-align:right;padding-right:6px}}
.af-heat thead span{{border-bottom:3px solid;padding-bottom:3px}}
.af-cell{{width:100%;aspect-ratio:1;border:0;border-radius:14px;cursor:pointer;font:inherit;display:flex;flex-direction:column;align-items:center;justify-content:center;transition:transform .15s}}
.af-cell:hover,.af-cell.is-on{{transform:scale(1.08);box-shadow:0 8px 20px rgba(90,82,255,.35)}}.af-cell b{{font-size:17px}}.af-cell small{{font-size:11px;opacity:.85}}
.af-self{{text-align:center;color:#ccc}}
.af-panels{{padding-top:20px;padding-bottom:80px}}
.af-panel{{background:#fff;border-radius:24px;padding:24px;box-shadow:0 20px 50px rgba(40,30,120,.08)}}
.af-panel h3{{margin:0 0 12px;font-size:22px}}
.af-ph{{display:grid;grid-template-columns:1fr 90px 90px;gap:8px;margin:0 0 4px;font-size:12px;text-align:center}}
.af-panel ul{{list-style:none;margin:0;padding:0}}
.af-panel li{{display:grid;grid-template-columns:1fr 90px 90px;gap:8px;align-items:center;padding:10px 12px;border-radius:12px;margin-bottom:6px}}
.af-panel li em{{font-style:normal;color:#fff;font-weight:900;font-size:12px;text-align:center;padding:4px;border-radius:999px}}
.af-eq{{background:#eaf8f0}}.af-ne{{background:#fdeceb}}.af-na{{background:#f4f4f8;opacity:.75}}
.af-foot{{color:var(--hp-mute);font-size:13px;padding-bottom:60px}}
@media(max-width:900px){{.af-grid{{grid-template-columns:1fr}}.af-hero h1{{font-size:40px;line-height:42px}}.af-panel li,.af-ph{{grid-template-columns:1fr 70px 70px}}}}
"""
    js = """
var net=document.querySelector('.af-net');
document.querySelectorAll('.af-n').forEach(function(n){n.addEventListener('click',function(){var p=n.dataset.p,on=net.dataset.sel!==p;net.dataset.sel=on?p:'';
 net.classList.toggle('has-sel',on);document.querySelectorAll('.af-e,.af-el').forEach(function(x){x.classList.toggle('is-on',on&&(x.dataset.a===p||x.dataset.b===p))})})});
document.querySelectorAll('.af-cell').forEach(function(c){c.addEventListener('click',function(){document.querySelectorAll('.af-panel').forEach(function(x){x.classList.add('hp-hide')});
 document.querySelectorAll('.af-cell').forEach(function(x){x.classList.toggle('is-on',x.dataset.pr===c.dataset.pr)});
 var p=document.getElementById(c.dataset.pr);p.classList.remove('hp-hide');p.scrollIntoView({behavior:'smooth',block:'nearest'})})});
"""
    return page("10 · Afinidad", css, body, js)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    D = load()
    for s in D["feed"]:
        s.setdefault("_topic", s["_topic"])
    for p in D["parties"]:
        tm = {t["key"]: t for t in D["topics"]}
        for s in D["stmts"][p["key"]]:
            s["_topic"] = tm[s["topic"]]
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("06-tira-y-afloja", v6_tira), ("07-revista", v7_revista), ("08-stories", v8_stories),
                     ("09-cronograma", v9_crono), ("10-afinidad", v10_afinidad)):
        (OUT / f"{name}.html").write_text(fn(D), encoding="utf-8")
        print("scritto", name)


if __name__ == "__main__":
    main()

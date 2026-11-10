"""Motore di calcolo "La factura en juego": effetto in € delle proposte dei partiti su una bolletta tipo.

Metodo (deciso nel grill dell'8 ott 2026):
- Effetto = bolletta annua con i parametri proposti dal partito − bolletta annua con lo SCENARIO BASE (legge in vigore
  il 1/1/2027 se nessuno interviene). È aritmetica a parità di tutto il resto, non una previsione.
- Due profili (data/bill_model.json): hogar_tipo (luce + gas TUR) e hogar_vulnerable (+ bono social).
- Livelli: 1 = cifra del partito, 2 = derivata da misura esistente (≈) o rifiuto esplicito (0 €), 3 = senza cifra (—).
- TUR: risparmio "aplazado" (il tetto genera debito) -> mostrato ma escluso dall'headline.
- Proposte "condicionadas" -> mostrate con asterisco, escluse dall'headline.
- Headline per profilo = differenza tra il totale più favorevole e il meno favorevole, solo partiti con cifre (liv. 1-2)
  su tutti i temi dell'headline di quel profilo.

Input:  data/bill_model.json (INTERCAMBIABILE, vedi docs/HANDOFF_bill_model.md), data/baseline_2027.json,
        data/answers/*.json, data/questions.json, data/parties.json, data/impacted.json
Output: data/euro_matrix.json  (+ stampa la matrice)
Uso:    py scripts/calc.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Fallback usati SOLO se baseline_2027.json non ha il valore verificato (vengono marcati come non verificati)
FALLBACK_BASELINE = {"iva_luz_pct": 21.0, "iva_gas_pct": 21.0, "iee_pct": 5.11269632}

TOPIC_PROFILES = {  # a quali profili si applica ciascun tema in €
    "impuestos_factura": ["hogar_tipo", "hogar_vulnerable"],
    "bono_social": ["hogar_vulnerable"],
    "tur_gas": ["hogar_tipo", "hogar_vulnerable"],
    "precio_luz_gas": ["hogar_tipo"],
}
HEADLINE_TOPICS = {"hogar_tipo": ["impuestos_factura"], "hogar_vulnerable": ["impuestos_factura", "bono_social"]}

# data di ogni prova (id -> YYYY-MM-DD) e soglia dei 12 mesi per l'headline
STMT_DATES = {s["id"]: s["date"] for f in (DATA / "statements").glob("*.json")
              for s in json.loads(f.read_text(encoding="utf-8")).get("statements", [])}
_today = __import__("datetime").date.today()
CUTOFF_12M = _today.replace(year=_today.year - 1).isoformat()


def load(p, default=None):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def v(field):
    return field["value"] if isinstance(field, dict) else field


# ----------------------------------------------------------------- bollette

def elec_bill(prof, prices, iva, iee, bono_dto=0.0):
    kwh, kw = v(prof["elec_kwh_year"]), v(prof["elec_power_kw"])
    pe, pp, meter = v(prices["elec_energy_eur_kwh"]), v(prices["elec_power_eur_kw_year"]), v(prices["elec_meter_eur_year"])
    energy, power = kwh * pe, kw * pp
    discount = 0.0
    if bono_dto:
        limit = v(prof.get("bono_kwh_limit_year", {"value": kwh}))
        discount = (power + min(kwh, limit) * pe) * bono_dto / 100  # sconto su potenza + energia fino al limite agevolato
    base = energy + power - discount
    iee_amt = base * iee / 100
    iva_amt = (base + iee_amt + meter) * iva / 100
    return base + iee_amt + meter + iva_amt


def gas_bill(prof, prices, iva, tur_var):
    if not prof.get("gas"):
        return 0.0
    kwh = v(prof["gas_kwh_year"])
    fixed = v(prices["gas_tur_fixed_eur_month"]) * 12
    pre = fixed + kwh * tur_var + kwh * v(prices["gas_hydrocarbon_tax_eur_kwh"])
    return pre * (1 + iva / 100)


# ----------------------------------------------------------------- scenario base

def baseline_params(bl):
    p = (bl or {}).get("params", {})
    out, unverified = {}, []
    for k in ("iva_luz_pct", "iva_gas_pct", "iee_pct"):
        val = (p.get(k) or {}).get("baseline_2027")
        if val is None:
            val = FALLBACK_BASELINE[k]
            unverified.append(k)
        out[k] = float(val)
    bono = (p.get("bono_dto_vulnerable_pct") or {}).get("baseline_2027")
    out["bono_dto_vulnerable_pct"] = float(bono) if bono is not None else None
    if bono is None:
        unverified.append("bono_dto_vulnerable_pct")
    tur = p.get("tur_oct2026") or {}
    out["tur_without_cap_pct"] = tur.get("increase_without_cap_pct")
    out["tur_applied_pct"] = tur.get("increase_applied_pct")
    out["tur_cn_gap"] = float(tur["cn_gap_eur_kwh"]) if tur.get("cn_gap_eur_kwh") is not None else None
    if out["tur_cn_gap"] is None:
        unverified.append("tur_oct2026")
    return out, unverified


# ----------------------------------------------------------------- risposte dei partiti

HORIZON_YEARS = 4  # legislatura 2027-2030
QUESTION_OF = {"impuestos_factura": "iva_luz", "bono_social": "bono_prorroga", "tur_gas": "tur_tope", "precio_luz_gas": "excepcion_iberica"}


def baseline_bill(topic, prof, prices, base):
    """Bolletta annua dello scenario 2027 per il tema (serve a '¿Cómo lo calculamos?' quando il partito non propone nulla)."""
    if topic == "bono_social":
        return elec_bill(prof, prices, base["iva_luz_pct"], base["iee_pct"], base["bono_dto_vulnerable_pct"] or 0.0)
    if topic == "tur_gas":
        return gas_bill(prof, prices, base["iva_gas_pct"], v(prices["gas_tur_var_eur_kwh"]))
    bono = (base["bono_dto_vulnerable_pct"] or 0.0) if prof.get("bono_social") else 0.0
    return elec_bill(prof, prices, base["iva_luz_pct"], base["iee_pct"], bono) + gas_bill(prof, prices, base["iva_gas_pct"], v(prices["gas_tur_var_eur_kwh"]))


def load_answers():
    ans = {}
    for f in sorted((DATA / "answers").glob("*.json")):
        for a in load(f, {}).get("answers", []):
            ans[(a["party"], a["question"])] = a
    return ans


def usable(a):
    """Risposta con cifra utilizzabile nel calcolo: livello 1-2 e valore presente."""
    return bool(a) and a.get("level") in (1, 2) and a.get("value") is not None


def topic_effect(topic, party, prof_key, prof, prices, base, A):
    """Ritorna dict con effect (€/anno, negativo = risparmio), level, flags, used answers (+ aplazado_eur per la TUR)."""
    used, flags = [], set()
    deferred, y2028 = None, 0.0

    def take(qkey, default):
        a = A.get((party, qkey))
        if usable(a):
            until = a.get("temporal_until")
            if until and str(until) < "2027-01-01":
                # la misura finisce prima dello scenario 2027: vale 0 € (resta visibile come voce, a 0)
                flags.add("expira_antes_2027")
                used.append({**a, "_expired": True})
                return default
            if a.get("temporal") == "condicionada":
                flags.add("condicionada")
            if a.get("temporal") in ("temporal", "desconocido"):
                flags.add("duracion_no_definida")
            used.append(a)
            return float(a["value"])
        return default

    if topic == "impuestos_factura":
        iva_l = take("iva_luz", base["iva_luz_pct"])
        iva_g = take("iva_gas", base["iva_gas_pct"])
        iee = take("impuesto_electrico", base["iee_pct"])
        bono = (base["bono_dto_vulnerable_pct"] or 0.0) if prof.get("bono_social") else 0.0
        ref = elec_bill(prof, prices, base["iva_luz_pct"], base["iee_pct"], bono) + gas_bill(prof, prices, base["iva_gas_pct"], v(prices["gas_tur_var_eur_kwh"]))
        new = elec_bill(prof, prices, iva_l, iee, bono) + gas_bill(prof, prices, iva_g, v(prices["gas_tur_var_eur_kwh"]))
    elif topic == "bono_social":
        if base["bono_dto_vulnerable_pct"] is None:
            return {"effect": None, "level": 3, "flags": ["baseline_no_verificada"], "used": []}
        cands = [take(q, None) for q in ("bono_prorroga", "bono_ampliar_descuento")]
        cands = [c for c in cands if c is not None]
        dto = max(cands) if cands else base["bono_dto_vulnerable_pct"]
        ref = elec_bill(prof, prices, base["iva_luz_pct"], base["iee_pct"], base["bono_dto_vulnerable_pct"])
        new = elec_bill(prof, prices, base["iva_luz_pct"], base["iee_pct"], dto)
    elif topic == "tur_gas":
        # Scenario base 2027 = prezzo TUR CON tetto (il tetto resta per legge finché si recupera il debito).
        # Risposte: value = % massimo di aumento proposto. value >= aumento applicato (15) -> nessun cambio;
        # "eliminar el tope" (value = aumento senza tetto, 45) -> +costo = quota oggi rinviata (cn_gap) su ogni kWh.
        # Congelare (0) richiederebbe la formula completa della TUR: lo trattiamo come senza cifra (—).
        if base.get("tur_cn_gap") is None:
            return {"effect": None, "level": 3, "flags": ["baseline_no_verificada"], "used": []}
        cands = [take(q, None) for q in ("tur_tope", "tur_congelar")]
        cands = [c for c in cands if c is not None]
        if not cands:
            return {"effect": None, "level": 3, "flags": sorted(flags), "used": []}
        cap, applied, nocap = min(cands), float(base["tur_applied_pct"]), float(base["tur_without_cap_pct"])
        pre = v(prices["gas_tur_var_eur_kwh"])
        ref = gas_bill(prof, prices, base["iva_gas_pct"], pre)
        if cap >= nocap:      # elimina il tetto: si paga subito la quota rinviata, ma non c'è debito da recuperare dopo
            new = gas_bill(prof, prices, base["iva_gas_pct"], pre + base["tur_cn_gap"])
            flags.add("sin_tope")
            # ponytail: recupero del debito della legge ipotizzato tutto nel 2028; se il BOE fissa un calendario, spalmarlo
            y2028 = -round(new - ref, 2)
        elif cap >= applied:  # mantiene (o allenta entro il tetto attuale): nessun cambio vs base
            new = ref
            flags.add("aplazado")
            # quota rinviata (si pagherà più avanti): cn_gap × consumo × (1 + IVA gas). Decisione 8 ott: mostrarla in cella
            deferred = round(base["tur_cn_gap"] * v(prof["gas_kwh_year"]) * (1 + base["iva_gas_pct"] / 100), 2)
        else:                 # tetto più stretto o congelamento: servirebbe la formula completa -> senza cifra
            return {"effect": None, "level": 3, "flags": ["tur_formula_completa_necesaria"], "used": []}
    elif topic == "precio_luz_gas":
        # decisione 9 ott (opzione A): nessun modello di mercato; si mostra il risparmio REALE dell'excepción ibérica
        # (jun-dic 2022, ~250 € hogar PVPC, EsadeEcPol) come riferimento storico. Fuori da titolo e totali.
        saving = take("excepcion_iberica", None)
        if saving is None:
            return {"effect": None, "level": 3, "flags": sorted(flags), "used": []}
        ref = new = baseline_bill(topic, prof, prices, base)
        new = ref - saving
        flags.add("referencia_2022")
    else:
        return {"effect": None, "level": 3, "flags": [], "used": []}

    if not used:
        return {"effect": None, "level": 3, "flags": sorted(flags), "used": []}
    # regola dei 12 mesi (decisione 8 ott): per l'headline la cifra deve venire da una prova degli ultimi 12 mesi
    ev_dates = [max((STMT_DATES.get(i, "") for i in a.get("evidence", [])), default="") for a in used]
    if any(d and d < CUTOFF_12M for d in ev_dates):
        flags.add("propuesta_antigua")
    level = 1 if any(a["level"] == 1 for a in used) else 2
    if all(a.get("answer") == "no" for a in used):
        flags.add("rechaza")
    return {"effect": round(new - ref, 2), "level": level, "flags": sorted(flags), "aplazado_eur": deferred, "y2028_eur": y2028,
            "ref_eur": round(ref, 2), "new_eur": round(new, 2),
            "used": [{"question": a["question"], "value": a["value"], "level": a["level"], "evidence": a.get("evidence", []),
                      "value_note": a.get("value_note", ""), "expired": bool(a.get("_expired"))} for a in used]}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    model = load(DATA / "bill_model.json")
    bl = load(DATA / "baseline_2027.json")
    base, unverified = baseline_params(bl)
    parties = [p for p in load(DATA / "parties.json")["parties"] if not p.get("hidden")]
    A = load_answers()
    impacted = load(DATA / "impacted.json", {})
    out = {"_meta": {"bill_model_status": model["_meta"]["status"], "baseline_unverified": unverified,
                     "note": "effect < 0 = risparmio annuo vs legge 1/1/2027; None = senza cifra (—)"},
           "baseline": base, "cells": {}, "headline": {}, "impacted": impacted.get("rows", {})}
    for p in parties:
        for topic, profs in TOPIC_PROFILES.items():
            for pk in profs:
                prof = model["profiles"][pk]
                r = topic_effect(topic, p["key"], pk, prof, model["prices"], base, A)
                if r["effect"] is None:
                    # decisione 8 ott: niente "—". Senza proposta in € si applica la legge 2027 -> 0 €
                    ref = baseline_bill(topic, prof, model["prices"], base)
                    r = {"effect": 0.0, "level": 0, "flags": sorted(set(r["flags"]) | {"sin_propuesta"}), "used": [],
                         "ref_eur": round(ref, 2), "new_eur": round(ref, 2),
                         "answer_hint": (A.get((p["key"], QUESTION_OF[topic])) or {}).get("answer")}
                if topic == "tur_gas" and r["effect"] == 0:
                    # il tetto resta per legge: la quota rinviata riguarda TUTTE le famiglie in TUR, con qualsiasi partito
                    r["aplazado_eur"] = round(base["tur_cn_gap"] * v(prof["gas_kwh_year"]) * (1 + base["iva_gas_pct"] / 100), 2)
                    r["flags"] = sorted(set(r["flags"]) | {"aplazado"})
                out["cells"][f'{p["key"]}|{topic}|{pk}'] = r
    # headline
    for pk, topics in HEADLINE_TOPICS.items():
        totals = {}
        for p in parties:
            cells = [out["cells"].get(f'{p["key"]}|{t}|{pk}') for t in topics]
            # tutti i partiti entrano; per il titolo le cifre condizionate o più vecchie di 12 mesi valgono come la legge (0 €).
            # "duracion_no_definida" conta (decisione 8 ott: pagina aggiornata ogni giorno fino al voto)
            totals[p["key"]] = round(sum(0.0 if {"condicionada", "propuesta_antigua"} & set(c["flags"]) else c["effect"] for c in cells), 2)
        if len(totals) >= 2:
            best, worst = min(totals, key=totals.get), max(totals, key=totals.get)
            # decisione 9 ott: il titolo è sulla legislatura (4 anni, a prezzi medi costanti)
            out["headline"][pk] = {"x_eur": round((totals[worst] - totals[best]) * HORIZON_YEARS), "x_eur_year": round(totals[worst] - totals[best]),
                                   "best": best, "worst": worst,
                                   "totals": totals, "topics": topics, "parties_compared": sorted(totals)}
        else:
            out["headline"][pk] = {"x_eur": None, "reason": "meno di 2 partiti con cifre su tutti i temi", "totals": totals}
    (DATA / "euro_matrix.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # report
    print(f"Modello bolletta: {model['_meta']['status']} · baseline non verificata: {unverified or 'nessuna'}")
    for pk in ("hogar_tipo", "hogar_vulnerable"):
        print(f"\n== {pk}")
        for topic, profs in TOPIC_PROFILES.items():
            if pk not in profs:
                continue
            row = []
            for p in parties:
                c = out["cells"][f'{p["key"]}|{topic}|{pk}']
                if c["effect"] is None:
                    row.append(f"{p['label'][:7]}: —")
                else:
                    mark = ("≈" if c["level"] == 2 else "") + ("*" if c["flags"] else "")
                    extra = f" ({c['aplazado_eur']:.0f}€ aplaz.)" if c.get("aplazado_eur") else ""
                    row.append(f"{p['label'][:7]}: {mark}{c['effect']:+.0f}€{extra}")
            print(f"  {topic:<18} " + " | ".join(row))
        h = out["headline"][pk]
        print(f"  HEADLINE: {h.get('x_eur')} € ({h.get('best')} vs {h.get('worst')}) {h.get('reason', '')}")


if __name__ == "__main__":
    main()

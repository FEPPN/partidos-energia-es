"""Sincronizza data/bill_model.json con i modelli Excel del Termómetro (Oscar Pacheco).

Fonti (file .xlsx in data/oscar_models/, scaricati da Google Sheets):
- Modelo 3 | Tracker PVPC  -> foglio "📈 Tracker PVPC": media PVPC (€/kWh, tutto incluso) degli ultimi 12 mesi
                           -> foglio "⚙️ Tarifas": potenza PVPC punta/valle (€/kW·año), margine + noleggio (€/mes)
                           -> foglio "🔀 Comparador": profilo hogar estándar (potenza kW, consumo kWh/año)
Formula di bolletta = quella del Comparador di Oscar (energia + potenza + fissi + IEE su energia+potenza + IVA su tutto),
con il prezzo medio 12 mesi al posto del prezzo del mese (decisione grill: prezzi reali 12 mesi, non previsioni).
Gas: i modelli di Oscar non lo includono -> consumo IDAE SPAHOUSEC II + tariffe TUR BOE (baseline_2027.json).

Uso: py scripts/sync_oscar.py   (poi py scripts/build_factura.py)
"""
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MODELS = DATA / "oscar_models"


def find(pattern):
    fs = sorted(MODELS.glob(pattern))
    if not fs:
        raise SystemExit(f"Manca {pattern} in {MODELS}")
    return fs[-1]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    m3 = openpyxl.load_workbook(find("Modelo_3*.xlsx"), data_only=True)
    t = m3["📈 Tracker PVPC"]
    rows = [r for r in range(5, t.max_row + 1) if t.cell(r, 1).value and isinstance(t.cell(r, 4).value, (int, float))]
    last12 = rows[-12:]
    prices = [float(t.cell(r, 4).value) for r in last12]
    period = f"{t.cell(last12[0], 1).value} {int(t.cell(last12[0], 2).value)} – {t.cell(last12[-1], 1).value} {int(t.cell(last12[-1], 2).value)}"
    pvpc12 = sum(prices) / len(prices)
    ta = m3["⚙️ Tarifas"]
    lab = {str(ta.cell(r, 1).value).strip(): r for r in range(1, ta.max_row + 1) if ta.cell(r, 1).value}
    p_punta = float(ta.cell(lab["Punta €/kW·año"], 2).value)
    p_valle = float(ta.cell(lab["Valle €/kW·año"], 2).value)
    co = m3["🔀 Comparador"]
    clab = {str(co.cell(r, 1).value).strip(): r for r in range(1, co.max_row + 1) if co.cell(r, 1).value}
    kw = float(co.cell(clab["Potencia punta (kW)"], 2).value)
    kwh = float(co.cell(clab["Consumo anual (kWh/año)"], 2).value)
    fixed_month = float(co.cell(clab["Margen + alquiler (€/mes)"], 2).value)
    bill_month_oscar = float(co.cell(clab["TOTAL (€/mes)"], 2).value)

    # decisione 9 ott: prezzo = media PVPC di tutto lo storico del Modelo 2 (2021-2026, ciclo intero con la crisi 2022)
    m2 = openpyxl.load_workbook(find("Modelo_2*.xlsx"), data_only=True)["📅 Timeline"]
    hist = [float(m2.cell(r, 6).value) for r in range(5, m2.max_row + 1) if isinstance(m2.cell(r, 6).value, (int, float))]
    pvpc12, period = sum(hist) / len(hist), f"Modelo 2 Histórico Medidas, {len(hist)} meses 2021-2026 (últimos 12 meses: {pvpc12:.4f} €/kWh)"
    bl = json.loads((DATA / "baseline_2027.json").read_text(encoding="utf-8"))["params"]["tur_oct2026"]
    gas_kwh = 5097.0
    src_m3 = "Termómetro papernest · Modelo 3 Tracker PVPC"
    model = json.loads((DATA / "bill_model.json").read_text(encoding="utf-8"))
    model["_meta"].update({
        "status": "TERMOMETRO",
        "note": ("Luz: modelo del Termómetro (Oscar Pacheco), fórmula del Comparador del Modelo 3 con PVPC medio de los últimos 12 meses. "
                 "Gas: no está en los modelos del Termómetro -> consumo IDAE SPAHOUSEC II (5.097 kWh/año, hogar sin calefacción central) + TUR 2 BOE oct 2026."),
        "updated_at": __import__("datetime").date.today().isoformat(),
        "oscar_bill_month_current_price": round(bill_month_oscar, 2),
        "pvpc_12m_period": period})
    for prof in ("hogar_tipo", "hogar_vulnerable"):
        P = model["profiles"][prof]
        P["elec_kwh_year"] = {"value": kwh, "source": f"{src_m3}, Comparador: hogar estándar (perfil OCU/regulador)"}
        P["elec_power_kw"] = {"value": kw, "source": f"{src_m3}, Comparador: 4,6 kW punta y valle"}
        P["gas_kwh_year"] = {"value": gas_kwh, "source": "IDAE, estudio SPAHOUSEC II (2019): consumo medio anual de gas natural en hogares sin calefacción central = 5.097 kWh"}
        P["description"] = "Vivienda de 4,6 kW y 3.500 kWh/año de luz (PVPC) y gas natural en tarifa regulada (TUR 2, 5.097 kWh/año)"
    model["prices"]["elec_energy_eur_kwh"] = {"value": round(pvpc12, 6), "source": f"Termómetro papernest: PVPC medio {period} (peajes, cargos y capacidad incluidos)"}
    model["prices"]["elec_power_eur_kw_year"] = {"value": round(p_punta + p_valle, 4), "source": f"{src_m3}, Tarifas: potencia PVPC punta {p_punta} + valle {p_valle} €/kW·año"}
    model["prices"]["elec_meter_eur_year"] = {"value": round(fixed_month * 12, 2), "source": f"{src_m3}, Comparador: margen + alquiler de equipos {fixed_month} €/mes"}
    model["prices"]["gas_tur_fixed_eur_month"] = {"value": float(bl.get("tur2_fixed_eur_month", 8.17)), "source": "BOE Resolución TUR 1/10/2026, TUR 2 término fijo"}
    model["prices"]["gas_tur_var_eur_kwh"] = {"value": float(bl.get("tur2_var_eur_kwh", 0.05042762)), "source": "BOE Resolución TUR 1/10/2026, TUR 2 término variable (con tope)"}
    model["prices"]["gas_hydrocarbon_tax_eur_kwh"] = {"value": 0.00234, "source": "Ley 38/1992, impuesto sobre hidrocarburos gas natural uso doméstico: 0,65 €/GJ = 0,00234 €/kWh"}
    (DATA / "bill_model.json").write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PVPC medio usado: {pvpc12:.5f} €/kWh ({period})")
    print(f"Potenza {p_punta}+{p_valle} €/kW·año · {kw} kW · {kwh:.0f} kWh · fissi {fixed_month} €/mes · bolletta Oscar (prezzo mese corrente) {bill_month_oscar:.2f} €/mes")
    print(f"Gas: {gas_kwh:.0f} kWh, TUR2 {model['prices']['gas_tur_fixed_eur_month']['value']} €/mes + {model['prices']['gas_tur_var_eur_kwh']['value']} €/kWh")


if __name__ == "__main__":
    main()

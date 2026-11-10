"""Controllo minimo del calcolo in €: py scripts/test_calc.py (fallisce se la logica si rompe)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calc  # noqa: E402

model = json.loads((calc.DATA / "bill_model.json").read_text(encoding="utf-8"))
prof, pr = model["profiles"]["hogar_tipo"], model["prices"]

# 1. la formula riproduce il Comparador di Oscar (Modelo 3) al prezzo del mese: 71,58 €/mes
pe_now = 0.25 * 0.22442 + 0.35 * 0.1603 + 0.40 * 0.088165
assert abs(calc.elec_bill(prof, {**pr, "elec_energy_eur_kwh": {"value": pe_now}}, 21, 5.11, 0) / 12 - 71.58) < 0.05

# 2. meno IVA = risparmio; stesso IVA = 0
base = calc.elec_bill(prof, pr, 21, 5.11269632, 0)
assert calc.elec_bill(prof, pr, 10, 5.11269632, 0) < base
assert calc.elec_bill(prof, pr, 21, 5.11269632, 0) == base

# 3. il bono social riduce la bolletta e uno sconto più alto la riduce di più
vul = model["profiles"]["hogar_vulnerable"]
assert calc.elec_bill(vul, pr, 21, 5.11269632, 42.5) < calc.elec_bill(vul, pr, 21, 5.11269632, 35)

# 4. matrice: nessun "—" (niente None), titolo presente per entrambi i profili
calc.main()
M = json.loads((calc.DATA / "euro_matrix.json").read_text(encoding="utf-8"))
assert all(c["effect"] is not None for c in M["cells"].values())
assert all(M["headline"][p]["x_eur"] for p in ("hogar_tipo", "hogar_vulnerable"))
print("ok")

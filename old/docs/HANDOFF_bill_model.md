# Handoff: modello di bolletta per "La factura en juego"

> **Stato 8 ott 2026:** `bill_model.json` è già sincronizzato con i modelli del Termómetro tramite `py scripts/sync_oscar.py`. Lo script legge i 4 .xlsx in `data/oscar_models/` e usa la formula del Comparador del Modelo 3 (riprodotta esattamente: 71,58 €/mes al prezzo del mese) con il **PVPC medio degli ultimi 12 mesi** preso dal Tracker.
>
> **Punti da confermare con Oscar:**
> 1. Tre bollette "estándar" diverse: Modelo 1 59,56 €/mes, Modelo 3 71,58 €/mes, Termómetro pubblicato 87,5 €/mes. Qui usiamo la formula del Modelo 3 con la media a 12 mesi, cioè **69,71 €/mes**.
> 2. Bono social: il Modelo 1 usa un limite di **1.380 kWh**, il BOE vigente (RD 897/2017 modificato dal RDL 18/2022) dice **1.587**. Qui usiamo il valore BOE. Anche il metodo è diverso: Oscar applica lo sconto in proporzione sul totale, qui seguiamo la regola BOE (potenza scontata per intero, energia fino al limite).
> 3. Gas: non c'è nei modelli del Termómetro. Qui usiamo il consumo IDAE SPAHOUSEC II (5.097 kWh/anno) con le tariffe TUR 2 del BOE di ottobre 2026.

**Per:** il Claude che gestisce il Termómetro Energético papernest (Oscar Pacheco, PR ES).
**Obiettivo:** sostituire i valori PROVVISORI di `data/bill_model.json` con il modello di bolletta del Termómetro, così le cifre in € della pagina elettorale sono coerenti con quelle che il Termómetro pubblica ogni mese.

## Cosa fa il progetto (in breve)

"La factura en juego | Elecciones 29N" mostra, per ogni partito spagnolo, quanto valgono in bolletta le sue proposte su tre temi: **imposte in bolletta** (IVA luce e gas, imposta elettrica), **bono social elettrico** e **TUR del gas**.

- **Il numero in €** è l'**effetto diretto della proposta a parità di tutto il resto**: bolletta annua con i parametri proposti dal partito, meno la bolletta annua con lo **scenario base**, cioè la legge in vigore il 1/1/2027 se nessuno interviene.
- **Non è una previsione.** Per questo i prezzi devono essere **medie reali degli ultimi 12 mesi**, non prezzi futuri.

Il calcolo è in `scripts/calc.py`. Le formule usano solo i campi descritti qui sotto: se il modello del Termómetro ha una struttura diversa, va tradotto in questi campi oppure va adattata la funzione di calcolo (vedi in fondo).

## Campi da fornire (`data/bill_model.json`)

Ogni campo è `{"value": ..., "source": "..."}`. In `source` scrivere da dove viene il dato: CNMC, OMIE, modello Termómetro, mese di riferimento.

### Profili (`profiles`)

| Campo | Profilo | Unità | Significato |
|---|---|---|---|
| `elec_kwh_year` | entrambi | kWh/anno | Consumo annuo di elettricità della famiglia tipo del Termómetro |
| `elec_power_kw` | entrambi | kW | Potenza contrattata (2.0TD) |
| `gas` | entrambi | true/false | La famiglia ha il gas naturale in TUR |
| `gas_kwh_year` | entrambi | kWh/anno | Consumo annuo di gas (TUR 1 ≤ 5.000 kWh) |
| `bono_kwh_limit_year` | vulnerable | kWh/anno | Limite di consumo agevolato del bono social per il tipo di famiglia scelto |

`hogar_vulnerable` è **la stessa famiglia** di `hogar_tipo` con il bono social: devono restare uguali i consumi, cambia solo lo sconto.

### Prezzi (`prices`), senza imposte, media degli ultimi 12 mesi

| Campo | Unità | Significato |
|---|---|---|
| `elec_energy_eur_kwh` | €/kWh | Termine di energia PVPC medio (energia + pedaggi + oneri) |
| `elec_power_eur_kw_year` | €/kW·anno | Termine di potenza annuo (pedaggi + oneri + margine) |
| `elec_meter_eur_year` | €/anno | Noleggio del contatore |
| `gas_tur_fixed_eur_month` | €/mese | TUR 1, termine fisso, **prima** della revisione di ottobre 2026 |
| `gas_tur_var_eur_kwh` | €/kWh | TUR 1, termine variabile, **prima** della revisione di ottobre 2026 |
| `gas_hydrocarbon_tax_eur_kwh` | €/kWh | Imposta speciale sugli idrocarburi, gas uso domestico |

## Come vengono usati (formule in `calc.py`)

**Elettricità:**
- base = consumo × prezzo energia + potenza × prezzo potenza − sconto bono social
- lo sconto bono social = % × (termine di potenza + energia fino al limite agevolato)
- imposta elettrica = base × aliquota imposta elettrica
- IVA = (base + imposta elettrica + noleggio contatore) × aliquota IVA

**Gas:** (fisso × 12 + consumo × prezzo variabile + consumo × imposta idrocarburi) × (1 + IVA)

**TUR:** confronto tra il prezzo variabile aumentato del % **senza tetto** (scenario base 2027) e quello aumentato del % **con il tetto** proposto dal partito. Il risultato è marcato come "aplazado" perché il tetto genera un debito.

Le aliquote (IVA, imposta elettrica, sconti del bono, % TUR) **non** stanno qui: sono in `data/baseline_2027.json` (scenario base verificato su BOE) e nelle risposte dei partiti (`data/answers/`).

## Come verificare dopo la sostituzione

```
py scripts/calc.py
```

Stampa la matrice in € per partito, tema e profilo, più l'headline ("hasta X €"). Controlli da fare:
1. In cima, `Modello bolletta:` non deve più dire `PROVISIONAL`: cambiare `_meta.status` in `"TERMOMETRO"` (o simile) dopo la sostituzione.
2. La bolletta annua della famiglia tipo nello scenario base deve essere coerente con la "factura modelo" del Termómetro. Si può controllare importando le funzioni `elec_bill` / `gas_bill` di `calc.py`.
3. Se il Termómetro calcola alcune voci in modo diverso (per esempio il bono social o l'imposta elettrica con il minimo per MWh), adattare `elec_bill` / `gas_bill` in `calc.py` **e** questa tabella, in modo che restino allineate.

## Cosa NON toccare

- `data/answers/*.json`, `data/baseline_2027.json`, `data/statements/`: sono i dati sui partiti e sulle norme, verificati con le fonti.
- Le regole di metodo descritte in cima a `calc.py` (scenario base, livelli, "aplazado", esclusioni dall'headline): le ha decise il team.

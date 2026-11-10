# Output Contract — `data/statements/<slug>.json`

Un file per partito. È la fonte unica di verità: `scripts/build.py` legge solo questi file + `parties.json` + `topics.json`.

```json
{
  "party": "PSOE",
  "collected_at": "2026-10-08",
  "key_people_verified": [
    { "name": "Pedro Sánchez", "role": "Presidente del Gobierno y secretario general del PSOE", "source_url": "https://..." }
  ],
  "candidate": { "name": "Pedro Sánchez", "official": true, "source_url": "https://..." },
  "statements": [
    {
      "id": "psoe-nucleares-20260801-a",
      "topic": "nucleares",
      "type": "declaracion",
      "date": "2026-08-01",
      "person": "Sara Aagesen",
      "role": "Vicepresidenta tercera y ministra para la Transición Ecológica",
      "level": "nacional",
      "quote": "Texto literal entre comillas tal como aparece en la fuente",
      "context": "Una frase neutra que explica en qué ocasión lo dijo (o qué se votó).",
      "stance": "en_contra",
      "rationale": "Una frase: por qué esta cita es a favor / en contra / ambigua respecto a la proposición del tema.",
      "source_name": "El País",
      "source_url": "https://...",
      "tier": 2,
      "verified": "scraped",
      "added_at": "2026-10-08"
    }
  ],
  "gaps": [
    { "topic": "data_center", "note": "Ninguna declaración nacional encontrada tras N búsquedas." }
  ],
  "excluded": [
    { "url": "https://...", "reason": "Tier3 / falso positivo / fecha no verificable / regional sin relevancia" }
  ]
}
```

## Campi

| Campo | Valori | Regola |
|---|---|---|
| `id` | `<slug>-<topic>-<yyyymmdd>-<a,b,c>` | univoco, stabile (serve per il diff negli aggiornamenti) |
| `topic` | chiave da `topics.json` | mai temi liberi |
| `type` | `declaracion` \| `voto` \| `programa` \| `reportada` | `voto` = votazione nominale in Congreso; `programa` = programma elettorale ufficiale; `reportada` = il giornalista riassume con parole sue cosa ha detto il politico (discorso indiretto) → `quote: null`, testo in `context` come "Según <testata>: …", mai tra virgolette |
| `date` | `YYYY-MM-DD` | data della dichiarazione ORIGINALE, non del repost (vedi gotcha) |
| `person` | nome | per `voto`: "Grupo Parlamentario X"; per `programa`: nome del partito |
| `role` | ruolo AL MOMENTO della dichiarazione | |
| `level` | `nacional` \| `regional` | `regional` = presidenti/consiglieri autonomici, cargos locali → solo timeline, NON conta per il badge |
| `quote` | testo letterale in spagnolo | DEVE comparire nella pagina scrapata o nello snippet. Per `voto`: `null` |
| `context` | 1 frase spagnolo, neutra | per `voto`: cosa si votava + esito (es. "Proposición no de ley del PP para derogar el calendario nuclear. Rechazada 171-178.") |
| `stance` | `a_favor` \| `en_contra` \| `ambiguo` \| `na` | rispetto alla `proposition` del tema; `na` per temi con proposition = null |
| `rationale` | 1 frase spagnolo | |
| `tier` | `1` \| `2` | tier3 non entra mai qui |
| `verified` | `scraped` \| `snippet` | `snippet` = pagina bloccata, citazione presa dallo snippet SERP |

## Regole di calcolo del badge (implementate in `build.py`)

1. Prove valide: `level=nacional`, `tier` 1-2, `date` ≥ 2023-08-17 (inizio XV legislatura), `stance` ≠ `na`. Per Podemos: ≥ 2024-01-01.
2. Nessuna prova valida → **Sin declaraciones**.
3. "Periodo attuale" = prove valide entro 180 giorni dalla più recente.
4. Nel periodo attuale ci sono sia `a_favor` sia `en_contra` → **Ambiguo** (se uno è `voto` e l'altro `declaracion` → flag "dice/vota").
5. Altrimenti badge = posizione del periodo attuale (`ambiguo` se solo prove ambigue).
6. Esiste una prova valida PIÙ VECCHIA del periodo attuale con posizione opposta → etichetta **Cambió de posición** + popup (prima → dopo).
7. Prove prima della legislatura: solo timeline ("Histórico"); se opposte alla posizione attuale → popup "Antes de esta legislatura decía otra cosa", senza etichetta sul badge.
8. Se non c'è né 6 né 7 ma esiste una prova nazionale più vecchia del periodo attuale con stance DIVERSA (non opposta, es. ambiguo → a_favor) → popup "Su posición ha evolucionado", senza etichetta sul badge.

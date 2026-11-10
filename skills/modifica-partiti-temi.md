---
name: modifica-partiti-temi
description: "Modifiche strutturali al tool partiti × energia: aggiungere/unire/rinominare un partito (es. Sumar + Podemos lista unica, candidato ufficiale), aggiungere un tema, cambiare la proposition di un tema, cambiare nome tool/URL base. Aggiorna i JSON in data/, rilancia build.py e dice quali pagine WP creare/ri-incollare/reindirizzare. Trigger: 'aggiungi partito', 'unisci Sumar e Podemos', 'candidato ufficiale', 'aggiungi tema', 'cambia proposizione', 'cambia nome tool'."
---

# Modifica partiti e temi

## Intent
- Goal: cambiare la struttura del tool senza rompere URL, dati o coerenza dei badge.
- Failure: URL di una pagina partito cambiato senza redirect; proposition cambiata senza riclassificare le stance; candidato inserito nell'H1 prima che sia ufficiale.

## Gotchas
- **Gli URL sono per partito e non cambiano mai**, nemmeno se cambia il leader. Se due partiti si uniscono, la pagina del partito assorbito va reindirizzata (301) verso quella della lista unica: il redirect lo fa chi gestisce WordPress, va segnalato nel report.
- **Cambiare la `proposition` cambia il significato di tutte le stance di quel tema.** Prima di rilanciare la build vanno riclassificate tutte le righe del tema, per ogni partito.
- **Nome del tool e `base_path`** sono in `data/config.json`. Cambiare `base_path` dopo la pubblicazione rompe tutti i link interni già indicizzati: va fatto solo prima del lancio.

## Runtime Rules
1. `candidate_official: true` solo con fonte ufficiale: proclamazione delle candidature (BOE / Junta Electoral) o annuncio ufficiale del partito.
2. Un nuovo tema richiede `key`, `group`, `label`, `label_short`, `title_label` (con articolo spagnolo), `proposition` (o `null`), `query_keywords` ed `exclude_context`.
3. Un nuovo partito richiede `key`, `slug`, `label`, `label_long`, `label_article`, `label_long_article`, `candidate` e un file `data/statements/<slug>.json` (anche vuoto: `{"statements": []}`).
4. Dopo ogni modifica: `py scripts/build.py --check`, poi `py scripts/build.py`.

## Workflow
1. Leggere la richiesta e i JSON in `data/`.
2. Applicare la modifica. Per le unioni di partiti: unire i due file statements (gli `id` restano), aggiornare `parties.json`, rimuovere il partito assorbito.
3. Se cambia una proposition: riclassificare tutte le righe del tema e annotare nel report ogni stance cambiata.
4. Build e report: pagine nuove da creare in WordPress, pagine da ri-incollare, redirect 301 da chiedere.

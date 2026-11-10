---
name: aggiorna-dichiarazioni
description: "Aggiorna il tool partiti × energia (papernest.es) con nuove dichiarazioni/voti/programmi: cerca le novità dall'ultimo aggiornamento, verifica fonti e citazioni letterali, aggiunge le righe ai data/statements/*.json, rilancia build.py e restituisce il report dei badge cambiati (= ganci PR) + l'elenco delle pagine WP da ri-incollare. Trigger: 'aggiorna tool partiti', 'aggiorna dichiarazioni', 'novità partiti energia', 'sono usciti i programmi'."
---

# Aggiorna dichiarazioni

## Intent
- Goal: portare il tool allo stato più recente senza mai rompere la regola d'oro (ogni citazione letterale, datata, con fonte).
- Optimizes for: freschezza durante la campagna (14-26 nov 2026) e difendibilità.
- Sacrifices: esaustività. Meglio 2 dichiarazioni solide che 6 deboli.
- Success: report con badge cambiati + pagine da ri-incollare, zero errori in `build.py`.
- Failure: una citazione parafrasata, una data di repost, una voce regionale che sposta un badge nazionale.

## Gotchas
- **La key Serper del server MCP può essere esaurita**: usare sempre `scripts/serper.py`, che chiama l'API diretta con la key in `ZZ_file ENV/Keys/scraper`. Saldo: `GET https://google.serper.dev/account`.
- **Serper non restituisce PAA né related sulle SERP spagnole.** Per le PAA usare SerpAPI (crediti limitati, vedi CLAUDE.md globale).
- **Repost con data sbagliata.** Un'intervista vecchia ripubblicata da un aggregatore porta la data del repost: risalire sempre alla prima pubblicazione.
- **"Nuclear" e "apagón" sono ambigui.** "Nuclear" può riferirsi a Iran o armi, "apagón" a "apagón informativo". Leggere sempre il soggetto della frase (vedi `exclude_context` in `topics.json`).
- **Alcuni ministri del PSOE sono di Sumar.** Le dichiarazioni di un ministro di Sumar vanno al partito Sumar, non al Governo/PSOE.
- **Podemos** conta solo dal 2024-01-01 (nel 2023 si presentava dentro Sumar).
- **SALF** non ha deputati in Congreso: niente voti in Congreso, solo dichiarazioni e voti al Parlamento europeo.
- **Lo scrape di Serper a volte sostituisce le lettere accentate con uno spazio** ("energ a"), e nei PDF le parole vanno a capo con il trattino ("ELIMI-\nNAREMOS"). `verify_quotes.py` normalizza entrambi i casi: se una citazione risulta "non trovata", guardare il testo grezzo prima di concludere che è sbagliata (8 ott 2026: 7 falsi negativi su 93, tutti per questo motivo).
- **Parafrasi del giornalista ≠ citazione.** Una frase può essere presente alla lettera nell'articolo ed essere comunque il giornalista che riassume ("Hernández también ha expuesto la necesidad de…"). `verify_quotes.py` la dà OK perché il testo c'è. Controllare che nella fonte sia tra virgolette o attribuita in discorso diretto; altrimenti `type: reportada`, senza quote. 8 ott 2026: 5 casi in un solo articolo di El País.
- **Voti su decreti omnibus** (es. "escudo social", decreti anticrisi): un "no" al decreto non è un "no" a ogni misura che contiene. Classificarli `ambiguo`, salvo motivazione esplicita del gruppo su quel tema. `build.py` non li usa come punto di partenza dei popup "evolución".
- **Se cambia la `proposition` di un tema, vanno riclassificate TUTTE le `stance` di quel tema**, per tutti i partiti, perché la stance è relativa al testo della proposta.

## Runtime Rules
1. Mai inventare citazioni, date o fonti. `quote` = testo letterale presente nella pagina o nello snippet.
2. Solo fonti tier 1-2 (`data/source_tiers.json`). Le fonti tier3 servono solo per risalire alla fonte primaria.
3. `level: regional` per i cargos autonómicos: compaiono nella timeline ma non contano per il badge.
4. Gli `id` esistenti non si toccano mai: si aggiungono righe nuove. Una riga si corregge solo se è un errore, e va annotato nel report.
5. Dopo ogni modifica ai dati: `py scripts/build.py --check`, poi `py scripts/build.py`. Se ci sono errori ⛔ non si consegna nulla.
6. Il report finale elenca sempre: righe aggiunte, badge cambiati, pagine da ri-incollare in WordPress, dubbi aperti.

## Input
- Default: tutti i partiti, tutti i temi, novità da `collected_at` di ciascun file in `data/statements/`.
- Opzionale: un partito (`PP`), un tema (`nucleares`), un evento ("debate a 4 del 18 nov", "Foro Solar UNEF"), oppure "programas" quando escono i programmi del 29N.

## Workflow
1. Leggere `data/config.json`, `parties.json`, `topics.json`, `source_tiers.json` e il `collected_at` di ogni `data/statements/<slug>.json`.
2. Per ogni partito × tema in scope, cercare con `py scripts/serper.py search "<persona o partido> <keyword>" --tbs qdr:w` (`qdr:m` se l'ultimo aggiornamento ha più di 10 giorni). Persone = `key_people_verified` del file partito.
3. Per ogni candidato: escludere i domini tier3 e i falsi positivi, poi fare lo scrape (`py scripts/serper.py scrape <url>`). Se la pagina è bloccata, usare lo snippet e marcare `verified: snippet`.
4. Classificare la `stance` rispetto alla `proposition` del tema, con una riga di `rationale`. Verificare la data originale.
5. Aggiungere le righe al file del partito (schema in `data/SCHEMA.md`, `added_at` = oggi) e aggiornare `collected_at`.
6. **Modalità "programas"**: per ogni partito, PDF ufficiale del programma 29N → `type: programa`, `person` = nome del partito, `quote` = frase letterale pertinente per tema, `source_url` = URL del PDF (con `#page=N` se possibile).
7. `py scripts/verify_quotes.py --only-new <data di oggi>`: rilegge ogni fonte e controlla che la citazione ci sia parola per parola. Gestione esiti:
   - **NON TROVATA o PARZIALE**: aprire la fonte e correggere la citazione, oppure togliere la riga.
   - **BLOCCATA**: cercare la frase esatta tra virgolette su Google e controllare che almeno un'altra testata la riporti identica.
8. `py scripts/build.py --check` → correggere gli errori → `py scripts/build.py`.
9. Report (formato sotto).

## Output (report)
```
➕ Righe aggiunte: 7
  - PP · nucleares · 2026-11-18 · Feijóo (debate RTVE) · a_favor
  - ...
🔄 Badge cambiati (possibili ganci PR):
  - SUMAR|precio_luz_gas: sin_declaraciones -> a_favor
📝 Pagine WordPress da ri-incollare:
  - output/sumar/codice_testo.html
  - output/hub/codice_testo.html   (l'hub cambia SEMPRE se cambia un qualsiasi partito)
❓ Dubbi aperti: ...
```

## QA Gates
- [ ] `verify_quotes.py`: ogni riga nuova è OK, oppure BLOCCATA ma confermata da un'altra testata
- [ ] `build.py --check` senza ⛔
- [ ] Ogni riga nuova ha `source_url` funzionante e `quote` letterale verificata
- [ ] Nessuna voce regionale ha spostato un badge
- [ ] Gli avvisi ⚠️ "solo snippet" sono stati letti e accettati consapevolmente
- [ ] Le pagine da ri-incollare sono elencate

---
v0.1 — 2026-10-08. I Gotchas vanno aggiornati solo con evidenze dall'uso reale.

# Partidos × energía: elecciones generales del 29-N (papernest.es)

Base de datos de lo que **dicen, votan y prometen** los partidos españoles sobre luz, gas y modelo energético, pensada para las elecciones generales del **29 de noviembre de 2026**. Cada dato es una cita literal (o una votación nominal en el Congreso) con fecha, persona, cargo y enlace a la fuente original.

No damos cifras en la factura ni opinamos: recopilamos, verificamos y mostramos la **última posición registrada** de cada partido en cada tema, y señalamos cuándo ha cambiado.

> Estado (10 nov 2026): datos recogidos hasta el **8 oct 2026** (170 pruebas). Los programas electorales de 2026 aún no están incorporados. La dirección de diseño elegida es el prototipo **05 v2 · Portada**.

## Qué contiene

```
partidos-energia-es/
├── data/                        ← FUENTE ÚNICA DE VERDAD
│   ├── config.json              ← nombre de la herramienta, URL base, email de rectificaciones (placeholders)
│   ├── parties.json             ← partidos, candidatos y personas clave
│   ├── topics.json              ← temas y la «proposición» neutra de cada uno (borrador por validar)
│   ├── source_tiers.json        ← fuentes admitidas (tier 1-2) y excluidas
│   ├── SCHEMA.md                ← contrato de datos y reglas de cálculo de la posición (en italiano)
│   └── statements/<partido>.json← declaraciones, votaciones y programas, un archivo por partido
├── scripts/
│   ├── build.py                 ← valida los datos → calcula posiciones → genera el HTML para WordPress
│   ├── verify_quotes.py         ← comprueba que cada cita aparece literalmente en su fuente
│   ├── serper.py                ← búsqueda y scraping (API Serper; la clave NO está en el repo)
│   ├── hub_proposals.py         ← genera los prototipos 01-05 de la página principal
│   ├── hub_proposals_free.py    ← genera los prototipos 06-10 (conceptos libres)
│   └── mockups_db.py            ← 5 mockups de la versión «base de datos» (3 nov 2026)
├── skills/                      ← procedimientos para el agente (en italiano)
│   ├── aggiorna-dichiarazioni.md← actualización periódica de declaraciones
│   └── modifica-partiti-temi.md ← coaliciones, nuevos temas, cambios de proposición
└── output/                      ← GENERADO, no editar a mano
    ├── hub/, <partido>/         ← codice_intro.html + codice_testo.html listos para WordPress
    ├── preview/                 ← vistas previas para abrir en el navegador
    ├── proposte_hub/            ← prototipos de la página principal (abrir index.html)
    ├── mockups_db/              ← mockups de la versión «base de datos» (abrir index.html)
    ├── badges.json              ← estado de las posiciones, sirve para detectar cambios
    └── verify_quotes.json, verify_cache.json ← resultado y caché de la verificación de citas
```

## Cómo se usa

Requisitos: Python 3.10+ (solo librería estándar). Para buscar y verificar citas hace falta una clave de [Serper](https://serper.dev) en `../ZZ_file ENV/Keys/scraper` (fuera del repo, una clave por línea).

| Qué | Comando |
|---|---|
| Comprobar los datos sin escribir nada | `py scripts/build.py --check` |
| Regenerar las páginas tras cambiar los datos | `py scripts/build.py` |
| Verificar que las citas son literales | `py scripts/verify_quotes.py` (1 crédito Serper por URL nueva, luego caché) |
| Regenerar los prototipos de la portada | `py scripts/hub_proposals.py` y `py scripts/hub_proposals_free.py` |
| Regenerar los mockups «base de datos» | `py scripts/mockups_db.py` |
| Actualizar las declaraciones | pedir al agente: «Ejecuta partidos-energia-es/skills/aggiorna-dichiarazioni.md» |

`build.py` imprime siempre la matriz de posiciones y, a partir de la segunda ejecución, **las posiciones que han cambiado respecto a la anterior**: cada una es un posible gancho para prensa («el partido X ha cambiado de posición sobre Y»).

## Cómo se calcula la posición

Resumen de las reglas de `data/SCHEMA.md`, implementadas en `build.py` (`compute_badge`):

1. Solo cuentan pruebas de la **dirección nacional** (las regionales van solo a la cronología), de fuentes tier 1-2 y posteriores al inicio de la XV legislatura (17/08/2023).
2. «Periodo actual» = pruebas de los 180 días anteriores a la más reciente.
3. Si en el periodo actual hay pruebas a favor y en contra → **Ambiguo** (con aviso «dice / vota» si una es una votación y la otra una declaración).
4. Si una prueba más antigua dice lo contrario → **Cambió de posición**, con ventana antes → después.
5. Cambios no netos (p. ej. ambiguo → a favor) → «Su posición ha evolucionado», sin etiqueta en la posición.

Tipos de prueba: `declaracion`, `voto` (votación nominal en el Congreso), `programa` (programa electoral oficial) y `reportada` (el periodista resume con sus palabras: nunca entre comillas).

## Publicación en WordPress (papernest.es)

1. `codice_intro.html`: H1 e introducción en bloques Gutenberg. Pegarlo en el editor de código; si el tema ya imprime el título como H1, quitarlo del bloque.
2. `codice_testo.html`: un único bloque **HTML personalizado** con CSS y JS propios (prefijo `.ppe-`, `addEventListener`, sin fuentes externas ni plugins).
3. El contenido está **en el propio HTML**: Google lo indexa sin JavaScript. El JS solo sirve para los filtros.

## Decisiones de proyecto

**8 oct 2026, primera versión**
- Observatorio permanente, URL sin año.
- Posición por partido × tema respecto a una proposición neutra, sin rankings ni valoraciones.
- Páginas nativas en papernest.es, no un iframe.
- Diferenciación frente a otros comparadores: **declaraciones recientes de las personas clave y votaciones**, no solo los programas de 2023.

**3 nov 2026, versión «base de datos» (aún no aplicada a `data/`, solo en `mockups_db.py`)**
- Se abandona la cifra en euros en la factura: no es objetiva.
- La posición se muestra como **«Última posición registrada»**, siempre con fecha y pruebas.
- Se añaden los programas 2026, la comparación de programas 2023 → 2026 y el aviso «dice / vota».
- **5 partidos:** PSOE, PP, Vox, **Frente Amplio** (coalición de IU, Más Madrid, Comuns y Movimiento Sumar, que hereda el historial de Sumar con nota metodológica) y Podemos. SALF queda fuera.
- **10 temas:**
  - TUR del gas se integra en «Precio de la luz y el gas», y autoconsumo en «Renovables».
  - Centros de datos y coche eléctrico solo aparecen en la cronología, sin posición.

## Antes de publicar

- [ ] Nombre de la herramienta, URL base y email de rectificaciones en `data/config.json`
- [ ] Proposiciones de los temas validadas (`data/topics.json`)
- [ ] Revisión de la metodología por Legal / PR ES (herramienta política en periodo electoral)
- [ ] Datos actualizados desde el 8 oct y programas 2026 incorporados
- [ ] Decisiones del 3 nov aplicadas a `data/` y a la portada 05 v2
- [ ] Lectura por un hablante nativo de las páginas en `output/preview/`
- [ ] `py scripts/build.py --check` sin errores

# old/: «La factura en juego» (archivado)

Versión monetaria de la herramienta, trabajada entre el 8 y el 13 de octubre de 2026 y **abandonada el 3 de noviembre de 2026**. Traducía las propuestas de cada partido en euros en la factura de luz y gas («Tu voto vale hasta X € en la factura»). Se descartó porque la cifra depende de supuestos (precio, duración de las medidas, consumo tipo) y no se puede presentar como un dato objetivo. La herramienta activa es la base de datos de declaraciones descrita en el [README principal](../README.md).

Se guarda como referencia: método, modelos y fuentes pueden reutilizarse.

## Contenido

| Ruta | Qué es |
|---|---|
| `scripts/calc.py` | Calcula el efecto en € por partido, tema y perfil de hogar → `data/euro_matrix.json`. Las reglas de método están al principio del archivo |
| `scripts/build_factura.py` | Genera la página «La factura en juego» (vuelve a lanzar `calc.py`) → `output/factura/` |
| `scripts/test_calc.py` | Comprobaciones del cálculo |
| `scripts/merge_answers.py` | Integra las respuestas por pregunta (`data/answers/`) en `data/statements/` |
| `scripts/sync_oscar.py`, `scripts/inspect_models.py` | Leen los modelos Excel del Termómetro Energético (PR ES) |
| `data/questions.json` | 25 preguntas por tema (borrador) |
| `data/answers/` | Respuestas por pregunta, con nivel de evidencia 1/2/3 y valor |
| `data/bill_model.json` | Modelo de factura (hogar tipo y hogar vulnerable) |
| `data/baseline_2027.json` | Escenario normativo a 1/1/2027 (BOE): qué medidas caducan el 31/12/2026 |
| `data/impacted.json` | Hogares afectados por medida (CNMC, INE) |
| `data/model_excepcion_iberica.json`, `data/model_nuclear.json` | Modelos de la «excepción ibérica» y del calendario nuclear |
| `data/euro_matrix.json` | Resultado del cálculo |
| `docs/HANDOFF_bill_model.md` | Traspaso del modelo de factura del Termómetro |
| `output/factura/` | Última página generada (13 oct 2026) |

## Últimos números (13 oct 2026)

Horizonte: legislatura de 4 años. Precio: media PVPC 2021-2026.
- Hogar tipo: hasta **958 €** de diferencia entre partidos (Vox frente a PSOE).
- Hogar vulnerable: hasta 672 €.
- Escala nacional: 4.750 M€ al año.

Con el modelo del Termómetro a 12 meses, la diferencia era de 213 € para el hogar tipo y de 128 € para el vulnerable. **No son cifras publicables**: el modelo de factura seguía marcado como provisional y la fuente de la posición de PP y Vox sobre la TUR no era primaria.

## Cómo volver a ejecutarlo

Los scripts calculan sus rutas desde su propia carpeta y `build_factura.py` importa `build.py`, así que **no funcionan desde `old/`**. Para relanzarlos, copia el contenido de `old/` sobre la raíz del proyecto (misma estructura de carpetas) y ejecuta `py scripts/build_factura.py`. Los scripts que leen Excel necesitan `openpyxl`.

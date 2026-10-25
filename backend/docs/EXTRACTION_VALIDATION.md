# Paso 6: reglas e informe de validación

`src/rag/extraction_validation.py` compone especificaciones de contrato,
política de estrategias y límites/texto de secciones. Las reglas compartidas de
tablas, representación textual y elegibilidad están en `extraction_rules.py`.
El informe se guarda separado; `extraction.json` conserva su formato v1.

| Estado | Significado | Consecuencia |
|---|---|---|
| `accepted` | Estructura coherente con las reglas automáticas | Puede aportar evidencia textual; no certifica fidelidad semántica ni aprobación humana. |
| `review` | Dependencia gráfica, glifos sin resolver, estructura deshabilitada o continuación sin confirmar | Consultar la elegibilidad por bloque. Se conserva la fuente para revisar. |
| `error` | Contrato, procedencia, referencias, orden/límites o texto reconstruido incoherentes | Se bloquea toda construcción de unidades del documento. |

Los contratos comprueban filas/columnas, coordenadas, IDs, auditoría de páginas,
perfil y jerarquía. Las especificaciones añaden orden de secciones, asignación
por posición y coincidencia exacta entre texto de sección y bloques. Las trazas
aportadas deben referir al mismo documento y a páginas válidas.

Las celdas vacías o combinadas no se rellenan. Una tabla marcada indexable con
celdas ambiguas se rechaza. Las tablas gráficas conservan sus datos y motivos;
no producen filas textuales y siguen declaradas como dependencias visuales del
texto próximo. Los glifos `U+FFFD` y `(cid:...)` excluyen el bloque afectado de
las unidades y del contexto de antecesores. Esta detección es parcial: su
ausencia no demuestra que todos los caracteres se hayan extraído correctamente.

Una política `text_only` conserva texto para revisión, pero excluye de evidencia
los bloques de la página afectada hasta revisar la estructura perdida. Si solo
una región deshabilita tablas, la exclusión actual también abarca toda esa
página, de forma conservadora. La decisión se deriva del perfil guardado, sin
depender de que exista una traza externa.

Una continuación pendiente pone la tabla en `review`, pero permite indexar sus
filas completas independientes cuando no tienen otros motivos de revisión.
No se unen filas ni se infieren relaciones entre páginas. En Ricoh hay 62
candidatos; dos coinciden con tablas gráficas ya excluidas.

## Uso y bloqueo

```python
from src.rag.extraction_validation import evaluate_extraction, require_valid_extraction

report = evaluate_extraction(result, strategy_trace)  # Diagnóstico sin mutación.
report = require_valid_extraction(result, strategy_trace)  # Lanza ante error.
```

`require_valid_extraction` conserva `pydantic.ValidationError` para errores del
contrato; los errores adicionales generan `ExtractionValidationError`, con
`.report`. El pipeline ejecuta estas reglas antes de devolver su resultado.
`external_chunking.evidence_units` vuelve a validar cada documento versionado y
usa exclusivamente los bloques elegibles, también para el contexto. La interfaz
histórica de entradas parciales en memoria conserva compatibilidad y aplica
reglas por bloque; no equivale a validar un documento v1 completo.

`safe_indexing_allowed=true` autoriza únicamente el subconjunto identificado en
`eligible_block_ids`; no autoriza todos los bloques en revisión. Ante cualquier
error, la lista elegible queda vacía. El informe incluye `block_counts`, motivos,
página/sección/bloque, hash de la extracción y estado documental. No sustituye
la comprobación de bytes del PDF: esa verificación corresponde a la etapa de
fuente y al comprobador de línea base. Tampoco interpreta figuras ni acredita
revisión humana o calidad de respuestas RAG.

Desde `backend`, para producir archivos nuevos en un directorio separado:

```bash
../.venv/bin/python -m scripts.extract_real_manual --output /tmp/ti-ricoh-validation-step6
```

El CLI añade `validation_report.json` y su checksum/estado/conteos a
`summary.json`. Valida antes de escribir los artefactos de éxito. Si falla la
extracción o validación, escribe un `validation_failure_<UTC>.json` exclusivo y
relanza la excepción con salida fallida; no publica una extracción parcial.
Los artefactos anteriores del directorio se conservan: comprobar el fallo y
sus timestamps antes de interpretar un resumen de una ejecución anterior.
El informe de ejecución fallida no copia el mensaje arbitrario de excepción
ni el texto fuente; registra tipo y notas de etapa. Si una especificación ya
produjo un informe, se conserva ese diagnóstico.

## Verificación del 24-10-2026

- 14 pruebas nuevas y 326 unitarias correctas. Sin nueva suite API.
- Extracción completa nueva en `/tmp/ti-ricoh-validation-step6`, idéntica byte a
  byte a la referencia: SHA-256
  `ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44`.
- Informe Ricoh: 1.673 bloques `accepted`, 66 `review`, cero `error`;
  1.733 elegibles y seis tablas gráficas excluidas. `review` no es revisión humana.
- Las 498 unidades reconstruidas mantienen el hash del índice local guardado;
  nueve archivos de referencia y línea base congelada intactos.
- Evidencia técnica local ignorada:
  `docs/rag_runs/extraction_validation/check_20261024.json`.

Sin proveedores, embeddings, escrituras Supabase ni cambios de índice activo.
El siguiente paso pendiente es evaluar nuevas muestras complejas (paso 7).

Actualización posterior: el paso 7 incorporó columnas/tablas sin bordes
explícitas y OCR separado para revisión. La validación también verifica
geometría/orden de bloques en columnas y rechaza marcadores internos ambiguos.
Véase [COMPLEX_PDF_EVALUATION.md](COMPLEX_PDF_EVALUATION.md); la evaluación con
otros PDF reales quedó diferida por indicación del usuario.

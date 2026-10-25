# Tiempos por etapa

Instrumentación `stages-v1`, en segundos de reloj monotónico (`perf_counter`).
Cada consulta mide trabajo realmente ejecutado; no se añaden esperas artificiales.

## Dónde leerlos

- API `POST /api/v1/rag/query/` y `POST /api/v1/rag/search/`:
  campo `tiempos_segundos`. Swagger documenta el campo.
- Pipeline: `result["rag"]["timings"]`, versión en `rag.timing_version`.
- Regresión: cada traza y `summary.json`; `timings.csv` tiene una fila por caso,
  con estado, etapa de fallo y columnas de segundos sin redondear.

Para exportar una nueva ejecución real, desde backend:

```sh
../.venv/bin/python -m scripts.validate_rag_scenarios --output docs/rag_runs/timing_validation
```

La regresión consulta Supabase y Groq y consume cuota. Los reportes anteriores
no se modifican ni reciben mediciones reconstruidas.

## Qué mide cada campo

| Campo | Trabajo incluido |
|---|---|
| `ocr_seconds` | Preparación de entrada; ejecuta OCR solo si existe una imagen. |
| `classification_seconds` | Clasificación, validación del clasificador y esperas/reintentos de sus llamadas. |
| `embedding_seconds` | Vector de la pregunta, incluido tokenizado y comprobaciones. |
| `semantic_search_seconds` | `repository.search`: RPC, transferencia y conversión a candidatos en Supabase; búsqueda exacta cuando se usa LocalRepository. No es tiempo interno exclusivo del servidor. |
| `lexical_fetch_seconds` | Lectura paginada y conversión del corpus autorizado compatible; en local, selección de candidatos en memoria. |
| `bm25_seconds` | Tokenización, estadísticas del corpus, cálculo BM25, ordenación y corte léxico. El índice léxico actual se construye por consulta. |
| `rrf_seconds` | Unión, contribuciones por posición, ajuste por categoría, ordenación y selección Top-k. |
| `candidate_scoring_seconds` | Preparación final y embeddings/cosenos adicionales de resultados exclusivamente léxicos seleccionados. |
| `retrieval_seconds` | Subtotal de las cinco etapas anteriores a partir de búsqueda semántica; excluye el embedding de pregunta. Conserva el significado del campo anterior. |
| `context_seconds` | Preparación del contexto y comprobaciones de presupuesto durante selección. |
| `generation_seconds` | Generación inicial, incluyendo espera/reintentos si llama al proveedor; si se aplica aclaración local, mide esa construcción local. Consultar `generation_source` en la traza. |
| `generation_correction_seconds` | Generación correctiva cuando se ejecuta; sus esperas/reintentos se incluyen. |
| `validation_seconds` | Validaciones documentales inicial y correctiva acumuladas. |
| `support_review_seconds` | Revisiones de respaldo inicial y posterior a corrección acumuladas, con llamadas/reintentos internos. |
| `total_seconds` | Duración total de `run_rag_case`, incluida coordinación y comprobaciones no asignadas a una etapa. |

`retrieval_seconds` contiene sus subetapas y `total_seconds` contiene el pipeline.
**No sumar todos los campos**, pues duplicaría esos intervalos. La suma de las
hojas puede ser menor al total por coordinación y serialización intermedia.

Los tiempos del pipeline excluyen arranque del servidor, carga inicial del modelo,
comprobación/restauración del índice y autenticación Supabase anterior al pipeline
(`api.services.retriever`). No representan la latencia HTTP completa. La búsqueda
simple solo publica las etapas del recuperador; no incluye clasificación/generación.

## Fallos y etapas opcionales

El cronómetro guarda la duración incluso si la operación lanza una excepción.
La traza mantiene `state` y `failure_stage`; esa duración mide un intento fallido,
no una búsqueda válida. Las etapas que no se ejecutaron no aparecen y sus celdas
CSV quedan vacías, sin inventar ceros. Una aclaración local no ejecuta el revisor
ni necesita una corrección documental.

## Verificación

- Pruebas con reloj controlado comprueban separación I/O/BM25, duración en fallo,
  acumulación de dos revisiones, generación correctiva y CSV con campos vacíos.
  Sus tiempos de control no son mediciones del modelo.
- `stage_timing_validation.json` contiene una verificación local con embeddings
  reales, mismo índice de 70 registros y 13 preguntas; el ranking y los puntajes
  coinciden exactamente con el recuperador previo. Arranque y calentamiento
  quedaron fuera de esos tiempos. No es un benchmark de latencia remota.

Esta instrumentación cubre el registro por etapa pendiente de clase 09. La
comparación descriptiva posterior entre variantes está en `TIMING_COMPARISON.md`;
las métricas de recuperación se documentan en `RETRIEVAL_METRICS.md`. Los tiempos
compartidos del experimento no constituyen un benchmark HTTP independiente.

La comprobación HTTP real posterior al despliegue (`stage_timing_validation.json`)
obtuvo 200 en búsqueda y consulta. En esa consulta, `total_seconds` fue 7,5787 s
frente a 8,4919 s HTTP; búsqueda semántica 4,3515 s, lectura léxica 0,1887 s,
BM25 0,0056 s y RRF 0,000040 s. Son observaciones de una ejecución, no promedios
ni una comparación entre estrategias. Las 25 pruebas API también pasaron en la
nueva imagen, además de 239 unitarias y 25 API locales.

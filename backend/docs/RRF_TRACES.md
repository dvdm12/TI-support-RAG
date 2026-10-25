# T7 - Rankings y aportes RRF

El export `rrf_traces_20261025.json/.csv/.pdf` explica los trece casos de desarrollo:
ranking semántico Top-10, ranking BM25 Top-10, unión por `chunk_id`, posiciones,
aportes por rama, puntaje fusionado, filtro de aplicabilidad y selección final.
Las trece selecciones coinciden exactamente con la híbrida v2 guardada.

## Procedencia y alcance

Se reutiliza el ranking semántico real de `retrieval_metrics_20261021.json` y
se recalcula BM25 localmente sobre los 70 fragmentos del índice congelado. Se
comprueban hashes de índice y anotaciones, así como el vínculo entre el informe
base y `coverage_improvements_20261021.json`. No se carga ningún modelo, ni se
llama a Supabase/Groq ni se abre la reserva. Esto es reproducción offline, no una
medición nueva de HTTP, latencia, calidad de respuesta o generalización.

Se exportan únicamente campos explícitos del inventario y los informes locales,
sin leer `.env`, encabezados HTTP ni credenciales. El JSON registra los hashes
de entradas y código. Los seis casos de comportamiento se conservan para
inspección: no tienen denominador de calidad de recuperación.

## Fórmula y ejemplo de la diapositiva 3

Las posiciones empiezan en 1. Cada rama aporta `peso / (60 + posición)`; una
rama ausente aporta cero. Se conserva una sola fila por `chunk_id`, incluso
si aparece en ambas ramas. Desempate: ID ascendente.

La diapositiva usa pesos iguales: semántica A,B,C y léxica C,A,D. La prueba
verifica A,C,B,D con 0,032522 / 0,032266 / 0,016129 / 0,015873 (seis decimales).
El sistema vigente usa pesos 1 semántico y 2 léxico; no se confunde con el ejemplo.

`rrf_score` suma los dos aportes; `category_boost` registra separadamente el
ajuste opcional 0,025. `selection_score` suma ambos. En el export la categoría
es `null`, de modo que el ajuste es cero. `applicable` y `exclusion_reason`
explican exclusiones antes de Top-3; `selected_rank=null` significa no seleccionado,
por exclusión o por quedar fuera del corte. Los puntajes RRF no son probabilidades.
El coseno guardado tampoco es un puntaje BM25.

## Implementación y uso

`fuse_rankings` y `select_ranked_candidates` en `src/rag/retrieval.py` son compartidos
por producción y el export; no hay una segunda fórmula exclusiva del informe.
El recuperador admite `retrieve(..., trace={})` como salida opcional de diagnóstico,
sin cambiar su retorno `(candidates, timings)` ni el contrato HTTP público. Esa traza
no añade lecturas de repositorio. El cálculo posterior del coseno para resultados
solo léxicos conserva el comportamiento anterior.

Desde `backend`:

```sh
../.venv/bin/python -m scripts.export_rrf_traces --output /tmp/rrf_traces_copy.json
../.venv/bin/python -m unittest test.test_rrf_traces
```

El export rechaza sobrescribir salidas existentes. JSON conserva listas completas
y parámetros; CSV tiene una fila por candidato de cada unión; PDF incluye ejemplo
y tablas por caso con secciones/IDs abreviados, remitiendo a JSON/CSV para IDs completos.
Las pruebas verifican el ejemplo de clase, ponderación vigente, ausencias,
desempates, IDs únicos, exclusiones, ajuste por categoría, traza de producción,
integridad de índice y coincidencia de las trece selecciones.

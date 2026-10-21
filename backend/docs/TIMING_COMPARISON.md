# Comparación de tiempos de recuperación

El módulo compara A (semántica) y B (semántica + BM25 + RRF) a partir de las
mediciones guardadas. No carga modelos ni llama a Supabase o Groq.

## Uso y salidas

Desde `backend/`, con las dependencias del proyecto:

```sh
../.venv/bin/python -m scripts.compare_retrieval_times
../.venv/bin/python -m scripts.compare_retrieval_times --input docs/retrieval_metrics_20261021.json --output docs/comparacion.json
```

La salida predeterminada es `docs/retrieval_metrics_20261021_times.json`,
acompañada siempre por CSV y PDF con el mismo nombre base. El archivo de entrada
se conserva. El PDF actual tiene tres páginas revisadas visualmente.

- `src/rag/timing_comparison.py`: validación, estadísticas y comparación emparejada.
- `scripts/compare_retrieval_times.py`: CLI y exportación de los tres formatos.
- `PDFReport.generate_timing_comparison` en `src/pdf_report.py`: informe con
  agregados, etapas, preguntas y trazabilidad, reutilizando el módulo existente.

## Resultado observado

Trece pares válidos y ninguno excluido. Tiempos en milisegundos:

| Estadística | A semántica | B híbrida |
|---|---:|---:|
| Media | 200,90 | 409,30 |
| Mediana | 188,37 | 398,69 |
| P95 | 291,13 | 555,66 |
| Mínimo | 149,72 | 319,16 |
| Máximo | 295,12 | 636,65 |

La mediana de las diferencias emparejadas B−A es **208,77 ms**; la mediana de
sus incrementos relativos es **112,35%**. Esta última se calcula por pregunta,
no dividiendo las medianas agregadas. Si A es cero, se conserva la diferencia
absoluta y el incremento relativo queda sin evaluar.

| Etapa, mediana en ms | A | B |
|---|---:|---:|
| Embedding de pregunta | 40,643 | 40,643 |
| Búsqueda semántica | 147,740 | 147,740 |
| Lectura del corpus léxico | N/E | 203,683 |
| BM25 | N/E | 4,486 |
| RRF | N/E | 0,023 |
| Puntajes adicionales | N/E | 0,006 |
| Coordinación derivada | N/E | 0,036 |

La lectura del corpus léxico concentra el costo adicional típico observado.
Las medianas de etapas no son aditivas. No se aplicaron optimizaciones ni cambios
al recuperador desplegado como parte de esta comparación.

## Alcance y cálculo

A suma embedding y búsqueda semántica; B suma embedding y el subtotal de
recuperación híbrida. No se vuelven a sumar las etapas contenidas en el subtotal.
La coordinación se deriva restando las etapas medidas a ese subtotal.

Los grupos separan todos los casos (13), documentales (7) y comportamiento (6).
Los seis de comportamiento sí sirven para tiempos, aunque no tienen métricas
de calidad documental. La mediana documental A/B es 188,38/401,05 ms; por eso
no debe confundirse con la mediana de los 13 casos de la tabla principal.

Se informa número de observaciones, media, mediana, P95, mínimo, máximo y suma.
P95 usa interpolación lineal en la posición `(n−1) × 0,95`; con 13 observaciones
es descriptivo y no acredita estabilidad de la cola de latencia.

Las variantes comparten embedding y búsqueda semántica medidos en el experimento
original, con una observación por pregunta conocida de desarrollo. Los componentes
se midieron secuencialmente; no son ejecuciones independientes completas de A y B.
Se excluyen autenticación previa, carga y calentamiento del modelo, generación
y latencia HTTP completa. No se infiere calidad de respuestas de estos tiempos;
ver `RETRIEVAL_METRICS.md` para el intercambio de calidad de recuperación.

## Integridad y errores

El JSON conserva fecha de medición original, huella SHA-256 de entrada, huellas
del código, protocolo y diferencias por caso. El PDF incorpora la huella del JSON
de comparación. El CSV contiene 26 filas, una por caso y variante; las etapas
no aplicables quedan vacías y se muestran como N/E en el PDF.

Una duración ausente, negativa, no finita o incompatible con los subtotales
excluye el par completo de los agregados. Se conservan estado, diagnóstico y
contadores. Una fuente incompleta produce informe incompleto y código de salida
1 después de exportar JSON, CSV y PDF. Un fallo de PDF se propaga.

Se añadieron seis pruebas del módulo: estadística, componentes compartidos,
entradas inválidas, denominador cero, grupos/protocolo y exportación incompleta.
La suite local completa pasó **252 pruebas**. También se recalcularon de forma
independiente los agregados y se comprobaron la huella de entrada y las 26 filas
CSV. No se hicieron llamadas nuevas a proveedores para generar estos informes.

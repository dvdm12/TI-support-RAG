# Auditoría del segundo corte — Clase 09

Fecha: 20-10-2026. Revisión del repositorio en `e5be392`.
Resultado: **cumplimiento parcial**. El backend funcional está validado; todavía
no está completa la evaluación comparativa ni la entrega consolidada del corte.

## Fuentes y alcance

Material local del curso, fuera del repositorio:

- `../../Clase-09/Clase_09_RevealJS/index.html`: diapositivas 6 (conjunto),
  8–10 (recuperación y respuestas), 12 (rúbrica), 15 (demo), 16–17 (entrega).
  Líneas 241–257, 360–426, 502–520, 563–583, 650–667 y 685–765.
- `../../Clase-09/Clase_09_Demo_Colab_Mejora_Evaluacion_RAG.ipynb`:
  celdas 8–19 (anotación, variantes, métricas y reserva), 22–28
  (generación, revisión, evidencia y trabajo del equipo).

Se contrastaron código, notebooks y reportes existentes. No se ejecutaron nuevas
llamadas a proveedores, pruebas, escrituras en Supabase ni modificaciones del
backend. Los resultados de ejecución citados pertenecen a sus reportes previos.
No se verificó el acceso del profesor a GitHub ni se ejecutó Colab.

La presentación exige una base y **al menos una mejora pertinente** (líneas
737 y 760); no obliga a implementar todas las técnicas. El laboratorio sí enseña
A semántica, B híbrida y C con reranker. Se puede entregar una comparación A/B
justificada sin incorporar C a producción. Las fuentes revisadas no fijan un
umbral mínimo numérico para estas métricas ni porcentajes institucionales.

## Métricas de recuperación

| Criterio del curso | Estado del RAG activo | Evidencia y pendiente |
|---|---|---|
| Precision@3: relevantes seleccionados / 3 | Pendiente | No hay cálculo sobre el corpus activo con IDs relevantes anotados. No sustituir por porcentaje de tests. |
| Recall@3: relevantes seleccionados / relevantes anotados | Pendiente | Falta el conjunto completo de fragmentos relevantes por pregunta; un prefijo de sección no aporta ese denominador. |
| Hit@3: al menos un relevante | Parcial | La regresión comprueba presencia de una sección esperada entre candidatos para algunos casos, no un benchmark completo anotado por fragmento. |
| MRR: promedio del inverso del primer rango relevante | Pendiente | No se calcula para el corpus activo. |
| Cobertura de unidades de información | Pendiente | Faltan unidades requeridas y sus IDs alternativos; no se mide si llegaron todas las condiciones al contexto final. |
| Cobertura de candidatos frente a contexto final | Pendiente | La traza conserva candidatos/contexto, pero no calcula cobertura en ambas etapas. |
| Latencia desglosada | Parcial | Hay embedding, recuperación, contexto, generación y revisión; RPC, lectura/BM25 y fusión están agrupados en recuperación. Falta comparativa por alternativa. |
| Tokens del proveedor | Cumple como registro disponible | Las trazas reales registran usage por llamada; falta presentarlo junto a alternativas comparables y exportar evidencia compartible. |
| Errores separados de falta de evidencia | Cumple en la regresión existente | Estados técnicos/formato y bloqueo por cuota son explícitos. Las abstenciones seguras quedan diferenciadas de respuestas aprobadas por el revisor. |

`docs/evaluacion/validaciones/backend_validation.json` acredita **13/13 criterios de comportamiento**,
234 unitarias y 24 API. No acredita Precision@3, Recall@3, MRR ni cobertura.
De esos 13 casos, ocho tienen `MODEL_SUPPORTED`, tres `LOCAL_CLARIFICATION`
y dos un reemplazo seguro tras `MODEL_REJECTED` (E07/E09).

`docs/extractor/ricoh_local_retrieval_validation.json` sí contiene Hit@3 y MRR@3 para
12 preguntas del índice Ricoh local (11/12 Top-3 en la mejor variante). Ese
corpus está fuera de la API y no es la comparación del RAG académico activo.
No mezclar sus resultados con los 13 casos de regresión del backend.

## Evaluación y comparación

| Requisito | Estado | Hallazgo |
|---|---|---|
| Preguntas propias, entre 12 y 20 como ejercicio inicial | Parcial | Hay 13 casos reales de regresión y ocho de comparación de cortes; falta un conjunto de recuperación con anotación completa, comportamiento esperado y familias. |
| Directas, paráfrasis, condiciones, ambigüedad y sin cobertura | Parcial | Existen ejemplos repartidos entre `cases/rag_questions.json`, `rag_regression.json` y el notebook de clase 08. No están reunidos en el protocolo comparativo final. |
| Evidencia definida leyendo fuentes antes del ranking | Parcial | Secciones y algunas condiciones anotadas; faltan unidades e IDs de todos los pasajes relevantes y revisión de esa anotación. |
| Desarrollo y reserva independientes | Pendiente | Los conjuntos existentes no contienen grupos de desarrollo/reserva. Los 13 casos se usaron para ajustar y no deben presentarse como reserva independiente. |
| Base semántica frente a una mejora con todo lo demás fijo | Pendiente | El recuperador activo combina semántica, BM25 y RRF con ajuste por categoría, pero no hay experimento controlado A/B del mismo corpus, preguntas, prompt y generador. |
| BM25 y RRF implementados | Cumple como implementación | `src/rag/lexical.py` contiene una variante BM25 y `retrieval.py` fusiona la unión por ID con constante 60 y desempate por ID. |
| Trazabilidad de rankings y contribuciones | Parcial | Se conservan candidatos finales, pero el recuperador activo no exporta rankings semántico/léxico separados y aportes RRF por candidato para la comparación. |
| Reranking | No implementado; opcional para la entrega | No se encontró CrossEncoder ni variante C. Solo sería pendiente obligatorio si elegimos reproducir el demo completo A/B/C. |
| Revisión humana de respuestas y citas | Pendiente | El revisor es otro llamado de modelo. No hay una ficha actual completada por personas ni comparación independiente entre dos integrantes. La bitácora histórica del primer corte no acredita la revisión de las respuestas actuales. |
| Conclusión y decisión comparativa | Pendiente | `docs/evaluacion/recuperacion/rag_comparison.json` compara fragmentación, no A/B de recuperación; `winner` es null y `semantic_review` sigue PENDIENTE. |

La implementación léxica normaliza tildes, elimina stopwords (incluidas `no`,
`sin`) y aplica una reducción de plurales. Difiere del baseline transparente del
demo. Esto no demuestra por sí solo incumplimiento de la entrega, pero exige
registrar la configuración y revisar negaciones/códigos. El ajuste por categoría
(`+0.025`) también debe documentarse o mantenerse controlado al comparar.

## Entregables y funciones previas

| Requisito | Estado | Evidencia o pendiente |
|---|---|---|
| Clasificación original, entrada libre, contratos y errores | Cumple en el backend | Prompts versionados, SolicitudTI/RespuestaRAG, API query y políticas; evidencia de dos HTTP reales y suite de regresión. |
| Corpus, extracción, fragmentación, embeddings y persistencia | Implementado y con evidencia previa | Siete manuales académicos, manifiestos, ingestor, índice, RPC/Supabase, documentación y SQL en infra. Falta integrarlo en la evidencia final consolidada. |
| OCR/modalidad anterior integrado en la demostración final | Parcial | Existen OCR y parámetro `image_path` del pipeline; la regresión final de 13 casos fue textual y el notebook deja OCR desactivado. No falta agregar OCR HTTP: eso no es un requisito docente. |
| Notebook final ejecutable en Colab sin ejecutar otros notebooks | Pendiente | Los notebooks dependen del checkout local. El de clase 08 exige que el kernel sea exactamente `.venv` del proyecto y no instala dependencias. No hay ejecución final demostrada en Colab con bootstrap y secretos. |
| README y bitácora del segundo corte | Parcial | README raíz describe ejecución, pero no identifica al equipo; backend/README y bitácora siguen anunciando Parcial 1 y system_v4. La configuración real es system_v7/rag_v5. La continuidad en .agents no reemplaza la bitácora de entrega. |
| Presentación final en PDF | No acreditada | Existe `docs/parcial1/model_results_report.pdf` vinculado al primer corte, pero no se identificó una presentación final del segundo corte con comparación, decisión y fallos. No se revisó visualmente ese PDF en esta auditoría. |
| Repositorio accesible al profesor | Por confirmar | GitHub y rama publicados; no se verificaron los permisos particulares del profesor. |
| Evidencia final reproducible y compartible | Parcial | Hay documentación y reportes versionados; las trazas completas están ignoradas. Falta un export limpio con anotaciones, variantes, rankings, contexto, respuestas, revisión humana, métricas y versiones. |

El notebook de clase 08 también tiene una incoherencia verificable: su texto
anuncia red desactivada, pero las variables `CONNECT_SUPABASE` y
`RUN_GROQ_QUERY` están True. Su cierre conserva pendientes históricos ya resueltos
(regresión completa). Requiere revisión antes de considerarlo entrega final.

## Prioridad para cerrar el corte manteniendo el proyecto simple

1. Congelar el corpus académico y los parámetros. Anotar 12–20 preguntas por
   familias, con desarrollo y reserva nueva, IDs relevantes y unidades necesarias.
2. Medir A semántica frente a B híbrida actual: Precision@3, Recall@3, Hit@3,
   MRR, cobertura y tiempos. Mantener controlado el ajuste por categoría.
3. Comparar respuestas con el mismo prompt/generador y completar revisión humana
   de afirmaciones/citas, incluyendo una muestra revisada por dos integrantes.
4. Registrar la decisión y abrir la reserva sin usarla para reajustar.
5. Consolidar notebook Colab, README/bitácora y presentación PDF; exportar las
   evidencias sin secretos y confirmar acceso del profesor.

No hace falta frontend, incorporar el manual Ricoh ni agregar un reranker para
resolver estas brechas mínimas. La comparación A/B puede justificar conservar la
opción más sencilla si la mejora no aporta.

## Actualización 21-10-2026: instrumentación por etapa

Se implementó `stages-v1` con separación de búsqueda semántica/RPC, lectura del
corpus léxico, cálculo BM25 y fusión RRF, además de los tiempos del pipeline.
API, trazas y export CSV publican esas observaciones. Se conserva el tiempo de
intentos fallidos, se acumulan revisiones repetidas y se omiten etapas no ejecutadas.
Ver `STAGE_TIMINGS.md` y `stage_timing_validation.json`. La fila de latencia de la
auditoría anterior queda superada respecto a instrumentación; la comparación de
latencias entre alternativas continúa pendiente. No cambia el estado de las
otras métricas ni acredita el conjunto de reserva o la revisión humana.

## Actualización 21-10-2026: evidencias anotadas

`cases/rag_evidence.json` fija las anotaciones del agente para las 13 preguntas
existentes, con condiciones, criterios de fallo, IDs relevantes, citas y offsets:
siete casos documentales, 35 unidades y seis casos solo de comportamiento. La
integridad se contrastó con los siete PDF originales y 70 fragmentos mediante
`scripts/validate_rag_evidence.py`; ver `docs/evaluacion/validaciones/rag_evidence_validation.json` y
`docs/rag/RAG_EVIDENCE.md`. No se anotaron respuestas del modelo como verdad fuente.
La anotación no es ciega: todas las preguntas ya participaron en desarrollo.
Quedan pendientes revisión humana de relevancia/unidades y reserva nueva. Aún no
se ejecutó la comparación A/B ni se calcularon las métricas con estas anotaciones.

## Actualización 21-10-2026: cálculo de métricas y comparación A/B

Se calcularon las métricas de recuperación con Supabase real: 13 consultas sin
errores, siete casos documentales incluidos y seis de comportamiento excluidos.
Comparación A semántica / B híbrida sin ajuste de categoría ni etiquetas esperadas.
Precision@3 47,62%/52,38%; Recall@3 73,81%/80,95%; Hit@3 85,71% en ambas;
MRR@3 0,8571 en ambas; cobertura macro 78,21%/80,36%. Se midieron también contexto
tras presupuesto y tiempos de componentes compartidos. Ver `RETRIEVAL_METRICS.md`
y los archivos `retrieval_metrics_20261021.json` y `.csv`.

Quedan superadas las filas anteriores de métricas no calculadas y experimento A/B
pendiente. Persisten anotación sin revisión humana, casos conocidos de desarrollo,
reserva nueva, revisión humana de respuestas, decisión final y entregables. Los
resultados documentan una mejora en 403, una pérdida en Wi-Fi y un fallo en mensaje
sospechoso; no acreditan calidad generativa ni una configuración ganadora definitiva.

## Actualización 21-10-2026: comparación descriptiva de tiempos

Implementado el comparador de las mediciones A/B guardadas, por etapa, pregunta
y grupo, con media, mediana, P95 y diferencias emparejadas. Exporta JSON, CSV y
PDF automáticamente; ver `TIMING_COMPARISON.md`. En los 13 casos, medianas A/B
188,37/398,69 ms y mediana de diferencia 208,77 ms. La lectura léxica concentra
el costo adicional típico. Suite local: 252 pruebas correctas.

Queda cubierta la comparación descriptiva pendiente: sus componentes compartidos
y una observación por pregunta no acreditan latencia HTTP independiente ni
estabilidad con repeticiones. No hubo nuevas llamadas a proveedores. Persisten
los pendientes de revisión humana, reserva, decisión y entregables consolidados.

## Actualización 21-10-2026: estructura de reserva

Se prepararon 12 candidatos sin ejecutar: nueve documentales (25 unidades) y
tres límites documentales, con citas, expectativas y criterios de fallo. Ver
`RAG_RESERVE.md`, `cases/rag_reserve.json` y `rag_reserve_validation.json`. La
estructura y procedencia están verificadas localmente; ocho controles negativos
correctos. Pendientes revisión humana y de novedad semántica, decisión con
desarrollo, congelación, conexión al evaluador y primera evaluación registrada.
No hay métricas de reserva ni independencia por familias acreditada.

## Actualización 21-10-2026: cobertura completa y tabla consolidada

La tabla vigente de métricas está en `.agents/CLASS09_METRICS_STATUS.md` respecto
a la raíz del repositorio. Se cerró el primer parcial: proporción de preguntas
con todas sus unidades cubiertas. Top-3 A/B: 4/7 y 5/7; contexto: 3/7 y 4/7.
Reporte derivado JSON/CSV/PDF `retrieval_metrics_20261021_coverage`, conservando
las observaciones originales. Sin ejecución de reserva ni llamadas a proveedores.
259 pruebas unitarias locales correctas, incluyendo siete nuevas; PDF de cuatro
páginas inspeccionadas.

La revisión directa de las diapositivas también identifica pendientes explícitos
que no deben ocultarse dentro de una revisión genérica: cobertura de citas por
afirmación, tasa de abstención correcta y tasa de abstención innecesaria. Siguen
pendientes, junto con fidelidad/corrección/utilidad revisadas por personas y
comparación equivalente de tokens A/B. Esta tarea no los ejecutó ni acredita.

## Actualización 21-10-2026: mejoras aplicadas de cobertura

La híbrida mejorada normaliza términos técnicos, filtra aplicabilidad antes de
Top-3, pondera léxico 2 frente a semántica 1 y usa rag_v6 compacto. Comparación
offline sobre rankings semánticos reales guardados: siete casos documentales
completos en Top-3/contexto y 35/35 unidades. Ver `COVERAGE_IMPROVEMENTS.md` y
`coverage_improvements_20261021.*`. Es ajuste con desarrollo conocido, no prueba
independiente ni evaluación de respuestas. Nuevas latencias y tokens reales
comparativos quedan pendientes; las métricas históricas se conservan.
263 unitarias y 26 API pasan; tres búsquedas HTTP reales correctas tras despliegue.
Revisión humana, reserva congelada, generación/revisión de respuestas y
entregables de clase 09 siguen pendientes. No se llamó a Groq ni se abrió reserva.

## Actualización 21-10-2026: comparación generativa de tokens completada

Se midió usage real Groq de A semántica y B híbrida con el mismo rag_v6, modelo,
esquema y parámetros: siete pares, 14 llamadas HTTP 200, sin errores o usage
faltante. A 6.592 / B 6.523 tokens, medias 941,71/931,86. Ver
`GENERATION_TOKENS.md` y JSON/CSV/PDF `generation_tokens_20261021`.

Se cubre el pendiente de comparación **de generación**; no consumo total de
query, clasificación/revisión/corrección ni nuevas latencias completas. No se
abrió reserva. Los 14 contratos/citas estructuralmente válidos no prueban
fidelidad/corrección/utilidad: respuestas/contextos guardados para revisión humana.
270 unitarias locales correctas, siete pruebas nuevas; PDF de tres páginas
renderizadas e inspeccionadas. No hubo despliegue ni commit/push nuevos.

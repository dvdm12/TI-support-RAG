# Estado de métricas de clase 09 — 21-10-2026

Tabla contrastada con las diapositivas locales y las evidencias publicadas en
`aea3002`. «Calculada» acredita disponibilidad de la medida, no aprobación de
calidad. El curso no fija un umbral numérico mínimo. Desarrollo tiene siete casos
documentales evaluables y seis de comportamiento; las anotaciones siguen
pendientes de revisión humana. Reserva: 12 candidatos sin ejecutar.

## Lectura vigente para continuar

La comparación de tokens está completada para generación: 14 llamadas reales,
siete pares, A 6.592 / B 6.523 tokens. Las respuestas/contextos se conservan en
`backend/docs/generation_tokens_20261021.json`; no regenerar para revisarlos.
El siguiente pendiente es revisión humana de fidelidad, corrección, utilidad y
respaldo. Reserva sin ejecutar. Las mejoras de híbrida v2 y sus resultados se
identifican en su sección posterior; no confundirlos con la base histórica.

## Matriz base y estado de cada métrica

Las cifras A/B de recuperación de esta matriz corresponden al experimento
original; la comparación de generación usa la política/prompt actual, detallada
al final. No mezclar estos protocolos como si fueran una única ejecución.

| Métrica | Estado | Evidencia o pendiente |
|---|---|---|
| Precision@3 | Calculada | A 47,62% / B 52,38%. |
| Recall@3 | Calculada | A 73,81% / B 80,95%. |
| Hit@3 | Calculada | 85,71% ambas. |
| MRR@3 | Calculada | 0,8571 ambas. |
| Cobertura de unidades Top-3 | Calculada | A 78,21% / B 80,36%. |
| Cobertura del contexto final | Calculada | A 69,29% / B 76,79%. |
| Cobertura completa por pregunta | Calculada: primera tarea parcial terminada | Top-3 A 4/7 (57,14%) / B 5/7 (71,43%); contexto A 3/7 (42,86%) / B 4/7 (57,14%). JSON/CSV/PDF derivados sin nuevas consultas. |
| Latencia por etapa y comparación | Cubierta, descriptiva | Medianas documentales A 188,38 / B 401,05 ms; componentes compartidos, no latencia HTTP independiente. |
| Consumo de tokens | Medido para generación comparable | Groq real, siete pares: A 6.592 / B 6.523 tokens; mismo rag_v6/modelo/parámetros. Excluye clasificación, revisión y corrección. |
| Fidelidad, corrección, utilidad y respaldo de citas | Pendiente | Revisión humana comparativa y justificación por caso. |
| Cobertura de citas sobre afirmaciones | Pendiente | Calcular presencia por afirmación y revisar respaldo por separado. |
| Abstención correcta | Pendiente | Casos sin cobertura tratados correctamente / casos sin cobertura revisados. |
| Abstención innecesaria | Pendiente | Preguntas respondibles rechazadas sin justificación / respondibles revisadas. |

La restricción de no generar correspondía a la primera tarea de cobertura.
El usuario autorizó después el siguiente paso: la comparación generativa real
de tokens, completada y documentada abajo. La reserva sigue sin ejecutar;
revisión humana, congelación, decisión final y entregables continúan pendientes.

## Primera tarea parcial terminada

Cobertura completa exige todas las unidades necesarias, con al menos una evidencia
alternativa por unidad. El informe distingue completa/incompleta por pregunta y
etapa, cuenta unidades presentes y enumera IDs de unidades faltantes. Comportamiento
no evaluable y errores técnicos quedan fuera del denominador; no se vuelven ceros.

| Etapa | A completas | A incompletas | B completas | B incompletas |
|---|---:|---:|---:|---:|
| Top-3 | 4/7 (57,14%) | 3 | 5/7 (71,43%) | 2 |
| Contexto final | 3/7 (42,86%) | 4 | 4/7 (57,14%) | 3 |

E03 y E05 siguen incompletos en Top-3 para ambas variantes. E06 pasa a completo
con B. E04 pierde una unidad al formar el contexto en ambas. Esto no certifica
fidelidad ni calidad de una respuesta generada; las anotaciones aún requieren
revisión humana. No se modificaron corpus, anotaciones, rankings ni tiempos.

Archivos: `backend/docs/retrieval_metrics_20261021_coverage.json`, `.csv` y `.pdf`.
La matriz original y los informes de tiempos permanecen intactos. Comando desde
backend: `../.venv/bin/python -m scripts.summarize_complete_coverage`. Las futuras
evaluaciones también incluyen esta medida y conservan la exportación PDF.

Validación: siete pruebas nuevas, suite local completa 259 correctas; recalculo
independiente de casos completos, SHA-256 de origen y 26 filas CSV; cuatro páginas
PDF renderizadas y revisadas visualmente. Sin proveedores, generación o reserva.
Cambios locales posteriores a aea3002, sin nuevo commit/push ni despliegue.

Siguiente parcial de la tabla: comparación de consumo de tokens entre variantes
con generación equivalente. **No se inició** como parte de esta tarea.

## Mejora aplicada posteriormente: resultados actuales de desarrollo

La tabla inicial conserva la medición histórica semántica/híbrida anterior. La
híbrida mejorada se compara contra la híbrida anterior, sin reetiquetar esas
mediciones ni mezclar resultados con reserva.

| Métrica | Híbrida anterior | Híbrida v2 + rag_v6 |
|---|---:|---:|
| Precision@3 | 52,38% | 66,67% |
| Recall@3 | 80,95% | 100% |
| Hit@3 | 85,71% | 100% |
| MRR@3 | 0,8571 | 1,0000 |
| Cobertura Top-3 | 80,36% | 100% |
| Cobertura contexto | 76,79% | 100% |
| Preguntas completas Top-3 | 5/7 | 7/7 |
| Preguntas completas contexto | 4/7 | 7/7 |

Comparación offline que reutiliza rankings semánticos reales guardados; léxico,
fusión y contexto recalculados. Parámetros elegidos con desarrollo conocido.
35/35 unidades, sin nuevas etiquetas ni cambios en preguntas. No acredita
generalización ni fidelidad del nuevo prompt. Revisión humana y reserva pendientes.
Tokens reales A/B y latencias comparativas de la nueva variante siguen pendientes.

Guía: `backend/docs/COVERAGE_IMPROVEMENTS.md`; JSON/CSV/PDF con base
`coverage_improvements_20261021`. 263 unitarias y 26 API pasan; trazas actuales
coinciden en 13 casos; HTTP search real E03/E04/E05 200 con cobertura completa.
Contenedor actualizado, sin Groq, reserva, commit ni push.

## Siguiente tarea completada: tokens reales de generación

Ejecutadas 14 llamadas Groq reales en siete preguntas documentales, sin reserva
ni comportamiento. A semántica y B híbrida v2 con el mismo rag_v6, modelo,
temperatura, esquema y límites; política de pertinencia en ambas antes de Top-3.
Uso de entrada/salida/total real, separado del cálculo local de presupuesto.

| Tokens informados | Semántica A | Híbrida B |
|---|---:|---:|
| Entrada total | 5.354 | 5.388 |
| Salida total | 1.238 | 1.135 |
| Total | 6.592 | 6.523 |
| Media total por pregunta | 941,71 | 931,86 |

Siete pares completos, 14 HTTP 200, 14 contratos/citas estructuralmente válidos,
cero fallos y uso desconocido, 13.115 tokens en total. B consume 69 menos (1,05%)
en esta ejecución; no acredita ahorro estable ni mejor calidad. No incluye
clasificador, revisor o corrección; falta medir consumo completo del pipeline
si se pretende esa afirmación. No se atribuyen las mediciones al endpoint query.

Guía `backend/docs/GENERATION_TOKENS.md`; JSON/CSV/PDF `generation_tokens_20261021`.
Respuestas/contextos guardados para revisión humana, sin repetir generación.
Siete pruebas nuevas y 270 unitarias locales correctas; cálculos, hashes y CSV
comprobados; tres páginas PDF revisadas. Sin despliegue, commit ni push nuevos.

**Siguiente pendiente según la tabla:** revisión humana de fidelidad, corrección,
utilidad y respaldo de las respuestas. No iniciada ni sustituida por validación
del contrato. Reserva y anotaciones continúan pendientes de aprobación.

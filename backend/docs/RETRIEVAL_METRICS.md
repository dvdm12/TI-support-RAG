# Métricas de recuperación — desarrollo

Ejecución real en Supabase con el índice académico activo de 70 fragmentos.
Se ejecutaron las 13 consultas anotadas, sin errores técnicos. Los promedios
documentales utilizan las mismas siete preguntas elegibles para A y B; seis
casos de comportamiento quedan fuera de esos denominadores.

**Resultados preliminares:** anotaciones del agente pendientes de revisión humana,
preguntas conocidas de desarrollo y ninguna reserva independiente. No se ajustaron
las anotaciones ni la configuración después de observar este resultado.

## Resultado agregado

| Métrica | A: semántica | B: BM25 + semántica + RRF |
|---|---:|---:|
| Precision@3 | 47.62% | 52.38% |
| Recall@3 | 73.81% | 80.95% |
| Hit@3 | 85.71% | 85.71% |
| Cobertura de información en Top-3 | 78.21% | 80.36% |
| MRR@3 | 0.8571 | 0.8571 |
| Cobertura del contexto tras presupuesto | 69.29% | 76.79% |
| Cobertura de candidatos (A: hasta 10; B: unión hasta 20) | 100.00% | 100.00% |
| Mediana de recuperación observada | 0.1884 s | 0.4011 s |

Precision, Recall, Hit y cobertura son promedios por pregunta (macro). MRR
es el promedio del inverso del primer rango relevante, con corte 3. Ambas
alternativas aciertan al menos un relevante en 6/7 casos y colocan ese acierto
en primera posición. No hubo listas cortas.

Como medida complementaria ponderada por unidades, ambas alternativas incluyen
**26 de las 35 unidades (74,29%)** en sus Top-3. La mejora de cobertura macro
no significa que hayan aumentado las unidades totales: se intercambian aciertos
entre preguntas de distinto tamaño.

Precision divide por tres aun cuando solo haya uno o dos fragmentos pertinentes.
Con esta anotación su máximo macro posible es 66,67%, pues hay 14 IDs relevantes
distribuidos entre las siete preguntas. No interpretar 100% como una meta
alcanzable para ese indicador con este corpus/anotación.

## Resultados por caso documental

| Caso | P@3 A/B | R@3 A/B | Cobertura Top-3 A/B | Cobertura contexto A/B |
|---|---:|---:|---:|---:|
| E01 | 0.333/0.333 | 1.000/1.000 | 100.0%/100.0% | 100.0%/100.0% |
| E02 | 0.667/0.667 | 1.000/1.000 | 100.0%/100.0% | 100.0%/100.0% |
| E03 | 0.667/0.667 | 0.667/0.667 | 87.5%/62.5% | 50.0%/62.5% |
| E04 | 0.667/0.667 | 1.000/1.000 | 100.0%/100.0% | 75.0%/75.0% |
| E05 | 0.000/0.000 | 0.000/0.000 | 0.0%/0.0% | 0.0%/0.0% |
| E06 | 0.333/0.667 | 0.500/1.000 | 60.0%/100.0% | 60.0%/100.0% |
| E12 | 0.667/0.667 | 1.000/1.000 | 100.0%/100.0% | 100.0%/100.0% |

## Hallazgos que deben conservarse

- **E06, error 403:** B aumenta Recall de 0,50 a 1 y cobertura de 0,60 a 1.
  Recupera también la comprobación del recurso concreto (ACS-05).
- **E03, Wi-Fi:** ambas recuperan dos de tres fragmentos relevantes, pero
  cambian cuáles. B pierde RED-02 con escalamiento y límites y selecciona
  RED-05 adicional sin aportar una unidad requerida. Cobertura baja de 87,5%
  a 62,5%. Igual Precision/Recall puede ocultar pérdida de información.
- **E05, mensaje sospechoso no abierto:** ambas tienen cero aciertos Top-3.
  Priorizan recuperación/exposición de contraseñas; los pasajes SEG-02 pertinentes
  sí están entre candidatos más profundos, pero se pierden al seleccionar tres.
  El problema observado está en la selección, no en ausencia de esos documentos.
- El presupuesto reduce la cobertura del contexto respecto a lo recuperado.
  En particular A pierde una condición Wi-Fi al omitir un pasaje completo.
- E07/E08/E09/E10/E11/E13 tienen métricas documentales nulas. Su tratamiento
  conductual no se evaluó mediante respuestas en este experimento.

La regresión 13/13 previa corresponde al pipeline completo con clasificación,
ajustes de categoría, filtros y generación. Esta comparación aísla recuperación
sin esas etapas; sus resultados deben identificarse con ese alcance.

## Protocolo y condiciones fijas

- Mismas preguntas, corpus, modelo/revisión y K=3; lectura con filtros del usuario
  autenticado. El inventario y cada candidato se contrastan con el índice anotado.
- Una única búsqueda semántica de diez candidatos por pregunta se comparte entre
  A y B. B usa además BM25 sobre los 70 fragmentos autorizados y RRF con constante
  60, pesos iguales y desempate por ID. La implementación se reutiliza de Retriever.
- Ajuste por categoría desactivado para ambas; no se usa la categoría esperada
  ni se llama al clasificador. Se aísla el efecto de BM25/RRF sin etiquetas de verdad.
- La selección híbrida se hace desde la unión completa de hasta 20 candidatos;
  se conserva este comportamiento del recuperador actual, no un reranker Top-10.
- Mismo prompt documental rag_v5, contrato, 6000 caracteres y presupuesto de
  entrada de 850 tokens para medir qué pasajes cabrían. `clasificacion` es null
  en ambos contextos y no se aplican filtros de pertinencia del pipeline completo.
  No se llama al generador; no se evaluaron respuestas ni fidelidad de sus citas.
- Tiempos emparejados: A=embedding+búsqueda semántica; B=embedding+recuperación
  híbrida. Comparten observaciones secuenciales y excluyen inicialización/Auth,
  calentamiento y reconstrucción de trazas. No son muestras independientes ni
  un estudio de latencia HTTP. Cobertura de candidatos declara tamaños distintos.
- La configuración BM25, stopwords, hashes del código, índices, prompt y
  anotaciones están en el JSON. Cero escrituras Supabase y cero llamadas Groq.
- Los errores técnicos producirían métricas vacías, contadores explícitos y
  comparación sobre el mismo subconjunto válido; hubo cero en esta ejecución.

## Evidencias y reproducción

- `docs/retrieval_metrics_20261021.json`: parámetros, métricas, candidatos,
  ranking semántico y BM25, contribuciones RRF, contexto, omisiones y tiempos.
- `docs/retrieval_metrics_20261021.csv`: 26 filas (13 casos por dos variantes);
  campos de calidad vacíos para los seis casos de comportamiento.
- `cases/rag_evidence.json`: unidades y fuentes congeladas.
- Cuatro pruebas numéricas del evaluador y suite local de 243 pruebas correctas.
  Los ejemplos numéricos y el CSV se recalcularon también de forma independiente.

Desde backend, con dependencias, índice y credenciales Supabase configurados:

```sh
../.venv/bin/python -m scripts.evaluate_retrieval_metrics
```

La opción `--backend local` permite una ejecución declaradamente local, con
búsqueda exacta sobre los vectores existentes. No se utiliza como fallback remoto.
Usar `--output` para conservar ejecuciones independientes.

## Decisión y pendientes

La híbrida ofrece una mejora macro pequeña y una pérdida concreta en Wi-Fi,
con mayor tiempo observado. Se documenta el intercambio sin cambiar la
configuración desplegada ni declarar un ganador definitivo. Antes de decidir:
revisar humanamente las anotaciones, investigar E03/E05 usando desarrollo y
validar la elección con una reserva nueva. La revisión humana de respuestas,
el notebook consolidado y los demás entregables siguen pendientes.

## Exportación PDF obligatoria

Por instrucción del usuario, **cada ejecución del evaluador genera JSON, CSV y
PDF**, con el mismo nombre base y en el mismo directorio. La exportación usa
`PDFReport.generate_retrieval_metrics` en `src/pdf_report.py`, reutilizando
estilos, tablas y paginación del módulo existente. La interfaz `generate()` de
los reportes anteriores se conserva.

El PDF presenta matriz agregada, matriz por caso, preguntas, denominadores,
condiciones del experimento y huella del JSON de origen. N/E permanece no
evaluable; un error técnico no se convierte en cero. Si se produce una matriz
incompleta, también se exporta su PDF antes de terminar con código de error.
Un fallo de renderizado se propaga: no se informa éxito silenciosamente.

Para regenerar el PDF existente sin modelos, conexión ni consumo de proveedores:

```sh
../.venv/bin/python -m scripts.evaluate_retrieval_metrics --from-json docs/retrieval_metrics_20261021.json
```

Salida actual: `docs/retrieval_metrics_20261021.pdf`, tres páginas revisadas
visualmente. Se añadieron tres pruebas de exportación automática, regeneración
sin proveedores y matrices incompletas; pasan las 246 pruebas locales. Las
métricas originales se conservaron sin ejecutar nuevamente Supabase ni Groq.

## Comparación de tiempos guardados

`scripts.compare_retrieval_times` resume las etapas ya medidas y exporta siempre
JSON, CSV y PDF, sin repetir búsquedas. Ver `TIMING_COMPARISON.md` y
`docs/retrieval_metrics_20261021_times.pdf`. Separa los 13 casos de tiempos de los
siete documentales usados para calidad; no confundir sus medianas.

## Cobertura completa por pregunta (derivación posterior)

Además de la fracción media de unidades, ahora se informa si cada pregunta
recibe **todas** las unidades necesarias en Top-3 y en el contexto final.

| Etapa | A completas | A incompletas | B completas | B incompletas |
|---|---:|---:|---:|---:|
| Top-3 | 4/7 (57,14%) | 3 | 5/7 (71,43%) | 2 |
| Contexto final | 3/7 (42,86%) | 4 | 4/7 (57,14%) | 3 |

Los seis casos de comportamiento no entran al denominador; no hubo errores
técnicos en el origen. Los errores quedan excluidos y contados si los hay; sin
casos válidos, la proporción es nula/N/E. No basta un Hit para declarar cobertura
completa. Las etiquetas requieren todas las unidades, aunque cada una permita
evidencias alternativas. E03/E05 siguen incompletos en Top-3; B completa E06.
El contexto pierde una unidad de E04 en ambas variantes.

Desde backend, sin modelos ni proveedores:

```sh
../.venv/bin/python -m scripts.summarize_complete_coverage
```

Genera `docs/retrieval_metrics_20261021_coverage.json`, CSV y PDF de cuatro páginas.
`--input`, `--annotations` y `--output` permiten otras rutas; la entrada y las
anotaciones no se sobrescriben. Se comprueba la huella de anotación usada en la
medición y la coherencia entre preguntas, IDs, unidades y fracciones almacenadas.
No modifica ni vuelve a ejecutar el experimento original; conserva su fecha,
parámetros, resultados y hashes de código históricos. El bloque
`complete_coverage_derivation` distingue fecha, código y fuente de esta derivación.
Los JSON/CSV muestran booleanos por caso, unidades presentes/total y unidades
faltantes; el PDF añade proporciones y matriz completa/incompleta.

El evaluador de nuevas búsquedas incluye estos campos automáticamente mediante
`src/rag/complete_coverage.py` y el exportador existente. Los informes antiguos
siguen admitidos por `--from-json`, sin atribuirles una medición nueva.

Siete pruebas nuevas y 259 unitarias locales correctas; recalculo independiente
y comprobación de 26 filas CSV. PDF renderizado e inspeccionado en sus cuatro
páginas. Cero consultas nuevas, generación o apertura de reserva. Las etiquetas
de relevancia siguen pendientes de revisión humana; no se evalúa calidad de las
respuestas con esta medida.

## Mejora posterior: recuperación técnica y prompt compacto

Se aplicaron normalización Wi-Fi/códigos con guiones, filtro de aplicabilidad
antes de Top-3, RRF ponderado (semántica 1, léxico 2) y prompt rag_v6. La
reproducción del conjunto de desarrollo obtiene 35/35 unidades y 7/7 preguntas
completas tanto en Top-3 como en contexto; cobertura macro 100%.
Ver `COVERAGE_IMPROVEMENTS.md` y `coverage_improvements_20261021.json/csv/pdf`.
No se sustituyen los resultados históricos de este documento. Es ajuste sobre
desarrollo conocido, no reserva, generación ni prueba independiente.

# Procedimiento de mejora del extractor PDF — 24-10-2026

Estado: pasos 1–8 implementados y verificados en el alcance local acordado (paso 8 el 25-10-2026).
El usuario autorizó posteriormente buscar PDF públicos y evaluarlos; seis probados, con límites registrados. Paso 9 pendiente.
Objetivo: ampliar soporte de PDF complejos conservando procedencia y evidencia.
Los patrones facilitan cambios; no demuestran por sí solos mejor calidad del RAG.

| Paso | Trabajo | Patrón/enfoque | Condición para avanzar |
|---|---|---|---|
| 1 — completado | PDF, perfil, hashes, código, entorno, extracción y archivos locales fijados | Regresión reproducible | 24 pruebas específicas correctas; dos extracciones completas coinciden; referencia protegida de sobrescritura. |
| 2 — completado | Contratos Pydantic de fuente, perfil, páginas, secciones, párrafos, tablas/filas, figuras y diagnósticos | Contratos + Composite | Extracción v1 idéntica a línea base; 11 pruebas nuevas y 287 unitarias correctas. Figuras/diagnósticos separados del JSON actual. |
| 3 — completado | Cinco etapas y subetapas por página; estado explícito y cierre de recursos | Pipeline | Extracción idéntica a línea base; 42 pruebas específicas y 294 unitarias correctas. |
| 4 — completado | Interfaces de estructura/layout y datos comunes; adaptadores de pypdf/pdfplumber e inyección PDFBackends | Adapter | Pipeline sin imports nativos, salida Ricoh idéntica; 50 pruebas específicas y 302 unitarias correctas. |
| 5 — completado | Estrategias native_text/ruled_tables/text_only, selección explícita por página/región y traza separada | Strategy | 60 pruebas específicas y 312 unitarias correctas; CLI real con 228 registros y extracción idéntica. |
| 6 — completado | Reglas componibles e informe separado; bloqueo documental y elegibilidad por bloque | Specification | 74 pruebas específicas y 326 unitarias correctas; Ricoh idéntico, seis tablas excluidas y 498 unidades con hash intacto. |
| 7 — completado en alcance local | Tablas sin bordes/columnas explícitas, continuaciones y OCR separado, con muestras controladas | Estrategias especializadas | Controles sintéticos y seis PDF públicos evaluados; 357 unitarias. Nueve controles de componentes correctos, 0/6 con pipeline genérico; Ricoh idéntico. |
| 8 — completado | Verificar unidades completas y recuperación en español | Preservación + evaluación | Extracción y 498 unidades idénticas antes/después; 194.084 caracteres PDF contabilizados sin pérdidas; 0 pérdidas previas a búsqueda en 12 casos; fallos solo de búsqueda (RIC-06; RIC-09 sin literal). 433 unitarias. |
| 9 | Preparar corpus aprobado, selección contextual y evaluar respuestas | Integración controlada | Fidelidad, corrección, citas, utilidad, tiempos y tokens; decisión antes del despliegue. |

Alcance inicial propuesto: pasos 1–6, local. Conservar perfil declarativo Ricoh,
formato que consume la fragmentación y salida pública existente, o introducir
adaptación/versionado explícitos si cambian. No reindexar ni cargar Supabase
como efecto de una refactorización. No interpretar figuras ni unir filas por
conjetura. Los pasos 7–9 requieren sus muestras, revisión y validación correspondientes.

Medir tres niveles por separado: extracción (estructura y procedencia), recuperación
(evidencia necesaria en candidatos/contexto) y respuesta (afirmaciones respaldadas).
El fallo histórico RIC-06 no se resuelve únicamente reorganizando el extractor.
El RAG desplegado no cambia hasta integrar Ricoh; no afirmar mejora de sus
respuestas por una refactorización local. Mantener pendientes de clase 09 separados.

## Paso 1 implementado

Referencia `backend/docs/baselines/ricoh_extraction_v1.json`; guía
`backend/docs/EXTRACTION_BASELINE.md`; comprobador
`backend/scripts/check_extraction_baseline.py` y módulo
`backend/src/rag/extraction_baseline.py`.
Desde backend: `../.venv/bin/python -m scripts.check_extraction_baseline`.
Informe técnico JSON local en docs/rag_runs/extraction_baseline/, sin proveedores.
Cambios de código/entorno son informativos; fuente, perfil, extracción y referencias
deben coincidir. No sustituir la línea base para ocultar una regresión.
El paso 2 se completó posteriormente; véase la sección siguiente.
Sin commit/push ni cambios al extractor productivo o Supabase.

## Paso 2 implementado

Contratos en `backend/src/rag/extraction_contracts.py`, guía
`backend/docs/EXTRACTION_CONTRACTS.md`. extract_real_document valida antes de
retornar el diccionario original; no reserializa ni cambia schema_version=1.
Conserva celdas ambiguas, metadatos, jerarquía, coordenadas y procedencia.
Figuras/diagnósticos son contratos separados, sin extracción gráfica ni nuevos
bloques incompatibles con fragmentación. 11 pruebas nuevas; 35 específicas
correctas y 287 unitarias completas correctas. Línea base y nueve referencias
intactas; informe local 20261025T023955782724Z.json. Sin proveedores/Supabase.
El paso 3 se completó posteriormente; véase la sección siguiente.
Sin commit/push ni despliegue nuevos.

## Paso 3 implementado

external_ingestion.extract_real_document coordina validate_source,
analyze_document, extract_pages, reconstruct_document y validate_extraction.
Cada página separa audit_page, extract_page_layout y assemble_page_blocks.
Estado propio por ejecución; análisis copiado para evitar acumulación de bloques.
Streams/documento/páginas se cierran también ante fallos; excepciones originales
con notas de etapa/página. No se cambia interfaz ni JSON v1.
Guía `backend/docs/EXTRACTION_PIPELINE.md`; siete pruebas nuevas, 42 específicas
correctas y 294 unitarias completas correctas. Extracción idéntica y nueve
referencias intactas; informe local 20261025T030355523352Z.json.
Sin proveedores, Supabase, datos modificados, despliegue, commit ni push.
El paso 4 se completó posteriormente; véase la sección siguiente.

## Paso 4 implementado

`backend/src/rag/pdf_adapters.py`: Protocols StructureDocument/LayoutDocument/
LayoutPage, OutlineEntry, TableSnapshot y factories de contexto inyectables
mediante PDFBackends. Los imports nativos y traducción de objetos se aíslan allí;
external_ingestion conserva reglas, perfil, reconstrucción y contratos.
`extract_real_document`, analyze_document y extract_pages admiten backends=.
Helpers previos aceptan objetos nativos vía adaptadores de compatibilidad;
page_tables devuelve TableSnapshot consumible por table_block.
Ocho pruebas nuevas: flujo entero con bibliotecas bloqueadas, fallos/cierre de
recursos, marcadores, celdas y página Ricoh real. 50 específicas y 302 unitarias
correctas; extracción completa idéntica y nueve referencias intactas. Guía
`backend/docs/PDF_ADAPTERS.md`; informe local 20261025T032202977078Z.json.
Sin estrategias nuevas, OCR, proveedores, Supabase, despliegue, commit o push.
El paso 5 se completó posteriormente; véase la sección siguiente.

## Paso 5 implementado

`backend/src/rag/extraction_strategies.py`: métodos separados de texto/tablas,
política de páginas/regiones validada e inyección de implementaciones.
Perfiles sin strategies conservan comportamiento previo; Ricoh activo intacto.
text_only requiere motivo, registra review y no es fallback automático.
Rangos/regiones ambiguos, nombres ausentes, tablas cortadas y pérdida de texto
por redetección fallan. Tablas completas sin cambios de settings se reutilizan:
una prueba real de Ricoh185 detectó pérdida de celda al recortar de nuevo por
bordes exactos; el caso se corrigió y quedó en regresión. No hay OCR/diagramas.
CLI extract_real_manual escribe strategy_trace.json separado y su checksum en
summary.json, sin cambiar extraction.json v1. 10 pruebas nuevas, 60 específicas
correctas y 312 unitarias completas correctas. CLI real en
/tmp/ti-ricoh-strategies-step5: 213 selecciones y 15 exclusiones con motivo.
Extracción idéntica y nueve referencias intactas; informe local
backend/docs/rag_runs/extraction_strategies/check_20261024.json.
Guía backend/docs/EXTRACTION_STRATEGIES.md. Sin proveedores/Supabase/despliegue,
commit o push. Siguiente paso cuando se solicite: 6, formalizar validaciones.


## Paso 6 implementado

extraction_rules.py reúne reglas deterministas de tablas/texto/elegibilidad;
extraction_validation.py compone contrato, política y orden/límites/texto de
secciones, con estados accepted/review/error e informe versionado separado.
Errores bloquean todo el documento; gráficas, glifos sin resolver y páginas
text_only se excluyen de unidades y contexto. Región text_only excluye por
ahora toda la página. Continuaciones requieren revisión, conservando filas
completas independientes sin unirlas. El constructor de evidencia revalida
entradas v1; compatibilidad parcial en memoria aplica reglas por bloque.
CLI guarda validation_report.json y hash/conteos en summary.json. Ante fallo
conserva diagnóstico único y relanza, sin publicar una extracción parcial.
14 pruebas nuevas, 74 específicas y 326 unitarias completas correctas.
Extracción nueva /tmp/ti-ricoh-validation-step6 idéntica byte a byte; 1.673
bloques aceptados estructuralmente, 66 review, cero errores y seis tablas
excluidas. 1.733 bloques elegibles; las 498 unidades mantienen hash del índice.
Nueve referencias y línea base congelada intactas. Guía
backend/docs/EXTRACTION_VALIDATION.md; informe técnico LOCAL IGNORADO:
backend/docs/rag_runs/extraction_validation/check_20261024.json.
No certifica fidelidad semántica ni revisión humana. Sin nueva suite API,
proveedores, Supabase, índices modificados, despliegue, commit o push.
Pasos 7–9 pendientes; siguiente cuando se solicite: 7, nuevas muestras complejas.


## Paso 7 implementado en el alcance acordado

Usuario indicó que no dispone ahora de otros PDF reales y que los buscará para
probar al finalizar. Dejar esa validación pendiente sin bloquear pasos locales.
No acreditar generalización por pruebas sintéticas ni afirmar revisión humana.

column_text admite columnas explícitas en orden de lectura, exige cubrir cada
carácter útil una sola vez y cierra párrafos al cambiar de columna. Tablas deben
caber enteras; marcadores dentro de columnas se rechazan por falta de eje
horizontal en el contrato de secciones. Documentos guardados se revalidan.
borderless_tables exige región y límites revisados de celdas; rechaza cortes de
caracteres y cuadrículas inconsistentes. Conserva también cuadrículas cortas
explícitas; la heurística antigua de iconos sigue para tablas detectadas.
OCR: pdf_ocr_review.py y scripts/review_pdf_scan.py, hash/página/imagen sin texto
nativo, Poppler y Tesseract local spa+eng, coordenadas de raster y confianza.
Candidato pdf-ocr-review-v1 separado, siempre review y no indexable; no hay
fallback ni cambios al contrato nativo. Figuras y tablas OCR sin interpretar.

scripts/complex_pdf_samples.py genera cuatro PDF reproducibles (cinco páginas);
scripts/evaluate_complex_pdfs.py compara celdas, orden, continuaciones y texto
OCR, y opcionalmente reextrae Ricoh completo para comparar. Evidencia LOCAL
IGNORADA: backend/docs/rag_runs/complex_pdfs/check_20261024_final/ con report.json,
checks.csv, report.pdf, muestras, trazas y ocr_candidate.json. Nueve controles
correctos; OCR recupera los cuatro textos de control (12 palabras, confianza
media 95,58). Esto no equivale a validar escaneados degradados ni nuevos manuales.
22 pruebas nuevas, 96 específicas y 348 unitarias correctas. Ricoh idéntico a
línea base, 498 unidades con hash guardado, seis tablas gráficas excluidas y
nueve referencias intactas. Sin nueva suite API, proveedores, modelos descargados,
embeddings, Supabase, índices modificados, despliegue, commit o push.
Guía backend/docs/COMPLEX_PDF_EVALUATION.md. Siguiente cuando se solicite: 8.


## Ampliación del paso 7: PDF públicos de la web

El usuario revocó el aplazamiento y autorizó buscar y aplicar pruebas en la web.
Se descargaron seis PDF públicos intactos: Camelot health, BERT de ACL,
Attention v5 de arXiv y tres variantes de un escaneado técnico de OCRmyPDF.
Cuatro contenidos independientes; las variantes no se cuentan como tres
manuales independientes. SHA-256, URL y versiones en
backend/docs/fixtures/web_pdf_sources_v1.json. No se añadieron al corpus activo.
Nueve controles de componentes correctos: 24 celdas muestreadas conservadas,
lectura de dos columnas y 3.868 caracteres NFKC conservados, encabezados
jerárquicos rechazados/no indexables y OCR siempre review. La sonda de celdas
no resuelve los encabezados y no produce evidencia indexada. El comprobador
se corrigió para ligaduras Unicode equivalentes sin modificar producción.
0/6 PDF completan el pipeline con perfil genérico: cinco carecen de marcadores;
Attention carece de número impreso en la primera página. No son fallos Ricoh ni
aprobaciones de extracción completa. Se necesitan perfiles/estrategias revisados.
OCR: confianza 92,54–93,84; WER 47,89–48,68 % contra linn.txt externo (contiene
artefactos, sin certificación humana nueva), recuperación de tokens sin orden
94,74–95,79 %. Se constató mezcla de columnas. No confundir palabras recuperadas
con procedimientos fieles ni presentar confianza como exactitud.
Nueve pruebas unitarias nuevas; 105 específicas y 357 unitarias correctas.
Ricoh completo idéntico, 498 unidades con hash guardado y nueve referencias
intactas. Sin nueva suite API, modelos, embeddings, Supabase, índices activos,
commit o push. Guía backend/docs/WEB_PDF_EVALUATION.md; evidencia LOCAL IGNORADA:
backend/docs/rag_runs/web_pdfs/check_20261024/results_final/ (JSON/CSV/PDF).
La ejecución results/ anterior es diagnóstica y no la vigente (comparación literal
de ligaduras producía falsa alarma). Pendientes: sin marcadores, secciones en
columnas, encabezados multinivel y OCR segmentado. No se declararon resueltos.
Siguiente paso solicitado sigue siendo el 8; no iniciarlo automáticamente.


## Descubrimiento posterior de fuentes por categoría

El usuario solicitó buscar PDF útiles para solucionar problemas de las siete
categorías. Se completó la búsqueda: diez PDF descargados/verificados de doce
candidatos, 363 páginas con revisión dirigida, al menos uno por categoría y dos
descargas pendientes TLS. Catálogo backend/docs/PDF_CANDIDATES_BY_CATEGORY.md y
registro backend/docs/fixtures/category_pdf_candidates_v1.json. No se probaron
ni aprobaron para ingestión. Mantener versiones/productos/ámbito institucional.
Esta selección no sustituye políticas propias ni implementa el paso 8. Sin
nuevos índices, Supabase, proveedores, tests/API, commit o push; nueve referencias
intactas. No confundir con la evaluación anterior de seis PDF públicos.


## Publicación de esta revisión

El usuario solicitó commit y push de los cambios acumulados de los pasos 1–7,
evaluación pública, catálogos y continuidad. Base previa c5826c0; identificar el
commit actual con git log. Verificación previa: 357 unitarias correctas.
Los informes/PDF descargados/índices ignorados quedan locales; no se reindexa,
no se mueve la colección candidata a manuals/ ni se inicia el paso 8 al publicar.
Las anotaciones históricas de ausencia de commit/push describen cada tarea
anterior y no sustituyen esta autorización posterior.


## Paso 8 implementado

`backend/src/rag/unit_verification.py` y `backend/scripts/verify_units_retrieval.py`;
guía `backend/docs/UNIT_RETRIEVAL_VERIFICATION.md`. Reextrae Ricoh, compara con
la extracción registrada y el índice ricoh-local-v1, contabiliza caracteres del
PDF por página y clasifica cada caso en extraction_loss/unit_loss/fragment_loss/
search_failure/retrieved. Exporta JSON/CSV/PDF en directorio nuevo.
Resultado: extracción idéntica (ca1178c5…), 498/498 unidades idénticas, 194.084
caracteres en 213 páginas con 0 faltantes/0 sobrantes, 1.647 párrafos y 364 filas
en una unidad, 19 filas gráficas excluidas con motivo. semantic/hybrid fallan
RIC-06 y RIC-09 en búsqueda; hybrid_literal solo RIC-06. Ninguna pérdida previa.
evaluate_ricoh_local usa la regla `relevant` compartida; posiciones idénticas.
76 pruebas nuevas (mutación 18/19, el restante equivalente), 433 unitarias. Evidencia local ignorada en
backend/docs/rag_runs/unit_retrieval/check_20261025/. Sin Groq/Supabase/índices.
No resuelve RIC-06 ni evalúa respuestas. Los diez PDF candidatos quedaron fuera:
sonda del 25-10 los bloquea a todos (6 sin marcadores; HP/LibreOffice con pie
"título + número"; SEG-BACKUP con marcadores fuera del rango numerado). Evidencia
en backend/docs/rag_runs/category_pdf_discovery/20261024/extraction_probe_20261025/.
Siguiente cuando se solicite: paso 9, o soporte de perfiles para candidatos.

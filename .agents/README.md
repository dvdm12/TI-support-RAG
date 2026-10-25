# Continuidad de TI-support-RAG

Actualizado el 24-10-2026 (America/Bogota). Leer primero el estado vigente al
inicio de [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md); los apartados anteriores
conservados como historial pueden contener cifras y pendientes superados.

## Estado actual

- Rama `codex/backend-infra-ricoh-local`. Esta revisión incorpora pasos 1–7
  del extractor, pruebas y catálogos documentales. Base publicada previa:
  `c5826c0` (recuperación híbrida, rag_v6, cobertura y comparación de tokens).
  Consultar `git log -1` para identificar el commit de esta revisión y comprobar
  la relación con origin mediante `git status -sb`.
- Backend saludable, imagen `a414431ee034`; corpus académico de 70 fragmentos.
  Ricoh sigue separado de la API y de Supabase.
- Desarrollo conocido: 7/7 documentales completos y 35/35 unidades con híbrida v2.
  No acredita generalización ni revisión humana.
- Tokens comparables: 14 generaciones, siete pares, A 6.592 / B 6.523.
  Solo generación; clasificación, revisión y corrección quedan fuera.
- Verificación reciente: 19/19 controles HTTP correctos; autenticación Supabase,
  inventario de 70 fragmentos y RPC consistentes desde dos clientes del mismo usuario.
- Suite previa al commit: 270 unitarias y 26 API correctas; posteriormente,
  357 unitarias correctas tras evaluar PDF públicos (sin nueva suite API).
  La verificación Ricoh independiente pasó 18 pruebas; no sumarla como suite distinta.
- Observación pendiente: query 403 devuelve OK_PIDE_ACLARACION con datos_faltantes
  vacío. Conservar la respuesta para revisar coherencia; no declarar fallo de conectividad.

## Búsqueda posterior: candidatos por categoría

El usuario pidió encontrar PDF relevantes para resolver problemas de cada una
de las siete categorías. Catálogo backend/docs/PDF_CANDIDATES_BY_CATEGORY.md;
registro backend/docs/fixtures/category_pdf_candidates_v1.json. Doce candidatos:
diez PDF descargados/verificados (363 páginas, revisión dirigida), al menos uno
por categoría, y dos pendientes de descarga por validación TLS (IDEP y DNP).
No se desactivó TLS. Copias locales ignoradas en
backend/docs/rag_runs/category_pdf_discovery/20261024/.
Fuentes: HP, LibreOffice, Cisco, Universidad Piloto, INCIBE, Icesi y Sabaneta.
Distinguir contexto de producto y políticas de otras instituciones; el manual
MFA de Icesi exige conservar acceso a la cuenta. Sabaneta es de 2017. No afirmar
que estos documentos resuelven cualquier caso ni que están listos para ingestión.
No se probaron en el pipeline completo ni se añadieron al corpus/Supabase.
Los resultados previos de seis PDF públicos no se transfieren a estos diez.
Nueve referencias del baseline intactas; no se repitieron suites/API ni modelos.
Esta búsqueda no implementa el paso 8 ni abre reserva. Sin commit/push.

## Para continuar

La mejora del extractor tiene **los pasos 1–7 implementados y verificados en el alcance local acordado**
(incluye controles sintéticos y seis PDF públicos; límites documentales registrados). Ver
[EXTRACTOR_IMPLEMENTATION_PLAN.md](EXTRACTOR_IMPLEMENTATION_PLAN.md).
La referencia está en `backend/docs/baselines/ricoh_extraction_v1.json`;
105 pruebas específicas y 357 unitarias correctas; extracción Ricoh completa idéntica.
Contratos y guía: `backend/src/rag/extraction_contracts.py` y
`backend/docs/EXTRACTION_CONTRACTS.md`.
Guía del pipeline: `backend/docs/EXTRACTION_PIPELINE.md`.
Adaptadores: `backend/src/rag/pdf_adapters.py`; guía `backend/docs/PDF_ADAPTERS.md`.
Estrategias: `backend/src/rag/extraction_strategies.py`; guía
`backend/docs/EXTRACTION_STRATEGIES.md`. CLI genera una traza separada de 228
registros para Ricoh; fuente/perfil/índices activos intactos.
Validación: `backend/src/rag/extraction_validation.py`; guía
`backend/docs/EXTRACTION_VALIDATION.md`. Ricoh: 1.673 bloques aceptados
estructuralmente, 66 para revisión y cero errores. Seis tablas excluidas;
498 unidades conservan hash. CLI añade validation_report.json; los errores
bloquean toda construcción y generan un diagnóstico de fallo separado.
Paso 7: column_text y borderless_tables con geometría explícita; OCR local
separado, siempre review/no indexable. Cuatro PDF sintéticos (cinco páginas),
nueve controles sintéticos correctos; no acreditan generalización. El usuario
autorizó después buscarlos en la web: seis PDF públicos evaluados (cuatro
contenidos; tres variantes del mismo escaneado). Nueve controles de componentes
correctos; 0/6 completan el pipeline con el perfil genérico. OCR mezcla columnas:
WER 47,89–48,68 % contra transcripción externa con artefactos, no verdad humana.
Guía `backend/docs/WEB_PDF_EVALUATION.md`; código productivo intacto en esa
evaluación. No repetir búsquedas ni iniciar mejoras adicionales por defecto.
Continuar con el paso 8 (unidades completas y recuperación en español) cuando se solicite avanzar;
no abrir reserva ni integrar Ricoh como consecuencia de esta actualización.

En evaluación de clase 09 sigue pendiente la revisión humana de las 14 respuestas
guardadas en `backend/docs/generation_tokens_20261021.json`, seguida de respaldo y
citas por afirmación, abstenciones, reserva congelada y entregables. Tabla vigente:
[CLASS09_METRICS_STATUS.md](CLASS09_METRICS_STATUS.md). No regenerar respuestas
para revisarlas. Toda exportación de métricas debe conservar JSON, CSV y PDF.

## Evidencias y límites

- `backend/docs/rag_runs/endpoint_check_20261024/`: endpoints.json, supabase.json
  y RESULTADOS.md. Una solicitud real a query con llamadas Groq del pipeline.
- `backend/docs/rag_runs/ricoh_extraction_check_20261024/`: verification.json y
  RESULTADOS.md. Extracción nueva idéntica byte a byte a la guardada; índice íntegro.
- Estos informes están ignorados por Git y permanecen locales. No se incluyeron
  en c5826c0 ni deben darse por disponibles al clonar el repositorio.
- Hay corpus, vectores, configuración y migración SQL locales; no se encontró un
  respaldo completo de Supabase. Upsert no elimina filas adicionales ni restaura Auth.

El usuario solicitó publicar esta revisión mediante commit y push. Incluye
código, pruebas, guías, línea base y registros de candidatos; los PDF descargados,
informes extensos, extracciones e índices ignorados siguen solo en local.
Los diez PDF candidatos siguen en docs/rag_runs/category_pdf_discovery/20261024/;
no se trasladaron a manuals/ ni se incorporaron al corpus como parte de publicar.
Verificación previa: 357 unitarias correctas; no nueva suite API, proveedores,
modelos ni despliegues. El hash final y estado remoto se verifican con Git;
no deducir publicación remota únicamente por la presencia de esta nota.
Consultar `git status -sb` antes de continuar. Proteger .env y credenciales.
No retomar pruebas de aislamiento entre usuarios ni Drive por iniciativa propia.
`plantuml_notebook_activity.toml` es una especificación histórica, no una tarea activa.

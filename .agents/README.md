# Continuidad de TI-support-RAG

Actualizado el 25-10-2026 (America/Bogota), tras publicar a7b3702. Leer primero el estado vigente al
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

## Publicación 25-10-2026

Commits 85b8bb2 (paso 8), ec2d1de (validador estricto) y a7b3702 (E06 + .agents)
publicados en origin/codex/backend-infra-ricoh-local. Verificar con `git status -sb`.

## Corrección E06 25-10-2026 (publicado en a7b3702)

prompt system_v8 + maxLength 240 en el resumen enviado a Groq. 13/13 casos de
desarrollo HTTP 200 con estado documental esperado; imagen f5118f3a626c.
Detalle en CLASS09_METRICS_STATUS.md y PROJECT_HANDOFF.md.

## Validador estricto 25-10-2026 (publicado en ec2d1de)

confianza StrictFloat y datos_faltantes sin vacíos (decisión del usuario); errores
de raíz sin ": " inicial. test/test_validator.py: 25 pruebas, 100 % de cobertura
de validator.py y request_v1.py. Suite: 458 unitarias y 26 API correctas.
Contenedor reconstruido: imagen 69245ccd8178 healthy; rollback en tag rollback-a414431ee034. Detalle en PROJECT_HANDOFF.md.

## Paso 8 completado el 25-10-2026 (publicado en 85b8bb2)

Publicación previa confirmada: HEAD 7be846f sincronizado con origin.
Paso 8 implementado: unit_verification.py, verify_units_retrieval.py, 76 pruebas
y guía backend/docs/UNIT_RETRIEVAL_VERIFICATION.md. Ricoh: extracción y 498
unidades idénticas antes/después, 194.084 caracteres sin pérdidas; en 12 casos
españoles no hay pérdidas previas a la búsqueda. Fallos solo de búsqueda: RIC-06
(todas las estrategias) y RIC-09 (sin literal). 433 unitarias correctas.
Los diez PDF candidatos: 0/10 pasan el pipeline genérico (sonda 25-10); su
soporte requiere cambios de perfil/extractor. Siguiente: paso 9 si se solicita.

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
El paso 8 se completó el 25-10-2026 (ver arriba); continuar con el paso 9 cuando se solicite;
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

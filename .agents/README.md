# Continuidad de TI-support-RAG

Lee primero [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md), sección
**Estado actual para continuar — leer primero** (actualizada el 21-10-2026).
Contiene el estado de Git, estructura backend/frontend/infra, Docker activo,
autenticación, pruebas, manual Ricoh verificado y trabajo pendiente de ingestión.

**Entrega Git posterior al cierre:** el usuario autorizó commit y push del
trabajo existente en `codex/backend-infra-ricoh-local`. Consultar `git log -1` y
`git status -sb` para identificar la entrega y verificar sincronización con origin.
Las menciones históricas a cambios locales sin publicar quedan superadas por esa
entrega; los pendientes funcionales y la reserva sin ejecutar se conservan.

**Cierre vigente (21-10-2026):** el usuario pidió dejar el trabajo en este punto.
Solo se actualizó la continuidad. No ejecutar la reserva ni avanzar en tareas
pendientes sin una nueva solicitud. La tabla de pendientes consolidada está al
principio de `PROJECT_HANDOFF.md`: revisión humana de desarrollo y reserva,
congelación, evaluación de respuestas/reserva, decisión final, entregables y
publicación de cambios. Swagger está actualizado en el contenedor local; la
reserva sigue como borrador de 12 candidatos sin ejecutar. No hubo commit/push.

El historial posterior se conserva como referencia y puede contener estados
superados. Las rutas operativas están en `backend/` y `infra/`.

`plantuml_notebook_activity.toml` es una especificación de diagrama basada en
una inspección histórica del notebook. No constituye una instrucción para
recrear el diagrama ni una prueba de las banderas actuales; contrastarla con el
notebook si se solicita trabajo en él.

El manual Ricoh está identificado, extraído y fragmentado con embeddings reales
en un índice local independiente. La evaluación tiene evidencia esperada Top-3
en 11/12 preguntas; sigue pendiente el caso de impresión retenida. La API activa
conserva sus 70 fragmentos académicos. La evaluación local del manual no lo
cargó a Supabase ni llamó a Groq; la regresión del backend sí usó ambos servicios.
La siguiente integración necesita resolver ese fallo y el presupuesto de contexto
para unidades completas. El usuario solicitó conservar el alcance simple y subir todos los cambios a una
rama nueva: `codex/backend-infra-ricoh-local`. No integrar todavía Ricoh en la API.

Actualización posterior: se corrigieron aclaraciones de incidentes ambiguos y se
completó la regresión del backend (13/13 criterios de entrega, incluidos dos
reemplazos seguros y tres aclaraciones locales; no son 13 respuestas validadas
por el modelo). Pasan 234 unitarias y 24 API. Imagen corregida desplegada y dos
consultas HTTP reales correctas. Ver `backend/docs/BACKEND_VALIDATION.md` y
`backend/docs/backend_validation.json`. El usuario autorizó crear y publicar el
commit `fix: clarify ambiguous requests and validate backend regression` en la
misma rama. Esta continuidad se incluye en esa entrega; consultar `git log -1`
y `git status -sb` para conocer su identificador y sincronización con origin.

Actualización 21-10: tiempos por etapa `stages-v1` implementados y desplegados.
API publica `tiempos_segundos`; regresión exporta `timings.csv`. Guía:
`backend/docs/STAGE_TIMINGS.md`; evidencia `backend/docs/stage_timing_validation.json`.
Pasan 239 unitarias y 25 API (también 25 API dentro de la nueva imagen); HTTP
search/query 200 y equivalencia de ranking real en 13 consultas locales.
Los cambios de auditoría y tiempos posteriores a `e5be392` aún son locales.
Las otras brechas de clase 09 siguen pendientes: ver `backend/docs/CLASS09_AUDIT.md`.

Avance anterior: evidencias anotadas en `backend/cases/rag_evidence.json` y guía
`backend/docs/RAG_EVIDENCE.md`: 13 casos, siete documentales, seis de comportamiento,
35 unidades. Integridad contrastada contra los siete PDF y 70 fragmentos;
`backend/scripts/validate_rag_evidence.py` permite repetirla sin APIs. Anotación
del agente pendiente de revisión humana. Todos los casos son desarrollo conocido;
reserva nueva sigue pendiente. No se calcularon métricas en esta etapa.

Último avance: métricas A/B calculadas en Supabase real, sin Groq ni escrituras.
Guía `backend/docs/RETRIEVAL_METRICS.md`, datos JSON/CSV `retrieval_metrics_20261021`
en backend/docs. Siete casos documentales válidos; seis de comportamiento excluidos;
cero errores. P@3 A/B 47,62%/52,38%, Recall 73,81%/80,95%, Hit 85,71%/85,71%,
MRR 0,8571/0,8571, cobertura 78,21%/80,36%. B mejora 403, empeora Wi-Fi; ambos
pierden mensaje sospechoso en Top-3. Categoría desactivada, sin clasificadores ni
filtros del pipeline; resultados preliminares de desarrollo, no reserva ni calidad
de respuestas. Pasan 243 unitarias; no se desplegó ni cambió el backend activo.
Todo el trabajo posterior a e5be392 sigue local, sin nuevo commit/push.

Preferencia permanente del usuario: **siempre PDF junto con JSON/CSV para esta
matriz de métricas**. `PDFReport.generate_retrieval_metrics` adapta el módulo
existente y el evaluador lo llama automáticamente, incluso para matrices parciales.
`--from-json` regenera solo PDF sin proveedores. PDF actual de tres páginas en
`backend/docs/retrieval_metrics_20261021.pdf`, inspeccionado visualmente. Pasan
246 unitarias. No repetir Supabase/Groq para volver a exportar una matriz guardada.

Último avance: comparador de tiempos terminado; guía
`backend/docs/TIMING_COMPARISON.md`. Desde backend:
`../.venv/bin/python -m scripts.compare_retrieval_times`. Lee mediciones guardadas
y exporta siempre JSON/CSV/PDF, sin proveedores. Informe actual:
`backend/docs/retrieval_metrics_20261021_times.pdf` (tres páginas revisadas).
Trece pares válidos; medianas A/B 188,37/398,69 ms y diferencia emparejada mediana
208,77 ms. Separa siete documentales y seis de comportamiento. Son componentes
compartidos del experimento original, no latencia HTTP independiente. Pasan
252 pruebas locales. Sin nuevo despliegue, commit ni push; revisar primero la
sección actual del handoff para continuar.

Avance más reciente: reserva estructurada en `backend/cases/rag_reserve.json`
(12 candidatos: nueve documentales, 25 unidades, tres límites documentales).
Guía `backend/docs/RAG_RESERVE.md`; validación offline
`python3 -m scripts.validate_rag_reserve` desde backend. Ocho controles negativos
correctos. Sin ejecutar preguntas ni proveedores. Pendiente revisión humana,
decisión con desarrollo y congelación; `--require-ready` falla por esos pendientes.
No conectada al evaluador actual y no constituye todavía reserva validada.
Compartir categorías/corpus y conocer desarrollo impide afirmar ceguera o
independencia por familias. Ver sección vigente del handoff antes de continuar.

Swagger descriptivo actualizado y desplegado el 21-10: autenticación, ejemplos
validados, campos, estados, tiempos y errores con acciones. 26 pruebas API pasan;
HTTP docs/esquema/assets y autenticación comprobados. Contenedor saludable con
imagen `9ee9f10dd1f4`. Sin proveedores ni ejecución de reserva; sin commit/push.
Recargar http://127.0.0.1:8000/api/v1/docs/ y autorizar nuevamente con solo el
valor de DJANGO_API_TOKEN, sin Bearer. Ver estado vigente en el handoff.

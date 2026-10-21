# Informe de continuidad — TI-support-RAG

Actualizado: 21 de octubre de 2026 (America/Bogota).
Repositorio: `/home/dvdm12/Documents/Obsidian Vault/TI-support-RAG`.

## Estado actual para continuar — leer primero

Esta sección prevalece sobre el historial que sigue. Las rutas antiguas del
historial, como `src/` o `docs/`, ahora corresponden a `backend/src/` y
`backend/docs/`, salvo las migraciones, ubicadas en `infra/supabase/`.
No contiene secretos. No releer ni ejecutar integraciones históricas por defecto.

### Entrega Git solicitada el 21-10-2026

El usuario autorizó crear un commit y actualizar el remoto después del cierre.
Esta autorización corresponde a publicar el trabajo existente, sin avanzar en
revisión humana, congelación o evaluación de la reserva.

Esta sección forma parte del commit de entrega de tiempos por etapa, métricas
A/B con PDF automático, comparación de tiempos, estructura de reserva y Swagger
descriptivo. Rama destino: `codex/backend-infra-ricoh-local`, remoto `origin`.
Consultar `git log -1` y `git status -sb` para obtener el identificador de esta
entrega y confirmar sincronización, en lugar de usar e5be392 como último estado.
Las referencias siguientes a «sin commit/push» describen los momentos históricos
anteriores a esta publicación. Antes de publicarla se revisaron los 42 archivos
pendientes, sin coincidencias con secretos locales ni patrones de credenciales;
se conservan ignorados .env y sus variantes privadas, índices y datos personales.
No se ejecutó la reserva ni se repitieron llamadas a proveedores para esta entrega.

### Cierre de sesión 21-10-2026 — dejar el trabajo en este punto

El usuario indicó «vamos a dejar así, actualiza .agents». Esta sesión termina
con documentación de continuidad: no avanzar en los pendientes ni ejecutar la
reserva como consecuencia de este cierre. Retomar según la siguiente solicitud.

**Completado:** instrumentación de tiempos desplegada; evidencias de desarrollo
anotadas por el agente; comparación A/B de recuperación y comparación descriptiva
de tiempos, con JSON/CSV/PDF; estructura de reserva sin ejecución; Swagger más
descriptivo actualizado en el contenedor local. Se mantiene la preferencia de
PDF automático para cada exportación de métricas. Corpus académico activo de
70 fragmentos; Ricoh continúa separado, sin integración en la API.

| Pendiente | Estado al cerrar | Siguiente acción cuando se retome |
|---|---|---|
| Evidencias de desarrollo | 35 unidades anotadas por el agente | Revisión humana de fuentes, relevancia y completitud. |
| Reserva | 12 candidatos, nueve documentales con 25 unidades y tres límites | Revisión humana de expectativas y novedad semántica; sin ejecutar. |
| Congelación | Protocolo definido, sin aprobar | Registrar decisión con desarrollo, snapshot de configuración y reserva aprobada. |
| Respuestas | Comparación y revisión humana pendientes | Mismo generador/prompt; evaluar exactitud, respaldo y citas, con muestra revisada por dos integrantes. |
| Evaluación de reserva | No conectada al evaluador | Adaptar lectura tras congelar y registrar primera apertura; exportar JSON/CSV/PDF. |
| Decisión final | Resultados preliminares de desarrollo | Justificar semántica o híbrida y contrastar con reserva sin reajustar sobre ella. |
| Entregables de clase 09 | Evidencias parciales | Consolidar Colab, README/bitácora, presentación PDF y acceso del profesor. |
| Git remoto | Cambios locales posteriores a e5be392 | Commit y push cuando se soliciten; revisar el diff completo, incluidos archivos nuevos. |

Rama de trabajo: `codex/backend-infra-ricoh-local`. Último commit publicado
registrado: `e5be392`. No se realizó commit ni push en este cierre.
Última imagen desplegada y verificada: `9ee9f10dd1f4` (hash completo abajo).
Últimas verificaciones: 26 pruebas API y HTTP de Swagger/esquema/assets/auth;
252 pruebas unitarias del trabajo de métricas/tiempos en su ejecución anterior;
ocho controles negativos de la estructura de reserva. No sumar recuentos ni
presentarlos como una ejecución conjunta nueva. No se repitieron pruebas,
consultas a proveedores ni operaciones Docker para actualizar este cierre.

### Actualización 21-10-2026: Swagger descriptivo desplegado

- Usuario pidió ampliar Swagger tras un rechazo de token. Se comprobó que
  DJANGO_API_TOKEN de backend/.env coincidía con el entorno del contenedor y
  categories devolvía 200 con él, 401 sin él o con Bearer duplicado. No se pudo
  determinar el encabezado exacto enviado por el navegador del usuario.
- `backend/api/documentation.py`: recorrido recomendado, autenticación paso a
  paso, diferencias entre search/query, límites, campos, citas, tiempos opcionales,
  estados documentales HTTP 200 y errores con códigos/acciones y encabezados.
  Ejemplos ilustrativos de entrada, éxito/error y tres resultados de query.
- `backend/api/contracts.py`: descripciones de campos; mismas restricciones.
  `backend/api/templates/api/swagger.html`: filtro, enlaces a operaciones y
  duración HTTP; autorización sigue sin persistirse y assets/validador locales.
- Todos los ejemplos se validan contra Pydantic y etiquetas de citas: **26 pruebas
  API locales correctas**. Sin llamadas a proveedores, sin ejecutar reserva.
- Imagen reconstruida y contenedor recreado, saludable:
  `sha256:9ee9f10dd1f4c70e1cfbd670a65da8ed76d84ab38b58c3f00dfa375254510153`.
  HTTP docs/OpenAPI/assets 200; categories autenticado 200, sin token 401.
  No había navegador disponible para inspección visual; verificación HTTP y esquema.
- Swagger: http://127.0.0.1:8000/api/v1/docs/ . Recargar y volver a autorizar
  con solo el valor de DJANGO_API_TOKEN. No se imprimieron ni cambiaron secretos.
- Guía actualizada: `backend/docs/API.md`. Sin commit ni push nuevos. La reserva
  continúa como borrador sin ejecución; el despliegue no implica evaluarla.

### Actualización 21-10-2026: conjunto de reserva estructurado, sin ejecutar

- `backend/cases/rag_reserve.json`, esquema propio `rag-reserve-v1`: **12
  candidatos**, nueve documentales con 25 unidades, tres de límite documental;
  17 fragmentos en catálogo con citas/offsets. Mismo corpus académico de 70.
- Guía y preguntas: `backend/docs/RAG_RESERVE.md`. No son paráfrasis deliberadas
  de desarrollo: cubren intervención interna, archivo individual, cola compartida,
  Ethernet dañado, incidente compartido, alta, exposición ya ocurrida, bloqueo,
  cierre por recurso y límites de catálogo/DNS/inventario. Revisión semántica de
  novedad pendiente; comparten corpus/categorías. No afirmar ceguera ni reserva
  independiente por familias: el agente conocía desarrollo y resultados previos.
- Estado **draft_pending_human_review**, split `reserve_candidate`; revisión por
  caso pendiente y ejecución `not_run`. No hay resultados de reserva.
- Verificador offline: desde backend,
  `python3 -m scripts.validate_rag_reserve --output docs/rag_reserve_validation.json`.
  Comprueba hashes, citas contra índice, duplicados exactos y estructura. Ocho
  controles negativos correctos; no certificar revisión semántica ni ausencia de
  ejecuciones externas no registradas. Cero modelos/llamadas a proveedores.
- `--require-ready` termina 1 mientras faltan revisión humana, congelación,
  decisión con desarrollo y snapshot de configuración. Solo verifica preparación;
  nunca ejecuta preguntas. Guardar también commit/huella externa del JSON al congelar.
- No está conectada al evaluador actual, que sigue fijo a desarrollo. No reemplazar
  `rag_evidence.json` con estos candidatos. Adaptar lectura cuando corresponda,
  conservar preguntas aprobadas y PDF automático de las futuras métricas.
- Secuencia: revisión humana → decisión con desarrollo → congelar configuración
  y reserva → apertura registrada → interpretar sin tuning sobre estos resultados.
  Si se usan para ajustar, retirar a desarrollo y crear otra reserva nueva.
- Sin métricas nuevas, despliegue, commit ni push. No se modificó código RAG/API.
  Las 252 pruebas previas corresponden al trabajo anterior; este paso se verificó
  con validación offline y controles negativos, sin repetir la suite ni el benchmark.

### Actualización 21-10-2026: módulo de comparación de tiempos terminado

- Guía: `backend/docs/TIMING_COMPARISON.md`. Implementación en
  `backend/src/rag/timing_comparison.py` y CLI
  `backend/scripts/compare_retrieval_times.py`.
- Desde backend: `../.venv/bin/python -m scripts.compare_retrieval_times`.
  Lee la matriz guardada y exporta **siempre JSON, CSV y PDF**, sin cargar modelos
  ni llamar a Supabase/Groq. Conserva la entrada y sus hashes; no repetir consultas
  para reconstruir informes. `--input` y `--output` permiten otros archivos.
- Archivos: `backend/docs/retrieval_metrics_20261021_times.json`, `.csv`, `.pdf`.
  PDF de tres páginas renderizadas e inspeccionadas, sin defectos observados.
- Trece pares válidos: media/mediana/P95 A = 200,90/188,37/291,13 ms;
  B = 409,30/398,69/555,66 ms. Mediana de diferencias emparejadas 208,77 ms;
  mediana de incrementos relativos 112,35%. Lectura léxica mediana 203,68 ms.
- Grupos separados: todos (13), documentales (7), comportamiento (6). Las
  medianas documentales son 188,38/401,05 ms; no confundirlas con todos los casos.
- A=embedding+semántica; B=embedding+subtotal híbrido. No sumar subtotal y sus
  hojas. Las variantes comparten componentes del experimento original: comparación
  descriptiva de desarrollo, una observación por pregunta, sin latencia HTTP,
  inicialización/Auth ni generación. No es un ensayo independiente de latencia.
- Datos inválidos excluyen el par completo con diagnóstico; etapas no aplicables
  N/E, sin ceros inventados. Exportación incompleta termina con error tras crear
  los tres archivos. P95 interpolado lineal; muestra pequeña.
- Seis pruebas nuevas, suite local completa **252 correctas**, recalculo
  independiente de estadísticas y comprobación de hash/26 filas CSV. Los recuentos
  inferiores en secciones siguientes son evidencias históricas.
- Sin despliegue, commit ni push nuevos. Cambios posteriores a e5be392 locales.
  Persisten revisión humana, reserva nueva, decisión y entregables consolidados.

### Preferencia vigente: PDF automático de la matriz de métricas

El usuario pidió que **siempre se cree un PDF de estas métricas**, adaptando el
módulo ya existente. Implementado:

- `PDFReport.generate_retrieval_metrics(report, source_json=...)` en
  `backend/src/pdf_report.py`, reutilizando estilos, tablas y NumberedCanvas.
  El método `generate()` de los reportes anteriores no cambia.
- `scripts.evaluate_retrieval_metrics.write_outputs` genera JSON, CSV y PDF de
  forma inseparable en el mismo directorio/nombre base. No agregar una opción
  que omita el PDF por defecto. Las matrices incompletas también generan PDF
  antes de terminar con error; un error de PDF se propaga y no se oculta.
- `--from-json <matriz.json>` regenera solamente PDF, sin validar el corpus,
  inicializar modelos ni llamar a Supabase/Groq. No repetir búsquedas para un PDF.
- Archivo actual: `backend/docs/retrieval_metrics_20261021.pdf`, tres páginas:
  agregados, matriz por caso y preguntas/trazabilidad. Mantiene N/E y ERROR,
  denominadores, revisión humana pendiente y SHA-256 del JSON fuente.
- PDF regenerado desde el JSON existente, sin alterar las métricas ni llamadas
  nuevas a proveedores. Tres pruebas nuevas; **246 unitarias correctas**.
  Se renderizaron e inspeccionaron las tres páginas con Poppler y se comprobó
  texto/paginación con pdfplumber, sin defectos visuales observados.
- Documentación en `backend/docs/RETRIEVAL_METRICS.md`. El PDF de métricas no
  acredita por sí solo la presentación final del proyecto del segundo corte.

Cambios aún locales sobre e5be392; sin commit/push ni reconstrucción del backend
por esta adaptación de informes. Conservar la preferencia en futuras ejecuciones.

### Actualización 21-10-2026: métricas de recuperación calculadas

El usuario pidió calcular las métricas. **Ejecutado en Supabase real**, sin Groq
ni escrituras; corpus académico activo de 70 fragmentos, índice intacto.

- Evaluador reproducible: `backend/scripts/evaluate_retrieval_metrics.py`;
  fórmulas: `backend/src/rag/retrieval_metrics.py`. Cuatro pruebas numéricas y
  suite local completa de **243 pruebas correctas**. Recalculo independiente de
  JSON/CSV correcto; no se repitió la regresión generativa de 13 consultas.
- Se ejecutaron 13 consultas; cero errores técnicos. Solo siete tienen unidades
  documentales. Los seis casos de comportamiento tienen métricas nulas y quedan
  fuera de los promedios. Todos siguen siendo desarrollo, sin reserva independiente
  ni revisión humana de las anotaciones.
- Comparación controlada: A semántica vs B BM25+semántica+RRF; mismo embedding y
  búsqueda semántica Top-10 por caso; Top-3 final. Ajuste por categoría desactivado,
  no se usa la categoría esperada ni se llama al clasificador. B conserva la unión
  completa hasta 20 candidatos del recuperador actual; no hay reranker.
- Promedios macro A/B: Precision@3 **47,62% / 52,38%**; Recall@3
  **73,81% / 80,95%**; Hit@3 **85,71% / 85,71%**; MRR@3
  **0,8571 / 0,8571**; cobertura Top-3 **78,21% / 80,36%**.
  Ambas cubren 26/35 unidades en total (micro 74,29%): el pequeño avance macro
  redistribuye aciertos entre preguntas de diferente número de unidades.
- Cobertura tras presupuesto **69,29% / 76,79%**. Contextos con prompt rag_v5,
  850 tokens, clasificación null en ambos y sin filtros de pertinencia; es una
  medición del recuperador aislado, no del pipeline completo de la API.
- Medianas observadas **0,1884 / 0,4011 s**: tiempos de componentes compartidos
  secuenciales, excluyen Auth/carga; no presentarlos como benchmark HTTP independiente.
- Casos: B mejora E06 (403), empeora cobertura E03 (Wi-Fi), y ambos fallan E05
  (mensaje sospechoso no abierto) en Top-3. SEG-02 está en candidatos profundos,
  se pierde en selección. No se cambió configuración ni anotación para ocultarlo.
- Informes versionables: `backend/docs/RETRIEVAL_METRICS.md`,
  `backend/docs/retrieval_metrics_20261021.json` y CSV con el mismo nombre.
  Incluyen preguntas, IDs, catálogo, rankings, aportes RRF, contexto/omisiones,
  tiempos, parámetros y hashes. El 13/13 previo de comportamiento es otra medida.

Pendientes: revisión humana de anotación/respuestas, reserva nueva, decisión
sobre configuración tras contrastar los intercambios y entregables consolidados.
No hay ganador definitivo. No hubo despliegue nuevo ni cambio de API; los cambios
posteriores a `e5be392` siguen locales y pendientes de commit/push.

### Actualización 21-10-2026: evidencias anotadas

El usuario pidió anotar evidencias para la evaluación de clase 09.
**Anotación del agente completada; revisión humana pendiente.**

- Datos: `backend/cases/rag_evidence.json`, esquema `rag-evidence-v1`.
- Lectura de los 70 fragmentos del corpus académico activo y contraste con los
  siete PDF originales/35 secciones. No se usó el índice Ricoh ni se ejecutó
  recuperación, embeddings o llamadas Groq/Supabase durante esta anotación.
- Se conservan preguntas y expectativas de `rag_regression.json`, con su hash.
  13 casos: siete documentales con 35 unidades requeridas y seis de comportamiento.
  Cada unidad tiene IDs, cita literal y offsets; catálogo con texto y procedencia.
  Se anotan condiciones, respuesta esperada, criterios de fallo y exclusiones.
- Conjunto relevante = unión de IDs de las unidades necesarias. Los seis casos
  de comportamiento tienen conjunto vacío; sus referencias a reglas de aclaración
  o rechazo no deben contarse como evidencia que resuelva la solicitud. Excluirlos
  de promedios de recuperación y cobertura, y evaluar comportamiento aparte.
- Los 13 casos ya se usaron para ajustar; todos se marcan desarrollo y ninguno
  reserva. No afirmar anotación ciega ni evaluación independiente. Preparar
  reserva nueva después, separando familias; no reciclar paráfrasis conocidas.
- Validador: desde backend `../.venv/bin/python -m scripts.validate_rag_evidence`.
  Verifica índice/configuración y sus hashes, PDF original, páginas, texto,
  preguntas originales, IDs, citas/offsets y unión de relevantes. No llama APIs.
  Inicialmente pasó y rechazó corpus distinto, cita alterada y unión incorrecta.
  Esto prueba integridad/fuente, no exhaustividad semántica ni revisión humana.
- Guía legible: `backend/docs/RAG_EVIDENCE.md`; informe:
  `backend/docs/rag_evidence_validation.json`. No se calcularon métricas ni se
  eligió estrategia. Pendiente revisión humana de unidades/relevancia/exclusiones.

Los cambios de anotación se suman a la auditoría y tiempos aún locales sobre
`e5be392`; sin nuevo commit/push ni reconstrucción del contenedor por esta tarea.

### Actualización 21-10-2026: tiempos por etapa implementados

El usuario pidió implementar el desglose de tiempos pendiente de clase 09.
**Implementado y desplegado**, sin cambiar prompts, corpus ni ranking:

- `src/rag/timing.py`: cronómetro monotónico acumulativo, incluso en excepciones.
- `Retriever` separa embedding, búsqueda semántica/RPC, lectura paginada del corpus
  léxico, BM25, RRF y puntuación extra de resultados exclusivamente léxicos.
  `retrieval_seconds` sigue siendo subtotal sin embedding; no sumarlo de nuevo.
- `repository.lexical_candidates` separa I/O de ranking; `lexical_search` conserva
  su interfaz previa y aplica los mismos filtros/ordenación.
- Pipeline conserva duraciones fallidas, acumula validación/revisión repetidas y
  mide generación correctiva aparte; agrega `total_seconds` y versión `stages-v1`.
- API search/query publica `tiempos_segundos`; Swagger y `docs/API.md` actualizados.
- La regresión escribe tiempos por caso en JSON y `timings.csv`, con estados de
  error explícitos y celdas vacías para etapas no ejecutadas. No se reescribieron
  tiempos históricos. No repetir la suite Groq solo para obtener esos archivos.
- 239 unitarias y 25 API locales correctas; 25 API también dentro de la imagen.
  Verificación con embeddings reales y el corpus local de 70 registros: mismos
  candidatos/puntajes que el recuperador previo para las 13 preguntas.
- HTTP real search/query 200; consulta 403 `OK_VALIDADO`, pipeline 7,5787 s y HTTP
  8,4919 s. Es una observación, no benchmark. Inicialización de recursos, Auth y
  carga anterior a `run_rag_case` quedan fuera de los tiempos del pipeline.
- Imagen activa: `sha256:efb734fd3c91d1ec6b4de90144f1fdb76b6417a794f2df6810a182e7e3e0c67b`.
  Docker resolvió una nueva base Python al reconstruir; no cambiaron los archivos
  de dependencias. `pip check`, API en contenedor y ambas consultas reales pasaron.
- Guía: `backend/docs/STAGE_TIMINGS.md`; evidencia:
  `backend/docs/stage_timing_validation.json`. Auditoría previa de clase 09:
  `backend/docs/CLASS09_AUDIT.md`, con actualización de instrumentación.

Base publicada `e5be392` en `codex/backend-infra-ricoh-local`. La auditoría y estos
cambios posteriores siguen locales, sin nuevo commit/push. El informe
`backend_validation.json` sigue describiendo la regresión anterior: no atribuir
su 13/13 a una nueva ejecución remota de esta instrumentación. Siguen pendientes
la comparación A/B, Precision/Recall/MRR/cobertura del corpus activo, reserva,
revisión humana y entregables consolidados. Ricoh sigue fuera de la API.

### Historial inmediato: aclaraciones y regresión


El usuario pidió resolver el tratamiento de preguntas ambiguas y completar la
regresión del backend. **Realizado y desplegado** el 20-10-2026:

- `system_v7` y `rag_v5`; contexto compacto conserva `datos_faltantes`.
- Política local pide comportamiento y mensaje ante incidentes vagos, incluso
  con marca/modelo. Conserva el texto original en el resumen y genera aclaraciones
  locales auditables (`LOCAL_CLARIFICATION`), sin diagnóstico documental.
- Instalación sin privilegios deriva a software/soporte independientemente de
  la categoría inicial. Riesgo físico excluye comprobaciones ordinarias de energía.
- 234 unitarias, 24 API y comprobación Django correctas.
- Regresión real Supabase/Groq: **13/13** según criterios de entrega. Ocho
  `MODEL_SUPPORTED`, tres `LOCAL_CLARIFICATION`, dos abstenciones seguras
  (`MODEL_REJECTED` reemplazado, E07/E09). No afirmar 13 respuestas aprobadas por
  el modelo: las salidas rechazadas siguen rechazadas. Los casos que exigen un
  procedimiento respaldado no aprueban por abstención.
- HTTP real del contenedor: consulta Ricoh ambigua 200/`OK_PIDE_ACLARACION`,
  datos faltantes explícitos y sin «no imprime»; consulta general de impresora
  200/`OK_VALIDADO`, con fuentes y sin preguntas innecesarias.
- Evidencia versionable: `backend/docs/backend_validation.json` y
  `backend/docs/BACKEND_VALIDATION.md`. Trazas en `backend/docs/rag_runs/`
  ignoradas. Comando desde backend: `../.venv/bin/python -m
  scripts.validate_rag_scenarios --output docs/rag_runs/validation` (cuota real).
- Imagen activa: `sha256:9130bb2b931300144628ac4e36b488bd7302e5db5f7f1e53b99eee80cf35cc8c`.

La rama `codex/backend-infra-ricoh-local` se publicó previamente en `057380f`.
El usuario autorizó actualizar `.agents`, crear el commit con estas correcciones
y publicar inmediatamente en esa misma rama. Esta actualización de continuidad
forma parte del commit de entrega `fix: clarify ambiguous requests and validate backend regression`.
Consultar `git log -1` y `git status -sb` para su identificador y sincronización.
No requiere repetir llamadas a Groq ni desplegar: la imagen corregida ya está activa.
Mantener simple el alcance: el manual Ricoh permanece fuera de la API, cuyo
índice académico conserva 70 fragmentos. No continuar la integración de Ricoh
ni la prueba de aislamiento entre usuarios. Sus limitaciones locales anteriores
(impresión Hold/Stored y presupuesto de contexto) siguen pendientes.

### Estructura y cambios locales

- `backend/`: Django/API, `src/`, `schemas/`, `scripts/`, `test/`, `prompts/`,
  `cases/`, notebooks, corpus, manuales, documentación y requirements.
- `frontend/`: solo README; framework y aplicación aún no elegidos.
- `infra/`: `compose.yaml`, README y `supabase/migrations/`.
- `.agents/`: continuidad y especificación histórica del diagrama del notebook.
- `.venv/` y `.venv-test/` siguen en la raíz para conservar sus rutas instaladas.
- Configuración privada en `backend/.env`; plantilla `backend/.env.example`.
  No imprimir credenciales ni incorporarlas a Git o a la imagen.

Rama de entrega: `codex/backend-infra-ricoh-local`, creada desde `83f2110`
(`codex/implement-embeddings`). El usuario autorizó incluir todos los cambios
versionables en un commit y subir esta rama a origin, sin integrar con la rama
base. La entrega incluye reorganización, Docker, extracción/evaluación local de
Ricoh y documentación. Los secretos, cachés, índices y extracciones generadas
siguen ignorados. Consultar `git log -1` y `git status` para el commit y estado
final de publicación. No ampliar la integración del manual complejo por ahora.

El commit 83f2110 dejó de seguir 47 `.pyc` sin borrarlos localmente. `.gitignore`
excluye `.env` y `.env.*` (excepto `.env.example`), `.aws/`, entornos, bytecode,
índices, cachés, trazas y artefactos personales de Drive. Las exclusiones con
rutas concretas se actualizaron al prefijo `backend/`. Conservarlas.

### Backend desplegado y autenticación

Contenedor **`infra-backend-1`**, saludable en la comprobación del 20-10-2026.
Imagen `ti-support-rag-backend:local`; imagen desplegada actual (21-10-2026)
`sha256:efb734fd3c91d1ec6b4de90144f1fdb76b6417a794f2df6810a182e7e3e0c67b`.
El ID del primer build que figura en el historial y `docker_validation.json`
corresponde a la validación anterior; Compose reconstruyó después con caché.
Imagen de unos 1,28 GB sin comprimir: PyTorch CPU es el mayor componente.

- API: `http://127.0.0.1:8000/api/v1/`.
- Swagger: `http://127.0.0.1:8000/api/v1/docs/`.
- Endpoints en `backend/api/urls.py` y `controllers.py`; prefijo en
  `backend/ti_api/urls.py`; recuperación/generación en `backend/api/services.py`.
- `categories`, `rag/search` y `rag/query` requieren `Authorization: Bearer`
  con **DJANGO_API_TOKEN**, no una clave o JWT de Supabase. En Swagger introducir
  solo el valor, sin `Bearer`; la autorización no persiste al recargar.
- El 401 de categories se reprodujo sin token, con clave Supabase y con Bearer
  duplicado. Con el token correcto devuelve 200 y las siete categorías.
  Token del contenedor y del `.env` local comprobados iguales, sin mostrarlos.
- Conexión Supabase desde el contenedor comprobada: autenticación y 70 fragmentos
  visibles; proyecto `fmsoacmvsmfrnbmnvizo`. Las sesiones se obtienen mediante
  usuario/contraseña Auth y clave publicable; no necesita Access Token personal
  para operar. No usar service_role ni desactivar RLS.
- El usuario **descartó** la prueba entre dos usuarios; no retomarla por iniciativa
  propia. Las verificaciones de dos clientes son del mismo usuario.

Compose inyecta el `.env`, publica solo en localhost y monta en lectura
`backend/data/indexes/sections/` en `/app/data/indexes/sections`.
Volúmenes: `ti-support-rag-model-cache` y `ti-support-rag-tokenizer-cache`.
El modelo real se descargó y se comprobó compatible con el índice desde la imagen.
Gunicorn usa un proceso, cuatro hilos y el semáforo RAG del backend.
Los cambios de código requieren reconstruir la imagen; los cambios del `.env`
requieren recrear el contenedor. La imagen no copia el PDF ni datos locales.

### Consultas HTTP reales ejecutadas

Ambas pasaron por Supabase/Groq y devolvieron HTTP 200, `OK_RESPUESTA_PARCIAL`:

1. «El portal de documentos devuelve error 403. ¿Eso demuestra que mi cuenta está
   suspendida?» → categoría `acceso`; cita ACS-03 y ACS-05; no confirma suspensión.
   Tiempo HTTP total 20,778 s; latencia del pipeline reportada 3,4762 s.
2. «Tengo problemas al enviar impresiones en la Ricoh MP 4002.» → `hardware`;
   cita HW-03 y HW-05 del manual académico general, **no el manual Ricoh**.
   Tiempo HTTP 8,862 s; pipeline 6,9628 s.

Trazas locales ignoradas por Git:
`backend/docs/rag_runs/http_query_check_20261020.json` y
`backend/docs/rag_runs/http_query_ricoh_mp4002_20261020.json`.
Observación de calidad pendiente: en la segunda, `datos_faltantes: []` pese a
reconocer que faltan síntomas/configuración/errores; también resume «problemas al
enviar impresiones» como «no imprime». Corregido posteriormente para incidentes vagos: ver la sección de continuidad
y `backend/docs/backend_validation.json`; esta traza antigua se conserva sin editar.
No volver a llamar Groq solo para leer esas respuestas guardadas.

### Manual Ricoh: identidad verificada y registro listo

Original intacto: `backend/manuals/hardware/RICOHMP4002_MANUAL.pdf`.
Registro separado: `backend/manuals/manifest.real.json`.
Evidencia: `backend/docs/ricoh_manual_verification.json`.
Guía/estado: `backend/manuals/README.md`.

- ID `RICOH-MP4002-USER-GUIDE-EN`, idioma `en`, 228 páginas, 5.520.145 bytes.
- SHA-256 `3e5a0a2702efdc320633c1409159a0d28d533c1f98239b9f9ddb6dd8b7b8c1d5`.
- **Idéntico byte por byte al PDF oficial de Ricoh**. No hace falta repetir la
  investigación ni volver a atribuir compatibilidad solo al nombre del archivo.
- Ricoh lo lista para Aficio MP 4002/4002SP/5002/5002SP:
  https://support.ricoh.com/bb_v1oi/html/oi/re/model/mp42/mp42en.htm
- Copia oficial comparada:
  https://support.ricoh.com/bb_v1oi/pub_e/oi/0001043/0001043003/VD1297802_01/D1297802_en.pdf
- `version: D129-7802` es el código editorial de la página PDF 228; no firmware.
  Copyright 2011 (página PDF 227). Actualización de la descarga: 2012-01-10;
  `document_date` queda null porque no se acreditó fecha exacta de publicación.
- `model_verified_from_official_source` y `official_source_verified`: true.
  `model_verified_from_document`: false porque el modelo no aparece explícito en
  el texto del PDF. No es una contradicción: la fuente oficial y los bytes
  idénticos establecen la asociación. Hay variaciones por región y opciones.
- Texto extraíble, página PDF 2 visualmente en blanco, tablas de mensajes/causas/
  soluciones; no requiere OCR general. Página PDF 185 = página impresa 183.
- `simulated: false`, estado **`locally_indexed_retrieval_partial`**.
- Extracción local en `backend/data/extracted/RICOH-MP4002-USER-GUIDE-EN/`: JSON,
  Markdown de revisión, resumen y muestras visuales. Directorio ignorado por Git.
  Guía: `backend/docs/RICOH_EXTRACTION.md`. Evidencia: `backend/docs/ricoh_extraction_validation.json`.

Se generaron fragmentos y embeddings locales en `backend/data/indexes/ricoh-local-v1/`,
con formato propio y sin subir este manual a Supabase. Ver
`backend/docs/RICOH_LOCAL_RETRIEVAL.md` y `backend/docs/ricoh_local_retrieval_validation.json`.
Los manifiestos académicos `backend/manuals/manifest.json` y
`backend/data/corpus/v2/manifest.json` conservan sus siete documentos simulados.
El RAG activo sigue con 70 fragmentos del corpus
`ti-manuals-v2-d479e96962b17496eaa3`.

### Aspectos técnicos para el próximo trabajo de ingestión

El extractor nuevo `backend/src/rag/external_ingestion.py` y el comando
`backend/scripts/extract_real_manual.py` procesan el registro real por separado.
`backend/src/rag/ingestion.py` (académico) solo admite `simulated: true`, rechaza páginas sin
texto y detecta únicamente encabezados del tipo `HW-02 | ...`. Por eso el importador académico no procesa
el PDF real; no se modificó su contrato. No marcarlo como simulado ni quitar validaciones sin separar el
formato real del académico. `manifest.real.json` ahora admite un perfil para el extractor local, todavía
no un contrato de indexación admitido por el importador académico. `load_corpus` solo lee archivos listados;
poner el PDF en `manuals/` no activa recuperación.

Conservar procedimientos, condiciones, advertencias y filas completas de tablas,
la procedencia, idioma, versión y páginas PDF/impresas. El modelo es multilingüe:
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, revisión
`e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, 384 dimensiones normalizadas, máximo
128 tokens. El corte actual de 80 tokens y los encabezados consumen ese límite;
evaluarlo antes de aplicarlo a procedimientos largos. No cambiar de modelo sin
revisar/reconstruir la representación del índice.

La verificación `backend/scripts/verify_supabase.py` admite solo 1000 filas por
corpus; añadir paginación si se supera. La recuperación léxica ya pagina, pero
lee todas las filas compatibles: medir el impacto del corpus mayor. Top-3 y
presupuesto de 1000 tokens de entrada por llamada siguen activos. Validar primero
extracción y recuperación local en español; después planear la carga remota y el
cambio de índice/contenedor. No reindexar ni subir por cada consulta.

### Validaciones y comandos actuales

Tras la reorganización: 210 pruebas unittest y 24 pruebas Django/API aprobadas;
Django check correcto. Sintaxis de notebooks y primera celda de los tres probadas
desde la raíz, sin ejecutar todos los notebooks. En la imagen: 24 pruebas API,
imports y embeddings reales/compatibilidad del índice aprobados; HTTP health,
docs, OpenAPI y categories autenticado 200. No se repitieron esas suites al
editar metadatos o preparar este handoff. Suite remota completa de diez escenarios
con configuración final sigue sin aprobarse; no confundirla con dos consultas HTTP.

Desde la raíz del repositorio:

```bash
source .venv/bin/activate
cd backend
python manage.py check
python manage.py test api
python -m unittest discover -s test
```

Docker, desde la raíz:

```bash
docker compose -f infra/compose.yaml ps
docker compose -f infra/compose.yaml logs --tail=30 backend
docker compose -f infra/compose.yaml build
docker compose -f infra/compose.yaml up -d --wait
```

El build puede requerir permiso del entorno para actualizar el caché Docker fuera
del workspace. No cambiar HOME ni eludir permisos. Mantener credenciales fuera
de salidas y argumentos de comandos. Las consultas Groq reales consumen cuota.
El usuario indicó que no necesita más trabajo en Drive: no ejecutar el script
personal de organización ni consultar Drive sin nueva solicitud.

## Historial anterior — referencia, no estado vigente

El informe original es del 14-10-2026. Se conserva abajo junto con sus
actualizaciones. Sus afirmaciones sobre ramas, rutas, tareas pendientes,
contenedores, identidad del manual o trabajo sin publicar pueden estar superadas
por el estado actual de arriba.

## Resumen para el siguiente agente

El proyecto implementa soporte TI con clasificación estructurada, recuperación documental mediante embeddings en Supabase, generación con Groq, citas y controles locales. Existe una API Django funcional y Swagger UI. La infraestructura y la recuperación real están comprobadas; la suite remota completa con la configuración final sigue pendiente por cuota de Groq. No afirmar que todas las respuestas futuras están garantizadas.

El usuario pidió documentar el estado y los cambios en el directorio existente `.agents/`. No pidió un nuevo commit ni push en esta última tarea. Conservar los cambios locales existentes.

## Git y trabajo sin publicar

- Repositorio remoto: `git@github.com:dvdm12/TI-support-RAG.git`.
- Rama activa: `codex/implement-embeddings`, seguimiento `origin/codex/implement-embeddings`.
- HEAD observado: `df58432` — `feat: implement documentary RAG with Supabase and embeddings`.
- En la vista local, HEAD coincide con la referencia de seguimiento; no se hizo fetch para verificar cambios remotos recientes.
- Las mejoras posteriores del RAG, límites de tokens, API Django y Swagger están sin commit. Hay archivos modificados y archivos nuevos sin seguimiento. Revisar `git status --short` y `git diff` antes de actuar; `git diff --stat` no incluye archivos nuevos sin seguimiento.
- Modificados: `.env.example`, `.gitignore`, `README.md`, `docs/RAG.md`, `docs/rag_validation.md`, `requirements.txt`, `src/groq_client.py`, `src/pdf_report.py`, `src/rag/config.py`, `src/rag/context.py`, `src/rag/pipeline.py`, `src/rag/repository.py`, `src/rag/retrieval.py`, `test/test_groq_client.py`, `test/test_rag.py`.
- Nuevos: `api/`, `ti_api/`, `manage.py`, `cases/rag_regression.json`, `docs/API.md`, `docs/api_validation.json`, `docs/rag_hardening_verification.json`, `scripts/validate_rag_scenarios.py`, `prompts/system_v5.md`, `prompts/system_v6.md`, `prompts/rag_v3.md`, `prompts/rag_v4.md`, `src/token_budget.py`, `src/rag/applicability.py`, `src/rag/lexical.py`, `src/rag/policy.py`, `src/rag/support.py`, `test/test_rag_hardening.py` y este informe. Lista ampliada en «Revisión local del estado».

## Arquitectura y archivos principales

Flujo: texto o imagen opcional → OCR → clasificación `SolicitudTI` → políticas locales → recuperación híbrida → contexto con fuentes → generación `RespuestaRAG` → validación de citas y respaldo → decisión final → traza/PDF.

| Componente | Ubicación |
|---|---|
| Configuración y selección de prompt | `src/config.py`, `src/rag/config.py` |
| Contratos de clasificación y respuesta | `schemas/request_v1.py`, `schemas/rag_response_v1.py` |
| Cliente Groq y presupuesto de entrada | `src/groq_client.py`, `src/token_budget.py` |
| Ingesta, fragmentación, embeddings, índice | `src/rag/ingestion.py`, `chunking.py`, `embeddings.py`, `index.py` |
| Supabase y recuperación | `src/rag/repository.py`, `retrieval.py`, `lexical.py` |
| Contexto, pipeline y citas | `src/rag/context.py`, `pipeline.py`, `citations.py` |
| Políticas, pertinencia y respaldo | `src/rag/policy.py`, `applicability.py`, `support.py` |
| Reportes PDF | `src/pdf_report.py` |
| API y contratos HTTP | `api/controllers.py`, `services.py`, `contracts.py`, `urls.py` |
| Proyecto Django | `ti_api/settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `manage.py` |
| Swagger y OpenAPI | `api/documentation.py`, `api/templates/api/swagger.html` |
| CLI y validadores | `scripts/` |
| Notebooks | `notebooks/ti_support.ipynb`, `notebooks/rag_chunking_comparison.ipynb` |

Categorías: `hardware`, `software`, `redes`, `cuentas`, `seguridad`, `acceso`, `otros`. El clasificador usa el `system_vN.md` de mayor versión: actualmente `prompts/system_v6.md`. El prompt documental se selecciona explícitamente: actualmente `prompts/rag_v4.md`.

## Corpus, embeddings y Supabase

- Corpus académico simulado: `data/corpus/v2/`, siete PDF, 14 páginas, 35 secciones. No confundir estos manuales simulados con los originales organizados anteriormente ni con documentación operativa real.
- `data/corpus/v2/manifest.json` registra fuentes y hashes para comprobar integridad y procedencia.
- Seguridad incluye secciones de mensaje/enlace sospechoso y credenciales posiblemente expuestas; verificar texto y condiciones antes de afirmar que cubre un procedimiento concreto de phishing.
- Índice activo: `data/indexes/sections/` (`records.json`, `vectors.npy`, `config.json`), ignorado por Git.
- Corpus ID: `ti-manuals-v2-d479e96962b17496eaa3`; 70 fragmentos.
- Modelo: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Revisión: `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`; 384 dimensiones, vectores normalizados, coseno, límite efectivo 128 tokens. Fragmentos de hasta 80 tokens incluyendo encabezado.
- Se compararon cortes por caracteres, solapamiento y secciones; `sections` es la configuración activa, sin declarar un ganador general. Evidencia: `docs/rag_comparison.json`.
- Supabase: proyecto `TI-support-RAG`, referencia `fmsoacmvsmfrnbmnvizo`.
- Migración aplicada: `supabase/migrations/20261014_documentary_rag.sql`.
- Tabla: `public.clase08_fragmentos`; RPC: `public.clase08_buscar_fragmentos`; pgvector en `extensions`.
- Clave primaria: `(owner_id, corpus_id, chunk_id)`. RLS limita SELECT/INSERT/UPDATE a filas propias; sin DELETE ni acceso anónimo. RPC `SECURITY INVOKER`.
- Se hizo upsert dos veces, manteniendo 70 filas, y se verificaron textos/ranking desde dos clientes nuevos del mismo usuario. Falta la prueba entre dos usuarios Auth reales distintos.

## Cambios posteriores al commit RAG

1. Recuperación híbrida: candidatos por coseno y BM25, fusión de rangos (constante 60), preferencia suave de categoría (0,025), Top-3. BM25 lee las filas del corpus y usuario bajo RLS; adecuado para el corpus pequeño, no para grandes volúmenes.
2. Políticas auditables: distinción cuentas/acceso, corrección para error 403 y operaciones de cuenta, escalamiento de síntomas físicos y falta de privilegios. Conservan salida original y consideran negaciones/condiciones.
3. Respaldo documental: otra llamada al mismo modelo revisa afirmaciones frente a fuentes. Una corrección máxima y nueva revisión; si no supera el control, devuelve una limitación explícita. La revisión puede tener fallos correlacionados.
4. Pertinencia: se filtran pasajes/consejos de cambio de contraseña cuando el usuario no abrió el enlace sospechoso y no reporta exposición. La exposición por otra vía o petición explícita conserva esa ruta.
5. Cuota y errores: estimación por proceso/modelo, espera y reintentos acotados de HTTP 429; máximo 120 segundos de espera por reintentos. Un reintento del HTTP 400 reconocido como `json_validate_failed`; no se exponen cuerpos del proveedor ni credenciales. La suite se detiene al bloquearse por cuota.
6. Presupuesto: máximo local de **1000 tokens de entrada por llamada**, contando mensajes, esquema JSON y reserva conservadora de 96 tokens (`tiktoken`, `o200k_harmony`). Se rechaza antes de enviar si excede, y se rechaza la salida si Groq informa más de 1000 `prompt_tokens`. El contexto incluye pasajes completos o los omite y conserva su procedencia en trazas.
7. Generación: `openai/gpt-oss-20b`, razonamiento bajo, máximo de salida 800 tokens; prompts compactos, respuesta documental de hasta 90 palabras y limitación de 25. El límite observado de 8000 en Groq es TPM, no tokens por consulta; el presupuesto local no evita agotar la cuota acumulada.
8. Regresión: diez escenarios en `cases/rag_regression.json`, ejecutables con `scripts/validate_rag_scenarios.py`. Reportes conservan citas, omisiones, revisión y errores.

## API Django y Swagger añadidos

Django 5.2.18 en `.venv`; API nativa con vistas de clase, sin Django REST Framework. No utiliza base de datos Django, usuarios ni sesiones de Django.

| Método | Ruta | Autenticación | Función |
|---|---|---|---|
| GET | `/api/v1/health/` | Pública | Proceso vivo y límite de entrada; no comprueba proveedores |
| GET | `/api/v1/categories/` | Bearer | Siete categorías |
| POST | `/api/v1/rag/search/` | Bearer | Recuperar pasajes de Supabase sin generación Groq |
| POST | `/api/v1/rag/query/` | Bearer | Clasificación, recuperación y respuesta documental con citas |
| GET | `/api/v1/docs/` | Pública | Swagger UI |
| GET | `/api/v1/openapi.json` | Pública | Esquema OpenAPI 3.1 |

Entradas: query `{ "pregunta": "..." }`; search admite además `categoria` opcional. Contratos Pydantic estrictos; campos extra prohibidos; cuerpo máximo 16 KiB. Errores JSON con `request_id`: 400, 401, 405, 413, 415, 422, 429, 502 y 503 según la operación. Estados documentales de aclaración, parcial o evidencia insuficiente pueden devolver HTTP 200.

Autenticación: `DJANGO_API_TOKEN` local, al menos 32 caracteres; no es el JWT de Supabase. Todos los consumidores del API usan el mismo usuario Supabase configurado en `.env`. No hay aislamiento individual por consumidor. POST sin autenticación por cookies, con Bearer explícito y exención CSRF en esas vistas; middleware CSRF instalado, sin CORS abierto. Semáforo: una operación RAG/búsqueda por proceso; otras reciben 503. API síncrona, sin cola persistente. OCR sigue disponible por CLI, no como carga de imagen HTTP.

Swagger: `drf-spectacular-sidecar==2026.10.1`, assets locales con lista permitida servidos incluso con `DEBUG=False`. No se usa CDN ni validador externo; token no se inyecta ni persiste al recargar. En **Authorize**, introducir solo `DJANGO_API_TOKEN`, sin `Bearer`. Esquema definido en `api/documentation.py`, reutiliza contratos Pydantic; mantenerlo alineado con cambios en controllers y respuestas.

## Validaciones ejecutadas y límites de la evidencia

- Suite existente: **201 pruebas aprobadas** antes de Swagger.
- Django/API: **24 pruebas aprobadas** después de Swagger, incluidos contratos, auth, límites, errores, concurrencia, esquema y assets con DEBUG desactivado.
- `python manage.py check`: sin problemas. `git diff --check`: sin errores al cerrar Swagger.
- HTTP real API: health 200, categories 200, query sin token 401, query inválida 400, búsqueda Supabase 200 con tres pasajes de SEG-03/SEG-02. No se ejecutó generación real de Groq mediante el endpoint HTTP.
- Swagger comprobado visualmente: muestra cuatro operaciones; **Try it out → Execute** en health obtuvo 200 y `input_token_limit: 1000`.
- Integración RAG previa: consulta completa con Supabase y Groq aceptó citas F1/F3 de hardware; la decisión local conservó `OK_PIDE_ACLARACION`. No certifica la configuración final de todos los escenarios.
- En la comprobación posterior de entrada limitada se observaron 531, 770 y 703 tokens reales de clasificación/generación/revisión. La respuesta inicial fue rechazada por consejo de contraseña no pertinente. Tras filtrar, el caso E05 se bloqueó por HTTP 429 (espera 238 s, superior a 120 permitidos).
- Última tanda anterior al nuevo límite: tres de diez casos aprobados, siete bloqueados por cuota. **La suite remota completa con configuración final no está aprobada**.
- El PDF fue generado y revisado en etapas anteriores; no se regeneró por las incorporaciones Django/Swagger. Revisar su vigencia antes de entregarlo como reporte actual.

Evidencia: `docs/supabase_verification.json`, `docs/rag_hardening_verification.json`, `docs/api_validation.json`, `docs/rag_comparison.json`, `docs/rag_validation.md`, `docs/API.md`. Trazas detalladas: `docs/rag_runs/` (ignorado).

Advertencias sobre documentos históricos: `docs/api_validation.json` conserva 20 pruebas del momento anterior a Swagger; el total posterior es 24. `docs/RAG.md` menciona al principio `rag_v2` y después documenta `rag_v4`; manda la configuración activa. `docs/rag_validation.md` y `docs/supabase_setup.md` conservan cifras de 185 y frases de etapas antiguas sobre push o revisión pendiente. No tratarlas como estado actual sin leer los apartados posteriores y el código.

## Entorno y comandos para continuar

Activar siempre `.venv` antes de instalar dependencias o ejecutar. Entorno observado: Python 3.12.3. No instalar globalmente ni imprimir `.env`. Variables documentadas en `.env.example`: `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_EMAIL`, `SUPABASE_PASSWORD`, `DJANGO_SECRET_KEY`, `DJANGO_API_TOKEN`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`. La contraseña Auth es distinta de la de PostgreSQL. No usar `service_role` ni desactivar RLS.

```bash
source .venv/bin/activate
python manage.py check
python manage.py test api
python -m unittest discover -s test
```

El servidor local quedó iniciado al finalizar Swagger en `127.0.0.1:8000` con `--noreload`. Su continuidad depende de la sesión; comprobarlo antes de iniciar otro proceso. Reiniciarlo tras modificar código; no matar procesos ajenos.

```bash
source .venv/bin/activate
HF_HOME=/tmp/ti-rag-hf HF_HUB_OFFLINE=1 HF_HUB_DISABLE_PROGRESS_BARS=1 PYTHONDONTWRITEBYTECODE=1 python manage.py runserver 127.0.0.1:8000 --noreload
```

Estas opciones offline suponen que el modelo ya está en `/tmp/ti-rag-hf`; ese caché es temporal. Si falta, permitir su descarga legítima y configurar un caché persistente. `tiktoken` utiliza `.cache/tiktoken/`, ignorado. `.venv`, índice, cachés y trazas no se suben a Git.

Comandos de integración (requieren credenciales; las consultas Groq consumen cuota):

```bash
python -m scripts.verify_supabase
python -m scripts.query_rag "¿Qué hago ante un error 403?"
python -m scripts.validate_rag_scenarios --output docs/rag_runs/regression
```

Si falta el índice, reconstruirlo con `scripts.index_manuals` y revisar corpus ID/revisión antes de cargar. No reindexar ni subir de nuevo solo para consultar.

## Pendientes prioritarios

1. Completar la suite remota de diez escenarios cuando haya cuota, conservando trazas y separando fallos reales de bloqueos del proveedor. No alterar expectativas para hacer pasar los casos ni eliminar límites/revisión de respaldo.
2. Probar RLS con dos usuarios Supabase Auth reales distintos y acceso/escritura cruzados. Los dos clientes ya probados pertenecían al mismo usuario.
3. Ejecutar el notebook completo y revisar tiempos en el entorno de entrega.
4. Actualizar documentos históricos, evidencia y PDF si se solicita un reporte consolidado actual.
5. Revisar diff y archivos nuevos antes de un commit/push autorizado. Nunca incorporar secretos, cachés, índices o trazas sensibles.
6. Para despliegue real: servidor WSGI/ASGI apropiado, HTTPS, identidades de cliente según requisitos y estrategia de concurrencia/cuota entre workers. El servidor de desarrollo actual es local.

No se hicieron nuevas consultas remotas, migraciones, cargas, commits ni pruebas durante la preparación de este informe: se consultó código, Git y evidencia existente.


## Actualización: práctica fiel de clase 08 (14-10-2026)

El notebook `notebooks/clase_08_rag_supabase_groq.ipynb` fue sustituido por el recorrido principal de diez pasos del profesor, como código cliente de `src/class08_client.py`. Conecta, carga por upsert y genera directamente; solo `EJECUTAR_PRUEBAS=False` permanece opcional. No incluye clasificación/híbrido/revisión por modelo/API en la práctica. El entorno local, índice propio, límite de entrada y configuración Groq se documentan en `docs/CLASE08.md`.

La ejecución real de diez celdas pasó: 70 filas comprobadas tras upsert, una generación Groq HTTP 200 aceptada (`parcial`, 724 tokens de entrada), persistencia de la misma pregunta desde otro cliente del mismo usuario. Suite local: 209 pruebas aprobadas. Resumen: `docs/class08_practice_validation.json`; resultados de sesión: `docs/rag_runs/clase08/20261014T202812739447Z/`, ignorados en Git. Los archivos `class08_notebook_validation.json` y `class08_notebook_retest.json` describen el notebook anterior, no el nuevo. Revisión humana y cinco pruebas adicionales siguen pendientes; se registró revisión documental del agente, sin atribuirle carácter humano. No se hizo commit/push de estos cambios.


## Verificación de métricas clase 08 — resultado parcial

Se ejecutó el notebook con las cinco pruebas opcionales activadas en una copia, conservando el valor False del fuente. Sesión: `docs/rag_runs/clase08/20261014T203144285329Z/`. Seis llamadas Groq reales aceptaron contrato/citas, entradas 717–736 tokens, generación media 0,8449 s, 70 filas comprobadas y persistencia correcta. Tres de cinco estados adicionales coincidieron. Falló el caso ambiguo: «¿Cómo lo hago?» obtuvo respondida con pasos concretos en vez de aclaracion. La paráfrasis conservó significado pero produjo parcial en vez de respondida. No afirmar cumplimiento completo. Faltan tiempos separados por etapa y justificación semántica de fragmentación. Informes: `docs/class08_metrics_report.md`, `docs/class08_metrics.json`, `docs/class08_metrics_execution.json`. No se corrigieron comportamientos ni expectativas durante esta auditoría.


## Drive (histórico; ya no es tarea activa)

El usuario indicó que **no se necesitan más consultas a Drive**; no hacer peticiones a `thor:` salvo nueva solicitud explícita. Estado final observado en sesión (14-10-2026): en `thor:Mesa de Ayuda TI inteligente/Clases/` existen `Clase-02`, `Clase-03`, `Clase-06` (notebook de clase 06 movido por el usuario y `bitacora_clase_06.md` subida y verificada por tamaño), `Clase-07` (notebook y bitácora, verificados por coincidencia en `docs/drive_classes_07_08_upload.json`) y `Clase-08` (`bitacora_clase_08.md`; ese JSON registra copia correcta pero `verified: false`). El ZIP del Parcial 1 seguía en la raíz de la carpeta. `docs/drive_upload_verification.json` (estado `blocked_by_drive_api_quota`) quedó obsoleto: describe el bloqueo por cuota previo, no el estado final. `scripts/organize_drive_classes.py` y `.venv/drive-upload-staging/` quedan como restos de esa tarea; no ejecutarlos sin pedirlo.


## Revisión local del estado — 14-10-2026, tarde

Revisión hecha solo en local (sin Supabase, Groq ni Drive), sin modificar código.

**Git.** Rama `codex/implement-embeddings`, HEAD `df58432`, igual a su seguimiento local (sin fetch). `main` en `2a63142`. Todo el trabajo posterior al commit RAG sigue sin commit. Además de los modificados listados arriba, ahora también aparece `notebooks/ti_support.ipynb` modificado (y varios `__pycache__/*.pyc` versionados por error, que conviene no incluir en un commit). Nuevos sin seguimiento añadidos desde la lista inicial: `notebooks/clase_08_rag_supabase_groq.ipynb`, `src/class08_client.py`, `test/test_class08_client.py`, `docs/CLASE08.md`, `docs/backend_supabase_validation.json`, `docs/class08_*.json`, `docs/class08_metrics_report.md`, `docs/drive_classes_07_08_upload.json`, `docs/drive_upload_verification.json`, `scripts/organize_drive_classes.py`. `.agents/` también está sin seguimiento.

**Discrepancia importante en el notebook de clase 08.** `notebooks/clase_08_rag_supabase_groq.ipynb` fue modificado a las 16:27 (-05), después de la última versión de este informe (16:09). Su contenido actual **no** es la «práctica fiel de diez pasos» descrita arriba: tiene 27 celdas (13 de código, ids `cl08-NN`), no importa `src/class08_client.py` y orquesta los módulos del proyecto (`Retriever` híbrido, `run_rag_case`, anexos OCR y API Django) con banderas en la primera celda de código. Coincide en estructura con la versión anterior descrita por `docs/class08_notebook_validation.json` (27 celdas / 13 de código). Banderas actuales: todas `False` salvo `CONNECT_SUPABASE = True`; solo 3 celdas de código conservan salidas y la celda de conexión muestra «Conexión remota no ejecutada», es decir, las salidas no corresponden a las banderas actuales. `RUN_DIR` apunta a `docs/rag_runs/class08/` (no a `clase08/`). Consecuencias: `src/class08_client.py`, `test/test_class08_client.py`, `docs/CLASE08.md`, `README.md` y `docs/class08_practice_validation.json` describen una versión que ya no está en el notebook. No se sabe si el cambio fue intencional (probablemente del usuario); **preguntar antes de restaurar o reescribir el notebook**, y no afirmar que la práctica de diez pasos está en el notebook actual.

**Pruebas ejecutadas ahora** (`.venv`, `HF_HUB_OFFLINE=1`): `python -m unittest discover -s test` → 209 pruebas OK; `python manage.py test api` → 24 pruebas OK; `python manage.py check` → sin problemas. No se ejecutó el notebook ni ninguna integración remota.

**Pendientes actualizados** (además de los prioritarios de arriba): aclarar con el usuario cuál versión del notebook de clase 08 es la vigente y alinear documentación/validaciones con ella; los fallos de métricas de clase 08 (caso ambiguo y paráfrasis) siguen sin corregir; separar `.pyc` y artefactos de Drive antes de cualquier commit autorizado.


## Reorganización backend/frontend/infra — 20-10-2026

El usuario autorizó separar el repositorio para preparar un futuro frontend. El código Python, API Django, notebooks, corpus, manuales, prompts, scripts, pruebas, assets, documentación y requirements.txt están ahora en `backend/`. Las migraciones SQL están en `infra/supabase/migrations/`. `frontend/` contiene un README y todavía no tiene framework ni aplicación. El README de la raíz describe los comandos actuales; `.agents/` sigue en la raíz.

La configuración local existente se movió a `backend/.env`, junto a `backend/.env.example`. Los índices, caché de tiktoken y trazas existentes se movieron con sus directorios a `backend/` y siguen ignorados. Los entornos `.venv/` y `.venv-test/` permanecen en la raíz para conservar sus rutas de instalación. Desde la raíz: `source .venv/bin/activate`, `cd backend`; después se ejecutan los comandos habituales. Los notebooks reconocen también la raíz del repositorio y localizan `backend/`; el de clase 08 utiliza el entorno de la raíz. No se cambiaron sus banderas de ejecución ni sus resultados históricos.

La rama sigue siendo `codex/implement-embeddings`. El último commit anterior a esta reorganización es `83f2110`, subido a origin; el informe inicial sobre trabajo sin publicar de octubre 14 es histórico. Las modificaciones de esta reorganización quedan locales hasta una nueva petición de commit/push.

El usuario descartó expresamente la prueba de aislamiento con dos usuarios Supabase: está fuera del objetivo actual. El 20-10-2026 se verificaron autenticación, 70 fragmentos y RPC desde dos clientes del mismo usuario, sin escribir datos. No crear usuarios ni retomar la prueba descartada por iniciativa propia. No se consultó Drive durante esta reorganización.

Validación posterior al movimiento: 210 pruebas de unittest y 24 pruebas Django/API aprobadas; `manage.py check` sin problemas desde backend y desde la raíz; sintaxis de todos los notebooks y primera celda de los tres notebooks comprobadas desde la raíz, sin ejecutar consultas remotas. Todos los archivos previamente versionados se localizaron en su destino. `.env`, índices, cachés, trazas y artefactos personales de Drive siguen excluidos por Git.


## Imagen Docker del backend — 20-10-2026

El usuario pidió una imagen liviana del backend. Se añadieron `backend/Dockerfile`, `backend/.dockerignore`, `backend/requirements-runtime.txt`, `backend/docs/DOCKER.md` e `infra/compose.yaml`. La imagen local `ti-support-rag-backend:local` fue construida con Docker: ID `sha256:8a5e7b745b76b5e62dca4fd4b2e724b1701eac0993e2ba07130f2998d1fe5ea5`, tamaño 1.282.325.554 bytes (Linux amd64). No se subió a un registry.

Usa Python 3.12 slim, construcción por etapas, PyTorch CPU, Gunicorn 26.2.0 con un proceso y cuatro hilos y usuario app (UID 10001). Conserva Sentence Transformers para no cambiar el modelo ni los embeddings. No prometer una imagen diminuta: PyTorch es el principal límite de tamaño. Excluye CUDA, torchvision, EasyOCR, Jupyter, corpus, reportes, notebooks y secretos. Pillow/pytesseract permanecen por imports del pipeline; no incluye el ejecutable Tesseract ni soporta el flujo académico completo de OCR/ingestión/reportes.

Compose inyecta `backend/.env` al ejecutar, monta el índice en lectura y conserva los pesos/tokenizadores en los volúmenes `ti-support-rag-model-cache` y `ti-support-rag-tokenizer-cache`. Los pesos no están dentro de la imagen y ocupan espacio adicional. Primer uso requiere descarga del modelo. El healthcheck solo comprueba HTTP, no proveedores ni disponibilidad del modelo.

Pruebas realizadas dentro de la imagen: 24 pruebas Django/API aprobadas, imports de inferencia y pipeline correctos, PyTorch CPU y UID/exclusiones comprobados. Gunicorn probado por HTTP real: health/docs/OpenAPI 200, categories sin token 401 y con token de prueba 200; healthcheck configurado aprobado. Contenedor HTTP de prueba detenido y eliminado. Ninguna llamada a Groq ni escritura en Supabase durante estas verificaciones.

También se cargó el modelo real dentro del contenedor y se comprobó la compatibilidad de los textos/vectores del índice y una nueva consulta de 384 dimensiones, sin Supabase ni Groq. Modelo descargado y conservado en el volumen de caché para reutilizarlo con Compose. Evidencia: `backend/docs/docker_validation.json`.


## Registro del manual externo Ricoh — 20-10-2026

El usuario pidió únicamente el primer paso de incorporación: registrar el documento. El PDF original está en `backend/manuals/hardware/RICOHMP4002_MANUAL.pdf`. Se creó `backend/manuals/manifest.real.json`, con rutas relativas a `manuals/`, ID `RICOH-MP4002-USER-GUIDE-EN`, idioma `en`, 228 páginas, 5.520.145 bytes y SHA-256 `3e5a0a2702efdc320633c1409159a0d28d533c1f98239b9f9ddb6dd8b7b8c1d5`. Estado `registered_pending_ingestion`; `simulated: false`.

Procedencia: archivo aportado por el usuario, sin URL oficial confirmada. La atribución a MP 4002 procede del usuario/nombre; no se encontró ese modelo en el texto. Versión y fecha de publicación quedan null; las fechas técnicas de creación/modificación del PDF se registran aparte. README de manuales actualizado. Hash/tamaño y separación del corpus simulado validados. No se modificaron los manifiestos académicos ni la ingestión, no se generaron embeddings, no se escribieron datos en Supabase y no se reinició el contenedor. El siguiente paso sería adaptar la extracción para documentos reales, páginas vacías y tablas, cuando el usuario lo autorice.


## Verificación oficial del manual Ricoh — 20-10-2026

A petición explícita del usuario se verificaron identidad y compatibilidad, sin iniciar ingestión. La página oficial `https://support.ricoh.com/bb_v1oi/html/oi/re/model/mp42/mp42en.htm` lista la familia Aficio MP 4002/4002SP/5002/5002SP y enlaza `https://support.ricoh.com/bb_v1oi/pub_e/oi/0001043/0001043003/VD1297802_01/D1297802_en.pdf`. La descarga oficial y el PDF del usuario son idénticos byte por byte: 5.520.145 bytes y SHA-256 `3e5a0a2702efdc320633c1409159a0d28d533c1f98239b9f9ddb6dd8b7b8c1d5`.

Se actualizó `backend/manuals/manifest.real.json`: `version` = `D129-7802` (identificador editorial impreso en página PDF 228, no firmware); copyright 2011 (página PDF 227); actualización de descarga oficial 2012-01-10, sin atribuirle carácter de fecha exacta de publicación. Asociación con MP 4002 confirmada por la página oficial y la identidad del archivo; `model_verified_from_document` sigue false porque el nombre no aparece explícito en el texto, pero `model_verified_from_official_source` y `official_source_verified` son true. Esta sección sustituye las dudas de atribución y procedencia del registro anterior.

Evidencia en `backend/docs/ricoh_manual_verification.json`; README de manuales actualizado. Hash y coherencia del registro comprobados. El PDF permanece intacto y `ingestion_status` continúa `registered_pending_ingestion`. No se modificaron el importador ni Supabase ni el despliegue. La guía cubre una familia de equipos, con diferencias por región/opciones; no prometer compatibilidad universal de firmware.


## Extracción local Ricoh terminada — 20-10-2026

Implementados `backend/src/rag/external_ingestion.py` y `backend/scripts/extract_real_manual.py`, con 11 pruebas nuevas en `backend/test/test_external_ingestion.py`. Se añadió `pdfplumber==0.11.9` únicamente a requirements completo; requirements-runtime e imagen Docker no cambian. El perfil `extraction_profile` del manifiesto real está ligado a los bytes verificados: contenido PDF 8–220, exclusiones explícitas de portada/índices/notas/créditos y coordenadas para encabezados, pie y pestañas laterales. Una corrección geométrica explícita de la tabla de la página PDF 75 evita que las líneas de las ilustraciones rompan las columnas. La página PDF 2 vacía se valida antes de omitirla; una página inesperada sin texto detiene el extractor.

Resultado reproducible local: 213 páginas de contenido, 146 secciones (de 149 marcadores totales), 1.647 párrafos, 92 tablas con 383 filas. Cada bloque tiene ID, coordenadas, página PDF y número impreso. Las filas permanecen completas con celdas originales; `ancestor_section_ids` enlaza las advertencias/condiciones del padre con el subprocedimiento. Los párrafos NO son todavía fragmentos con presupuesto de tokens. Hay 62 candidatos a continuación entre tablas de páginas consecutivas, no fusiones automáticas de filas.

Se revisaron visualmente 11 páginas: 65, 66, 75, 76, 78, 95, 97, 146, 185, 186 y 187. Seis tablas dependen de ilustraciones (páginas 65, 66, 75, 76, 78, 146): conservan su cuadrícula, pero llevan `text_index_eligible: false` y motivos de revisión. No inventar descripciones de los gráficos ni indexar esos bloques como texto completo. La revisión fue del agente, no humana. No se interpretaron semánticamente todas las ilustraciones del manual.

Salidas locales ignoradas: `backend/data/extracted/RICOH-MP4002-USER-GUIDE-EN/extraction.json`, `review.md`, `summary.json`, `previews/`. Resumen de validación apto para versionar: `backend/docs/ricoh_extraction_validation.json`. Guía: `backend/docs/RICOH_EXTRACTION.md`. Estado del registro: `locally_extracted_pending_fragmentation`; `local_extraction` contiene rutas, conteos y hash del resultado. El extractor excluye estos punteros de ciclo de vida de su snapshot para no crear hashes autorreferentes al repetir.

Comando desde backend y con entorno activo: `python -m scripts.extract_real_manual`. Usa pdfplumber/pypdf locales, sin Groq, Supabase ni modelo de embeddings. Comprobaciones: hash del PDF intacto; las 228 páginas contabilizadas; numeración impresa = PDF−2 en las 213 páginas; once pasos/condiciones de Quick Install conservados; advertencia de Standard Printing enlazada al subprocedimiento PCL6; separación correcta de fax/impresión en página 185; sin caracteres de sustitución ni `(cid:...)`; corpus activo sigue con 70 fragmentos. Pasaron 221 pruebas unittest, 24 Django/API, `manage.py check`, `pip check` y diff whitespace.

Incidencia local detectada al verificar Django: `backend/api/controllers.py` tenía `from uuid import uuid4|` (errata preexistente en el árbol local). Se retiró solo el carácter `|`; la API pasó después. No se reconstruyó ni reinició el contenedor. No se cambió el PDF ni los manifiestos académicos, no se generaron embeddings ni se escribieron filas Supabase. El historial anterior que diga que no existe extractor real o que el estado es registered_pending_ingestion está superado por esta sección y el resumen actual.


## Fragmentación y recuperación local Ricoh — 20-10-2026

A petición del usuario se implementaron `backend/src/rag/external_chunking.py`, `external_retrieval.py`, `backend/scripts/evaluate_ricoh_local.py` y siete pruebas nuevas en `backend/test/test_external_chunking.py`. Casos fijos: `backend/cases/ricoh_retrieval_es.json`. No se cambió `Chunk`, el formato académico ni el Retriever desplegado, para no invalidar el índice actual de 70 fragmentos.

Índice independiente `backend/data/indexes/ricoh-local-v1/`, ID `ricoh-local-85995a0e67f7d4017a02`: 498 unidades completas (134 secciones textuales + 364 filas de tablas) y 779 vistas de búsqueda, máximo 128 tokens, embeddings reales normalizados de 384 dimensiones con el modelo/revisión activos. Todos los 1647 párrafos se conservan. Las seis tablas gráficas siguen excluidas de texto. Cada unidad conserva cuerpo completo, contexto de antecesores, páginas/versión/hash y fila original. Las vistas tienen offsets contiguos al cuerpo; se valida cobertura, IDs, hashes y muestras recomputadas de vectores. Las unidades largas (115 cuerpos >128 tokens) no se cortan como evidencia final: solo se dividen sus vistas para embeddings. La hidratación recupera toda la unidad y sus advertencias. No es un formato intercambiable directamente con records.json/config.json del índice académico.

Resultados en 12 preguntas diagnósticas en español (7 de procedimientos, 5 con mensajes de pantalla ingleses), sin generación: semantic Top-1 7/12, Top-3 10/12; hybrid Top-1 8/12, Top-3 10/12; hybrid_literal Top-1 10/12, Top-3 11/12, MRR@3 0.8611. El híbrido combina coseno/BM25/RRF y deduplica por unidad. hybrid_literal prioriza coincidencia genérica del mensaje completo entre comillas con la celda Message original; no contiene reglas por ID de caso. La comparación normaliza whitespace de PDF; el mensaje Hardware Problem: Ethernet estaba partido por un salto de línea, no era un error de recuperación. Mantener expectativas, no confundir 11/12 con cumplimiento total ni con una evaluación ciega.

Fallo pendiente real: RIC-06 pregunta por enviar impresión retenida (Sending a Hold Print File), pero recupera documentos almacenados. No se inventaron equivalencias bilingües ni se cambió el esperado a Stored Print. La sonda de la pregunta amplia de impresiones se registra aparte, sin contar como acierto de diagnóstico: faltan síntomas para establecer una causa. Las puntuaciones no son confianza de diagnóstico. La evidencia completa puede superar 128 tokens y al combinar resultados el presupuesto de 1000 tokens de generación: integrar selección contextual antes de activar en el generador.

Reporte: `backend/docs/ricoh_local_retrieval_validation.json`; guía/métricas legibles: `backend/docs/RICOH_LOCAL_RETRIEVAL.md`. Registro/README de manuales actualizados a `locally_indexed_retrieval_partial`; campos `local_fragmentation` y `local_retrieval_validation` guardan cantidades y fallo. Los snapshots del extractor excluyen campos local_* y estado de ciclo de vida para conservar su reproducibilidad. Estos cambios no requieren reextraer el PDF: su JSON revisado conserva hash ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44.

Se reutilizó la caché pública hub del contenedor copiándola a `/tmp/ti-rag-hf/hub`, sin secretos. Comandos desde backend con entorno activo: `HF_HOME=/tmp/ti-rag-hf HF_HUB_OFFLINE=1 OMP_NUM_THREADS=2 python -m scripts.evaluate_ricoh_local` para construir/evaluar; añadir `--existing` para reutilizar vectores. La caché temporal puede desaparecer: usar la revisión fijada y descargar legítimamente si falta. No se hicieron llamadas a Groq/Supabase. Los avisos de tokenizador sobre cuerpos completos largos ocurren al contar tokens; solo las vistas validadas <=128 entran al modelo de embeddings.

Pruebas: 228 unittest aprobadas (incluyen 7 nuevas de fragmentación/hidratación/literales), 24 Django/API aprobadas, `manage.py check` correcto. La evaluación verifica hash del PDF/extracción registrada, hashes de la construcción y que los tres archivos del índice activo no cambien. No se reconstruyó ni reinició Docker; no se cargó Supabase. Todo sigue local sin commit desde la reorganización posterior a 83f2110.

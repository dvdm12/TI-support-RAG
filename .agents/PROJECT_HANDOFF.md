# Informe de continuidad — TI-support-RAG

Fecha: 14 de octubre de 2026 (America/Bogota).
Ubicación: `/home/dvdm12/Documents/Obsidian Vault/TI-support-RAG`.
Este informe describe el estado observado al cierre de la integración Django y Swagger, con actualizaciones posteriores al final (la más reciente: «Revisión local del estado — 14-10-2026, tarde»). Las secciones finales prevalecen sobre las anteriores cuando difieren. No contiene secretos.

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

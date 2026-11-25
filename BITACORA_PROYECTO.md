---
tipo: bitacora-proyecto
curso: Electiva VI — EAM-2026II
profesor: Robert Garcia Rey
proyecto: Mesa de Ayuda TI Inteligente (TI-support-RAG)
integrantes:
  - David Mantilla Aviles
  - Juan Camilo Velez
fecha_actualizacion: 2026-11-25
estado: corte-3-implementado-despliegue-pendiente
---

# Bitácora del Proyecto — Mesa de Ayuda TI Inteligente

**Curso:** Electiva VI · EAM-2026II  
**Profesor:** Robert Garcia Rey  
**Repositorio:** `TI-support-RAG`  
**Rama activa (entrega final):** `feat/clase-12-entrega-final`

---

## Resumen ejecutivo

| Corte | Foco principal | Estado |
|---|---|---|
| 1 | Clasificación estructurada + OCR multimodal | Cerrado y documentado |
| 2 | RAG híbrido (semántico + BM25) + Supabase vectorial | Cerrado y documentado |
| 3 | Auth Supabase · historial persistente · MCP · interfaz Gradio | Implementado; despliegue en Render pendiente |

Principio de diseño sostenido en los tres cortes:

> **El modelo propone; el programa valida; el sistema decide.**

---

## Corte 1 — Clasificación estructurada y multimodalidad

> Bitácora detallada: [`backend/docs/parcial1/bitacora_parcial.md`](backend/docs/parcial1/bitacora_parcial.md)

### Qué se implementó

- Recepción de solicitudes de texto e imagen.
- Clasificación estructurada con Groq (`openai/gpt-oss-20b`, `temperature=0`).
- Contrato `SolicitudTI` validado con Pydantic.
- Estados de decisión: `OK_VALIDADO`, `OK_PIDE_ACLARACION`, `OK_REQUIERE_HUMANO`.
- Prompt versionado de `system_v0` a `system_v4`.
- OCR con patrón Strategy + Factory (EasyOCR, Tesseract, PaddleOCR).
- Trazabilidad de `raw_output` → salida validada → PDF consolidado.

### Resultado principal

| Indicador | system_v3 | system_v4 |
|---|---:|---:|
| Criterios cumplidos | 26 / 27 | 27 / 27 |
| Cobertura interna | 96.30 % | 100.00 % |

La diferencia entre versiones: `system_v4` añadió una regla para que `datos_faltantes` no quede vacío ante solicitudes insuficientes (`case_03`).

### Hallazgos y correcciones

| Hallazgo | Corrección |
|---|---|
| `NameError: tempfile` no importado | `import tempfile` añadido |
| Imagen multimodal no persistía entre celdas | Ruta fija `docs/multimodal/multimodal_demo.png` |
| PDF generado antes del caso OCR | Reordenadas celdas de exportación |
| `case_03` → `datos_faltantes` vacío | Regla explícita en `system_v4` |

---

## Corte 2 — RAG híbrido y recuperación documental

> Bitácora detallada: [`backend/docs/parcial2/bitacora_corte2.md`](backend/docs/parcial2/bitacora_corte2.md)

### Qué se implementó

- Pipeline RAG completo: clasificación → recuperación → contexto → generación → validación.
- Corpus: 7 PDF, 14 páginas, 35 secciones, 70 fragmentos.
- Embeddings: `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones).
- Recuperación híbrida: semántica (Supabase `pgvector`) + léxica (BM25) + fusión RRF (pesos 1/2).
- Tabla `clase08_fragmentos` y función `clase08_buscar_fragmentos` en Supabase.
- Prompt generador `rag_v6`; clasificador `system_v8`.
- Validación de estructura, citas y respaldo en la respuesta generada.
- API Django (`/api/v1/rag/query/`) exponiendo el pipeline completo.
- Interfaz Gradio básica (`interfaces/gradio/app.py`) sobre la API.

### Resultados de recuperación (desarrollo)

| Medida | Híbrida anterior | Híbrida mejorada |
|---|---:|---:|
| Precision@3 | 52.38 % | 66.67 % |
| Recall@3 | 80.95 % | 100.00 % |
| Hit@3 | 85.71 % | 100.00 % |
| MRR@3 | 0.8571 | 1.0000 |
| Cobertura macro Top-3 | 80.36 % | 100.00 % |

### Hallazgos y correcciones

| Hallazgo | Corrección |
|---|---|
| Resumen del clasificador > 240 caracteres en `E06` | `system_v8` limita longitud del resumen |
| Pérdida de términos técnicos en la búsqueda léxica | Normalización y filtrado antes del corte Top-3 |
| Presupuesto de contexto dejaba fuera fragmentos relevantes | Compactación de `rag_v6`; comparación cobertura Top-3 vs contexto final |

---

## Corte 3 — Autenticación, historial y app final

### Objetivos del corte

1. Persistir el historial de conversaciones por usuario en Supabase.
2. Autenticar usuarios con Supabase Auth (email + contraseña).
3. Integrar MCP para la consulta de tickets.
4. Construir la interfaz Gradio final (`app/`) con login, selector de conversaciones y chat.

### Arquitectura del corte 3

```text
app/app.py          ← UI Gradio (login, conversaciones, chat, sources)
    │
    ├── almacenamiento.py  ← Supabase: conversaciones + mensajes + Auth
    │       └── Supabase (RLS, JWT por sesión)
    │
    └── sistema.py         ← Enrutador + coordinador
            ├── consulta_ticket    → servidor_mcp.py (FastMCP stdio)
            │                           └── backend/api/tickets_demo.json
            ├── consulta_documental → backend API /api/v1/rag/query/
            ├── respuesta_directa  → respuesta local
            ├── aclaracion         → respuesta local
            └── operacion_prohibida → rechazo local
```

### Componentes implementados

#### `infra/supabase/migrations/20261124_chat_history.sql`

Tablas `conversaciones` y `mensajes` con RLS estricta:

- `conversaciones`: cada fila pertenece a `auth.uid()`; políticas select/insert/update/delete por usuario.
- `mensajes`: accesibles solo si su conversación pertenece al usuario autenticado (subconsulta RLS).
- Trigger `trg_refrescar_conv` → actualiza `actualizada_en` en cada mensaje insertado.
- Aplicada vía Supabase Management API (curl al endpoint `/v1/projects/{ref}/database/query`).

```sql
-- Patrón clave que resuelve la violación RLS en INSERT
usuario_id uuid not null default auth.uid()
```

#### `app/almacenamiento.py`

- Sin cliente global: cada sesión de Gradio crea su propio `Client` con `ClientOptions(persist_session=False)`.
- Funciones: `construir_cliente`, `autenticar`, `cerrar_sesion`, `crear_conversacion`, `listar_conversaciones`, `renombrar_conversacion`, `eliminar_conversacion`, `cargar_mensajes`, `guardar_turno`, `historial_como_pares`.
- **58 pruebas unitarias** (`test_almacenamiento.py`) con `unittest` + `MagicMock`; tiempo de ejecución: 0.09 s; sin conexión real a Supabase.

#### `app/servidor_mcp.py`

- Servidor FastMCP con transporte stdio.
- Herramienta `consultar_estado_ticket(codigo_ticket)` → lee `backend/api/tickets_demo.json`.
- Valida formato TI-NNNN antes de buscar.
- Devuelve `{encontrada, estado, detalle, fuente}`.
- Arranca como subproceso desde `sistema.py` al resolver una ruta `consulta_ticket`.

#### `app/sistema.py`

Enrutador y coordinador. Función principal: `async procesar(pregunta, historial, api_url, api_token) → Resultado`.

| Ruta | Condición de activación | Acción |
|---|---|---|
| `operacion_prohibida` | Verbos de mutación + mención de ticket | Rechazo local |
| `respuesta_directa` | Saludo, fuera de alcance | Respuesta local |
| `aclaracion` | Ticket sin código único, intención mixta | Pregunta local |
| `consulta_ticket` | Código TI-NNNN con intención de estado | MCP stdio |
| `consulta_documental` | Todo lo demás | API backend |

- El enrutador normaliza Unicode y elimina tildes antes de aplicar las expresiones regulares.
- La conexión MCP se abre y cierra en cada llamada (sin estado global).
- El campo `traza` del `Resultado` incluye ruta, herramienta MCP y resultado del servidor.

#### `app/app.py`

Interfaz Gradio 6 con:

- Panel de login → `autenticar()` → visibilidad condicional con `gr.update(visible=...)`.
- Dropdown de conversaciones con tuplas `(titulo, id)`; al seleccionar carga mensajes desde Supabase.
- Al login crea automáticamente una conversación si no existe ninguna.
- Handler async `_enviar_pregunta` → `sistema.procesar()` → `guardar_turno()` → actualiza chatbot.
- Chatbot usa formato Messages de Gradio 6 (`[{"role": "user"/"assistant", "content": "..."}]`); el estado interno `s_hist` mantiene el formato de tuplas para `almacenamiento.py` y `sistema.py`.
- Acordeones colapsables para fuentes documentales y traza de enrutamiento.
- Renombrar y eliminar conversaciones.
- Cerrar sesión limpia el estado y vuelve al panel de login.

### Variables de entorno requeridas (`app/.env`)

| Variable | Propósito |
|---|---|
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_PUBLISHABLE_KEY` | Clave publishable (`sb_publishable_...`) o anon heredada (`eyJ...`); nunca `service_role` |
| `BACKEND_URL` | URL base del backend Django (ej. `http://127.0.0.1:8000`) |
| `BACKEND_API_TOKEN` | Bearer token del backend |
| `GRADIO_SERVER_NAME` | Interfaz de red (opcional, por defecto `0.0.0.0`) |
| `GRADIO_SERVER_PORT` | Puerto (opcional, por defecto `7860`) |

### Hallazgos y correcciones del corte 3

| Hallazgo | Corrección |
|---|---|
| `INSERT` en `conversaciones` violaba RLS | Faltaba `DEFAULT auth.uid()` en columna `usuario_id`; añadido con `ALTER TABLE` y en la migración |
| `gr.Chatbot` no acepta `type="tuples"` en Gradio 6.32 | Parámetro eliminado |
| `gr.Chatbot` no acepta `show_copy_button` en Gradio 6.32 | Parámetro eliminado |
| Gradio 6 espera formato Messages, no tuplas | Función `_a_mensajes()` convierte el historial interno antes de enviarlo al chatbot |
| Variables de entorno no se expandían en heredoc `<< 'EOF'` | Script movido a archivo temporal con `os.environ` |
| DNS `download.pytorch.org` no resolvía en Docker build | Se usaron imágenes ya construidas; no se reconstruyeron |
| `SUPABASE_API_TOKEN` inválido al aplicar migración | Token regenerado en `supabase.com/dashboard/account/tokens` |
| `.env.ejemplo` quedaba bloqueado por `.gitignore` | Renombrado a `app/.env.example` (excepción ya prevista en `.gitignore`) |
| `mcp` 2.x renombró `mcp.server.fastmcp`; `servidor_mcp.py` fallaba al importar (el rango `<3` instalaba 2.3.0) | Dependencia fijada a `mcp>=1.0,<2`; verificado con 1.30.0 |
| «mi ticket no avanza» iba al RAG y terminaba en HTTP 502 (`ERROR_FORMATO`) | El enrutador reconoce quejas de avance como consulta de estado: sin código pide aclaración, con código consulta MCP |
| Tras suspender el equipo, el host no alcanzaba el puerto 8000 aunque el contenedor estaba *healthy* | NetworkManager retiró la IP de los bridges de Docker; se resolvió reiniciando Docker |
| RAG respondía 503 `RepositoryError` | La contraseña del usuario de Supabase en `backend/.env` estaba desactualizada; se corrigió y se recreó el contenedor |

### Decisiones técnicas del corte 3

| Decisión | Justificación |
|---|---|
| Sin cliente Supabase global | Gradio puede servir múltiples usuarios concurrentes; un cliente global compartiría el JWT |
| `persist_session=False` en `ClientOptions` | Evita que supabase-py intente persistir la sesión en disco |
| MCP vía stdio (subprocess) | Reutiliza el mismo patrón del notebook de clase 11; no requiere servidor HTTP separado |
| Enrutador local en `sistema.py` | Permite mostrar la ruta tomada en la traza sin depender del backend para la decisión |
| Formato Messages en el chatbot | Requerimiento de Gradio 6.32; el estado interno conserva tuplas para compatibilidad con `almacenamiento.py` |
| Historial de los últimos 3 turnos para RAG | Limita el tamaño del contexto enviado al backend sin perder continuidad |
| `mcp>=1.0,<2` | El servidor usa la API FastMCP de la versión 1; la 2.x la renombró |

### Estado al cierre del corte 3

#### Completado

- [x] Migración SQL `conversaciones` + `mensajes` + RLS aplicada en Supabase
- [x] `app/almacenamiento.py` con 58 pruebas unitarias (100 % pasan)
- [x] `app/servidor_mcp.py` — servidor FastMCP de tickets
- [x] `app/sistema.py` — enrutador + MCP + RAG; `test_sistema.py` con 16 casos de ruta (100 % pasan)
- [x] `app/app.py` — interfaz Gradio completa con auth y conversaciones
- [x] `app/requirements.txt` y `app/.env.example`
- [x] Credencial de Supabase Auth configurada para pruebas
- [x] `BITACORA_PROYECTO.md` unificada en la raíz (este archivo)
- [x] `README.md` actualizado con `app/` y tablas Supabase
- [x] `app/presentacion_proyecto.pdf` copiada desde `backend/docs/parcial2/presentacion/`
- [x] Verificación local (25-11-2026): rutas directa, fuera de alcance, prohibida, MCP (TI-1001, TI-1003, TI-9999) y RAG con fuentes

#### Pendiente

- [ ] Despliegue en Render con variables de entorno configuradas (y su sección en `README.md`)
- [ ] Merge de `feat/clase-12-entrega-final` en `main`

---

## Arquitectura global del proyecto

```text
TI-support-RAG/
├── backend/                   # Django — API REST
│   ├── api/
│   │   ├── attention.py       # Enrutador de solicitudes
│   │   ├── services.py        # Orquestador RAG (run_query, attend)
│   │   └── tickets.py         # Catálogo de tickets de demostración
│   └── src/
│       ├── pipeline.py        # Flujo: prepare → execute → run_case
│       ├── decision.py        # Estados: OK_VALIDADO / PIDE_ACLARACION / REQUIERE_HUMANO
│       └── rag/
│           └── repository.py  # SupabaseRepository (vectores + búsqueda híbrida)
│
├── app/                       # Gradio — Interfaz final (Clase 12)
│   ├── app.py                 # UI: login, conversaciones, chat
│   ├── almacenamiento.py      # Supabase: historial de conversaciones
│   ├── sistema.py             # Enrutador + MCP + RAG
│   ├── servidor_mcp.py        # FastMCP stdio: consultar_estado_ticket
│   ├── test_almacenamiento.py # 58 pruebas unitarias
│   ├── test_sistema.py        # Pruebas del enrutador
│   ├── presentacion_proyecto.pdf
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                  # React — Chat institucional
├── infra/
│   ├── compose.yaml           # Docker Compose (backend + frontend)
│   └── supabase/migrations/
│       ├── 20261014_documentary_rag.sql   # clase08_fragmentos
│       └── 20261124_chat_history.sql      # conversaciones + mensajes (Clase 12)
│
└── BITACORA_PROYECTO.md       # Este archivo
```

## Supabase — esquema de tablas

| Tabla | Propósito | Corte |
|---|---|---|
| `clase08_fragmentos` | Corpus documental vectorizado (RAG) | 2 |
| `conversaciones` | Una fila por conversación de usuario | 3 |
| `mensajes` | Un fila por turno (usuario o asistente) | 3 |

Todas las tablas tienen RLS activada. Las tablas del corte 3 usan `auth.uid()` como eje de acceso.

---

## Instrucciones de reproducción

### Backend (Django + RAG)

```bash
cd backend
cp .env.example .env   # completar variables
docker compose -f ../infra/compose.yaml up --build
# API disponible en http://127.0.0.1:8000
```

### App Gradio (Clase 12)

```bash
cd app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar variables
python app.py
# UI disponible en http://127.0.0.1:7860
```

### Pruebas unitarias (almacenamiento y enrutador)

```bash
cd app
python3 -m unittest test_almacenamiento test_sistema -v   # 59 pruebas, < 0.1 s
```

---

*Última actualización: 2026-11-25 — Corte 3 implementado y verificado en local; despliegue en Render pendiente.*

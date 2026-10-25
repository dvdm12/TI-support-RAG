# API Django de TI-support-RAG

Django 5.2, proyecto `ti_api`, aplicación `api`. Los controllers están en
`api/controllers.py` y el adaptador del RAG en `api/services.py`. El servicio
reutiliza el corpus existente, Supabase, Groq y la política de 1000 tokens por
llamada. No requiere una base de datos Django ni migraciones: el corpus permanece
en Supabase. No se cargan modelos ni se llama a servicios al arrancar o consultar
el endpoint de estado.

## Swagger y OpenAPI

Abre [Swagger UI](http://127.0.0.1:8000/api/v1/docs/) con el servidor activo.
El esquema está en `/api/v1/openapi.json` (OpenAPI 3.1). Ambos son públicos.
La interfaz documenta los cuatro endpoints con recorrido recomendado, autenticación
paso a paso, propósito, límites y descripción de campos. Cada operación ofrece
ejemplos de entrada, éxito y errores con acciones sugeridas. La consulta incluye
ejemplos de respuesta documentada, aclaración y evidencia insuficiente; todos
son ilustrativos y no constituyen mediciones ni respuestas garantizadas.
El explorador permite filtrar operaciones, enlazarlas y ver el tiempo HTTP de
una petición, distinto de los tiempos internos publicados por el pipeline.

Para probar rutas protegidas, pulsa **Authorize**, introduce el valor de
`DJANGO_API_TOKEN` de tu `.env` (sin el prefijo `Bearer`) y confirma. Después
abre una operación, pulsa **Try it out** y **Execute**. `/health/` no requiere
token. `/rag/query/` realiza llamadas reales a Groq y consume su cuota.
Los resultados de aclaración o evidencia insuficiente son respuestas HTTP 200.

Swagger usa archivos locales de `drf-spectacular-sidecar`, incluso con
`DEBUG=False`; no envía el esquema a un validador externo ni persiste el token
tras recargar la página. Las credenciales nunca se incluyen automáticamente.
El esquema se define en `api/documentation.py`, reutilizando los contratos
Pydantic de entrada y clasificación. Actualízalo junto con cualquier cambio de
contrato. Los assets se sirven con una lista explícita de archivos permitidos.

## Inicio local

Desde la raíz del repositorio:

```bash
source .venv/bin/activate
cd backend
python -m pip install -r requirements.txt
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

Se prepararon `DJANGO_SECRET_KEY` y `DJANGO_API_TOKEN` en `.env` con valores
aleatorios distintos, sin publicarlos. `.env.example` documenta los nombres.
Para otro entorno, configura valores nuevos y `DJANGO_ALLOWED_HOSTS` (lista
separada por comas). `DJANGO_DEBUG` es false por defecto. Reinicia el proceso
tras cambiar estas variables. En Docker Compose, recrea el contenedor con
`docker compose -f infra/compose.yaml up -d --force-recreate backend` desde
la raíz; reiniciar el mismo contenedor no recarga el archivo de entorno. El servidor de desarrollo se usa localmente;
para un despliegue emplea el entrypoint WSGI/ASGI y configura sus tiempos de
espera según las llamadas RAG, que pueden esperar por cuota del proveedor.

## Endpoints

| Método | Ruta | Autenticación | Operación |
|---|---|---|---|
| GET | `/api/v1/health/` | Pública | Estado del proceso, sin comprobar dependencias remotas |
| GET | `/api/v1/categories/` | Bearer | Siete categorías de soporte |
| POST | `/api/v1/rag/search/` | Bearer | Recuperar pasajes en Supabase, sin llamar a Groq |
| POST | `/api/v1/rag/query/` | Bearer | Clasificación, recuperación, respuesta y validaciones del RAG |

Las rutas llevan barra final. No hay redirecciones automáticas de un POST sin
barra. Se requiere `Content-Type: application/json` para los POST.

Consulta RAG:

```json
{"pregunta": "No puedo conectarme al Wi-Fi. ¿Qué comprobaciones indica el manual?"}
```

Búsqueda, con categoría opcional como preferencia de ranking:

```json
{"pregunta": "Mensaje sospechoso con un enlace", "categoria": "seguridad"}
```

No se aceptan campos para cambiar usuario, índice, proveedor o modo mock.
Esta primera versión recibe texto; el OCR del pipeline sigue disponible por
CLI, pero todavía no hay un endpoint de carga de imágenes.

## Cliente de ejemplo

Este ejemplo lee el token localmente y nunca lo imprime ni lo incluye en la URL:

```python
from dotenv import dotenv_values
import requests

config = dotenv_values('.env')
headers = {'Authorization': f"Bearer {config['DJANGO_API_TOKEN']}"}
response = requests.post(
    'http://127.0.0.1:8000/api/v1/rag/search/',
    headers=headers,
    json={'pregunta': 'No puedo conectar el Wi-Fi', 'categoria': 'redes'},
    timeout=120,
)
print(response.status_code)
print(response.json())
```

La respuesta de consulta incluye `request_id`, `estado`, `clasificacion`,
`respuesta_documental`, `fuentes` citadas y `latencia_segundos`. No incluye
salidas crudas rechazadas, errores internos, encabezados del proveedor o
credenciales. Una aclaración o falta de evidencia documental es un resultado
HTTP 200: el estado y la limitación describen qué puede responderse.
La búsqueda devuelve el `corpus_id`, texto, procedencia y similitud de los
pasajes; esa similitud es ranking, no confianza en la respuesta.

## Errores y límites

| HTTP | Código | Significado |
|---|---|---|
| 400 | `invalid_input` | JSON, tipo, campo adicional o categoría inválidos |
| 401 | `unauthorized` | Token ausente o incorrecto |
| 404 | `not_found` | Ruta desconocida |
| 405 | `method_not_allowed` | Método incompatible |
| 413 | `body_too_large` | Cuerpo mayor de 16 KiB |
| 415 | `unsupported_media_type` | Content-Type incorrecto |
| 422 | `input_too_large` | Presupuesto de entrada o capacidad del embedder excedidos |
| 429 | `provider_rate_limited` | Cuota de Groq; Retry-After cuando se conoce |
| 502 | `invalid_provider_response` | Contrato/citas inválidos o respuesta incompleta |
| 503 | `api_not_configured`, `service_busy`, `service_unavailable` | Configuración, concurrencia o fallo de servicio |

Errores del controller tienen forma:

```json
{"request_id": "UUID", "error": {"code": "invalid_input", "message": "JSON inválido o campos incorrectos."}}
```

La validación no recorta preguntas o pasajes silenciosamente. Los 1000 tokens
son del total de entrada al generador, no 1000 tokens disponibles para la
pregunta sola. La capacidad adicional del embedder es 128 tokens de su propio
tokenizer: una pregunta demasiado larga debe resumirse.

Se permite una operación RAG/búsqueda en curso por proceso; las demás reciben
503 con Retry-After. Es una API síncrona, sin cola de trabajos persistente. La
espera de quota de Groq se comparte dentro del proceso, pero varios workers o
programas pueden consumir la misma cuota de la organización.

## Autenticación y alcance

El Bearer de esta API es `DJANGO_API_TOKEN`, **no** una clave administrativa ni
el JWT de Supabase. No acepta autenticación por cookies/sesiones. Solo los POST
con Bearer explícito están exentos de CSRF; el middleware permanece instalado.
No se habilita CORS abierto. Para uso remoto configura HTTPS y hosts autorizados.

Esta versión consulta como el usuario Supabase de práctica definido en `.env`.
Todos los clientes con el token de API acceden a ese mismo corpus del servidor;
no implementa identidades ni aislamiento individual entre consumidores de la
API. La RLS de Supabase y la ausencia de grants anónimos permanecen vigentes.

## Comprobación

```bash
source ../.venv/bin/activate
python manage.py test api
python -m unittest discover -s test
```

Las 24 pruebas de API comprueban Swagger, sus assets locales, OpenAPI y, con
servicios simulados, auth, contratos,
CSRF/Bearer, límites, errores, fuentes y concurrencia sin gastar cuota Groq.
Las 201 pruebas existentes siguen siendo independientes. Las comprobaciones
HTTP reales se registran en `docs/api/api_validation.json`; una búsqueda real no
equivale a haber ejecutado generación Groq a través del endpoint.

Referencias: [controllers/View](https://docs.djangoproject.com/en/5.2/ref/class-based-views/base/),
[JsonResponse](https://docs.djangoproject.com/en/5.2/ref/request-response/),
[configuración](https://docs.djangoproject.com/en/5.2/ref/settings/).

## Tiempos por etapa

`rag/query` y `rag/search` incluyen `tiempos_segundos`, un objeto de duraciones
en segundos. La consulta separa clasificación, embedding, búsqueda semántica,
lectura léxica, BM25, RRF, puntuación adicional, contexto, generación, validación,
revisión y total; solo se publican etapas ejecutadas. `retrieval_seconds` es un
subtotal y `total_seconds` lo contiene: no sumarlos otra vez con sus subetapas.
El tiempo HTTP puede ser mayor por inicialización/autenticación previa al pipeline.
Ver [definiciones y exportación CSV](../evaluacion/tiempos/STAGE_TIMINGS.md).

## Actualización de Swagger: documentación descriptiva

Se ampliaron las explicaciones sin cambiar rutas, campos aceptados ni
autenticación. Un 401 usa el token local de API, no el de Supabase; Swagger
añade Bearer automáticamente y olvida la autorización al recargar. Se documentan
los cuatro estados documentales HTTP 200, prioridad/confianza del clasificador,
fuentes y etiquetas, preferencias de categoría, límites y errores por código.
Los tiempos muestran cada etapa opcional y advierten sobre subtotales contenidos.

Las 26 pruebas API pasan, incluida validación de todos los ejemplos de entrada,
éxito y error contra los modelos Pydantic y coherencia de etiquetas de cita.
Las pruebas no llaman a proveedores ni ejecutan el conjunto de reserva.

## Mejora de recuperación desplegada

La versión `technical_tokens_applicable_weighted_rrf_v2` conserva términos
Wi-Fi y códigos con guiones, usa RRF con pesos semántica 1 / léxico 2 y aplica
el filtro de enlaces no abiertos antes de cortar Top-3. El pipeline conserva
sus comprobaciones posteriores. El prompt documental vigente es `rag_v6`.
Rutas, contratos, tokens y límites no cambian. Tres búsquedas HTTP reales
E03/E04/E05 devolvieron 200 y evidencia completa según la anotación de desarrollo;
ver `COVERAGE_IMPROVEMENTS.md`. No se ejecutó generación con el nuevo prompt.

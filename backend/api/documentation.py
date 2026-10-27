"""OpenAPI for the native Django controllers; Swagger assets stay local."""
from pathlib import Path

import drf_spectacular_sidecar
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_safe
from pydantic import BaseModel, Field

from schemas.request_v1 import Categoria, SolicitudTI
from schemas.rag_response_v1 import RespuestaRAG
from .contracts import QueryRequest, SearchRequest, OCRResponse


AUTH_HELP = """### Autenticación paso a paso
1. Abre **Authorize** y pega únicamente el valor de `DJANGO_API_TOKEN` de `backend/.env`.
2. **No escribas `Bearer`, comillas ni espacios adicionales**: Swagger agrega el prefijo.
3. Pulsa **Authorize**, cierra el diálogo y ejecuta la operación.

El token de esta API es distinto del JWT, las claves y el access token de Supabase.
En clientes HTTP el encabezado es `Authorization: Bearer <DJANGO_API_TOKEN>`.
Si recibes **401**, comprueba el valor y evita `Bearer Bearer ...`. Al recargar esta
página debes autorizar nuevamente. Si cambias `backend/.env`, recrea el contenedor
para que reciba el nuevo entorno; reiniciar el mismo contenedor no actualiza sus variables.
Nunca pegues un token real en el cuerpo, la URL o un reporte de error.
"""

TIMING_HELP = ("Duraciones observadas en segundos, con reloj monotónico. Solo aparecen etapas "
               "ejecutadas; una etapa ausente no equivale a cero. retrieval_seconds contiene "
               "sus subetapas y total_seconds contiene el pipeline: no sumar subtotales con "
               "sus componentes. Excluyen inicialización y autenticación anteriores al pipeline; "
               "no representan la latencia HTTP completa.")

TIMING_STAGES = {
    "ocr_seconds": "Preparación de la entrada RAG. La extracción de imágenes se ejecuta por separado en ocr/extract.",
    "classification_seconds": "Clasificación, validación y reintentos del clasificador.",
    "embedding_seconds": "Vectorización de la pregunta.",
    "semantic_search_seconds": "Consulta semántica a Supabase y conversión de candidatos; incluye comunicación.",
    "lexical_fetch_seconds": "Lectura paginada del corpus autorizado compatible para búsqueda léxica.",
    "bm25_seconds": "Tokenización, cálculo BM25 y ordenación léxica.",
    "rrf_seconds": "Fusión por posiciones, preferencia de categoría y selección Top-k.",
    "candidate_scoring_seconds": "Preparación y puntajes adicionales de candidatos léxicos seleccionados.",
    "retrieval_seconds": "Subtotal desde búsqueda semántica hasta selección final; excluye embedding de pregunta.",
    "context_seconds": "Construcción del contexto y comprobación del presupuesto.",
    "generation_seconds": "Generación inicial o construcción de aclaración local, incluyendo esperas aplicables.",
    "generation_correction_seconds": "Generación correctiva, únicamente si se ejecutó.",
    "validation_seconds": "Validaciones documentales acumuladas.",
    "support_review_seconds": "Revisiones acumuladas del respaldo documental.",
    "total_seconds": "Duración total del pipeline, incluyendo coordinación; contiene las etapas anteriores.",
}

EXAMPLE_REQUEST_ID = "00000000-0000-4000-8000-000000000001"


class Source(BaseModel):
    document_id: str | None
    title: str | None
    category: str | None
    section: str | None
    source: str | None
    version: str | None
    pages: list[int] | None


class CitedSource(Source):
    id: str
    chunk_id: str


class Passage(BaseModel):
    chunk_id: str = Field(description="Identificador estable del fragmento en el corpus.")
    texto: str = Field(description="Pasaje recuperado con su encabezado documental; no es una respuesta generada.")
    similitud: float = Field(description="Similitud coseno con la pregunta. No es probabilidad, confianza ni el puntaje RRF final; la lista puede no estar ordenada por este valor.")
    fuente: Source = Field(description="Procedencia del pasaje, sección y páginas del PDF.")


class SearchResponse(BaseModel):
    request_id: str = Field(description="Identificador de esta petición para localizarla al reportar un error.")
    corpus_id: str = Field(description="Identificador del corpus compatible consultado por el servidor.")
    pasajes: list[Passage] = Field(description="Hasta tres pasajes en orden de recuperación híbrida; una lista vacía no es un fallo de autenticación.")
    tiempos_segundos: dict[str, float] = Field(description=TIMING_HELP)


class QueryResponse(BaseModel):
    request_id: str = Field(description="Identificador de la petición; conservarlo para diagnosticar errores.")
    estado: str = Field(description="Resultado global del pipeline: OK_VALIDADO, OK_RESPUESTA_PARCIAL, OK_PIDE_ACLARACION, OK_EVIDENCIA_INSUFICIENTE u OK_REQUIERE_HUMANO. No equivale al estado documental ni confirma que el incidente real esté resuelto.")
    clasificacion: SolicitudTI = Field(description="Categoría, prioridad, datos faltantes y necesidad de atención humana de la solicitud.")
    respuesta_documental: RespuestaRAG = Field(description="Respuesta en español, estado documental, citas y limitación. Leer estado y limitacion incluso con HTTP 200.")
    fuentes: list[CitedSource] = Field(description="Solo las fuentes citadas en la respuesta. id=F1 corresponde a [F1] en respuesta y F1 en citas; puede estar vacío si no hay afirmaciones documentales.")
    latencia_segundos: float = Field(description="Duración global del pipeline en segundos, redondeada a cuatro decimales; puede diferir del tiempo HTTP observado por el cliente.")
    tiempos_segundos: dict[str, float] = Field(description=TIMING_HELP)


class HealthResponse(BaseModel):
    status: str
    service: str
    input_token_limit: int


class CategoriesResponse(BaseModel):
    categorias: list[Categoria]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    request_id: str | None
    error: ErrorDetail


def openapi_document():
    components = {}
    for model in (QueryRequest, SearchRequest, SearchResponse, QueryResponse,
                  HealthResponse, CategoriesResponse, ErrorResponse, OCRResponse):
        definition = model.model_json_schema(ref_template='#/components/schemas/{model}')
        components.update(definition.pop('$defs', {}))
        components[model.__name__] = definition

    # Descriptions enrich the exported schema without changing runtime contracts.
    descriptions = {
        'Source': {'document_id':'Identificador del documento original.', 'title':'Título del manual.',
                   'category':'Categoría de soporte de la fuente.', 'section':'Código y título de la sección.',
                   'source':'Ruta relativa del PDF dentro del corpus; no es una URL de descarga.',
                   'version':'Versión declarada del documento.', 'pages':'Números de página del PDF, comenzando en 1.'},
        'CitedSource': {'id':'Etiqueta de cita sin corchetes, por ejemplo F1.',
                      'chunk_id':'Identificador del fragmento citado.'},
        'SolicitudTI': {'categoria':'Una de las siete categorías de soporte.',
                       'prioridad':'Prioridad estimada: baja, media o alta; no establece un SLA.',
                       'resumen':'Resumen de la solicitud, entre 10 y 240 caracteres.',
                       'datos_faltantes':'Datos necesarios para precisar el incidente; una lista vacía indica que no se solicitaron datos adicionales.',
                       'requiere_humano':'Indica que se requiere intervención humana; el asistente no ejecuta reparaciones ni concede permisos.',
                       'confianza':'Valor entre 0 y 1 declarado por el clasificador; no es una probabilidad calibrada de exactitud.'},
        'RespuestaRAG': {'estado':'respondida: respuesta documentada; parcial: cobertura limitada; aclaracion: necesita datos; evidencia_insuficiente: no hay respaldo suficiente. Los cuatro pueden devolver HTTP 200.',
                         'limitacion':'Explica el alcance, información faltante o ausencia de respaldo. Obligatoria y no vacía salvo en respondida.'},
        'HealthResponse': {'status':'ok indica que el proceso responde; no comprueba Supabase, Groq ni el modelo.',
                           'service':'Nombre del servicio.', 'input_token_limit':'Presupuesto máximo de entrada por llamada al generador, incluyendo instrucciones y contexto; no son tokens disponibles solo para la pregunta.'},
        'CategoriesResponse': {'categorias':'Valores aceptados para categoria en búsqueda: hardware, software, redes, cuentas, seguridad, acceso y otros.'},
        'ErrorResponse': {'request_id':'Identificador para diagnóstico. Puede ser null en errores fuera del controller.',
                          'error':'Código estable y mensaje legible; no incluye credenciales ni errores internos del proveedor.'},
        'ErrorDetail': {'code':'Código estable de la API para gestionar el error en el cliente.',
                        'message':'Explicación del error y acción sugerida cuando corresponde.'},
    }
    for model, fields in descriptions.items():
        for name, description in fields.items():
            components[model]['properties'][name]['description'] = description
    for name, description in descriptions['Source'].items():
        components['CitedSource']['properties'][name]['description'] = description
    for model in ('SearchResponse', 'QueryResponse'):
        timings = components[model]['properties']['tiempos_segundos']
        names = list(TIMING_STAGES) if model == 'QueryResponse' else list(TIMING_STAGES)[2:9]
        timings['properties'] = {name:{'type':'number', 'minimum':0, 'description':TIMING_STAGES[name]} for name in names}

    source = {'document_id':'TI-SEG', 'title':'Incidentes y riesgos de seguridad',
              'category':'seguridad', 'section':'SEG-02 | Mensaje o enlace sospechoso',
              'source':'seguridad/manual_seguridad.pdf', 'version':'2.0', 'pages':[1]}
    classification = {'categoria':'seguridad', 'prioridad':'media',
                      'resumen':'Correo sospechoso con un enlace que aún no se ha abierto.',
                      'datos_faltantes':[], 'requiere_humano':True, 'confianza':0.9}
    answered = {'request_id':EXAMPLE_REQUEST_ID, 'estado':'OK_REQUIERE_HUMANO',
                'clasificacion':classification, 'respuesta_documental':{
                    'estado':'respondida', 'respuesta':'No abras enlaces ni adjuntos y no respondas con información sensible. Conserva remitente, fecha y descripción para reportarlo por el canal autorizado. [F1]',
                    'citas':['F1'], 'limitacion':''},
                'fuentes':[{'id':'F1', 'chunk_id':'TI-SEG-bb9b19a0f7619c181cc2ab47', **source}],
                'latencia_segundos':3.2,
                'tiempos_segundos':{'classification_seconds':0.5, 'embedding_seconds':0.04,
                    'semantic_search_seconds':0.15, 'lexical_fetch_seconds':0.2, 'bm25_seconds':0.005,
                    'rrf_seconds':0.00003, 'candidate_scoring_seconds':0.00001,
                    'retrieval_seconds':0.3551, 'context_seconds':0.01, 'generation_seconds':0.6,
                    'validation_seconds':0.001, 'support_review_seconds':1.6, 'total_seconds':3.2}}
    clarification = {'request_id':EXAMPLE_REQUEST_ID, 'estado':'OK_PIDE_ACLARACION',
                     'clasificacion':{'categoria':'otros', 'prioridad':'baja',
                         'resumen':'Solicitud sin identificar el equipo, servicio o síntoma.',
                         'datos_faltantes':['Equipo o servicio afectado', 'Mensaje observado'],
                         'requiere_humano':False, 'confianza':0.5},
                     'respuesta_documental':{'estado':'aclaracion',
                         'respuesta':'¿Qué equipo o servicio falla y qué mensaje observas?',
                         'citas':[], 'limitacion':'Faltan datos para seleccionar un procedimiento específico.'},
                     'fuentes':[], 'latencia_segundos':0.9,
                     'tiempos_segundos':{'classification_seconds':0.4, 'retrieval_seconds':0.3,
                                         'generation_seconds':0.0001, 'total_seconds':0.9}}
    insufficient = {'request_id':EXAMPLE_REQUEST_ID, 'estado':'OK_EVIDENCIA_INSUFICIENTE',
                    'clasificacion':{'categoria':'redes', 'prioridad':'baja',
                        'resumen':'Solicitud de configuración VPN ausente del corpus.',
                        'datos_faltantes':[], 'requiere_humano':False, 'confianza':0.8},
                    'respuesta_documental':{'estado':'evidencia_insuficiente',
                        'respuesta':'No dispongo de un procedimiento documentado para configurar esa VPN.',
                        'citas':[], 'limitacion':'El corpus disponible no aporta el servidor, puerto ni procedimiento solicitado.'},
                    'fuentes':[], 'latencia_segundos':2.0,
                    'tiempos_segundos':{'classification_seconds':0.4, 'retrieval_seconds':0.3,
                                        'generation_seconds':0.5, 'total_seconds':2.0}}

    def example(value, summary):
        return {'summary':summary, 'description':'Ejemplo ilustrativo del contrato; no es una medición ni una respuesta garantizada.', 'value':value}

    success_examples = {
        'health/': {'disponible':example({'status':'ok','service':'ti-support-rag','input_token_limit':1000}, 'Proceso disponible; proveedores sin comprobar')},
        'categories/': {'categorias':example({'categorias':['hardware','software','redes','cuentas','seguridad','acceso','otros']}, 'Las siete categorías admitidas')},
        'rag/search/': {'pasajes':example({'request_id':EXAMPLE_REQUEST_ID,
            'corpus_id':'ti-manuals-v2-d479e96962b17496eaa3', 'pasajes':[{
                'chunk_id':'TI-SEG-bb9b19a0f7619c181cc2ab47',
                'texto':'Ante un mensaje sospechoso, el usuario no abre enlaces ni adjuntos y no responde con información sensible.',
                'similitud':0.72, 'fuente':source}],
            'tiempos_segundos':{'embedding_seconds':0.04,'semantic_search_seconds':0.15,
                'lexical_fetch_seconds':0.2,'bm25_seconds':0.005,'rrf_seconds':0.00003,
                'candidate_scoring_seconds':0.00001,'retrieval_seconds':0.3551}}, 'Pasaje recuperado, sin generación de respuesta')},
        'rag/query/': {'documentada':example(answered, 'Respuesta con cita e intervención humana'),
                       'aclaracion':example(clarification, 'HTTP 200 que solicita información adicional'),
                       'sin_evidencia':example(insufficient, 'HTTP 200 sin respaldo suficiente')},
    }
    details = {
        'health/': ('Sistema', 'Comprobar disponibilidad del proceso',
            'Comprueba que la API responde. Es pública y no inicializa el modelo ni consulta Supabase o Groq. '
            'Un resultado ok no confirma credenciales, corpus o disponibilidad de proveedores.'),
        'categories/': ('Sistema', 'Consultar las siete categorías admitidas',
            'Devuelve los valores válidos de categoria para búsqueda y clasificación. No requiere cuerpo. '
            'Necesita DJANGO_API_TOKEN; no consulta Supabase ni Groq.\n\n'+AUTH_HELP),
        'rag/search/': ('RAG', 'Recuperar pasajes sin generar una respuesta',
            'Combina búsqueda semántica y BM25 mediante RRF sobre el corpus autorizado en Supabase y devuelve '
            'hasta tres pasajes con procedencia. No llama a Groq. categoria es opcional y favorece el ranking: '
            '**no es un filtro estricto**; pueden aparecer pasajes de otras categorías. '
            'La similitud coseno no equivale al puntaje de fusión ni a confianza.\n\n'
            '**Cuándo usarlo:** inspeccionar qué evidencia recupera una pregunta antes de generar una respuesta.\n\n'
            '**Límites:** JSON de hasta 16 KiB, pregunta de 1 a 8000 caracteres tras quitar espacios externos, '
            'máximo 1000 tokens de entrada y capacidad del modelo de embeddings (128 tokens con la configuración actual). '
            'Cumplir el límite de caracteres no garantiza cumplir el de tokens. No recibe imágenes ni archivos. '
            'Una lista vacía es un resultado válido; un fallo de consulta devuelve error técnico.\n\n'+AUTH_HELP),
        'rag/query/': ('RAG', 'Clasificar una solicitud y responder con evidencia',
            'Clasifica la solicitud, recupera evidencia, construye contexto y genera o limita la respuesta; '
            'valida contrato, citas y respaldo. Usa Supabase y puede realizar varias llamadas a Groq '
            '(clasificación, generación, revisión y corrección), con consumo de cuota. Algunas aclaraciones '
            'se construyen localmente. La operación es síncrona y puede tardar por esperas o reintentos.\n\n'
            '**Cómo leer el resultado:** estado es el resultado global; respuesta_documental.estado indica '
            'respondida, parcial, aclaracion o evidencia_insuficiente. **HTTP 200 no significa que el incidente '
            'esté resuelto ni que exista una respuesta completa.** Lee también limitacion, datos_faltantes y '
            'requiere_humano. Las citas [F1] del texto se resuelven en fuentes mediante id=F1. '
            'El asistente no crea cuentas, concede permisos ni ejecuta reparaciones.\n\n'
            '**Entrada:** solo pregunta; no admite categoria, usuario, proveedor o modo mock. JSON de hasta 16 KiB; '
            'de 1 a 8000 caracteres tras quitar espacios externos. El presupuesto es de 1000 tokens por llamada '
            'al generador incluyendo instrucciones, contexto y esquema, además del límite del embedder '
            '(128 tokens con la configuración actual). No hay carga HTTP de imágenes.\n\n'
            '**Concurrencia:** una búsqueda o consulta en curso por proceso; una petición simultánea puede '
            'recibir 503 service_busy con Retry-After. Los tiempos del JSON no son latencia HTTP completa.\n\n'+AUTH_HELP),
    }
    errors = {
        '400':('JSON o campos inválidos', [('invalid_input','JSON inválido o campos incorrectos.')], 'Revisa sintaxis, tipos, pregunta no vacía, categoría válida y ausencia de campos adicionales.'),
        '401':('Autenticación rechazada', [('unauthorized','Se requiere un token Bearer válido.')], 'Autoriza con DJANGO_API_TOKEN. En Swagger pega solo el valor; evita Bearer duplicado y tokens de Supabase.'),
        '405':('Método no permitido', [('method_not_allowed','Método HTTP no permitido.')], 'Usa el método documentado para la ruta con barra final. Consulta Allow.'),
        '413':('Cuerpo demasiado grande', [('body_too_large','La petición supera 16 KiB.')], 'Reduce el cuerpo JSON completo; el límite se mide en bytes.'),
        '415':('Tipo de contenido incorrecto', [('unsupported_media_type','Usa Content-Type: application/json.')], 'Envía un objeto JSON con Content-Type: application/json.'),
        '422':('Presupuesto de entrada excedido', [('input_too_large','Resume la pregunta: excede el presupuesto de entrada o del modelo de búsqueda.')], 'Resume la pregunta. El límite de caracteres no sustituye los límites de tokens; no se trunca silenciosamente.'),
        '429':('Cuota del proveedor agotada', [('provider_rate_limited','Groq no tiene cuota disponible. Reintenta después.')], 'Espera el intervalo Retry-After cuando esté disponible; no repitas solicitudes en bucle.'),
        '502':('Respuesta del proveedor no aceptada', [('invalid_provider_response','No se obtuvo una respuesta RAG válida.')], 'No se obtuvo un contrato documental válido o completo. Conserva request_id para diagnóstico.'),
        '503':('Servicio ocupado, no configurado o no disponible', [
            ('api_not_configured','Configura DJANGO_API_TOKEN en el servidor.'),
            ('service_busy','Hay otra solicitud en proceso. Reintenta después.'),
            ('service_unavailable','No se pudo completar la operación RAG.')],
            'api_not_configured: configura un token de al menos 32 caracteres y recrea el contenedor. '
            'service_busy: espera Retry-After (2 s). service_unavailable: revisa configuración, índice o proveedores; '
            'no equivale a ausencia de evidencia documental. Conserva request_id.'),
    }

    def response(model, description, examples=None):
        media = {'schema':{'$ref':f'#/components/schemas/{model}'}}
        if examples:
            media['examples'] = examples
        return {'description':description, 'content':{'application/json':media}}

    paths = {}
    for route, method, output, request_model in (
        ('health/', 'get', 'HealthResponse', None),
        ('categories/', 'get', 'CategoriesResponse', None),
        ('rag/search/', 'post', 'SearchResponse', 'SearchRequest'),
        ('rag/query/', 'post', 'QueryResponse', 'QueryRequest'),
    ):
        tag, summary, description = details[route]
        operation = {'operationId':route.strip('/').replace('/', '_'), 'summary':summary,
                     'description':description, 'tags':[tag],
                     'responses':{'200':response(output, 'Operación completada. Los ejemplos son ilustrativos.', success_examples[route])}}
        statuses = ['405']
        if route == 'health/':
            operation['security'] = []
        else:
            statuses += ['401', '503']
        if request_model:
            examples = {'general':example({'pregunta':'Recibí un correo sospechoso con un enlace. No lo he abierto. ¿Qué indica el manual?'}, 'Pregunta concreta con condición relevante')}
            if route == 'rag/search/':
                examples['categoria_preferida'] = example({'pregunta':'Mensaje sospechoso con un enlace', 'categoria':'seguridad'}, 'Categoría opcional como preferencia de ranking')
            else:
                examples['ambigua'] = example({'pregunta':'No funciona. Ayúdame.'}, 'Solicitud que necesita aclaración')
                examples['sin_cobertura'] = example({'pregunta':'Necesito configurar una VPN corporativa en Windows 11. Dame el servidor y el puerto exactos.'}, 'Solicitud sin procedimiento en el corpus académico')
                examples['ocr_revisado'] = example({'pregunta':'¿Qué indica este error?', 'texto_ocr':'Error de red'}, 'Texto OCR revisado; se valida el presupuesto de ambos campos juntos')
            operation['requestBody'] = {'required':True, 'description':'Objeto JSON; los campos adicionales se rechazan.',
                'content':{'application/json':{'schema':{'$ref':f'#/components/schemas/{request_model}'}, 'examples':examples}}}
            statuses += ['400', '413', '415', '422']
        if route == 'rag/query/':
            statuses += ['429', '502']
        for status in statuses:
            title, codes, action = errors[status]
            # Categories does not run RAG or acquire its semaphore.
            if route == 'categories/' and status == '503':
                codes = codes[:1]
                title, action = 'Token del servidor no configurado', 'Configura DJANGO_API_TOKEN con al menos 32 caracteres y recrea el contenedor.'
            operation['responses'][status] = response('ErrorResponse', title+'. '+action,
                {code:{'summary':code, 'value':{'request_id':EXAMPLE_REQUEST_ID,
                                             'error':{'code':code,'message':message}}} for code, message in codes})
            headers = {}
            if status == '401':
                headers['WWW-Authenticate'] = {'description':'Esquema requerido.', 'schema':{'type':'string', 'const':'Bearer'}}
            if status == '405':
                headers['Allow'] = {'description':'Métodos admitidos en esta ruta.', 'schema':{'type':'string'}}
            if status in {'429', '503'} and route != 'categories/':
                headers['Retry-After'] = {'description':'Segundos de espera, cuando están disponibles. service_busy devuelve 2.', 'schema':{'type':'integer','minimum':0}}
            if headers:
                operation['responses'][status]['headers'] = headers
        paths[f'/api/v1/{route}'] = {method:operation}
    ocr_responses = {'200': response('OCRResponse', 'Extracción para revisión; presupuesto.admisible puede ser false.', {
        'captura': example({'request_id': EXAMPLE_REQUEST_ID, 'texto_ocr': 'Error de red',
            'motor': 'tesseract', 'idiomas': 'spa+eng', 'confianza_ocr': 92.0, 'cantidad_palabras': 3,
            'presupuesto': {'admisible': True, 'tokens_entrada': 730, 'limite_entrada': 1000,
                'tokens_busqueda': 30, 'limite_busqueda': 128, 'motivo': None}}, 'Ejemplo ilustrativo, no una medición')})}
    for status in ('400', '401', '405', '413', '415', '422', '503'):
        ocr_responses[status] = response('ErrorResponse', {
            '400': 'Archivo ausente, corrupto o campos incorrectos.', '401': 'Bearer ausente o incorrecto.',
            '405': 'Método no permitido.', '413': 'Máximo 5 MiB, 4 megapíxeles y 4096 px por lado.',
            '415': 'Requiere multipart y una imagen PNG/JPEG/WebP con MIME y extensión coherentes.',
            '422': 'Imagen sin texto legible o extracción fallida.',
            '503': 'Motor OCR no disponible, servicio ocupado o modelo de búsqueda no disponible.',
        }[status])
    paths['/api/v1/ocr/extract/'] = {'post': {
        'operationId': 'ocr_extract', 'tags': ['OCR'], 'summary': 'Extraer texto de una captura',
        'description': ('No llama a Groq ni carga documentos en Supabase. Solo acepta una imagen estática. '
            'El temporal se elimina al terminar. La confianza es del OCR, no de la respuesta TI. '
            'Un presupuesto no admisible permite revisar y reducir el texto; rag/query vuelve a validarlo. '
            'Comparte el límite de una operación en curso por proceso.'),
        'requestBody': {'required': True, 'content': {'multipart/form-data': {'schema': {
            'type': 'object', 'additionalProperties': False, 'required': ['imagen'], 'properties': {
                'imagen': {'type': 'string', 'format': 'binary', 'description': 'PNG, JPEG o WebP; máximo 5 MiB.'},
                'pregunta': {'type': 'string', 'maxLength': 8000, 'description': 'Opcional; se usa para comprobar pregunta + OCR.'},
            }}}}}, 'responses': ocr_responses}}
    return {'openapi':'3.1.0', 'info':{'title':'TI Support RAG API','version':'1.0.0',
        'description':('Soporte TI con clasificación y respuestas fundamentadas en manuales.\n\n'
            '### Recorrido recomendado\n1. Ejecuta **health** para comprobar el proceso.\n'
            '2. Autoriza y consulta **categories** para comprobar el token.\n'
            '3. Usa **rag/search** para inspeccionar pasajes sin generar texto con Groq.\n'
            '4. Usa **rag/query** para obtener clasificación, respuesta y citas.\n\n'+AUTH_HELP+
            '\n### Alcance\nLas rutas terminan en `/`. Los POST RAG requieren `application/json`; OCR usa `multipart/form-data`. '
            'El servidor usa el usuario Supabase configurado: el token de API no crea identidades '
            'individuales ni aislamiento entre consumidores. Los ejemplos son ilustrativos; sus '
            'duraciones y respuestas no son resultados garantizados. No se incluyen secretos.\n\n'
            '### Estados y errores\nHTTP 200 puede contener aclaración o evidencia insuficiente. '
            '401 corresponde al token de esta API; 429 a cuota de Groq; 503 a configuración, '
            'ocupación o disponibilidad. Un fallo técnico no demuestra ausencia de documentos.')},
        'servers':[{'url':'/', 'description':'Mismo servidor que sirve Swagger'}],
        'tags':[{'name':'Sistema','description':'Disponibilidad del proceso y catálogo de categorías. No consultan proveedores.'},
                {'name':'RAG','description':'Recuperación documental y respuestas con citas. Requieren autenticación y servicios configurados.'},
                {'name':'OCR','description':'Extraer y revisar texto antes de consultar el RAG.'}],
        'paths':paths, 'security':[{'BearerAuth':[]}],
        'components':{'schemas':components,'securitySchemes':{'BearerAuth':{
            'type':'http','scheme':'bearer','description':AUTH_HELP}}}}


@require_safe
def schema(request):
    return JsonResponse(openapi_document(), json_dumps_params={'ensure_ascii':False})


@require_safe
def swagger(request):
    return render(request, 'api/swagger.html', {'schema_url':reverse('openapi-schema')})


@require_safe
def swagger_asset(request, filename):
    # Explicit allowlist makes assets available with DEBUG=False without exposing
    # arbitrary package files or requiring a separate static server locally.
    content_types = {'swagger-ui.css':'text/css', 'swagger-ui-bundle.js':'application/javascript',
                     'swagger-ui-standalone-preset.js':'application/javascript'}
    if filename not in content_types:
        raise Http404
    root = Path(drf_spectacular_sidecar.__file__).parent / 'static/drf_spectacular_sidecar/swagger-ui-dist'
    return FileResponse((root / filename).open('rb'), content_type=content_types[filename])

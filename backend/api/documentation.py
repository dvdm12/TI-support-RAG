"""OpenAPI for the native Django controllers; Swagger assets stay local."""
from pathlib import Path

import drf_spectacular_sidecar
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_safe
from pydantic import BaseModel

from schemas.request_v1 import Categoria, SolicitudTI
from schemas.rag_response_v1 import RespuestaRAG
from .contracts import QueryRequest, SearchRequest


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
    chunk_id: str
    texto: str
    similitud: float
    fuente: Source


class SearchResponse(BaseModel):
    request_id: str
    corpus_id: str
    pasajes: list[Passage]


class QueryResponse(BaseModel):
    request_id: str
    estado: str
    clasificacion: SolicitudTI
    respuesta_documental: RespuestaRAG
    fuentes: list[CitedSource]
    latencia_segundos: float


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
                  HealthResponse, CategoriesResponse, ErrorResponse):
        definition = model.model_json_schema(ref_template='#/components/schemas/{model}')
        components.update(definition.pop('$defs', {}))
        components[model.__name__] = definition

    def response(model, description):
        return {'description':description, 'content':{'application/json':{
            'schema':{'$ref':f'#/components/schemas/{model}'}}}}

    paths = {}
    for route, method, summary, output, request_model in (
        ('health/', 'get', 'Estado de la API (sin comprobar proveedores)', 'HealthResponse', None),
        ('categories/', 'get', 'Categorías de soporte TI', 'CategoriesResponse', None),
        ('rag/search/', 'post', 'Buscar pasajes en los manuales de Supabase', 'SearchResponse', 'SearchRequest'),
        ('rag/query/', 'post', 'Clasificar y responder con RAG y citas', 'QueryResponse', 'QueryRequest'),
    ):
        operation = {'operationId':route.strip('/').replace('/', '_'), 'summary':summary,
                     'tags':['Sistema' if method=='get' else 'RAG'],
                     'responses':{'200':response(output, 'Operación completada')}}
        errors = {'405':'Método no permitido'}
        if route == 'health/':
            operation['security'] = []
        else:
            errors.update({'401':'Token Bearer ausente o incorrecto',
                           '503':'Servicio ocupado, no configurado o no disponible'})
        if request_model:
            operation['description'] = ('Entrada limitada a 1000 tokens; la búsqueda también aplica '
                'el límite del modelo de embeddings. Cuerpo máximo: 16 KiB. '
                'Las respuestas de aclaración o evidencia insuficiente devuelven HTTP 200.')
            operation['requestBody'] = {'required':True,'content':{'application/json':{
                'schema':{'$ref':f'#/components/schemas/{request_model}'},
                'example':{'pregunta':'¿Qué debo hacer si recibo un correo sospechoso?'}}}}
            errors.update({'400':'JSON o campos inválidos', '413':'Cuerpo demasiado grande',
                           '415':'Se requiere application/json', '422':'Presupuesto de entrada excedido'})
        if route == 'rag/query/':
            errors.update({'429':'Cuota de Groq agotada', '502':'Respuesta del proveedor inválida'})
        for status, description in errors.items():
            operation['responses'][status] = response('ErrorResponse', description)
            if status in {'429', '503'}:
                operation['responses'][status]['headers'] = {'Retry-After':{
                    'description':'Segundos de espera, cuando están disponibles', 'schema':{'type':'integer'}}}
        paths[f'/api/v1/{route}'] = {method:operation}
    return {'openapi':'3.1.0', 'info':{'title':'TI Support RAG API','version':'1.0.0',
        'description':'API Django de soporte TI. Usa Authorize con DJANGO_API_TOKEN para los endpoints protegidos.'},
        'servers':[{'url':'/'}], 'paths':paths, 'security':[{'BearerAuth':[]}],
        'components':{'schemas':components,'securitySchemes':{'BearerAuth':{
            'type':'http','scheme':'bearer','description':'Token del servidor configurado en DJANGO_API_TOKEN; introduce solo el token.'}}}}


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

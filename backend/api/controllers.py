"""Django controllers with explicit bearer authentication and JSON contracts."""
import json
import logging
import math
import re
import secrets
from typing import get_args
from uuid import uuid4
from django.conf import settings
from django.http import JsonResponse
from django.http.multipartparser import MultiPartParserError
from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError
from schemas.request_v1 import Categoria
from src.token_budget import InputBudgetError
from . import services
from .contracts import QueryRequest, SearchRequest, OCRExtractRequest
from .uploads import BoundedImageUploadHandler, UploadError
from src.ocr.exceptions import OCRDependencyError, OCRConfigurationError, OCRExtractionError

logger = logging.getLogger('api')


def error(code,message,status,request_id=None):
    return JsonResponse({'request_id':request_id,'error':{'code':code,'message':message}},status=status,json_dumps_params={'ensure_ascii':False})


class JsonController(View):
    authenticated = True

    def dispatch(self,request,*args,**kwargs):
        self.request_id = str(uuid4())
        if self.authenticated:
            expected = settings.RAG_API_TOKEN
            if len(expected) < 32:
                return error('api_not_configured','Configura DJANGO_API_TOKEN en el servidor.',503,self.request_id)
            scheme,_,token = request.headers.get('Authorization','').partition(' ')
            if scheme.lower() != 'bearer' or not secrets.compare_digest(token.encode(),expected.encode()):
                response = error('unauthorized','Se requiere un token Bearer válido.',401,self.request_id)
                response['WWW-Authenticate'] = 'Bearer'
                return response
        try:
            return super().dispatch(request,*args,**kwargs)
        except InputBudgetError:
            return error('input_too_large','Resume la pregunta: excede el presupuesto de entrada o del modelo de búsqueda.',422,self.request_id)
        except services.ServiceBusy:
            response = error('service_busy','Hay otra solicitud en proceso. Reintenta después.',503,self.request_id)
            response['Retry-After'] = '2'
            return response
        except UploadError as exc:
            return error(exc.code, exc.message, exc.status, self.request_id)
        except (TooManyFilesSent, TooManyFieldsSent, MultiPartParserError):
            return error('invalid_input', 'Envía una imagen y únicamente el campo pregunta opcional.', 400, self.request_id)
        except (OCRDependencyError, OCRConfigurationError):
            return error('ocr_unavailable', 'El motor OCR no está disponible en el servidor.', 503, self.request_id)
        except OCRExtractionError:
            return error('ocr_failed', 'No se pudo leer la imagen. Prueba con una captura más clara.', 422, self.request_id)
        except RequestDataTooBig:
            return error('body_too_large','La petición supera 16 KiB.',413,self.request_id)
        except Exception as exc:
            # No exception text, traceback, body or credentials go to the client/log.
            logger.error('request_id=%s failure_type=%s',self.request_id,type(exc).__name__)
            return error('service_unavailable','No se pudo completar la operación RAG.',503,self.request_id)

    def http_method_not_allowed(self,request,*args,**kwargs):
        response = error('method_not_allowed','Método HTTP no permitido.',405,self.request_id)
        response['Allow'] = ', '.join(self._allowed_methods())
        return response

    def body(self,request,schema):
        if request.content_type != 'application/json':
            return None,error('unsupported_media_type','Usa Content-Type: application/json.',415,self.request_id)
        # Also bound the actual bytes for clients without Content-Length.
        if len(request.body) > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
            return None,error('body_too_large','La petición supera 16 KiB.',413,self.request_id)
        try:
            value = schema.model_validate(json.loads(request.body.decode('utf-8')))
        except (ValidationError,ValueError,UnicodeDecodeError):
            return None,error('invalid_input','JSON inválido o campos incorrectos.',400,self.request_id)
        return value,None


class HealthController(JsonController):
    authenticated = False
    http_method_names = ['get','head','options']

    def get(self,request):
        return JsonResponse({'status':'ok','service':'ti-support-rag','input_token_limit':1000})


class CategoriesController(JsonController):
    http_method_names = ['get','head','options']

    def get(self,request):
        return JsonResponse({'categorias':list(get_args(Categoria))})


# These endpoints never use session/cookie authentication. Bearer is supplied
# explicitly and checked before parsing or invoking RAG; CSRF is not a substitute.
@method_decorator(csrf_exempt,name='dispatch')
class SearchController(JsonController):
    http_method_names = ['post','options']

    def post(self,request):
        data,failure = self.body(request,SearchRequest)
        if failure is not None:
            return failure
        return JsonResponse({'request_id':self.request_id,**services.search(data.pregunta,data.categoria)},json_dumps_params={'ensure_ascii':False})


@method_decorator(csrf_exempt,name='dispatch')
class QueryController(JsonController):
    http_method_names = ['post','options']

    def post(self,request):
        data,failure = self.body(request,QueryRequest)
        if failure is not None:
            return failure
        options = {'ocr_text': data.texto_ocr} if data.texto_ocr is not None else {}
        result = services.run_query(data.pregunta,self.request_id,**options)
        if result['state'] in {'ERROR_TECNICO','ERROR_FORMATO'}:
            if 'HTTP 429' in (result.get('execution_error') or ''):
                response = error('provider_rate_limited','Groq no tiene cuota disponible. Reintenta después.',429,self.request_id)
                wait = re.search(r'espera requerida de (\d+(?:\.\d+)?) s',result['execution_error'])
                if wait:
                    response['Retry-After'] = str(math.ceil(float(wait.group(1))))
                return response
            return error('invalid_provider_response' if result['state']=='ERROR_FORMATO' else 'service_unavailable',
                         'No se obtuvo una respuesta RAG válida.',502 if result['state']=='ERROR_FORMATO' else 503,self.request_id)
        documentary = result.get('documentary_output')
        if not documentary:
            return error('invalid_provider_response','Respuesta RAG incompleta.',502,self.request_id)
        sources = []
        for label in documentary['citas']:
            candidate = result['rag']['catalog'][label]
            sources.append({'id':label,'chunk_id':candidate['chunk_id'],
                            **{k:candidate['metadata'].get(k) for k in ('document_id','title','category','section','source','version','pages')}})
        return JsonResponse({'request_id':self.request_id,'estado':result['state'],
                             'clasificacion':result['classification'],'respuesta_documental':documentary,
                             'fuentes':sources,'latencia_segundos':result['latency_seconds'],
                             'tiempos_segundos':result['rag'].get('timings',{})},
                            json_dumps_params={'ensure_ascii':False})


@method_decorator(csrf_exempt, name='dispatch')
class OCRExtractController(JsonController):
    http_method_names = ['post', 'options']

    def post(self, request):
        if request.content_type != 'multipart/form-data':
            return error('unsupported_media_type', 'Envía multipart/form-data con una imagen.', 415, self.request_id)
        try:
            length = int(request.META.get('CONTENT_LENGTH') or 0)
            if length < 0:
                raise ValueError
        except ValueError:
            return error('invalid_input', 'Longitud de petición inválida.', 400, self.request_id)
        if length > settings.OCR_MAX_UPLOAD_BYTES + settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
            return error('body_too_large', 'La petición de imagen supera el tamaño permitido.', 413, self.request_id)
        handler = BoundedImageUploadHandler(request)
        request.upload_handlers = [handler]
        fields, files = request.POST, request.FILES
        if handler.error:
            raise handler.error
        if (set(fields) - {'pregunta'} or any(len(fields.getlist(key)) != 1 for key in fields)
                or set(files) != {'imagen'} or len(files.getlist('imagen')) != 1):
            return error('invalid_input', 'Envía una imagen y únicamente el campo pregunta opcional.', 400, self.request_id)
        try:
            data = OCRExtractRequest.model_validate(fields.dict())
        except ValidationError:
            return error('invalid_input', 'La pregunta no cumple el contrato.', 400, self.request_id)
        result = services.extract_ocr(files['imagen'], data.pregunta)
        return JsonResponse({'request_id': self.request_id, **result}, json_dumps_params={'ensure_ascii': False})


def not_found(request,exception):
    return error('not_found','Endpoint no encontrado.',404)


def server_error(request):
    return error('internal_error','Error interno del servicio.',500)

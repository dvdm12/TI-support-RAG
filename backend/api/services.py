"""Lazy RAG adapter. Cache the immutable index/model, not Supabase sessions."""
from functools import lru_cache
import logging
from threading import BoundedSemaphore
from time import perf_counter
from django.conf import settings
from src.token_budget import InputBudgetError
from .attention import select_route
from .tickets import TicketCatalogError, consultar_estado_ticket

_work_slot = BoundedSemaphore(1)
logger = logging.getLogger("api")


class ServiceBusy(RuntimeError):
    pass


@lru_cache(maxsize=1)
def resources():
    from src.rag.embeddings import SentenceEmbedder
    from src.rag.index import load_index
    _,_,_,config = load_index(settings.RAG_INDEX_PATH)
    embedder = SentenceEmbedder(config.revision)
    corpus_id,_,_,config = load_index(settings.RAG_INDEX_PATH,embedder)
    return embedder,corpus_id,config


def retriever(question):
    from src.rag.repository import SupabaseRepository
    from src.rag.retrieval import Retriever
    embedder,corpus,config = resources()
    if embedder.count_tokens(question) > config.max_seq_length:
        raise InputBudgetError('Resume la pregunta para que el modelo de búsqueda pueda procesarla sin truncarla.')
    return Retriever(SupabaseRepository.connect(),embedder,corpus,config)


def query_content(question, ocr_text=None):
    if ocr_text is None:
        return question
    from src.pipeline import prepare_case_input
    content, _ = prepare_case_input({'input': question}, {
        'extraction_valid': True, 'extracted_text': ocr_text,
    })
    return content


def run_query(question, request_id, *, ocr_text=None):
    from src.config import PROMPT_PATH
    from src.groq_client import build_payload
    from src.token_budget import enforce_input_budget
    content = query_content(question, ocr_text)
    enforce_input_budget(build_payload(PROMPT_PATH.read_text(),content))
    if not _work_slot.acquire(blocking=False):
        raise ServiceBusy()
    try:
        from src.rag.pipeline import run_rag_case
        return run_rag_case({'id':request_id,'tipo':'api','input':content},retriever(content),mode='groq')
    finally:
        _work_slot.release()


def attend(question, request_id, **options):
    """Dispatch one independent turn and record the operation actually attempted."""
    started = perf_counter()
    route, code = select_route(question)
    operation = None
    if route == "consulta_documental":
        operation = "run_query"
        try:
            result = run_query(question, request_id, **options)
        except (InputBudgetError, ServiceBusy) as exc:
            logger.info("request_id=%s ruta=%s operacion=%s motivo_salida=%s",
                        request_id, route, operation, type(exc).__name__)
            raise
        except Exception as exc:
            logger.error("request_id=%s failure_type=%s", request_id, type(exc).__name__)
            result = {"state": "ERROR_TECNICO"}
        result = {**result}
        reason = result["state"].lower()
        if result["state"].startswith("OK_") and not result.get("documentary_output"):
            reason = "respuesta_documental_incompleta"
    else:
        if route == "respuesta_directa":
            state, reason = "OK_RESPUESTA_DIRECTA", code or "alcance_informado"
            answer = "Puedo consultar manuales de soporte TI y el estado de tickets de demostración."
            if reason == "fuera_de_alcance":
                answer = f"Esa pregunta queda fuera del alcance de la mesa de ayuda. {answer}"
        elif route == "aclaracion":
            state = "OK_PIDE_ACLARACION"
            if code == "intencion_mixta":
                reason = "intencion_mixta"
                answer = "¿Quieres consultar el estado del ticket o revisar el procedimiento en los manuales?"
            else:
                reason = "codigo_requerido"
                answer = "Indica un único código de ticket válido, por ejemplo TI-1001."
        elif route == "operacion_prohibida":
            state, reason = "OPERACION_NO_PERMITIDA", "herramienta_solo_lectura"
            answer = "Solo puedo consultar el estado de los tickets. Solicita el cambio a soporte TI."
        else:
            operation = "consultar_estado_ticket"
            try:
                ticket = consultar_estado_ticket(code)
            except TicketCatalogError:
                state, reason = "ERROR_TECNICO", "catalogo_indisponible"
                answer = "El catálogo de tickets de demostración está indisponible. Inténtalo más tarde."
            else:
                if ticket is None:
                    state, reason = "TICKET_NO_ENCONTRADO", "ticket_inexistente"
                    answer = f"El ticket {code} no aparece en el catálogo de demostración."
                else:
                    state, reason = "OK_TICKET_CONSULTADO", "ticket_encontrado"
                    answer = f"Ticket ficticio {code} — {ticket['estado']}. {ticket['detalle']}"
        result = {"state": state, "answer": answer,
                  "latency_seconds": round(perf_counter() - started, 4)}
    trace = {"ruta": route, "operacion": operation,
             "resultado": result["state"], "motivo_salida": reason}
    logger.info("request_id=%s traza_atencion=%s", request_id, trace)
    return {**result, "trace": trace}


def ocr_budget(question, text):
    from src.config import PROMPT_PATH
    from src.groq_client import build_payload
    from src.token_budget import input_budget, INPUT_TOKEN_LIMIT
    content = query_content(question, text)
    budget = input_budget(build_payload(PROMPT_PATH.read_text(), content))
    result = {'admisible': False, 'tokens_entrada': budget['total_tokens'],
              'limite_entrada': INPUT_TOKEN_LIMIT, 'tokens_busqueda': None,
              'limite_busqueda': None, 'motivo': None}
    if len(text) > 8000 or budget['total_tokens'] > INPUT_TOKEN_LIMIT:
        result['motivo'] = 'Reduce el texto OCR o recorta la captura antes de consultar.'
        return result
    embedder, _, config = resources()
    result['tokens_busqueda'] = embedder.count_tokens(content)
    result['limite_busqueda'] = config.max_seq_length
    result['admisible'] = result['tokens_busqueda'] <= config.max_seq_length
    if not result['admisible']:
        result['motivo'] = 'Reduce la pregunta y el texto OCR para el modelo de búsqueda.'
    return result


def extract_ocr(upload, question=''):
    from .uploads import temporary_ocr_image, UploadError
    from src.multimodal import prepare_multimodal_input
    if not _work_slot.acquire(blocking=False):
        raise ServiceBusy()
    try:
        with temporary_ocr_image(upload) as path:
            multimodal = prepare_multimodal_input(question, path, ocr_engine='tesseract')
            if not multimodal['extraction_valid']:
                raise UploadError('ocr_no_text', 'No se encontró texto legible. Prueba con una captura más nítida.', 422)
            extraction = multimodal['extraction']
            text = multimodal['extracted_text']
            return {'texto_ocr': text, 'motor': extraction['engine'],
                    'idiomas': extraction['language'], 'confianza_ocr': extraction['ocr_confidence'],
                    'cantidad_palabras': extraction['word_count'],
                    'presupuesto': ocr_budget(question, text)}
    finally:
        _work_slot.release()


def search(question, category=None):
    from src.token_budget import encoding, INPUT_TOKEN_LIMIT
    if len(encoding().encode(question,disallowed_special=())) > INPUT_TOKEN_LIMIT:
        raise InputBudgetError('Pregunta excede el presupuesto de entrada.')
    if not _work_slot.acquire(blocking=False):
        raise ServiceBusy()
    try:
        service = retriever(question)
        candidates,timings = service.retrieve(question,category=category)
        return {'corpus_id':service.corpus_id,'tiempos_segundos':timings,'pasajes':[{
            'chunk_id':c.chunk_id,'texto':c.content,'similitud':c.similitud,
            'fuente':{k:c.metadata.get(k) for k in ('document_id','title','category','section','source','version','pages')}
        } for c in candidates]}
    finally:
        _work_slot.release()

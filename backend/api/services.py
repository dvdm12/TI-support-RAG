"""Lazy RAG adapter. Cache the immutable index/model, not Supabase sessions."""
from functools import lru_cache
from threading import BoundedSemaphore
from django.conf import settings
from src.token_budget import InputBudgetError

_work_slot = BoundedSemaphore(1)


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

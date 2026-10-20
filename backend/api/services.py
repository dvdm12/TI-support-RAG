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


def run_query(question, request_id):
    from src.config import PROMPT_PATH
    from src.groq_client import build_payload
    from src.token_budget import enforce_input_budget
    enforce_input_budget(build_payload(PROMPT_PATH.read_text(),question))
    if not _work_slot.acquire(blocking=False):
        raise ServiceBusy()
    try:
        from src.rag.pipeline import run_rag_case
        return run_rag_case({'id':request_id,'tipo':'api','input':question},retriever(question),mode='groq')
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
        candidates,_ = service.retrieve(question,category=category)
        return {'corpus_id':service.corpus_id,'pasajes':[{
            'chunk_id':c.chunk_id,'texto':c.content,'similitud':c.similitud,
            'fuente':{k:c.metadata.get(k) for k in ('document_id','title','category','section','source','version','pages')}
        } for c in candidates]}
    finally:
        _work_slot.release()

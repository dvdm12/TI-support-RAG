"""Small client adapter for the teacher's class 08 documentary RAG practice.

Uses exact Supabase cosine retrieval and one documentary generation, without
the application's classifier, hybrid retrieval or semantic-review pipeline.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np

from schemas.rag_response_v1 import RespuestaRAG
from src.config import MODEL
from src.groq_client import build_payload, call_groq
from src.rag.citations import validate_response
from src.rag.config import RAGConfig
from src.rag.context import build_context
from src.token_budget import INPUT_TOKEN_LIMIT, input_budget
from scripts.verify_supabase import inventory


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def upload_and_check(repository, corpus_id, chunks, vectors, config):
    repository.upsert(corpus_id, chunks, vectors, config)
    expected = {chunk.chunk_id: chunk.text for chunk in chunks}
    if inventory(repository, corpus_id) != expected:
        raise RuntimeError('Las filas de Supabase no coinciden con el índice cargado.')
    return {'corpus_id': corpus_id, 'rows_verified': len(chunks), 'upsert_performed': True}


def recover(question, repository, embedder, corpus_id, config, k=3):
    if not isinstance(question, str) or not question.strip():
        raise ValueError('Escribe una pregunta no vacía.')
    embedder.assert_compatible(config)
    vector = embedder.encode([question])[0]
    return repository.search(corpus_id, vector, config, k)


def verify_new_client(question, candidates, first, second, embedder, corpus_id, config):
    if first.owner_id != second.owner_id:
        raise RuntimeError('La práctica requiere el mismo usuario en ambos clientes.')
    repeated = recover(question, second, embedder, corpus_id, config)
    if ([c.chunk_id for c in candidates] != [c.chunk_id for c in repeated]
            or [c.content for c in candidates] != [c.content for c in repeated]
            or not np.allclose([c.similitud for c in candidates], [c.similitud for c in repeated])):
        raise RuntimeError('El cliente nuevo no recuperó los mismos pasajes.')
    return {'corpus_id': corpus_id, 'same_question': question,
            'persistence_new_client': True, 'matching_passages': len(repeated),
            'upsert_performed': False, 'owner_isolation': 'No probado: ambos clientes usan el mismo usuario.'}


def execute_query(question, repository, embedder, corpus_id, config, *, candidates=None,
                  generator=call_groq, k=3):
    """One real documentary call; record rejected output as a failure, never accept it."""
    started = perf_counter()
    prompt_path = RAGConfig().prompt
    trace = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'consulta': question,
             'corpus_id': corpus_id, 'prompt_version': prompt_path.stem,
             'modelo_generativo': MODEL, 'temperatura': 0, 'reasoning_effort': 'low',
             'k': k, 'source': 'groq', 'status': 'ERROR_TECNICO', 'resultado': None,
             'recuperados': [], 'catalogo': {}, 'failure_stage': None}
    stage = 'retrieval'
    try:
        if candidates is None:
            candidates = recover(question, repository, embedder, corpus_id, config, k)
        trace['recuperados'] = [c.model_dump() for c in candidates]
        stage = 'context'
        response_format = {'type': 'json_schema', 'json_schema': {
            'name': 'respuesta_rag', 'strict': True, 'schema': RespuestaRAG.model_json_schema()}}
        prompt = prompt_path.read_text(encoding='utf-8')
        context = build_context(question, candidates, request_fits=lambda text:
            input_budget(build_payload(prompt, text, response_format=response_format))['total_tokens'] <= INPUT_TOKEN_LIMIT)
        trace.update(contexto=context['user_content'], omitidos=context['omitted'],
                     catalogo={label: c.model_dump() for label, c in context['catalog'].items()},
                     input_budget=input_budget(build_payload(prompt, context['user_content'], response_format=response_format)))
        stage = 'generation'
        response = generator(prompt, context['user_content'], model=MODEL,
                             response_format=response_format, max_retries=0)
        trace.update(uso_tokens=response.get('usage'), modelo_servido=response.get('model'),
                     latencia_generacion_segundos=response.get('latency_seconds'),
                     http_status=(response.get('http') or {}).get('status_code'))
        stage = 'validation'
        if response.get('finish_reason') != 'stop':
            raise ValueError('La generación no terminó completamente.')
        usage = response.get('usage') or {}
        if usage.get('prompt_tokens') is not None and usage['prompt_tokens'] > INPUT_TOKEN_LIMIT:
            raise ValueError('El proveedor excedió el presupuesto de entrada.')
        output = validate_response(response['raw_output'], context['catalog'])
        trace.update(status='ACCEPTED', resultado=output.model_dump())
    except Exception as exc:
        trace.update(failure_stage=stage, error_type=type(exc).__name__)
        # Exception messages, rejected raw output and credentials are not exported.
        status = re.search(r'HTTP (\d{3})', str(exc))
        if status:
            trace['http_status'] = int(status.group(1))
    trace['latencia_total_segundos'] = round(perf_counter() - started, 4)
    return trace


def show(trace):
    output = trace['resultado']
    if output is None:
        print('ERROR_TECNICO:', trace.get('error_type'), '| etapa:', trace['failure_stage'],
              '| HTTP:', trace.get('http_status'), '| No se aceptó una respuesta sin validar.')
        return
    print('Estado:', output['estado'], '\nRespuesta:', output['respuesta'])
    if output['limitacion']:
        print('Limitación:', output['limitacion'])
    for label in output['citas']:
        candidate = trace['catalogo'][label]
        meta = candidate['metadata']
        print(f"\n[{label}] {meta['source']} / {meta['section']} / versión {meta['version']}")
        print('Identificador:', candidate['chunk_id'])
        print(candidate['content'])

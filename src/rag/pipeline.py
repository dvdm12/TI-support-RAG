"""OCR → classification → retrieval → documentary generation → local decision."""
import json
import hashlib
import time
from datetime import datetime, timezone
from pydantic import ValidationError
from src.config import MODEL, PROMPT_PATH, PROMPT_VERSION
from src.pipeline import run_case, prepare_case_input
from src.multimodal import prepare_multimodal_input
from src.groq_client import call_groq
from schemas.rag_response_v1 import RespuestaRAG
from .config import RAGConfig
from .context import build_context
from .citations import validate_response


def run_rag_case(case, retriever, *, image_path=None, ocr_engine='easyocr',
                 mode='groq', model=MODEL, context_chars=6000,
                 documentary_fixture=None, classifier=run_case, generator=call_groq):
    started = time.perf_counter()
    result = {'case_id': case['id'], 'tipo': case['tipo'], 'input': case['input'],
              'model': 'mock' if mode == 'mock' else None, 'model_requested': model, 'source': mode,
              'prompt_version': RAGConfig().prompt.stem, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'state': None, 'classification': None, 'classification_state': None,
              'raw_output': None, 'validated_output': None, 'documentary_output': None,
              'validation_errors': [], 'execution_error': None, 'multimodal': None,
              'usage': None, 'metrics': None, 'http': None, 'user_content_sent': None,
              'rag': {'corpus_id': retriever.corpus_id, 'config': retriever.config.model_dump(),
                      'k': retriever.k, 'candidates': [], 'catalog': {}, 'omitted': [],
                      'citations_valid': False, 'semantic_support_review': 'PENDIENTE',
                      'contract_version': 'rag_response_v1',
                      'contract_schema': RespuestaRAG.model_json_schema(),
                      'generation_parameters': {'temperature': 0, 'max_completion_tokens': 1500,
                                                'max_retries': 0, 'http_timeout_seconds': [10, 60]},
                      'timings': {}}, 'failure_stage': None}
    stage = 'ocr'
    try:
        begin = time.perf_counter()
        multimodal = prepare_multimodal_input(case['input'], image_path, ocr_engine=ocr_engine)
        result['multimodal'] = multimodal if image_path else None
        user_input, _ = prepare_case_input(case, multimodal if image_path else None)
        result['rag']['timings']['ocr_seconds'] = time.perf_counter() - begin
        stage = 'classification'
        begin = time.perf_counter()
        classification = classifier(case, system_prompt=PROMPT_PATH.read_text(),
                                    prompt_version=PROMPT_VERSION, model=model, mode=mode,
                                    multimodal_input=multimodal if image_path else None)
        result['rag']['timings']['classification_seconds'] = time.perf_counter() - begin
        result['classification'] = classification.get('validated_output')
        result['validated_output'] = result['classification']
        result['classification_state'] = classification['state']
        result['classification_trace'] = classification
        if classification['state'] in {'ERROR_FORMATO', 'ERROR_TECNICO'}:
            result['state'] = classification['state']
            result['validation_errors'] = classification.get('validation_errors', [])
            result['execution_error'] = classification.get('execution_error')
            result['failure_stage'] = stage
            return result
        stage = 'retrieval'
        candidates, timings = retriever.retrieve(user_input)
        result['rag']['timings'].update(timings)
        result['rag']['candidates'] = [c.model_dump() for c in candidates]
        stage = 'context'
        begin = time.perf_counter()
        context = build_context(user_input, candidates, classification=result['classification'], max_chars=context_chars)
        result['rag']['timings']['context_seconds'] = time.perf_counter() - begin
        result['rag']['catalog'] = {label: c.model_dump() for label, c in context['catalog'].items()}
        result['rag']['omitted'] = context['omitted']
        result['rag']['context_chars'] = context['chars']
        result['rag']['context_budget_chars'] = context_chars
        result['rag']['context_budget_unit'] = context['budget_unit']
        result['user_content_sent'] = context['user_content']
        stage = 'generation'
        begin = time.perf_counter()
        if not context['catalog']:
            raw = {'estado': 'evidencia_insuficiente', 'respuesta': 'No se pudo incluir evidencia en el contexto.',
                   'citas': [], 'limitacion': 'El presupuesto excluyó los pasajes recuperados.'}
            result['rag']['generation_source'] = 'local_context_limit'
            result['model'] = None
        elif mode == 'mock':
            if documentary_fixture is None:
                raise ValueError('El modo mock requiere una respuesta documental explícita.')
            raw = documentary_fixture
            result['rag']['generation_source'] = 'explicit_mock_fixture'
        elif mode == 'groq':
            prompt = RAGConfig().prompt.read_text()
            result['rag']['prompt_sha256'] = hashlib.sha256(prompt.encode()).hexdigest()
            response = generator(prompt, context['user_content'], max_retries=0,
                                 model=model, response_format={'type': 'json_schema', 'json_schema': {
                                     'name': 'respuesta_rag', 'strict': True,
                                     'schema': RespuestaRAG.model_json_schema()}})
            raw = response['raw_output']
            result.update({key: response.get(key) for key in ('usage', 'metrics', 'http')})
            result['model'] = response.get('model', model)
            result['rag']['generation_source'] = 'groq'
        else:
            raise ValueError('Modo desconocido.')
        result['rag']['timings']['generation_seconds'] = time.perf_counter() - begin
        stage = 'validation'
        begin = time.perf_counter()
        result['raw_output'] = json.loads(raw) if isinstance(raw, str) else raw
        documentary = validate_response(raw, context['catalog'])
        result['documentary_output'] = documentary.model_dump()
        result['rag']['citations_valid'] = True
        result['rag']['timings']['validation_seconds'] = time.perf_counter() - begin
        # Preserve local classification policy independently of documentary coverage.
        local = result['classification_state']
        if local in {'OK_REQUIERE_HUMANO', 'OK_PIDE_ACLARACION'}:
            result['state'] = local
        else:
            result['state'] = {'respondida': 'OK_VALIDADO', 'parcial': 'OK_RESPUESTA_PARCIAL',
                               'aclaracion': 'OK_PIDE_ACLARACION',
                               'evidencia_insuficiente': 'OK_EVIDENCIA_INSUFICIENTE'}[documentary.estado]
    except (ValidationError, json.JSONDecodeError, ValueError) as error:
        result['state'] = 'ERROR_FORMATO' if stage == 'validation' else 'ERROR_TECNICO'
        result['failure_stage'] = stage
        if stage == 'validation':
            result['validation_errors'] = [str(error)] if type(error) is ValueError else ([e['msg'] for e in error.errors()] if isinstance(error, ValidationError) else ['JSON inválido.'])
        else:
            result['execution_error'] = f'{stage}: {type(error).__name__}'
    except Exception as error:
        result['state'] = 'ERROR_TECNICO'
        result['failure_stage'] = stage
        result['execution_error'] = f'{stage}: {type(error).__name__}'
    finally:
        result['latency_seconds'] = round(time.perf_counter() - started, 4)
    return result

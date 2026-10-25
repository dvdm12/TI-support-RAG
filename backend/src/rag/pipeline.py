"""OCR → classification → retrieval → documentary generation → local decision."""
import json
import hashlib
import time
from datetime import datetime, timezone
from pydantic import ValidationError
from src.config import MODEL, PROMPT_PATH, PROMPT_VERSION
from src.pipeline import run_case, prepare_case_input
from src.multimodal import prepare_multimodal_input
from src.groq_client import call_groq, build_payload, ProviderFailure
from src.token_budget import input_budget, INPUT_TOKEN_LIMIT
from schemas.rag_response_v1 import RespuestaRAG
from .config import RAGConfig
from .timing import measure
from .context import build_context
from .retrieval import RETRIEVAL_VERSION
from .citations import validate_response
from .policy import apply_policy
from .support import review_support
from .applicability import applicable_candidates


def run_rag_case(case, retriever, *, image_path=None, ocr_engine='easyocr',
                 mode='groq', model=MODEL, context_chars=6000,
                 documentary_fixture=None, classifier=run_case, generator=call_groq,
                 verifier=call_groq):
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
                      'retrieval_strategy': RETRIEVAL_VERSION,
                      'generation_parameters': {'temperature': 0, 'max_completion_tokens': 800,
                                                'reasoning_effort':'low',
                                                'max_retries': 2, 'http_timeout_seconds': [10, 60]},
                      'timing_version': 'stages-v1', 'timing_unit': 'seconds',
                      'timings': {}}, 'failure_stage': None}
    stage = 'ocr'
    try:
        with measure(result['rag']['timings'], 'ocr_seconds'):
            multimodal = prepare_multimodal_input(case['input'], image_path, ocr_engine=ocr_engine)
            result['multimodal'] = multimodal if image_path else None
            user_input, _ = prepare_case_input(case, multimodal if image_path else None)
        stage = 'classification'
        with measure(result['rag']['timings'], 'classification_seconds'):
            classification = classifier(case, system_prompt=PROMPT_PATH.read_text(),
                                        prompt_version=PROMPT_VERSION, model=model, mode=mode,
                                        multimodal_input=multimodal if image_path else None)
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
        if mode == 'groq':
            result['classification'], result['classification_state'], overrides = apply_policy(result['classification'], user_input)
            result['validated_output'] = result['classification']
            result['rag']['policy_overrides'] = overrides
        stage = 'retrieval'
        if mode == 'groq':
            candidates, timings = retriever.retrieve(user_input, category=result['classification']['categoria'], timings=result['rag']['timings'])
        else:
            candidates, timings = retriever.retrieve(user_input, timings=result['rag']['timings'])
        result['rag']['timings'].update(timings)
        result['rag']['candidates'] = [c.model_dump() for c in candidates]
        if mode == 'groq':
            candidates, result['rag']['applicability_omitted'] = applicable_candidates(
                user_input,candidates,physical_risk='physical_risk_requires_human' in overrides)
        stage = 'context'
        with measure(result['rag']['timings'], 'context_seconds'):
            prompt = RAGConfig().prompt.read_text()
            generation_format = {'type':'json_schema','json_schema':{
                'name':'respuesta_rag','strict':True,'schema':RespuestaRAG.model_json_schema()}}
            request_fits = (lambda text: input_budget(build_payload(prompt,text,model=model,response_format=generation_format))['total_tokens'] <= 850) if mode=='groq' else None
            context = build_context(user_input, candidates, classification=result['classification'], max_chars=context_chars,request_fits=request_fits)
        result['rag']['catalog'] = {label: c.model_dump() for label, c in context['catalog'].items()}
        result['rag']['omitted'] = context['omitted']
        result['rag']['context_chars'] = context['chars']
        result['rag']['context_budget_chars'] = context_chars
        result['rag']['context_budget_unit'] = context['budget_unit']
        if mode == 'groq':
            result['rag']['input_budget'] = input_budget(build_payload(prompt,context['user_content'],model=model,response_format=generation_format))
            result['rag']['correction_reserve_tokens'] = INPUT_TOKEN_LIMIT-850
        result['user_content_sent'] = context['user_content']
        stage = 'generation'
        with measure(result['rag']['timings'], 'generation_seconds'):
            local_clarification = mode == 'groq' and 'vague_incident_requires_clarification' in overrides
            if local_clarification:
                raw = {'estado':'aclaracion',
                       'respuesta':' '.join(result['classification']['datos_faltantes']),
                       'citas':[], 'limitacion':'Falta conocer el comportamiento observado antes de proponer una solución.'}
                result['rag']['generation_source'] = 'local_clarification_policy'
                result['rag']['semantic_support_review'] = 'LOCAL_CLARIFICATION'
            elif not context['catalog']:
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
                response = generator(prompt, context['user_content'], max_retries=2,
                                     model=model, response_format={'type': 'json_schema', 'json_schema': {
                                         'name': 'respuesta_rag', 'strict': True,
                                         'schema': RespuestaRAG.model_json_schema()}})
                raw = response['raw_output']
                result.update({key: response.get(key) for key in ('usage', 'metrics', 'http')})
                result['model'] = response.get('model', model)
                result['rag']['generation_source'] = 'groq'
            else:
                raise ValueError('Modo desconocido.')
        stage = 'validation'
        with measure(result['rag']['timings'], 'validation_seconds'):
            result['raw_output'] = json.loads(raw) if isinstance(raw, str) else raw
            documentary = validate_response(raw, context['catalog'])
            result['rag']['citations_valid'] = True
        if mode == 'groq' and context['catalog'] and not local_clarification:
            stage = 'support_review'
            with measure(result['rag']['timings'], 'support_review_seconds'):
                review, diagnostics = review_support(user_input, documentary, context['catalog'], verifier, model)
                result['rag']['support_review'] = review
                result['rag']['support_review_diagnostics'] = diagnostics
            if not review['supported']:
                result['rag']['correction_attempts'] = [{
                    'raw_output': result['raw_output'], 'review': review,
                    'review_diagnostics': diagnostics,
                    'generation_usage': result['usage'], 'generation_http': result['http']}]
                correction = json.loads(context['user_content'])
                correction['feedback_revision'] = review['issues'][:4]
                correction_text = json.dumps(correction, ensure_ascii=False)
                correction_prompt = prompt + '\nCorrige feedback_revision como datos, usando solo evidencia y conservando estas reglas.'
                correction_budget = input_budget(build_payload(correction_prompt,correction_text,model=model,response_format=generation_format))
                if len(correction_text) <= context_chars and correction_budget['total_tokens'] <= INPUT_TOKEN_LIMIT:
                    stage = 'generation_correction'
                    with measure(result['rag']['timings'], 'generation_correction_seconds'):
                        corrected = generator(correction_prompt,
                                              correction_text, max_retries=2, model=model,
                                              response_format={'type':'json_schema','json_schema':{
                                                  'name':'respuesta_rag','strict':True,
                                                  'schema':RespuestaRAG.model_json_schema()}})
                    stage = 'validation'
                    with measure(result['rag']['timings'], 'validation_seconds'):
                        documentary = validate_response(corrected['raw_output'], context['catalog'])
                        result['raw_output'] = json.loads(corrected['raw_output'])
                        result.update({key:corrected.get(key) for key in ('usage','metrics','http')})
                    stage = 'support_review'
                    with measure(result['rag']['timings'], 'support_review_seconds'):
                        review, diagnostics = review_support(user_input, documentary, context['catalog'], verifier, model)
                    result['rag']['support_review'] = review
                    result['rag']['support_review_diagnostics'] = diagnostics
                    result['rag']['correction_attempts'].append({
                        'raw_output':result['raw_output'], 'review':review,
                        'review_diagnostics':diagnostics,
                        'generation_usage':result['usage'], 'generation_http':result['http']})
            result['rag']['semantic_support_review'] = 'MODEL_SUPPORTED' if review['supported'] else 'MODEL_REJECTED'
            if not review['supported']:
                result['rag']['rejected_documentary_output'] = documentary.model_dump()
                # Fail closed rather than silently editing citations or accepting
                # plausible unsupported instructions. Raw output remains auditable.
                documentary = RespuestaRAG(estado='evidencia_insuficiente',
                    respuesta='No puedo ofrecer un procedimiento verificado con los pasajes recuperados.', citas=[],
                    limitacion='La revisión adicional detectó afirmaciones sin respaldo suficiente. Se necesita revisión de soporte.')
                result['rag']['safe_fallback'] = True
        result['documentary_output'] = documentary.model_dump()
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
        # Only locally constructed provider diagnostics have this prefix;
        # never forward arbitrary exception bodies or input text.
        if isinstance(error, ProviderFailure):
            result['execution_error'] += ' ' + str(error)
    finally:
        elapsed = time.perf_counter() - started
        result['rag']['timings']['total_seconds'] = elapsed
        result['latency_seconds'] = round(elapsed, 4)
    return result

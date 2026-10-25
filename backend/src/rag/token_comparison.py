"""Paired generation-token accounting; provider usage is never imputed."""
import json
import statistics
import time
from datetime import datetime, timezone
from src import groq_client
from src.rag.citations import validate_response
from src.token_budget import enforce_input_budget
from schemas.rag_response_v1 import RespuestaRAG

VARIANTS = ('A_semantic', 'B_hybrid_rrf')
TOKEN_KEYS = ('prompt_tokens', 'completion_tokens', 'total_tokens')


def response_format():
    return {'type':'json_schema','json_schema':{'name':'respuesta_rag','strict':True,
            'schema':RespuestaRAG.model_json_schema()}}


def valid_usage(usage):
    return (isinstance(usage,dict) and all(type(usage.get(k)) is int and usage[k]>=0 for k in TOKEN_KEYS)
            and usage['total_tokens']==usage['prompt_tokens']+usage['completion_tokens'])


def observe(prompt, context, catalog, model, session_factory=None):
    """One generation request, no hidden retries, retaining usage on invalid outputs."""
    payload=groq_client.build_payload(prompt,context,model=model,response_format=response_format())
    budget=enforce_input_budget(payload)
    result={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'status':'not_sent',
        'usage':None,'usage_valid':False,'model':None,'raw_output':None,'documentary_output':None,
        'validation_error':None,'http_status':None,'headers':{},'latency_seconds':None,
        'local_input_budget':budget,'transport_invoked':False}
    import requests
    session_factory=session_factory or requests.Session
    started=time.perf_counter()
    try:
        with session_factory() as http:
            http.headers.update(groq_client.build_headers())
            result['transport_invoked']=True
            response=groq_client.send_request(http,payload)
        result['http_status']=response.status_code
        result['headers']=groq_client.safe_headers(response)
        if not response.ok:
            result['status']='provider_error'
            return result  # Do not export arbitrary provider error bodies.
        data=response.json()
        result['usage']=groq_client.extract_usage(data)
        result['usage_valid']=valid_usage(result['usage'])
        result['model']=data.get('model')
        choice=data['choices'][0]
        result['finish_reason']=choice.get('finish_reason')
        result['raw_output']=choice['message'].get('content')
        if not result['usage_valid']:
            result['status']='invalid_usage'
        elif result['model']!=model:
            result['status']='model_mismatch'
        elif result['usage']['prompt_tokens']>1000:
            result['status']='provider_input_limit_exceeded'
        elif choice.get('finish_reason')!='stop' or choice['message'].get('refusal'):
            result['status']='incomplete_generation'
        else:
            try:
                result['documentary_output']=validate_response(result['raw_output'],catalog).model_dump()
                result['status']='contract_valid'
            except ValueError as error:
                result['status']='invalid_documentary'
                result['validation_error']=type(error).__name__
    except Exception as error:
        result['status']='transport_or_response_error'
        result['validation_error']=type(error).__name__
    finally:
        result['latency_seconds']=time.perf_counter()-started
    return result


def comparable(observation, model):
    return (observation is not None and observation['usage_valid']
            and observation['model']==model and observation['usage']['prompt_tokens']<=1000)


def summarize(report):
    rows=report['cases'];model=report['protocol']['model']
    paired=[r for r in rows if all(comparable(r['variants'][v]['observations'][-1],model)
            if r['variants'][v]['observations'] else False for v in VARIANTS)]
    summary={'planned_pairs':len(rows),'paired_measured_cases':len(paired),
             'paired_case_ids':[r['id'] for r in paired],'variants':{},'paired_difference':{}}
    for name in VARIANTS:
        samples=[r['variants'][name]['observations'][-1]['usage'] for r in paired]
        observations=[o for r in rows for o in r['variants'][name]['observations']]
        known=[o['usage'] for o in observations if o['usage_valid']]
        summary['variants'][name]={
            'paired_usage':{k:{'n':len(samples),'sum':sum(s[k] for s in samples) if samples else None,
                'mean':statistics.mean(s[k] for s in samples) if samples else None,
                'median':statistics.median(s[k] for s in samples) if samples else None} for k in TOKEN_KEYS},
            'observations':len(observations),'http_responses':sum(o['http_status'] is not None for o in observations),
            'all_observed_usage':{k:sum(s[k] for s in known) if known else None for k in TOKEN_KEYS},
            'observations_without_valid_usage':sum(not o['usage_valid'] for o in observations),
            'contract_valid_outputs':sum(o['status']=='contract_valid' for o in observations),
            'not_run_cases':[r['id'] for r in rows if not r['variants'][name]['observations']]}
    for key in TOKEN_KEYS:
        deltas=[r['variants'][VARIANTS[1]]['observations'][-1]['usage'][key]-
                r['variants'][VARIANTS[0]]['observations'][-1]['usage'][key] for r in paired]
        summary['paired_difference'][key]={'n':len(deltas),
            'mean':statistics.mean(deltas) if deltas else None,
            'sum':sum(deltas) if deltas else None}
    return summary

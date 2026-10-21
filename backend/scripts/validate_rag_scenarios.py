"""Real regression suite. No mocks, edited model replies or artificial pacing."""
import argparse
import csv
import json
from pathlib import Path
from src.rag.embeddings import SentenceEmbedder
from src.rag.index import load_index
from src.rag.repository import SupabaseRepository
from src.rag.retrieval import Retriever
from src.rag.pipeline import run_rag_case


def support_gate_passes(case, result):
    """An abstention test accepts a rejected answer only when safely replaced.

    Rejection is never accepted for cases that require a grounded procedure.
    Raw rejected output remains in the trace and is not the delivered answer.
    """
    rag=result['rag']; documentary=result.get('documentary_output') or {}
    if rag['semantic_support_review']=='MODEL_SUPPORTED':
        return True
    if rag['semantic_support_review']=='LOCAL_CLARIFICATION':
        return (case.get('expected_missing_data') is True
                and documentary.get('estado')=='aclaracion'
                and documentary.get('citas')==[]
                and documentary.get('respuesta')==' '.join((result.get('classification') or {}).get('datos_faltantes',[])))
    return (rag.get('safe_fallback') is True
            and 'evidencia_insuficiente' in case['expected_documentary_states']
            and documentary.get('estado')=='evidencia_insuficiente'
            and documentary.get('citas')==[]
            and documentary.get('respuesta')=='No puedo ofrecer un procedimiento verificado con los pasajes recuperados.')


def write_timings(path, results):
    """Blank cells mean an unexecuted stage, never zero-quality measurements."""
    stages=list(dict.fromkeys(key for row in results for key in row.get('timings',{})))
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['case_id','state','failure_stage','timing_version',*stages])
        writer.writeheader()
        for row in results:
            writer.writerow({'case_id':row['id'],'state':row['state'],
                             'failure_stage':row['failure_stage'],'timing_version':row.get('timing_version'),
                             **row.get('timings',{})})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cases',type=Path,default=Path('cases/rag_regression.json'))
    parser.add_argument('--output',type=Path,default=Path('docs/rag_runs/hardened_20261014'))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    _,_,_,config=load_index('data/indexes/sections')
    embedder=SentenceEmbedder(config.revision)
    corpus,_,_,config=load_index('data/indexes/sections',embedder)
    retriever=Retriever(SupabaseRepository.connect(),embedder,corpus,config)
    summary=[]
    cases=json.loads(args.cases.read_text())
    for position,case in enumerate(cases):
        result=run_rag_case(case,retriever,mode='groq')
        (args.output/f"{case['id']}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
        classification=result['classification'] or {}
        documentary=result['documentary_output'] or {}
        checks={'no_technical_or_format_error':result['state'] not in {'ERROR_FORMATO','ERROR_TECNICO'},
                'category':case['expected_category'] is None or classification.get('categoria')==case['expected_category'],
                'documentary_state':documentary.get('estado') in case['expected_documentary_states'],
                'references':result['rag']['citations_valid'],
                'support_gate':support_gate_passes(case,result),
                'human_escalation':'expected_human' not in case or classification.get('requiere_humano')==case['expected_human'],
                'clarification_data':'expected_missing_data' not in case or bool(classification.get('datos_faltantes')) == case['expected_missing_data'],
                'final_state':'expected_state' not in case or result['state']==case['expected_state'],
                'faithful_summary':not any(term.casefold() in classification.get('resumen','').casefold() for term in case.get('summary_excludes',[])),
                'expected_section':not case['expected_section'] or any(c['metadata']['section'].startswith(case['expected_section']+' ') for c in result['rag']['candidates'])}
        item={'id':case['id'],'passed':all(checks.values()),'checks':checks,'state':result['state'],
              'documentary_state':documentary.get('estado'),'category':classification.get('categoria'),
              'latency_seconds':result['latency_seconds'],'failure_stage':result['failure_stage'],
              'support_review':result['rag']['semantic_support_review'],
              'safe_fallback':result['rag'].get('safe_fallback',False),
              'timing_version':result['rag'].get('timing_version'),
              'timings':result['rag'].get('timings',{})}
        summary.append(item)
        (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
        write_timings(args.output/'timings.csv',summary)
        print(json.dumps(item,ensure_ascii=False),flush=True)
        if 'HTTP 429' in (result.get('execution_error') or ''):
            pending=[c['id'] for c in cases[position+1:]]
            (args.output/'run_status.json').write_text(json.dumps({
                'status':'blocked_provider_quota','planned':len(cases),
                'executed':len(summary),'pending_case_ids':pending},indent=2))
            print('Cuota bloqueada: no se envían los casos pendientes.',flush=True)
            break
    if len(summary)==len(cases):
        (args.output/'run_status.json').write_text(json.dumps({
            'status':'passed' if all(item['passed'] for item in summary) else 'failed',
            'planned':len(cases),'executed':len(summary),'pending_case_ids':[]},indent=2))
    if len(summary)!=len(cases) or not all(item['passed'] for item in summary):raise SystemExit(1)


if __name__=='__main__':main()

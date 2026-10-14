"""Real regression suite. No mocks, edited model replies or artificial pacing."""
import argparse
import json
from pathlib import Path
from src.rag.embeddings import SentenceEmbedder
from src.rag.index import load_index
from src.rag.repository import SupabaseRepository
from src.rag.retrieval import Retriever
from src.rag.pipeline import run_rag_case


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
                'model_support_review':result['rag']['semantic_support_review']=='MODEL_SUPPORTED',
                'human_escalation':'expected_human' not in case or classification.get('requiere_humano')==case['expected_human'],
                'expected_section':not case['expected_section'] or any(c['metadata']['section'].startswith(case['expected_section']+' ') for c in result['rag']['candidates'])}
        item={'id':case['id'],'passed':all(checks.values()),'checks':checks,'state':result['state'],
              'documentary_state':documentary.get('estado'),'category':classification.get('categoria'),
              'latency_seconds':result['latency_seconds'],'failure_stage':result['failure_stage']}
        summary.append(item)
        (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
        print(json.dumps(item,ensure_ascii=False),flush=True)
        if 'HTTP 429' in (result.get('execution_error') or ''):
            pending=[c['id'] for c in cases[position+1:]]
            (args.output/'run_status.json').write_text(json.dumps({
                'status':'blocked_provider_quota','planned':len(cases),
                'executed':len(summary),'pending_case_ids':pending},indent=2))
            print('Cuota bloqueada: no se envían los casos pendientes.',flush=True)
            break
    if len(summary)!=len(cases) or not all(item['passed'] for item in summary):raise SystemExit(1)


if __name__=='__main__':main()

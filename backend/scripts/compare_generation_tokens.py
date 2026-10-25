"""Measure actual Groq generation tokens on development only; always JSON/CSV/PDF."""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from src.config import MODEL
from src.rag.config import ROOT
from src.rag.models import Candidate
from src.rag.applicability import applicable_candidates
from src.rag.context import build_context
from src.rag.token_comparison import VARIANTS, TOKEN_KEYS, response_format, observe, summarize
from src.groq_client import build_payload
from src.token_budget import input_budget


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(source_path, annotations_path):
    raw=source_path.read_bytes();source=json.loads(raw)
    annotation_bytes=annotations_path.read_bytes();annotations=json.loads(annotation_bytes)
    prompt_path=ROOT/'prompts/rag_v6.md';prompt=prompt_path.read_text()
    if (annotations['schema_version']!='rag-evidence-v1' or source['backend']!='offline_replay'
            or source['annotations_sha256']!=digest(annotation_bytes)
            or source['code_sha256']['prompts/rag_v6.md']!=digest(prompt.encode())):
        raise ValueError('Fuentes de desarrollo o prompt distintos de los registrados.')
    catalog={ident:Candidate(chunk_id=ident,content=r['text'],
        metadata={k:v for k,v in r.items() if k not in ('chunk_id','text')},similitud=0)
        for ident,r in source['candidate_catalog'].items()}
    expected={c['id']:c for c in annotations['cases']}
    cases=[]
    for row in source['cases']:
        annotation=expected[row['id']]
        if row['question']!=annotation['question'] or annotation['split']!='development':
            raise ValueError('Pregunta distinta de desarrollo.')
        if not annotation['retrieval_evaluable']:
            continue
        sem=[catalog[x['chunk_id']] for x in source['recorded_semantic_rankings'][row['id']]]
        sem,_=applicable_candidates(row['question'],sem)
        hybrid=[catalog[i] for i in row['variants']['Después: híbrida v2']['selected_ids']]
        variants={}
        for name,selected in zip(VARIANTS,(sem[:3],hybrid)):
            fmt=response_format()
            fits=lambda text:input_budget(build_payload(prompt,text,model=MODEL,response_format=fmt))['total_tokens']<=850
            context=build_context(row['question'],selected,classification=None,request_fits=fits)
            variants[name]={'selected_ids':[c.chunk_id for c in selected],
                'context_ids':[c.chunk_id for c in context['catalog'].values()],
                'context':context['user_content'], 'catalog':{k:c.model_dump() for k,c in context['catalog'].items()},
                'local_input_budget':input_budget(build_payload(prompt,context['user_content'],model=MODEL,response_format=fmt)),
                'observations':[]}
        cases.append({'id':row['id'],'question':row['question'],'split':'development','variants':variants,
                      'human_review':{'status':'pending','reviewer':None,'notes':None}})
    if len(cases)!=len({c['id'] for c in cases}) or len(cases)!=sum(c['retrieval_evaluable'] for c in annotations['cases']):
        raise ValueError('Faltan preguntas documentales o hay duplicados.')
    return {'schema_version':'generation-token-comparison-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'not_started','source_filename':source_path.name,'source_sha256':digest(raw),
        'annotations_sha256':digest(annotation_bytes),'corpus_id':source['corpus_id'],
        'protocol':{'model':MODEL,'prompt_version':'rag_v6','prompt':prompt,'prompt_sha256':digest(prompt.encode()),
            'temperature':0,'reasoning_effort':'low','max_completion_tokens':800,
            'response_schema':response_format(),'response_schema_sha256':digest(json.dumps(response_format(),sort_keys=True).encode()),
            'context_budget_input_tokens':850,'generator_input_limit':1000,
            'k':3,'category_boost':False,'classifier_run':False,'applicability_before_top_k':'both variants',
            'sample':'all documentary development cases; behavior and reserve excluded',
            'scope':'one direct generation per variant/case; no classifier, support reviewer or corrective calls',
            'execution_order':'alternate A/B and B/A by case; no automatic retries',
            'usage':'Groq reported prompt/completion/total tokens. Completion may include internal reasoning. Local estimates stored separately; never imputed.',
            'aggregation':'same paired cases with valid reported usage/model; invalid documentary outputs still consume tokens and remain in accounting'},
        'cases':cases,'human_review_completed':False,'reserve_executed':False,
        'code_sha256':{name:digest((ROOT/name).read_bytes()) for name in (
            'src/rag/token_comparison.py','scripts/compare_generation_tokens.py','src/rag/context.py',
            'src/groq_client.py','src/token_budget.py','src/pdf_report.py')}}


def write_outputs(report, output):
    from src.pdf_report import PDFReport
    report['summary']=summarize(report)
    report['status']='complete' if report['summary']['paired_measured_cases']==len(report['cases']) else 'incomplete'
    report['updated_at_utc']=datetime.now(timezone.utc).isoformat()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    with output.with_suffix('.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['case','variant','observation','status',*TOKEN_KEYS,
            'usage_valid','http_status','contract_valid','local_input_estimate'],lineterminator='\n')
        writer.writeheader()
        for row in report['cases']:
            for name,v in row['variants'].items():
                for i,o in enumerate(v['observations'] or [None],1):
                    writer.writerow({'case':row['id'],'variant':name,'observation':i if o else None,
                        'status':o['status'] if o else 'not_run',**((o.get('usage') or {}) if o else {}),
                        'usage_valid':o['usage_valid'] if o else None,'http_status':o['http_status'] if o else None,
                        'contract_valid':o['status']=='contract_valid' if o else None,
                        'local_input_estimate':v['local_input_budget']['total_tokens']})
    return PDFReport(output.with_suffix('.pdf')).generate_token_comparison(report,source_json=output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'docs/coverage_improvements_20261021.json')
    parser.add_argument('--annotations',type=Path,default=ROOT/'cases/rag_evidence.json')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/generation_tokens_20261021.json')
    parser.add_argument('--resume',action='store_true',help='Continúa solo peticiones no realizadas o HTTP 429; conserva observaciones previas.')
    parser.add_argument('--from-json',type=Path,help='Reexporta JSON/CSV/PDF sin llamadas; requiere --output distinto de fuentes.')
    args=parser.parse_args()
    protected={args.source.resolve(),args.annotations.resolve()}
    if args.output.suffix!='.json' or args.output.resolve() in protected:
        raise ValueError('Usa una salida JSON distinta de las fuentes.')
    if args.from_json:
        report=json.loads(args.from_json.read_text())
        if report['schema_version']!='generation-token-comparison-v1':raise ValueError('Esquema desconocido.')
        print(write_outputs(report,args.output));return
    fresh=prepare(args.source,args.annotations)
    if args.output.exists():
        if not args.resume:raise ValueError('La salida ya existe: usa --resume o una ruta nueva.')
        report=json.loads(args.output.read_text())
        for key in ('schema_version','source_sha256','annotations_sha256','protocol','code_sha256'):
            if report[key]!=fresh[key]:raise ValueError('Cambió el protocolo o código: no mezclar ejecuciones.')
    else:
        report=fresh
    write_outputs(report,args.output)  # Initial checkpoint includes all planned calls.
    for i,row in enumerate(report['cases']):
        for name in (VARIANTS if i%2==0 else tuple(reversed(VARIANTS))):
            variant=row['variants'][name];previous=variant['observations']
            if previous and previous[-1]['http_status']!=429:
                continue
            result=observe(report['protocol']['prompt'],variant['context'],variant['catalog'],report['protocol']['model'])
            previous.append(result)
            write_outputs(report,args.output)
            print(json.dumps({'case':row['id'],'variant':name,'status':result['status'],'usage':result['usage']},ensure_ascii=False),flush=True)
            if result['status'] in ('provider_error','transport_or_response_error'):
                raise SystemExit('Ejecución interrumpida; evidencias JSON/CSV/PDF conservadas. Revisar diagnóstico antes de continuar.')
    print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
    if report['status']!='complete':raise SystemExit(1)


if __name__=='__main__':
    main()

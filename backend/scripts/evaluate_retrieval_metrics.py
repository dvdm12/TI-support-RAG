"""Paired semantic/hybrid development evaluation. No generation or DB writes."""
import argparse
import csv
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from scripts.validate_rag_evidence import validate, digest
from src.rag.config import ROOT, RAGConfig
from src.rag.index import load_index
from src.rag.embeddings import SentenceEmbedder
from src.rag.repository import LocalRepository, SupabaseRepository
from src.rag.retrieval import Retriever
from src.rag.lexical import rank, STOP
from src.rag.context import build_context
from src.rag.retrieval_metrics import metrics, coverage
from src.groq_client import build_payload
from src.token_budget import input_budget, encoding
from schemas.rag_response_v1 import RespuestaRAG

VARIANTS=('A_semantic','B_hybrid_rrf')


class CaptureRepository:
    """Read-only adapter retaining the exact shared lists and checking provenance."""
    def __init__(self, repository, chunks):
        self.repository=repository
        self.expected={c.chunk_id:c for c in chunks}
        self.semantic=[]; self.lexical_corpus=[]

    def check(self, candidates, *, full=False):
        ids=[c.chunk_id for c in candidates]
        if len(ids)!=len(set(ids)) or (full and set(ids)!=set(self.expected)):
            raise ValueError('Inventario autorizado distinto o duplicado.')
        for c in candidates:
            expected=self.expected[c.chunk_id]
            if c.content!=expected.text or c.metadata!=expected.model_dump(exclude={'chunk_id','text'}):
                raise ValueError('Texto o procedencia remotos distintos del índice anotado.')

    def search(self,*args):
        self.semantic=self.repository.search(*args)
        self.check(self.semantic)
        return self.semantic

    def lexical_candidates(self,*args):
        self.lexical_corpus=self.repository.lexical_candidates(*args)
        self.check(self.lexical_corpus,full=True)
        return self.lexical_corpus


def aggregate(rows):
    # Paired comparisons never silently use different successful subsets.
    eligible=[r for r in rows if r['retrieval_evaluable']]
    paired=[r for r in eligible if not r['error']]
    result={}
    for name in VARIANTS:
        samples=[r['variants'][name] for r in paired]
        means={key:statistics.mean(s['metrics_at_3'][key] for s in samples) if samples else None
               for key in ('precision','recall','hit','rr','coverage')}
        result[name]={'eligible_cases':len(eligible),'paired_valid_cases':len(paired),
                      'excluded_behavior_cases':sum(not r['retrieval_evaluable'] for r in rows),
                      'metrics_at_3':means,
                      'context_coverage_mean':statistics.mean(s['context_coverage'] for s in samples) if samples else None,
                      'candidate_coverage_mean':statistics.mean(s['candidate_coverage'] for s in samples) if samples else None,
                      'short_lists':sum(len(s['selected_ids'])<3 for s in samples),
                      'retrieval_seconds_median':statistics.median(s['retrieval_seconds'] for s in samples) if samples else None}
    return result


def evaluate_case(case, retriever, capture, fits):
    row={'id':case['id'],'question':case['question'],'split':case['split'],
         'family':case['family'],'retrieval_evaluable':case['retrieval_evaluable'],
         'relevant_ids':case['relevant_chunk_ids'],'units_count':len(case['required_information_units']),
         'error':None,'variants':{},'timings':{}}
    capture.semantic=[];capture.lexical_corpus=[]
    try:
        selected,t=retriever.retrieve(case['question'],category=None,timings=row['timings'])
        lexical=rank(case['question'],capture.lexical_corpus,10)  # Trace reconstruction, outside recorded retrieval time.
        sempos={c.chunk_id:i for i,c in enumerate(capture.semantic,1)}
        lexpos={c.chunk_id:i for i,c in enumerate(lexical,1)}
        fused=[]
        for ident in set(sempos)|set(lexpos):
            a=1/(60+sempos[ident]) if ident in sempos else 0
            b=1/(60+lexpos[ident]) if ident in lexpos else 0
            fused.append({'chunk_id':ident,'semantic_rank':sempos.get(ident),'bm25_rank':lexpos.get(ident),
                          'semantic_contribution':a,'bm25_contribution':b,'rrf_score':a+b})
        fused.sort(key=lambda r:(-r['rrf_score'],r['chunk_id']))
        if [r['chunk_id'] for r in fused[:3]]!=[c.chunk_id for c in selected]:
            raise ValueError('Traza RRF no coincide con el recuperador ejecutado.')
        row['semantic_ranking']=[{'chunk_id':c.chunk_id,'cosine':c.similitud} for c in capture.semantic]
        row['bm25_ranking']=[c.chunk_id for c in lexical]
        row['rrf_union']=fused
        row['union_coverage']=coverage([r['chunk_id'] for r in fused],case['required_information_units'])
        for name,candidates in zip(VARIANTS,(capture.semantic[:3],selected)):
            context=build_context(case['question'],candidates,classification=None,request_fits=fits)
            ids=[c.chunk_id for c in candidates]
            context_ids=[c.chunk_id for c in context['catalog'].values()]
            pool=list(sempos) if name=='A_semantic' else [r['chunk_id'] for r in fused]
            row['variants'][name]={'selected_ids':ids,'context_ids':context_ids,
                'context':context['user_content'],'omitted':context['omitted'],
                'metrics_at_3':metrics(ids,case['required_information_units']),
                'context_coverage':coverage(context_ids,case['required_information_units']),
                'candidate_coverage':coverage(pool,case['required_information_units']),
                'retrieval_seconds':t['embedding_seconds']+(t['semantic_search_seconds'] if name=='A_semantic' else t['retrieval_seconds'])}
    except Exception as error:
        # No arbitrary provider body or credentials in exported diagnostics.
        row['error']={'type':type(error).__name__,'stage':'retrieval_or_context'}
        row['variants']={}
    return row


def generate_pdf(report, json_path):
    from src.pdf_report import PDFReport
    return PDFReport(json_path.with_suffix('.pdf')).generate_retrieval_metrics(report, source_json=json_path)


def write_outputs(report, output):
    """Publish JSON, CSV and PDF for complete or partially failed evaluations."""
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    with output.with_suffix('.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['case','variant','eligible','technical_error','precision_at_3','recall_at_3','hit_at_3','rr_at_3','coverage_at_3','context_coverage','candidate_coverage','retrieval_seconds'])
        writer.writeheader()
        for row in report['cases']:
            for name in VARIANTS:
                v=row['variants'].get(name,{});m=v.get('metrics_at_3',{})
                writer.writerow({'case':row['id'],'variant':name,'eligible':row['retrieval_evaluable'],
                    'technical_error':bool(row['error']),**{key+'_at_3':m.get(key) for key in ('precision','recall','hit','rr','coverage')},
                    **{key:v.get(key) for key in ('context_coverage','candidate_coverage','retrieval_seconds')}})
    return generate_pdf(report,output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-json',type=Path,help='Generar solo el PDF desde una matriz guardada, sin modelos ni proveedores.')
    parser.add_argument('--backend',choices=('supabase','local'),default='supabase')
    parser.add_argument('--annotations',type=Path,default=ROOT/'cases/rag_evidence.json')
    parser.add_argument('--index',type=Path,default=ROOT/'data/indexes/sections')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/retrieval_metrics_20261021.json')
    args=parser.parse_args()
    if args.from_json is not None:
        print(generate_pdf(json.loads(args.from_json.read_text()),args.from_json))
        return
    validated=validate(args.annotations,args.index)
    data=json.loads(args.annotations.read_text())
    before={name:digest(args.index/name) for name in ('config.json','records.json','vectors.npy')}
    corpus,chunks,vectors,cfg=load_index(args.index)
    embedder=SentenceEmbedder(cfg.revision)
    load_index(args.index,embedder)
    if args.backend=='supabase':
        repository=SupabaseRepository.connect()
    else:
        repository=LocalRepository();repository.upsert(corpus,chunks,vectors,cfg)
    capture=CaptureRepository(repository,chunks)
    # Verify full authorized corpus before evaluating. No fallback to local data.
    capture.lexical_candidates(corpus,cfg)
    retriever=Retriever(capture,embedder,corpus,cfg)
    prompt=RAGConfig().prompt.read_text()
    response_format={'type':'json_schema','json_schema':{'name':'respuesta_rag','strict':True,'schema':RespuestaRAG.model_json_schema()}}
    fits=lambda text:input_budget(build_payload(prompt,text,response_format=response_format))['total_tokens']<=850
    # Model/tokenizer loading and compatibility checks excluded from observations.
    embedder.encode(['Calentamiento del modelo para evaluación.']);encoding()
    rows=[]
    for case in data['cases']:
        row=evaluate_case(case,retriever,capture,fits);rows.append(row)
        print(json.dumps({'id':row['id'],'eligible':row['retrieval_evaluable'],'error':row['error'],
                          'metrics':{k:v['metrics_at_3'] for k,v in row['variants'].items()}},ensure_ascii=False),flush=True)
    after={name:digest(args.index/name) for name in before}
    if before!=after:
        raise ValueError('El índice activo cambió durante la evaluación.')
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'status':'complete' if not any(r['error'] for r in rows) else 'incomplete_technical_errors',
        'scope':'Development retrieval metrics with agent annotations pending human review; no independent holdout, generation or behavioral scoring.',
        'backend':args.backend,'corpus_id':corpus,'records':len(chunks),'index_config':cfg.model_dump(),
        'annotation_validation':validated,'planned_cases':len(data['cases']),'executed_cases':len(rows),
        'technical_errors':sum(bool(r['error']) for r in rows),
        'protocol':{'k':3,'search_depth_per_branch':10,'rrf_constant':60,'weights':[1,1],
                    'category_boost':False,'classifier_run':False,'expected_category_used':False,
                    'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                    'context_budget_input_tokens':850,'context_chars':6000,'context_classification':None,
                    'applicability_filters_applied':False,
                    'timing':'One shared embedding and semantic search per case. A=embedding+semantic; B=embedding+full hybrid. Shared sequential observations, not independent latency benchmarks. Initialization/authentication and trace reconstruction excluded.',
                    'bm25':{'k1':1.5,'b':.75,'idf':'log(1+(N-df+.5)/(df+.5))','stopwords':sorted(STOP)},
                    'aggregation':'Macro means over the same paired successful eligible cases. RR mean is MRR@3. Behavior metrics null; errors excluded and counted explicitly.'},
        'aggregate':aggregate(rows),'cases':rows,
        'candidate_catalog':{c.chunk_id:c.model_dump() for c in chunks},
        'active_index_hashes':after,'active_index_unchanged':True,'supabase_writes':0,'groq_calls':0,
        'source_sha256':{name:digest(ROOT/name) for name in ('src/rag/retrieval.py','src/rag/lexical.py','src/rag/context.py','src/rag/retrieval_metrics.py','scripts/evaluate_retrieval_metrics.py','src/pdf_report.py')}}
    pdf=write_outputs(report,args.output)
    print(f'PDF: {pdf}',flush=True)
    print(json.dumps(report['aggregate'],ensure_ascii=False,indent=2))
    if report['technical_errors']:
        raise SystemExit(1)


if __name__=='__main__':
    main()

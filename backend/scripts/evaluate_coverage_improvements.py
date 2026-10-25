"""Offline development replay: historical hybrid vs current selection/context.

Reuses recorded semantic Top-10 results, not simulated semantic rankings. Real
pinned embeddings are used only for the current retriever's cosine bookkeeping.
No Supabase/Groq calls, generations, new reserve cases or latency comparison.
"""
import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from src.rag.config import ROOT, RAGConfig
from src.rag.index import load_index
from src.rag.embeddings import SentenceEmbedder
from src.rag.models import Candidate
from src.rag.retrieval import Retriever, RETRIEVAL_VERSION
from src.rag.context import build_context
from src.rag.retrieval_metrics import metrics, coverage
from src.rag.complete_coverage import details
from src.groq_client import build_payload
from src.token_budget import input_budget
from schemas.rag_response_v1 import RespuestaRAG
from scripts.evaluate_retrieval_metrics import aggregate, write_outputs

BEFORE = 'Antes: híbrida v1'
AFTER = 'Después: híbrida v2'


class RecordedSemanticRepository:
    """Replay recorded remote reads; do not label this as new Supabase timing."""
    def __init__(self, chunks):
        self.inventory = {c.chunk_id: Candidate(chunk_id=c.chunk_id,content=c.text,
            metadata=c.model_dump(exclude={'chunk_id','text'}),similitud=0) for c in chunks}
        self.row = None

    def search(self, corpus_id, vector, config, k):
        return [self.inventory[r['chunk_id']].model_copy(update={'similitud':r['cosine']})
                for r in self.row['semantic_ranking'][:k]]

    def lexical_candidates(self, corpus_id, config):
        return list(self.inventory.values())


def observation(question, selected, units, prompt):
    fmt={'type':'json_schema','json_schema':{'name':'respuesta_rag','strict':True,'schema':RespuestaRAG.model_json_schema()}}
    budget=lambda text:input_budget(build_payload(prompt,text,response_format=fmt))['total_tokens']
    context=build_context(question,selected,classification=None,request_fits=lambda text:budget(text)<=850)
    ids=[c.chunk_id for c in selected];context_ids=[c.chunk_id for c in context['catalog'].values()]
    return {'selected_ids':ids,'context_ids':context_ids,'context':context['user_content'],
        'omitted':context['omitted'],'metrics_at_3':metrics(ids,units),
        'context_coverage':coverage(context_ids,units),
        'coverage_completeness':{'top_3':details(ids,units),'context':details(context_ids,units)},
        'candidate_coverage':None,'retrieval_seconds':None,'generation_input_tokens':budget(context['user_content'])}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'docs/retrieval_metrics_20261021.json')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/coverage_improvements_20261021.json')
    args=parser.parse_args()
    if args.output.suffix!='.json' or args.output.resolve()==args.source.resolve():
        raise ValueError('Usa una salida JSON distinta del informe original.')
    source_bytes=args.source.read_bytes();source=json.loads(source_bytes)
    annotation_path=ROOT/'cases/rag_evidence.json';annotation_bytes=annotation_path.read_bytes()
    annotations=json.loads(annotation_bytes)
    digest=lambda b:hashlib.sha256(b).hexdigest()
    if digest(annotation_bytes)!=source['annotation_validation']['annotation_sha256']:
        raise ValueError('Las anotaciones cambiaron; no se comparan etiquetas nuevas.')
    corpus,chunks,_,cfg=load_index(ROOT/'data/indexes/sections')
    if (corpus!=source['corpus_id'] or digest((ROOT/'data/indexes/sections/records.json').read_bytes())
            !=source['active_index_hashes']['records.json']):
        raise ValueError('El índice difiere del usado para medir la base.')
    old_prompt=(ROOT/'prompts/rag_v5.md').read_text();new_prompt=RAGConfig().prompt.read_text()
    if digest(old_prompt.encode())!=source['protocol']['prompt_sha256']:
        raise ValueError('El prompt base cambió.')
    embedder=SentenceEmbedder(cfg.revision)
    repository=RecordedSemanticRepository(chunks)
    retriever=Retriever(repository,embedder,corpus,cfg)
    annotated={r['id']:r for r in annotations['cases']}
    if len(source['cases'])!=len(annotated) or {r['id'] for r in source['cases']}!=set(annotated):
        raise ValueError('Faltan casos de desarrollo.')
    rows=[];ablations={'context_only':[],'ranking_only':[]};empty_catalog={}
    for original in source['cases']:
        if original['error']:raise ValueError('La base contiene errores técnicos; resolver antes de comparar.')
        annotation=annotated[original['id']]
        if original['question']!=annotation['question'] or annotation['split']!='development':
            raise ValueError('Pregunta no perteneciente a desarrollo.')
        units=annotation['required_information_units'];question=original['question']
        repository.row=original
        selected,_=retriever.retrieve(question,category=None)
        old_ids=original['variants']['B_hybrid_rrf']['selected_ids']
        old_selected=[repository.inventory[i] for i in old_ids]
        baseline=observation(question,old_selected,units,old_prompt)
        if baseline['context_ids']!=original['variants']['B_hybrid_rrf']['context_ids']:
            raise ValueError('No se pudo reproducir el contexto histórico con el mismo presupuesto.')
        current=observation(question,selected,units,new_prompt)
        row={k:copy.deepcopy(original[k]) for k in ('id','question','split','family','retrieval_evaluable','relevant_ids','units_count')}
        row.update(error=None,variants={BEFORE:baseline,AFTER:current})
        rows.append(row)
        for name,selection,prompt in (('context_only',old_selected,new_prompt),('ranking_only',selected,old_prompt)):
            ablations[name].append({**row,'variants':{AFTER:observation(question,selection,units,prompt)}})
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status':'complete',
        'scope':'Development-only replay of saved semantic rankings; labels known during tuning; not independent validation or answer-quality measurement.',
        'backend':'offline_replay','corpus_id':corpus,'index_config':cfg.model_dump(),
        'active_index_hashes':source['active_index_hashes'],'planned_cases':len(rows),'executed_cases':len(rows),
        'annotation_validation':source['annotation_validation'],'technical_errors':0,
        'aggregate':aggregate(rows,variants=(BEFORE,AFTER)),'cases':rows,
        'candidate_catalog':source['candidate_catalog'],
        'recorded_semantic_rankings':{r['id']:r['semantic_ranking'] for r in source['cases']},
        'protocol':{'k':3,'search_depth_per_branch':10,'rrf_constant':60,'category_boost':False,
            'classifier_run':False,'context_budget_input_tokens':850,'context_chars':6000,
            'before':{'weights':[1,1],'prompt':'rag_v5','applicability_before_top_k':False},
            'after':{'weights':[1,2],'prompt':RAGConfig().prompt.stem,'applicability_before_top_k':True,
                     'retrieval_version':RETRIEVAL_VERSION},
            'timing':'No latency comparison. Stored semantic Top-10 reused, new lexical ranking and contexts computed locally. Historical times are not relabeled as current measurements.',
            'tuning':'Wi-Fi normalization, preselection applicability and lexical weight 2 selected using development only; reserve unopened.'},
        'ablations':{name:aggregate(values,variants=(AFTER,)) for name,values in ablations.items()},
        'source_sha256':digest(source_bytes),'annotations_sha256':digest(annotation_bytes),
        'provider_calls':0,'supabase_writes':0,'groq_calls':0,'reserve_executed':False,
        'code_sha256':{name:digest((ROOT/name).read_bytes()) for name in (
            'src/rag/retrieval.py','src/rag/lexical.py','src/rag/applicability.py','src/rag/context.py',
            'prompts/rag_v6.md','scripts/evaluate_coverage_improvements.py',
            'scripts/evaluate_retrieval_metrics.py','src/rag/complete_coverage.py','src/pdf_report.py')},
        'limitation':'Small known development set, human annotation review and reserve evaluation pending. Cannot infer unseen generalization, answer fidelity, new HTTP latency or generation token usage.'}
    pdf=write_outputs(report,args.output)
    print(json.dumps(report['aggregate'],ensure_ascii=False,indent=2));print(f'PDF: {pdf}')


if __name__=='__main__':
    main()

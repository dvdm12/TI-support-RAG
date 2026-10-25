"""Check frozen annotations against original PDFs and index, without searching."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from src.rag.config import ROOT
from src.rag.index import load_index
from src.rag.ingestion import load_corpus


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(path, index):
    data=json.loads(path.read_text())
    corpus,chunks,_,config=load_index(index)
    records={c.chunk_id:c.model_dump() for c in chunks}
    declared=data['corpus']; manifest=ROOT/'data/corpus/v2/manifest.json'
    require(data['schema_version']=='rag-evidence-v1','Versión de anotaciones desconocida.')
    require(declared['corpus_id']==corpus and declared['records_count']==len(records)
            and declared['index_config']==config.model_dump()
            and declared['index_records_sha256']==digest(index/'records.json'),'Índice distinto del anotado.')
    require(declared['manifest_path']=='data/corpus/v2/manifest.json'
            and declared['manifest_sha256']==digest(manifest),'Manifiesto distinto del anotado.')
    documents=json.loads(manifest.read_text())['documents']
    keys=('document_id','path','sha256','pages','simulated','version')
    require(declared['source_documents']==[{k:r[k] for k in keys} for r in documents],'Inventario de fuentes distinto.')
    sections=load_corpus(manifest)  # Checks PDF hashes and extracts original text.
    sources={(s.document_id,s.source,s.section):s for s in sections}
    for r in records.values():
        s=sources[(r['document_id'],r['source'],r['section'])]
        require(r['text'].split('\n',1)[1] in s.text and set(r['pages']).issubset(s.pages)
                and r['source_hash']==s.source_hash,'Fragmento distinto del PDF original.')
    questions=ROOT/'cases/rag_regression.json'
    require(data['question_source']=={'path':'cases/rag_regression.json','sha256':digest(questions)},'Suite original distinta.')
    originals={c['id']:c for c in json.loads(questions.read_text())}
    cases=data['cases']; catalog=data['evidence_catalog']; used=set(); units_count=0
    require(len({c['id'] for c in cases})==len(cases) and {c['id'] for c in cases}==set(originals),'Preguntas duplicadas o faltantes.')
    for ident,e in catalog.items():
        r=records[ident]
        require(all(e[k]==r[k] for k in e if k!='text_sha256') and e['text_sha256']==hashlib.sha256(r['text'].encode()).hexdigest(),'Catálogo distinto del índice.')
    def quote(e):
        ident=e['chunk_id'];text=records[ident]['text'];a,b=e['start_char'],e['end_char']
        require(ident in catalog and 0<=a<b<=len(text) and text[a:b]==e['quote'],'Cita o posición incorrecta.')
        used.add(ident)
    for case in cases:
        original=originals[case['id']]
        require(case['question']==original['input'] and case['type']==original['tipo']
                and case['expected_category']==original['expected_category']
                and case['expected_documentary_states']==original['expected_documentary_states'],'Se alteró una pregunta o expectativa original.')
        require(case['split']=='development' and case['previously_exercised'] is True,'Los casos conocidos no son reserva.')
        units=case['required_information_units'];relevant=set()
        require(len({u['id'] for u in units})==len(units),'Unidades duplicadas.')
        for u in units:
            require(u['statement'].strip() and u['support_mode']=='any' and u['evidence'],'Unidad vacía o sin respaldo.')
            for e in u['evidence']:
                quote(e);relevant.add(e['chunk_id'])
            units_count+=1
        require(sorted(relevant)==case['relevant_chunk_ids'] and case['retrieval_evaluable']==bool(units)
                and (units or case['non_evaluable_reason']),'Unión de relevantes o denominador incorrecto.')
        for e in case['behavior_policy_references']:
            quote(e)
        for e in case['related_but_non_relevant']:
            require(e['chunk_id'] in catalog and e['chunk_id'] not in relevant and e['reason'].strip(),'Exclusión incoherente.')
            used.add(e['chunk_id'])
        require(case['expected_answer'].strip() and case['conditions_to_preserve'] and case['failure_criteria'],'Caso sin expectativas completas.')
    require(used==set(catalog),'Evidencia no utilizada en el catálogo.')
    return {'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status':'source_integrity_validated',
            'annotation_sha256':digest(path),'annotation_status':data['annotation']['status'],
            'human_review_completed':data['annotation']['human_review_completed'],'corpus_id':corpus,
            'source_documents_verified':len(documents),'source_sections_verified':len(sections),
            'source_fragments_verified':len(records),'cases':len(cases),
            'retrieval_evaluable_cases':sum(c['retrieval_evaluable'] for c in cases),
            'behavior_only_cases':sum(not c['retrieval_evaluable'] for c in cases),
            'required_information_units':units_count,'catalog_entries':len(catalog),
            'development_cases':len(cases),'reserve_cases':0,'provider_calls':0,'retrieval_executed':False,
            'limitation':'Source/structure validation does not certify semantic completeness or replace human review. No retrieval metrics computed.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations',type=Path,default=ROOT/'cases/rag_evidence.json')
    parser.add_argument('--index',type=Path,default=ROOT/'data/indexes/sections')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/evaluacion/validaciones/rag_evidence_validation.json')
    args=parser.parse_args(); report=validate(args.annotations,args.index)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()

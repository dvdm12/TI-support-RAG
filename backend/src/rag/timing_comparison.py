"""Paired descriptive timing statistics; source observations remain untouched."""
import math
import statistics
from datetime import datetime, timezone

VARIANTS=('A_semantic','B_hybrid_rrf')
STAGES=('embedding_seconds','semantic_search_seconds','lexical_fetch_seconds',
        'bm25_seconds','rrf_seconds','candidate_scoring_seconds','coordination_seconds')


def stats(values):
    """P95 uses linear interpolation at (n-1)*0.95, even for a small sample."""
    if not values:
        return {key:(0 if key=='n' else None) for key in ('n','mean','median','p95','min','max','sum')}
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise ValueError('Las observaciones deben ser números finitos.')
    ordered=sorted(values); position=(len(ordered)-1)*.95
    lower=math.floor(position);upper=math.ceil(position)
    return {'n':len(values),'mean':statistics.mean(values),'median':statistics.median(values),
            'p95':ordered[lower]+(position-lower)*(ordered[upper]-ordered[lower]),
            'min':ordered[0],'max':ordered[-1],'sum':sum(values)}


def duration(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:
        raise ValueError('Duración ausente, negativa o no finita.')
    return value


def compare_case(case):
    raw=case.get('timings') or {}
    finite={key:value for key,value in raw.items() if type(value) in (int,float) and math.isfinite(value)}
    row={'id':case['id'],'question':case.get('question',''),
         'group':'documentary' if case['retrieval_evaluable'] else 'behavior',
         'status':'valid','error':None,'source_timings':finite,
         'non_numeric_or_non_finite_fields':[key for key in raw if key not in finite],
         'variants':{},'difference_seconds':None,'relative_change_percent':None}
    if case.get('error'):
        row.update(status='source_error',error=case['error'])
        return row
    try:
        t=case['timings'];d={name:duration(t[name]) for name in STAGES if name!='coordination_seconds'}
        retrieval=duration(t['retrieval_seconds'])
        residual=retrieval-sum(d[name] for name in STAGES[1:-1])
        if residual < -1e-9:
            raise ValueError('Las subetapas exceden su subtotal.')
        d['coordination_seconds']=max(0.0,residual)
        a=d['embedding_seconds']+d['semantic_search_seconds']
        b=d['embedding_seconds']+retrieval
        for name,total in zip(VARIANTS,(a,b)):
            recorded=duration(case['variants'][name]['retrieval_seconds'])
            if not math.isclose(total,recorded,rel_tol=1e-9,abs_tol=1e-9):
                raise ValueError('El total registrado no coincide con sus componentes.')
            row['variants'][name]={'total_seconds':total,'stages':{
                key:(value if name==VARIANTS[1] or key in STAGES[:2] else None) for key,value in d.items()}}
        row['difference_seconds']=b-a
        row['relative_change_percent']=100*(b-a)/a if a else None
    except (KeyError,TypeError,ValueError):
        row.update(status='invalid_timing_data',error={'type':'invalid_timing_data'},variants={})
    return row


def summarize(rows):
    valid=[r for r in rows if r['status']=='valid']
    return {'recorded_pairs':len(rows),'valid_pairs':len(valid),'excluded_pairs':len(rows)-len(valid),
            'variants':{name:{'total_seconds':stats([r['variants'][name]['total_seconds'] for r in valid]),
                'stage_seconds':{stage:stats([r['variants'][name]['stages'][stage] for r in valid
                    if r['variants'][name]['stages'][stage] is not None]) for stage in STAGES}} for name in VARIANTS},
            'paired_difference_seconds':stats([r['difference_seconds'] for r in valid]),
            'paired_relative_change_percent':stats([r['relative_change_percent'] for r in valid
                                                    if r['relative_change_percent'] is not None]),
            'zero_baseline_pairs':sum(r['variants'][VARIANTS[0]]['total_seconds']==0 for r in valid)}


def compare_timings(source):
    protocol=source['protocol']
    # These formulas apply only to the shared-component experiment, not arbitrary
    # independent HTTP runs or a pipeline with classification/reranking attached.
    if (protocol.get('k')!=3 or protocol.get('category_boost') is not False
            or protocol.get('classifier_run') is not False
            or source.get('backend') not in ('supabase','local')
            or any(name not in source['aggregate'] for name in VARIANTS)):
        raise ValueError('Protocolo de tiempos compartidos incompatible.')
    ids=[c['id'] for c in source['cases']]
    if not ids:
        raise ValueError('No hay mediciones para comparar.')
    if len(ids)!=len(set(ids)):
        raise ValueError('Casos duplicados; no se mezclan repeticiones sin identificarlas.')
    rows=[compare_case(case) for case in source['cases']]
    groups={'all':summarize(rows),
            **{key:summarize([r for r in rows if r['group']==key]) for key in ('documentary','behavior')}}
    return {'schema_version':'timing-comparison-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
            'status':'complete' if groups['all']['excluded_pairs']==0 and source.get('status')=='complete' and source.get('planned_cases',len(rows))==len(rows) else 'incomplete',
            'source_planned_cases':source.get('planned_cases',len(rows)),
            'source_recorded_cases':len(rows),
            'unit':'seconds','backend':source['backend'],'corpus_id':source['corpus_id'],
            'measurement_timestamp_utc':source['timestamp_utc'],
            'protocol':{'comparison':'Paired shared-component observations, not independent HTTP benchmark.',
                        'baseline':'embedding + semantic search',
                        'hybrid':'embedding + full hybrid retrieval subtotal',
                        'coordination':'Derived residual of retrieval subtotal minus measured leaves; never add subtotal twice.',
                        'relative_change':'100 * (B - A) / A for each valid pair; undefined when A=0.',
                        'p95':'Linear interpolation at (n-1)*0.95; descriptive small-sample statistic.',
                        'initialization':'Model loading, authentication and warm-up excluded by source protocol.',
                        'source_protocol':protocol,
                        'sample_design':'One observation per question, known development cases; no repeated-run or independent holdout claims.'},
            'groups':groups,'cases':rows,'provider_calls':0,
            'limitations':['Descriptive observations share embedding and semantic-search cost.',
                           'All valid cases count for timing, including behavior cases without relevance labels.',
                           'Failures and invalid timings are excluded as pairs, retained explicitly and never imputed as zero.',
                           'Stage medians and P95 are not additive. Quality metrics and human review are separate.']}

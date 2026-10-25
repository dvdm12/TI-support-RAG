"""All required information units must be covered; no providers or model calls."""
import copy
import math

STAGES = ('top_3', 'context')
VARIANTS = ('A_semantic', 'B_hybrid_rrf')


def details(ids, units):
    if len(set(ids)) != len(ids):
        raise ValueError('IDs duplicados en una etapa de cobertura.')
    unit_ids = [u['id'] for u in units]
    if len(set(unit_ids)) != len(unit_ids) or any(not u['evidence'] for u in units):
        raise ValueError('Unidades duplicadas o sin evidencia.')
    if not units:
        return {'complete': None, 'covered_units': None, 'total_units': 0,
                'missing_unit_ids': []}
    selected = set(ids)
    missing = [u['id'] for u in units if not any(e['chunk_id'] in selected for e in u['evidence'])]
    return {'complete': not missing, 'covered_units': len(units)-len(missing),
            'total_units': len(units), 'missing_unit_ids': missing}


def summarize(rows, variant):
    eligible = [r for r in rows if r['retrieval_evaluable']]
    valid = [r for r in eligible if not r['error']]
    summary = {}
    for stage in STAGES:
        complete, incomplete, unassessed = [], [], []
        for row in valid:
            value = row['variants'][variant].get('coverage_completeness', {}).get(stage, {}).get('complete')
            if value is True:
                complete.append(row['id'])
            elif value is False:
                incomplete.append(row['id'])
            else:
                unassessed.append(row['id'])
        n = len(complete)+len(incomplete)
        summary[stage] = {'eligible_cases': len(eligible), 'evaluated_cases': n,
            'complete_cases': len(complete), 'incomplete_cases': len(incomplete),
            'complete_rate': len(complete)/n if n else None,
            'complete_case_ids': complete, 'incomplete_case_ids': incomplete,
            'excluded_technical_cases': [r['id'] for r in eligible if r['error']],
            'unassessed_case_ids': unassessed,
            'excluded_behavior_cases': sum(not r['retrieval_evaluable'] for r in rows)}
    return summary


def enrich_saved_report(source, annotations):
    """Derive completeness from stored selected IDs and frozen source units.

    The caller verifies the annotation byte hash; this additionally rejects
    mismatched cases, units, fragment IDs and previously reported fractions.
    Historical quality/timing fields and source code hashes are preserved.
    """
    if annotations['schema_version'] != 'rag-evidence-v1':
        raise ValueError('Solo se admiten anotaciones de desarrollo validadas; no la reserva.')
    if (source['corpus_id'] != annotations['corpus']['corpus_id']
            or source['active_index_hashes']['records.json'] != annotations['corpus']['index_records_sha256']
            or source['protocol']['k'] != 3):
        raise ValueError('Corpus, índice o corte distintos de las anotaciones.')
    expected = {c['id']: c for c in annotations['cases']}
    ids = [r['id'] for r in source['cases']]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError('Preguntas duplicadas o distintas de las anotadas.')
    result = copy.deepcopy(source)
    catalog = set(source['candidate_catalog'])
    for row in result['cases']:
        case = expected[row['id']]
        units = case['required_information_units']
        if (row['question'] != case['question'] or row['split'] != 'development'
                or case['split'] != 'development' or row['retrieval_evaluable'] != bool(units)
                or row['units_count'] != len(units)
                or row['relevant_ids'] != case['relevant_chunk_ids']):
            raise ValueError('Pregunta, split, relevancia o unidades alteradas.')
        if row['error']:
            continue  # Failures are excluded, never classified as incomplete evidence.
        for name in VARIANTS:
            variant = row['variants'][name]
            if not set(variant['context_ids']).issubset(variant['selected_ids']):
                raise ValueError('El contexto contiene un fragmento no seleccionado.')
            stages = {}
            for stage, key in (('top_3', 'selected_ids'), ('context', 'context_ids')):
                selected = variant[key]
                if not set(selected).issubset(catalog) or (stage == 'top_3' and len(selected)>3):
                    raise ValueError('Fragmento desconocido o corte excedido.')
                detail = details(selected, units)
                observed = (variant['metrics_at_3']['coverage'] if stage == 'top_3'
                            else variant['context_coverage'])
                if units:
                    fraction = detail['covered_units']/detail['total_units']
                    if (type(observed) not in (float, int) or not math.isfinite(observed)
                            or not math.isclose(fraction, observed, abs_tol=1e-12, rel_tol=0)):
                        raise ValueError('La cobertura almacenada no coincide con las unidades y los IDs.')
                elif observed is not None:
                    raise ValueError('Un caso de comportamiento tiene cobertura documental.')
                stages[stage] = detail
            variant['coverage_completeness'] = stages
    for name in VARIANTS:
        result['aggregate'][name]['coverage_completeness'] = summarize(result['cases'], name)
    return result

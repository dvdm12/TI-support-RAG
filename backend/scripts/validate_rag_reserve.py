"""Validate reserve structure/provenance offline; never execute its questions."""
import argparse
import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold())
                   if c.isalnum())


def validate(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    require(data['schema_version'] == 'rag-reserve-v1', 'Esquema de reserva desconocido.')
    require(data['split'] == 'reserve_candidate', 'La estructura debe identificar candidatos de reserva.')
    corpus = data['corpus']
    index = ROOT / 'data/indexes/sections'
    require(digest(index / 'records.json') == corpus['index_records_sha256'], 'Cambió el índice.')
    config = json.loads((index / 'config.json').read_text())
    require(config['corpus_id'] == corpus['corpus_id'] and config['config'] == corpus['index_config'],
            'Cambió la configuración del índice.')
    manifest = ROOT / corpus['manifest_path']
    require(digest(manifest) == corpus['manifest_sha256'], 'Cambió el manifiesto.')
    documents = json.loads(manifest.read_text())['documents']
    keys = ('document_id', 'path', 'sha256', 'pages', 'simulated', 'version')
    require(corpus['source_documents'] == [{k: d[k] for k in keys} for d in documents],
            'Inventario declarado distinto del manifiesto.')
    for doc in documents:
        require(digest(manifest.parent / doc['path']) == doc['sha256'], 'Cambió un PDF fuente.')
    records = {r['chunk_id']: r for r in json.loads((index / 'records.json').read_text())}
    require(len(records) == corpus['records_count'], 'Cantidad de fragmentos distinta.')
    baseline = data['development_annotation']
    require(digest(ROOT / baseline['path']) == baseline['sha256'], 'Cambió la anotación de desarrollo.')
    dev = json.loads((ROOT / baseline['path']).read_text())
    prior = {normalize(c['question']) for c in dev['cases']}
    prior_ids = {c['id'] for c in dev['cases']}
    for source in data['prior_question_sources']:
        file = ROOT / source['path']
        require(digest(file) == source['sha256'], 'Cambió una fuente previa de preguntas.')
        for case in json.loads(file.read_text()):
            prior.add(normalize(case.get('question', case.get('input', ''))))
            prior_ids.add(case['id'])
    catalog = data['evidence_catalog']
    for ident, entry in catalog.items():
        require(ident in records, 'Referencia fuera del corpus.')
        record = records[ident]
        require({k: v for k, v in entry.items() if k != 'text_sha256'} == record
                and entry['text_sha256'] == hashlib.sha256(record['text'].encode()).hexdigest(),
                'Catálogo distinto del índice.')
    used = set()

    def quote(e):
        ident = e['chunk_id']
        require(ident in catalog, 'Cita fuera del catálogo.')
        text = records[ident]['text']
        a, b = e['start_char'], e['end_char']
        require(type(a) is int and type(b) is int and 0 <= a < b <= len(text)
                and text[a:b] == e['quote'], 'Cita o posición incorrecta.')
        used.add(ident)

    cases = data['cases']
    require(bool(cases) and len({c['id'] for c in cases}) == len(cases), 'IDs vacíos o duplicados.')
    questions = [normalize(c['question']) for c in cases]
    require(all(questions) and len(set(questions)) == len(cases), 'Preguntas vacías o duplicadas.')
    require(not set(questions) & prior, 'Pregunta ya presente en desarrollo.')
    require(not {c['id'] for c in cases} & prior_ids, 'IDs reutilizados de desarrollo.')
    for case in cases:
        require(case['split'] == 'reserve_candidate' and case['previously_exercised'] is False,
                'Caso no identificado como candidato sin ejecución previa.')
        require(case['family'].strip() and case['novelty_rationale'].strip()
                and case['conditions_to_preserve'] and case['failure_criteria']
                and case['expected_answer'].strip(), 'Expectativas o justificación incompletas.')
        require(case['expected_category'] in {'hardware', 'software', 'redes', 'cuentas', 'seguridad', 'acceso', 'otros'},
                'Categoría desconocida.')
        units = case['required_information_units']
        require(len({u['id'] for u in units}) == len(units), 'Unidades duplicadas.')
        relevant = set()
        for unit in units:
            require(unit['statement'].strip() and unit['support_mode'] == 'any' and unit['evidence'],
                    'Unidad sin contenido o evidencia.')
            for e in unit['evidence']:
                quote(e)
                relevant.add(e['chunk_id'])
        require(case['retrieval_evaluable'] == bool(units) and sorted(relevant) == case['relevant_chunk_ids'],
                'Denominador o unión de relevantes incorrectos.')
        require(case['type'] == ('documentary' if units else 'behavior'), 'Tipo incoherente.')
        require(bool(units) or (case['non_evaluable_reason'] and case['behavior_policy_references']),
                'Caso de límite sin justificación.')
        for e in case['behavior_policy_references']:
            quote(e)
        require(case['execution'] == {'status': 'not_run', 'first_run_at_utc': None, 'report_path': None},
                'La reserva ya tiene ejecución declarada: revisar exposición antes de continuar.')
    require(used == set(catalog), 'Catálogo con entradas no utilizadas.')
    require(data['protocol'] == {
        'retrieval_k': 3, 'candidate_k': 10, 'variants': ['A_semantic', 'B_hybrid_rrf'],
        'category_boost': False, 'classifier_for_retrieval': False,
        'behavior_cases_in_retrieval_metrics': False,
        'relevant_set': 'Union of required_information_units evidence IDs; behavior_policy_references excluded.',
        'human_review_required_before_freeze': True, 'freeze_before_first_execution': True,
        'selection_decision_required_before_first_execution': True, 'do_not_tune_on_reserve_results': True,
        'on_reuse_for_tuning': 'Retire affected cases to development, document exposure and author a new reserve; never relabel used questions as unseen.'},
        'Protocolo distinto del diseñado; revisar antes de validar.')
    blockers = []
    if not data['annotation']['human_review_completed'] or any(
            c['human_review']['status'] != 'approved' or not c['human_review']['reviewer']
            or not c['human_review']['reviewed_at_utc'] for c in cases):
        blockers.append('human_review_pending')
    release = data['release']
    if release['status'] != 'frozen' or not release['frozen_at_utc'] or not release['approved_by']:
        blockers.append('reserve_not_frozen')
    for label in ('selection_decision', 'configuration_snapshot'):
        name, expected = release[label + '_path'], release[label + '_sha256']
        if not name or not expected:
            blockers.append(label + '_missing')
        else:
            require(digest(ROOT / name) == expected, 'Cambió un documento de congelación.')
    require(release['first_execution_at_utc'] is None, 'Existe apertura declarada; revisar exposición.')
    return {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'structure_and_source_hashes_validated', 'reserve_sha256': digest(path),
            'cases': len(cases), 'documentary_cases': sum(c['retrieval_evaluable'] for c in cases),
            'behavior_cases': sum(not c['retrieval_evaluable'] for c in cases),
            'required_information_units': sum(len(c['required_information_units']) for c in cases),
            'catalog_entries': len(catalog), 'source_documents_verified': len(documents),
            'ready_for_first_execution': not blockers, 'blockers': blockers,
            'retrieval_executed': False, 'provider_calls': 0,
            'limitation': 'Validates structure, exact duplicates, source hashes and quotes against the index; not semantic novelty, annotation completeness, human approval authenticity or absence of undeclared runs.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reserve', type=Path, default=ROOT / 'cases/rag_reserve.json')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--require-ready', action='store_true', help='Falla si falta revisión/congelación; nunca ejecuta preguntas.')
    args = parser.parse_args()
    report = validate(args.reserve)
    if args.output:
        require(args.output.resolve() != args.reserve.resolve(), 'No reemplazar la reserva con el informe.')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.require_ready and not report['ready_for_first_execution']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

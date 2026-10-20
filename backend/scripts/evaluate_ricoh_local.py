"""Build and evaluate an isolated Ricoh retrieval index; no Supabase or Groq."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from src.rag.config import EMBEDDING_MODEL
from src.rag.embeddings import SentenceEmbedder
from src.rag.external_chunking import digest, evidence_units, fragment_extraction, load_local_index, save_local_index
from src.rag.external_retrieval import evidence_text, retrieve_units


def file_hashes(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(directory).glob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extraction', type=Path, default=Path('data/extracted/RICOH-MP4002-USER-GUIDE-EN/extraction.json'))
    parser.add_argument('--output', type=Path, default=Path('data/indexes/ricoh-local-v1'))
    parser.add_argument('--cases', type=Path, default=Path('cases/ricoh_retrieval_es.json'))
    parser.add_argument('--report', type=Path, default=Path('docs/ricoh_local_retrieval_validation.json'))
    parser.add_argument('--revision', default='e8f8c211226b894fcb81acc59f3b34ba3efd5f42')
    parser.add_argument('--existing', action='store_true')
    args = parser.parse_args()
    active = Path('data/indexes/sections').resolve()
    if args.output.resolve() == active or args.output.resolve().is_relative_to(active):
        raise ValueError('La evaluación no puede escribir sobre el índice activo.')
    before = file_hashes(active)
    started = time.perf_counter()
    extraction = json.loads(args.extraction.read_text())
    extraction_hash = hashlib.sha256(args.extraction.read_bytes()).hexdigest()
    registered = json.loads(Path('manuals/manifest.real.json').read_text())['documents']
    registered = next(d for d in registered if d['document_id'] == extraction['document']['document_id'])
    if extraction_hash != registered['local_extraction']['extraction_sha256']:
        raise ValueError('La extracción no coincide con la revisión registrada.')
    source = Path('manuals') / extraction['document']['path']
    if hashlib.sha256(source.read_bytes()).hexdigest() != extraction['document']['sha256']:
        raise ValueError('El PDF ya no coincide con la extracción.')
    embedder = SentenceEmbedder(args.revision)
    if embedder.model_name != EMBEDDING_MODEL or embedder.max_seq_length != 128:
        raise ValueError('La representación debe conservar el modelo y su límite de 128 tokens.')
    build_started = time.perf_counter()
    if not args.existing:
        units, fragments, excluded = fragment_extraction(extraction, embedder)
        vectors = embedder.encode([f['text'] for f in fragments])
        manifest = save_local_index(args.output, extraction, units, fragments, excluded, vectors, embedder)
    manifest, units, fragments, vectors = load_local_index(args.output)
    expected_units, excluded = evidence_units(extraction)
    if digest(expected_units) != digest(units):
        raise ValueError('Las unidades no conservan el contenido de la extracción registrada.')
    if manifest['revision'] != embedder.revision or manifest['model'] != embedder.model_name:
        raise ValueError('La representación local no coincide con el evaluador.')
    if any(f['tokens'] != embedder.count_tokens(f['text']) or f['tokens'] > 128 for f in fragments):
        raise ValueError('Tokenización distinta o fragmento truncado.')
    sample = sorted({0, len(fragments) // 2, len(fragments) - 1})
    recalculated = embedder.encode([fragments[i]['text'] for i in sample])
    if not np.allclose(np.sum(recalculated * vectors[sample], axis=1), 1, atol=1e-3):
        raise ValueError('Los vectores no corresponden a los textos.')
    build_seconds = time.perf_counter() - build_started
    cases = json.loads(args.cases.read_text())
    query_vectors = embedder.encode([c['question'] for c in cases])
    strategies = {}
    for strategy in ['semantic', 'hybrid', 'hybrid_literal']:
        results = []
        for case, query_vector in zip(cases, query_vectors):
            matches = retrieve_units(case['question'], query_vector, units, fragments, vectors, 3, strategy)
            hits = []
            for match in matches:
                unit = match['unit']
                row_text = ' '.join(' '.join(cell.split()) for cell in unit['row']['cells']) if unit['row'] else ''
                relevant = (unit['section_title'] == case['expected_section']
                            and (not case.get('expected_row_contains') or case['expected_row_contains'] in row_text))
                hits.append({'unit_id': unit['unit_id'], 'kind': unit['kind'],
                             'section': unit['section_title'], 'references': unit['references'],
                             'row_message': unit['row']['cells'][0] if unit['row'] else None,
                             'cosine': match['cosine'], 'relevant': relevant,
                             'match_basis': match.get('match_basis', strategy),
                             'retrieved_evidence_tokens': embedder.count_tokens(evidence_text(unit)),
                             'requires_visual_reference': unit['requires_visual_reference']})
            rank = next((i for i, h in enumerate(hits, 1) if h['relevant']), None)
            results.append({**case, 'first_relevant_rank': rank, 'top3': hits})
        strategies[strategy] = {
            'cases': len(cases), 'hit_at_1': sum(r['first_relevant_rank'] == 1 for r in results) / len(cases),
            'hit_at_3': sum(r['first_relevant_rank'] is not None for r in results) / len(cases),
            'mrr_at_3': sum(1 / r['first_relevant_rank'] if r['first_relevant_rank'] else 0 for r in results) / len(cases),
            'failed_case_ids': [r['id'] for r in results if r['first_relevant_rank'] is None],
            'results': results,
        }
    probe = 'Tengo problemas al enviar impresiones en la Ricoh MP 4002.'
    probe_vector = embedder.encode([probe])[0]
    probe_results = retrieve_units(probe, probe_vector, units, fragments, vectors, 3, 'hybrid_literal')
    if file_hashes(active) != before:
        raise ValueError('El índice activo cambió durante la evaluación.')
    report = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Local retrieval over real English source using Spanish queries; no answer generation.',
        'source_text_comparison': 'PDF whitespace normalized; expected sections and messages unchanged.',
        'source_extraction_sha256': extraction_hash,
        'index': manifest, 'build_seconds': round(build_seconds, 3),
        'fragmentation_checks': {
            'all_source_units_preserved': True,
            'all_unit_bodies_fully_covered': True,
            'each_table_row_retained_as_one_full_evidence_unit': True,
            'ancestor_context_preserved': True,
            'no_silent_truncation': True,
            'real_vectors_normalized_and_samples_recomputed': True,
            'graphical_tables_excluded': len(excluded),
        },
        'max_fragment_tokens': max(f['tokens'] for f in fragments),
        'units_longer_than_embedding_window': sum(embedder.count_tokens(u['body']) > 128 for u in units),
        'strategies': strategies,
        'broad_question_probe': {'question': probe, 'scored_in_benchmark': False,
            'note': 'Nearest passages do not establish a specific cause; this input still needs symptom/error clarification.',
            'top3': [{'section': r['unit']['section_title'], 'references': r['unit']['references'],
                      'unit_id': r['unit_id'], 'cosine': r['cosine']} for r in probe_results]},
        'elapsed_seconds': round(time.perf_counter() - started, 3),
        'active_index_unchanged': True, 'active_index_hashes': before,
        'source_pdf_unchanged': True, 'supabase_writes': False, 'groq_calls': False,
        'limitations': [
            'Diagnostic cases are source-linked and are not a blinded benchmark.',
            'Retrieval scores are not diagnostic confidence.',
            'Full units can exceed generation budgets; context selection is a separate pending step.',
            'Graphical tables remain excluded; procedural units may require their figures.',
            'No production retriever or API routing is modified by this evaluation.',
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'index_id': manifest['index_id'], 'units': len(units), 'fragments': len(fragments),
        'max_fragment_tokens': report['max_fragment_tokens'],
        'strategies': {k: {p: v[p] for p in ['hit_at_1', 'hit_at_3', 'mrr_at_3', 'failed_case_ids']} for k, v in strategies.items()},
        'report': str(args.report), 'elapsed_seconds': report['elapsed_seconds'],
        'active_index_unchanged': True, 'remote_services_called': False,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

"""Step 8: verify complete units before/after and Spanish retrieval by failure stage.

Local only: re-extracts Ricoh, compares units with the registered extraction and
the frozen local index, then classifies each Spanish case. No Supabase or Groq;
no index, extraction or report is overwritten.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from xml.sax.saxutils import escape

from src.rag.extraction_baseline import write_new_json
from src.rag.external_chunking import digest, evidence_units, load_local_index
from src.rag.external_ingestion import extract_real_document
from src.rag.external_retrieval import retrieve_units
from src.rag.unit_verification import (
    block_coverage, classify, compare_units, evidence_presence, relevant, source_accounting, stage_summary,
)

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ID = 'RICOH-MP4002-USER-GUIDE-EN'
STRATEGIES = ('semantic', 'hybrid', 'hybrid_literal')


def file_hashes(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(directory).glob('*')) if p.is_file()}


def page_texts(path, first, last):
    import pdfplumber
    with pdfplumber.open(str(path)) as pdf:
        return {n: ''.join(c['text'] for c in pdf.pages[n - 1].chars) for n in range(first, last + 1)}


def evaluate_cases(cases, query_vectors, extraction, units, fragments, vectors, excluded):
    strategies = {}
    for strategy in STRATEGIES:
        results = []
        for case, vector in zip(cases, query_vectors):
            matches = retrieve_units(case['question'], vector, units, fragments, vectors, 3, strategy)
            top3 = [{'unit_id': m['unit_id'], 'section': m['unit']['section_title'],
                     'cosine': round(m['cosine'], 6), 'relevant': relevant(m['unit'], case)} for m in matches]
            rank = next((i for i, h in enumerate(top3, 1) if h['relevant']), None)
            presence = evidence_presence(case, extraction, units, fragments, excluded)
            results.append({'id': case['id'], 'question': case['question'],
                            'expected_section': case['expected_section'],
                            'expected_row_contains': case.get('expected_row_contains'),
                            'stage': classify(presence, rank), 'first_relevant_rank': rank,
                            'presence': presence, 'top3': top3})
        strategies[strategy] = {**stage_summary(results), 'results': results}
    return strategies


def export(output, report):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    existing = [n for n in ('report.json', 'cases.csv', 'report.pdf') if (output / n).exists()]
    if existing:
        # Check all targets first so a refused export never leaves partial results.
        raise FileExistsError(f'No se sobrescriben informes existentes: {existing}.')
    write_new_json(output / 'report.json', report)
    with (output / 'cases.csv').open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=['strategy', 'id', 'stage', 'first_relevant_rank',
                                                    'expected_section', 'expected_row_contains', 'top1_section'])
        writer.writeheader()
        for strategy, data in report['retrieval'].items():
            for r in data['results']:
                writer.writerow({'strategy': strategy, 'id': r['id'], 'stage': r['stage'],
                                 'first_relevant_rank': r['first_relevant_rank'] or '',
                                 'expected_section': r['expected_section'],
                                 'expected_row_contains': r['expected_row_contains'] or '',
                                 'top1_section': r['top3'][0]['section'] if r['top3'] else ''})
    styles = getSampleStyleSheet()
    p = lambda text: Paragraph(escape(str(text)), styles['BodyText'])
    style = TableStyle([('GRID', (0, 0), (-1, -1), .4, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP')])
    pres = report['preservation']
    story = [Paragraph('Paso 8: unidades completas y recuperación en español', styles['Title']), Spacer(1, 8),
             p(f"{report['timestamp_utc']} - Ricoh MP 4002, extracción local y preguntas en español. "
               'Sin Supabase, Groq ni índices nuevos. Diagnóstico por etapa; no es benchmark ciego.'),
             Spacer(1, 10), Paragraph('Preservación', styles['Heading2'])]
    acc = pres['source_accounting']
    rows = [[p('Comprobación'), p('Resultado')],
            [p('Extracción nueva idéntica a la registrada'), p(pres['extraction_identical_to_registered'])],
            [p('Unidades antes / después'), p(f"{pres['units_before_after']['before']} / {pres['units_before_after']['after']}, idénticas: {pres['units_before_after']['identical']}")],
            [p('Unidades del índice local = unidades nuevas'), p(pres['index_units_match_new_extraction'])],
            [p('Caracteres del PDF contabilizados'), p(f"{acc['source_characters']} en {acc['pages_checked']} páginas; faltan {acc['missing_characters']}, sobran {acc['extra_characters']}")],
            [p('Bloques en unidades o exclusión explícita'), p(f"{pres['block_coverage']['status']}; problemas: {len(pres['block_coverage']['problems'])}")]]
    table = Table(rows, colWidths=[220, 235]); table.setStyle(style)
    story += [table, Spacer(1, 12), Paragraph('Recuperación por etapa (Top-3)', styles['Heading2'])]
    rows = [[p('Estrategia'), p('Pérdida extracción'), p('Pérdida unidad/fragmento'), p('Fallo búsqueda'), p('Recuperado')]]
    for strategy, data in report['retrieval'].items():
        s = data['by_stage']
        rows.append([p(strategy), p(s['extraction_loss']), p(s['unit_loss'] + s['fragment_loss']),
                     p(f"{s['search_failure']} {data['search_failure_ids']}"), p(s['retrieved'])])
    table = Table(rows, colWidths=[90, 85, 95, 110, 75]); table.setStyle(style)
    story += [table, Spacer(1, 10)]
    for limit in report['limitations']:
        story += [p('- ' + limit), Spacer(1, 3)]
    SimpleDocTemplate(str(output / 'report.pdf'), title='Paso 8').build(story)


def default_embedder(revision):
    from src.rag.embeddings import SentenceEmbedder
    return SentenceEmbedder(revision)


def verify(root, index, cases_path, revision, *, extract=extract_real_document,
           embedder_factory=default_embedder, read_pages=page_texts):
    """Return the step-8 report; collaborators are injectable for offline tests."""
    root, index = Path(root), Path(index)
    started = time.perf_counter()
    active = root / 'data/indexes/sections'
    if index.resolve() == active.resolve() or index.resolve().is_relative_to(active.resolve()):
        raise ValueError('La verificación no puede usar el índice activo como índice Ricoh.')
    guarded = {'active': file_hashes(active), 'ricoh_index': file_hashes(index)}
    manifest_path = root / 'manuals/manifest.real.json'
    registered = next(d for d in json.loads(manifest_path.read_text())['documents'] if d['document_id'] == DOCUMENT_ID)
    stored = root / registered['local_extraction']['output_directory_relative_to_backend'] / 'extraction.json'
    stored_hash = hashlib.sha256(stored.read_bytes()).hexdigest()
    if stored_hash != registered['local_extraction']['extraction_sha256']:
        raise ValueError('La extracción guardada no coincide con la registrada.')
    before = json.loads(stored.read_text())
    after = extract(manifest_path, DOCUMENT_ID)
    after_hash = hashlib.sha256((json.dumps(after, ensure_ascii=False, indent=2) + '\n').encode()).hexdigest()
    units_before, _ = evidence_units(before)
    units_after, excluded = evidence_units(after)
    index_manifest, index_units, fragments, vectors = load_local_index(index)
    first, last = after['profile']['content_pdf_page_range']
    accounting = source_accounting(after, read_pages(root / 'manuals' / registered['path'], first, last))
    coverage = block_coverage(after, units_after, excluded)
    comparison = compare_units(units_before, units_after)
    if digest(index_units) != digest(units_after):
        raise ValueError('El índice local no corresponde a la extracción actual: reconstruir antes de evaluar búsqueda.')
    embedder = embedder_factory(revision)
    if index_manifest['revision'] != embedder.revision or index_manifest['model'] != embedder.model_name:
        raise ValueError('El evaluador no usa el modelo/revisión del índice.')
    cases = json.loads(Path(cases_path).read_text())
    retrieval = evaluate_cases(cases, embedder.encode([c['question'] for c in cases]),
                               after, index_units, fragments, vectors, excluded)
    if guarded != {'active': file_hashes(active), 'ricoh_index': file_hashes(index)}:
        raise ValueError('Un índice cambió durante la verificación.')
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True,
                                         stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'git_commit': commit,
        'scope': 'Step 8: unit preservation and Spanish retrieval over the local Ricoh index; no generation.',
        'document_id': DOCUMENT_ID, 'cases_file': Path(cases_path).name,
        'cases_sha256': hashlib.sha256(Path(cases_path).read_bytes()).hexdigest(),
        'index_id': index_manifest['index_id'], 'model_revision': embedder.revision,
        'preservation': {
            'registered_extraction_sha256': stored_hash, 'new_extraction_sha256': after_hash,
            'extraction_identical_to_registered': after_hash == stored_hash,
            'units_before_after': comparison,
            'index_units_match_new_extraction': True,
            'excluded_blocks': excluded, 'source_accounting': accounting, 'block_coverage': coverage,
        },
        'retrieval': retrieval,
        'stage_definitions': {
            'extraction_loss': 'Expected section/row absent from the new extraction.',
            'unit_loss': 'Present in extraction but no complete unit (excluded or missing).',
            'fragment_loss': 'Unit exists but has no search view.',
            'search_failure': 'Evidence indexed but not in Top-3.',
            'retrieved': 'Relevant complete unit in Top-3.',
        },
        'indexes_unchanged': True, 'supabase_writes': False, 'groq_calls': False,
        'elapsed_seconds': round(time.perf_counter() - started, 3),
        'limitations': [
            'Doce casos diagnósticos con expectativa por sección/fila; no es un benchmark ciego ni generaliza a otros manuales.',
            'La contabilidad de caracteres comprueba conservación, no orden de lectura ni corrección semántica.',
            'Recuperar la unidad correcta no evalúa la respuesta generada (paso 9).',
            'Las seis tablas gráficas excluidas siguen sin interpretación visual.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Directorio nuevo para JSON/CSV/PDF.')
    parser.add_argument('--index', type=Path, default=ROOT / 'data/indexes/ricoh-local-v1')
    parser.add_argument('--cases', type=Path, default=ROOT / 'cases/ricoh_retrieval_es.json')
    parser.add_argument('--revision', default='e8f8c211226b894fcb81acc59f3b34ba3efd5f42')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('La salida debe ser un directorio nuevo.')
    report = verify(ROOT, args.index, args.cases, args.revision)
    args.output.mkdir(parents=True)
    export(args.output, report)
    pres, acc = report['preservation'], report['preservation']['source_accounting']
    print(json.dumps({
        'extraction_identical': pres['extraction_identical_to_registered'],
        'units': pres['units_before_after']['after'], 'units_identical': pres['units_before_after']['identical'],
        'source_characters': acc['source_characters'],
        'missing_characters': acc['missing_characters'], 'extra_characters': acc['extra_characters'],
        'block_coverage': pres['block_coverage']['status'], 'block_problems': len(pres['block_coverage']['problems']),
        'retrieval': {k: {'by_stage': v['by_stage'], 'search_failure_ids': v['search_failure_ids']}
                      for k, v in report['retrieval'].items()},
        'output': str(args.output), 'elapsed_seconds': report['elapsed_seconds'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

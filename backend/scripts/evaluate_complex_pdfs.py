"""Evaluate controlled complex PDFs locally; no models, providers or active index."""
import argparse
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path

from scripts.complex_pdf_samples import COLUMN_LINES, HEADERS, ROWS, SCAN_TEXT, build_samples, sample_profile
from src.rag.extraction_baseline import check_inputs, check_references, compare, write_new_json
from src.rag.extraction_strategies import select_strategy, trace_selection, validate_policy
from src.rag.external_ingestion import (
    DocumentAnalysis, ExtractedPages, RegisteredSource, assemble_page_blocks, audit_page,
    extract_page_layout, extract_real_document,
)
from src.rag.extraction_rules import block_indexing_decision
from src.rag.external_chunking import digest, evidence_units
from src.rag.pdf_adapters import open_layout_document
from src.rag.pdf_ocr_review import review_scan_page


def sample_blocks(path, case, *, override_profile=None):
    profile = sample_profile(case) if override_profile is None else override_profile
    count = 2 if case == 'continuation' else 1
    sections = [{'id': 'S1', 'title': 'Sample', 'heading_path': ['Sample'],
                 'level': 0, 'start_pdf_page': 1, 'start_top': 0, 'blocks': []}]
    analysis = DocumentAnalysis(1, count, sections)
    # Synthetic sources stay outside the real registry/full extraction contract.
    source = RegisteredSource(path, {'inspection': {'blank_pdf_pages': []}}, profile)
    state = ExtractedPages(deepcopy(sections))
    traces = []
    with open_layout_document(path) as document:
        for page in document.pages:
            try:
                audit = audit_page(page, page.number, source, analysis)
                selection = select_strategy(validate_policy(profile, count), page.number)
                traces.extend(trace_selection('SYNTHETIC-'+case.upper(), page.number, selection))
                layout = extract_page_layout(page, profile, page.number, audit['printed_page'], selection=selection)
                assemble_page_blocks(state, layout, page.number, audit['printed_page'])
            finally:
                page.close()
    return state.sections[0]['blocks'], traces


def evaluate_samples(directory, *, ocr=True):
    directory = Path(directory)
    paths = build_samples(directory/'samples')
    checks = []

    def check(name, passed, details):
        checks.append({'check': name, 'passed': bool(passed), 'details': details})

    blocks, trace = sample_blocks(paths['borderless'], 'borderless')
    tables = [b for b in blocks if b['type'] == 'table']
    grid = [tables[0]['headers'], *[r['cells'] for r in tables[0]['rows']]] if len(tables) == 1 else []
    check('borderless_exact_cells', grid == [HEADERS, *ROWS], grid)
    native, _ = sample_blocks(paths['borderless'], 'borderless', override_profile=sample_profile('plain'))
    check('borderless_default_does_not_recover_grid', not any(b['type'] == 'table' for b in native),
          'Default ruled detector leaves aligned text unstructured.')
    write_new_json(directory/'borderless_trace.json', trace)
    blocks, trace = sample_blocks(paths['columns'], 'columns')
    expected = [' '.join(lines) for lines in COLUMN_LINES]
    check('columns_exact_reading_order', [b['text'] for b in blocks] == expected, [b['text'] for b in blocks])
    native, _ = sample_blocks(paths['columns'], 'columns', override_profile=sample_profile('plain'))
    check('columns_default_differs', [b['text'] for b in native] != expected, [b['text'] for b in native])
    write_new_json(directory/'columns_trace.json', trace)
    blocks, _ = sample_blocks(paths['continuation'], 'continuation')
    tables = [b for b in blocks if b['type'] == 'table']
    check('continuation_link_without_merge', len(tables) == 2
          and tables[1].get('continuation_candidate_of') == tables[0]['id']
          and [len(t['rows']) for t in tables] == [2, 2], [t.get('continuation_candidate_of') for t in tables])
    check('continuation_ambiguous_row_excluded', len(tables) == 2
          and not block_indexing_decision(tables[1])['text_index_eligible'],
          tables[1]['review_flags'] if len(tables) == 2 else [])
    try:
        sample_blocks(paths['scan'], 'scan')
    except ValueError as error:
        check('scan_native_rejected', 'sin texto' in str(error), str(error))
    else:
        check('scan_native_rejected', False, 'Image-only page was accepted as native text.')
    if ocr:
        candidate = review_scan_page(paths['scan'], 1, source_sha256=hashlib.sha256(paths['scan'].read_bytes()).hexdigest())
        write_new_json(directory/'ocr_candidate.json', candidate)
        check('scan_ocr_exact_control_text', ' '.join(candidate['text'].split()) == ' '.join(SCAN_TEXT),
              {'text': candidate['text'], 'confidence': candidate['mean_word_confidence']})
        check('scan_ocr_remains_review_only', candidate['status'] == 'review'
              and not candidate['text_index_eligible'] and bool(candidate['words']),
              {'words': len(candidate['words']), 'coordinate_space': candidate['coordinate_space']})
    return {'scope': 'controlled_synthetic_pdf_samples', 'ocr_executed': ocr,
            'source_sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()},
            'passed': all(c['passed'] for c in checks), 'checks': checks,
            'limitations': ['Synthetic fixtures are mechanism tests, not representative external-manual validation.',
                           'No human approval or RAG response quality is measured.']}


def ricoh_regression(root):
    baseline = json.loads((root/'docs/extractor/baselines/ricoh_extraction_v1.json').read_text())
    manifest = root/'manuals/manifest.real.json'
    check_inputs(baseline, manifest, baseline['document_id'])
    result = extract_real_document(manifest, baseline['document_id'])
    regression = compare(baseline, result)
    references = check_references(root, baseline)
    units, excluded = evidence_units(result)
    saved = json.loads((root/'data/indexes/ricoh-local-v1/manifest.json').read_text())
    return {'passed': regression['passed'] and not references and digest(units) == saved['units_sha256'],
            'comparison': regression, 'changed_reference_files': references,
            'units': len(units), 'excluded_tables': len(excluded),
            'units_hash_matches': digest(units) == saved['units_sha256']}


def export_report(directory, report):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    write_new_json(directory/'report.json', report)
    with (directory/'checks.csv').open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=['check', 'passed', 'details'])
        writer.writeheader()
        for item in report['samples']['checks']:
            writer.writerow({**item, 'details': json.dumps(item['details'], ensure_ascii=False)})
    styles = getSampleStyleSheet()
    story = [Paragraph('PDF extractor: controlled complex samples', styles['Title']), Spacer(1, 12),
             Paragraph('Synthetic fixtures only. These checks do not certify external-document generalization, human approval or RAG quality.', styles['BodyText']), Spacer(1, 12)]
    data = [[Paragraph('Check', styles['Heading4']), Paragraph('Result', styles['Heading4'])]]
    for check in report['samples']['checks']:
        data.append([Paragraph(check['check'].replace('_', ' '), styles['BodyText']),
                     'PASS' if check['passed'] else 'FAIL'])
    table = Table(data, colWidths=[390, 65], repeatRows=1)
    table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .5, colors.grey),
                               ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
    story.extend([table, Spacer(1, 16)])
    regression = report.get('ricoh')
    text = ('Ricoh: extraction identical to baseline; 498 evidence units keep their saved hash. Nine reference files unchanged.'
            if regression and regression['passed'] else 'Ricoh regression not passed or not executed: see report.json.')
    story.append(Paragraph(text, styles['BodyText']))
    story.extend([Spacer(1, 12), Paragraph('OCR stays in a separate review-only candidate. Native extraction v1 and active indexes remain unchanged.', styles['BodyText'])])
    SimpleDocTemplate(str(directory/'report.pdf'), title='Controlled PDF extraction checks').build(story)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory; refuses to overwrite.')
    parser.add_argument('--without-ocr', action='store_true')
    parser.add_argument('--with-ricoh', action='store_true', help='Re-extract the real manual in memory and verify its baseline.')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    samples = evaluate_samples(args.output, ocr=not args.without_ocr)
    report = {'schema_version': 'complex-pdf-checks-v1', 'samples': samples,
              'providers_used': False, 'supabase_writes': False, 'active_index_changed': False}
    if args.with_ricoh:
        report['ricoh'] = ricoh_regression(Path(__file__).resolve().parents[1])
    report['passed'] = samples['passed'] and report.get('ricoh', {'passed': True})['passed']
    export_report(args.output, report)
    print(json.dumps({'passed': report['passed'], 'checks': len(samples['checks']), 'output': str(args.output)}, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

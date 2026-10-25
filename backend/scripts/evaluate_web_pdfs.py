"""Offline checks of hash-pinned public PDFs; separate component and pipeline results."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from xml.sax.saxutils import escape

from scripts.complex_pdf_samples import profile as base_profile
from scripts.evaluate_complex_pdfs import ricoh_regression
from src.rag.extraction_baseline import write_new_json
from src.rag.extraction_strategies import (
    BorderlessTableStrategy, ColumnTextStrategy, ExtractionStrategies, RegionRule, StrategySelection,
)
from src.rag.external_ingestion import extract_real_document, table_block
from src.rag.pdf_adapters import open_layout_document
from src.rag.pdf_ocr_review import review_scan_page


def tokens(text):
    return re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold())


def word_error(reference, hypothesis):
    """Unit-cost word Levenshtein distance; descriptive, without a quality threshold."""
    expected, actual = tokens(reference), tokens(hypothesis)
    if not expected:
        raise ValueError('Referencia vacía: no calcular WER sin denominador.')
    previous = list(range(len(actual)+1))
    for i, word in enumerate(expected, 1):
        current = [i]
        for j, candidate in enumerate(actual, 1):
            current.append(min(previous[j]+1, current[j-1]+1, previous[j-1]+(word != candidate)))
        previous = current
    matched = sum((Counter(expected) & Counter(actual)).values())
    return {'reference_tokens': len(expected), 'hypothesis_tokens': len(actual),
            'word_edit_distance': previous[-1], 'word_error_rate': previous[-1]/len(expected),
            'matched_token_multiplicity': matched,
            'order_insensitive_token_recall': matched/len(expected),
            'order_insensitive_token_precision': matched/len(actual) if actual else 0.0,
            'normalization': 'Unicode NFKC, casefold, Unicode word tokens; punctuation ignored.',
            'interpretation': 'Agreement with upstream transcript; not human-certified semantic accuracy.'}


def character_agreement(native, extracted):
    raw = [Counter(c for c in text if not c.isspace()) for text in (native, extracted)]
    normalized = [Counter(c for c in unicodedata.normalize('NFKC', text) if not c.isspace())
                  for text in (native, extracted)]
    expected, actual = normalized
    return {'equivalent': expected == actual, 'normalization': 'Unicode NFKC; whitespace ignored; case and digits preserved.',
            'native_raw_nonspace_characters': sum(raw[0].values()),
            'output_raw_nonspace_characters': sum(raw[1].values()),
            'raw_missing_characters': dict(raw[0]-raw[1]), 'raw_extra_characters': dict(raw[1]-raw[0]),
            'native_normalized_characters': sum(expected.values()),
            'output_normalized_characters': sum(actual.values()),
            'missing': sum((expected-actual).values()), 'extra': sum((actual-expected).values())}


def verify_sources(directory, config):
    paths = {}
    for source in [*config['sources'], config['ocr_reference']]:
        if 'id' in source and not re.fullmatch(r'[a-z0-9_-]+', source['id']):
            raise ValueError('Identificador de muestra pública inválido.')
        path = (directory/source['file']).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError('La fuente debe permanecer en el directorio de pruebas.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('La fuente pública cambió: ' + source['file'])
        if 'id' in source:
            paths[source['id']] = path
    return paths


def pipeline_attempt(path, source, output):
    profile = base_profile()
    profile.update(content_pdf_page_range=[1, source['pages']], running_header_bottom=0,
                   running_header_max_font_size=0, right_sidebar_x0=10000, footer_height=40)
    document = {'document_id': 'WEB-TEST-'+source['id'].upper(), 'path': 'sources/'+source['file'],
                'sha256': source['sha256'], 'version': source['sha256'][:12],
                'language': 'en', 'simulated': False, 'pages': source['pages'],
                'size_bytes': source['bytes'], 'inspection': {'blank_pdf_pages': []},
                'extraction_profile': profile, 'provenance': {'url': source['url'],
                    'scope': 'Isolated compatibility probe; profile not approved for ingestion.'}}
    # A private probe registry only: keep PDF bytes unchanged and use the same
    # source confinement rules as production. No outline is fabricated.
    probe = output/('pipeline-'+source['id'])
    (probe/'sources').mkdir(parents=True, exist_ok=False)
    (probe/'sources'/source['file']).write_bytes(path.read_bytes())
    manifest = probe/'manifest.json'
    write_new_json(manifest, {'documents': [document]})
    try:
        result = extract_real_document(manifest, document['document_id'])
    except Exception as error:
        return {'id': source['id'], 'supported': False, 'status': 'blocked',
                'error_type': type(error).__name__, 'reason': str(error),
                'stages': getattr(error, '__notes__', []), 'partial_result_accepted': False}
    write_new_json(probe/'candidate_extraction.json', result)
    return {'id': source['id'], 'supported': True, 'status': 'structurally_extracted',
            'semantic_approval': False, 'index_created': False}


def evaluate(directory, config, output):
    paths = verify_sources(directory, config)
    sources = {s['id']: s for s in config['sources']}
    checks = []
    artifacts = {}

    def check(name, passed, detail):
        checks.append({'check': name, 'passed': bool(passed), 'details': detail})

    with open_layout_document(paths['health']) as document:
        page = next(iter(document.pages))
        try:
            defaults = [table_block(t, 1, 23) for t in page.tables()]
            check('health_merged_headers_remain_nonindexable', bool(defaults)
                  and all(b and not b['text_index_eligible'] for b in defaults),
                  [{'columns': len(b['headers']), 'rows': len(b['rows']), 'review_flags': b['review_flags']}
                   for b in defaults if b])
            settings = config['health_probe']
            table = BorderlessTableStrategy().extract(page.region(tuple(settings['bbox'])), {}, settings=settings['settings'])[0]
            check('health_sampled_24_data_cells_match', table.grid == settings['expected_grid'],
                  {'data_rows': len(table.grid), 'columns': table.column_count,
                   'scope': settings['interpretation']})
            artifacts['health_grid_probe'] = {'source_sha256': sources['health']['sha256'],
                'pdf_page': 1, 'grid': table.grid, 'bbox': table.bbox,
                'text_index_eligible': False, 'reason': 'Multi-level headers excluded from probe; unresolved.'}
        finally:
            page.close()

    with open_layout_document(paths['bert']) as document:
        for page in document.pages:
            try:
                if page.number != config['bert_columns']['pdf_page']:
                    continue
                settings = config['bert_columns']
                body = page.select(lambda c: c.get('object_type') != 'char'
                                   or settings['body_top'] <= c['top'] < settings['body_bottom'])
                lines = ColumnTextStrategy().extract(body, columns=tuple(settings['columns']))
                groups = [[line for line in lines if line['_column_order'] == i] for i in (0, 1)]
                anchors = [[group[0]['text'], group[-1]['text']] for group in groups]
                check('bert_column_start_end_anchors_match', anchors == settings['anchors'],
                      {'lines': [len(group) for group in groups], 'scope': settings['interpretation']})
                agreement = character_agreement(''.join(c['text'] for c in body.characters),
                                                ''.join(line['text'] for line in lines))
                check('bert_all_body_characters_preserved', agreement['equivalent'], agreement)
                ordinary = body.lines(x_tolerance=2, y_tolerance=3)
                check('bert_default_merges_columns', ordinary[0]['text'] != lines[0]['text'],
                      'Default first line mixes left/right; explicit strategy changes reading order.')
                artifacts['bert_column_probe'] = {'pdf_page': page.number, 'columns': settings['columns'],
                    'lines': lines, 'section_mapping_approved': False, 'text_index_eligible': False}
            finally:
                page.close()

    with open_layout_document(paths['attention']) as document:
        for page in document.pages:
            try:
                if page.number != 8:
                    continue
                region = RegionRule(bbox=[130, 96, 480, 242], tables='borderless_tables',
                    reason='Negative probe: hierarchical header crosses simple column boundaries.', settings={
                        'vertical_strategy': 'explicit', 'horizontal_strategy': 'explicit',
                        'explicit_vertical_lines': [130, 280, 325, 365, 430, 480],
                        'explicit_horizontal_lines': [96, 124, 136, 147, 159, 170.5, 181, 193, 204.5, 217, 229, 242]})
                try:
                    ExtractionStrategies().table_snapshots(page, {}, StrategySelection(
                        'native_text', 'ruled_tables', 'Negative probe', (region,)))
                except ValueError as error:
                    check('attention_hierarchical_cells_not_forced_flat', 'columna única' in str(error), str(error))
                else:
                    check('attention_hierarchical_cells_not_forced_flat', False, 'Complex header accepted by simple-cell profile.')
            finally:
                page.close()

    reference = (directory/config['ocr_reference']['file']).read_text()
    ocr_results = []
    for name in ('scan', 'skew', 'rotated'):
        candidate = review_scan_page(paths[name], 1, source_sha256=sources[name]['sha256'])
        write_new_json(output/(name+'_ocr_candidate.json'), candidate)
        metric = word_error(reference, candidate['text'])
        ocr_results.append({'id': name, 'mean_word_confidence': candidate['mean_word_confidence'],
                            'word_agreement': metric, 'text_index_eligible': candidate['text_index_eligible']})
        check(name+'_ocr_review_only', candidate['status'] == 'review' and not candidate['text_index_eligible']
              and bool(candidate['words']), {'words': len(candidate['words']), 'confidence': candidate['mean_word_confidence']})
    for name, value in artifacts.items():
        write_new_json(output/(name+'.json'), value)
    pipeline = [pipeline_attempt(paths[s['id']], s, output) for s in config['sources']]
    verify_sources(directory, config)
    return {'checks': checks, 'component_checks_passed': all(c['passed'] for c in checks),
            'ocr_results': ocr_results, 'pipeline': pipeline,
            'whole_document_supported': sum(p['supported'] for p in pipeline),
            'whole_document_attempted': len(pipeline), 'semantic_approval': False,
            'indexing_approval': False, 'reference_scope': config['ocr_reference']['reference_kind']}


def export(output, report):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    write_new_json(output/'report.json', report)
    fields = ['kind', 'id', 'outcome', 'details']
    with (output/'checks.csv').open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in report['evaluation']['checks']:
            writer.writerow({'kind': 'component_check', 'id': row['check'], 'outcome': row['passed'],
                             'details': json.dumps(row['details'], ensure_ascii=False)})
        for row in report['evaluation']['pipeline']:
            writer.writerow({'kind': 'whole_document', 'id': row['id'], 'outcome': row['status'],
                             'details': row.get('reason', '')})
        for row in report['evaluation']['ocr_results']:
            writer.writerow({'kind': 'ocr_word_agreement', 'id': row['id'], 'outcome': row['word_agreement']['word_error_rate'],
                             'details': json.dumps(row, ensure_ascii=False)})
    styles = getSampleStyleSheet()
    p = lambda text: Paragraph(escape(str(text)), styles['BodyText'])
    story = [Paragraph('Pruebas con PDF públicos', styles['Title']), Spacer(1, 10),
             p('24-10-2026 - Fuentes originales sin modificar. Evaluación local por componentes y compatibilidad del pipeline, separadas. Sin Supabase, embeddings ni índice nuevo.'), Spacer(1, 12)]
    evaluation = report['evaluation']
    story += [p(f"Documentos completos con el perfil genérico de prueba: {evaluation['whole_document_supported']} de {evaluation['whole_document_attempted']}. Requieren perfiles revisados; los controles de rechazo correctos no equivalen a soporte documental."), Spacer(1, 12)]
    data = [[p('Comprobación técnica'), p('Resultado')]]
    data += [[p(c['check']), p('Correcta' if c['passed'] else 'Fallo')] for c in evaluation['checks']]
    table = Table(data, colWidths=[360, 95], repeatRows=1)
    table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .4, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    story += [table, Spacer(1, 14), Paragraph('OCR: acuerdo con transcripción externa', styles['Heading2'])]
    for result in evaluation['ocr_results']:
        metric = result['word_agreement']
        story += [p(f"{result['id']}: confianza media {result['mean_word_confidence']:.2f}; WER {metric['word_error_rate']:.2%} ({metric['word_edit_distance']} ediciones / {metric['reference_tokens']} palabras de referencia); recuperación de tokens sin considerar orden {metric['order_insensitive_token_recall']:.2%}."), Spacer(1, 5)]
    story += [p('WER descriptivo: normalización NFKC, minúsculas y tokens de palabras; sin umbral de aprobación. La referencia de OCRmyPDF contiene artefactos y no es una anotación humana nueva. Confianza del motor no equivale a exactitud. Candidatos OCR siempre en revisión y no indexables.'), Spacer(1, 12),
              Paragraph('Límites del pipeline completo', styles['Heading2'])]
    for result in evaluation['pipeline']:
        story += [p(result['id']+': '+result.get('reason', result['status'])), Spacer(1, 5)]
    story += [Spacer(1, 10), Paragraph('Procedencia', styles['Heading2'])]
    for source in report['sources']:
        story += [p(source['id']+' - '+source['landing_page']), Spacer(1, 5)]
    if report.get('ricoh'):
        story += [Spacer(1, 12), p('Regresión Ricoh: '+('correcta; extracción idéntica, 498 unidades y referencias intactas.' if report['ricoh']['passed'] else 'FALLO; consultar JSON.'))]
    SimpleDocTemplate(str(output/'report.pdf'), title='Pruebas con PDF públicos').build(story)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=Path('docs/extractor/fixtures/web_pdf_sources_v1.json'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--with-ricoh', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 'public-pdf-evaluation-v1', 'local_date': '2026-10-24',
              'sources': config['sources'], 'source_rights': config['source_rights'],
              'evaluation': evaluate(args.sources, config, args.output),
              'production_code_changed': False, 'supabase_writes': False, 'active_index_changed': False,
              'human_review_performed': False}
    if args.with_ricoh:
        report['ricoh'] = ricoh_regression(Path(__file__).resolve().parents[1])
    export(args.output, report)
    print(json.dumps({'components_passed': report['evaluation']['component_checks_passed'],
                      'whole_document_supported': report['evaluation']['whole_document_supported'],
                      'whole_document_attempted': report['evaluation']['whole_document_attempted'],
                      'ocr': report['evaluation']['ocr_results'], 'ricoh_passed': report.get('ricoh', {}).get('passed')}, indent=2))
    if not report['evaluation']['component_checks_passed'] or report.get('ricoh', {}).get('passed') is False:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

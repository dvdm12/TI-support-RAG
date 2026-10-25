"""Local, reviewable PDF extraction; independent of the simulated RAG corpus.

No embeddings, provider clients or database operations are used here. Outline
destinations define section boundaries; ruled tables remain structured grids.
Layout exclusions are explicit, source-hash-bound manifest configuration.
"""
import hashlib
import json
import re
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from .extraction_contracts import validate_extraction
from .extraction_rules import render_block_text, table_review_flags
from .extraction_validation import ExtractionValidationError, evaluate_extraction
from .pdf_adapters import (
    DEFAULT_BACKENDS, PDFBackends, layout_page, structure_document, table_snapshot,
)
from .extraction_strategies import (
    DEFAULT_STRATEGIES, RuledTableStrategy, StrategyPolicy,
    containing_column, select_strategy, trace_selection, validate_column_sections, validate_policy,
)

PARSER_VERSION = 'pdf-outline-tables-v1'


def normalized(text):
    return ' '.join(text.split())


def contains(box, char):
    x = (char['x0'] + char['x1']) / 2
    y = (char['top'] + char['bottom']) / 2
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def read_registered_document(manifest_path, document_id):
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text())
    matches = [d for d in manifest['documents'] if d['document_id'] == document_id]
    if len(matches) != 1:
        raise ValueError('El identificador debe aparecer exactamente una vez en el registro.')
    document = matches[0]
    source = (manifest_path.parent / document['path']).resolve()
    if not source.is_relative_to(manifest_path.parent) or source.suffix.lower() != '.pdf':
        raise ValueError('El PDF debe permanecer dentro del directorio del registro.')
    if hashlib.sha256(source.read_bytes()).hexdigest() != document['sha256']:
        raise ValueError('La fuente cambió; revisar su registro antes de extraer.')
    if document.get('simulated') is not False:
        raise ValueError('Este extractor solo admite documentos externos no simulados.')
    if not document.get('version'):
        raise ValueError('Registra la versión documental antes de extraer.')
    profile = document.get('extraction_profile', {})
    if profile.get('parser') != PARSER_VERSION:
        raise ValueError('Falta un perfil de extracción revisado para este documento.')
    return source, document, profile


def outline_sections(reader, first_page, last_page):
    """Keep the complete outline hierarchy and source coordinate boundaries."""
    sections = []

    for item in structure_document(reader).outline_entries():
        if first_page <= item.pdf_page <= last_page:
            sections.append({'id': f'S{len(sections) + 1:04d}',
                             'title': item.title, 'heading_path': [*item.ancestors, item.title],
                             'level': len(item.ancestors), 'start_pdf_page': item.pdf_page,
                             'start_top': round(item.top, 3), 'blocks': []})
    if not sections:
        raise ValueError('No hay marcadores: este documento requiere otro perfil de extracción.')
    sections.sort(key=lambda s: (s['start_pdf_page'], s['start_top'], s['level']))
    return sections


def section_at(sections, page, top):
    candidates = [s for s in sections
                  if (s['start_pdf_page'], s['start_top']) <= (page, top + 1)]
    if not candidates:
        raise ValueError(f'Contenido sin sección en la página PDF {page}.')
    return candidates[-1]


def heading_line(line, section, page):
    if section['start_pdf_page'] != page or abs(line['top'] - section['start_top']) > 50:
        return False
    # The printed headings can wrap. Never remove ordinary body text merely
    # because it repeats words from the current heading.
    text = normalized(line['text'])
    return (max(c['size'] for c in line['chars']) >= 10.9
            and bool(text) and text in normalized(section['title']))


def table_block(table, page_number, printed_page, *, reviewed_grid=False):
    table = table_snapshot(table)
    grid = table.grid
    # Small warning icons can look like ruled tables. Reject only grids with
    # no substantive text, leaving those characters in the ordinary text flow.
    if (len(grid) < 2 or table.column_count < 2
            or (not reviewed_grid and sum(len(c or '') for row in grid for c in row) <= 30)):
        return None
    headers = [normalized(c or '') for c in grid[0]]
    rows = []
    for number, values in enumerate(grid[1:], 1):
        rows.append({'row_number': number,
                     'cells': values,
                     'bbox': [round(v, 3) for v in table.row_boxes[number]]})
    flags = table_review_flags(headers, grid)
    return {'type': 'table', 'pdf_page': page_number, 'printed_page': printed_page,
            'bbox': [round(v, 3) for v in table.bbox], 'headers': headers,
            'raw_header': grid[0], 'rows': rows, 'review_flags': flags,
            'text_index_eligible': not flags}


def page_tables(page, profile):
    """Legacy helper: the reviewed ruled-table behavior, without page routing."""
    return RuledTableStrategy().extract(layout_page(page), profile)


def block_text(block):
    return render_block_text(block)


@dataclass(frozen=True)
class RegisteredSource:
    path: Path
    document: dict
    profile: dict


@dataclass(frozen=True)
class DocumentAnalysis:
    first_page: int
    last_page: int
    sections: list[dict]


@dataclass
class PageLayout:
    items: list[tuple]
    excluded_text: list[dict]
    body_characters: int
    table_count: int
    non_table_lines: int


@dataclass
class ExtractedPages:
    sections: list[dict]
    audits: list[dict] = field(default_factory=list)
    excluded_text: list[dict] = field(default_factory=list)
    block_number: int = 0
    previous_table: dict | None = None
    strategy_decisions: list[dict] = field(default_factory=list)


@contextmanager
def extraction_stage(name, pdf_page=None):
    """Annotate failures without changing their original class or message."""
    try:
        yield
    except Exception as error:
        note = f'PDF extraction stage: {name}'
        if pdf_page is not None:
            note += f'; PDF page: {pdf_page}'
        error.add_note(note)
        raise


def validate_source(manifest_path, document_id):
    source, document, profile = read_registered_document(manifest_path, document_id)
    return RegisteredSource(source, document, profile)


def analyze_document(source, *, backends: PDFBackends | None = None):
    """Read PDF structure while its stream is open; return no reader handles."""
    libraries = DEFAULT_BACKENDS if backends is None else backends
    with libraries.open_structure(source.path) as reader:
        if reader.encrypted:
            raise ValueError('No se admiten PDF cifrados.')
        if reader.page_count != source.document['pages']:
            raise ValueError('El número de páginas difiere del registro.')
        first, last = source.profile['content_pdf_page_range']
        if not 1 <= first <= last <= reader.page_count:
            raise ValueError('Rango de páginas de contenido inválido.')
        sections = outline_sections(reader, first, last)
    return DocumentAnalysis(first, last, sections)


def audit_page(page, number, source, analysis):
    page = layout_page(page)
    profile, document = source.profile, source.document
    lines = page.lines(x_tolerance=2, y_tolerance=3)
    footers = [l['text'] for l in lines
               if l['top'] > page.height - profile['footer_height']
               and re.fullmatch(r'\d+', l['text'])]
    if len(footers) > 1:
        raise ValueError(f'Numeración impresa ambigua en página {number}.')
    printed = int(footers[0]) if footers else None
    audit = {'pdf_page': number, 'printed_page': printed,
             'source_characters': len(page.characters), 'table_count': 0}
    if not analysis.first_page <= number <= analysis.last_page:
        reasons = [r['reason'] for r in profile['excluded_pdf_page_ranges']
                   if r['first'] <= number <= r['last']]
        if len(reasons) != 1:
            raise ValueError(f'Falta motivo único de exclusión para página {number}.')
        if number in document['inspection']['blank_pdf_pages']:
            if page.characters or page.image_count:
                raise ValueError(f'La página {number} ya no está vacía: revisar perfil.')
        audit.update(status='excluded', reason=reasons[0])
        return audit
    if not page.characters:
        raise ValueError(f'Página {number} sin texto: revisar OCR, no omitir automáticamente.')
    if printed is None:
        raise ValueError(f'Falta número impreso en página de contenido {number}.')
    return audit


def extract_page_layout(page, profile, number, printed, *, strategies=None, selection=None):
    """Separate layout filtering/table detection from paragraph reconstruction."""
    page = layout_page(page)
    methods = DEFAULT_STRATEGIES if strategies is None else strategies
    if selection is None:
        selection = select_strategy(StrategyPolicy.model_validate(profile.get('strategies', {})), number)
    def body_char(char):
        if char.get('object_type') != 'char':
            return True
        return not (char['top'] >= page.height - profile['footer_height']
                    or char['x0'] >= profile['right_sidebar_x0']
                    or (char['top'] < profile['running_header_bottom']
                        and char['size'] <= profile['running_header_max_font_size']))

    body = page.select(body_char)
    body_ids = {id(c) for c in body.characters}
    removed_lines = page.select(lambda c: c.get('object_type') != 'char'
                               or id(c) not in body_ids).lines()
    excluded = [{'pdf_page': number, 'text': l['text'],
                 'reason': 'running_header_footer_or_sidebar'} for l in removed_lines]
    tables = []
    for snapshot in methods.table_snapshots(page, profile, selection):
        # Explicitly reviewed grids are tables even when their text is short;
        # the legacy warning-icon heuristic still applies to detected grids.
        reviewed_grid = any(r.tables == 'borderless_tables'
                            and r.bbox[0] <= snapshot.bbox[0] and r.bbox[1] <= snapshot.bbox[1]
                            and r.bbox[2] >= snapshot.bbox[2] and r.bbox[3] >= snapshot.bbox[3]
                            for r in selection.regions)
        block = table_block(snapshot, number, printed, reviewed_grid=reviewed_grid)
        if block is not None:
            tables.append(block)
    for table in tables:
        if not all(body_char(c) for c in page.characters if contains(table['bbox'], c)):
            raise ValueError(f'Tabla cruza una zona excluida en página {number}.')
    text_page = body.select(lambda c: c.get('object_type') != 'char'
                            or not any(contains(t['bbox'], c) for t in tables))
    text_lines = methods.text_lines(text_page, selection)
    items = [(l['top'], 'line', l) for l in text_lines]
    items += [(t['bbox'][1], 'table', t) for t in tables]
    if selection.text == 'column_text':
        items.sort(key=lambda item: (
            item[2]['_column_order'] if item[1] == 'line' else containing_column(item[2]['bbox'], selection.columns),
            item[0]))
    else:
        items.sort(key=lambda item: item[0])
    return PageLayout(items, excluded, len(body.characters), len(tables), len(text_lines))


def append_block(state, section, block, number):
    state.block_number += 1
    block['id'] = f'B{state.block_number:05d}'
    if block['type'] == 'table':
        for row in block['rows']:
            row['id'] = f'{block["id"]}-R{row["row_number"]:03d}'
        previous = state.previous_table
        if (previous and previous['section_id'] == section['id']
                and previous['pdf_page'] == number - 1
                and previous['headers'] == block['headers']):
            block['continuation_candidate_of'] = previous['id']
        state.previous_table = {**block, 'section_id': section['id']}
    section['blocks'].append(block)


def assemble_page_blocks(state, layout, number, printed):
    paragraph = None
    paragraph_section = None
    previous_column = None
    for top, kind, item in layout.items:
        section = section_at(state.sections, number, top)
        if kind == 'line' and heading_line(item, section, number):
            if paragraph:
                append_block(state, paragraph_section, paragraph, number)
                paragraph = None
            continue
        starts_step = kind == 'line' and re.match(r'^(?:\d+\.|[•●])\s', item['text'])
        gap = kind == 'line' and paragraph and top - paragraph['bbox'][3] > 5
        column = item.get('_column_order') if kind == 'line' else None
        if paragraph and (kind == 'table' or section is not paragraph_section or starts_step or gap
                          or column != previous_column):
            append_block(state, paragraph_section, paragraph, number)
            paragraph = None
        if kind == 'table':
            append_block(state, section, item, number)
        else:
            box = [item['x0'], item['top'], item['x1'], item['bottom']]
            if paragraph is None:
                paragraph = {'type': 'paragraph', 'pdf_page': number,
                             'printed_page': printed, 'bbox': box,
                             'text': normalized(item['text'])}
                paragraph_section = section
            else:
                paragraph['text'] += ' ' + normalized(item['text'])
                paragraph['bbox'] = [min(paragraph['bbox'][0], box[0]),
                                     paragraph['bbox'][1], max(paragraph['bbox'][2], box[2]), box[3]]
        previous_column = column
    if paragraph:
        append_block(state, paragraph_section, paragraph, number)


def extract_pages(source, analysis, *, backends: PDFBackends | None = None,
                  strategies=None, policy=None, strategy_trace=None):
    libraries = DEFAULT_BACKENDS if backends is None else backends
    methods = DEFAULT_STRATEGIES if strategies is None else strategies
    policy = validate_policy(source.profile, source.document['pages']) if policy is None else policy
    # A reusable analysis must not accumulate blocks/IDs from a previous run.
    state = ExtractedPages(deepcopy(analysis.sections))
    with libraries.open_layout(source.path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            try:
                with extraction_stage('page_audit', number):
                    audit = audit_page(page, number, source, analysis)
                if audit.get('status') != 'excluded':
                    with extraction_stage('strategy_selection', number):
                        selection = select_strategy(policy, number)
                        methods.require(selection)
                        validate_column_sections(analysis.sections, number, selection)
                        decisions = trace_selection(source.document['document_id'], number, selection)
                        state.strategy_decisions.extend(decisions)
                        if strategy_trace is not None:
                            strategy_trace.extend(decisions)
                    with extraction_stage('page_layout', number):
                        layout = extract_page_layout(page, source.profile, number, audit['printed_page'],
                                                     strategies=methods, selection=selection)
                    with extraction_stage('page_reconstruction', number):
                        assemble_page_blocks(state, layout, number, audit['printed_page'])
                    state.excluded_text.extend(layout.excluded_text)
                    audit.update(status='extracted', body_characters=layout.body_characters,
                                 table_count=layout.table_count, non_table_lines=layout.non_table_lines)
                elif strategy_trace is not None:
                    strategy_trace.append({'kind': 'page_excluded', 'document_id': source.document['document_id'],
                                           'pdf_page': number, 'reason': audit['reason']})
                state.audits.append(audit)
            finally:
                page.close()
    return state


def reconstruct_document(source, state):
    """Link ancestors and render section text after all pages were assembled."""
    for section in state.sections:
        section['ancestor_section_ids'] = [
            parent['id'] for parent in state.sections
            if len(parent['heading_path']) < len(section['heading_path'])
            and section['heading_path'][:len(parent['heading_path'])] == parent['heading_path']]
        section['pages'] = sorted({b['pdf_page'] for b in section['blocks']})
        section['text'] = '\n\n'.join(block_text(b) for b in section['blocks'])
    # Lifecycle pointers can contain the previous output hash; keep them out of
    # the source snapshot so re-extracting identical bytes stays deterministic.
    source_metadata = {k: v for k, v in source.document.items()
                       if k != 'ingestion_status' and not k.startswith('local_')}
    return {'schema_version': 1, 'parser_version': PARSER_VERSION,
            'document': source_metadata, 'profile': source.profile, 'pages': state.audits,
            'excluded_layout_text': state.excluded_text, 'sections': state.sections,
            'limitations': ['Figures and graphical cells are not interpreted.',
                            'Cross-page table links are review candidates, not automatic row merges.',
                            'This is extraction, not token-limited fragmentation or an active RAG index.']}


def extract_real_document(manifest_path, document_id, *, backends: PDFBackends | None = None,
                          strategies=None, strategy_trace=None):
    """Sequential pipeline; a failed stage prevents later stages from running."""
    with extraction_stage('source_validation'):
        source = validate_source(manifest_path, document_id)
        policy = validate_policy(source.profile, source.document['pages'])
    with extraction_stage('document_analysis'):
        analysis = analyze_document(source, backends=backends)
    with extraction_stage('page_extraction'):
        state = extract_pages(source, analysis, backends=backends, strategies=strategies,
                              policy=policy, strategy_trace=strategy_trace)
    with extraction_stage('document_reconstruction'):
        result = reconstruct_document(source, state)
    with extraction_stage('final_validation'):
        validate_extraction(result)
        report = evaluate_extraction(result, strategy_trace or state.strategy_decisions)
        if report['has_errors']:
            raise ExtractionValidationError(report)
    # Preserve original dictionary ordering and optional fields of format v1.
    return result


def review_markdown(result):
    doc = result['document']
    lines = [f'# Extracción local: {doc["document_id"]}', '',
             f'Fuente: `{doc["path"]}`; versión: `{doc["version"]}`; idioma: `{doc["language"]}`.',
             f'SHA-256: `{doc["sha256"]}`.', '',
             'Las tablas conservan sus filas completas. Los números PDF e impresos se muestran separados.',
             'Las ilustraciones no se interpretan; las tablas marcadas requieren revisión visual.', '']
    for section in result['sections']:
        lines += [f'## {section["id"]} — {" / ".join(section["heading_path"])}', '']
        if not section['blocks']:
            lines += ['Marcador estructural sin contenido propio.', '']
        for block in section['blocks']:
            lines += [f'PDF {block["pdf_page"]} · impresa {block["printed_page"]} · {block["id"]}', '']
            if block['type'] == 'table':
                lines += ['Tabla — ' + ' | '.join(block['headers']), '']
                if block['review_flags']:
                    lines += ['Revisar: ' + ', '.join(block['review_flags']), '']
                if block.get('continuation_candidate_of'):
                    lines += [f'Posible continuación de {block["continuation_candidate_of"]}; no fusionada automáticamente.', '']
                for row in block['rows']:
                    lines += [f'Fila {row["row_number"]}:', '']
                    for i, value in enumerate(row['cells']):
                        label = block['headers'][i] or f'Columna {i + 1}'
                        lines += [f'- **{label}:** {normalized(value) if value is not None else "[celda combinada; revisar JSON]"}']
                    lines += ['']
            else:
                lines += [block['text'], '']
    return '\n'.join(lines)

"""Local, reviewable PDF extraction; independent of the simulated RAG corpus.

No embeddings, provider clients or database operations are used here. Outline
destinations define section boundaries; ruled tables remain structured grids.
Layout exclusions are explicit, source-hash-bound manifest configuration.
"""
import hashlib
import json
import re
from pathlib import Path

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

    def visit(items, ancestors=()):
        previous = None
        for item in items:
            if isinstance(item, list):
                if previous is None:
                    raise ValueError('Marcadores sin padre; revisar el índice del PDF.')
                visit(item, ancestors + (previous,))
                continue
            previous = item.title
            page = reader.get_destination_page_number(item) + 1
            if first_page <= page <= last_page:
                height = float(reader.pages[page - 1].mediabox.height)
                top = max(0, height - float(item.get('/Top') or height))
                sections.append({'id': f'S{len(sections) + 1:04d}',
                                 'title': item.title, 'heading_path': [*ancestors, item.title],
                                 'level': len(ancestors), 'start_pdf_page': page,
                                 'start_top': round(top, 3), 'blocks': []})

    visit(reader.outline)
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


def table_block(table, page_number, printed_page):
    grid = table.extract(x_tolerance=2, y_tolerance=3)
    # Small warning icons can look like ruled tables. Reject only grids with
    # no substantive text, leaving those characters in the ordinary text flow.
    if (len(grid) < 2 or len(table.columns) < 2
            or sum(len(c or '') for row in grid for c in row) <= 30):
        return None
    headers = [normalized(c or '') for c in grid[0]]
    rows = []
    for number, values in enumerate(grid[1:], 1):
        rows.append({'row_number': number,
                     'cells': values,
                     'bbox': [round(v, 3) for v in table.rows[number].bbox]})
    flags = []
    if any(not h for h in headers) or any(c is None for row in grid for c in row):
        flags.append('complex_or_merged_header_or_cell')
    if any(not normalized(c or '') for row in grid[1:] for c in row):
        flags.append('empty_text_cells_may_contain_graphics_or_continuation')
    return {'type': 'table', 'pdf_page': page_number, 'printed_page': printed_page,
            'bbox': [round(v, 3) for v in table.bbox], 'headers': headers,
            'raw_header': grid[0], 'rows': rows, 'review_flags': flags,
            'text_index_eligible': not flags}


def page_tables(page, profile):
    tables = page.find_tables()
    for override in profile.get('table_overrides', []):
        if override['pdf_page'] != page.page_number:
            continue
        box = override['bbox']
        replaced = [t for t in tables
                    if all(abs(a - b) < 1 for a, b in zip(t.bbox, box))]
        if len(replaced) != 1:
            raise ValueError('La tabla no coincide con la corrección de geometría revisada.')
        repaired = page.crop(tuple(box)).find_tables(override['settings'])
        if len(repaired) != 1:
            raise ValueError('La corrección de geometría no produjo una tabla única.')
        tables.remove(replaced[0])
        tables.extend(repaired)
    return sorted(tables, key=lambda t: (t.bbox[1], t.bbox[0]))


def block_text(block):
    if block['type'] == 'paragraph':
        return block['text']
    rows = []
    for row in block['rows']:
        # All cells from one source row stay together, including empty values.
        # The raw grid remains the authority for graphical/merged tables.
        rows.append('\n'.join(
            f'{header or "Column " + str(i + 1)}: {normalized(value) if value is not None else "[merged cell; review raw table]"}'
            for i, (header, value) in enumerate(zip(block['headers'], row['cells']))))
    return '\n\n'.join(rows)


def extract_real_document(manifest_path, document_id):
    import pdfplumber
    from pypdf import PdfReader

    source, document, profile = read_registered_document(manifest_path, document_id)
    reader = PdfReader(source)
    if reader.is_encrypted:
        raise ValueError('No se admiten PDF cifrados.')
    if len(reader.pages) != document['pages']:
        raise ValueError('El número de páginas difiere del registro.')
    first, last = profile['content_pdf_page_range']
    if not 1 <= first <= last <= len(reader.pages):
        raise ValueError('Rango de páginas de contenido inválido.')
    sections = outline_sections(reader, first, last)
    audits, excluded_items = [], []
    block_number = 0
    previous_table = None
    with pdfplumber.open(source, unicode_norm='NFC') as pdf:
        for number, page in enumerate(pdf.pages, 1):
            lines = page.extract_text_lines(x_tolerance=2, y_tolerance=3)
            footers = [l['text'] for l in lines
                       if l['top'] > page.height - profile['footer_height']
                       and re.fullmatch(r'\d+', l['text'])]
            if len(footers) > 1:
                raise ValueError(f'Numeración impresa ambigua en página {number}.')
            printed = int(footers[0]) if footers else None
            audit = {'pdf_page': number, 'printed_page': printed,
                     'source_characters': len(page.chars), 'table_count': 0}
            if not first <= number <= last:
                reasons = [r['reason'] for r in profile['excluded_pdf_page_ranges']
                           if r['first'] <= number <= r['last']]
                if len(reasons) != 1:
                    raise ValueError(f'Falta motivo único de exclusión para página {number}.')
                if number in document['inspection']['blank_pdf_pages']:
                    if page.chars or page.images:
                        raise ValueError(f'La página {number} ya no está vacía: revisar perfil.')
                audit.update(status='excluded', reason=reasons[0])
                audits.append(audit)
                page.close()
                continue
            if not page.chars:
                raise ValueError(f'Página {number} sin texto: revisar OCR, no omitir automáticamente.')
            if printed is None:
                raise ValueError(f'Falta número impreso en página de contenido {number}.')

            def body_char(char):
                if char.get('object_type') != 'char':
                    return True
                return not (char['top'] >= page.height - profile['footer_height']
                            or char['x0'] >= profile['right_sidebar_x0']
                            or (char['top'] < profile['running_header_bottom']
                                and char['size'] <= profile['running_header_max_font_size']))

            body = page.filter(body_char)
            body_ids = {id(c) for c in body.chars}
            removed_lines = page.filter(lambda c: c.get('object_type') != 'char'
                                       or id(c) not in body_ids).extract_text_lines()
            excluded_items.extend({'pdf_page': number, 'text': l['text'],
                                   'reason': 'running_header_footer_or_sidebar'}
                                  for l in removed_lines)
            tables = [b for t in page_tables(page, profile)
                      if (b := table_block(t, number, printed)) is not None]
            for table in tables:
                if not all(body_char(c) for c in page.chars if contains(table['bbox'], c)):
                    raise ValueError(f'Tabla cruza una zona excluida en página {number}.')
            text_page = body.filter(lambda c: c.get('object_type') != 'char'
                                    or not any(contains(t['bbox'], c) for t in tables))
            text_lines = text_page.extract_text_lines(x_tolerance=2, y_tolerance=3)
            items = [(l['top'], 'line', l) for l in text_lines]
            items += [(t['bbox'][1], 'table', t) for t in tables]
            items.sort(key=lambda item: item[0])
            paragraph = None
            paragraph_section = None

            def append_block(section, block):
                nonlocal block_number, previous_table
                block_number += 1
                block['id'] = f'B{block_number:05d}'
                if block['type'] == 'table':
                    for row in block['rows']:
                        row['id'] = f'{block["id"]}-R{row["row_number"]:03d}'
                    if (previous_table and previous_table['section_id'] == section['id']
                            and previous_table['pdf_page'] == number - 1
                            and previous_table['headers'] == block['headers']):
                        block['continuation_candidate_of'] = previous_table['id']
                    previous_table = {**block, 'section_id': section['id']}
                section['blocks'].append(block)

            for top, kind, item in items:
                section = section_at(sections, number, top)
                if kind == 'line' and heading_line(item, section, number):
                    if paragraph:
                        append_block(paragraph_section, paragraph)
                        paragraph = None
                    continue
                starts_step = kind == 'line' and re.match(r'^(?:\d+\.|[•●])\s', item['text'])
                gap = kind == 'line' and paragraph and top - paragraph['bbox'][3] > 5
                if paragraph and (kind == 'table' or section is not paragraph_section or starts_step or gap):
                    append_block(paragraph_section, paragraph)
                    paragraph = None
                if kind == 'table':
                    append_block(section, item)
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
            if paragraph:
                append_block(paragraph_section, paragraph)
            audit.update(status='extracted', body_characters=len(body.chars),
                         table_count=len(tables),
                         non_table_lines=len(text_lines))
            audits.append(audit)
            page.close()
    for section in sections:
        section['ancestor_section_ids'] = [
            parent['id'] for parent in sections
            if len(parent['heading_path']) < len(section['heading_path'])
            and section['heading_path'][:len(parent['heading_path'])] == parent['heading_path']]
        section['pages'] = sorted({b['pdf_page'] for b in section['blocks']})
        section['text'] = '\n\n'.join(block_text(b) for b in section['blocks'])
    # Lifecycle pointers can contain the previous output hash; keep them out of
    # the source snapshot so re-extracting identical bytes stays deterministic.
    source_metadata = {k: v for k, v in document.items()
                       if k != 'ingestion_status' and not k.startswith('local_')}
    return {'schema_version': 1, 'parser_version': PARSER_VERSION,
            'document': source_metadata, 'profile': profile, 'pages': audits,
            'excluded_layout_text': excluded_items, 'sections': sections,
            'limitations': ['Figures and graphical cells are not interpreted.',
                            'Cross-page table links are review candidates, not automatic row merges.',
                            'This is extraction, not token-limited fragmentation or an active RAG index.']}


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

"""Bounded search views pointing to complete, source-backed evidence units.

An embedding fragment is never a standalone procedure or a generated summary.
Hydration returns the full unit and its explicit ancestor context. No active
RAG contracts, source PDFs, academic indexes or remote repositories are changed.
"""
import hashlib
import json
import re
from pathlib import Path

import numpy as np

from .embeddings import validate_vectors
from .external_ingestion import normalized

FORMAT = 'external-parent-child-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def evidence_units(extraction):
    document = extraction['document']
    if document['simulated'] is not False:
        raise ValueError('Esta construcción es exclusivamente para documentos reales.')
    sections = {s['id']: s for s in extraction['sections']}
    units, excluded = [], []
    for section in extraction['sections']:
        ancestors = [sections[i] for i in section['ancestor_section_ids']]
        paragraphs = [b for b in section['blocks'] if b['type'] == 'paragraph']
        context = [b for s in ancestors for b in s['blocks'] if b['type'] == 'paragraph']
        graphics = [b['id'] for s in [*ancestors, section] for b in s['blocks']
                    if b['type'] == 'table' and not b['text_index_eligible']]

        def register(kind, body, source_blocks, context_blocks, row=None):
            identity = [document['sha256'], section['id'], kind,
                        [b['id'] for b in source_blocks], row['id'] if row else None]
            units.append({
                'unit_id': 'U-' + digest(identity)[:24],
                'kind': kind, 'document_id': document['document_id'],
                'source': document['path'], 'source_hash': document['sha256'],
                'version': document['version'], 'language': document['language'],
                'simulated': False, 'equipment': document['equipment'],
                'section_id': section['id'], 'section_title': section['title'],
                'heading_path': section['heading_path'],
                'body': body, 'source_blocks': source_blocks,
                'context_blocks': context_blocks,
                'references': sorted({(b['pdf_page'], b['printed_page'])
                                      for b in [*source_blocks, *context_blocks]}),
                'row': row, 'graphical_dependencies': graphics,
                'requires_visual_reference': bool(graphics),
            })

        if paragraphs:
            register('section_text', '\n\n'.join(b['text'] for b in paragraphs), paragraphs, context)
        for table in (b for b in section['blocks'] if b['type'] == 'table'):
            if not table['text_index_eligible']:
                excluded.append({'block_id': table['id'], 'pdf_page': table['pdf_page'],
                                 'reason': table['review_flags']})
                continue
            for row in table['rows']:
                if len(row['cells']) != len(table['headers']) or any(c is None for c in row['cells']):
                    raise ValueError('Fila ambigua: requiere revisión antes de fragmentar.')
                body = '\n'.join(f'{h}: {normalized(c)}'
                                 for h, c in zip(table['headers'], row['cells']))
                register('table_row', body, [table], [*context, *paragraphs],
                         {**row, 'table_id': table['id'], 'headers': table['headers'],
                          'continuation_candidate_of': table.get('continuation_candidate_of')})
    return units, excluded


def fragment_unit(unit, embedder, max_tokens=128):
    limit = min(max_tokens, embedder.max_seq_length)
    if limit < 16:
        raise ValueError('Presupuesto insuficiente para una referencia documental.')
    title = unit['section_title'].split()
    equipment = unit['equipment']
    prefix = f'{equipment["manufacturer"]} {equipment["model"]} | '
    while title and embedder.count_tokens(prefix + ' '.join(title)) > min(32, limit // 2):
        title.pop()
    header = prefix + ' '.join(title) + '\n'
    body, start, fragments = unit['body'], 0, []
    while start < len(body):
        low, high = start + 1, len(body)
        end = start
        while low <= high:
            middle = (low + high) // 2
            if embedder.count_tokens(header + body[start:middle]) <= limit:
                end, low = middle, middle + 1
            else:
                high = middle - 1
        if end == start:
            raise ValueError('No cabe contenido dentro del presupuesto.')
        if end < len(body):
            # Prefer paragraph/sentence boundaries, then whole words. The full
            # source unit is retained even when a long sentence needs windows.
            minimum = start + (end - start) // 2
            boundaries = [start + m.end() for m in re.finditer(r'\n\n|[.!?]\s+', body[start:end])]
            natural = [b for b in boundaries if b >= minimum]
            spaces = [start + m.end() for m in re.finditer(r'\s+', body[start:end])]
            end = natural[-1] if natural else next((b for b in reversed(spaces) if b >= minimum), end)
        text = header + body[start:end]
        count = embedder.count_tokens(text)
        if count > limit:
            raise ValueError('Fragmento superior al límite: no se truncará silenciosamente.')
        identity = [FORMAT, unit['unit_id'], max_tokens, start, end, text]
        fragments.append({'fragment_id': 'F-' + digest(identity)[:24],
                          'unit_id': unit['unit_id'], 'text': text, 'tokens': count,
                          'body_start': start, 'body_end': end, 'header': header})
        start = end
    if not fragments or ''.join(body[f['body_start']:f['body_end']] for f in fragments) != body:
        raise ValueError('Los fragmentos no cubren la unidad completa.')
    return fragments


def fragment_extraction(extraction, embedder, max_tokens=128):
    units, excluded = evidence_units(extraction)
    fragments = [f for unit in units for f in fragment_unit(unit, embedder, max_tokens)]
    return units, fragments, excluded


def save_local_index(directory, extraction, units, fragments, excluded, vectors, embedder):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    matrix = validate_vectors(vectors, len(fragments)).astype('<f4')
    manifest = {
        'format': FORMAT, 'document_id': extraction['document']['document_id'],
        'source_sha256': extraction['document']['sha256'],
        'model': embedder.model_name, 'revision': embedder.revision,
        'dimension': 384, 'normalized': True, 'max_seq_length': embedder.max_seq_length,
        'units': len(units), 'fragments': len(fragments), 'excluded_tables': excluded,
        'units_sha256': digest(units), 'fragments_sha256': digest(fragments),
        'vectors_sha256': hashlib.sha256(matrix.tobytes()).hexdigest(),
        'supabase_uploaded': False, 'active_index': False,
    }
    manifest['index_id'] = 'ricoh-local-' + digest(manifest)[:20]
    (directory / 'units.json').write_text(json.dumps(units, ensure_ascii=False, indent=2) + '\n')
    (directory / 'fragments.json').write_text(json.dumps(fragments, ensure_ascii=False, indent=2) + '\n')
    np.save(directory / 'vectors.npy', matrix)
    (directory / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


def load_local_index(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    units = json.loads((directory / 'units.json').read_text())
    fragments = json.loads((directory / 'fragments.json').read_text())
    vectors = validate_vectors(np.load(directory / 'vectors.npy', allow_pickle=False), len(fragments))
    identity = {k: v for k, v in manifest.items() if k != 'index_id'}
    if (manifest['index_id'] != 'ricoh-local-' + digest(identity)[:20]
            or manifest['units'] != len(units) or manifest['fragments'] != len(fragments)
            or manifest['format'] != FORMAT or digest(units) != manifest['units_sha256']
            or digest(fragments) != manifest['fragments_sha256']
            or hashlib.sha256(vectors.astype('<f4').tobytes()).hexdigest() != manifest['vectors_sha256']):
        raise ValueError('La construcción local fue alterada.')
    body_by_id = {u['unit_id']: u['body'] for u in units}
    if len(body_by_id) != len(units):
        raise ValueError('Identidades de unidad duplicadas.')
    if len({f['fragment_id'] for f in fragments}) != len(fragments):
        raise ValueError('Identidades de fragmento duplicadas.')
    for f in fragments:
        if f['text'] != f['header'] + body_by_id[f['unit_id']][f['body_start']:f['body_end']]:
            raise ValueError('El fragmento no corresponde a su unidad.')
    for uid, body in body_by_id.items():
        views = sorted((f for f in fragments if f['unit_id'] == uid), key=lambda f: f['body_start'])
        position = 0
        for view in views:
            if view['body_start'] != position or view['body_end'] <= position:
                raise ValueError('Hueco o solapamiento inesperado en la cobertura de una unidad.')
            position = view['body_end']
        if position != len(body):
            raise ValueError('Una unidad no está cubierta completamente por sus fragmentos.')
    return manifest, units, fragments, vectors

"""Immutable fingerprints for local PDF extraction regression checks.

Code and runtime versions are provenance, not acceptance criteria: refactoring
may change them while the source, profile and extraction must remain identical.
No embeddings, provider clients, or database operations are invoked.
"""
from collections import Counter
import hashlib
from importlib.metadata import version
import json
import platform
from pathlib import Path

from .external_ingestion import read_registered_document

SCHEMA = 'pdf-extraction-baseline-v1'


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def extraction_bytes(result):
    # Same serialization as scripts.extract_real_manual; formatting drift is visible.
    return (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()


def fingerprint(result):
    blocks = [b for s in result['sections'] for b in s['blocks']]
    tables = [b for b in blocks if b['type'] == 'table']
    return {
        'sha256': sha256(extraction_bytes(result)),
        'counts': {
            'pages': len(result['pages']),
            'page_statuses': dict(Counter(p['status'] for p in result['pages'])),
            'sections': len(result['sections']),
            'block_types': dict(Counter(b['type'] for b in blocks)),
            'table_rows': sum(len(t['rows']) for t in tables),
            'continuation_candidates': sum('continuation_candidate_of' in t for t in tables),
        },
        'graphical_or_ambiguous_table_ids': [t['id'] for t in tables if not t['text_index_eligible']],
        'section_sha256': {s['id']: sha256(canonical(s)) for s in result['sections']},
        'page_audit_sha256': sha256(canonical(result['pages'])),
        'excluded_layout_sha256': sha256(canonical(result['excluded_layout_text'])),
    }


def runtime():
    return {'python': platform.python_version(),
            **{name: version(name) for name in ('pdfplumber', 'pdfminer.six', 'pypdf')}}


def artifact_paths(root, document_id):
    """Fixed local references; never follow file paths supplied by a baseline."""
    relative = [f'data/extracted/{document_id}/extraction.json',
                f'data/extracted/{document_id}/review.md',
                *[f'data/indexes/ricoh-local-v1/{name}' for name in
                  ('manifest.json', 'units.json', 'fragments.json', 'vectors.npy')],
                *[f'data/indexes/sections/{name}' for name in
                  ('records.json', 'config.json', 'vectors.npy')]]
    return {name: root / name for name in relative}


def create_baseline(root, manifest, document_id, result, *, created_at_utc, git_commit):
    source, document, profile = read_registered_document(manifest, document_id)
    references = artifact_paths(root, document_id)
    saved = references[f'data/extracted/{document_id}/extraction.json'].read_bytes()
    historical = json.loads((root / 'docs/ricoh_extraction_validation.json').read_text())
    if (saved != extraction_bytes(result)
            or sha256(saved) != historical['extraction_sha256']
            or historical['source_sha256'] != document['sha256']
            or result['document']['document_id'] != document_id
            or result['profile'] != profile):
        raise ValueError('La extracción no coincide con la referencia Ricoh revisada; no fijar una nueva verdad automáticamente.')
    code = ('src/rag/external_ingestion.py', 'src/rag/external_chunking.py',
            'scripts/extract_real_manual.py', 'src/rag/extraction_baseline.py',
            'scripts/check_extraction_baseline.py')
    return {
        'schema_version': SCHEMA, 'created_at_utc': created_at_utc,
        'document_id': document_id, 'source_sha256': sha256(source.read_bytes()),
        'source_size_bytes': source.stat().st_size,
        'profile': profile, 'profile_sha256': sha256(canonical(profile)),
        'expected': fingerprint(result),
        'reference_files_sha256': {name: sha256(path.read_bytes()) for name, path in references.items()},
        'provenance': {'git_commit': git_commit, 'runtime': runtime(),
                       'code_sha256': {name: sha256((root / name).read_bytes()) for name in code}},
        'limits': ['Exact regression reference for this registered Ricoh PDF only.',
                   'No new semantic or human review; graphical limits remain.',
                   'Code/runtime drift is reported separately from extraction drift.'],
    }


def check_inputs(baseline, manifest, document_id):
    if baseline['schema_version'] != SCHEMA or baseline['document_id'] != document_id:
        raise ValueError('Esquema o documento de línea base incorrecto.')
    source, _, profile = read_registered_document(manifest, document_id)
    if (sha256(source.read_bytes()) != baseline['source_sha256']
            or source.stat().st_size != baseline['source_size_bytes']
            or profile != baseline['profile']
            or sha256(canonical(profile)) != baseline['profile_sha256']):
        raise ValueError('Fuente o perfil distintos de la línea base; no comparar como una refactorización equivalente.')


def compare(baseline, result):
    expected, actual = baseline['expected'], fingerprint(result)
    old, new = expected['section_sha256'], actual['section_sha256']
    return {'passed': actual == expected,
            'expected_sha256': expected['sha256'], 'actual_sha256': actual['sha256'],
            'changed_sections': sorted(k for k in old.keys() & new.keys() if old[k] != new[k]),
            'missing_sections': sorted(old.keys() - new.keys()),
            'added_sections': sorted(new.keys() - old.keys()),
            'changed_fields': [k for k in expected if expected[k] != actual.get(k)],
            'actual_counts': actual['counts']}


def check_references(root, baseline):
    paths = artifact_paths(root, baseline['document_id'])
    if set(paths) != set(baseline['reference_files_sha256']):
        raise ValueError('Inventario de referencias de línea base incorrecto.')
    return [name for name, path in paths.items()
            if not path.is_file() or sha256(path.read_bytes()) != baseline['reference_files_sha256'][name]]


def write_new_json(path, data):
    """Never replace a frozen baseline, report, or other existing file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

"""Composable extraction specifications and a separate validation report.

Accepted means structurally accepted, never human/semantic approval. No files
are read or mutated; source-byte verification remains a pipeline responsibility.
"""
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from typing import Protocol

from pydantic import ValidationError

from .extraction_contracts import validate_extraction
from .extraction_rules import block_indexing_decision, render_block_text
from .extraction_strategies import containing_column, select_strategy, validate_column_sections, validate_policy

SCHEMA = 'extraction-validation-v1'


@dataclass(frozen=True)
class Finding:
    rule_id: str
    status: str
    scope: str
    message: str
    pdf_page: int | None = None
    section_id: str | None = None
    block_id: str | None = None
    location: str | None = None

    def record(self):
        return {key: value for key, value in vars(self).items() if value is not None}


class ExtractionSpecification(Protocol):
    def evaluate(self, payload: dict) -> list[Finding]: ...


class ContractSpecification:
    def evaluate(self, payload):
        try:
            validate_extraction(payload)
        except ValidationError as error:
            # Exclude input/context: a diagnostic must not duplicate source text.
            return [Finding('structural_contract', 'error', 'document', item['msg'],
                            location='.'.join(map(str, item['loc'])) or 'document')
                    for item in error.errors(include_input=False, include_context=False, include_url=False)]
        return [Finding('structural_contract', 'accepted', 'document',
                        'Contrato, fuente declarada, páginas, jerarquía, IDs y cuadrículas coherentes.')]


class SectionSpecification:
    def evaluate(self, payload):
        findings = []
        sections = payload['sections']
        positions = [(s['start_pdf_page'], s['start_top'], s['level']) for s in sections]
        if positions != sorted(positions):
            findings.append(Finding('section_order', 'error', 'document',
                                    'Las secciones deben seguir el orden de sus posiciones en el PDF.'))
        for section in sections:
            expected = '\n\n'.join(render_block_text(b) for b in section['blocks'])
            if section['text'] != expected:
                findings.append(Finding('section_text_consistency', 'error', 'section',
                    'El texto de sección no coincide con sus bloques originales.', section_id=section['id']))
            for block in section['blocks']:
                candidates = [s for s in sections if (s['start_pdf_page'], s['start_top'])
                              <= (block['pdf_page'], block['bbox'][1]+1)]
                if not candidates or candidates[-1]['id'] != section['id']:
                    findings.append(Finding('section_boundary', 'error', 'block',
                        'Bloque asignado a una sección distinta de su posición.',
                        block['pdf_page'], section['id'], block['id']))
        return findings


class StrategySpecification:
    def evaluate(self, payload):
        try:
            policy = validate_policy(payload['profile'], payload['document']['pages'])
            for number in range(1, payload['document']['pages'] + 1):
                selection = select_strategy(policy, number)
                validate_column_sections(payload['sections'], number, selection)
                if selection.text == 'column_text':
                    positions = [(containing_column(b['bbox'], selection.columns), b['bbox'][1])
                                 for s in payload['sections'] for b in s['blocks'] if b['pdf_page'] == number]
                    if positions != sorted(positions):
                        raise ValueError('Orden de bloques incompatible con columnas declaradas.')
        except ValueError:
            return [Finding('strategy_policy', 'error', 'document',
                            'Política de estrategias inválida; revisar rangos, nombres y motivos.')]
        return []


class ExtractionValidationError(ValueError):
    def __init__(self, report):
        super().__init__('La extracción contiene errores de validación; no debe indexarse.')
        self.report = report


def _report(payload, findings, blocks):
    errors = any(f.status == 'error' for f in findings) or any(b['status'] == 'error' for b in blocks)
    review = any(f.status == 'review' for f in findings) or any(b['status'] == 'review' for b in blocks)
    document = payload.get('document') if isinstance(payload, dict) else None
    document = document if isinstance(document, dict) else {}
    raw = (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=True)+'\n').encode()
    return {'schema_version': SCHEMA, 'document_id': document.get('document_id'),
            'source_sha256': document.get('sha256'), 'extraction_sha256': hashlib.sha256(raw).hexdigest(),
            'status': 'error' if errors else ('review' if review else 'accepted'),
            'has_errors': errors, 'safe_indexing_allowed': not errors,
            'block_counts': {status: sum(b['status'] == status for b in blocks)
                             for status in ('accepted', 'review', 'error')},
            'finding_counts': dict(Counter(f.status for f in findings)),
            'eligible_block_ids': [b['block_id'] for b in blocks if b['text_index_eligible']] if not errors else [],
            'excluded_block_ids': [b['block_id'] for b in blocks if not b['text_index_eligible']],
            'findings': [f.record() for f in findings], 'blocks': blocks,
            'human_review_performed': False,
            'limits': ['Structural validation only; source PDF bytes verified separately by the pipeline.',
                       'Continuation links require review; complete standalone rows may remain eligible.',
                       'Accepted does not certify semantic fidelity or human approval.']}


def evaluate_extraction(payload, strategy_trace=None):
    """Invalid contracts never yield an accepted block or an indexing permit."""
    findings = ContractSpecification().evaluate(payload)
    if any(f.status == 'error' for f in findings):
        return _report(payload, findings, [])
    findings.extend(StrategySpecification().evaluate(payload))
    if any(f.status == 'error' for f in findings):
        return _report(payload, findings, [])
    findings.extend(SectionSpecification().evaluate(payload))
    policy = validate_policy(payload['profile'], payload['document']['pages'])
    blocks = []
    for section in payload['sections']:
        for block in section['blocks']:
            selection = select_strategy(policy, block['pdf_page'])
            text_only = selection.tables == 'text_only' or any(r.tables == 'text_only' for r in selection.regions)
            decision = block_indexing_decision(block, text_only=text_only)
            blocks.append({'block_id': block['id'], 'section_id': section['id'],
                           'pdf_page': block['pdf_page'], **decision})
            for code in decision['reasons']:
                findings.append(Finding(code, 'error' if decision['status'] == 'error' else 'review', 'block',
                    'Requiere revisión; la elegibilidad textual se indica por bloque.',
                    block['pdf_page'], section['id'], block['id']))
    for item in strategy_trace or []:
        if (not isinstance(item, dict) or item.get('document_id') != payload['document']['document_id']
                or type(item.get('pdf_page')) is not int or not 1 <= item['pdf_page'] <= payload['document']['pages']
                or item.get('kind') not in ('strategy_selection', 'region_strategy', 'diagnostic', 'page_excluded')):
            findings.append(Finding('strategy_trace_provenance', 'error', 'document',
                                    'Traza de estrategia sin procedencia válida.'))
    return _report(payload, findings, blocks)


def require_valid_extraction(payload, strategy_trace=None):
    # Keep the original ValidationError type/message for existing callers.
    validate_extraction(payload)
    report = evaluate_extraction(payload, strategy_trace)
    if report['has_errors']:
        raise ExtractionValidationError(report)
    return report


def execution_failure_report(error, document_id):
    existing = getattr(error, 'report', None)
    if existing is not None:
        return existing
    report = _report({'document': {'document_id': document_id}},
                     [Finding('pipeline_execution', 'error', 'document',
                              'La extracción no terminó; no se acepta ni indexa un resultado parcial.')], [])
    report['extraction_sha256'] = None
    report['error_type'] = type(error).__name__
    report['stages'] = [note for note in getattr(error, '__notes__', []) if note.startswith('PDF extraction stage:')]
    return report

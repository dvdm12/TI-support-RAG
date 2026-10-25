import copy
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from scripts import extract_real_manual
from src.rag.extraction_rules import block_indexing_decision, render_block_text
from src.rag.extraction_validation import (
    ExtractionValidationError, evaluate_extraction, require_valid_extraction,
)
from src.rag.external_chunking import evidence_units
from test.test_extraction_contracts import payload


def sync_text(value):
    for section in value['sections']:
        section['text'] = '\n\n'.join(render_block_text(b) for b in section['blocks'])


class ExtractionValidationTests(unittest.TestCase):
    def test_accepted_report_is_deterministic_and_does_not_modify_input(self):
        value = payload()
        before = copy.deepcopy(value)
        report = require_valid_extraction(value)
        self.assertEqual(report, evaluate_extraction(value))
        self.assertEqual(value, before)
        self.assertEqual(report['status'], 'accepted')
        self.assertEqual(report['eligible_block_ids'], ['B1', 'B2'])
        self.assertFalse(report['human_review_performed'])
        raw = (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()
        self.assertEqual(report['extraction_sha256'], hashlib.sha256(raw).hexdigest())

    def test_contract_errors_block_all_indexing_and_preserve_validation_exception(self):
        for mutation in ('schema', 'page', 'row', 'id'):
            value = payload()
            if mutation == 'schema':
                value['schema_version'] = 99
            elif mutation == 'page':
                value['pages'].pop()
            elif mutation == 'row':
                value['sections'][1]['blocks'][0]['rows'][0]['cells'].pop()
            else:
                value['sections'][1]['blocks'][0]['id'] = 'B1'
            with self.subTest(mutation=mutation):
                report = evaluate_extraction(value)
                self.assertEqual(report['status'], 'error')
                self.assertEqual(report['eligible_block_ids'], [])
                self.assertFalse(report['safe_indexing_allowed'])
                with self.assertRaises(ValidationError):
                    evidence_units(value)

    def test_inconsistent_section_text_cannot_enter_index(self):
        value = payload()
        value['sections'][0]['text'] += ' Invented instruction.'
        report = evaluate_extraction(value)
        self.assertIn('section_text_consistency', [f['rule_id'] for f in report['findings']])
        with self.assertRaises(ExtractionValidationError):
            evidence_units(value)

    def test_wrong_section_boundary_and_section_order_are_errors(self):
        value = payload()
        value['sections'][1]['start_pdf_page'] = 2
        value['sections'][1]['start_top'] = 15
        self.assertIn('section_boundary', [f['rule_id'] for f in evaluate_extraction(value)['findings']])
        value = payload()
        value['sections'].reverse()
        self.assertIn('section_order', [f['rule_id'] for f in evaluate_extraction(value)['findings']])

    def test_graphical_table_is_reviewed_and_kept_as_visual_dependency(self):
        value = payload()
        table = value['sections'][1]['blocks'][0]
        table['rows'][0]['cells'][0] = ''
        table['review_flags'] = ['empty_text_cells_may_contain_graphics_or_continuation']
        table['text_index_eligible'] = False
        sync_text(value)
        report = require_valid_extraction(value)
        self.assertEqual(report['status'], 'review')
        self.assertEqual(report['excluded_block_ids'], ['B2'])
        units, excluded = evidence_units(value)
        self.assertFalse(any(u['kind'] == 'table_row' for u in units))
        self.assertEqual(excluded[0]['reason'], table['review_flags'])
        # Add safe text next to the graphical table: dependency remains explicit.
        text = copy.deepcopy(value['sections'][0]['blocks'][0])
        text.update(id='B3', pdf_page=3, printed_page=2)
        value['sections'][1]['blocks'].append(text)
        sync_text(value)
        unit = evidence_units(value)[0][-1]
        self.assertEqual(unit['graphical_dependencies'], ['B2'])
        self.assertTrue(unit['requires_visual_reference'])

    def test_unsafe_eligible_table_is_rejected_even_in_legacy_memory_input(self):
        from test.test_external_chunking import extraction
        value = extraction()
        value['sections'][2]['blocks'][0]['rows'][0]['cells'][1] = ''
        with self.assertRaisesRegex(ValueError, 'ambiguo'):
            evidence_units(value)

    def test_corrupt_paragraph_is_excluded_from_units_and_ancestor_context(self):
        value = payload()
        value['sections'][0]['blocks'][0]['text'] = 'Unknown glyph: (cid:123)'
        sync_text(value)
        report = require_valid_extraction(value)
        self.assertEqual(report['excluded_block_ids'], ['B1'])
        units, excluded = evidence_units(value)
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]['context_blocks'], [])
        self.assertEqual(excluded[0]['reason'], ['unresolved_glyphs'])

    def test_text_only_page_and_region_are_excluded_without_relying_on_trace(self):
        for region in (False, True):
            value = payload()
            rule = {'first': 2, 'last': 2, 'reason': 'Table structure needs review.'}
            if region:
                rule['regions'] = [{'bbox': [0, 0, 110, 110], 'tables': 'text_only',
                                    'reason': 'Graphical region needs review.'}]
            else:
                rule['tables'] = 'text_only'
            value['profile']['strategies'] = {'pages': [rule]}
            value['document']['extraction_profile'] = copy.deepcopy(value['profile'])
            with self.subTest(region=region):
                report = require_valid_extraction(value)
                self.assertEqual(report['excluded_block_ids'], ['B1'])
                self.assertEqual(len(evidence_units(value)[0]), 1)

    def test_continuation_is_reviewed_but_complete_rows_remain_independent(self):
        value = payload()
        previous = copy.deepcopy(value['sections'][1]['blocks'][0])
        previous.update(id='B0', pdf_page=2, printed_page=1)
        previous['rows'][0]['id'] = 'B0-R1'
        value['sections'][0]['blocks'].append(previous)
        current = value['sections'][1]['blocks'].pop()
        current['continuation_candidate_of'] = 'B0'
        value['sections'][0]['blocks'].append(current)
        value['sections'][0]['pages'] = [2, 3]
        value['sections'][1]['pages'] = []
        value['sections'][1]['start_top'] = 80
        value['pages'][1]['table_count'] = 1
        sync_text(value)
        report = require_valid_extraction(value)
        self.assertEqual(report['status'], 'review')
        self.assertIn('B2', report['eligible_block_ids'])
        self.assertEqual(sum(u['kind'] == 'table_row' for u in evidence_units(value)[0]), 2)

    def test_trace_from_another_document_is_an_error(self):
        report = evaluate_extraction(payload(), [{'kind': 'strategy_selection',
                                                  'document_id': 'OTHER', 'pdf_page': 2}])
        self.assertTrue(report['has_errors'])
        self.assertEqual(report['eligible_block_ids'], [])

    def test_cli_exports_separate_report_and_matching_hash(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(extract_real_manual, 'extract_real_document', return_value=payload()), \
                 patch('sys.argv', ['extract', '--output', folder]), patch('sys.stdout', new=io.StringIO()):
                extract_real_manual.main()
            raw = (root/'validation_report.json').read_bytes()
            report = json.loads(raw)
            summary = json.loads((root/'summary.json').read_text())
            self.assertEqual(summary['validation_report_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(report['extraction_sha256'], hashlib.sha256((root/'extraction.json').read_bytes()).hexdigest())

    def test_cli_failure_writes_only_unique_failure_diagnostics_and_preserves_old_files(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            old = root/'extraction.json'
            old.write_bytes(b'previous extraction')
            error = RuntimeError('Sensitive source text must not be copied to the report.')
            error.add_note('PDF extraction stage: page_extraction')
            for _ in range(2):
                with patch.object(extract_real_manual, 'extract_real_document', side_effect=error), \
                     patch('sys.argv', ['extract', '--output', folder]), self.assertRaises(RuntimeError):
                    extract_real_manual.main()
            self.assertEqual(old.read_bytes(), b'previous extraction')
            files = list(root.glob('validation_failure_*.json'))
            self.assertEqual(len(files), 2)
            for file in files:
                raw = file.read_text()
                report = json.loads(raw)
                self.assertEqual(report['status'], 'error')
                self.assertFalse(report['safe_indexing_allowed'])
                self.assertNotIn('Sensitive source', raw)
                self.assertEqual(report['stages'], ['PDF extraction stage: page_extraction'])
            self.assertFalse((root/'summary.json').exists())

    def test_cli_semantic_rule_failure_retains_report_and_prevents_success_artifacts(self):
        value = payload()
        value['sections'][0]['text'] = 'Does not match source blocks.'
        with TemporaryDirectory() as folder:
            with patch.object(extract_real_manual, 'extract_real_document', return_value=value), \
                 patch('sys.argv', ['extract', '--output', folder]), self.assertRaises(ExtractionValidationError):
                extract_real_manual.main()
            root = Path(folder)
            report = json.loads(next(root.glob('validation_failure_*.json')).read_text())
            self.assertIn('section_text_consistency', [f['rule_id'] for f in report['findings']])
            self.assertFalse((root/'extraction.json').exists())

    def test_current_ricoh_report_and_units_keep_baseline(self):
        from src.rag.extraction_baseline import check_references, compare
        from src.rag.external_chunking import digest
        root = Path(__file__).resolve().parents[1]
        file = root/'data/extracted/RICOH-MP4002-USER-GUIDE-EN/extraction.json'
        if not file.exists():
            self.skipTest('Local Ricoh extraction unavailable.')
        baseline = json.loads((root/'docs/baselines/ricoh_extraction_v1.json').read_text())
        value = json.loads(file.read_text())
        report = require_valid_extraction(value)
        self.assertEqual(report['status'], 'review')
        self.assertEqual(report['block_counts']['error'], 0)
        self.assertEqual(len(report['excluded_block_ids']), 6)
        units, excluded = evidence_units(value)
        manifest = json.loads((root/'data/indexes/ricoh-local-v1/manifest.json').read_text())
        self.assertEqual(len(units), 498)
        self.assertEqual(len(excluded), 6)
        self.assertEqual(digest(units), manifest['units_sha256'])
        self.assertTrue(compare(baseline, value)['passed'])
        self.assertEqual(check_references(root, baseline), [])

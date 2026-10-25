from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from pydantic import ValidationError

from src.rag.extraction_strategies import (
    ExtractionStrategies, RegionRule, StrategyPolicy, StrategySelection,
    select_strategy, trace_selection, validate_policy,
)
from src.rag.external_ingestion import PARSER_VERSION, extract_real_document
from src.rag.pdf_adapters import OutlineEntry, PDFBackends, TableSnapshot, open_layout_document
from scripts import extract_real_manual
from test.test_pdf_adapters import memory_page


def snapshot(box, label):
    return TableSnapshot(tuple(box), 2, [tuple(box), tuple(box)], [['Message', 'Solution'], [label, 'Ask support.']])


class ExtractionStrategyTests(unittest.TestCase):
    def test_legacy_default_and_page_selection_are_explicit_and_scoped(self):
        policy = StrategyPolicy.model_validate({'pages': [
            {'first': 2, 'last': 3, 'tables': 'text_only', 'reason': 'Reviewed plain-text pages.'}]})
        self.assertEqual(select_strategy(policy, 1).tables, 'ruled_tables')
        self.assertEqual(select_strategy(policy, 2).tables, 'text_only')
        self.assertEqual(select_strategy(policy, 3).reason, 'Reviewed plain-text pages.')
        self.assertEqual(select_strategy(policy, 4).tables, 'ruled_tables')
        self.assertEqual(select_strategy(StrategyPolicy(), 75).text, 'native_text')

    def test_unknown_ambiguous_out_of_range_or_unjustified_configuration_is_rejected(self):
        cases = [
            {'default_text': 'ocr'}, {'default_tables': 'unknown'}, {'default_tables': 'text_only'},
            {'pages': [{'first': 4, 'last': 3, 'reason': 'Invalid range'}]},
            {'pages': [{'first': 1, 'last': 3, 'reason': 'A'}, {'first': 3, 'last': 4, 'reason': 'B'}]},
            {'pages': [{'first': 1, 'last': 9, 'reason': 'Beyond source'}]},
            {'pages': [{'first': 1, 'last': 1, 'reason': 'Overlapping regions', 'regions': [
                {'bbox': [0, 0, 50, 50], 'tables': 'ruled_tables', 'reason': 'A'},
                {'bbox': [40, 40, 70, 70], 'tables': 'ruled_tables', 'reason': 'B'}]}]},
        ]
        for config in cases:
            with self.subTest(config=config), self.assertRaises(ValueError):
                validate_policy({'strategies': config}, 5)
        with self.assertRaises(ValidationError):
            RegionRule(bbox=[1, 1, 1, 3], tables='ruled_tables', reason='Zero area')

    def test_text_only_is_deliberate_and_reports_loss_of_table_structure(self):
        page = Mock(number=2)
        methods = ExtractionStrategies()
        selection = StrategySelection('native_text', 'text_only', 'Reviewed text-only page.')
        self.assertEqual(methods.table_snapshots(page, {}, selection), [])
        page.tables.assert_not_called()
        records = trace_selection('DOC', 2, selection)
        self.assertEqual(records[0]['reason'], selection.reason)
        self.assertEqual(records[1]['severity'], 'review')
        with self.assertRaisesRegex(ValueError, 'conflicto'):
            methods.table_snapshots(page, {'table_overrides': [{'pdf_page': 2}]}, selection)

    def test_region_replaces_whole_table_and_keeps_other_tables(self):
        first = snapshot([10, 20, 100, 80], 'original')
        outside = snapshot([10, 200, 100, 260], 'outside')
        replacement = snapshot([11, 21, 99, 79], 'original')
        page = Mock(height=800, number=1)
        page.tables.return_value = [first, outside]
        page.region.return_value.tables.return_value = [replacement]
        region = RegionRule(bbox=[10, 20, 100, 80], tables='ruled_tables',
                            settings={'snap_tolerance': 1}, reason='Reviewed geometry.')
        selection = StrategySelection('native_text', 'ruled_tables', 'Default', (region,))
        result = ExtractionStrategies().table_snapshots(page, {}, selection)
        self.assertEqual(result, [replacement, outside])
        page.region.return_value.tables.assert_called_once_with({'snap_tolerance': 1})

    def test_cut_table_or_empty_expected_region_never_falls_back_silently(self):
        page = Mock(height=800, number=1)
        page.tables.return_value = [snapshot([10, 20, 100, 80], 'Original')]
        region = RegionRule(bbox=[30, 20, 100, 80], tables='ruled_tables', reason='Bad boundary')
        with self.assertRaisesRegex(ValueError, 'corta una tabla'):
            ExtractionStrategies().table_snapshots(page, {}, StrategySelection('native_text', 'ruled_tables', 'Test', (region,)))
        page.region.assert_not_called()
        region = RegionRule(bbox=[10, 20, 100, 80], tables='ruled_tables', reason='Missing table')
        page.tables.return_value = []
        page.region.return_value.tables.return_value = []
        with self.assertRaisesRegex(ValueError, 'sin tabla detectable'):
            ExtractionStrategies().table_snapshots(page, {}, StrategySelection('native_text', 'ruled_tables', 'Test', (region,)))

    def test_region_text_only_keeps_surrounding_tables_and_is_marked_for_review(self):
        first = snapshot([10, 20, 100, 80], 'Original')
        outside = snapshot([10, 200, 100, 260], 'Outside')
        page = Mock(height=800, number=1)
        page.tables.return_value = [first, outside]
        region = RegionRule(bbox=[10, 20, 100, 80], tables='text_only', reason='Reviewed text region')
        selection = StrategySelection('native_text', 'ruled_tables', 'Default', (region,))
        self.assertEqual(ExtractionStrategies().table_snapshots(page, {}, selection), [outside])
        page.region.assert_not_called()
        records = trace_selection('DOC', 1, selection)
        self.assertEqual(records[1]['kind'], 'region_strategy')
        self.assertEqual(records[2]['severity'], 'review')

    def test_regional_redetection_cannot_discard_text_from_an_existing_grid(self):
        page = Mock(height=800, number=1)
        page.tables.return_value = [snapshot([10, 20, 100, 80], 'Original message')]
        page.region.return_value.tables.return_value = [snapshot([10, 20, 100, 80], 'Missing source text')]
        region = RegionRule(bbox=[10, 20, 100, 80], tables='ruled_tables',
                            settings={'snap_tolerance': 1}, reason='Needs review')
        selection = StrategySelection('native_text', 'ruled_tables', 'Test', (region,))
        with self.assertRaisesRegex(ValueError, 'pierde texto'):
            ExtractionStrategies().table_snapshots(page, {}, selection)

    def test_selected_strategies_are_injectable_and_missing_implementation_is_rejected(self):
        text, tables = Mock(), Mock()
        page = Mock()
        text.extract.return_value = [{'text': 'Documented content'}]
        tables.extract.return_value = []
        methods = ExtractionStrategies(text={'native_text': text}, tables={'ruled_tables': tables})
        selection = StrategySelection('native_text', 'ruled_tables', 'Test implementation')
        self.assertEqual(methods.text_lines(page, selection), [{'text': 'Documented content'}])
        self.assertEqual(methods.table_snapshots(page, {}, selection), [])
        text.extract.assert_called_once_with(page)
        tables.extract.assert_called_once_with(page, {})
        with self.assertRaisesRegex(ValueError, 'no implementada'):
            methods.require(StrategySelection('native_text', 'text_only', 'Unavailable implementation'))

    def test_real_ricoh_region_selection_keeps_both_table_grids(self):
        path = Path(__file__).resolve().parents[1]/'manuals/hardware/RICOHMP4002_MANUAL.pdf'
        with open_layout_document(path) as pdf:
            page = next(p for p in pdf.pages if p.number == 185)
            original = page.tables()
            region = RegionRule(bbox=list(original[0].bbox), tables='ruled_tables', reason='Review of real fax table.')
            selection = StrategySelection('native_text', 'ruled_tables', 'Reviewed table page', (region,))
            result = ExtractionStrategies().table_snapshots(page, {}, selection)
            self.assertEqual([t.grid for t in result], [t.grid for t in original])
            page.close()

    def test_pipeline_records_selection_separately_and_cli_exports_trace(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'manual.pdf'
            source.write_bytes(b'memory backend source, not a real PDF')
            profile = {'parser': PARSER_VERSION, 'content_pdf_page_range': [1, 1],
                       'excluded_pdf_page_ranges': [], 'running_header_bottom': 65,
                       'running_header_max_font_size': 9, 'footer_height': 50, 'right_sidebar_x0': 480,
                       'strategies': {'pages': [{'first': 1, 'last': 1, 'tables': 'text_only',
                                                 'reason': 'Reviewed source contains plain text.'}]}}
            doc = {'document_id': 'MEMORY', 'path': source.name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                   'version': '1', 'language': 'en', 'simulated': False, 'pages': 1, 'size_bytes': source.stat().st_size,
                   'inspection': {'blank_pdf_pages': []}, 'extraction_profile': profile}
            manifest = root/'manifest.json'
            manifest.write_text(json.dumps({'documents': [doc]}))
            page = memory_page()
            @contextmanager
            def structure(path):
                yield SimpleNamespace(encrypted=False, page_count=1,
                                      outline_entries=lambda: [OutlineEntry('Procedure', 1, 0, ())])
            @contextmanager
            def layout(path):
                yield SimpleNamespace(pages=[page])
            backends = PDFBackends(structure, layout)
            trace = []
            before = deepcopy(doc)
            result = extract_real_document(manifest, 'MEMORY', backends=backends, strategy_trace=trace)
            self.assertEqual(result['sections'][0]['blocks'][0]['text'], 'Keep this documented condition.')
            self.assertNotIn('strategy_trace', result)
            self.assertEqual(trace[0]['tables'], 'text_only')
            self.assertEqual(trace[1]['severity'], 'review')
            self.assertEqual(json.loads(manifest.read_text())['documents'][0], before)
            output = root/'output'
            def saved_result(*args, strategy_trace):
                strategy_trace.extend(trace)
                return result
            with patch.object(extract_real_manual, 'extract_real_document', side_effect=saved_result), \
                 patch('sys.argv', ['extract', '--manifest', str(manifest), '--document-id', 'MEMORY', '--output', str(output)]):
                extract_real_manual.main()
            actual_trace = (output/'strategy_trace.json').read_bytes()
            self.assertEqual(json.loads(actual_trace), trace)
            summary = json.loads((output/'summary.json').read_text())
            self.assertEqual(summary['strategy_trace_records'], 2)
            self.assertEqual(summary['strategy_trace_sha256'], hashlib.sha256(actual_trace).hexdigest())

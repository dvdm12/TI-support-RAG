from copy import deepcopy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts.complex_pdf_samples import (
    COLUMN_LINES, HEADERS, ROWS, borderless_region, build_samples, sample_profile,
)
from scripts.evaluate_complex_pdfs import evaluate_samples, sample_blocks
from scripts import review_pdf_scan
from src.ocr.models import BoundingBox, OCRBlock, OCRResult
from src.rag.extraction_rules import block_indexing_decision
from src.rag.extraction_strategies import StrategyPolicy, validate_column_sections, select_strategy
from src.rag.extraction_validation import evaluate_extraction
from src.rag.pdf_adapters import render_ocr_page
from src.rag.pdf_adapters import OutlineEntry, PDFBackends, TableSnapshot
from src.rag.external_ingestion import extract_real_document, table_block
from src.rag.pdf_ocr_review import review_scan_page
from test.test_extraction_contracts import payload


class ComplexPDFSampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = TemporaryDirectory(prefix='ti-pdf-test-')
        cls.root = Path(cls.folder.name)
        cls.paths = build_samples(cls.root/'sources')
        cls.hashes = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in cls.paths.items()}

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_borderless_grid_preserves_exact_headers_rows_and_cells(self):
        blocks, trace = sample_blocks(self.paths['borderless'], 'borderless')
        table = next(b for b in blocks if b['type'] == 'table')
        self.assertEqual([table['headers'], *[r['cells'] for r in table['rows']]], [HEADERS, *ROWS])
        self.assertTrue(block_indexing_decision(table)['text_index_eligible'])
        self.assertEqual(trace[1]['tables'], 'borderless_tables')
        plain, _ = sample_blocks(self.paths['borderless'], 'borderless', override_profile=sample_profile('plain'))
        self.assertFalse(any(b['type'] == 'table' for b in plain))

    def test_explicit_short_grid_is_not_discarded_by_warning_icon_heuristic(self):
        snapshot = TableSnapshot((0, 0, 100, 80), 2, [(0, 0, 100, 40), (0, 40, 100, 80)],
                                 [['A', 'B'], ['1', '2']])
        self.assertIsNone(table_block(snapshot, 1, 1))
        block = table_block(snapshot, 1, 1, reviewed_grid=True)
        self.assertEqual(block['rows'][0]['cells'], ['1', '2'])
        self.assertTrue(block['text_index_eligible'])

    def test_borderless_cutting_a_word_is_rejected(self):
        profile = sample_profile('borderless')
        profile['strategies']['pages'][0]['regions'][0]['settings']['explicit_vertical_lines'][1] = 70
        with self.assertRaisesRegex(ValueError, 'columna única'):
            sample_blocks(self.paths['borderless'], 'borderless', override_profile=profile)

    def test_borderless_unknown_missing_unordered_nonfinite_boundaries_are_rejected(self):
        for change in ('missing', 'unordered', 'outside', 'nan', 'automatic', 'unknown'):
            region = borderless_region()
            settings = region['settings']
            if change == 'missing':
                del settings['explicit_horizontal_lines']
            elif change == 'unordered':
                settings['explicit_vertical_lines'] = [40, 390, 210, 570]
            elif change == 'outside':
                settings['explicit_vertical_lines'][-1] = 580
            elif change == 'nan':
                settings['explicit_vertical_lines'][1] = float('nan')
            elif change == 'automatic':
                settings['vertical_strategy'] = 'text'
            else:
                settings['unsupported_setting'] = True
            config = {'pages': [{'first': 1, 'last': 1, 'reason': 'Invalid test.', 'regions': [region]}]}
            with self.subTest(change=change), self.assertRaises(ValueError):
                StrategyPolicy.model_validate(config)

    def test_specialized_modes_cannot_be_enabled_globally_without_geometry(self):
        for config in ({'default_text': 'column_text'},
                       {'default_tables': 'borderless_tables', 'default_reason': 'Test'},
                       {'pages': [{'first': 1, 'last': 1, 'reason': 'Test', 'tables': 'borderless_tables'}]}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                StrategyPolicy.model_validate(config)

    def test_columns_keep_whole_conditions_actions_and_reading_order(self):
        blocks, trace = sample_blocks(self.paths['columns'], 'columns')
        self.assertEqual([b['text'] for b in blocks], [' '.join(lines) for lines in COLUMN_LINES])
        self.assertLess(blocks[0]['bbox'][2], blocks[1]['bbox'][0])
        self.assertTrue(all(b['bbox'][1] < b['bbox'][3] for b in blocks))
        self.assertEqual(len(trace[0]['columns']), 2)
        plain, _ = sample_blocks(self.paths['columns'], 'columns', override_profile=sample_profile('plain'))
        self.assertNotEqual([b['text'] for b in plain], [b['text'] for b in blocks])

    def test_uncovered_column_text_cannot_be_silently_dropped(self):
        profile = sample_profile('columns')
        profile['strategies']['pages'][0]['columns'][1][0] = 500
        with self.assertRaisesRegex(ValueError, 'columna única'):
            sample_blocks(self.paths['columns'], 'columns', override_profile=profile)

    def test_overlapping_missing_or_zero_area_columns_are_rejected(self):
        for columns in ([[40, 80, 350, 700], [325, 80, 570, 700]],
                        [[40, 80, 285, 700]], [[40, 80, 40, 700], [325, 80, 570, 700]]):
            config = {'pages': [{'first': 1, 'last': 1, 'reason': 'Test', 'text': 'column_text', 'columns': columns}]}
            with self.subTest(columns=columns), self.assertRaises(ValueError):
                StrategyPolicy.model_validate(config)

    def test_outline_changes_inside_columns_require_a_richer_contract(self):
        selection = select_strategy(StrategyPolicy.model_validate(sample_profile('columns')['strategies']), 1)
        with self.assertRaisesRegex(ValueError, 'eje horizontal'):
            validate_column_sections([{'start_pdf_page': 1, 'start_top': 0},
                                      {'start_pdf_page': 1, 'start_top': 100}], 1, selection)

    def test_saved_column_document_is_revalidated_before_indexing(self):
        value = payload()
        value['profile']['strategies'] = {'pages': [{'first': 2, 'last': 2, 'reason': 'Test',
            'text': 'column_text', 'columns': [[0, 15, 110, 100], [120, 15, 240, 100]]}]}
        value['document']['extraction_profile'] = deepcopy(value['profile'])
        self.assertFalse(evaluate_extraction(value)['has_errors'])
        value['sections'][0]['blocks'][0]['bbox'][2] = 150
        self.assertTrue(evaluate_extraction(value)['has_errors'])

    def test_saved_column_reading_order_cannot_be_reversed(self):
        value = payload()
        value['profile']['strategies'] = {'pages': [{'first': 2, 'last': 2, 'reason': 'Test',
            'text': 'column_text', 'columns': [[0, 15, 110, 100], [120, 15, 240, 100]]}]}
        value['document']['extraction_profile'] = deepcopy(value['profile'])
        section = value['sections'][0]
        second = {**deepcopy(section['blocks'][0]), 'id': 'B3', 'bbox': [130, 20, 180, 30]}
        section['blocks'].insert(0, second)
        section['text'] = '\n\n'.join(b['text'] for b in section['blocks'])
        self.assertTrue(evaluate_extraction(value)['has_errors'])

    def test_continuation_keeps_rows_separate_and_ambiguous_table_out(self):
        tables, _ = sample_blocks(self.paths['continuation'], 'continuation')
        self.assertEqual([len(t['rows']) for t in tables], [2, 2])
        self.assertEqual(tables[1]['continuation_candidate_of'], tables[0]['id'])
        self.assertTrue(block_indexing_decision(tables[0])['text_index_eligible'])
        self.assertFalse(block_indexing_decision(tables[1])['text_index_eligible'])
        self.assertEqual(tables[1]['rows'][1]['cells'], ['Split row sample', '', 'Unconfirmed continuation'])

    def test_native_scan_failure_does_not_trigger_ocr(self):
        with patch('src.rag.pdf_ocr_review.render_ocr_page') as render, self.assertRaisesRegex(ValueError, 'sin texto'):
            sample_blocks(self.paths['scan'], 'scan')
        render.assert_not_called()

    def test_ocr_hash_page_resolution_and_native_text_guards_run_before_renderer(self):
        cases = [('scan', 1, '0'*64, 200), ('scan', 0, self.hashes['scan'], 200),
                 ('scan', 2, self.hashes['scan'], 200), ('scan', 1, self.hashes['scan'], 800),
                 ('columns', 1, self.hashes['columns'], 200)]
        with patch('src.rag.pdf_ocr_review.render_ocr_page') as render:
            for name, page, source_hash, dpi in cases:
                with self.subTest(name=name, page=page, dpi=dpi), self.assertRaises(ValueError):
                    review_scan_page(self.paths[name], page, source_sha256=source_hash, dpi=dpi)
        render.assert_not_called()

    @staticmethod
    def raster(path, number, dpi, prefix):
        from PIL import Image
        destination = Path(str(prefix)+'.png')
        Image.new('RGB', (100, 100), 'white').save(destination)
        return destination

    def engine(self, bbox=None):
        return SimpleNamespace(scale=1.0, extract=Mock(return_value=OCRResult(
            text='Controlled', word_count=1, ocr_confidence=90, has_text=True,
            blocks=[OCRBlock('Controlled', 90, bbox or BoundingBox(10, 10, 50, 10))],
            image_path='temporary.png', image_size=(100, 100), language='eng', engine='fake-test-engine')))

    def test_ocr_candidate_preserves_pixels_provenance_and_stays_nonindexable(self):
        with patch('src.rag.pdf_ocr_review.render_ocr_page', side_effect=self.raster) as render:
            report = review_scan_page(self.paths['scan'], 1, source_sha256=self.hashes['scan'], engine=self.engine())
        self.assertEqual(report['source_sha256'], self.hashes['scan'])
        self.assertEqual(report['words'][0]['bbox'], [10, 10, 60, 20])
        self.assertEqual(report['coordinate_space'], 'rendered_page_pixels')
        self.assertEqual(report['status'], 'review')
        self.assertFalse(report['text_index_eligible'])
        self.assertFalse(Path(str(render.call_args.args[-1])+'.png').exists())
        self.assertEqual(hashlib.sha256(self.paths['scan'].read_bytes()).hexdigest(), self.hashes['scan'])

    def test_ocr_invalid_word_coordinates_and_scaled_engines_are_rejected(self):
        with patch('src.rag.pdf_ocr_review.render_ocr_page', side_effect=self.raster):
            with self.assertRaisesRegex(ValueError, 'fuera de la imagen'):
                review_scan_page(self.paths['scan'], 1, source_sha256=self.hashes['scan'],
                                 engine=self.engine(BoundingBox(90, 10, 50, 10)))
        engine = self.engine()
        engine.scale = 2
        with patch('src.rag.pdf_ocr_review.render_ocr_page') as render, self.assertRaisesRegex(ValueError, 'escala 1'):
            review_scan_page(self.paths['scan'], 1, source_sha256=self.hashes['scan'], engine=engine)
        render.assert_not_called()

    def test_missing_poppler_is_explicit_and_does_not_start_another_engine(self):
        with patch('shutil.which', return_value=None), self.assertRaisesRegex(RuntimeError, 'Poppler'):
            render_ocr_page(self.paths['scan'], 1, 200, self.root/'missing')

    def test_ocr_engine_failure_is_propagated_without_partial_candidate(self):
        engine = self.engine()
        engine.extract.side_effect = RuntimeError('Local OCR unavailable')
        with patch('src.rag.pdf_ocr_review.render_ocr_page', side_effect=self.raster), self.assertRaisesRegex(RuntimeError, 'unavailable'):
            review_scan_page(self.paths['scan'], 1, source_sha256=self.hashes['scan'], engine=engine)

    def test_ocr_cli_refuses_to_overwrite_an_existing_report_before_running(self):
        with TemporaryDirectory() as folder:
            output = Path(folder)/'candidate.json'
            output.write_text('original')
            with patch('sys.argv', ['review', str(self.paths['scan']), '--page', '1', '--source-sha256',
                                   self.hashes['scan'], '--output', str(output)]), \
                 patch.object(review_pdf_scan, 'review_scan_page') as review, self.assertRaises(FileExistsError):
                review_pdf_scan.main()
            self.assertEqual(output.read_text(), 'original')
            review.assert_not_called()

    def test_controlled_checks_run_without_ocr_and_remain_labeled_synthetic(self):
        with TemporaryDirectory() as folder:
            report = evaluate_samples(Path(folder), ocr=False)
        self.assertTrue(report['passed'])
        self.assertEqual(len(report['checks']), 7)
        self.assertEqual(report['scope'], 'controlled_synthetic_pdf_samples')
        self.assertFalse(report['ocr_executed'])

    def test_generated_sources_are_reproducible_and_not_overwritten(self):
        with TemporaryDirectory() as folder:
            paths = build_samples(Path(folder))
            self.assertEqual({k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()}, self.hashes)
            with self.assertRaises(FileExistsError):
                build_samples(Path(folder))

    def test_full_pipeline_accepts_specialized_layouts_with_injected_outline(self):
        @contextmanager
        def outline(path):
            yield SimpleNamespace(encrypted=False, page_count=1,
                                  outline_entries=lambda: [OutlineEntry('Sample', 1, 0, ())])
        for case in ('columns', 'borderless'):
            document = {'document_id': 'SYNTHETIC-TEST', 'path': self.paths[case].name,
                        'sha256': self.hashes[case], 'pages': 1, 'size_bytes': self.paths[case].stat().st_size,
                        'version': 'test-only', 'language': 'en', 'simulated': False,
                        'inspection': {'blank_pdf_pages': []}, 'fixture_kind': 'synthetic_test_only',
                        'extraction_profile': sample_profile(case)}
            # This temporary test manifest is never added to the external registry.
            with TemporaryDirectory() as folder:
                root = Path(folder)
                (root/self.paths[case].name).write_bytes(self.paths[case].read_bytes())
                manifest = root/'test-manifest.json'
                manifest.write_text(json.dumps({'documents': [document]}))
                with self.subTest(case=case):
                    result = extract_real_document(manifest, document['document_id'], backends=PDFBackends(open_structure=outline))
                    self.assertFalse(evaluate_extraction(result)['has_errors'])
                    self.assertEqual(len(result['sections'][0]['blocks']), 2 if case == 'columns' else 1)

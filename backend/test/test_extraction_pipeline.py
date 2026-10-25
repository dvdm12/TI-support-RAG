from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from src.rag.external_ingestion import (
    DocumentAnalysis, ExtractedPages, PageLayout, RegisteredSource, analyze_document,
    assemble_page_blocks, extract_pages, extract_real_document, extraction_stage,
)


def section(ident='S1', page=1, title='Setup'):
    return {'id': ident, 'title': title, 'heading_path': [title], 'level': 0,
            'start_pdf_page': page, 'start_top': 0, 'blocks': []}


def table(page):
    return {'type': 'table', 'pdf_page': page, 'printed_page': page,
            'bbox': [10, 80, 100, 120], 'headers': ['Message', 'Solution'],
            'rows': [{'row_number': 1, 'cells': ['Offline', 'Check connection.']}],
            'review_flags': [], 'text_index_eligible': True}


def line(text, top, size=10):
    return (top, 'line', {'text': text, 'top': top, 'bottom': top+10,
                         'x0': 10, 'x1': 100, 'chars': [{'size': size}]})


class ExtractionPipelineTests(unittest.TestCase):
    def test_paragraph_assembly_keeps_conditions_and_separates_numbered_steps(self):
        state = ExtractedPages([section()])
        layout = PageLayout([
            line('Setup', 10, 20), line('1. Install the driver.', 30),
            line('Only after administrator approval.', 42),
            line('2. Select the printer.', 54), (80, 'table', table(1)),
        ], [], 100, 1, 4)
        assemble_page_blocks(state, layout, 1, 1)
        blocks = state.sections[0]['blocks']
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0]['text'], '1. Install the driver. Only after administrator approval.')
        self.assertEqual(blocks[1]['text'], '2. Select the printer.')
        self.assertEqual(blocks[2]['rows'][0]['cells'], ['Offline', 'Check connection.'])

    def test_continuation_state_survives_pages_but_does_not_cross_sections(self):
        state = ExtractedPages([section(), section('S2', 3, 'Fax')])
        for page in (1, 2, 3):
            assemble_page_blocks(state, PageLayout([(80, 'table', table(page))], [], 1, 1, 0), page, page)
        first, continuation = state.sections[0]['blocks']
        other = state.sections[1]['blocks'][0]
        self.assertEqual(continuation['continuation_candidate_of'], first['id'])
        self.assertNotIn('continuation_candidate_of', other)
        self.assertEqual(continuation['rows'][0]['id'], continuation['id']+'-R001')
        self.assertEqual(len(continuation['rows']), 1)  # Rows were linked, never merged.

    def test_reusing_analysis_does_not_accumulate_blocks_or_identifiers(self):
        analysis = DocumentAnalysis(1, 1, [section()])
        before = deepcopy(analysis.sections)
        source = RegisteredSource(Path('unused.pdf'), {'pages': 1, 'document_id': 'TEST'}, {})
        page = Mock()
        with patch('pdfplumber.open') as opened, \
             patch('src.rag.external_ingestion.audit_page', side_effect=lambda *a: {'printed_page': 1}), \
             patch('src.rag.external_ingestion.extract_page_layout',
                   side_effect=lambda *a, **kw: PageLayout([line('Documented procedure.', 30)], [], 1, 0, 1)):
            opened.return_value.__enter__.return_value.pages = [page]
            first = extract_pages(source, analysis)
            second = extract_pages(source, analysis)
        self.assertEqual(analysis.sections, before)
        self.assertEqual(first.sections, second.sections)
        self.assertIsNot(first.sections[0], second.sections[0])
        self.assertEqual(first.block_number, 1)
        self.assertEqual(page.close.call_count, 2)

    def test_bad_content_page_stops_pipeline_and_closes_resources(self):
        source = RegisteredSource(Path('unused.pdf'), {'inspection': {'blank_pdf_pages': []},
                                                       'pages': 2, 'document_id': 'TEST'},
                                  {'footer_height': 50})
        analysis = DocumentAnalysis(1, 2, [section()])
        bad = Mock(height=800, chars=[])
        bad.extract_text_lines.return_value = []
        later = Mock()
        with patch('src.rag.external_ingestion.validate_source', return_value=source), \
             patch('src.rag.external_ingestion.analyze_document', return_value=analysis), \
             patch('pdfplumber.open') as opened, \
             patch('src.rag.external_ingestion.reconstruct_document') as reconstruction:
            opened.return_value.__enter__.return_value.pages = [bad, later]
            with self.assertRaisesRegex(ValueError, 'sin texto') as caught:
                extract_real_document('unused.json', 'DOC')
            reconstruction.assert_not_called()
            bad.close.assert_called_once()
            later.extract_text_lines.assert_not_called()
            opened.return_value.__exit__.assert_called_once()
        self.assertIn('PDF extraction stage: page_audit; PDF page: 1', caught.exception.__notes__)
        self.assertIn('PDF extraction stage: page_extraction', caught.exception.__notes__)

    def test_source_failure_prevents_pdf_processing(self):
        with TemporaryDirectory() as folder, patch('pdfplumber.open') as opened, \
             patch('pypdf.PdfReader') as reader:
            with self.assertRaises(FileNotFoundError) as caught:
                extract_real_document(Path(folder)/'missing.json', 'DOC')
            opened.assert_not_called()
            reader.assert_not_called()
        self.assertIn('PDF extraction stage: source_validation', caught.exception.__notes__)

    def test_analysis_closes_source_stream_on_pdf_validation_failure(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'manual.pdf'
            path.write_bytes(b'%PDF-test')
            source = RegisteredSource(path, {}, {})
            with patch('pypdf.PdfReader', return_value=SimpleNamespace(is_encrypted=True)) as reader:
                with self.assertRaisesRegex(ValueError, 'cifrados'):
                    analyze_document(source)
                self.assertTrue(reader.call_args.args[0].closed)

    def test_stage_annotation_preserves_original_exception_identity_and_message(self):
        original = RuntimeError('Invalid source geometry')
        try:
            with extraction_stage('page_layout', 75):
                raise original
        except RuntimeError as caught:
            self.assertIs(caught, original)
            self.assertEqual(str(caught), 'Invalid source geometry')
            self.assertEqual(caught.__notes__, ['PDF extraction stage: page_layout; PDF page: 75'])
        else:
            self.fail('The stage swallowed an extraction failure.')

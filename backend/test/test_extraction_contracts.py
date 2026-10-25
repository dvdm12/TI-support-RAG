import copy
import json
from pathlib import Path
import unittest

from pydantic import ValidationError

from src.rag.extraction_contracts import (
    ExtractionDiagnostic, ExtractionResult, FigureReference, Table, validate_extraction,
)


def payload():
    profile = {'parser': 'pdf-outline-tables-v1', 'content_pdf_page_range': [2, 3],
               'excluded_pdf_page_ranges': [{'first': 1, 'last': 1, 'reason': 'cover'}],
               'running_header_bottom': 65, 'running_header_max_font_size': 9,
               'footer_height': 50, 'right_sidebar_x0': 480}
    paragraph = {'id': 'B1', 'type': 'paragraph', 'pdf_page': 2, 'printed_page': 1,
                 'bbox': [10, 20, 100, 30], 'text': 'Ask the administrator first.'}
    table = {'id': 'B2', 'type': 'table', 'pdf_page': 3, 'printed_page': 2,
             'bbox': [10, 20, 100, 70], 'headers': ['Message', 'Solution'],
             'raw_header': ['Message', 'Solution'],
             'rows': [{'id': 'B2-R1', 'row_number': 1, 'bbox': [10, 40, 100, 70],
                       'cells': ['Offline', 'Check the connection.']}],
             'review_flags': [], 'text_index_eligible': True}
    return {'schema_version': 1, 'parser_version': profile['parser'],
            'document': {'document_id': 'DOC', 'path': 'manual.pdf', 'sha256': 'a'*64,
                         'version': '1', 'language': 'en', 'simulated': False,
                         'pages': 3, 'size_bytes': 100, 'extraction_profile': copy.deepcopy(profile),
                         'equipment': {'manufacturer': 'Example', 'model': 'X'},
                         'provenance': {'kind': 'authorized_sample'}},
            'profile': profile,
            'pages': [{'pdf_page': 1, 'printed_page': None, 'source_characters': 10,
                       'table_count': 0, 'status': 'excluded', 'reason': 'cover'},
                      *[{'pdf_page': page, 'printed_page': page-1, 'source_characters': 100,
                         'table_count': int(page == 3), 'status': 'extracted',
                         'body_characters': 90, 'non_table_lines': 2} for page in (2, 3)]],
            'sections': [{'id': 'S1', 'title': 'Print', 'heading_path': ['Print'], 'level': 0,
                          'start_pdf_page': 2, 'start_top': 10, 'blocks': [paragraph],
                          'ancestor_section_ids': [], 'pages': [2], 'text': paragraph['text']},
                         {'id': 'S2', 'title': 'Messages', 'heading_path': ['Print', 'Messages'],
                          'level': 1, 'start_pdf_page': 3, 'start_top': 10, 'blocks': [table],
                          'ancestor_section_ids': ['S1'], 'pages': [3],
                          'text': 'Message: Offline\nSolution: Check the connection.'}],
            'excluded_layout_text': [{'pdf_page': 2, 'text': 'Chapter 1', 'reason': 'header'}],
            'limitations': ['Figures are not interpreted.']}


class ExtractionContractTests(unittest.TestCase):
    def test_validation_preserves_raw_payload_including_omitted_fields_and_metadata(self):
        value = payload()
        before = json.dumps(value, ensure_ascii=False, indent=2)
        model = validate_extraction(value)
        self.assertEqual(json.dumps(value, ensure_ascii=False, indent=2), before)
        self.assertEqual(model.document.model_extra['equipment']['model'], 'X')
        self.assertNotIn('continuation_candidate_of', value['sections'][1]['blocks'][0])

    def test_missing_provenance_strict_types_versions_and_unknown_fields_are_rejected(self):
        for change in ('hash', 'page', 'type', 'version', 'extra', 'simulated'):
            value = payload()
            if change == 'hash':
                del value['document']['sha256']
            elif change == 'page':
                del value['sections'][0]['blocks'][0]['printed_page']
            elif change == 'type':
                value['pages'][1]['pdf_page'] = '2'
            elif change == 'version':
                value['schema_version'] = 2
            elif change == 'simulated':
                value['document']['simulated'] = True
            else:
                value['sections'][0]['blocks'][0]['unknown_field'] = 'value'
            with self.subTest(change=change), self.assertRaises(ValidationError):
                validate_extraction(value)

    def test_nonfinite_inverted_or_malformed_coordinates_are_rejected(self):
        for box in ([10, 20, 5, 30], [10, 30, 100, 20], [10, float('nan'), 100, 30], [1, 2, 3]):
            value = payload()
            value['sections'][0]['blocks'][0]['bbox'] = box
            with self.subTest(box=box), self.assertRaises(ValidationError):
                validate_extraction(value)

    def test_missing_duplicate_or_excluded_page_references_are_rejected(self):
        for change in ('missing', 'duplicate', 'excluded', 'printed', 'table_count', 'reason'):
            value = payload()
            if change == 'missing':
                value['pages'].pop()
            elif change == 'duplicate':
                value['pages'][2]['pdf_page'] = 2
            elif change == 'excluded':
                value['sections'][0]['blocks'][0]['pdf_page'] = 1
                value['sections'][0]['pages'] = [1]
            elif change == 'printed':
                value['sections'][0]['blocks'][0]['printed_page'] = 99
            elif change == 'table_count':
                value['pages'][2]['table_count'] = 0
            else:
                value['pages'][0]['reason'] = 'unregistered_reason'
            with self.subTest(change=change), self.assertRaises(ValidationError):
                validate_extraction(value)

    def test_hierarchy_and_global_ids_are_checked(self):
        for change in ('parent', 'level', 'block_id', 'section_id', 'pages', 'start'):
            value = payload()
            if change == 'parent':
                value['sections'][1]['ancestor_section_ids'] = []
            elif change == 'level':
                value['sections'][1]['level'] = 0
            elif change == 'block_id':
                value['sections'][1]['blocks'][0]['id'] = 'B1'
            elif change == 'section_id':
                value['sections'][1]['id'] = 'S1'
            elif change == 'pages':
                value['sections'][0]['pages'] = [3]
            else:
                value['sections'][1]['start_top'] = 80
            with self.subTest(change=change), self.assertRaises(ValidationError):
                validate_extraction(value)

    def test_table_rows_cannot_lose_cells_or_escape_their_table(self):
        for change in ('cells', 'raw_header', 'row_number', 'bbox', 'row_id'):
            value = payload()
            table = value['sections'][1]['blocks'][0]
            if change == 'cells':
                table['rows'][0]['cells'].pop()
            elif change == 'raw_header':
                table['raw_header'].pop()
            elif change == 'row_number':
                table['rows'][0]['row_number'] = 2
            elif change == 'row_id':
                table['rows'][0]['id'] = 'S1'
            else:
                table['rows'][0]['bbox'][2] = 120
            with self.subTest(change=change), self.assertRaises(ValidationError):
                validate_extraction(value)

    def test_merged_cells_are_preserved_and_require_review(self):
        value = payload()
        table = value['sections'][1]['blocks'][0]
        table['rows'][0]['cells'][0] = None
        with self.assertRaises(ValidationError):
            validate_extraction(value)
        table['review_flags'] = ['complex_or_merged_header_or_cell']
        table['text_index_eligible'] = False
        validated = validate_extraction(value).sections[1].blocks[0]
        self.assertIsInstance(validated, Table)
        self.assertIsNone(validated.rows[0].cells[0])
        self.assertFalse(validated.text_index_eligible)

    def test_continuations_need_an_earlier_table_in_same_section(self):
        value = payload()
        table = value['sections'][1]['blocks'][0]
        table['continuation_candidate_of'] = 'nonexistent'
        with self.assertRaises(ValidationError):
            validate_extraction(value)

    def test_source_profile_mismatch_is_rejected(self):
        value = payload()
        value['document']['extraction_profile']['footer_height'] = 60
        with self.assertRaises(ValidationError):
            validate_extraction(value)

    def test_figure_references_and_diagnostics_are_explicit_separate_contracts(self):
        figure = {'id': 'FIG1', 'type': 'figure_reference', 'document_id': 'DOC',
                  'pdf_page': 2, 'printed_page': 1, 'bbox': [1, 2, 3, 4],
                  'interpretation_status': 'not_performed'}
        FigureReference.model_validate(figure)
        with self.assertRaises(ValidationError):
            FigureReference.model_validate({**figure, 'interpretation_status': 'understood'})
        value = payload()
        value['sections'][0]['blocks'].append(figure)
        with self.assertRaises(ValidationError):
            validate_extraction(value)
        diagnostic = {'code': 'graphical_table', 'severity': 'review',
                      'message': 'Requires visual review.', 'document_id': 'DOC', 'pdf_page': 2}
        ExtractionDiagnostic.model_validate(diagnostic)
        with self.assertRaises(ValidationError):
            ExtractionDiagnostic.model_validate({**diagnostic, 'severity': 'approved'})
        self.assertIn('discriminator', ExtractionResult.model_json_schema()['$defs']['ExtractionSection']['properties']['blocks']['items'])

    def test_current_ricoh_extraction_passes_without_reserialization(self):
        root = Path(__file__).resolve().parents[1]
        path = root / 'data/extracted/RICOH-MP4002-USER-GUIDE-EN/extraction.json'
        if not path.exists():
            self.skipTest('Extracción local ignorada no disponible; casos sintéticos siguen activos.')
        raw = path.read_bytes()
        value = json.loads(raw)
        model = validate_extraction(value)
        self.assertEqual(len(model.pages), 228)
        self.assertEqual(len(model.sections), 146)
        self.assertEqual((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode(), raw)
        self.assertEqual(path.read_bytes(), raw)

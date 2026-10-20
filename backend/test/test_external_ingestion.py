import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from src.rag.external_ingestion import (
    PARSER_VERSION, block_text, heading_line, outline_sections,
    page_tables, read_registered_document, review_markdown, section_at, table_block,
)


class ExternalRegistrationTests(unittest.TestCase):
    def registered(self, root):
        data = b'%PDF-test-registration-only'
        (root / 'manual.pdf').write_bytes(data)
        doc = {'document_id': 'RICOH', 'path': 'manual.pdf', 'version': 'D129-7802',
               'simulated': False, 'sha256': hashlib.sha256(data).hexdigest(),
               'extraction_profile': {'parser': PARSER_VERSION}}
        path = root / 'manifest.json'
        path.write_text(json.dumps({'documents': [doc]}))
        return path, doc

    def test_modified_source_is_rejected_before_pdf_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _ = self.registered(root)
            (root / 'manual.pdf').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'fuente cambió'):
                read_registered_document(manifest, 'RICOH')

    def test_simulated_source_and_path_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, doc = self.registered(root)
            doc['simulated'] = True
            manifest.write_text(json.dumps({'documents': [doc]}))
            with self.assertRaisesRegex(ValueError, 'no simulados'):
                read_registered_document(manifest, 'RICOH')
            doc['path'] = '../manual.pdf'
            manifest.write_text(json.dumps({'documents': [doc]}))
            with self.assertRaisesRegex(ValueError, 'dentro'):
                read_registered_document(manifest, 'RICOH')

    def test_missing_profile_and_duplicate_id_do_not_silently_select_a_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, doc = self.registered(root)
            doc['extraction_profile'] = {}
            manifest.write_text(json.dumps({'documents': [doc]}))
            with self.assertRaisesRegex(ValueError, 'perfil'):
                read_registered_document(manifest, 'RICOH')
            manifest.write_text(json.dumps({'documents': [doc, doc]}))
            with self.assertRaisesRegex(ValueError, 'exactamente una'):
                read_registered_document(manifest, 'RICOH')


class ExternalStructureTests(unittest.TestCase):
    def table(self, rows):
        return SimpleNamespace(
            bbox=(50, 100, 450, 300), columns=[1, 2, 3],
            rows=[SimpleNamespace(bbox=(50, 100 + i * 40, 450, 140 + i * 40))
                  for i in range(len(rows))],
            extract=lambda **kwargs: rows)

    def test_problem_cause_solution_rows_remain_associated(self):
        rows = [['Message', 'Causes', 'Solutions'],
                ['Job suspended', 'Job Operation selected', 'Resume the\nselected job.'],
                ['Offline', 'Printer offline', 'Review the\nconnection.']]
        result = table_block(self.table(rows), 185, 183)
        self.assertEqual(result['rows'][0]['cells'], rows[1])
        self.assertEqual(result['rows'][1]['cells'], rows[2])
        text = block_text(result)
        self.assertIn('Message: Job suspended\nCauses: Job Operation selected\nSolutions: Resume the selected job.', text)
        self.assertEqual((result['pdf_page'], result['printed_page']), (185, 183))

    def test_merged_cells_are_flagged_not_filled_with_another_rows_message(self):
        result = table_block(self.table([
            ['Message', 'Causes', 'Solutions'],
            ['Message A', 'A documented cause', 'A documented solution'],
            [None, 'Another documented cause', 'Another documented solution'],
        ]), 186, 184)
        self.assertIsNone(result['rows'][1]['cells'][0])
        self.assertIn('complex_or_merged_header_or_cell', result['review_flags'])
        self.assertIn('[merged cell; review raw table]', block_text(result))

    def test_warning_icon_grid_is_not_treated_as_a_text_table(self):
        self.assertIsNone(table_block(self.table([['', '', '']]), 95, 93))

    def test_same_page_section_boundary_uses_position(self):
        sections = [
            {'id': 'fax', 'start_pdf_page': 185, 'start_top': 88},
            {'id': 'print', 'start_pdf_page': 185, 'start_top': 254},
        ]
        self.assertEqual(section_at(sections, 185, 115)['id'], 'fax')
        self.assertEqual(section_at(sections, 185, 358)['id'], 'print')

    def test_body_text_repeating_a_heading_is_not_discarded(self):
        section = {'title': 'Standard Printing', 'start_pdf_page': 97, 'start_top': 88}
        line = {'text': 'Standard Printing', 'top': 93, 'chars': [{'size': 10}]}
        self.assertFalse(heading_line(line, section, 97))
        line['chars'][0]['size'] = 20
        self.assertTrue(heading_line(line, section, 97))

    def test_review_contains_no_silent_table_continuation_merge(self):
        table = table_block(self.table([
            ['Message', 'Causes', 'Solutions'], ['Error', 'Unknown cause', 'Contact authorized support'],
        ]), 185, 183)
        table.update(id='B001', continuation_candidate_of='B000')
        result = {'document': {'document_id': 'RICOH', 'path': 'manual.pdf',
                              'version': 'D129-7802', 'language': 'en', 'sha256': 'a'*64},
                  'sections': [{'id': 'S001', 'heading_path': ['Print'], 'blocks': [table]}]}
        review = review_markdown(result)
        self.assertIn('PDF 185 · impresa 183', review)
        self.assertIn('Posible continuación de B000; no fusionada automáticamente.', review)
        self.assertIn('**Solutions:** Contact authorized support', review)


class RicohSourceRegressionTests(unittest.TestCase):
    """Real source regressions for layouts that can corrupt retrieval evidence."""

    def registered(self):
        manifest = Path(__file__).resolve().parents[1] / 'manuals/manifest.real.json'
        return read_registered_document(manifest, 'RICOH-MP4002-USER-GUIDE-EN')

    def test_staple_table_header_is_not_split_by_lines_inside_the_diagrams(self):
        import pdfplumber
        source, _, profile = self.registered()
        with pdfplumber.open(source) as pdf:
            blocks = [b for t in page_tables(pdf.pages[74], profile)
                      if (b := table_block(t, 75, 73)) is not None]
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['headers'][1], 'Placing the original on the exposure glass')
        self.assertEqual(blocks[0]['headers'][2], 'Placing the original in the ADF')
        self.assertFalse(blocks[0]['text_index_eligible'])

    def test_fax_and_print_tables_on_same_page_have_different_sections(self):
        import pdfplumber
        from pypdf import PdfReader
        source, _, profile = self.registered()
        sections = outline_sections(PdfReader(source), *profile['content_pdf_page_range'])
        with pdfplumber.open(source) as pdf:
            tables = [b for t in page_tables(pdf.pages[184], profile)
                      if (b := table_block(t, 185, 183)) is not None]
        self.assertEqual(len(tables), 2)
        fax = section_at(sections, 185, tables[0]['bbox'][1])
        printing = section_at(sections, 185, tables[1]['bbox'][1])
        self.assertIn('Messages Displayed When Using the Facsimile Function', fax['heading_path'])
        self.assertIn('Messages Displayed When Using the Printer Function', printing['heading_path'])
        suspended = next(r for r in tables[1]['rows'] if r['cells'][0] == '"Job Suspended..."')
        self.assertIn('ask your system administrator first', suspended['cells'][1])


if __name__ == '__main__':
    unittest.main()

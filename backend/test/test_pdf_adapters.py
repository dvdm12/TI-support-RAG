import builtins
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.rag.external_ingestion import PARSER_VERSION, extract_real_document, table_block
from src.rag.pdf_adapters import (
    LayoutPage, OutlineEntry, PDFBackends, PypdfStructureAdapter, TableSnapshot,
    open_layout_document, open_structure_document, table_snapshot,
)


class MemoryPage:
    """A tiny common-interface fixture, with no library methods or objects."""
    number = 1
    height = 800
    image_count = 0

    def __init__(self, characters):
        self.characters = characters
        self.closed = False

    def lines(self, **options):
        return [{'text': c['text'], 'top': c['top'], 'bottom': c['bottom'],
                 'x0': c['x0'], 'x1': c['x1'], 'chars': [c]} for c in self.characters]

    def select(self, predicate):
        return MemoryPage([c for c in self.characters if predicate(c)])

    def region(self, box):
        raise AssertionError('This fixture has no tables to crop.')

    def tables(self, settings=None):
        return []

    def close(self):
        self.closed = True


def memory_page(blank=False):
    def char(text, top):
        return {'object_type': 'char', 'text': text, 'top': top,
                'bottom': top+10, 'x0': 20, 'x1': 200, 'size': 10}
    return MemoryPage([] if blank else [char('Keep this documented condition.', 100), char('1', 780)])


class PDFAdapterTests(unittest.TestCase):
    def fixture(self, root):
        source = root/'manual.pdf'
        source.write_bytes(b'synthetic source; decoded only by memory backends')
        profile = {'parser': PARSER_VERSION, 'content_pdf_page_range': [1, 1],
                   'excluded_pdf_page_ranges': [], 'running_header_bottom': 65,
                   'running_header_max_font_size': 9, 'footer_height': 50, 'right_sidebar_x0': 480}
        doc = {'document_id': 'MEMORY', 'path': source.name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'version': '1', 'language': 'en', 'simulated': False, 'pages': 1,
               'size_bytes': source.stat().st_size, 'inspection': {'blank_pdf_pages': []},
               'extraction_profile': profile}
        manifest = root/'manifest.json'
        manifest.write_text(json.dumps({'documents': [doc]}))
        return manifest

    def backends(self, page, events, encrypted=False):
        @contextmanager
        def structure(path):
            events.append('structure_open')
            try:
                yield SimpleNamespace(encrypted=encrypted, page_count=1,
                                      outline_entries=lambda: [OutlineEntry('Procedure', 1, 0, ())])
            finally:
                events.append('structure_close')

        @contextmanager
        def layout(path):
            events.append('layout_open')
            try:
                yield SimpleNamespace(pages=[page])
            finally:
                events.append('layout_close')

        return PDFBackends(structure, layout)

    def test_whole_pipeline_runs_with_common_interfaces_and_no_pdf_library_imports(self):
        events = []
        page = memory_page()
        original_import = builtins.__import__
        def no_pdf_libraries(name, *a, **kw):
            if name.split('.')[0] in ('pypdf', 'pdfplumber'):
                raise AssertionError('Core pipeline imported a PDF library.')
            return original_import(name, *a, **kw)
        with TemporaryDirectory() as folder:
            manifest = self.fixture(Path(folder))
            with patch('builtins.__import__', side_effect=no_pdf_libraries):
                result = extract_real_document(manifest, 'MEMORY', backends=self.backends(page, events))
        self.assertEqual(result['sections'][0]['blocks'][0]['text'], 'Keep this documented condition.')
        self.assertEqual(result['excluded_layout_text'][0]['text'], '1')
        self.assertEqual(result['schema_version'], 1)
        self.assertTrue(page.closed)
        self.assertEqual(events, ['structure_open', 'structure_close', 'layout_open', 'layout_close'])

    def test_injected_page_failure_closes_context_and_page_without_returning_partial_result(self):
        events = []
        page = memory_page(blank=True)
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'sin texto') as caught:
                extract_real_document(self.fixture(Path(folder)), 'MEMORY', backends=self.backends(page, events))
        self.assertTrue(page.closed)
        self.assertEqual(events[-1], 'layout_close')
        self.assertIn('PDF extraction stage: page_audit; PDF page: 1', caught.exception.__notes__)

    def test_injected_structure_failure_closes_context_and_never_opens_layout(self):
        events = []
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'cifrados'):
                extract_real_document(self.fixture(Path(folder)), 'MEMORY',
                                      backends=self.backends(memory_page(), events, encrypted=True))
        self.assertEqual(events, ['structure_open', 'structure_close'])

    def test_pypdf_constructor_failure_closes_stream_and_preserves_exception(self):
        failure = RuntimeError('Cannot decode PDF structure')
        with TemporaryDirectory() as folder:
            path = Path(folder)/'manual.pdf'
            path.write_bytes(b'%PDF-test')
            with patch('pypdf.PdfReader', side_effect=failure) as reader:
                with self.assertRaises(RuntimeError) as caught:
                    with open_structure_document(path):
                        self.fail('A broken reader must not yield a document.')
                self.assertIs(caught.exception, failure)
                self.assertTrue(reader.call_args.args[0].closed)

    def test_pdfplumber_document_context_receives_consumer_failure(self):
        failure = RuntimeError('Layout processing failed')
        with patch('pdfplumber.open') as opened:
            with self.assertRaises(RuntimeError) as caught:
                with open_layout_document(Path('unused.pdf')):
                    raise failure
            self.assertIs(caught.exception, failure)
            self.assertIs(opened.return_value.__exit__.call_args.args[1], failure)

    def test_pypdf_destinations_become_plain_outline_data(self):
        class Destination(dict):
            def __init__(self, title, top):
                super().__init__({'/Top': top})
                self.title = title
        root = Destination('Print', 700)
        child = Destination('PCL 6', 600)
        reader = SimpleNamespace(outline=[root, [child]], is_encrypted=False,
                                 pages=[SimpleNamespace(mediabox=SimpleNamespace(height=800))],
                                 get_destination_page_number=lambda item: 0)
        self.assertEqual(PypdfStructureAdapter(reader).outline_entries(),
                         [OutlineEntry('Print', 1, 100, ()), OutlineEntry('PCL 6', 1, 200, ('Print',))])

    def test_table_snapshot_preserves_raw_cells_and_geometry_without_native_objects(self):
        grid = [['Message', 'Solution'], ['Offline', 'Check connection.'], [None, 'Ask support.']]
        native = SimpleNamespace(bbox=(10, 20, 100, 80), columns=[1, 2],
                                 rows=[SimpleNamespace(bbox=(10, y, 100, y+20)) for y in (20, 40, 60)],
                                 extract=lambda **kw: grid)
        snapshot = table_snapshot(native)
        self.assertIsInstance(snapshot, TableSnapshot)
        self.assertEqual(snapshot.grid, grid)
        self.assertFalse(hasattr(snapshot, 'extract'))
        block = table_block(snapshot, 1, 1)
        self.assertIsNone(block['rows'][1]['cells'][0])
        self.assertFalse(block['text_index_eligible'])

    def test_real_layout_adapter_preserves_character_identity_and_plain_tables(self):
        path = Path(__file__).resolve().parents[1]/'manuals/hardware/RICOHMP4002_MANUAL.pdf'
        with open_layout_document(path) as pdf:
            page = next(p for p in pdf.pages if p.number == 185)
            self.assertIsInstance(page, LayoutPage)
            original = page.characters
            view = page.select(lambda obj: True)
            self.assertTrue(original)
            self.assertTrue(all(a is b for a, b in zip(original, view.characters)))
            tables = page.tables()
            self.assertEqual(len(tables), 2)
            self.assertTrue(all(isinstance(t, TableSnapshot) for t in tables))
            self.assertTrue(any('"Job Suspended..."' in row for t in tables for row in t.grid))
            page.close()

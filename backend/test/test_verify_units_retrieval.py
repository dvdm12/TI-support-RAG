import copy
import csv
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import numpy as np

from scripts import evaluate_ricoh_local, verify_units_retrieval as step8
from src.rag import unit_verification
from src.rag.config import EMBEDDING_MODEL
from src.rag.external_chunking import evidence_units, save_local_index

REVISION = 'a' * 40


def vector(position):
    value = np.zeros(384, dtype='float32')
    value[position] = 1
    return value


class FakeEmbedder:
    model_name = EMBEDDING_MODEL
    max_seq_length = 128

    def __init__(self, revision=REVISION, targets=None):
        self.revision = revision
        self.targets = targets or {}

    def encode(self, texts):
        return np.stack([vector(self.targets.get(t, 383)) for t in texts])


def extraction():
    """Legacy-shaped extraction accepted by evidence_units without full contracts."""
    paragraph = lambda bid, page, text: {'id': bid, 'type': 'paragraph', 'pdf_page': page, 'printed_page': page,
                                         'bbox': [0, 0, 1, 1], 'text': text}
    return {
        'document': {'document_id': step8.DOCUMENT_ID, 'path': 'hardware/manual.pdf', 'sha256': 'f' * 64,
                     'version': 'V1', 'language': 'en', 'simulated': False,
                     'equipment': {'manufacturer': 'Ricoh', 'model': 'MP 4002'}},
        'profile': {'content_pdf_page_range': [1, 2]},
        'excluded_layout_text': [{'pdf_page': 1, 'text': '1'}],
        'sections': [
            {'id': 'S1', 'title': 'Sending a Hold Print File', 'heading_path': ['Sending a Hold Print File'],
             'ancestor_section_ids': [], 'start_pdf_page': 1,
             'blocks': [paragraph('B1', 1, 'Select Hold Print.')]},
            {'id': 'S2', 'title': 'Status messages', 'heading_path': ['Status messages'],
             'ancestor_section_ids': [], 'start_pdf_page': 2,
             'blocks': [{'id': 'B2', 'type': 'table', 'pdf_page': 2, 'printed_page': 2, 'bbox': [0, 0, 1, 1],
                         'headers': ['Message', 'Cause'], 'raw_header': ['Message', 'Cause'],
                         'rows': [{'id': 'R1', 'row_number': 1, 'cells': ['"Offline"', 'Printer is offline.']},
                                  {'id': 'R2', 'row_number': 2, 'cells': ['"Toner"', 'Replace toner.']}],
                         'review_flags': [], 'text_index_eligible': True}]},
        ],
    }


PAGES = {1: 'Sending a Hold Print File Select Hold Print. 1',
         2: 'Status messages Message Cause "Offline" Printer is offline. "Toner" Replace toner.'}
CASES = [
    {'id': 'RIC-06', 'question': 'retenida', 'expected_section': 'Sending a Hold Print File'},
    {'id': 'RIC-09', 'question': 'offline', 'expected_section': 'Status messages', 'expected_row_contains': '"Offline"'},
    {'id': 'RIC-99', 'question': 'toner low', 'expected_section': 'Status messages', 'expected_row_contains': '"Toner Low"'},
]


def fragments_for(units):
    return [{'fragment_id': 'F-' + u['unit_id'], 'unit_id': u['unit_id'], 'text': 'H\n' + u['body'],
             'tokens': 5, 'body_start': 0, 'body_end': len(u['body']), 'header': 'H\n'} for u in units]


def build_root(directory, data=None):
    """Temporary backend with registered extraction, active index and frozen local Ricoh index."""
    root = Path(directory)
    data = data or extraction()
    stored = root / 'data/extracted/RICOH'
    stored.mkdir(parents=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    (stored / 'extraction.json').write_text(payload)
    (root / 'manuals').mkdir()
    (root / 'manuals/manifest.real.json').write_text(json.dumps({'documents': [{
        'document_id': step8.DOCUMENT_ID, 'path': 'hardware/manual.pdf',
        'local_extraction': {'output_directory_relative_to_backend': 'data/extracted/RICOH',
                             'extraction_sha256': hashlib.sha256(payload.encode()).hexdigest()}}]}))
    (root / 'data/indexes/sections').mkdir(parents=True)
    (root / 'data/indexes/sections/records.json').write_text('[]')
    units, excluded = evidence_units(data)
    fragments = fragments_for(units)
    vectors = np.stack([vector(i) for i in range(len(fragments))])
    save_local_index(root / 'data/indexes/ricoh', data, units, fragments, excluded, vectors, FakeEmbedder())
    (root / 'cases.json').write_text(json.dumps(CASES, ensure_ascii=False))
    return root, units


def targets(units):
    # RIC-06 is pointed at the wrong unit (search failure); RIC-09 at the right row.
    position = {u['unit_id']: i for i, u in enumerate(units)}
    offline = next(u for u in units if u['row'] and u['row']['id'] == 'R1')
    toner = next(u for u in units if u['row'] and u['row']['id'] == 'R2')
    return {'retenida': position[toner['unit_id']], 'offline': position[offline['unit_id']]}


def run(root, units, **overrides):
    options = {'extract': lambda manifest, document_id: extraction(),
               'embedder_factory': lambda revision: FakeEmbedder(revision, targets(units)),
               'read_pages': lambda path, first, last: {n: PAGES[n] for n in range(first, last + 1)}}
    options.update(overrides)
    return step8.verify(root, root / 'data/indexes/ricoh', root / 'cases.json', REVISION, **options)


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).rglob('*')) if p.is_file()}


class VerifyIntegrationTests(unittest.TestCase):
    def test_full_report_separates_stages_and_preserves_everything(self):
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)
            report = run(root, units)
        pres = report['preservation']
        self.assertTrue(pres['extraction_identical_to_registered'])
        self.assertTrue(pres['units_before_after']['identical'])
        self.assertTrue(pres['source_accounting']['complete'])
        self.assertTrue(pres['block_coverage']['complete'])
        self.assertEqual(pres['block_coverage']['status'], {'paragraphs_in_units': 1, 'table_rows_in_units': 2})
        for strategy in step8.STRATEGIES:
            with self.subTest(strategy=strategy):
                stages = {r['id']: r['stage'] for r in report['retrieval'][strategy]['results']}
                self.assertEqual(stages['RIC-99'], 'extraction_loss')
                self.assertEqual(stages['RIC-09'], 'retrieved')
        semantic = report['retrieval']['semantic']
        self.assertEqual({r['id']: r['stage'] for r in semantic['results']}['RIC-06'], 'retrieved')
        self.assertEqual(semantic['searchable_cases'], 2)
        self.assertFalse(report['supabase_writes'] or report['groq_calls'])
        self.assertIsNone(report['git_commit'])

    def test_search_failure_when_relevant_unit_is_outside_top3(self):
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)
            # Simulate a retriever that never ranks the indexed evidence in Top-3.
            with mock.patch.object(step8, 'retrieve_units', lambda *a, **k: []):
                report = run(root, units)
        stages = {r['id']: r['stage'] for r in report['retrieval']['semantic']['results']}
        self.assertEqual(stages, {'RIC-06': 'search_failure', 'RIC-09': 'search_failure', 'RIC-99': 'extraction_loss'})
        self.assertEqual(report['retrieval']['semantic']['hit_at_3_given_evidence_indexed'], 0)

    def test_verification_writes_nothing_under_backend(self):
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)
            before = snapshot(root)
            run(root, units)
            self.assertEqual(snapshot(root), before)

    def test_registered_hash_mismatch_is_rejected(self):
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)
            (root / 'data/extracted/RICOH/extraction.json').write_text('{}\n')
            with self.assertRaisesRegex(ValueError, 'registrada'):
                run(root, units)

    def test_changed_extraction_is_reported_and_blocks_search_on_stale_index(self):
        changed = extraction()
        changed['sections'][0]['blocks'][0]['text'] = 'Select Stored Print.'
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)
            with self.assertRaisesRegex(ValueError, 'reconstruir'):
                run(root, units, extract=lambda manifest, document_id: copy.deepcopy(changed))

    def test_embedder_revision_or_model_mismatch_is_rejected(self):
        class OtherModel(FakeEmbedder):
            model_name = 'other/model'
        for factory in (lambda revision: FakeEmbedder('b' * 40), lambda revision: OtherModel(revision)):
            with self.subTest(factory=factory), TemporaryDirectory() as directory:
                root, units = build_root(directory)
                with self.assertRaisesRegex(ValueError, 'modelo/revisión'):
                    run(root, units, embedder_factory=factory)

    def test_tampered_local_index_is_rejected(self):
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)
            path = root / 'data/indexes/ricoh/units.json'
            altered = json.loads(path.read_text())
            altered[0]['body'] += ' x'
            path.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError, 'alterada'):
                run(root, units)

    def test_active_index_cannot_be_used_as_ricoh_index(self):
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)
            for index in (root / 'data/indexes/sections', root / 'data/indexes/sections/sub'):
                with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'índice activo'):
                    step8.verify(root, index, root / 'cases.json', REVISION)

    def test_index_modified_during_run_is_detected(self):
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)

            def extract(manifest, document_id):
                (root / 'data/indexes/sections/records.json').write_text('[1]')
                return extraction()
            with self.assertRaisesRegex(ValueError, 'cambió'):
                run(root, units, extract=extract)

    def test_source_loss_is_reported_without_aborting(self):
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)
            pages = {1: PAGES[1] + ' Warning!', 2: PAGES[2]}
            report = run(root, units, read_pages=lambda path, first, last: pages)
        accounting = report['preservation']['source_accounting']
        self.assertFalse(accounting['complete'])
        self.assertEqual(accounting['missing_characters'], len('Warning!'))

    def test_page_reader_receives_profile_range_and_registered_pdf(self):
        calls = []
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)
            run(root, units, read_pages=lambda path, first, last: calls.append((path, first, last)) or PAGES)
        self.assertEqual(calls, [(root / 'manuals/hardware/manual.pdf', 1, 2)])


class EvaluateCasesTests(unittest.TestCase):
    def test_top3_ranks_relevance_and_presence_per_strategy(self):
        data = extraction()
        units, excluded = evidence_units(data)
        fragments = fragments_for(units)
        vectors = np.stack([vector(i) for i in range(len(fragments))])
        queries = FakeEmbedder(targets=targets(units)).encode([c['question'] for c in CASES])
        result = step8.evaluate_cases(CASES, queries, data, units, fragments, vectors, excluded)
        self.assertEqual(set(result), set(step8.STRATEGIES))
        ric09 = next(r for r in result['semantic']['results'] if r['id'] == 'RIC-09')
        self.assertEqual(ric09['first_relevant_rank'], 1)
        self.assertTrue(ric09['top3'][0]['relevant'])
        self.assertLessEqual(len(ric09['top3']), 3)
        self.assertEqual(ric09['presence']['extraction_blocks'], ['B2'])
        self.assertEqual(sum(result['semantic']['by_stage'].values()), len(CASES))

    def test_literal_strategy_promotes_quoted_message(self):
        data = extraction()
        units, excluded = evidence_units(data)
        fragments = fragments_for(units)
        vectors = np.stack([vector(i) for i in range(len(fragments))])
        case = [{'id': 'Q', 'question': 'El panel muestra "Toner"', 'expected_section': 'Status messages',
                 'expected_row_contains': '"Toner"'}]
        query = vector(0)[None, :]  # semantically closest to the paragraph unit
        result = step8.evaluate_cases(case, query, data, units, fragments, vectors, excluded)
        self.assertEqual(result['hybrid_literal']['results'][0]['first_relevant_rank'], 1)
        self.assertNotEqual(result['semantic']['results'][0]['first_relevant_rank'], 1)


class ExportTests(unittest.TestCase):
    def report(self):
        with TemporaryDirectory() as directory:
            root, units = build_root(directory)
            return run(root, units)

    def test_json_csv_and_pdf_are_written(self):
        report = self.report()
        with TemporaryDirectory() as directory:
            output = Path(directory)
            step8.export(output, report)
            self.assertEqual(json.loads((output / 'report.json').read_text()), report)
            with (output / 'cases.csv').open(encoding='utf-8') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), len(step8.STRATEGIES) * len(CASES))
            self.assertEqual({r['stage'] for r in rows} - set(unit_verification.STAGES), set())
            self.assertTrue((output / 'report.pdf').read_bytes().startswith(b'%PDF'))

    def test_existing_reports_are_never_overwritten(self):
        report = self.report()
        with TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'report.json').write_text('keep')
            with self.assertRaises(FileExistsError):
                step8.export(output, report)
            self.assertEqual((output / 'report.json').read_text(), 'keep')

    def test_refused_export_leaves_no_partial_files(self):
        report = self.report()
        for name in ('cases.csv', 'report.pdf'):
            with self.subTest(name=name), TemporaryDirectory() as directory:
                output = Path(directory)
                (output / name).write_text('keep')
                with self.assertRaisesRegex(FileExistsError, name):
                    step8.export(output, report)
                self.assertEqual([p.name for p in output.iterdir()], [name])
                self.assertEqual((output / name).read_text(), 'keep')


class HelperTests(unittest.TestCase):
    def test_file_hashes_cover_files_only(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'a.txt').write_text('a')
            (root / 'sub').mkdir()
            self.assertEqual(step8.file_hashes(root), {'a.txt': hashlib.sha256(b'a').hexdigest()})

    def test_page_texts_reads_requested_range_from_real_pdf(self):
        from reportlab.pdfgen import canvas
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.pdf'
            pdf = canvas.Canvas(str(path))
            for text in ('Page one', 'Page two', 'Page three'):
                pdf.drawString(72, 720, text)
                pdf.showPage()
            pdf.save()
            result = step8.page_texts(path, 2, 3)
        self.assertEqual(sorted(result), [2, 3])
        self.assertEqual(unit_verification.characters(result[2]), unit_verification.characters('Page two'))

    def test_main_refuses_existing_output_directory(self):
        with TemporaryDirectory() as directory, mock.patch.object(sys, 'argv', ['x', '--output', directory]), \
                mock.patch('sys.stderr'), mock.patch.object(step8, 'verify') as verify:
            with self.assertRaises(SystemExit):
                step8.main()
            verify.assert_not_called()

    def test_main_exports_into_new_directory(self):
        report = ExportTests().report()
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'new'
            with mock.patch.object(sys, 'argv', ['x', '--output', str(output)]), \
                    mock.patch.object(step8, 'verify', return_value=report), mock.patch('builtins.print'):
                step8.main()
            self.assertEqual(sorted(p.name for p in output.iterdir()), ['cases.csv', 'report.json', 'report.pdf'])


class RicohEvaluatorRefactorTests(unittest.TestCase):
    def test_ricoh_evaluator_uses_the_shared_relevance_rule(self):
        self.assertIs(evaluate_ricoh_local.relevant, unit_verification.relevant)
        self.assertIs(step8.relevant, unit_verification.relevant)


if __name__ == '__main__':
    unittest.main()

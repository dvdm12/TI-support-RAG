import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from src.rag.external_chunking import (
    evidence_units, fragment_extraction, fragment_unit, load_local_index, save_local_index,
)
from src.rag.external_retrieval import evidence_text, retrieve_units


class WordBudget:
    max_seq_length = 128
    model_name = 'control-vectors-only'
    revision = 'a' * 40

    def count_tokens(self, text):
        return len(text.split()) + 2


def extraction():
    warning = {'id': 'B1', 'type': 'paragraph', 'text': 'If USB printing reports an error in Sleep mode, check whether the document was printed.', 'pdf_page': 97, 'printed_page': 95}
    steps = {'id': 'B2', 'type': 'paragraph', 'text': '\n\n'.join(f'{i}. Perform documented step {i}, then check its condition.' for i in range(1, 36)), 'pdf_page': 97, 'printed_page': 95}
    cells = ['A printer message', 'The complete documented cause.', 'The complete documented solution.']
    table = {'id': 'B3', 'type': 'table', 'pdf_page': 98, 'printed_page': 96,
             'text_index_eligible': True, 'headers': ['Message', 'Causes', 'Solutions'],
             'rows': [{'id': 'B3-R001', 'cells': cells}]}
    return {'document': {'document_id': 'RICOH', 'path': 'ricoh.pdf', 'sha256': 'b'*64,
                         'simulated': False, 'version': 'D129-7802', 'language': 'en',
                         'equipment': {'manufacturer': 'Ricoh', 'model': 'MP 4002'}},
            'sections': [
                {'id': 'S1', 'title': 'Standard Printing', 'heading_path': ['Print', 'Standard Printing'],
                 'ancestor_section_ids': [], 'blocks': [warning]},
                {'id': 'S2', 'title': 'PCL 6', 'heading_path': ['Print', 'Standard Printing', 'PCL 6'],
                 'ancestor_section_ids': ['S1'], 'blocks': [steps]},
                {'id': 'S3', 'title': 'Messages', 'heading_path': ['Print', 'Messages'],
                 'ancestor_section_ids': [], 'blocks': [table]},
            ]}


class SourcePreservingFragmentTests(unittest.TestCase):
    def test_long_procedure_is_searchable_without_losing_any_of_35_steps(self):
        units, fragments, _ = fragment_extraction(extraction(), WordBudget())
        procedure = next(u for u in units if u['section_id'] == 'S2')
        views = [f for f in fragments if f['unit_id'] == procedure['unit_id']]
        self.assertGreater(len(views), 1)
        self.assertTrue(all(f['tokens'] <= 128 for f in views))
        recovered = ''.join(f['text'][len(f['header']):] for f in views)
        self.assertEqual(recovered, procedure['body'])
        self.assertIn('35. Perform documented step 35', recovered)
        self.assertIn('If USB printing reports an error in Sleep mode', evidence_text(procedure))

    def test_long_table_row_is_one_evidence_unit_even_if_it_needs_several_search_views(self):
        original = extraction()
        row = original['sections'][2]['blocks'][0]['rows'][0]
        row['cells'][2] = ' '.join(['preserve the complete conditional solution'] * 80)
        units, fragments, _ = fragment_extraction(original, WordBudget())
        unit = next(u for u in units if u['kind'] == 'table_row')
        self.assertEqual(unit['row']['cells'], row['cells'])
        self.assertIn('Message: A printer message\nCauses: The complete documented cause.', unit['body'])
        self.assertGreater(sum(f['unit_id'] == unit['unit_id'] for f in fragments), 1)
        self.assertTrue(unit['body'].endswith(row['cells'][2]))

    def test_graphical_table_does_not_become_invented_text_evidence(self):
        original = extraction()
        table = original['sections'][2]['blocks'][0]
        table.update(text_index_eligible=False, review_flags=['graphical cell'])
        units, _, excluded = fragment_extraction(original, WordBudget())
        self.assertFalse(any(u['kind'] == 'table_row' for u in units))
        self.assertEqual(excluded[0]['block_id'], 'B3')

    def test_repeated_build_keeps_identifiers_and_source_data_unchanged(self):
        original = extraction()
        before = copy.deepcopy(original)
        first = fragment_extraction(original, WordBudget())
        self.assertEqual(first, fragment_extraction(original, WordBudget()))
        self.assertEqual(original, before)

    def test_roundtrip_checks_vectors_and_linked_source_body(self):
        original = extraction()
        units, fragments, excluded = fragment_extraction(original, WordBudget())
        vectors = np.zeros((len(fragments), 384), dtype=np.float32)
        vectors[:, 0] = 1
        with tempfile.TemporaryDirectory() as directory:
            save_local_index(directory, original, units, fragments, excluded, vectors, WordBudget())
            manifest, actual, views, matrix = load_local_index(directory)
            self.assertEqual(actual[1]['body'], units[1]['body'])
            self.assertEqual(len(views), len(fragments))
            path = Path(directory) / 'fragments.json'
            tampered = json.loads(path.read_text())
            tampered[0]['text'] += ' invented advice'
            path.write_text(json.dumps(tampered))
            with self.assertRaisesRegex(ValueError, 'alterada'):
                load_local_index(directory)

    def test_parent_deduplication_returns_full_context_instead_of_three_slices_of_same_procedure(self):
        units, fragments, _ = fragment_extraction(extraction(), WordBudget())
        procedure_id = next(u['unit_id'] for u in units if u['section_id'] == 'S2')
        vectors = np.zeros((len(fragments), 384), dtype=np.float32)
        for i, f in enumerate(fragments):
            vectors[i, 0 if f['unit_id'] == procedure_id else 1] = 1
        query_vector = np.eye(384, dtype=np.float32)[0]
        results = retrieve_units('PCL 6', query_vector, units, fragments, vectors, 3)
        self.assertEqual(len({r['unit_id'] for r in results}), len(results))
        self.assertEqual(results[0]['unit']['section_id'], 'S2')
        self.assertIn('35. Perform documented step 35', evidence_text(results[0]['unit']))
        self.assertIn('Sleep mode', evidence_text(results[0]['unit']))

    def test_exact_quoted_unseen_message_beats_a_semantically_similar_wrong_row(self):
        original = extraction()
        original['sections'][2]['blocks'][0]['rows'][0]['cells'][0] = '"Novel\nMessage ZX-73"'
        units, fragments, _ = fragment_extraction(original, WordBudget())
        vectors = np.zeros((len(fragments), 384), dtype=np.float32)
        for i, f in enumerate(fragments):
            unit = next(u for u in units if u['unit_id'] == f['unit_id'])
            vectors[i, 1 if unit['kind'] == 'table_row' else 0] = 1
        query_vector = np.eye(384, dtype=np.float32)[0]
        results = retrieve_units('Aparece "Novel Message ZX-73". ¿Qué significa?', query_vector,
                                 units, fragments, vectors, 3, 'hybrid_literal')
        self.assertEqual(results[0]['unit']['kind'], 'table_row')
        self.assertEqual(results[0]['match_basis'], 'exact_quoted_source_message')
        self.assertIn('The complete documented solution.', evidence_text(results[0]['unit']))


if __name__ == '__main__':
    unittest.main()

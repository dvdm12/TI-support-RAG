import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.rag.extraction_baseline import (
    SCHEMA, artifact_paths, canonical, check_inputs, check_references, compare,
    create_baseline, extraction_bytes, fingerprint, sha256, write_new_json,
)


def result():
    return {'pages': [{'pdf_page': 1, 'status': 'extracted'}],
            'sections': [{'id': 'S1', 'title': 'Print', 'blocks': [
                {'id': 'B1', 'type': 'paragraph', 'text': 'Ask administrator first.'},
                {'id': 'B2', 'type': 'table', 'text_index_eligible': False,
                 'rows': [{'cells': ['Message', 'Cause', 'Solution']}]}]}],
            'excluded_layout_text': [{'text': 'Footer'}]}


class BaselineTests(unittest.TestCase):
    def test_text_or_table_change_fails_even_when_counts_stay_equal(self):
        original = result()
        baseline = {'expected': fingerprint(original)}
        self.assertTrue(compare(baseline, original)['passed'])
        for change in ('paragraph', 'table', 'layout', 'page'):
            changed = copy.deepcopy(original)
            if change == 'paragraph':
                changed['sections'][0]['blocks'][0]['text'] = 'No administrator required.'
            elif change == 'table':
                changed['sections'][0]['blocks'][1]['rows'][0]['cells'].reverse()
            elif change == 'layout':
                changed['excluded_layout_text'][0]['text'] = 'Lost warning'
            else:
                changed['pages'][0]['pdf_page'] = 2
            with self.subTest(change=change):
                report = compare(baseline, changed)
                self.assertFalse(report['passed'])
                self.assertEqual(report['actual_counts'], baseline['expected']['counts'])
        self.assertEqual(compare(baseline, changed)['changed_fields'], ['sha256', 'page_audit_sha256'])

    def test_added_missing_and_changed_sections_are_reported(self):
        baseline = {'expected': fingerprint(result())}
        changed = result()
        changed['sections'][0]['id'] = 'S2'
        report = compare(baseline, changed)
        self.assertEqual(report['missing_sections'], ['S1'])
        self.assertEqual(report['added_sections'], ['S2'])
        changed = result()
        changed['sections'][0]['blocks'][0]['text'] += ' Changed.'
        self.assertEqual(compare(baseline, changed)['changed_sections'], ['S1'])

    def test_new_json_never_overwrites_a_reference_or_report(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'baseline.json'
            write_new_json(path, {'reference': True})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_new_json(path, {'reference': False})
            self.assertEqual(path.read_bytes(), before)

    def test_changed_source_profile_or_wrong_document_cannot_be_compared(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.pdf'
            source.write_bytes(b'original')
            profile = {'parser': 'test'}
            baseline = {'schema_version': SCHEMA, 'document_id': 'RICOH',
                        'source_sha256': sha256(source.read_bytes()), 'source_size_bytes': 8,
                        'profile': profile, 'profile_sha256': sha256(canonical(profile))}
            with patch('src.rag.extraction_baseline.read_registered_document',
                       return_value=(source, {}, profile)):
                check_inputs(baseline, None, 'RICOH')
                source.write_bytes(b'modified')
                with self.assertRaisesRegex(ValueError, 'Fuente o perfil'):
                    check_inputs(baseline, None, 'RICOH')
                source.write_bytes(b'original')
                changed = copy.deepcopy(baseline)
                changed['profile']['parser'] = 'changed'
                with self.assertRaisesRegex(ValueError, 'Fuente o perfil'):
                    check_inputs(changed, None, 'RICOH')
                with self.assertRaisesRegex(ValueError, 'documento'):
                    check_inputs(baseline, None, 'OTHER')

    def test_reference_changes_and_missing_files_are_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = artifact_paths(root, 'RICOH')
            for path in paths.values():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'reference')
            baseline = {'document_id': 'RICOH', 'reference_files_sha256':
                        {k: sha256(p.read_bytes()) for k, p in paths.items()}}
            self.assertEqual(check_references(root, baseline), [])
            names = list(paths)
            paths[names[0]].write_bytes(b'changed')
            paths[names[1]].unlink()
            self.assertEqual(check_references(root, baseline), names[:2])

    def test_capture_rejects_a_new_extraction_that_differs_from_reviewed_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = result()
            original.update(document={'document_id': 'RICOH'}, profile={'parser': 'test'})
            path = artifact_paths(root, 'RICOH')['data/extracted/RICOH/extraction.json']
            path.parent.mkdir(parents=True)
            path.write_bytes(extraction_bytes(original))
            (root / 'docs/extractor').mkdir(parents=True)
            (root / 'docs/extractor/ricoh_extraction_validation.json').write_text(json.dumps({
                'extraction_sha256': sha256(path.read_bytes()), 'source_sha256': 'registered'}))
            changed = copy.deepcopy(original)
            changed['sections'][0]['blocks'][0]['text'] = 'An invented instruction.'
            with patch('src.rag.extraction_baseline.read_registered_document',
                       return_value=(root / 'source.pdf', {'sha256': 'registered'}, original['profile'])):
                with self.assertRaisesRegex(ValueError, 'referencia Ricoh'):
                    create_baseline(root, None, 'RICOH', changed,
                                    created_at_utc='test', git_commit='test')

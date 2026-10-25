import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.evaluate_web_pdfs import character_agreement, verify_sources, word_error


class WebPDFEvaluationTests(unittest.TestCase):
    def test_word_agreement_normalizes_case_unicode_and_punctuation(self):
        result = word_error('Cable: ﬁle OFFLINE.', 'cable file offline')
        self.assertEqual(result['word_edit_distance'], 0)
        self.assertEqual(result['reference_tokens'], 3)
        self.assertEqual(result['order_insensitive_token_recall'], 1)

    def test_character_conservation_handles_ligatures_and_keeps_raw_differences(self):
        result = character_agreement('ﬁle ﬂow', 'file flow')
        self.assertTrue(result['equivalent'])
        self.assertEqual(result['raw_missing_characters'], {'ﬁ': 1, 'ﬂ': 1})
        self.assertEqual(result['missing'], 0)

    def test_character_conservation_does_not_hide_missing_digits_or_changed_case(self):
        for actual in ('Model 12', 'model 123'):
            with self.subTest(actual=actual):
                self.assertFalse(character_agreement('Model 123', actual)['equivalent'])

    def test_word_agreement_counts_substitution_deletion_and_insertion(self):
        for actual in ('check printer', 'check', 'check the cable'):
            with self.subTest(actual=actual):
                result = word_error('check cable', actual)
                self.assertEqual(result['word_edit_distance'], 1)
                self.assertEqual(result['word_error_rate'], .5)

    def test_many_insertions_can_exceed_one_hundred_percent(self):
        self.assertEqual(word_error('cable', 'cable one two three')['word_error_rate'], 3)

    def test_empty_reference_has_no_invented_denominator(self):
        with self.assertRaisesRegex(ValueError, 'denominador'):
            word_error('---', 'printer')

    def fixture(self, directory):
        pdf = directory/'test.pdf'
        reference = directory/'test.txt'
        pdf.write_bytes(b'%PDF-probe')
        reference.write_text('Reference')
        return {'sources': [{'id': 'sample', 'file': pdf.name, 'sha256': hashlib.sha256(pdf.read_bytes()).hexdigest()}],
                'ocr_reference': {'file': reference.name, 'sha256': hashlib.sha256(reference.read_bytes()).hexdigest()}}

    def test_unchanged_downloads_are_reused_without_network_or_mutation(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            config = self.fixture(root)
            before = (root/'test.pdf').read_bytes()
            self.assertEqual(verify_sources(root, config), {'sample': (root/'test.pdf').resolve()})
            self.assertEqual((root/'test.pdf').read_bytes(), before)

    def test_tampered_pdf_or_reference_is_rejected(self):
        for name in ('test.pdf', 'test.txt'):
            with TemporaryDirectory() as folder:
                root = Path(folder)
                config = self.fixture(root)
                (root/name).write_text('changed')
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'cambió'):
                    verify_sources(root, config)

    def test_path_escape_or_unsafe_id_is_rejected_before_use(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for field, value in [('file', '../outside.pdf'), ('id', '../outside')]:
                config = self.fixture(root)
                config['sources'][0][field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    verify_sources(root, config)

"""Current OCR contract; no EasyOCR downloads during tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.multimodal import prepare_multimodal_input
from src.ocr.strategy import OCRStrategy
from src.ocr.models import OCRResult
from src.ocr.exceptions import OCRInputError

class TestMultimodal(unittest.TestCase):
    def test_text_only(self):
        result = prepare_multimodal_input('  No puedo entrar.  ')
        self.assertEqual(result['text'], 'No puedo entrar.')
        self.assertFalse(result['has_attachment'])
        self.assertTrue(result['extraction_valid'])
        self.assertIsNone(result['extracted_text'])

    def test_invalid_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in (Path(tmp), Path(tmp)/'missing.png', Path(tmp)/'document.pdf'):
                with self.assertRaises(OCRInputError): OCRStrategy.validate_image(path)

    def test_ocr_options_and_evidence(self):
        ocr = OCRResult('Error 403', 2, 92, True, [], '/tmp/error.png', (100,100), 'spa', 'tesseract')
        with patch('src.multimodal.OCRFactory.create') as factory, patch('src.multimodal.OCRExtractor') as extractor:
            extractor.return_value.extract.return_value = ocr
            result = prepare_multimodal_input('Error', '/tmp/error.png', ocr_engine='tesseract', psm=6)
        factory.assert_called_once_with('tesseract', psm=6)
        self.assertEqual(result['extracted_text'], 'Error 403')
        self.assertEqual(result['extraction']['engine'], 'tesseract')
        self.assertTrue(result['extraction_valid'])

    def test_empty_ocr_rejected(self):
        ocr = OCRResult('', 0, 0, False, [], '/tmp/blank.png', (100,100), 'spa', 'tesseract')
        with patch('src.multimodal.OCRFactory.create'), patch('src.multimodal.OCRExtractor') as extractor:
            extractor.return_value.extract.return_value = ocr
            result = prepare_multimodal_input('Problema', '/tmp/blank.png')
        self.assertFalse(result['extraction_valid'])
        self.assertTrue(result['extraction_errors'])

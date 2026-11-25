"""Upload lifecycle, real image decoding and combined-input budget regressions."""
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.uploadhandler import StopUpload
from django.test import Client, SimpleTestCase, override_settings
from PIL import Image
from pydantic import ValidationError

from . import services
from .contracts import OCRResponse, QueryRequest, SearchRequest
from .uploads import BoundedImageUploadHandler, temporary_ocr_image
from src.ocr.exceptions import OCRDependencyError, OCRExtractionError
from src.token_budget import InputBudgetError

TOKEN = 't' * 48


def image_bytes(format='PNG', size=(80, 30)):
    buffer = BytesIO()
    Image.new('RGB', size, 'white').save(buffer, format=format)
    return buffer.getvalue()


def upload(name='capture.png', data=None, content_type='image/png'):
    return SimpleUploadedFile(name, image_bytes() if data is None else data, content_type=content_type)


def extracted(text='Error de red'):
    return {'extraction_valid': bool(text), 'extracted_text': text,
            'extraction': {'engine': 'tesseract', 'language': 'spa+eng',
                           'ocr_confidence': 91.0, 'word_count': len(text.split())}}


def local_resources(tokens=40):
    embedder = Mock()
    embedder.count_tokens.return_value = tokens
    config = Mock(max_seq_length=128)
    return embedder, 'corpus', config


@override_settings(RAG_API_TOKEN=TOKEN, ALLOWED_HOSTS=['testserver'], DEBUG=False)
class OCRControllerTests(SimpleTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.headers = {'HTTP_AUTHORIZATION': 'Bearer ' + TOKEN}

    def post(self, fields=None):
        return self.client.post('/api/v1/ocr/extract/', fields or {'imagen': upload()}, **self.headers)

    def test_auth_precedes_upload_parsing_and_cookie_auth_is_not_accepted(self):
        self.client.cookies['sessionid'] = 'unused'
        with patch('api.controllers.BoundedImageUploadHandler') as handler:
            response = self.client.post('/api/v1/ocr/extract/', {'imagen': upload()})
        self.assertEqual(response.status_code, 401)
        handler.assert_not_called()

    def test_method_and_content_type_are_explicit(self):
        self.assertEqual(self.client.get('/api/v1/ocr/extract/', **self.headers).status_code, 405)
        response = self.client.post('/api/v1/ocr/extract/', '{}', content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 415)
        malformed = self.client.post('/api/v1/ocr/extract/', b'x', content_type='multipart/form-data', **self.headers)
        self.assertEqual(malformed.status_code, 400)

    def test_missing_extra_duplicate_fields_and_multiple_files_are_rejected(self):
        factories = [
            lambda: {'pregunta': 'Error'},
            lambda: {'imagen': upload(), 'mode': 'mock'},
            lambda: {'imagen': upload(), 'pregunta': ['a', 'b']},
            lambda: {'imagen': [upload(), upload()]},
            lambda: {'archivo': upload()},
            lambda: {'imagen': upload(), 'pregunta': 'x' * 8001},
        ]
        with patch('src.multimodal.prepare_multimodal_input') as ocr:
            for factory in factories:
                with self.subTest(factory=factory):
                    self.assertEqual(self.post(factory()).status_code, 400)
        ocr.assert_not_called()

    def test_declared_body_limit_precedes_parser_and_ocr(self):
        with patch('api.services.extract_ocr') as ocr:
            response = self.client.generic('POST', '/api/v1/ocr/extract/', b'x',
                content_type='multipart/form-data; boundary=test',
                CONTENT_LENGTH=str(settings.OCR_MAX_UPLOAD_BYTES + settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1),
                **self.headers)
        self.assertEqual(response.status_code, 413)
        ocr.assert_not_called()

    @override_settings(OCR_MAX_UPLOAD_BYTES=32)
    def test_actual_file_bytes_are_bounded_during_multipart_parsing(self):
        with patch('src.multimodal.prepare_multimodal_input') as ocr:
            response = self.post()
        self.assertEqual(response.status_code, 413)
        ocr.assert_not_called()

    def test_corrupt_image_and_spoofed_extension_or_mime_do_not_reach_engine(self):
        files = [
            (upload(data=b'not an image'), 400),
            (upload(data=image_bytes()[:32]), 400),
            (upload(name='wrong.jpg'), 415),
            (upload(content_type='text/plain'), 415),
            (upload(name='image.gif', data=image_bytes('GIF'), content_type='image/gif'), 415),
        ]
        with patch('src.multimodal.prepare_multimodal_input') as ocr:
            for file, status in files:
                with self.subTest(name=file.name):
                    self.assertEqual(self.post({'imagen': file}).status_code, status)
        ocr.assert_not_called()

    @override_settings(OCR_MAX_IMAGE_PIXELS=1000)
    def test_pixel_limit_is_enforced_before_extraction(self):
        with patch('src.multimodal.prepare_multimodal_input') as ocr:
            self.assertEqual(self.post({'imagen': upload(data=image_bytes(size=(100, 20)))}).status_code, 413)
        ocr.assert_not_called()

    @override_settings(OCR_MAX_IMAGE_SIDE=64)
    def test_individual_side_limit_is_enforced(self):
        self.assertEqual(self.post().status_code, 413)

    def test_animated_png_is_not_accepted_as_a_static_screenshot(self):
        buffer = BytesIO()
        Image.new('RGB', (20, 20), 'white').save(buffer, format='PNG', save_all=True,
            append_images=[Image.new('RGB', (20, 20), 'black')], duration=100)
        self.assertEqual(self.post({'imagen': upload(data=buffer.getvalue())}).status_code, 415)

    def test_real_decoding_success_returns_safe_contract_and_removes_temporary(self):
        paths = []
        def engine(question, path, **options):
            self.assertTrue(path.is_file())
            self.assertEqual(path.name, 'input.png')
            self.assertEqual(options, {'ocr_engine': 'tesseract'})
            paths.append(path)
            return extracted()
        with patch('src.multimodal.prepare_multimodal_input', side_effect=engine), \
             patch('api.services.resources', return_value=local_resources()), \
             patch('src.groq_client.call_groq') as groq:
            response = self.post({'imagen': upload(name='private-original.png'), 'pregunta': '¿Qué indica este error?'})
        self.assertEqual(response.status_code, 200)
        result = OCRResponse.model_validate(response.json())
        self.assertEqual(result.texto_ocr, 'Error de red')
        self.assertTrue(result.presupuesto.admisible)
        self.assertNotIn('private-original', response.content.decode())
        self.assertNotIn('image_path', response.content.decode())
        self.assertFalse(paths[0].exists())
        self.assertFalse(paths[0].parent.exists())
        groq.assert_not_called()

    def test_empty_ocr_and_engine_failures_clean_up_and_release_slot(self):
        for exception, expected_status in [(None, 422), (OCRDependencyError('private-secret'), 503),
                                           (OCRExtractionError('private-secret'), 422), (RuntimeError('private-secret'), 503)]:
            paths = []
            def engine(question, path, **options):
                paths.append(path)
                if exception:
                    raise exception
                return extracted('')
            with patch('src.multimodal.prepare_multimodal_input', side_effect=engine):
                response = self.post()
            self.assertEqual(response.status_code, expected_status)
            self.assertNotIn('private', response.content.decode())
            self.assertFalse(paths[0].exists())
            self.assertFalse(paths[0].parent.exists())
            self.assertTrue(services._work_slot.acquire(blocking=False))
            services._work_slot.release()

    def test_budget_failure_cleans_up_before_returning_error(self):
        paths = []
        def engine(question, path, **options):
            paths.append(path)
            return extracted()
        with patch('src.multimodal.prepare_multimodal_input', side_effect=engine), \
             patch('api.services.ocr_budget', side_effect=RuntimeError('private-budget')):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertFalse(paths[0].parent.exists())

    def test_large_ocr_is_returned_for_editing_without_silent_truncation(self):
        text = 'palabra ' * 1500
        with patch('src.multimodal.prepare_multimodal_input', return_value=extracted(text)), \
             patch('api.services.resources') as resources:
            response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['texto_ocr'], text)
        self.assertFalse(response.json()['presupuesto']['admisible'])
        resources.assert_not_called()

    def test_busy_ocr_does_not_create_a_temporary_or_call_engine(self):
        services._work_slot.acquire()
        try:
            with patch('src.multimodal.prepare_multimodal_input') as engine, patch('api.uploads.TemporaryDirectory') as directory:
                response = self.post()
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.headers['Retry-After'], '2')
            engine.assert_not_called()
            directory.assert_not_called()
        finally:
            services._work_slot.release()

    def test_schema_exposes_multipart_and_valid_ocr_example(self):
        document = self.client.get('/api/v1/openapi.json').json()
        operation = document['paths']['/api/v1/ocr/extract/']['post']
        schema = operation['requestBody']['content']['multipart/form-data']['schema']
        self.assertEqual(schema['required'], ['imagen'])
        self.assertEqual(schema['properties']['imagen']['format'], 'binary')
        example = operation['responses']['200']['content']['application/json']['examples']['captura']['value']
        OCRResponse.model_validate(example)

    def test_query_rechecks_combined_ocr_budget_before_any_provider(self):
        import json
        with patch('api.services.retriever') as retriever, patch('src.rag.pipeline.run_rag_case') as pipeline:
            response = self.client.post('/api/v1/rag/query/', json.dumps({
                'pregunta': '¿Qué significa?', 'texto_ocr': 'palabra ' * 1000,
            }), content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error']['code'], 'input_too_large')
        retriever.assert_not_called()
        pipeline.assert_not_called()

    def test_query_forwards_reviewed_ocr_and_search_rejects_it(self):
        import json
        body = json.dumps({'pregunta': '¿Qué significa?', 'texto_ocr': 'Error 403'})
        with patch('api.services.run_query', side_effect=InputBudgetError('budget')) as query:
            response = self.client.post('/api/v1/rag/query/', body, content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(query.call_args.kwargs, {'ocr_text': 'Error 403'})
        response = self.client.post('/api/v1/rag/search/', body, content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 400)


class OCRBudgetTests(SimpleTestCase):
    def test_upload_handler_bounds_chunks_even_when_declared_file_size_is_wrong(self):
        with override_settings(OCR_MAX_UPLOAD_BYTES=8):
            handler = BoundedImageUploadHandler(None)
            handler.new_file('imagen', 'fake.png', 'image/png', 1)
            handler.receive_data_chunk(b'12345678', 0)
            with self.assertRaises(StopUpload):
                handler.receive_data_chunk(b'9', 8)
            self.assertEqual(handler.error.status, 413)
            self.assertTrue(handler.buffer.closed)

    def test_temporary_filename_is_server_owned(self):
        with temporary_ocr_image(upload(name='../../private.png')) as path:
            self.assertEqual(path.name, 'input.png')
            self.assertTrue(path.exists())
        self.assertFalse(path.parent.exists())

    def test_jpeg_and_webp_are_decoded_and_saved_with_server_owned_extensions(self):
        for format, extension, mime in [('JPEG', '.jpg', 'image/jpeg'), ('WEBP', '.webp', 'image/webp')]:
            with self.subTest(format=format):
                with temporary_ocr_image(upload(name='capture'+extension,
                        data=image_bytes(format), content_type=mime)) as path:
                    self.assertEqual(path.suffix, extension)
                    self.assertTrue(path.exists())
                self.assertFalse(path.parent.exists())

    def test_generation_budget_combines_both_fields_before_loading_or_calling_providers(self):
        with patch('api.services.retriever') as retriever, patch('src.rag.pipeline.run_rag_case') as pipeline:
            with self.assertRaises(InputBudgetError):
                services.run_query('¿Qué significa?', 'id', ocr_text='palabra ' * 1000)
        retriever.assert_not_called()
        pipeline.assert_not_called()

    def test_embedding_limit_checks_the_combined_content_before_supabase_or_groq(self):
        resources = local_resources(tokens=129)
        with patch('api.services.resources', return_value=resources), \
             patch('src.rag.repository.SupabaseRepository.connect') as connect, \
             patch('src.rag.pipeline.run_rag_case') as pipeline:
            with self.assertRaises(InputBudgetError):
                services.run_query('Pregunta corta', 'id', ocr_text='Texto visible')
        content = resources[0].count_tokens.call_args.args[0]
        self.assertIn('Pregunta corta', content)
        self.assertIn('Texto visible', content)
        connect.assert_not_called()
        pipeline.assert_not_called()

    def test_accepted_query_forwards_combined_text_without_running_ocr_twice(self):
        with patch('api.services.retriever') as retriever, patch('src.rag.pipeline.run_rag_case') as pipeline:
            services.run_query('Mi pregunta', 'id', ocr_text='Error 403')
        content = retriever.call_args.args[0]
        self.assertIn('Solicitud escrita por el usuario:\nMi pregunta', content)
        self.assertIn('Texto extraído de la imagen mediante OCR:\nError 403', content)
        self.assertEqual(pipeline.call_args.args[0]['input'], content)
        self.assertNotIn('image_path', pipeline.call_args.kwargs)

    def test_budget_preview_checks_embedding_and_avoids_model_load_for_excessive_input(self):
        with patch('api.services.resources', return_value=local_resources(tokens=129)):
            result = services.ocr_budget('Pregunta', 'texto OCR')
        self.assertFalse(result['admisible'])
        self.assertEqual(result['tokens_busqueda'], 129)
        self.assertEqual(result['limite_busqueda'], 128)
        with patch('api.services.resources') as resources:
            result = services.ocr_budget('Pregunta', 'palabra ' * 1500)
        self.assertFalse(result['admisible'])
        self.assertIsNone(result['tokens_busqueda'])
        resources.assert_not_called()

    def test_ocr_field_is_opt_in_only_for_queries(self):
        self.assertIsNone(QueryRequest(pregunta='Texto').texto_ocr)
        with self.assertRaises(ValidationError):
            QueryRequest(pregunta='Texto', texto_ocr='   ')
        with self.assertRaises(ValidationError):
            SearchRequest(pregunta='Texto', texto_ocr='No se ignora en búsqueda')

    def test_tesseract_timeout_is_bounded_and_errors_use_the_ocr_contract(self):
        from src.ocr.tesseract_strategy import TesseractStrategy
        from src.ocr.exceptions import OCRConfigurationError
        for timeout in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(OCRConfigurationError):
                TesseractStrategy(timeout=timeout)
        with temporary_ocr_image(upload()) as path, \
             patch.object(TesseractStrategy, '_get_tesseract_binary', return_value='/usr/bin/tesseract'), \
             patch('pytesseract.image_to_string', side_effect=RuntimeError('Tesseract process timeout')) as call:
            with self.assertRaises(OCRExtractionError):
                TesseractStrategy(timeout=3).extract(path)
        self.assertEqual(call.call_args.kwargs['timeout'], 3)

    def test_timeout_after_text_extraction_does_not_return_partial_success(self):
        from src.ocr.tesseract_strategy import TesseractStrategy
        with temporary_ocr_image(upload()) as path, \
             patch.object(TesseractStrategy, '_get_tesseract_binary', return_value='/usr/bin/tesseract'), \
             patch('pytesseract.image_to_string', return_value='Error 403'), \
             patch('pytesseract.image_to_data', side_effect=RuntimeError('Tesseract process timeout')) as blocks:
            with self.assertRaises(OCRExtractionError):
                TesseractStrategy(timeout=3).extract(path)
        self.assertEqual(blocks.call_args.kwargs['timeout'], 3)
        self.assertFalse(Path(path).exists())

    def test_interrupted_upload_releases_its_in_memory_buffer(self):
        handler = BoundedImageUploadHandler(Mock())
        handler.new_file('imagen', 'capture.png', 'image/png', None, None)
        handler.receive_data_chunk(b'partial image', 0)
        buffer = handler.buffer
        handler.upload_interrupted()
        self.assertTrue(buffer.closed)

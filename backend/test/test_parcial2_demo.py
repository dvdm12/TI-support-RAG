import unittest
from unittest.mock import Mock, patch

import numpy as np

from src.parcial2_demo import ProfessorDemo


class ProfessorDemoTests(unittest.TestCase):
    def setUp(self):
        self.demo = ProfessorDemo()

    def test_saved_case_has_real_passages_without_provider_calls(self):
        with patch('src.parcial2_demo.SupabaseRepository.connect') as connect, patch('src.parcial2_demo.SentenceEmbedder') as model:
            result = self.demo.saved_case('E06')
        self.assertEqual(result['mode'], 'saved_observation')
        self.assertTrue(result['sources'])
        self.assertEqual(result['provider_calls'], 0)
        connect.assert_not_called()
        model.assert_not_called()
        result['response']['respuesta'] = 'changed'
        self.assertNotEqual(self.demo.saved_case('E06')['response']['respuesta'], 'changed')

    def test_bm25_accepts_new_questions_without_model_or_generator(self):
        with patch('src.parcial2_demo.SentenceEmbedder') as model, patch('src.parcial2_demo.run_rag_case') as generator:
            result = self.demo.search('Mi impresora tiene trabajos pendientes en cola')
        self.assertEqual(result['method'], 'bm25')
        self.assertTrue(result['candidates'])
        self.assertFalse(result['answer_generated'])
        model.assert_not_called()
        generator.assert_not_called()

    def test_invalid_input_stops_before_model_or_auth(self):
        with patch('src.parcial2_demo.SentenceEmbedder') as model, patch('src.parcial2_demo.SupabaseRepository.connect') as connect:
            for question in ('', ' ', None, 'x' * 4001):
                with self.subTest(question_type=type(question).__name__), self.assertRaises(ValueError):
                    self.demo.search(question)
        connect.assert_not_called()
        model.assert_not_called()

    def configured_clients(self):
        first, second = Mock(owner_id='same-owner'), Mock(owner_id='same-owner')
        first.lexical_candidates.return_value = self.demo.inventory
        first.search.return_value = self.demo.inventory[:3]
        second.search.return_value = self.demo.inventory[:3]
        self.demo.embedder = Mock(spec=['assert_compatible', 'encode', 'count_tokens'])
        self.demo.embedder.encode.return_value = np.ones((1, 384)) / np.sqrt(384)
        return first, second

    def test_second_supabase_client_checks_persistence_without_upserts(self):
        first, second = self.configured_clients()
        with patch('src.parcial2_demo.SupabaseRepository.connect', side_effect=[first, second]):
            result = self.demo.prepare_supabase('¿Qué significa 403?')
        self.assertEqual(result['rows_verified'], 70)
        self.assertTrue(result['persistence_new_client'])
        self.assertFalse(result['second_client_upsert'])
        first.upsert.assert_not_called()
        second.upsert.assert_not_called()
        self.assertIs(self.demo.remote, first)

    def test_empty_professor_corpus_is_not_replaced_with_local(self):
        first, _ = self.configured_clients()
        first.lexical_candidates.return_value = []
        with patch('src.parcial2_demo.SupabaseRepository.connect', return_value=first), self.assertRaisesRegex(ValueError, 'usuario de Auth'):
            self.demo.prepare_supabase('Consulta')
        first.upsert.assert_not_called()
        self.assertIsNone(self.demo.remote)

    def test_second_client_mismatch_is_rejected(self):
        first, second = self.configured_clients()
        second.search.return_value = []
        with patch('src.parcial2_demo.SupabaseRepository.connect', side_effect=[first, second]), self.assertRaisesRegex(ValueError, 'segundo cliente'):
            self.demo.prepare_supabase('Consulta')

    def test_upload_requires_explicit_flag_and_only_first_client_writes(self):
        first, second = self.configured_clients()
        with patch('src.parcial2_demo.SupabaseRepository.connect', side_effect=[first, second]), patch(
                'src.parcial2_demo.load_index', return_value=(self.demo.corpus_id, self.demo.chunks,
                    np.ones((70,384)) / np.sqrt(384), self.demo.config)):
            result = self.demo.prepare_supabase('Consulta', upload=True)
        self.assertTrue(result['upsert_performed'])
        first.upsert.assert_called_once()
        second.upsert.assert_not_called()

    def test_live_export_uses_allowlist_instead_of_raw_provider_response(self):
        self.demo.embedder = Mock(spec=['assert_compatible', 'encode', 'count_tokens'])
        result = {'state':'ERROR_TECNICO', 'classification': None, 'documentary_output': None,
                  'failure_stage': 'generation', 'user_content_sent': 'context', 'usage': None,
                  'http': {'Authorization': 'secret-must-not-leak'},
                  'rag': {'candidates': [], 'catalog': {}, 'timings': {}}}
        with patch('src.parcial2_demo.run_rag_case', return_value=result):
            exported = self.demo.query('¿Cómo recupero mi contraseña?')
        self.assertNotIn('http', exported)
        self.assertNotIn('secret-must-not-leak', str(exported))
        self.assertEqual(exported['failure_stage'], 'generation')

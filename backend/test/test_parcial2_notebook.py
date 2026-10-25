"""Integrity and safety checks for the notebook and its inspectable resource ZIP."""
import ast
import hashlib
import io
import json
import unittest
import os
from unittest.mock import patch
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Parcial2NotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads((ROOT / 'notebooks/parcial2.ipynb').read_text())
        cls.cells = {c['id']: ''.join(c['source']) for c in cls.notebook['cells']}
        tree = ast.parse(cls.cells['paquete'])
        assignments = {node.targets[0].id: ast.literal_eval(node.value)
                       for node in tree.body if isinstance(node, ast.Assign)
                       and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id == 'BUNDLE_SHA256'}
        cls.raw = (ROOT / 'notebooks/parcial2_recursos.zip').read_bytes()
        cls.expected_hash = assignments['BUNDLE_SHA256']
        helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'restore_resources')
        namespace = dict(Path=Path, hashlib=hashlib, zipfile=zipfile, io=io, json=json)
        exec(compile(ast.Module(body=[helper], type_ignores=[]), 'restore_resources', 'exec'), namespace)
        cls.restore = staticmethod(namespace['restore_resources'])

    def test_notebook_has_twelve_class09_sections_and_compiles(self):
        self.assertEqual(self.notebook['nbformat'], 4)
        self.assertIn('# Parcial 2', self.cells['portada'])
        for number in range(1, 13):
            self.assertIn(f'## {number}.', self.cells[f'punto-{number}'])
        for cell in self.notebook['cells']:
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), cell['id'], 'exec')

    def test_bundle_hash_and_all_member_hashes(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), self.expected_hash)
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive:
            manifest = json.loads(archive.read('bundle_manifest.json'))
            self.assertEqual(set(manifest) | {'bundle_manifest.json'}, set(archive.namelist()))
            for name, digest in manifest.items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest, name)

    def test_notebook_sources_have_no_embedded_base64_payload(self):
        for source in self.cells.values():
            self.assertNotIn('BUNDLE_B64', source)
            self.assertNotIn('base64.b64decode', source)
            self.assertLess(len(source), 15000)

    def test_restore_verifies_before_extracting_and_rejects_a_different_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'resources'
            with self.assertRaisesRegex(ValueError, 'no corresponde'):
                self.restore(self.raw + b'changed', self.expected_hash, root)
            self.assertFalse(root.exists())
            manifest = self.restore(self.raw, self.expected_hash, root)
            self.assertTrue((root / 'backend/data/indexes/sections/vectors.npy').is_file())
            self.assertEqual(len(list(p for p in root.rglob('*') if p.is_file())), len(manifest) + 1)

    def test_restore_rejects_manifest_mismatch_before_extracting(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('bundle_manifest.json', json.dumps({'example.txt': hashlib.sha256(b'correct').hexdigest()}))
            archive.writestr('example.txt', b'changed')
        raw = data.getvalue()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'resources'
            with self.assertRaisesRegex(ValueError, 'distinto del manifiesto'):
                self.restore(raw, hashlib.sha256(raw).hexdigest(), root)
            self.assertFalse(root.exists())

    def test_bundle_has_no_secrets_reserve_agents_or_external_pdf(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive:
            names = archive.namelist()
            for name in names:
                path = Path(name)
                self.assertFalse(path.is_absolute())
                self.assertNotIn('..', path.parts)
                self.assertFalse(any(p.startswith('.env') or p in {'.agents', '.aws', '.git'} for p in path.parts))
                self.assertNotIn('rag_reserve', name)
            pdfs = [n for n in names if n.endswith('.pdf')]
            self.assertEqual(len(pdfs), 7)
            self.assertTrue(all(n.startswith('backend/data/corpus/v2/') for n in pdfs))
            self.assertIn('infra/supabase/migrations/20261014_documentary_rag.sql', names)
            self.assertEqual(json.loads(archive.read('backend/data/indexes/sections/config.json'))['config']['dimension'], 384)

    def test_default_mode_uses_groq_and_supabase_without_automatic_upload(self):
        tree = ast.parse(self.cells['configuracion'])
        literals = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                try:
                    literals[node.targets[0].id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass
        self.assertEqual(literals['MODE'], 'consulta_real')
        self.assertTrue(literals['USE_SUPABASE'])
        self.assertFalse(literals['ALLOW_SUPABASE_UPSERT'])
        self.assertFalse(self.notebook['metadata']['parcial2']['human_review_completed'])
        self.assertFalse(self.notebook['metadata']['parcial2']['reserve_executed'])

    def test_professor_form_starts_with_remote_query_and_uses_own_secrets(self):
        tree = ast.parse(self.cells['panel-profesor'])
        action = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'ACCION')
        self.assertEqual(ast.literal_eval(action.value), 'Consultar con Groq')
        remote = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'USAR_SUPABASE')
        self.assertTrue(ast.literal_eval(remote.value))
        self.assertIn('load_own_secrets(names)', self.cells['panel-profesor'])
        self.assertIn('userdata.get(name)', self.cells['modelo-secretos'])
        self.assertIn('hashlib.sha256(downloaded).hexdigest() != BUNDLE_SHA256', self.cells['paquete'])

    def results_locator(self):
        tree = ast.parse(self.cells['configuracion'])
        helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'results_root')
        namespace = dict(Path=Path, os=os)
        exec(compile(ast.Module(body=[helper], type_ignores=[]), 'paths', 'exec'), namespace)
        return namespace['results_root']

    def test_results_stay_in_backend_docs_from_all_supported_start_directories(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            backend = root / 'backend'
            (backend / 'src/rag').mkdir(parents=True)
            (backend / 'notebooks').mkdir()
            (backend / 'requirements-parcial2.txt').touch()
            locate = self.results_locator()
            for start in [root, backend, backend / 'notebooks']:
                with self.subTest(start=start):
                    self.assertEqual(locate(start, False), backend / 'docs/parcial2')
            self.assertEqual(locate(root / 'standalone', False), root / 'standalone/backend/docs/parcial2')
            self.assertEqual(locate(root, True), Path('/content/parcial2/backend/docs/parcial2'))

    def test_custom_results_directory_is_independent_of_temporary_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'professor-results'
            with patch.dict(os.environ, {'PARCIAL2_OUTPUT_DIR': str(target), 'PARCIAL2_WORKDIR': '/tmp/unrelated'}):
                self.assertEqual(self.results_locator()(Path(directory), False), target)
                self.assertEqual(self.results_locator()(Path(directory), True), target)

    def secret_loader(self, env_file):
        tree = ast.parse(self.cells['modelo-secretos'])
        helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'load_own_secrets')
        namespace = dict(IN_COLAB=False, LOCAL_ENV_FILE=env_file, os=os)
        exec(compile(ast.Module(body=[helper], type_ignores=[]), 'secrets', 'exec'), namespace)
        return namespace['load_own_secrets']

    def test_local_secrets_survive_extraction_directory_and_preserve_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / '.env'
            env_file.write_text('GROQ_API_KEY=fixture-file\nSUPABASE_URL=https://fixture.invalid\n')
            loader = self.secret_loader(env_file)
            with patch.dict(os.environ, {'GROQ_API_KEY': 'fixture-environment'}, clear=True):
                with patch('builtins.print') as output:
                    loader(['GROQ_API_KEY', 'SUPABASE_URL'])
                self.assertEqual(os.environ['GROQ_API_KEY'], 'fixture-environment')
                self.assertEqual(os.environ['SUPABASE_URL'], 'https://fixture.invalid')
                self.assertNotIn('fixture', str(output.call_args_list))

    def test_missing_local_credentials_stop_with_configuration_instructions(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'GROQ_API_KEY.*PARCIAL2_ENV_FILE'):
                self.secret_loader(None)(['GROQ_API_KEY'])
        with self.assertRaisesRegex(RuntimeError, 'No existe.*PARCIAL2_ENV_FILE'):
            self.secret_loader(Path('/nonexistent/parcial2/.env'))(['GROQ_API_KEY'])

    def test_snapshot_copies_original_api_answers_but_no_arbitrary_headers(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive:
            api = json.loads(archive.read('backend/docs/parcial2/evidencias/parcial2_saved_api.json'))
            review = json.loads(archive.read('backend/docs/human_review/class09_review_v1.json'))
            expected = {r['case_id']: r['response'] for r in review['rows'] if r['variant'] == 'API_system_v8'}
            self.assertEqual(len(api['cases']), 13)
            allowed = {'id','status','http_seconds','expected_states','estado','clasificacion',
                       'respuesta_documental','fuentes','tiempos_segundos'}
            for row in api['cases']:
                self.assertEqual(set(row), allowed)
                self.assertEqual(row['respuesta_documental'], expected[row['id']])

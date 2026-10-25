"""Integrity and safety checks for the notebook and its inspectable resource ZIP."""
import ast
import hashlib
import io
import json
import unittest
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

    def test_default_mode_cannot_call_providers_or_write_supabase(self):
        tree = ast.parse(self.cells['configuracion'])
        literals = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                try:
                    literals[node.targets[0].id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass
        self.assertEqual(literals['MODE'], 'evidencia_guardada')
        self.assertFalse(literals['USE_SUPABASE'])
        self.assertFalse(literals['ALLOW_SUPABASE_UPSERT'])
        self.assertFalse(self.notebook['metadata']['parcial2']['human_review_completed'])
        self.assertFalse(self.notebook['metadata']['parcial2']['reserve_executed'])

    def test_professor_form_starts_in_saved_mode_and_uses_own_secrets(self):
        tree = ast.parse(self.cells['panel-profesor'])
        action = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'ACCION')
        self.assertEqual(ast.literal_eval(action.value), 'Caso guardado')
        self.assertIn('load_own_secrets(names)', self.cells['panel-profesor'])
        self.assertIn('userdata.get(name)', self.cells['modelo-secretos'])
        self.assertIn('hashlib.sha256(downloaded).hexdigest() != BUNDLE_SHA256', self.cells['paquete'])

    def test_snapshot_copies_original_api_answers_but_no_arbitrary_headers(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive:
            api = json.loads(archive.read('backend/docs/parcial2_saved_api.json'))
            review = json.loads(archive.read('backend/docs/human_review/class09_review_v1.json'))
            expected = {r['case_id']: r['response'] for r in review['rows'] if r['variant'] == 'API_system_v8'}
            self.assertEqual(len(api['cases']), 13)
            allowed = {'id','status','http_seconds','expected_states','estado','clasificacion',
                       'respuesta_documental','fuentes','tiempos_segundos'}
            for row in api['cases']:
                self.assertEqual(set(row), allowed)
                self.assertEqual(row['respuesta_documental'], expected[row['id']])

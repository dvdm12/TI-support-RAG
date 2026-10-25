import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from scripts import validate_lab as lab


class LabValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'backend'
        raw = (lab.ROOT / 'notebooks/parcial2_recursos.zip').read_bytes()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            archive.extractall(Path(self.tmp.name))
        (self.root / 'notebooks').mkdir()
        for name in ['parcial2.ipynb', 'parcial2_recursos.zip']:
            shutil.copyfile(lab.ROOT / 'notebooks' / name, self.root / 'notebooks' / name)

    def test_clean_checkout_reconstructs_the_same_index_without_private_files(self):
        shutil.rmtree(self.root / 'data/indexes')
        result = lab.prepare(self.root)
        self.assertTrue(result['passed'])
        self.assertEqual(result['chunks'], 70)
        self.assertFalse((self.root / '.env').exists())
        self.assertFalse((self.root / 'docs/rag_runs').exists())
        self.assertEqual(lab.prepare(self.root), result)

    def test_index_drift_is_rejected_without_overwriting_it(self):
        path = self.root / 'data/indexes/sections/records.json'
        path.write_text('[]')
        with self.assertRaisesRegex(ValueError, 'No se sobrescribe'):
            lab.prepare(self.root)
        self.assertEqual(path.read_text(), '[]')

    def test_stale_bundle_cannot_mask_changed_or_new_backend_code(self):
        path = self.root / 'src/config.py'
        original = path.read_bytes()
        path.write_bytes(original + b'\n# changed\n')
        with self.assertRaisesRegex(ValueError, 'código del checkout'):
            lab.prepare(self.root)
        path.write_bytes(original)
        (self.root / 'src/new_component.py').write_text('x = 1\n')
        with self.assertRaisesRegex(ValueError, 'omite código'):
            lab.prepare(self.root)

    def test_full_lab_is_not_approved_from_green_technical_checks_alone(self):
        output = Path(self.tmp.name) / 'reports'
        for name in ['prepare', 'unit', 'notebook', 'http']:
            lab.write_json(output / (name + '.json'), {'passed': True, 'live': False})
        env = {'LAB_' + n + '_OUTCOME': 'success' for n in ['INSTALL', 'DJANGO', 'API_TESTS', 'DOCKER_BUILD', 'DOCKER_START']}
        with patch.object(lab, 'ROOT', self.root), patch.dict(os.environ, env, clear=True):
            result = lab.compliance(output)
            self.assertTrue(result['technical_passed'])
            self.assertFalse(result['complete_lab'])
            self.assertFalse(result['external_services_verified'])
            os.environ['LAB_DOCKER_BUILD_OUTCOME'] = 'skipped'
            self.assertFalse(lab.compliance(output)['technical_passed'])

    def test_nested_zip_secrets_block_artifact_publication(self):
        output = Path(self.tmp.name) / 'artifacts'
        output.mkdir()
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, 'w') as archive:
            archive.writestr('response.json', '{"leak":"fixture-secret-only-for-tests"}')
        with zipfile.ZipFile(output / 'outer.zip', 'w') as archive:
            archive.writestr('inner.zip', inner.getvalue())
        with patch.object(lab, 'ROOT', self.root), patch.dict(os.environ, {'GROQ_API_KEY': 'fixture-secret-only-for-tests'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'Credencial detectada'):
                lab.scan_artifacts(output)

    def test_real_notebook_requires_all_five_secrets_before_starting_a_kernel(self):
        with patch.object(lab, 'ROOT', self.root), patch.dict(os.environ, {}, clear=True), patch('jupyter_client.KernelManager') as kernel:
            with self.assertRaisesRegex(ValueError, 'Faltan secretos'):
                lab.execute_notebook(Path(self.tmp.name) / 'run', live=True)
            kernel.assert_not_called()

    def test_http_200_without_evidence_is_not_a_successful_integration(self):
        # Readiness + health + Swagger + OpenAPI + unauthorized + categories + search.
        responses = [Mock(status_code=200)] * 4 + [Mock(status_code=401), Mock(status_code=200), Mock(status_code=200)]
        responses[-1].json.return_value = {'pasajes': []}
        session = Mock()
        session.get.return_value = Mock(status_code=200)
        # The readiness request uses .get; all checks use .request.
        session.request.side_effect = responses[1:]
        with patch('requests.Session', return_value=session), patch.dict(os.environ, {'DJANGO_API_TOKEN': 'fixture-token'}, clear=True), patch('dotenv.load_dotenv'):
            with self.assertRaisesRegex(ValueError, 'pasajes completos'):
                lab.http_checks('http://localhost/api/v1', live=True)

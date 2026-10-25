"""Matrix exports stay source-based, automatic, and explicit about missing data."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pdfplumber
from scripts import evaluate_retrieval_metrics as evaluator
from src.rag.config import ROOT


class RetrievalPDFTests(unittest.TestCase):
    def setUp(self):
        self.report=json.loads((ROOT/'docs/evaluacion/recuperacion/retrieval_metrics_20261021.json').read_text())

    def text(self,path):
        with pdfplumber.open(path) as doc:
            return '\n'.join(page.extract_text() or '' for page in doc.pages)

    def test_evaluation_export_always_writes_three_formats(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'matrix.json'
            pdf=evaluator.write_outputs(self.report,output)
            self.assertEqual(pdf,output.with_suffix('.pdf'))
            self.assertTrue(output.with_suffix('.csv').exists())
            self.assertEqual(json.loads(output.read_text()),self.report)
            text=self.text(pdf)
            self.assertIn('47,62%',text)
            self.assertIn('52,38%',text)
            self.assertIn('0,8571',text)
            self.assertIn('Revisión humana pendiente',text)
            self.assertIn('N/E',text)
            self.assertIn('E13',text)

    def test_saved_json_render_never_initializes_model_or_providers(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'saved.json';output.write_text(json.dumps(self.report))
            before=output.read_bytes()
            with patch('sys.argv',['evaluate','--from-json',str(output)]),patch.object(evaluator,'SentenceEmbedder') as model,patch.object(evaluator.SupabaseRepository,'connect') as connect,patch.object(evaluator,'validate') as validate:
                evaluator.main()
                model.assert_not_called();connect.assert_not_called();validate.assert_not_called()
            self.assertEqual(before,output.read_bytes())
            self.assertTrue(output.with_suffix('.pdf').exists())

    def test_incomplete_evaluation_keeps_errors_and_unevaluable_cells(self):
        report=copy.deepcopy(self.report)
        report.update(status='incomplete_technical_errors',technical_errors=1)
        failed=report['cases'][0]
        failed.update(error={'type':'TimeoutError'},variants={})
        behavior=next(c for c in report['cases'] if not c['retrieval_evaluable'])
        report['cases']=[failed,behavior]
        for aggregate in report['aggregate'].values():
            aggregate['paired_valid_cases']=0
            aggregate['metrics_at_3']={key:None for key in aggregate['metrics_at_3']}
            for key in ('context_coverage_mean','candidate_coverage_mean','retrieval_seconds_median'):
                aggregate[key]=None
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'incomplete.json'
            pdf=evaluator.write_outputs(report,output)
            text=self.text(pdf)
        self.assertIn('INCOMPLETO',text)
        self.assertIn('ERROR',text)
        self.assertIn('N/E',text)
        self.assertNotIn('0,00%',text)

import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import pdfplumber
from src.config import MODEL
from src.rag.config import ROOT
from src.rag.token_comparison import observe, summarize, valid_usage, VARIANTS
from scripts.compare_generation_tokens import prepare, write_outputs


class TokenComparisonTests(unittest.TestCase):
    def setUp(self):
        self.report=prepare(ROOT/'docs/evaluacion/recuperacion/coverage_improvements_20261021.json',ROOT/'cases/rag_evidence.json')

    def observed(self,prompt=10,completion=4,status='contract_valid'):
        return {'status':status,'usage':{'prompt_tokens':prompt,'completion_tokens':completion,'total_tokens':prompt+completion},
                'usage_valid':True,'model':MODEL,'http_status':200}

    def test_usage_must_be_actual_consistent_integer_counts(self):
        self.assertTrue(valid_usage(self.observed()['usage']))
        for usage in (None,{}, {'prompt_tokens':True,'completion_tokens':1,'total_tokens':2},
                      {'prompt_tokens':10,'completion_tokens':4,'total_tokens':13}):
            self.assertFalse(valid_usage(usage))

    def test_paired_denominator_and_invalid_outputs_still_consume_tokens(self):
        self.report['cases']=self.report['cases'][:2]
        for name in VARIANTS:
            self.report['cases'][0]['variants'][name]['observations']=[self.observed(status='invalid_documentary')]
        self.report['cases'][0]['variants'][VARIANTS[1]]['observations']=[self.observed(12,5)]
        self.report['cases'][1]['variants'][VARIANTS[0]]['observations']=[self.observed(20,8)]
        result=summarize(self.report)
        self.assertEqual(result['paired_measured_cases'],1)
        self.assertEqual(result['paired_difference']['total_tokens']['mean'],3)
        self.assertEqual(result['variants'][VARIANTS[0]]['paired_usage']['total_tokens']['sum'],14)
        self.assertEqual(result['variants'][VARIANTS[0]]['all_observed_usage']['total_tokens'],42)

    def test_missing_usage_is_not_zero_and_empty_pairs_are_unevaluable(self):
        result=summarize(self.report)
        self.assertEqual(result['paired_measured_cases'],0)
        self.assertIsNone(result['variants'][VARIANTS[0]]['paired_usage']['total_tokens']['sum'])
        self.assertIsNone(result['paired_difference']['total_tokens']['mean'])

    def test_prepare_uses_development_and_equal_generation_contract(self):
        self.assertEqual(len(self.report['cases']),7)
        self.assertFalse(self.report['reserve_executed'])
        for case in self.report['cases']:
            self.assertEqual(case['split'],'development')
            for name in VARIANTS:
                self.assertLessEqual(case['variants'][name]['local_input_budget']['total_tokens'],850)
                self.assertEqual(case['variants'][name]['observations'],[])

    def test_real_client_adapter_retains_usage_when_documentary_contract_is_invalid(self):
        response=MagicMock(status_code=200,ok=True,headers={})
        response.json.return_value={'model':MODEL,'usage':self.observed()['usage'],
            'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}
        with patch('src.groq_client.build_headers',return_value={}),patch('src.groq_client.send_request',return_value=response) as send:
            result=observe('Reglas','Pregunta',{},MODEL,session_factory=MagicMock())
        self.assertEqual(result['status'],'invalid_documentary')
        self.assertTrue(result['usage_valid'])
        self.assertEqual(result['usage']['total_tokens'],14)
        send.assert_called_once()

    def test_rate_limit_body_is_not_exported_or_retried(self):
        response=MagicMock(status_code=429,ok=False,headers={'retry-after':'30'})
        with patch('src.groq_client.build_headers',return_value={}),patch('src.groq_client.send_request',return_value=response) as send:
            result=observe('Reglas','Pregunta',{},MODEL,session_factory=MagicMock())
        send.assert_called_once()
        response.json.assert_not_called()
        self.assertIsNone(result['usage'])
        self.assertEqual(result['status'],'provider_error')
        self.assertEqual(result['headers']['retry-after'],'30')

    def test_checkpoint_always_writes_all_formats_and_marks_unknown_usage(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'tokens.json'
            pdf=write_outputs(copy.deepcopy(self.report),output)
            with output.with_suffix('.csv').open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),14)
            self.assertTrue(all(r['total_tokens']=='' for r in rows))
            saved=json.loads(output.read_text())
            self.assertEqual(saved['status'],'incomplete')
            with pdfplumber.open(pdf) as doc:text='\n'.join(p.extract_text() or '' for p in doc.pages)
            self.assertIn('MEDICIÓN INCOMPLETA',text)
            self.assertIn('N/E',text)
            self.assertIn('Revisión humana pendiente',text)

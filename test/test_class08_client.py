import json
import unittest
from unittest.mock import Mock
import numpy as np
from src.class08_client import execute_query, recover, verify_new_client
from src.rag.models import Candidate

class Class08ClientTests(unittest.TestCase):
    def setUp(self):
        self.candidate=Candidate(chunk_id='test-1',content='El 403 no demuestra suspensión.',similitud=0.7,
            metadata={'document_id':'test','category':'acceso','source':'test.pdf','section':'ACS-03',
                      'version':'test','source_hash':'a'*64,'pages':[1]})
        self.repository=Mock(owner_id='owner')
        self.repository.search.return_value=[self.candidate]
        self.embedder=Mock(spec=['assert_compatible','encode'])
        self.embedder.encode.return_value=np.ones((1,384))/np.sqrt(384)
        self.generator=Mock(return_value={'raw_output':json.dumps({'estado':'respondida',
            'respuesta':'El 403 no demuestra suspensión. [F1]','citas':['F1'],'limitacion':''}),
            'finish_reason':'stop','model':'test','usage':{'prompt_tokens':700},'http':{'status_code':200}})
    def query(self):
        return execute_query('¿Qué significa 403?',self.repository,self.embedder,'test-corpus',Mock(),generator=self.generator)
    def test_exact_rpc_and_single_call(self):
        self.assertEqual(self.query()['status'],'ACCEPTED')
        self.repository.search.assert_called_once()
        self.repository.lexical_search.assert_not_called()
        self.generator.assert_called_once()
        self.assertEqual(self.generator.call_args.kwargs['max_retries'],0)
    def test_invalid_citation_does_not_export_rejected_output(self):
        self.generator.return_value['raw_output']=json.dumps({'estado':'respondida',
            'respuesta':'Texto rechazado. [F99]','citas':['F99'],'limitacion':''})
        result=self.query()
        self.assertEqual(result['failure_stage'],'validation')
        self.assertIsNone(result['resultado'])
        self.assertNotIn('Texto rechazado',json.dumps(result))
    def test_quota_failure_without_secret_leak(self):
        self.generator.side_effect=RuntimeError('HTTP 429 password=must-not-leak')
        result=self.query()
        self.assertEqual(result['status'],'ERROR_TECNICO')
        self.assertEqual(result['http_status'],429)
        self.assertIsNone(result['resultado'])
        self.assertNotIn('must-not-leak',json.dumps(result))
    def test_empty_input_never_calls_rpc(self):
        with self.assertRaises(ValueError):recover(' ',self.repository,self.embedder,'test',Mock())
        self.repository.search.assert_not_called()
    def test_incomplete_output_rejected(self):
        self.generator.return_value['finish_reason']='length'
        self.assertIsNone(self.query()['resultado'])
    def test_provider_input_budget_rejected(self):
        self.generator.return_value['usage']['prompt_tokens']=1001
        self.assertIsNone(self.query()['resultado'])
    def test_persistence_must_match_actual_content_without_upsert(self):
        second=Mock(owner_id='owner')
        second.search.return_value=[self.candidate.model_copy(update={'content':'Otro texto'})]
        with self.assertRaises(RuntimeError):
            verify_new_client('403',[self.candidate],self.repository,second,self.embedder,'test',Mock())
        second.upsert.assert_not_called()
    def test_persistence_same_user_required(self):
        with self.assertRaises(RuntimeError):
            verify_new_client('403',[self.candidate],self.repository,Mock(owner_id='other'),self.embedder,'test',Mock())

if __name__=='__main__':unittest.main()

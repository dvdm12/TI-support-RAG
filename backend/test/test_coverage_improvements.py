import json
import unittest
from unittest.mock import Mock, patch
from src.rag.config import ROOT
from src.rag.lexical import tokens, rank
from src.rag.models import Candidate
from src.rag.retrieval import Retriever
from src.rag.applicability import applicable_candidates
from src.rag.context import build_context
from src.token_budget import input_budget
from src.groq_client import build_payload
from schemas.rag_response_v1 import RespuestaRAG
from scripts.evaluate_coverage_improvements import observation
from test.test_rag import FakeEmbedder, config


class CoverageImprovementTests(unittest.TestCase):
    def test_technical_tokens_survive_variations_and_keep_exact_codes(self):
        self.assertEqual(tokens('Wi-Fi'),tokens('WIFI'))
        self.assertEqual(tokens('wi fi'),tokens('Wi-Fi'))
        self.assertIn('mp-4002',tokens('MP-4002'))
        self.assertIn('403',tokens('Error 403'))
        self.assertNotEqual(tokens('MP-4002'),tokens('MP-5002'))
        wifi=Candidate(chunk_id='wifi',content='Conexión Wi-Fi autorizada.',metadata={},similitud=0)
        self.assertEqual(rank('wifi',[wifi]),[wifi])

    def test_applicability_filters_union_before_top_k_and_refills(self):
        candidates=[Candidate(chunk_id=str(i),content='Texto de prueba '+str(i),
            metadata={'section':'Credenciales posiblemente expuestas' if i<3 else 'Mensaje sospechoso'},similitud=0)
            for i in range(6)]
        repository=Mock();repository.search.return_value=candidates
        repository.lexical_candidates.return_value=candidates
        with patch('src.rag.retrieval.rank',return_value=candidates):
            selected,_=Retriever(repository,FakeEmbedder(),'test',config()).retrieve('Mensaje con adjunto sin abrir.')
        self.assertEqual(len(selected),3)
        self.assertTrue(all(int(c.chunk_id)>=3 for c in selected))
        repository.search.assert_called_once();repository.lexical_candidates.assert_called_once()

    def test_reported_exposure_keeps_the_password_route(self):
        candidate=Candidate(chunk_id='exposure',content='Reporta la exposición.',
                            metadata={'section':'Credenciales posiblemente expuestas'},similitud=0)
        self.assertEqual(applicable_candidates('No abrí el enlace pero compartí mi contraseña por teléfono.',[candidate])[0],[candidate])
        self.assertEqual(applicable_candidates('Adjunto sospechoso sin abrir.',[candidate])[0],[])

    def test_smaller_prompt_preserves_whole_passages_and_missing_data(self):
        source=json.loads((ROOT/'docs/evaluacion/recuperacion/retrieval_metrics_20261021.json').read_text())
        case=next(c for c in source['cases'] if c['id']=='E04')
        candidates=[]
        for ident in case['variants']['B_hybrid_rrf']['selected_ids']:
            record=source['candidate_catalog'][ident]
            candidates.append(Candidate(chunk_id=ident,content=record['text'],metadata=record,similitud=0))
        units=json.loads((ROOT/'cases/rag_evidence.json').read_text())['cases'][3]['required_information_units']
        old=observation(case['question'],candidates,units,(ROOT/'prompts/rag_v5.md').read_text())
        new=observation(case['question'],candidates,units,(ROOT/'prompts/rag_v6.md').read_text())
        self.assertLess(len(old['context_ids']),len(new['context_ids']))
        self.assertTrue(new['coverage_completeness']['context']['complete'])
        prompt=(ROOT/'prompts/rag_v6.md').read_text()
        fmt={'type':'json_schema','json_schema':{'name':'respuesta_rag','strict':True,'schema':RespuestaRAG.model_json_schema()}}
        fits=lambda text:input_budget(build_payload(prompt,text,response_format=fmt))['total_tokens']<=850
        classification={'categoria':'cuentas','datos_faltantes':['¿Qué mensaje observas?']}
        context=build_context(case['question'],candidates,classification=classification,request_fits=fits)
        payload=json.loads(context['user_content'])
        self.assertEqual(payload['clasificacion']['datos_faltantes'],classification['datos_faltantes'])
        for passage,candidate in zip(payload['evidencia'],context['catalog'].values()):
            self.assertEqual(passage['texto'],candidate.content)
        self.assertTrue(fits(context['user_content']))

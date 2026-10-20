import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np
from src.rag.config import EMBEDDING_MODEL, RAGConfig
from src.rag.models import Section, EmbeddingConfig
from src.rag.embeddings import validate_vectors, SentenceEmbedder
from src.rag.chunking import fragment_sections
from src.rag.ingestion import load_corpus, clean_text
from src.rag.index import save_index, load_index
from src.rag.repository import LocalRepository, SupabaseRepository, rpc_params, RepositoryError
from src.rag.retrieval import Retriever
from src.rag.context import build_context
from src.rag.citations import validate_response
from src.rag.pipeline import run_rag_case
from src.rag.comparison import compare_strategies
from src.pipeline import run_case
from src.groq_client import build_payload

class FakeEmbedder:
    """Control fixture, never presented as semantic model evidence."""
    model_name = EMBEDDING_MODEL
    revision = 'a'*40
    max_seq_length = 128
    def count_tokens(self, text): return len(text.split()) + 2
    def encode(self, texts):
        if any(not t.strip() or self.count_tokens(t)>128 for t in texts): raise ValueError('input')
        rows=[]
        for text in texts:
            row=np.zeros(384,dtype=float)
            row[:32]=np.frombuffer(hashlib.sha256(text.encode()).digest(),dtype=np.uint8).astype(float)+1
            rows.append(row/np.linalg.norm(row))
        return np.asarray(rows)
    def assert_compatible(self, config): SentenceEmbedder.assert_compatible(self, config)

def config(strategy='sections'):
    return EmbeddingConfig(modelo=EMBEDDING_MODEL, revision='a'*40,max_seq_length=128,
        estrategia=strategy,chunk_chars=160,overlap_chars=30,max_tokens=40)

def section():
    return Section(document_id='TI-ACS',source='acceso/manual_acceso.pdf',title='Acceso',
        section='ACS-03 | Error 403',category='acceso',version='2.0',source_hash='b'*64,pages=[1],
        text='Un error 403 no confirma que la cuenta esté suspendida. Soporte revisa los permisos.\n\nNo se evade la autorización del recurso.')

def setup_index():
    e=FakeEmbedder();cfg=config();chunks=fragment_sections([section()],e,cfg)
    vectors=e.encode([c.text for c in chunks]);repo=LocalRepository()
    repo.upsert('test-construction',chunks,vectors,cfg)
    return e,cfg,chunks,vectors,repo

class TestIngestion(unittest.TestCase):
    def test_seven_real_pdfs_sections_negation(self):
        sections=load_corpus(RAGConfig().manifest)
        self.assertEqual(len(sections),35)
        self.assertEqual(len({s.document_id for s in sections}),7)
        self.assertEqual({s.category for s in sections},{'hardware','software','redes','cuentas','seguridad','acceso','otros'})
        target=next(s for s in sections if s.section.startswith('ACS-03'))
        self.assertIn('no confirma que la cuenta esté suspendida',target.text)
        self.assertEqual(target.pages,[1])
        self.assertFalse(any('Página 1' in s.text or 'Continuación ·' in s.text for s in sections))
    def test_cleaning(self):
        self.assertEqual(clean_text(' No   se\n entrega.\n\nSi falta, no continúa. '),'No se entrega.\n\nSi falta, no continúa.')
    def test_changed_source_and_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);doc={'document_id':'one','path':'manual.pdf','sha256':'0'*64}
            (root/'manual.pdf').write_bytes(b'changed')
            (root/'manifest.json').write_text(json.dumps({'documents':[doc]}))
            with self.assertRaisesRegex(ValueError,'cambió'):load_corpus(root/'manifest.json')
            doc['path']='../outside.pdf'
            (root/'manifest.json').write_text(json.dumps({'documents':[doc]}))
            with self.assertRaisesRegex(ValueError,'dentro'):load_corpus(root/'manifest.json')

class TestIndex(unittest.TestCase):
    def test_stable_ids_budget_and_overlap(self):
        text=section().model_copy(update={'text':' '.join(['condición no se omite']*60)})
        for name in ('characters','overlap','sections'):
            e=FakeEmbedder();cfg=config(name);chunks=fragment_sections([text],e,cfg)
            self.assertGreater(len(chunks),1)
            self.assertEqual(chunks,fragment_sections([text],e,cfg))
            self.assertTrue(all(c.tokens<=40 for c in chunks))
            self.assertTrue(all('Acceso / ACS-03' in c.text for c in chunks))
        with self.assertRaises(ValueError):
            fragment_sections([text],e,config('overlap').model_copy(update={'overlap_chars':160}))
    def test_roundtrip_and_corruption(self):
        e,cfg,chunks,vectors,_=setup_index()
        with tempfile.TemporaryDirectory() as tmp:
            cid=save_index(tmp,chunks,vectors,cfg)
            actual,loaded,matrix,_=load_index(tmp,e)
            self.assertEqual(cid,actual);self.assertEqual(loaded,chunks)
            np.testing.assert_allclose(matrix,vectors)
            np.save(Path(tmp)/'vectors.npy',matrix[::-1])
            with self.assertRaisesRegex(ValueError,'alterada'):load_index(tmp,e)
    def test_invalid_vectors(self):
        for matrix in (np.ones((1,383)),np.zeros((1,384)),np.full((1,384),np.nan),np.ones((1,384),dtype=int)):
            with self.assertRaises(ValueError):validate_vectors(matrix,1)
    def test_incompatible_revision(self):
        with self.assertRaises(ValueError):FakeEmbedder().assert_compatible(config().model_copy(update={'revision':'c'*40}))
    def test_comparison_no_automatic_winner(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=compare_strategies([section()],FakeEmbedder(),[{'question':'error 403','expected_section':'ACS-03','condition':'no confirma'}],tmp)
        self.assertIsNone(result['winner'])
        self.assertEqual(len({v['corpus_id'] for v in result['strategies'].values()}),3)
        self.assertTrue(all(v['trials'][0]['condition_in_single_chunk'] for v in result['strategies'].values()))

class TestRepository(unittest.TestCase):
    def test_repeat_upsert_variants(self):
        e,cfg,chunks,vectors,repo=setup_index()
        repo.upsert('test-construction',chunks,vectors,cfg)
        self.assertEqual(len(repo.rows),len(chunks))
        repo.upsert('variant',chunks,vectors,cfg)
        self.assertEqual(len(repo.search('variant',vectors[0],cfg)),len(chunks))
        with self.assertRaises(RepositoryError):repo.search('absent',vectors[0],cfg)
    def test_rpc_contract_and_range(self):
        _,cfg,_,vectors,_=setup_index();params=rpc_params('test-construction',vectors[0],cfg)
        self.assertEqual(set(params),{'query_embedding','p_corpus_id','p_modelo','p_revision','match_count'})
        self.assertEqual(params['p_revision'],'a'*40)
        for k in (0,11,True):
            with self.assertRaises(ValueError):rpc_params('x',vectors[0],cfg,k)
    def test_supabase_owner_and_rpc_adapter(self):
        _,cfg,chunks,vectors,local=setup_index();client=Mock();owner='00000000-0000-0000-0000-000000000001'
        repo=SupabaseRepository(client,owner);repo.upsert('test-construction',chunks,vectors,cfg)
        args,kwargs=client.table.return_value.upsert.call_args
        self.assertEqual(kwargs['on_conflict'],'owner_id,corpus_id,chunk_id')
        self.assertEqual(args[0][0]['owner_id'],owner)
        candidates=local.search('test-construction',vectors[0],cfg)
        client.rpc.return_value.execute.return_value.data=[c.model_dump() for c in candidates]
        self.assertEqual(repo.search('test-construction',vectors[0],cfg),candidates)
        client.rpc.assert_called_with('clase08_buscar_fragmentos',rpc_params('test-construction',vectors[0],cfg))
        client.rpc.return_value.execute.return_value.data=[]
        with self.assertRaises(RepositoryError):repo.search('test-construction',vectors[0],cfg)

class TestContext(unittest.TestCase):
    def setUp(self):
        _,cfg,_,vectors,repo=setup_index();self.candidates=repo.search('test-construction',vectors[0],cfg)
    def test_budget_and_dedup(self):
        ctx=build_context('403',self.candidates+[self.candidates[0]])
        self.assertEqual(len(ctx['catalog']),len(self.candidates))
        self.assertEqual(ctx['omitted'][0]['reason'],'duplicate_content')
        small=build_context('403',self.candidates,max_chars=100)
        self.assertFalse(small['catalog']);self.assertLessEqual(small['chars'],100)
        with self.assertRaises(ValueError):build_context('x'*1000,[],max_chars=100)
    def test_valid_and_invalid_citations(self):
        catalog=build_context('403',self.candidates)['catalog']
        valid={'estado':'respondida','respuesta':'El 403 no prueba suspensión. [F1]','citas':['F1'],'limitacion':''}
        self.assertEqual(validate_response(valid,catalog).estado,'respondida')
        for bad in ({**valid,'citas':['F9']},{**valid,'citas':[]},{**valid,'citas':['F1','F1']},{**valid,'estado':'parcial'},{**valid,'extra':True},{**valid,'respuesta':' '}):
            with self.assertRaises(ValueError):validate_response(bad,catalog)
        # This succeeds structurally: its unsupported assertion still needs review.
        self.assertEqual(validate_response({**valid,'respuesta':'Se resuelve en dos horas. [F1]'},catalog).estado,'respondida')

class TestPipeline(unittest.TestCase):
    def setUp(self):
        e,cfg,_,_,repo=setup_index();self.retriever=Retriever(repo,e,'test-construction',cfg)
        self.case={'id':'T','tipo':'ambiguo','input':'Error 403 en el Portal TI.'}
        self.classification={'categoria':'software','prioridad':'media','resumen':'Una aplicación presenta un fallo de ingreso.','datos_faltantes':[],'requiere_humano':False,'confianza':0.9}
        self.classifier=Mock(return_value={'state':'OK_VALIDADO','validated_output':self.classification})
        self.fixture={'estado':'evidencia_insuficiente','respuesta':'No hay respaldo para esa parte.','citas':[],'limitacion':'Falta cobertura en este corpus.'}
    def run_fixture(self,**kwargs):
        return run_rag_case(self.case,self.retriever,mode='mock',classifier=self.classifier,documentary_fixture=self.fixture,**kwargs)
    def test_category_survives_no_coverage(self):
        result=self.run_fixture()
        self.assertEqual(result['state'],'OK_EVIDENCIA_INSUFICIENTE')
        self.assertEqual(result['classification']['categoria'],'software')
        self.assertEqual(result['rag']['semantic_support_review'],'PENDIENTE')
        self.assertEqual(result['model'],'mock')
    def test_valid_answer_partial_and_documentary_clarification(self):
        for documentary_state, final_state in [('respondida','OK_VALIDADO'),('parcial','OK_RESPUESTA_PARCIAL'),('aclaracion','OK_PIDE_ACLARACION')]:
            self.fixture={'estado':documentary_state,'respuesta':'Regla del procedimiento. [F1]',
                          'citas':['F1'],'limitacion':'' if documentary_state=='respondida' else 'Falta precisar el recurso.'}
            result=self.run_fixture()
            self.assertEqual(result['state'],final_state)
            self.assertTrue(result['rag']['citations_valid'])
    def test_empty_ocr_and_context_limit_do_not_generate(self):
        with patch('src.rag.pipeline.prepare_multimodal_input', return_value={'extraction_valid':False}):
            result=self.run_fixture(image_path='blank.png')
        self.assertEqual(result['failure_stage'],'ocr')
        result=self.run_fixture(context_chars=450)
        self.assertEqual(result['rag']['generation_source'],'local_context_limit')
        self.assertEqual(result['documentary_output']['estado'],'evidencia_insuficiente')
    def test_existing_local_policy(self):
        for state in ('OK_REQUIERE_HUMANO','OK_PIDE_ACLARACION'):
            self.classifier.return_value['state']=state
            self.assertEqual(self.run_fixture()['state'],state)
    def test_invalid_cites_and_technical_error(self):
        self.fixture={'estado':'respondida','respuesta':'Algo. [F99]','citas':['F99'],'limitacion':''}
        result=self.run_fixture();self.assertEqual(result['state'],'ERROR_FORMATO')
        self.assertIsNone(result['documentary_output'])
        with patch.object(self.retriever,'retrieve',side_effect=RepositoryError('secret-must-not-leak')):result=self.run_fixture()
        self.assertEqual(result['state'],'ERROR_TECNICO')
        self.assertNotIn('secret-must-not-leak',json.dumps(result))
    def test_ocr_reaches_query(self):
        mm={'text':self.case['input'],'has_attachment':True,'attachment':{},'extracted_text':'Error 403','extraction_valid':True,'extraction_errors':[],'extraction':{}}
        with patch('src.rag.pipeline.prepare_multimodal_input',return_value=mm),patch.object(self.retriever,'retrieve',wraps=self.retriever.retrieve) as retrieve:
            result=self.run_fixture(image_path='test.png')
        self.assertIn('Texto extraído',retrieve.call_args.args[0])
        self.assertIn('Error 403',result['user_content_sent'])
    def test_provider_model_schema(self):
        generator=Mock(return_value={'raw_output':json.dumps(self.fixture),'model':'served-model'})
        verifier=Mock(return_value={'raw_output':json.dumps({'supported':True,'issues':[]})})
        result=run_rag_case(self.case,self.retriever,classifier=self.classifier,generator=generator,verifier=verifier,model='requested-model')
        self.assertEqual(generator.call_args.kwargs['model'],'requested-model')
        self.assertEqual(generator.call_args.kwargs['max_retries'],2)
        self.assertEqual(generator.call_args.kwargs['response_format']['json_schema']['name'],'respuesta_rag')
        self.assertEqual(result['model'],'served-model')
    def test_mock_without_credential_loading(self):
        env={k:v for k,v in os.environ.items() if not k.startswith(('GROQ_','SUPABASE_'))}
        code="from unittest.mock import patch; from src.pipeline import run_case; from src.rag.pipeline import run_rag_case\nwith patch('src.config.load_dotenv') as load:\n r=run_case({'id':'M','tipo':'ambiguo','input':'No puedo entrar'},system_prompt='p',prompt_version='v',model='x',mode='mock'); assert r['state']=='OK_PIDE_ACLARACION'; load.assert_not_called()"
        subprocess.run([sys.executable,'-c',code],env=env,check=True,capture_output=True)
    def test_original_pipeline_requested_and_served_model(self):
        self.assertEqual(build_payload('p','t',model='chosen')['model'],'chosen')
        with patch('src.pipeline.call_groq',return_value={'raw_output':json.dumps(self.classification),'model':'served','usage':{},'metrics':{},'http':{}}) as provider:
            result=run_case(self.case,system_prompt='p',prompt_version='v',model='chosen')
        self.assertEqual(provider.call_args.kwargs['model'],'chosen')
        self.assertEqual(result['model'],'served')

class TestSQL(unittest.TestCase):
    def test_security_contract(self):
        sql=(Path(__file__).resolve().parents[2] / 'infra/supabase/migrations/20261014_documentary_rag.sql').read_text().lower()
        for term in ('enable row level security','security invoker',"set search_path = ''",'vector(384)','primary key (owner_id, corpus_id, chunk_id)',"configuracion ->> 'modelo'","configuracion ->> 'revision'",'coalesce(match_count, 3)'):self.assertIn(term,sql)
        self.assertNotIn('security definer',sql)
        self.assertNotIn('grant delete',sql)

class TestReports(unittest.TestCase):
    def test_pdf_rag_contains_sources_and_not_spurious_ocr(self):
        from src.pdf_report import PDFReport
        e,cfg,_,_,repo=setup_index()
        result=run_rag_case({'id':'R','tipo':'ambiguo','input':'No puedo entrar'},Retriever(repo,e,'test-construction',cfg),
            mode='mock',documentary_fixture={'estado':'aclaracion','respuesta':'¿A qué servicio intenta acceder?',
                                            'citas':[],'limitacion':'Falta identificar el servicio.'})
        report=PDFReport('/tmp/not-generated-by-test.pdf')
        report.register_test_case(case={'id':'R','tipo':'ambiguo','input':'No puedo entrar'},result=result)
        self.assertEqual(report._summary()['ocr_cases'],0)
        self.assertIsNone(result['multimodal'])

class TestSupabaseVerification(unittest.TestCase):
    def test_new_client_persistence_without_upsert(self):
        from scripts.verify_supabase import verify
        _,cfg,chunks,vectors,local=setup_index()
        first,second=Mock(),Mock()
        first.owner_id=second.owner_id='00000000-0000-0000-0000-000000000001'
        candidates=local.search('test-construction',vectors[0],cfg)
        first.search.return_value=second.search.return_value=candidates
        expected={c.chunk_id:c.text for c in chunks}
        with patch('scripts.verify_supabase.load_index',return_value=('test-construction',chunks,vectors,cfg)),patch('scripts.verify_supabase.inventory',return_value=expected):
            result=verify('unused',connect=Mock(side_effect=[first,second]))
        self.assertTrue(result['persistence_new_client'])
        self.assertFalse(result['upsert_performed'])
        first.upsert.assert_not_called();second.upsert.assert_not_called()
    def test_incomplete_upload_is_rejected(self):
        from scripts.verify_supabase import verify
        _,cfg,chunks,vectors,_=setup_index()
        with patch('scripts.verify_supabase.load_index',return_value=('test-construction',chunks,vectors,cfg)),patch('scripts.verify_supabase.inventory',return_value={}):
            with self.assertRaises(RepositoryError):verify('unused',connect=Mock())

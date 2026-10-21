"""Controlled-clock checks for boundaries, failures and repeated provider work."""
import json
import unittest
from unittest.mock import Mock, patch
from src.rag.timing import measure
from src.rag.pipeline import run_rag_case
from src.rag.retrieval import Retriever
from src.rag.lexical import rank
from test.test_rag import setup_index


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds, result=None):
        self.now += seconds
        return result


class TimingTests(unittest.TestCase):
    def test_csv_keeps_unexecuted_stages_blank_and_failure_explicit(self):
        import csv
        import tempfile
        from pathlib import Path
        from scripts.validate_rag_scenarios import write_timings
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'timings.csv'
            write_timings(path,[
                {'id':'ok','state':'OK_VALIDADO','failure_stage':None,'timing_version':'stages-v1',
                 'timings':{'semantic_search_seconds':.2,'bm25_seconds':.01}},
                {'id':'failure','state':'ERROR_TECNICO','failure_stage':'retrieval','timing_version':'stages-v1',
                 'timings':{'semantic_search_seconds':.4}}])
            with path.open() as stream:
                rows=list(csv.DictReader(stream))
        self.assertEqual(rows[1]['bm25_seconds'],'')
        self.assertEqual(rows[1]['semantic_search_seconds'],'0.4')
        self.assertEqual(rows[1]['failure_stage'],'retrieval')

    def test_accumulates_attempts_including_a_failed_stage(self):
        clock = Clock(); timings = {}
        with patch('src.rag.timing.perf_counter', clock):
            with measure(timings, 'review'):
                clock.advance(2)
            with self.assertRaises(ValueError):
                with measure(timings, 'review'):
                    clock.advance(3)
                    raise ValueError('failed')
        self.assertEqual(timings, {'review': 5})

    def test_retrieval_separates_io_from_bm25_without_extra_searches(self):
        clock = Clock(); embedder,cfg,_,_,repo = setup_index()
        real_encode, real_search, real_fetch = embedder.encode, repo.search, repo.lexical_candidates
        def encode(texts):
            return clock.advance(1, real_encode(texts))
        def search(*args):
            return clock.advance(2, real_search(*args))
        def fetch(*args):
            return clock.advance(3, real_fetch(*args))
        def bm25(*args):
            return clock.advance(4, rank(*args))
        with patch('src.rag.timing.perf_counter',clock),patch.object(embedder,'encode',side_effect=encode) as enc,patch.object(repo,'search',side_effect=search) as rpc,patch.object(repo,'lexical_candidates',side_effect=fetch) as read,patch('src.rag.retrieval.rank',side_effect=bm25):
            candidates,t = Retriever(repo,embedder,'test-construction',cfg).retrieve('Error 403')
        self.assertTrue(candidates)
        self.assertEqual(t['embedding_seconds'],1)
        self.assertEqual(t['semantic_search_seconds'],2)
        self.assertEqual(t['lexical_fetch_seconds'],3)
        self.assertEqual(t['bm25_seconds'],4)
        self.assertEqual(t['retrieval_seconds'],9)
        self.assertEqual(t['rrf_seconds'],0)
        self.assertEqual(t['candidate_scoring_seconds'],0)
        self.assertEqual((enc.call_count,rpc.call_count,read.call_count),(1,1,1))

    def test_pipeline_preserves_failed_retrieval_duration_and_omits_unrun_steps(self):
        clock = Clock(); embedder,cfg,_,_,repo = setup_index()
        classifier = Mock(return_value={'state':'OK_VALIDADO','validated_output':{
            'categoria':'acceso','prioridad':'media','resumen':'Error 403 en el portal.',
            'datos_faltantes':[],'requiere_humano':False,'confianza':.9}})
        def fail(*args):
            clock.advance(7)
            raise RuntimeError('connection failed')
        with patch('src.rag.timing.perf_counter',clock),patch('src.rag.pipeline.time.perf_counter',clock),patch.object(repo,'search',side_effect=fail):
            result=run_rag_case({'id':'failure','tipo':'manual','input':'Error 403'},Retriever(repo,embedder,'test-construction',cfg),classifier=classifier)
        self.assertEqual(result['state'],'ERROR_TECNICO')
        self.assertEqual(result['failure_stage'],'retrieval')
        t=result['rag']['timings']
        self.assertEqual(t['semantic_search_seconds'],7)
        self.assertEqual(t['retrieval_seconds'],7)
        self.assertEqual(t['total_seconds'],7)
        self.assertNotIn('bm25_seconds',t)
        self.assertNotIn('generation_seconds',t)

    def test_correction_generation_and_both_reviews_are_measured(self):
        clock = Clock(); embedder,cfg,_,_,repo = setup_index()
        classifier = Mock(return_value={'state':'OK_VALIDADO','validated_output':{
            'categoria':'acceso','prioridad':'media','resumen':'Error 403 en el portal.',
            'datos_faltantes':[],'requiere_humano':False,'confianza':.9}})
        bad={'estado':'respondida','respuesta':'Se resuelve en dos horas. [F1]','citas':['F1'],'limitacion':''}
        good={**bad,'respuesta':'Un 403 no confirma suspensión. [F1]'}
        generations=iter([(4,bad),(6,good)])
        reviews=iter([(2,{'supported':False,'issues':['Plazo sin respaldo.']}),(3,{'supported':True,'issues':[]})])
        def generate(*args,**kwargs):
            delay,body=next(generations)
            return clock.advance(delay,{'raw_output':json.dumps(body)})
        def review(*args,**kwargs):
            delay,body=next(reviews)
            return clock.advance(delay,{'raw_output':json.dumps(body)})
        with patch('src.rag.timing.perf_counter',clock),patch('src.rag.pipeline.time.perf_counter',clock):
            result=run_rag_case({'id':'correction','tipo':'manual','input':'Error 403 en el recurso'},Retriever(repo,embedder,'test-construction',cfg),classifier=classifier,generator=generate,verifier=review)
        self.assertEqual(result['documentary_output'],good)
        t=result['rag']['timings']
        self.assertEqual(t['generation_seconds'],4)
        self.assertEqual(t['generation_correction_seconds'],6)
        self.assertEqual(t['support_review_seconds'],5)
        self.assertEqual(t['total_seconds'],15)

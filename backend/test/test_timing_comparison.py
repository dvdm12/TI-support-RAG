import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
import pdfplumber
from src.rag.timing_comparison import compare_timings, stats
from scripts.compare_retrieval_times import write_outputs


def source():
    # Controlled arithmetic fixture, never presented as observed model latency.
    case={'id':'D1','question':'Pregunta de control','retrieval_evaluable':True,'error':None,
          'timings':{'embedding_seconds':1,'semantic_search_seconds':2,'lexical_fetch_seconds':3,
                     'bm25_seconds':4,'rrf_seconds':5,'candidate_scoring_seconds':6,'retrieval_seconds':21},
          'variants':{'A_semantic':{'retrieval_seconds':3},'B_hybrid_rrf':{'retrieval_seconds':22}}}
    return {'status':'complete','planned_cases':1,'timestamp_utc':'2026-10-21T00:00:00Z',
            'backend':'local','corpus_id':'unit-test','protocol':{'k':3,'category_boost':False,'classifier_run':False},
            'aggregate':{'A_semantic':{},'B_hybrid_rrf':{}},'cases':[case]}


class TimingComparisonTests(unittest.TestCase):
    def test_known_statistics_and_percentile_interpolation(self):
        result=stats([1,2,3,4,5])
        self.assertEqual(result['mean'],3)
        self.assertEqual(result['median'],3)
        self.assertAlmostEqual(result['p95'],4.8)
        self.assertEqual(stats([2])['p95'],2)
        self.assertIsNone(stats([])['mean'])
        self.assertEqual(stats([])['n'],0)

    def test_shared_components_not_double_counted_and_stages_not_imputed(self):
        report=compare_timings(source());case=report['cases'][0]
        self.assertEqual(case['variants']['A_semantic']['total_seconds'],3)
        self.assertEqual(case['variants']['B_hybrid_rrf']['total_seconds'],22)
        self.assertEqual(case['difference_seconds'],19)
        self.assertAlmostEqual(case['relative_change_percent'],100*19/3)
        self.assertIsNone(case['variants']['A_semantic']['stages']['bm25_seconds'])
        self.assertEqual(case['variants']['B_hybrid_rrf']['stages']['coordination_seconds'],1)
        self.assertEqual(report['groups']['behavior']['valid_pairs'],0)

    def test_failures_and_missing_values_exclude_the_entire_pair(self):
        for change in ('failure','missing','negative','nan','wrong_total'):
            original=source();case=original['cases'][0]
            if change=='failure':case['error']={'type':'TimeoutError'}
            elif change=='missing':del case['timings']['bm25_seconds']
            elif change=='negative':case['timings']['bm25_seconds']=-1
            elif change=='nan':case['timings']['bm25_seconds']=math.nan
            else:case['variants']['A_semantic']['retrieval_seconds']=30
            report=compare_timings(original)
            self.assertEqual(report['status'],'incomplete')
            self.assertEqual(report['groups']['all']['valid_pairs'],0)
            self.assertIsNone(report['groups']['all']['variants']['A_semantic']['total_seconds']['mean'])
            json.dumps(report,allow_nan=False)

    def test_zero_baseline_keeps_absolute_delta_but_no_relative_percentage(self):
        original=source();case=original['cases'][0]
        case['timings'].update(embedding_seconds=0,semantic_search_seconds=0,retrieval_seconds=19)
        case['variants']['A_semantic']['retrieval_seconds']=0
        case['variants']['B_hybrid_rrf']['retrieval_seconds']=19
        report=compare_timings(original)
        self.assertEqual(report['cases'][0]['difference_seconds'],19)
        self.assertIsNone(report['cases'][0]['relative_change_percent'])
        self.assertEqual(report['groups']['all']['zero_baseline_pairs'],1)

    def test_group_denominators_and_invalid_protocol(self):
        original=source();behavior=copy.deepcopy(original['cases'][0])
        behavior.update(id='C1',retrieval_evaluable=False)
        original['cases'].append(behavior);original['planned_cases']=2
        report=compare_timings(original)
        self.assertEqual(report['groups']['all']['valid_pairs'],2)
        self.assertEqual(report['groups']['documentary']['valid_pairs'],1)
        self.assertEqual(report['groups']['behavior']['valid_pairs'],1)
        original['protocol']['category_boost']=True
        with self.assertRaises(ValueError):compare_timings(original)
        original=source();original['planned_cases']=2
        self.assertEqual(compare_timings(original)['status'],'incomplete')

    def test_json_csv_pdf_export_for_an_incomplete_comparison(self):
        original=source();original['cases'][0]['error']={'type':'TimeoutError'}
        report=compare_timings(original)
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'timing.json'
            pdf=write_outputs(report,output)
            self.assertTrue(output.with_suffix('.csv').exists())
            self.assertEqual(json.loads(output.read_text())['status'],'incomplete')
            with pdfplumber.open(pdf) as doc:
                text='\n'.join(page.extract_text() or '' for page in doc.pages)
            self.assertIn('INCOMPLETA',text)
            self.assertIn('ERROR',text)
            self.assertIn('N/E',text)

import unittest
from src.rag.retrieval_metrics import metrics, coverage
from scripts.evaluate_retrieval_metrics import aggregate, VARIANTS


def unit(*ids):
    return {'evidence':[{'chunk_id':ident} for ident in ids]}


class RetrievalMetricTests(unittest.TestCase):
    def test_class09_numeric_example(self):
        units=[unit('A'),unit('B')]
        baseline=metrics(['C','A','D'],units)
        self.assertEqual(baseline,{'precision':1/3,'recall':.5,'hit':1,'rr':.5,'coverage':.5})
        improved=metrics(['A','B','E'],units)
        self.assertEqual(improved,{'precision':2/3,'recall':1,'hit':1,'rr':1,'coverage':1})

    def test_short_list_uses_requested_cutoff_and_alternatives_are_not_units(self):
        self.assertEqual(metrics(['A'],[unit('A')])['precision'],1/3)
        units=[unit('A','B'),unit('C')]
        self.assertEqual(metrics(['B'],units)['recall'],1/3)
        self.assertEqual(coverage(['B'],units),.5)
        self.assertEqual(coverage(['B','C'],units),1)

    def test_absent_evidence_is_null_but_a_miss_is_zero(self):
        self.assertTrue(all(v is None for v in metrics(['nearby'],[]).values()))
        self.assertEqual(metrics([], [unit('A')]),{'precision':0,'recall':0,'hit':0,'rr':0,'coverage':0})
        for ids in (['A','A'],['A','B','C','D']):
            with self.assertRaises(ValueError):metrics(ids,[unit('A')])

    def test_failed_pairs_and_behavior_are_counted_but_not_zero_quality(self):
        valid={'metrics_at_3':metrics(['A'],[unit('A')]),'context_coverage':1,
               'candidate_coverage':1,'selected_ids':['A'],'retrieval_seconds':.2}
        rows=[{'retrieval_evaluable':True,'error':None,'variants':{name:valid for name in VARIANTS}},
              {'retrieval_evaluable':True,'error':{'type':'Timeout'},'variants':{}},
              {'retrieval_evaluable':False,'error':None,'variants':{}}]
        for result in aggregate(rows).values():
            self.assertEqual(result['eligible_cases'],2)
            self.assertEqual(result['paired_valid_cases'],1)
            self.assertEqual(result['excluded_behavior_cases'],1)
            self.assertEqual(result['metrics_at_3']['recall'],1)
            self.assertEqual(result['short_lists'],1)
        empty=aggregate(rows[1:])
        self.assertIsNone(empty['A_semantic']['metrics_at_3']['precision'])

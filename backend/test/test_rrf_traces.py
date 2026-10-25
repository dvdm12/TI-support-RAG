import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.export_rrf_traces import ROOT, build_report, classroom_example
from src.rag.models import Candidate
from src.rag.retrieval import Retriever, fuse_rankings, select_ranked_candidates
from test.test_rag import FakeEmbedder, config


def candidates(ids, category='hardware', section='Alcance'):
    return [Candidate(chunk_id=i, content='Texto ' + i, metadata={'category': category, 'section': section},
                      similitud=.5) for i in ids]


class RRFTraceTests(unittest.TestCase):
    def test_classroom_slide_three_exact_order_and_six_decimal_scores(self):
        rows = classroom_example()
        self.assertEqual([r['chunk_id'] for r in rows], ['A', 'C', 'B', 'D'])
        self.assertEqual([f"{r['rrf_score']:.6f}" for r in rows],
                         ['0.032522', '0.032266', '0.016129', '0.015873'])
        self.assertEqual((rows[0]['semantic_rank'], rows[0]['bm25_rank']), (1, 2))
        self.assertEqual(rows[2]['bm25_contribution'], 0)
        self.assertEqual(rows[3]['semantic_contribution'], 0)

    def test_weighted_union_is_distinct_from_unweighted_example(self):
        rows = fuse_rankings(candidates(['A', 'B', 'C']), candidates(['C', 'A', 'D']))
        self.assertEqual([r['chunk_id'] for r in rows], ['C', 'A', 'D', 'B'])
        first = rows[0]
        self.assertAlmostEqual(first['semantic_contribution'], 1 / 63)
        self.assertAlmostEqual(first['bm25_contribution'], 2 / 61)
        self.assertEqual(len({r['chunk_id'] for r in rows}), 4)

    def test_empty_rankings_ties_and_duplicate_branch_rejection(self):
        self.assertEqual(fuse_rankings([], []), [])
        rows = fuse_rankings(candidates(['B']), candidates(['A']), semantic_weight=1, lexical_weight=1)
        self.assertEqual([r['chunk_id'] for r in rows], ['A', 'B'])
        with self.assertRaises(ValueError):
            fuse_rankings(candidates(['A', 'A']), [])

    def test_exclusion_before_top_k_is_visible_and_refills_selection(self):
        sem = candidates(['bad'], section='Credenciales posiblemente expuestas') + candidates(['good', 'other'])
        selected, trace = select_ranked_candidates('Correo sospechoso sin abrir.', sem, sem, k=2)
        self.assertEqual([c.chunk_id for c in selected], ['good', 'other'])
        bad = next(r for r in trace['rrf_union'] if r['chunk_id'] == 'bad')
        self.assertFalse(bad['applicable'])
        self.assertEqual(bad['exclusion_reason'], 'password_route_not_requested_or_exposed')
        self.assertIsNone(bad['selected_rank'])

    def test_category_boost_is_separate_from_rrf_and_changes_selection(self):
        sem = candidates(['A']) + candidates(['B'], category='redes')
        selected, trace = select_ranked_candidates('Consulta de red', sem, [], k=1, category='redes')
        self.assertEqual(selected[0].chunk_id, 'B')
        winner = trace['rrf_union'][0]
        self.assertEqual(winner['category_boost'], .025)
        self.assertAlmostEqual(winner['rrf_score'], 1 / 62)
        self.assertAlmostEqual(winner['selection_score'], 1 / 62 + .025)

    def test_production_trace_matches_returned_candidates_without_extra_reads(self):
        sem, lexical = candidates(['A', 'B', 'C']), candidates(['C', 'A', 'D'])
        repository = Mock()
        repository.search.return_value = sem
        repository.lexical_candidates.return_value = lexical
        retriever = Retriever(repository, FakeEmbedder(), 'test', config())
        trace = {'stale': True}
        with patch('src.rag.retrieval.rank', return_value=lexical):
            selected, timings = retriever.retrieve('Consulta', trace=trace)
        self.assertEqual(trace['selected_ids'], [c.chunk_id for c in selected])
        self.assertEqual(trace['selected_ids'], ['C', 'A', 'D'])
        self.assertNotIn('stale', trace)
        self.assertIn('rrf_seconds', timings)
        repository.search.assert_called_once()
        repository.lexical_candidates.assert_called_once()

    def test_offline_report_preserves_all_thirteen_saved_v2_selections(self):
        report = build_report()
        self.assertEqual(len(report['cases']), 13)
        self.assertEqual(sum(c['retrieval_evaluable'] for c in report['cases']), 7)
        self.assertEqual(report['provider_calls'], 0)
        self.assertFalse(report['reserve_executed'])
        for case in report['cases']:
            self.assertTrue(case['matches_saved_hybrid_v2'])
            selected = sorted((r for r in case['rrf_union'] if r['selected_rank']), key=lambda r: r['selected_rank'])
            self.assertEqual([r['chunk_id'] for r in selected], case['selected_ids'])
            for row in case['rrf_union']:
                self.assertAlmostEqual(row['semantic_contribution'] + row['bm25_contribution'], row['rrf_score'])

    def test_changed_index_fails_before_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('docs/evaluacion/recuperacion/retrieval_metrics_20261021.json', 'docs/evaluacion/recuperacion/coverage_improvements_20261021.json',
                         'cases/rag_evidence.json', 'data/indexes/sections/records.json'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / name).read_bytes())
            with (root / 'data/indexes/sections/records.json').open('a') as stream:
                stream.write(' ')
            with self.assertRaisesRegex(ValueError, 'Índice distinto'):
                build_report(root)

    def test_saved_csv_exports_every_union_candidate_and_contribution(self):
        report = json.loads((ROOT / 'docs/evaluacion/recuperacion/rrf_traces_20261025.json').read_text())
        with (ROOT / 'docs/evaluacion/recuperacion/rrf_traces_20261025.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        expected = {(case['id'], r['chunk_id']): r for case in report['cases'] for r in case['rrf_union']}
        self.assertEqual(len(rows), len(expected))
        for row in rows:
            original = expected[(row['case'], row['chunk_id'])]
            for key in ('semantic_contribution', 'bm25_contribution', 'rrf_score'):
                self.assertEqual(float(row[key]), original[key])

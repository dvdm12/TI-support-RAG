import contextlib
import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pdfplumber
from src.rag.config import ROOT
from src.rag.complete_coverage import details, enrich_saved_report
from scripts import summarize_complete_coverage as cli
from scripts import evaluate_retrieval_metrics as evaluator


class CompleteCoverageTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads((ROOT/'docs/retrieval_metrics_20261021.json').read_text())
        self.annotations = json.loads((ROOT/'cases/rag_evidence.json').read_text())

    def test_alternatives_and_incomplete_information_are_distinct_from_hits(self):
        units = [{'id':'u1','evidence':[{'chunk_id':'a'},{'chunk_id':'b'}]},
                 {'id':'u2','evidence':[{'chunk_id':'c'}]}]
        self.assertFalse(details(['b'],units)['complete'])
        self.assertEqual(details(['b'],units)['missing_unit_ids'],['u2'])
        self.assertTrue(details(['b','c'],units)['complete'])
        self.assertEqual(details([],units)['covered_units'],0)
        self.assertIsNone(details(['a'],[])['complete'])
        with self.assertRaises(ValueError): details(['a','a'],units)

    def test_saved_counts_and_historical_fields_are_preserved(self):
        report = enrich_saved_report(self.source,self.annotations)
        for name, expected in {'A_semantic':(4,3), 'B_hybrid_rrf':(5,4)}.items():
            for stage, count in zip(('top_3','context'),expected):
                summary = report['aggregate'][name]['coverage_completeness'][stage]
                self.assertEqual(summary['complete_cases'],count)
                self.assertEqual(summary['incomplete_cases'],7-count)
                self.assertEqual(summary['complete_rate'],count/7)
                self.assertEqual(summary['excluded_behavior_cases'],6)
            del report['aggregate'][name]['coverage_completeness']
        for row in report['cases']:
            for variant in row['variants'].values(): del variant['coverage_completeness']
        self.assertEqual(report,self.source)

    def test_errors_and_behavior_do_not_become_incomplete_evidence(self):
        self.source['cases'][0].update(error={'type':'TimeoutError'},variants={})
        report = enrich_saved_report(self.source,self.annotations)
        summary = report['aggregate']['A_semantic']['coverage_completeness']['top_3']
        self.assertEqual(summary['eligible_cases'],7)
        self.assertEqual(summary['evaluated_cases'],6)
        self.assertEqual(summary['complete_cases'],3)
        self.assertEqual(summary['incomplete_cases'],3)
        self.assertEqual(summary['excluded_technical_cases'],['E01'])
        for case in report['cases']:
            if not case['retrieval_evaluable']:
                self.assertIsNone(case['variants']['A_semantic']['coverage_completeness']['context']['complete'])

    def test_all_errors_leave_rate_unevaluable(self):
        for case in self.source['cases']:
            if case['retrieval_evaluable']:case.update(error={'type':'TimeoutError'},variants={})
        report = enrich_saved_report(self.source,self.annotations)
        summary = report['aggregate']['A_semantic']['coverage_completeness']['top_3']
        self.assertEqual(summary['evaluated_cases'],0)
        self.assertIsNone(summary['complete_rate'])

    def test_changed_data_and_reserve_annotations_are_rejected(self):
        for change in ('fraction','unknown_id','duplicate_id','context','question','units'):
            report = copy.deepcopy(self.source)
            case = report['cases'][0]; variant = case['variants']['A_semantic']
            if change=='fraction': variant['metrics_at_3']['coverage']=0.5
            elif change=='unknown_id': variant['selected_ids']=['unknown']
            elif change=='duplicate_id': variant['selected_ids']*=2
            elif change=='context': variant['context_ids']=['unknown']
            elif change=='question': case['question']='Pregunta distinta'
            else: case['units_count']+=1
            with self.subTest(change=change),self.assertRaises(ValueError):
                enrich_saved_report(report,self.annotations)
        self.annotations['schema_version']='rag-reserve-v1'
        with self.assertRaises(ValueError): enrich_saved_report(self.source,self.annotations)

    def test_cli_exports_all_formats_without_model_or_providers(self):
        source=ROOT/'docs/retrieval_metrics_20261021.json';before=source.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'complete.json'
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch('sys.argv',['coverage','--input',str(source),'--output',str(output)]))
                model=stack.enter_context(patch.object(evaluator,'SentenceEmbedder'))
                connect=stack.enter_context(patch.object(evaluator.SupabaseRepository,'connect'))
                validate=stack.enter_context(patch.object(evaluator,'validate'))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                cli.main()
            model.assert_not_called();connect.assert_not_called();validate.assert_not_called()
            self.assertEqual(before,source.read_bytes())
            report=json.loads(output.read_text())
            self.assertEqual(report['complete_coverage_derivation']['provider_calls'],0)
            with output.with_suffix('.csv').open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),26)
            self.assertEqual(rows[0]['top_3_complete'],'True')
            self.assertEqual(next(r for r in rows if r['case']=='E07')['top_3_complete'],'')
            with pdfplumber.open(output.with_suffix('.pdf')) as document:
                text='\n'.join(page.extract_text() or '' for page in document.pages)
            self.assertIn('Cobertura completa por pregunta',text)
            self.assertIn('57,14%',text);self.assertIn('71,43%',text)
            self.assertIn('Incompleta',text);self.assertIn('N/E',text)

    def test_cli_rejects_changed_annotation_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            annotations=Path(folder)/'changed.json'
            annotations.write_text(json.dumps(self.annotations))
            output=Path(folder)/'output.json'
            with patch('sys.argv',['coverage','--annotations',str(annotations),'--output',str(output)]),self.assertRaises(ValueError):
                cli.main()
            self.assertFalse(output.exists())

import csv
import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError
from schemas.human_review_v1 import HumanJudgement, ReviewSheet
from scripts.prepare_class09_review import ROOT, GENERATION, API, build_sheet, export_sheet


class Class09ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = ROOT / "docs/human_review/class09_review_v1.json"
        cls.sheet = ReviewSheet.model_validate_json(cls.saved.read_text())

    def test_saved_sheet_population_and_pending_verdicts(self):
        rows = self.sheet.rows
        self.assertEqual(len(rows), 27)
        self.assertEqual(sum(r.variant == "API_system_v8" for r in rows), 13)
        for row in rows:
            for review in [row.human_review, *row.independent_reviews, row.adjudication]:
                self.assertTrue(all(v is None for v in review.model_dump().values()))
            self.assertEqual(row.claims, [])
            self.assertTrue(all(u["covered"] is None for u in row.unit_reviews))

    def test_duplicate_rows_and_missing_passages_are_rejected(self):
        data = self.sheet.model_dump(mode="json")
        data["rows"].append(data["rows"][0])
        with self.assertRaises(ValidationError):
            ReviewSheet.model_validate(data)
        data = self.sheet.model_dump(mode="json")
        data["rows"][0]["cited_passages"] = []
        with self.assertRaises(ValidationError):
            ReviewSheet.model_validate(data)

    def test_human_verdict_requires_identity_date_and_justification(self):
        for bad in ({"correccion": True}, {"respaldo": "true"}, {"utilidad": 1}):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                HumanJudgement.model_validate(bad)
        result = HumanJudgement(correccion=False, revisor="Persona", fecha="2026-10-25",
                                justificacion="Omite una condición de la fuente.")
        self.assertFalse(result.correccion)

    def test_csv_is_lossless_and_cannot_overwrite_reviews(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "review.json"
            export_sheet(self.sheet, output)
            with output.with_suffix(".csv").open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 27)
            for actual, expected in zip(rows, self.sheet.model_dump(mode="json")["rows"]):
                self.assertEqual(actual["question"], expected["question"])
                for key in ("response", "cited_passages", "expected_information_units", "human_review"):
                    self.assertEqual(json.loads(actual[key]), expected[key])
            with self.assertRaises(FileExistsError):
                export_sheet(self.sheet, output)

    @unittest.skipUnless((ROOT / API).exists(), "Traza HTTP solo disponible en esta máquina")
    def test_build_matches_saved_observations_and_full_source_text(self):
        rebuilt = build_sheet()
        # The stored sheet is immutable evidence; only its historical source path
        # differs after physically organizing the documents.
        expected = self.sheet.model_dump()
        old_generation = 'docs/generation_tokens_20261021.json'
        for source in expected['sources']:
            if source['path'] == old_generation:
                source['path'] = GENERATION
        for row in expected['rows']:
            if row['source_path'] == old_generation:
                row['source_path'] = GENERATION
        self.assertEqual(rebuilt.model_dump(), expected)
        generation = json.loads((ROOT / GENERATION).read_text())
        api = json.loads((ROOT / API).read_text())
        records = {r["chunk_id"]: r for r in json.loads((ROOT / "data/indexes/sections/records.json").read_text())}
        for row in rebuilt.rows:
            if row.variant == "API_system_v8":
                original = next(r for r in api if r["id"] == row.case_id)["response"]["respuesta_documental"]
            else:
                original = next(r for r in generation["cases"] if r["id"] == row.case_id)["variants"][row.variant]["observations"][0]["documentary_output"]
            self.assertEqual(row.response, original)
            for passage in row.cited_passages:
                self.assertEqual(passage.text, records[passage.chunk_id]["text"])

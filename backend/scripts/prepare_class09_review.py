"""Prepare T1 from saved observations only. No provider or database imports."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from schemas.human_review_v1 import HumanJudgement, ReviewSheet

ROOT = Path(__file__).resolve().parents[1]
GENERATION = "docs/generation_tokens_20261021.json"
API = "docs/rag_runs/backend_check_20261025/phase_b_v8.json"
ANNOTATIONS = "cases/rag_evidence.json"
RECORDS = "data/indexes/sections/records.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_sheet(root=ROOT):
    def read(path):
        return json.loads((root / path).read_text(encoding="utf-8"))

    annotations = read(ANNOTATIONS)
    records = {r["chunk_id"]: r for r in read(RECORDS)}
    if sha(root / RECORDS) != annotations["corpus"]["index_records_sha256"]:
        raise ValueError("El índice no coincide con el corpus anotado.")
    cases = {c["id"]: c for c in annotations["cases"]}
    generation = read(GENERATION)
    if sha(root / ANNOTATIONS) != generation["annotations_sha256"]:
        raise ValueError("Las anotaciones cambiaron desde la comparación A/B.")
    rows = []

    def append(case, variant, path, locator, response, sources, error=None):
        passages = []
        for label in response.get("citas", []):
            source = sources[label]
            record = records[source["chunk_id"]]
            if "content" in source and source["content"] != record["text"]:
                raise ValueError("El pasaje guardado difiere del índice congelado.")
            passages.append(dict(label=label, chunk_id=record["chunk_id"],
                                 text=record["text"], metadata={k: v for k, v in record.items()
                                                              if k not in ("text", "tokens")}))
        policies = [{**p, "full_text": records[p["chunk_id"]]["text"]}
                    for p in case["behavior_policy_references"]]
        rows.append(dict(
            row_id=f'{case["id"]}:{variant}', case_id=case["id"], variant=variant,
            source_path=path, source_locator=locator,
            evaluation_scope="http_query" if variant == "API_system_v8" else "direct_generation",
            question=case["question"], response=response, technical_error=error,
            cited_passages=passages, expected_information_units=case["required_information_units"],
            behavior_policy_references=policies, expected_answer=case["expected_answer"],
            expected_documentary_states=case["expected_documentary_states"],
            conditions_to_preserve=case["conditions_to_preserve"],
            failure_criteria=case["failure_criteria"], retrieval_evaluable=case["retrieval_evaluable"],
            agent_draft={"status": "not_evaluated", "annotation_status": annotations["annotation"]["status"],
                         "note": "Expectativas anotadas por agente; pendientes de validación humana."},
            human_review=HumanJudgement().model_dump(mode="json"),
            independent_reviews=[HumanJudgement().model_dump(mode="json") for _ in range(2)],
            adjudication=HumanJudgement().model_dump(mode="json"), claims=[],
            unit_reviews=[{"unit_id": u["id"], "covered": None, "justification": None}
                          for u in case["required_information_units"]]))

    for i, case in enumerate(generation["cases"]):
        if case["question"] != cases[case["id"]]["question"]:
            raise ValueError("Pregunta A/B distinta de las anotaciones.")
        for variant, data in case["variants"].items():
            if len(data["observations"]) != 1:
                raise ValueError("Seleccionar explícitamente la observación si hay múltiples intentos.")
            obs = data["observations"][0]
            append(cases[case["id"]], variant, GENERATION,
                   f"/cases/{i}/variants/{variant}/observations/0",
                   obs.get("documentary_output") or {}, data["catalog"], obs.get("validation_error"))
    for i, item in enumerate(read(API)):
        response = item["response"]
        append(cases[item["id"]], "API_system_v8", API, f"/{i}/response",
               response.get("respuesta_documental") or {},
               {s["id"]: s for s in response.get("fuentes", [])},
               None if item["status"] == 200 else f'HTTP {item["status"]}')
    if len(rows) != 27 or len({r["case_id"] for r in rows}) != 13:
        raise ValueError("Población inesperada: se requieren 14 A/B y 13 API.")
    return ReviewSheet.model_validate(dict(
        schema_version="class09-human-review-v1", status="pending_human_review",
        sources=[{"path": p, "sha256": sha(root / p)} for p in (GENERATION, API, ANNOTATIONS, RECORDS)],
        protocol={
            "split": "development_only", "human_review_completed": False,
            "generation_protocol": generation["protocol"],
            "api_configuration": {"classifier": "system_v8", "generator": "rag_v6"},
            "comparability": "A/B: generación directa del 21-10. API: pipeline completo del 25-10; no agrupar como experimento A/B/C.",
            "passage_origin": "A/B contrastado con catálogo guardado; API resuelto por chunk_id en índice con hash verificado. No reconstruye contexto API completo.",
            "review": "Criterios null hasta revisión humana. Al menos tres casos con dos revisores independientes y discrepancias resueltas en adjudication; human_review recoge el veredicto final.",
            "claims": "Segmentar afirmaciones en claims: text, supported (bool/null), citation_covered (bool/null), labels y justification. No contar preguntas de aclaración como afirmaciones documentales.",
            "units": "Marcar covered y justificar en unit_reviews; sin unidades documentales, no aplica cobertura.",
            "rubric": {"correccion": "Resuelve correctamente según fuentes y condiciones.",
                       "fidelidad": "Conserva condiciones, negaciones y límites sin distorsión.",
                       "respaldo": "Las afirmaciones documentales tienen evidencia que realmente las sostiene.",
                       "utilidad": "La respuesta es pertinente, clara y accionable dentro del alcance."},
        }, rows=rows))


def export_sheet(sheet, output):
    """Never overwrite a worksheet that may already contain human decisions."""
    csv_path = output.with_suffix(".csv")
    if output.exists() or csv_path.exists():
        raise FileExistsError("La ficha ya existe; elija otra ruta para conservar la revisión humana.")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = sheet.model_dump(mode="json")
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(data["rows"][0])
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in data["rows"]:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list))
                             else v for k, v in row.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/human_review/class09_review_v1.json")
    args = parser.parse_args()
    sheet = build_sheet()
    export_sheet(sheet, args.output)
    print(f"Ficha preparada: {len(sheet.rows)} filas; revisión humana pendiente. {args.output}")


if __name__ == "__main__":
    main()

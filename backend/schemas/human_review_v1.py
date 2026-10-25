"""Offline human-review worksheet; machine checks never become human verdicts."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator


class ReviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HumanJudgement(ReviewModel):
    correccion: StrictBool | None = None
    fidelidad: StrictBool | None = None
    respaldo: StrictBool | None = None
    utilidad: StrictBool | None = None
    justificacion: str | None = None
    revisor: str | None = None
    fecha: date | None = None

    @model_validator(mode="after")
    def identified_verdict(self):
        if any(getattr(self, k) is not None for k in
               ("correccion", "fidelidad", "respaldo", "utilidad")):
            if not (self.justificacion and self.justificacion.strip()
                    and self.revisor and self.revisor.strip() and self.fecha):
                raise ValueError("Un juicio humano requiere justificación, revisor y fecha.")
        return self


class CitedPassage(ReviewModel):
    label: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    metadata: dict


class ReviewRow(ReviewModel):
    row_id: str
    case_id: str
    variant: Literal["A_semantic", "B_hybrid_rrf", "API_system_v8"]
    source_path: str
    source_locator: str
    evaluation_scope: Literal["direct_generation", "http_query"]
    question: str = Field(min_length=1)
    response: dict
    technical_error: str | None
    cited_passages: list[CitedPassage]
    expected_information_units: list[dict]
    behavior_policy_references: list[dict]
    expected_answer: str
    expected_documentary_states: list[str]
    conditions_to_preserve: list[str]
    failure_criteria: list[str]
    retrieval_evaluable: StrictBool
    agent_draft: dict
    human_review: HumanJudgement
    independent_reviews: list[HumanJudgement] = Field(min_length=2)
    adjudication: HumanJudgement
    claims: list[dict]
    unit_reviews: list[dict]

    @model_validator(mode="after")
    def citations_resolved(self):
        labels = [p.label for p in self.cited_passages]
        if len(set(labels)) != len(labels) or set(labels) != set(self.response.get("citas", [])):
            raise ValueError("Cada etiqueta citada debe tener un único pasaje completo.")
        return self


class ReviewSheet(ReviewModel):
    schema_version: Literal["class09-human-review-v1"]
    status: Literal["pending_human_review", "in_progress", "completed"]
    sources: list[dict]
    protocol: dict
    rows: list[ReviewRow]

    @model_validator(mode="after")
    def unique_rows(self):
        if len({r.row_id for r in self.rows}) != len(self.rows):
            raise ValueError("Filas duplicadas.")
        return self

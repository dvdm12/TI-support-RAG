"""Deterministic decision rules for TI-support-RAG."""

from typing import Mapping, Any

CLARIFICATION_THRESHOLD = 0.60


def determine_state(output: Mapping[str, Any]) -> str:
    """Determine the application state from a validated model output."""
    if output["requiere_humano"]:
        return "OK_REQUIERE_HUMANO"

    if (
        output["confianza"] < CLARIFICATION_THRESHOLD
        or output["datos_faltantes"]
    ):
        return "OK_PIDE_ACLARACION"

    return "OK_VALIDADO"


def run_decision_contract_checks() -> list[str]:
    """Run deterministic regression checks for the decision policy."""
    checks = [
        (
            {"requiere_humano": True, "confianza": 0.99, "datos_faltantes": []},
            "OK_REQUIERE_HUMANO",
        ),
        (
            {"requiere_humano": False, "confianza": 0.40, "datos_faltantes": []},
            "OK_PIDE_ACLARACION",
        ),
        (
            {"requiere_humano": False, "confianza": 0.90, "datos_faltantes": ["Sistema"]},
            "OK_PIDE_ACLARACION",
        ),
        (
            {"requiere_humano": False, "confianza": 0.90, "datos_faltantes": []},
            "OK_VALIDADO",
        ),
    ]

    observed_states = []
    for sample, expected in checks:
        observed = determine_state(sample)
        if observed != expected:
            raise AssertionError(f"Estado esperado {expected}, observado {observed}.")
        observed_states.append(observed)

    return observed_states

"""Application pipeline orchestration for TI-support-RAG.

This module coordinates existing infrastructure modules. It does not implement
OCR, validation rules, PDF rendering, or provider-specific behavior itself.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from .decision import determine_state
from .groq_client import call_groq
from .mocks import mock_response
from .validator import validate_output


def prepare_case_input(
    case: dict[str, Any],
    multimodal_input: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Compose the user content from text plus already-prepared OCR evidence."""
    if multimodal_input is None:
        return case["input"], None

    if not multimodal_input.get("extraction_valid", False):
        raise ValueError("La extracción OCR no superó la validación.")

    content = (
        "Solicitud escrita por el usuario:\n"
        f"{case['input']}\n\n"
        "Texto extraído de la imagen mediante OCR:\n"
        f"{multimodal_input['extracted_text']}"
    )
    return content, multimodal_input


def execute_case(
    case: dict[str, Any],
    mode: str,
    user_content: str,
    *,
    system_prompt: str,
    model: str,
) -> dict[str, Any]:
    """Execute one case through Groq or the explicit mock provider."""
    if mode == "groq":
        response = call_groq(system_prompt, user_content)
        content = response["raw_output"]
        if not content:
            raise RuntimeError("Groq devolvió una salida vacía.")

        return {
            "content": content,
            "usage": response["usage"],
            "metrics": response["metrics"],
            "http": response["http"],
            "source": "groq",
            "model": model,
        }

    if mode == "mock":
        return {
            "content": None,
            "mock_output": mock_response(case["tipo"]),
            "usage": None,
            "metrics": None,
            "http": None,
            "source": f"mock:{case['tipo']}",
            "model": "mock",
        }

    raise ValueError("mode debe ser 'groq' o 'mock'.")


def run_case(
    case: dict[str, Any],
    *,
    system_prompt: str,
    prompt_version: str,
    model: str,
    mode: str = "groq",
    multimodal_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run, validate, decide, and normalize one application case."""
    started = time.perf_counter()
    user_content, multimodal = prepare_case_input(case, multimodal_input)

    raw_output = None
    validated_output = None
    validation_errors: list[str] = []
    execution_error = None
    usage = metrics = http = None
    state = None
    execution: dict[str, Any] = {}

    try:
        execution = execute_case(
            case,
            mode,
            user_content,
            system_prompt=system_prompt,
            model=model,
        )
        usage = execution["usage"]
        metrics = execution["metrics"]
        http = execution["http"]

        raw_output = (
            execution["mock_output"]
            if mode == "mock"
            else json.loads(execution["content"])
        )

        valid, errors, validated = validate_output(raw_output)
        validation_errors = errors

        if not valid:
            state = "ERROR_FORMATO"
        else:
            validated_output = validated.model_dump()
            state = determine_state(validated_output)

    except json.JSONDecodeError as error:
        validation_errors = [f"JSON inválido: {error}"]
        state = "ERROR_FORMATO"
    except Exception as error:
        execution_error = str(error)
        state = "ERROR_TECNICO"

    return {
        "case_id": case["id"],
        "tipo": case["tipo"],
        "input": case["input"],
        "user_content_sent": user_content,
        "prompt_version": prompt_version,
        "model": execution.get("model", model),
        "source": execution.get("source", mode),
        "raw_output": raw_output,
        "validated_output": validated_output,
        "validation_errors": validation_errors,
        "execution_error": execution_error,
        "state": state,
        "usage": usage,
        "metrics": metrics,
        "http": http,
        "multimodal": multimodal,
        "latency_seconds": round(time.perf_counter() - started, 4),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

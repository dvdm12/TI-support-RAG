import re
import time
from typing import Any

import requests

from src.config import API_URL, GROQ_API_KEY, MODEL


HTTP_TIMEOUT = (10, 60)
DEFAULT_RETRY_DELAY = 15


RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "solicitud_ti",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "categoria": {
                    "type": "string",
                    "enum": [
                        "hardware",
                        "software",
                        "redes",
                        "cuentas",
                        "seguridad",
                        "acceso",
                        "otros",
                    ],
                },
                "prioridad": {
                    "type": "string",
                    "enum": ["baja", "media", "alta"],
                },
                "resumen": {"type": "string"},
                "datos_faltantes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "requiere_humano": {"type": "boolean"},
                "confianza": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
            },
            "required": [
                "categoria",
                "prioridad",
                "resumen",
                "datos_faltantes",
                "requiere_humano",
                "confianza",
            ],
            "additionalProperties": False,
        },
    },
}


def build_headers() -> dict[str, str]:
    """Construye los headers de autenticación y configuración para Groq."""
    return {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Groq-Beta": "inference-metrics",
    }


def build_payload(system_prompt: str, user_text: str) -> dict[str, Any]:
    """Construye el payload utilizado por la API de Groq."""
    return {
        "model": MODEL,
        "temperature": 0,
        "max_completion_tokens": 1500,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "<texto_usuario>\n"
                    f"{user_text}\n"
                    "</texto_usuario>"
                ),
            },
        ],
        "response_format": RESPONSE_SCHEMA,
    }


def safe_headers(response: requests.Response) -> dict[str, str | None]:
    """Extrae headers de diagnóstico sin exponer credenciales."""
    interesting = [
        "x-groq-region",
        "cf-ray",
        "retry-after",
        "x-ratelimit-limit-tokens",
        "x-ratelimit-remaining-tokens",
        "x-ratelimit-reset-tokens",
        "x-ratelimit-limit-requests",
        "x-ratelimit-remaining-requests",
        "x-ratelimit-reset-requests",
    ]

    return {
        key: response.headers.get(key)
        for key in interesting
        if response.headers.get(key) is not None
    }


def parse_error_body(response: requests.Response) -> Any:
    """Obtiene el cuerpo de error como JSON o, si falla, como texto."""
    try:
        return response.json()
    except ValueError:
        return response.text


def parse_retry_delay(
    error_body: Any,
    default_delay: float = DEFAULT_RETRY_DELAY,
) -> float:
    """Extrae el tiempo de espera indicado en el mensaje de Groq."""
    match = re.search(
        r"try again in\s+(\d+(?:\.\d+)?)s",
        str(error_body),
        re.IGNORECASE,
    )

    if match:
        return max(float(match.group(1)), 0.0)

    return default_delay


def get_retry_delay(
    response: requests.Response,
    error_body: Any,
    default_delay: float = DEFAULT_RETRY_DELAY,
) -> float:
    """Determina el tiempo de espera para reintentar un HTTP 429."""
    retry_after = response.headers.get("retry-after")

    if retry_after:
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            pass

    return parse_retry_delay(error_body, default_delay)


def extract_usage(data: dict[str, Any]) -> dict[str, int | None]:
    """Extrae los tokens consumidos de la respuesta."""
    usage_data = data.get("usage") or {}

    return {
        "prompt_tokens": usage_data.get("prompt_tokens"),
        "completion_tokens": usage_data.get("completion_tokens"),
        "total_tokens": usage_data.get("total_tokens"),
    }


def extract_metrics(data: dict[str, Any]) -> dict[str, float | int | None]:
    """Extrae las métricas de inferencia reportadas por Groq."""
    usage_data = data.get("usage") or {}

    metrics = {
        "queue_time": usage_data.get("queue_time"),
        "prompt_time": usage_data.get("prompt_time"),
        "completion_time": usage_data.get("completion_time"),
        "total_time": usage_data.get("total_time"),
        "cached_tokens": None,
    }

    details = usage_data.get("prompt_tokens_details")
    if isinstance(details, dict):
        metrics["cached_tokens"] = details.get("cached_tokens")

    return metrics


def calculate_network_overhead(
    elapsed: float,
    server_total: float | None,
) -> float | None:
    """Calcula el overhead estimado entre cliente y servidor."""
    if server_total is None:
        return None

    return round(elapsed - float(server_total), 4)


def send_request(
    http: requests.Session,
    payload: dict[str, Any],
) -> requests.Response:
    """Realiza una petición HTTP a Groq."""
    return http.post(
        API_URL,
        json=payload,
        timeout=HTTP_TIMEOUT,
    )


def call_groq(
    system_prompt: str,
    user_text: str,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Ejecuta una llamada a Groq y devuelve salida y métricas."""
    payload = build_payload(system_prompt, user_text)

    http = requests.Session()
    http.headers.update(build_headers())

    start_time = time.perf_counter()
    attempts = 0
    retry_delays: list[float] = []

    while attempts <= max_retries:
        attempts += 1

        try:
            response = send_request(http, payload)
            response_headers = safe_headers(response)

            if response.status_code == 429:
                error_body = parse_error_body(response)

                if attempts > max_retries:
                    elapsed = time.perf_counter() - start_time
                    raise RuntimeError(
                        f"HTTP 429 después de {attempts} intentos: {error_body}"
                    )

                retry_delay = get_retry_delay(response, error_body)
                retry_delays.append(retry_delay)

                print(
                    "HTTP 429 - límite de tasa alcanzado. "
                    f"Reintentando en {retry_delay:.2f} segundos "
                    f"(intento {attempts}/{max_retries + 1})..."
                )
                time.sleep(retry_delay)
                continue

            if not response.ok:
                error_body = parse_error_body(response)
                elapsed = time.perf_counter() - start_time
                raise RuntimeError(
                    f"HTTP {response.status_code}: {error_body}"
                )

            elapsed = time.perf_counter() - start_time
            data = response.json()
            choice = data["choices"][0]
            usage = extract_usage(data)
            metrics = extract_metrics(data)

            return {
                "raw_output": choice["message"].get("content"),
                "finish_reason": choice.get("finish_reason"),
                "latency_seconds": round(elapsed, 4),
                "usage": usage,
                "metrics": metrics,
                "http": {
                    "status_code": response.status_code,
                    "url": API_URL,
                    "network_overhead_seconds": calculate_network_overhead(
                        elapsed,
                        metrics.get("total_time"),
                    ),
                    "headers": response_headers,
                    "attempts": attempts,
                    "retry_delays": retry_delays,
                },
            }

        except requests.RequestException as error:
            elapsed = time.perf_counter() - start_time
            raise RuntimeError(
                f"Error HTTP después de {elapsed:.4f} s: {error}"
            ) from error

    raise RuntimeError("La llamada a Groq terminó sin una respuesta válida.")
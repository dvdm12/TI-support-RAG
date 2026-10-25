import re
import time
import threading
from typing import Any

import requests

from src.config import API_URL, MODEL, get_secret
from src.token_budget import enforce_input_budget, InputBudgetError, INPUT_TOKEN_LIMIT


HTTP_TIMEOUT = (10, 60)
DEFAULT_RETRY_DELAY = 15
_RATE_LOCK = threading.Lock()
_TOKEN_BUDGETS = {}


class ProviderFailure(RuntimeError):
    """Locally constructed, sanitized diagnostics; never external error bodies."""
    pass


def bounded_sleep(duration):
    if duration > 120:
        raise RuntimeError('La espera del proveedor excede 120 segundos.')
    while duration > 0:
        portion = min(duration,60)
        time.sleep(portion)
        duration -= portion


def safe_provider_code(error_body):
    error = error_body.get('error') if isinstance(error_body,dict) else None
    code = error.get('code') if isinstance(error,dict) else None
    return code if isinstance(code,str) and code in {'json_validate_failed','rate_limit_exceeded','invalid_request_error'} else 'unknown'


def parse_reset_seconds(value):
    """Parse provider durations such as 1m2.5s, not an assumed fixed window."""
    parts = re.findall(r'(\d+(?:\.\d+)?)(ms|s|m|h)', str(value))
    if not parts or ''.join(number + unit for number, unit in parts) != str(value):
        return None
    return sum(float(number) * {'ms':.001,'s':1,'m':60,'h':3600}[unit] for number, unit in parts)


def wait_for_token_budget(model, reservation):
    budget = _TOKEN_BUDGETS.get(model)
    if not budget:
        return 0.0
    remaining, observed, refill = budget
    available = remaining + max(0, time.monotonic() - observed) * refill
    delay = max(0, (reservation - available) / refill) if refill > 0 else 0
    if delay > 120:
        raise RuntimeError('El presupuesto del proveedor requiere esperar más de 120 segundos.')
    if delay:
        bounded_sleep(delay)
    return delay


def observe_token_budget(model, headers):
    try:
        remaining = float(headers['x-ratelimit-remaining-tokens'])
        limit = float(headers['x-ratelimit-limit-tokens'])
        reset = parse_reset_seconds(headers['x-ratelimit-reset-tokens'])
        if reset and 0 <= remaining < limit:
            _TOKEN_BUDGETS[model] = (remaining, time.monotonic(), (limit - remaining) / reset)
    except (KeyError, ValueError, TypeError):
        pass


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
                # Same bounds as SolicitudTI so the provider sees the limit (E06).
                "resumen": {"type": "string", "minLength": 10, "maxLength": 240},
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
        "Authorization": f"Bearer {get_secret('GROQ_API_KEY')}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Groq-Beta": "inference-metrics",
    }


def build_payload(system_prompt: str, user_text: str, *, model: str = MODEL,
                  response_format: dict | None = None) -> dict[str, Any]:
    """Construye el payload utilizado por la API de Groq."""
    payload = {
        "model": model,
        "temperature": 0,
        "max_completion_tokens": 800,
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
        "response_format": response_format or RESPONSE_SCHEMA,
    }
    if model in {'openai/gpt-oss-20b','openai/gpt-oss-120b'}:
        payload['reasoning_effort'] = 'low'
    return payload


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
    # Serialize request reservations within this process. RLS and secrets are
    # unaffected. Other processes may consume quota: bounded 429 retry remains.
    reservation = enforce_input_budget(payload)['total_tokens'] + payload.get('max_completion_tokens',800)
    with _RATE_LOCK:
        wait_for_token_budget(payload['model'], reservation)
        response = http.post(API_URL, json=payload, timeout=HTTP_TIMEOUT)
        observe_token_budget(payload['model'], response.headers)
        return response


def call_groq(
    system_prompt: str,
    user_text: str,
    max_retries: int = 3,
    *,
    model: str = MODEL,
    response_format: dict | None = None,
) -> dict[str, Any]:
    """Ejecuta una llamada a Groq y devuelve salida y métricas."""
    payload = build_payload(system_prompt, user_text, model=model,
                            response_format=response_format)
    budget = enforce_input_budget(payload)

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
                    raise ProviderFailure(
                        f"HTTP 429 después de {attempts} intentos."
                    )

                retry_delay = get_retry_delay(response, error_body)
                if retry_delay > 120 or sum(retry_delays) + retry_delay > 120:
                    raise ProviderFailure(f'HTTP 429: espera requerida de {retry_delay:.2f} s fuera del presupuesto de reintentos.')
                retry_delays.append(retry_delay)

                print(
                    "HTTP 429 - límite de tasa alcanzado. "
                    f"Reintentando en {retry_delay:.2f} segundos "
                    f"(intento {attempts}/{max_retries + 1})..."
                )
                bounded_sleep(retry_delay)
                continue

            if not response.ok:
                error_body = parse_error_body(response)
                code = safe_provider_code(error_body)
                # Groq can reject the model's structured output with HTTP 400.
                # Retry that specific generation failure once, never malformed
                # requests, permissions, authentication or arbitrary 400 bodies.
                if response.status_code == 400 and code == 'json_validate_failed' and attempts == 1 and max_retries > 0:
                    continue
                elapsed = time.perf_counter() - start_time
                raise ProviderFailure(
                    f"HTTP {response.status_code}: fallo del proveedor ({code})."
                )

            elapsed = time.perf_counter() - start_time
            data = response.json()
            choice = data["choices"][0]
            if choice.get("finish_reason") != "stop" or choice["message"].get("refusal"):
                raise RuntimeError("Groq no devolvió una respuesta completa aceptable.")
            usage = extract_usage(data)
            if usage['prompt_tokens'] is not None and usage['prompt_tokens'] > INPUT_TOKEN_LIMIT:
                raise InputBudgetError('El proveedor informó más de 1000 tokens de entrada; salida no aceptada.')
            metrics = extract_metrics(data)

            return {
                "raw_output": choice["message"].get("content"),
                "model": data.get("model", model),
                "finish_reason": choice.get("finish_reason"),
                "latency_seconds": round(elapsed, 4),
                "usage": usage,
                "metrics": metrics,
                "http": {
                    "input_budget":budget,
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
                f"Error HTTP después de {elapsed:.4f} s: {type(error).__name__}"
            ) from error

    raise RuntimeError("La llamada a Groq terminó sin una respuesta válida.")

"""Read-only access to the demonstration tickets stored in Supabase.

The table public.tickets is readable with the publishable key (RLS allows
SELECT to anon); only support accounts can change it, from the React view.
This module never writes and never sends the support credentials.
"""

import re

import requests

from src.config import get_secret

TICKET_CODE_PATTERN = r"TI-[0-9]{4}"
PUBLIC_FIELDS = ("estado", "detalle")
TIMEOUT_SECONDS = 5


class TicketCatalogError(RuntimeError):
    """The catalog cannot provide a reliable result."""


def _leer(code: str) -> dict | None:
    """Fetch one ticket row from Supabase, or None if it does not exist."""
    url = get_secret("SUPABASE_URL").rstrip("/")
    key = get_secret("SUPABASE_PUBLISHABLE_KEY")
    response = requests.get(
        f"{url}/rest/v1/tickets",
        params={"codigo": f"eq.{code}", "select": ",".join(PUBLIC_FIELDS)},
        headers={"apikey": key, "Accept": "application/json"},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or len(rows) > 1:
        raise ValueError("Respuesta inesperada del catálogo.")
    return rows[0] if rows else None


def listar_tickets(limit: int = 50) -> list[dict[str, str]]:
    """Return [{codigo, estado}] for every demo ticket, ordered by code."""
    try:
        url = get_secret("SUPABASE_URL").rstrip("/")
        key = get_secret("SUPABASE_PUBLISHABLE_KEY")
        response = requests.get(
            f"{url}/rest/v1/tickets",
            params={"select": "codigo,estado", "order": "codigo", "limit": str(limit)},
            headers={"apikey": key, "Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or not re.fullmatch(TICKET_CODE_PATTERN, str(row.get("codigo", "")))
            or not isinstance(row.get("estado"), str) or not row["estado"].strip()
            for row in rows
        ):
            raise ValueError("Respuesta inesperada del catálogo.")
        return [{"codigo": row["codigo"], "estado": row["estado"]} for row in rows]
    except (RuntimeError, ValueError, requests.RequestException) as exc:
        raise TicketCatalogError("Catálogo de tickets indisponible.") from exc


def consultar_estado_ticket(codigo: str) -> dict[str, str] | None:
    """Return public status details, or None if a valid code is absent."""
    code = codigo.strip().upper()
    if not re.fullmatch(TICKET_CODE_PATTERN, code):
        raise ValueError("El código de ticket debe tener el formato TI-1001.")

    try:
        record = _leer(code)
        if record is None:
            return None
        if not isinstance(record, dict) or any(
            not isinstance(record.get(field), str) or not record[field].strip()
            for field in PUBLIC_FIELDS
        ):
            raise ValueError("Registro de ticket inválido.")
        return {field: record[field] for field in PUBLIC_FIELDS}
    except (RuntimeError, ValueError, requests.RequestException) as exc:
        raise TicketCatalogError("Catálogo de tickets indisponible.") from exc

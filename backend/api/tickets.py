"""Read-only access to the demonstration ticket catalog."""

import json
import re
from pathlib import Path

TICKET_CODE_PATTERN = r"TI-[0-9]{4}"
TICKET_CATALOG = Path(__file__).with_name("tickets_demo.json")
PUBLIC_FIELDS = ("estado", "detalle")


class TicketCatalogError(RuntimeError):
    """The catalog cannot provide a reliable result."""


def consultar_estado_ticket(codigo: str) -> dict[str, str] | None:
    """Return public status details, or None if a valid code is absent."""
    code = codigo.strip().upper()
    if not re.fullmatch(TICKET_CODE_PATTERN, code):
        raise ValueError("El código de ticket debe tener el formato TI-1001.")

    try:
        catalog = json.loads(TICKET_CATALOG.read_text(encoding="utf-8"))
        if not isinstance(catalog, dict):
            raise ValueError("Se esperaba un catálogo de tickets.")
        if code not in catalog:
            return None

        record = catalog[code]
        if not isinstance(record, dict) or any(
            not isinstance(record.get(field), str) or not record[field].strip()
            for field in PUBLIC_FIELDS
        ):
            raise ValueError("Registro de ticket inválido.")
        return {field: record[field] for field in PUBLIC_FIELDS}
    except (OSError, ValueError) as exc:
        raise TicketCatalogError("Catálogo de tickets indisponible.") from exc

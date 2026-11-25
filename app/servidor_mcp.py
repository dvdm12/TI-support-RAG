"""Servidor MCP de solo lectura para el catálogo de tickets de demostración.

Expone una única herramienta: consultar_estado_ticket.
Transporte: stdio (arranca como subproceso desde sistema.py).

Uso directo:
    python servidor_mcp.py
"""
import json
import re
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError("Instala mcp>=1.0: pip install 'mcp>=1.0,<2'") from exc

CATALOG_PATH = Path(__file__).parent.parent / "backend" / "api" / "tickets_demo.json"
TICKET_CODE_PATTERN = re.compile(r"^TI-[0-9]{4}$")

mcp = FastMCP("Tickets TI-support-RAG")


def _cargar_catalogo() -> dict:
    try:
        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Formato inesperado en el catálogo.")
        return data
    except (OSError, ValueError) as exc:
        raise RuntimeError("Catálogo de tickets indisponible.") from exc


@mcp.tool()
def consultar_estado_ticket(codigo_ticket: str) -> dict:
    """Devuelve el estado y detalle de un ticket de demostración (solo lectura).

    Args:
        codigo_ticket: Código con formato TI-NNNN, por ejemplo TI-1001.

    Returns:
        Diccionario con campos: codigo_ticket, encontrada, estado, detalle, fuente.
    """
    codigo = codigo_ticket.strip().upper()
    if not TICKET_CODE_PATTERN.fullmatch(codigo):
        return {
            "codigo_ticket": codigo,
            "encontrada": False,
            "estado": "",
            "detalle": "El código debe tener el formato TI-NNNN (por ejemplo TI-1001).",
            "fuente": str(CATALOG_PATH),
        }

    catalogo = _cargar_catalogo()
    registro = catalogo.get(codigo)

    if registro is None:
        return {
            "codigo_ticket": codigo,
            "encontrada": False,
            "estado": "",
            "detalle": f"El ticket {codigo} no aparece en el catálogo de demostración.",
            "fuente": str(CATALOG_PATH),
        }

    return {
        "codigo_ticket": codigo,
        "encontrada": True,
        "estado": registro.get("estado", ""),
        "detalle": registro.get("detalle", ""),
        "fuente": str(CATALOG_PATH),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")

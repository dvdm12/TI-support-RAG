"""Servidor MCP de solo lectura para el catálogo de tickets de demostración.

Expone dos herramientas de solo lectura: consultar_estado_ticket y listar_tickets.
Transporte: stdio (arranca como subproceso desde sistema.py).

Uso directo:
    python servidor_mcp.py
"""
import os
import re

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError("Instala mcp>=1.0: pip install 'mcp>=1.0,<2'") from exc

TICKET_CODE_PATTERN = re.compile(r"^TI-[0-9]{4}$")
# Los tickets viven en la tabla public.tickets de Supabase (lectura pública por RLS;
# solo soporte los modifica). Este servidor solo lee, con la clave publishable.
FUENTE = "supabase:public.tickets"

mcp = FastMCP("Tickets TI-support-RAG")


def _consultar(params: dict) -> list:
    """GET a public.tickets con la clave publishable; devuelve la lista de filas."""
    import httpx

    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Catálogo de tickets indisponible: falta configurar Supabase.")
    try:
        respuesta = httpx.get(
            f"{url}/rest/v1/tickets",
            params=params,
            headers={"apikey": key, "Accept": "application/json"},
            timeout=5,
        )
        respuesta.raise_for_status()
        filas = respuesta.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("Catálogo de tickets indisponible.") from exc
    if not isinstance(filas, list):
        raise RuntimeError("Catálogo de tickets indisponible.")
    return filas


def _leer_ticket(codigo: str) -> dict | None:
    """Devuelve la fila {estado, detalle} del ticket, o None si no existe."""
    filas = _consultar({"codigo": f"eq.{codigo}", "select": "estado,detalle"})
    if len(filas) > 1:
        raise RuntimeError("Catálogo de tickets indisponible.")
    return filas[0] if filas else None


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
            "fuente": FUENTE,
        }

    registro = _leer_ticket(codigo)

    if registro is None:
        return {
            "codigo_ticket": codigo,
            "encontrada": False,
            "estado": "",
            "detalle": f"El ticket {codigo} no aparece en el catálogo de demostración.",
            "fuente": FUENTE,
        }

    return {
        "codigo_ticket": codigo,
        "encontrada": True,
        "estado": registro.get("estado", ""),
        "detalle": registro.get("detalle", ""),
        "fuente": FUENTE,
    }


@mcp.tool()
def listar_tickets() -> dict:
    """Lista los tickets de demostración con su estado (solo lectura).

    Returns:
        Diccionario con campos: tickets (lista de {codigo, estado}) y fuente.
    """
    filas = _consultar({"select": "codigo,estado", "order": "codigo", "limit": "50"})
    tickets = [
        {"codigo": f["codigo"], "estado": f["estado"]}
        for f in filas
        if isinstance(f, dict) and TICKET_CODE_PATTERN.fullmatch(str(f.get("codigo", "")))
        and isinstance(f.get("estado"), str)
    ]
    return {"tickets": tickets, "fuente": FUENTE}


if __name__ == "__main__":
    mcp.run(transport="stdio")

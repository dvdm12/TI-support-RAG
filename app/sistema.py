"""Coordina enrutamiento → MCP/RAG → respuesta para la app de Gradio.

Recibe la pregunta del usuario y el historial autorizado; devuelve un Resultado
que app.py puede representar directamente. No duplica lógica de almacenamiento.

Rutas disponibles:
  consulta_ticket      → MCP (servidor_mcp.py vía stdio)
  consulta_documental  → API del backend (/api/v1/rag/query/)
  respuesta_directa    → respuesta local (saludo, fuera de alcance)
  aclaracion           → respuesta local (intención mixta, código requerido)
  operacion_prohibida  → rechazo local (mutación de tickets)
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unicodedata import combining, normalize

import httpx

# ── Resultado ─────────────────────────────────────────────────────────────────

@dataclass
class Resultado:
    respuesta: str
    fuentes: list[dict] = field(default_factory=list)
    estado: str = ""
    traza: dict[str, Any] = field(default_factory=dict)


class SistemaError(RuntimeError):
    pass


# ── Enrutamiento (lógica extraída de backend/api/attention.py) ────────────────

_TICKET_CODE       = re.compile(r"\bti-[0-9]{4}\b(?!-)")
_TICKET_WORD       = re.compile(r"\b(?:tickets?|ti-[\w-]+)\b")
_TICKET_STATUS     = re.compile(
    r"\b(?:estado|estatus|seguimiento|consulta(?:r)? (?:el |mi |un )?ticket|"
    r"como (?:va|sigue|esta)|(?:esta|fue) (?:abierto|cerrado|resuelto|asignado|en revision)|"
    # Quejas de avance: preguntan por el estado aunque no usen la palabra.
    r"no (?:ha )?avanza(?:do)?|no (?:me )?(?:han )?(?:respondido|contestado|resuelto|atendido)|"
    r"sigue (?:abierto|pendiente|igual|sin (?:respuesta|resolver|avanzar))|"
    r"(?:esta )?(?:atascado|estancado|parado|detenido))\b"
)
_TICKET_MUTATION   = re.compile(
    r"(?:^|[.!?;]|\by\b)\s*(?:por favor[, ]+)?"
    r"(?:me\s+)?(?:(?:puedes|podrias|quiero|quisiera|necesito)\s+(?:que\s+)?(?:me\s+)?)?"
    # Infinitivo, imperativo y subjuntivo ("necesito que me crees un ticket").
    r"(?:cerrar|cierra|cierres|reabrir|reabre|reabras|cancelar|cancela|canceles|"
    r"eliminar|elimina|elimines|borrar|borra|borres|actualizar|actualiza|actualices|"
    r"modificar|modifica|modifiques|crear|crea|crees|abrir|abre|abras|"
    r"asignar|asigna|asignes|escalar|escala|escales|registrar|registra|registres|"
    r"generar|genera|generes|levantar|levanta|levantes)\b"
    r"[^.!?;]*\b(?:tickets?|ti-[\w-]+)\b"
)
_TICKET_LIST       = re.compile(
    r"\b(?:(?:que|cuales) tickets|tickets (?:hay|existen|disponibles|abiertos|registrados)|"
    r"(?:lista|listar|listado|muestrame|mostrar|ver|dame|ensename)\s+(?:de\s+|los\s+|todos\s+los\s+|mis\s+)*tickets|"
    r"mis tickets|todos los tickets)\b"
)
_HUMAN_REQUEST     = re.compile(
    r"\b(?:(?:escalar|escala|escalame|escalalo|escalarlo|pasar|pasame|transferir|transfiereme|"
    r"comunicar|comunicame|conectar|conectame)\s+(?:esto\s+|el caso\s+)?(?:a|con)\s+"
    r"(?:un |una |el |la )?(?:humano|persona|agente|tecnico|especialista|operador)|"
    r"hablar con (?:un |una |el |la )?(?:humano|persona|agente|tecnico|especialista|operador)|"
    r"(?:agente|soporte|atencion|asistencia|operador) human[oa]|persona real)\b"
)
_PROCEDURE         = re.compile(
    r"^(?:como (?!va\b|sigue\b|esta\b)|cual es el procedimiento|"
    r"que pasos|segun el manual|donde )"
)
_DIRECT            = re.compile(
    r"(?:(?:hola|buenos dias|buenas tardes|buenas noches)[, ]+[¿¡]?\s*)?"
    r"(?:hola|buenos dias|buenas tardes|buenas noches|que puedes hacer|"
    r"en que me puedes ayudar|como puedes ayudarme|que haces)[.!? ]*"
)
_GREETING_PREFIX   = re.compile(r"^(?:hola|buenos dias|buenas tardes|buenas noches)[,.! ]+[¿¡]?\s*")
_OUT_OF_SCOPE      = re.compile(
    r"(?:(?:(?:cual|que) es el nombre de|como se llama) mi (?:madre|mama|padre|papa|herman[oa]|pareja|mascota)|"
    r"cual es (?:mi fecha de nacimiento|la capital de [\w -]+)|"
    r"quien (?:escribio (?:el quijote|don quijote(?: de la mancha)?)|pinto la mona lisa)|"
    r"como (?:se (?:hace|prepara) una tortilla de patatas|preparo (?:una tortilla de patatas|arroz con leche))|"
    r"(?:quien|que seleccion) gano el mundial de futbol(?: de \d{4})?|"
    r"cuanto es \d+\s*(?:\+|menos|mas|por)\s*\d+)[.!? ]*"
)
_CLAUSE_BREAK      = re.compile(r"[.!?;]+\s*|\s+y\s+(?=(?:como|que|cual|donde)\b)")


def _normalizar(texto: str) -> str:
    return "".join(
        c for c in normalize("NFD", texto.casefold()) if not combining(c)
    ).strip(" ¿¡")


def _enrutar(pregunta: str) -> tuple[str, str | None]:
    """Devuelve (ruta, código_de_ticket_o_None)."""
    texto = _normalizar(pregunta)
    if _TICKET_MUTATION.search(texto):
        return "operacion_prohibida", None
    if _DIRECT.fullmatch(texto):
        return "respuesta_directa", None
    if _HUMAN_REQUEST.search(texto):
        return "solicitud_humano", None
    if _TICKET_LIST.search(texto) and not _TICKET_CODE.search(texto):
        return "listar_tickets", None
    clausulas = [p.strip(" ¿¡") for p in _CLAUSE_BREAK.split(texto) if p.strip(" ¿¡")]
    clausulas_ticket = [
        p for p in clausulas
        if _TICKET_WORD.search(p) and _TICKET_STATUS.search(p) and not _PROCEDURE.match(p)
    ]
    if clausulas_ticket:
        if any(_PROCEDURE.match(p) for p in clausulas):
            return "aclaracion", "intencion_mixta"
        codigos = set(_TICKET_CODE.findall(texto))
        if len(codigos) == 1:
            return "consulta_ticket", codigos.pop().upper()
        return "aclaracion", None
    if _TICKET_CODE.fullmatch(texto.rstrip("?!.")):
        return "aclaracion", None
    if _OUT_OF_SCOPE.fullmatch(_GREETING_PREFIX.sub("", texto)):
        return "respuesta_directa", "fuera_de_alcance"
    return "consulta_documental", None


# ── Respuestas locales ────────────────────────────────────────────────────────

def _respuesta_directa(codigo: str | None) -> Resultado:
    if codigo == "fuera_de_alcance":
        return Resultado(
            respuesta="Esa pregunta queda fuera del alcance de la mesa de ayuda. "
                      "Puedo consultar manuales de soporte TI y el estado de tickets.",
            estado="OK_RESPUESTA_DIRECTA",
            traza={"ruta": "respuesta_directa", "motivo": "fuera_de_alcance"},
        )
    return Resultado(
        respuesta="Puedo consultar manuales de soporte TI y el estado de tickets de demostración.",
        estado="OK_RESPUESTA_DIRECTA",
        traza={"ruta": "respuesta_directa", "motivo": "saludo"},
    )


def _aclaracion(codigo: str | None) -> Resultado:
    if codigo == "intencion_mixta":
        return Resultado(
            respuesta="¿Quieres consultar el estado del ticket o revisar el procedimiento en los manuales?",
            estado="OK_PIDE_ACLARACION",
            traza={"ruta": "aclaracion", "motivo": "intencion_mixta"},
        )
    return Resultado(
        respuesta="Indica un único código de ticket válido, por ejemplo TI-1001.",
        estado="OK_PIDE_ACLARACION",
        traza={"ruta": "aclaracion", "motivo": "codigo_requerido"},
    )


_RESPUESTA_HUMANO = (
    "No puedo transferirte a una persona desde este chat. Para atención humana, "
    "contacta a la mesa de ayuda por el canal de soporte autorizado e indica qué ocurre, "
    "en qué equipo o servicio y el mensaje de error, si aparece. Si ya tienes un ticket, "
    "puedo consultar su estado con el código (por ejemplo, TI-1001)."
)


def _solicitud_humano() -> Resultado:
    return Resultado(
        respuesta=_RESPUESTA_HUMANO,
        estado="OK_SOLICITUD_HUMANO",
        traza={"ruta": "solicitud_humano", "motivo": "derivacion_humana"},
    )


def _operacion_prohibida() -> Resultado:
    return Resultado(
        respuesta="Solo puedo consultar el estado de los tickets. Solicita el cambio a soporte TI.",
        estado="OPERACION_NO_PERMITIDA",
        traza={"ruta": "operacion_prohibida"},
    )


# ── MCP: consulta de tickets ──────────────────────────────────────────────────

_SERVIDOR_MCP = Path(__file__).parent / "servidor_mcp.py"


async def _llamar_mcp(herramienta: str, argumentos: dict, traza: dict[str, Any]) -> Any:
    """Arranca el servidor MCP por stdio, llama a una herramienta y devuelve su JSON."""
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import get_default_environment, stdio_client
    except ImportError:
        raise SistemaError("La librería MCP no está instalada. Ejecuta: pip install 'mcp>=1.0,<2'")

    # El cliente stdio arranca el servidor con un entorno mínimo; solo se le pasan
    # la URL y la clave publishable de Supabase (públicas), nunca tokens.
    entorno = get_default_environment()
    for nombre in ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY"):
        if os.environ.get(nombre):
            entorno[nombre] = os.environ[nombre]
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(_SERVIDOR_MCP)],
        env=entorno,
    )
    traza.update({"herramienta": herramienta, "servidor": str(_SERVIDOR_MCP)})
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(herramienta, argumentos)
    except Exception as exc:
        traza["error"] = type(exc).__name__
        raise SistemaError(f"El servidor MCP no pudo completar la consulta: {type(exc).__name__}") from None

    if result.isError:
        traza["mcp_error"] = True
        raise SistemaError("El servidor MCP rechazó la herramienta.")

    datos = result.content[0].text if result.content else ""
    try:
        import json
        return json.loads(datos) if isinstance(datos, str) else datos
    except Exception:
        raise SistemaError("El servidor MCP devolvió una respuesta con formato inesperado.")


async def _consultar_ticket_mcp(codigo: str) -> Resultado:
    """Consulta el ticket usando MCP vía stdio. Lanza SistemaError si falla."""
    traza: dict[str, Any] = {"ruta": "consulta_ticket", "codigo_solicitado": codigo}
    datos = await _llamar_mcp("consultar_estado_ticket", {"codigo_ticket": codigo}, traza)
    traza["resultado_mcp"] = datos

    if not datos.get("encontrada", False):
        return Resultado(
            respuesta=datos.get("detalle", f"El ticket {codigo} no fue encontrado."),
            estado="TICKET_NO_ENCONTRADO",
            traza=traza,
        )
    return Resultado(
        respuesta=f"Ticket {datos['codigo_ticket']} — {datos['estado']}. {datos['detalle']}",
        estado="OK_TICKET_CONSULTADO",
        traza=traza,
    )


async def _listar_tickets_mcp() -> Resultado:
    """Lista los tickets de demostración usando MCP vía stdio."""
    traza: dict[str, Any] = {"ruta": "listar_tickets"}
    datos = await _llamar_mcp("listar_tickets", {}, traza)
    tickets = datos.get("tickets") if isinstance(datos, dict) else None
    if not isinstance(tickets, list):
        raise SistemaError("El servidor MCP devolvió una respuesta con formato inesperado.")
    traza["total"] = len(tickets)
    if not tickets:
        return Resultado(respuesta="No hay tickets de demostración registrados.",
                         estado="OK_TICKETS_LISTADOS", traza=traza)
    lineas = "\n".join(f"- **{t['codigo']}** — {t['estado']}" for t in tickets)
    return Resultado(
        respuesta=(f"Tickets de demostración disponibles:\n\n{lineas}\n\n"
                   "Pregunta por un código para ver su detalle, por ejemplo: "
                   "«¿Cuál es el estado del ticket TI-1001?»."),
        estado="OK_TICKETS_LISTADOS",
        traza=traza,
    )


# ── RAG: consulta documental ──────────────────────────────────────────────────

async def _consultar_rag(
    pregunta: str,
    historial: list[tuple[str, str]],
    api_url: str,
    api_token: str,
) -> Resultado:
    """Llama al backend RAG y devuelve un Resultado.

    Solo se envía la pregunta actual. El backend aplica su propio enrutador al
    texto recibido: si se le pegaba el historial, las respuestas anteriores del
    asistente («…por ejemplo TI-1001») lo desviaban a consultas de ticket. El
    historial sigue persistido en Supabase y visible en la interfaz.
    """
    del historial  # la API /rag/query/ solo acepta el campo `pregunta`

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=5)) as client:
            response = await client.post(
                f"{api_url.rstrip('/')}/api/v1/rag/query/",
                json={"pregunta": pregunta},
                headers={"Authorization": f"Bearer {api_token}"},
            )
    except httpx.TimeoutException:
        raise SistemaError("El backend tardó demasiado en responder.")
    except httpx.RequestError as exc:
        raise SistemaError(f"No se pudo conectar con el backend: {type(exc).__name__}")

    try:
        data = response.json()
    except Exception:
        raise SistemaError(f"El backend devolvió una respuesta inesperada (HTTP {response.status_code}).")

    if not isinstance(data, dict):
        raise SistemaError(f"El backend devolvió una respuesta inesperada (HTTP {response.status_code}).")

    if response.is_error:
        error = (data.get("error") or {}).get("message") or "No se pudo completar la consulta."
        raise SistemaError(f"{error} (HTTP {response.status_code})")

    return Resultado(
        respuesta=data.get("respuesta") or "El backend no devolvió una respuesta.",
        fuentes=data.get("fuentes") or [],
        estado=data.get("estado") or "",
        traza={**(data.get("traza") or {}), "ruta": "consulta_documental"},
    )


# ── Punto de entrada principal ────────────────────────────────────────────────

async def procesar(
    pregunta: str,
    historial: list[tuple[str, str]],
    api_url: str,
    api_token: str,
) -> Resultado:
    """Enruta la pregunta y devuelve un Resultado listo para Gradio.

    Args:
        pregunta:  Texto libre del usuario (no vacío).
        historial: Pares (usuario, asistente) de la conversación activa.
        api_url:   URL base del backend Django (ej. http://127.0.0.1:8000).
        api_token: Bearer token de la API del backend.
    """
    pregunta = pregunta.strip()
    if not pregunta:
        return Resultado(
            respuesta="Escribe una pregunta antes de enviar.",
            estado="ERROR_ENTRADA",
        )

    ruta, codigo = _enrutar(pregunta)

    if ruta == "respuesta_directa":
        return _respuesta_directa(codigo)
    if ruta == "aclaracion":
        return _aclaracion(codigo)
    if ruta == "operacion_prohibida":
        return _operacion_prohibida()
    if ruta == "solicitud_humano":
        return _solicitud_humano()
    if ruta == "listar_tickets":
        return await _listar_tickets_mcp()
    if ruta == "consulta_ticket":
        return await _consultar_ticket_mcp(codigo)

    # consulta_documental
    return await _consultar_rag(pregunta, historial, api_url, api_token)

"""Routing rules for the support chat."""
import re
from unicodedata import combining, normalize

from .tickets import TICKET_CODE_PATTERN

TICKET_CODE = re.compile(rf"\b{TICKET_CODE_PATTERN.lower()}\b(?!-)")
TICKET_WORD = re.compile(r"\b(?:tickets?|ti-[\w-]+)\b")
TICKET_STATUS = re.compile(
    r"\b(?:estado|estatus|seguimiento|consulta(?:r)? (?:el |mi |un )?ticket|como (?:va|sigue|esta)|"
    r"(?:esta|fue) (?:abierto|cerrado|resuelto|asignado|en revision))\b"
)
TICKET_MUTATION = re.compile(
    r"(?:^|[.!?;]|\by\b)\s*(?:por favor[, ]+)?"
    r"(?:(?:puedes|podrias|quiero|necesito)\s+(?:que\s+)?(?:me\s+)?)?"
    r"(?:cerrar|cierra|cierres|reabrir|reabre|cancelar|cancela|"
    r"eliminar|elimina|borrar|borra|actualizar|actualiza|modificar|modifica|"
    r"crear|crea|abrir|abre|asignar|asigna|escalar|escala)\b"
    r"[^.!?;]*\b(?:tickets?|ti-[\w-]+)\b"
)
PROCEDURE = re.compile(
    r"^(?:como (?!va\b|sigue\b|esta\b)|cual es el procedimiento|"
    r"que pasos|segun el manual|donde )"
)
DIRECT = re.compile(
    r"(?:(?:hola|buenos dias|buenas tardes|buenas noches)[, ]+)?"
    r"(?:hola|buenos dias|buenas tardes|buenas noches|que puedes hacer|"
    r"en que me puedes ayudar|como puedes ayudarme|que haces)[.!? ]*"
)
CLAUSE_BREAK = re.compile(r"[.!?;]+\s*|\s+y\s+(?=(?:como|que|cual|donde)\b)")


def select_route(question):
    text = "".join(char for char in normalize("NFD", question.casefold())
                   if not combining(char)).strip(" ¿¡")
    if TICKET_MUTATION.search(text):
        return "operacion_prohibida", None
    if DIRECT.fullmatch(text):
        return "respuesta_directa", None
    clauses = [part.strip(" ¿¡") for part in CLAUSE_BREAK.split(text) if part.strip(" ¿¡")]
    ticket_clauses = [
        part for part in clauses
        if TICKET_WORD.search(part) and TICKET_STATUS.search(part) and not PROCEDURE.match(part)
    ]
    if ticket_clauses:
        if any(PROCEDURE.match(part) for part in clauses):
            return "aclaracion", "intencion_mixta"
        codes = set(TICKET_CODE.findall(text))
        if len(codes) == 1:
            return "consulta_ticket", codes.pop().upper()
        return "aclaracion", None
    if TICKET_CODE.fullmatch(text.rstrip("?!.")):
        return "aclaracion", None
    return "consulta_documental", None

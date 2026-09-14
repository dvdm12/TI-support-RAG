
from pydantic import ValidationError

from schemas.request_v1 import SolicitudTI


def validate_output(data: dict) -> tuple[bool, list[str], SolicitudTI | None]:
    """
    Valida la salida del modelo contra el esquema SolicitudTI.

    Returns:
        tuple:
            - True si la salida es válida.
            - Lista de errores de validación.
            - Objeto SolicitudTI validado o None si la validación falla.
    """
    try:
        validated = SolicitudTI.model_validate(data)
        return True, [], validated
    except ValidationError as error:
        errors = []

        for item in error.errors():
            location = ".".join(str(part) for part in item["loc"])
            message = item["msg"]
            errors.append(f"{location}: {message}")

        return False, errors, None

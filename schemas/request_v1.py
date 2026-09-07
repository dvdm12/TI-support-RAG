from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr


Categoria = Literal[
    "hardware",
    "software",
    "redes",
    "cuentas",
    "seguridad",
    "acceso",
    "otros",
]

Prioridad = Literal[
    "baja",
    "media",
    "alta",
]


class SolicitudTI(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    categoria: Categoria

    prioridad: Prioridad

    resumen: StrictStr = Field(
        min_length=10,
        max_length=240,
    )

    datos_faltantes: list[StrictStr]

    requiere_humano: StrictBool

    confianza: float = Field(
        ge=0.0,
        le=1.0,
    )
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictStr


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

    # Whitespace is stripped first, so blank entries fail min_length.
    datos_faltantes: list[Annotated[StrictStr, Field(min_length=1)]]

    requiere_humano: StrictBool

    # Strict: numbers only (ints allowed); no strings, booleans, NaN or infinity.
    confianza: StrictFloat = Field(
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )


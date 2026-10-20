"""Documentary response, independent of SolicitudTI classification."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RespuestaRAG(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    estado: Literal["respondida", "parcial", "aclaracion", "evidencia_insuficiente"]
    respuesta: str = Field(min_length=1, max_length=4000,
                          description="Texto en español. Incluye literalmente [F1], [F2], etc. dentro de esta cadena junto a cada afirmación documental citada.")
    citas: list[str] = Field(description="Etiquetas sin corchetes, como F1. Deben coincidir exactamente con las etiquetas [F1] escritas dentro de respuesta.")
    limitacion: str = Field(max_length=1500)

    @model_validator(mode="after")
    def coherence(self):
        if not self.respuesta.strip():
            raise ValueError("La respuesta está vacía.")
        if len(set(self.citas)) != len(self.citas):
            raise ValueError("Citas repetidas.")
        if self.estado in {"respondida", "parcial"} and not self.citas:
            raise ValueError("Una respuesta documental necesita citas.")
        if self.estado != "respondida" and not self.limitacion.strip():
            raise ValueError("Falta explicar la limitación o aclaración.")
        return self

from pydantic import BaseModel, ConfigDict, Field
from schemas.request_v1 import Categoria


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True,str_strip_whitespace=True)
    pregunta: str = Field(min_length=1,max_length=8000,
        description="Pregunta o incidente en español. Indica equipo/servicio, síntoma y condiciones relevantes. Se eliminan espacios externos; no admite texto vacío. Los límites adicionales de tokens pueden rechazar una pregunta de menos de 8000 caracteres.")


class SearchRequest(QueryRequest):
    categoria: Categoria | None = Field(default=None,
        description="Preferencia opcional de ranking: hardware, software, redes, cuentas, seguridad, acceso u otros. No filtra estrictamente los pasajes. Omite el campo o usa null para buscar sin esta preferencia.")

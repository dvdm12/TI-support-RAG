from pydantic import BaseModel, ConfigDict, Field
from schemas.request_v1 import Categoria


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True,str_strip_whitespace=True)
    pregunta: str = Field(min_length=1,max_length=8000,
        description="Pregunta o incidente en español. Indica equipo/servicio, síntoma y condiciones relevantes. Se eliminan espacios externos; no admite texto vacío. Los límites adicionales de tokens pueden rechazar una pregunta de menos de 8000 caracteres.")


class QueryRequest(QuestionRequest):
    texto_ocr: str | None = Field(default=None, min_length=1, max_length=8000,
        description="Texto OCR revisado por el usuario, opcional. Se combina con pregunta y se vuelve a validar el presupuesto completo. Es entrada del usuario, no una fuente documental.")


class SearchRequest(QuestionRequest):
    categoria: Categoria | None = Field(default=None,
        description="Preferencia opcional de ranking: hardware, software, redes, cuentas, seguridad, acceso u otros. No filtra estrictamente los pasajes. Omite el campo o usa null para buscar sin esta preferencia.")


class OCRExtractRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    pregunta: str = Field(default='', max_length=8000,
        description="Descripción que acompañará al OCR. Opcional durante la extracción; la consulta final siempre revalida el contenido revisado.")


class OCRBudget(BaseModel):
    admisible: bool
    tokens_entrada: int
    limite_entrada: int
    tokens_busqueda: int | None
    limite_busqueda: int | None
    motivo: str | None


class OCRResponse(BaseModel):
    request_id: str
    texto_ocr: str
    motor: str
    idiomas: str
    confianza_ocr: float
    cantidad_palabras: int
    presupuesto: OCRBudget

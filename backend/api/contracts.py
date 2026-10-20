from pydantic import BaseModel, ConfigDict, Field
from schemas.request_v1 import Categoria


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True,str_strip_whitespace=True)
    pregunta: str = Field(min_length=1,max_length=8000)


class SearchRequest(QueryRequest):
    categoria: Categoria | None = None

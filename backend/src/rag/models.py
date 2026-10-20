"""Validated document, fragment, configuration and retrieval contracts."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from schemas.request_v1 import Categoria


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    source: str
    title: str
    section: str
    category: Categoria
    version: str
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    pages: list[int]
    text: str = Field(min_length=1)
    simulated: bool = True


class Chunk(Section):
    chunk_id: str
    tokens: int = Field(gt=0)


class EmbeddingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modelo: str
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    dimension: Literal[384] = 384
    normalizados: Literal[True] = True
    similitud: Literal["coseno"] = "coseno"
    max_seq_length: int = Field(gt=0)
    estrategia: Literal["characters", "overlap", "sections"]
    chunk_chars: int = Field(gt=0)
    overlap_chars: int = Field(ge=0)
    max_tokens: int = Field(gt=0)
    preparation_version: str = "pdf-sections-v1"


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str
    content: str = Field(min_length=1, max_length=10000)
    metadata: dict
    similitud: float = Field(ge=-1.00001, le=1.00001, allow_inf_nan=False)

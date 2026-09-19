from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BoundingBox:
    """Área rectangular de un elemento detectado en la imagen."""

    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class OCRBlock:
    """Fragmento de texto detectado por el motor OCR."""

    text: str
    confidence: float
    bounding_box: BoundingBox


@dataclass(frozen=True)
class OCRResult:
    """Resultado normalizado de una extracción OCR."""

    text: str
    word_count: int
    ocr_confidence: float
    has_text: bool

    blocks: list[OCRBlock]

    image_path: str
    image_size: tuple[int, int]

    language: str
    engine: str

    def to_dict(self) -> dict[str, Any]:
        """Convierte el resultado a un diccionario serializable."""
        return asdict(self)
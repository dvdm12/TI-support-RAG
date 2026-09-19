from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from .exceptions import (
    OCRConfigurationError,
    OCRDependencyError,
    OCRExtractionError,
)
from .models import BoundingBox, OCRBlock, OCRResult
from .strategy import OCRStrategy


DEFAULT_LANGUAGES = ["es", "en"]
DEFAULT_GPU = False
DEFAULT_DETAIL = 1
DEFAULT_PARAGRAPH = False


class EasyOCRStrategy(OCRStrategy):
    """Implementación concreta de OCR basada en EasyOCR.

    Adapta la salida de EasyOCR al contrato común ``OCRResult`` para que
    el motor pueda sustituirse sin modificar ``OCRExtractor``.
    """

    name = "easyocr"

    def __init__(
        self,
        languages: list[str] | None = None,
        *,
        gpu: bool = DEFAULT_GPU,
        decoder: str = "greedy",
        batch_size: int = 1,
        workers: int = 0,
        paragraph: bool = DEFAULT_PARAGRAPH,
        verbose: bool = False,
    ) -> None:
        selected_languages = languages or DEFAULT_LANGUAGES.copy()

        if not selected_languages:
            raise OCRConfigurationError(
                "Debe especificarse al menos un idioma para EasyOCR."
            )

        if batch_size <= 0:
            raise OCRConfigurationError(
                "batch_size debe ser mayor que 0."
            )

        if workers < 0:
            raise OCRConfigurationError(
                "workers no puede ser negativo."
            )

        self.languages = selected_languages
        self.gpu = gpu
        self.decoder = decoder
        self.batch_size = batch_size
        self.workers = workers
        self.paragraph = paragraph
        self.verbose = verbose

        self._reader: Any | None = None

    def _build_reader(self) -> Any:
        """Construye el lector EasyOCR de forma diferida."""
        try:
            import easyocr
        except ImportError as exc:
            raise OCRDependencyError(
                "EasyOCR no está instalado en el entorno actual."
            ) from exc

        try:
            return easyocr.Reader(
                self.languages,
                gpu=self.gpu,
                verbose=self.verbose,
            )
        except Exception as exc:
            raise OCRConfigurationError(
                f"No fue posible inicializar EasyOCR: {exc}"
            ) from exc

    @property
    def reader(self) -> Any:
        """Devuelve el lector reutilizable de EasyOCR."""
        if self._reader is None:
            self._reader = self._build_reader()

        return self._reader

    @staticmethod
    def _validate_image_content(image_path: Path) -> None:
        """Comprueba que el archivo sea una imagen legible."""
        try:
            with Image.open(image_path) as image:
                image.verify()
        except (OSError, Image.UnidentifiedImageError) as exc:
            raise OCRExtractionError(
                f"La imagen no pudo validarse: {image_path}"
            ) from exc

    @staticmethod
    def _parse_box(points: Any) -> BoundingBox:
        """Convierte un polígono EasyOCR en un BoundingBox."""
        try:
            coordinates = [
                (float(point[0]), float(point[1]))
                for point in points
                if len(point) >= 2
            ]

            if not coordinates:
                return BoundingBox(
                    left=0,
                    top=0,
                    width=0,
                    height=0,
                )

            left = int(min(point[0] for point in coordinates))
            top = int(min(point[1] for point in coordinates))
            right = int(max(point[0] for point in coordinates))
            bottom = int(max(point[1] for point in coordinates))

            return BoundingBox(
                left=left,
                top=top,
                width=max(0, right - left),
                height=max(0, bottom - top),
            )
        except (TypeError, ValueError, IndexError):
            return BoundingBox(
                left=0,
                top=0,
                width=0,
                height=0,
            )

    @classmethod
    def _extract_blocks(cls, results: Any) -> list[OCRBlock]:
        """Convierte la salida estándar de EasyOCR en OCRBlock."""
        if not isinstance(results, list):
            return []

        blocks: list[OCRBlock] = []

        for item in results:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue

            points, raw_text, raw_confidence = item[:3]
            text = str(raw_text).strip()

            if not text:
                continue

            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError):
                confidence = 0.0

            blocks.append(
                OCRBlock(
                    text=text,
                    confidence=max(0.0, min(100.0, confidence * 100.0)),
                    bounding_box=cls._parse_box(points),
                )
            )

        return blocks

    @staticmethod
    def _calculate_confidence(blocks: list[OCRBlock]) -> float:
        """Calcula la confianza media de reconocimiento en escala 0-100."""
        if not blocks:
            return 0.0

        return round(
            sum(block.confidence for block in blocks) / len(blocks),
            2,
        )

    def extract(self, image_path: Path) -> OCRResult:
        """Extrae texto mediante EasyOCR y devuelve un OCRResult."""
        image_path = Path(image_path)

        self.validate_image(image_path)
        self._validate_image_content(image_path)

        try:
            results = self.reader.readtext(
                str(image_path),
                decoder=self.decoder,
                batch_size=self.batch_size,
                workers=self.workers,
                detail=DEFAULT_DETAIL,
                paragraph=self.paragraph,
            )
        except Exception as exc:
            raise OCRExtractionError(
                f"EasyOCR no pudo procesar la imagen: {exc}"
            ) from exc

        blocks = self._extract_blocks(results)
        text = "\n".join(block.text for block in blocks)

        try:
            with Image.open(image_path) as image:
                image_size = image.size
        except (OSError, Image.UnidentifiedImageError) as exc:
            raise OCRExtractionError(
                f"No se pudo obtener el tamaño de la imagen: {image_path}"
            ) from exc

        return OCRResult(
            text=text,
            word_count=len(text.split()),
            ocr_confidence=self._calculate_confidence(blocks),
            has_text=bool(text),
            blocks=blocks,
            image_path=str(image_path),
            image_size=image_size,
            language="+".join(self.languages),
            engine=self.name,
        )


__all__ = [
    "EasyOCRStrategy",
]

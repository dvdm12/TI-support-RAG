from __future__ import annotations

import math
import shutil
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps
import pytesseract

from .exceptions import (
    OCRConfigurationError,
    OCRDependencyError,
    OCRExtractionError,
)
from .models import BoundingBox, OCRBlock, OCRResult
from .strategy import OCRStrategy


DEFAULT_LANGUAGE = "spa+eng"
DEFAULT_PSM = 6
DEFAULT_SCALE = 2.0


class TesseractStrategy(OCRStrategy):
    """Implementación concreta de OCR basada en Tesseract."""

    name = "tesseract"

    def __init__(
        self,
        language: str = DEFAULT_LANGUAGE,
        psm: int = DEFAULT_PSM,
        scale: float = DEFAULT_SCALE,
    ) -> None:
        if not isinstance(language, str) or not language.strip():
            raise OCRConfigurationError(
                "language no puede estar vacío."
            )

        if psm <= 0:
            raise OCRConfigurationError(
                "psm debe ser mayor que 0."
            )

        if scale <= 0:
            raise OCRConfigurationError(
                "scale debe ser mayor que 0."
            )

        self.language = language
        self.psm = psm
        self.scale = scale

    @staticmethod
    def _get_tesseract_binary() -> str:
        """Obtiene el ejecutable de Tesseract disponible en PATH."""
        binary = shutil.which("tesseract")

        if binary is None:
            raise OCRDependencyError(
                "Tesseract no está instalado o no está disponible en PATH."
            )

        return binary

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocesa la imagen para mejorar la extracción OCR."""
        image = image.convert("RGB")

        if not math.isclose(self.scale, 1.0):
            width = max(1, round(image.width * self.scale))
            height = max(1, round(image.height * self.scale))

            image = image.resize(
                (width, height),
                Image.Resampling.LANCZOS,
            )

        grayscale = ImageOps.grayscale(image)
        grayscale = ImageOps.autocontrast(grayscale)

        return grayscale.filter(ImageFilter.SHARPEN)

    def _extract_blocks(
        self,
        image: Image.Image,
    ) -> list[OCRBlock]:
        """Extrae palabras con confianza y coordenadas."""
        try:
            data = pytesseract.image_to_data(
                image,
                lang=self.language,
                config=f"--psm {self.psm}",
                output_type=pytesseract.Output.DICT,
            )
        except pytesseract.TesseractError as exc:
            raise OCRExtractionError(
                f"Tesseract no pudo extraer los bloques: {exc}"
            ) from exc

        blocks: list[OCRBlock] = []

        for index, raw_text in enumerate(data.get("text", [])):
            text = raw_text.strip()

            if not text:
                continue

            try:
                confidence = float(data["conf"][index])
                left = int(data["left"][index])
                top = int(data["top"][index])
                width = int(data["width"][index])
                height = int(data["height"][index])
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise OCRExtractionError(
                    "Tesseract devolvió datos de bloque inválidos."
                ) from exc

            blocks.append(
                OCRBlock(
                    text=text,
                    confidence=max(0.0, confidence),
                    bounding_box=BoundingBox(
                        left=left,
                        top=top,
                        width=width,
                        height=height,
                    ),
                )
            )

        return blocks

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza espacios sin alterar agresivamente el texto técnico."""
        lines: list[str] = []

        for raw_line in text.splitlines():
            line = " ".join(raw_line.split()).strip()

            if line:
                lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _calculate_confidence(
        blocks: list[OCRBlock],
    ) -> float:
        """Calcula la confianza media de los bloques detectados."""
        if not blocks:
            return 0.0

        return round(
            sum(block.confidence for block in blocks) / len(blocks),
            2,
        )

    def extract(self, image_path: Path) -> OCRResult:
        """Extrae texto y devuelve un OCRResult normalizado."""
        image_path = Path(image_path)

        self.validate_image(image_path)

        tesseract_binary = self._get_tesseract_binary()
        pytesseract.pytesseract.tesseract_cmd = tesseract_binary

        try:
            with Image.open(image_path) as image:
                original_size = image.size
                processed = self._preprocess_image(image)

                text = pytesseract.image_to_string(
                    processed,
                    lang=self.language,
                    config=f"--psm {self.psm}",
                )

                blocks = self._extract_blocks(processed)

        except OSError as exc:
            raise OCRExtractionError(
                f"No se pudo abrir o procesar la imagen: {exc}"
            ) from exc
        except pytesseract.TesseractError as exc:
            raise OCRExtractionError(
                f"Tesseract no pudo procesar la imagen: {exc}"
            ) from exc

        normalized_text = self._normalize_text(text)

        return OCRResult(
            text=normalized_text,
            word_count=len(normalized_text.split()),
            ocr_confidence=self._calculate_confidence(blocks),
            has_text=bool(normalized_text),
            blocks=blocks,
            image_path=str(image_path),
            image_size=original_size,
            language=self.language,
            engine=self.name,
        )


__all__ = [
    "TesseractStrategy",
]

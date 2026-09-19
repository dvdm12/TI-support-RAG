from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import re
import shutil
import math
from typing import Any

from PIL import Image, ImageOps, ImageFilter
import pytesseract


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

DEFAULT_LANG = "spa"
DEFAULT_MIN_CONFIDENCE = 20.0
DEFAULT_SCALE = 2.0
DEFAULT_PSM = 6


@dataclass(frozen=True)
class OCRBlock:
    """Bloque de texto detectado por OCR con posición y confianza."""

    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int


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
    psm: int
    preprocessing_scale: float

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blocks"] = [asdict(block) for block in self.blocks]
        return data


def validate_attachment(image_path: Path) -> tuple[bool, str | None]:
    """
    Valida que el archivo exista, sea un archivo regular y tenga
    una extensión soportada por el extractor OCR.
    """
    image_path = Path(image_path)

    if not image_path.exists():
        return False, "El archivo no existe."

    if not image_path.is_file():
        return False, "La ruta indicada no corresponde a un archivo."

    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False, (
            f"Formato de imagen no soportado: {image_path.suffix or '<sin extensión>'}."
        )

    return True, None


def _find_tesseract_languages() -> set[str]:
    """
    Obtiene los idiomas instalados en Tesseract.

    La función devuelve un conjunto vacío cuando Tesseract no está disponible.
    """
    if shutil.which("tesseract") is None:
        return set()

    try:
        return set(pytesseract.get_languages(config=""))
    except pytesseract.TesseractError:
        return set()


def _select_language(requested: str | None = None) -> str:
    """
    Selecciona el idioma OCR.

    Preferencia:
    1. Idioma solicitado si está instalado.
    2. spa+eng si ambos están disponibles.
    3. spa si está disponible.
    4. eng si está disponible.
    5. el idioma solicitado como último recurso.
    """
    installed = _find_tesseract_languages()

    if requested:
        requested_parts = [part.strip() for part in requested.split("+") if part.strip()]
        if requested_parts and all(part in installed for part in requested_parts):
            return requested

    if {"spa", "eng"} <= installed:
        return "spa+eng"

    if "spa" in installed:
        return "spa"

    if "eng" in installed:
        return "eng"

    return requested or DEFAULT_LANG


def _preprocess_image(image: Image.Image, scale: float) -> Image.Image:
    """
    Preprocesa una captura de pantalla para mejorar la legibilidad OCR.

    El objetivo es conservar texto técnico pequeño sin alterar demasiado
    caracteres relevantes como COM3, códigos de error o identificadores.
    """
    image = image.convert("RGB")

    if not math.isclose(scale, 1.0):
        width = max(1, round(image.width * scale))
        height = max(1, round(image.height * scale))
        image = image.resize((width, height), Image.Resampling.LANCZOS)

    grayscale = ImageOps.grayscale(image)
    grayscale = ImageOps.autocontrast(grayscale)
    grayscale = grayscale.filter(ImageFilter.SHARPEN)

    return grayscale


def _normalize_text(text: str) -> str:
    """
    Normaliza ruido superficial sin modificar agresivamente el contenido técnico.
    """
    lines: list[str] = []

    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def _extract_blocks(
    image: Image.Image,
    language: str,
    psm: int,
) -> list[OCRBlock]:
    """
    Extrae palabras/bloques con coordenadas y confianza usando image_to_data.
    """
    data = pytesseract.image_to_data(
        image,
        lang=language,
        config=f"--psm {psm}",
        output_type=pytesseract.Output.DICT,
    )

    blocks: list[OCRBlock] = []

    for i, raw_text in enumerate(data.get("text", [])):
        text = raw_text.strip()

        if not text:
            continue

        try:
            confidence = float(data["conf"][i])
        except (KeyError, TypeError, ValueError):
            confidence = 0.0

        blocks.append(
            OCRBlock(
                text=text,
                confidence=max(0.0, confidence),
                left=int(data["left"][i]),
                top=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
            )
        )

    return blocks


def _calculate_confidence(blocks: list[OCRBlock]) -> float:
    """
    Calcula la confianza media de las palabras detectadas.

    Devuelve 0.0 cuando no existen bloques.
    """
    if not blocks:
        return 0.0

    return round(
        sum(block.confidence for block in blocks) / len(blocks),
        2,
    )


def extract_text_from_image(
    image_path: Path,
    *,
    language: str | None = None,
    psm: int = DEFAULT_PSM,
    scale: float = DEFAULT_SCALE,
) -> dict[str, Any]:
    """
    Extrae texto visible de una imagen y devuelve un resultado compatible
    con el pipeline actual del proyecto.

    El resultado contiene:
    - text
    - word_count
    - ocr_confidence (0-100)
    - has_text
    - blocks con coordenadas
    - metadatos de la imagen y configuración OCR
    """
    image_path = Path(image_path)

    valid, error = validate_attachment(image_path)
    if not valid:
        raise ValueError(error or "Archivo de imagen inválido.")

    tesseract_path = shutil.which("tesseract")
    if not tesseract_path:
        raise RuntimeError(
            "Tesseract no está instalado o no está disponible en PATH."
        )

    pytesseract.pytesseract.tesseract_cmd = tesseract_path

    if scale <= 0:
        raise ValueError("scale debe ser mayor que 0.")

    if psm <= 0:
        raise ValueError("psm debe ser mayor que 0.")

    selected_language = _select_language(language)

    try:
        with Image.open(image_path) as image:
            original_size = image.size
            processed = _preprocess_image(image, scale)

            blocks = _extract_blocks(
                processed,
                selected_language,
                psm,
            )

            raw_text = pytesseract.image_to_string(
                processed,
                lang=selected_language,
                config=f"--psm {psm}",
            )

    except OSError as exc:
        raise RuntimeError(
            f"No se pudo abrir o procesar la imagen: {exc}"
        ) from exc
    except pytesseract.TesseractError as exc:
        raise RuntimeError(
            f"Tesseract no pudo procesar la imagen: {exc}"
        ) from exc

    text = _normalize_text(raw_text)
    words = text.split()
    confidence = _calculate_confidence(blocks)

    result = OCRResult(
        text=text,
        word_count=len(words),
        ocr_confidence=confidence,
        has_text=bool(text),
        blocks=blocks,
        image_path=str(image_path),
        image_size=original_size,
        language=selected_language,
        psm=psm,
        preprocessing_scale=scale,
    )

    return result.to_dict()


def validate_extracted_text(
    ocr_result: dict[str, Any],
    *,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_words: int = 1,
) -> tuple[bool, list[str]]:
    """
    Valida el resultado OCR sin intentar interpretar el significado del texto.

    Reglas:
    - Debe existir texto.
    - Debe alcanzar el mínimo de palabras.
    - Si existe texto pero la confianza es demasiado baja, se considera
      una extracción de baja calidad.

    La confianza OCR (0-100) NO representa la confianza de clasificación
    del modelo (0-1).
    """
    errors: list[str] = []

    if not isinstance(ocr_result, dict):
        return False, ["Resultado OCR inválido: se esperaba un diccionario."]

    text = str(ocr_result.get("text", "")).strip()
    has_text = bool(ocr_result.get("has_text", text))
    word_count = int(ocr_result.get("word_count", len(text.split())))
    confidence = float(ocr_result.get("ocr_confidence", 0.0))

    if not has_text or not text:
        errors.append("El OCR no produjo texto.")

    if word_count < min_words:
        errors.append(
            f"El OCR produjo menos de {min_words} palabra(s)."
        )

    if text and confidence < min_confidence:
        errors.append(
            f"La confianza OCR ({confidence:.2f}) está por debajo "
            f"del mínimo configurado ({min_confidence:.2f})."
        )

    return not errors, errors


def extract_and_validate(
    image_path: Path,
    *,
    language: str | None = None,
    psm: int = DEFAULT_PSM,
    scale: float = DEFAULT_SCALE,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_words: int = 1,
) -> tuple[dict[str, Any], bool, list[str]]:
    """
    Atajo para ejecutar extracción y validación en una sola operación.
    """
    result = extract_text_from_image(
        image_path,
        language=language,
        psm=psm,
        scale=scale,
    )

    valid, errors = validate_extracted_text(
        result,
        min_confidence=min_confidence,
        min_words=min_words,
    )

    return result, valid, errors


__all__ = [
    "OCRBlock",
    "OCRResult",
    "SUPPORTED_EXTENSIONS",
    "extract_text_from_image",
    "validate_attachment",
    "validate_extracted_text",
    "extract_and_validate",
]

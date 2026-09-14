from pathlib import Path
from typing import Any

import pytesseract
from PIL import Image


SUPPORTED_IMAGE_TYPES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def validate_attachment(file_path: str | Path) -> tuple[bool, str]:
    """
    Valida que el archivo exista, sea un archivo regular y
    corresponda a una imagen soportada.
    """
    path = Path(file_path).expanduser()

    if not path.exists():
        return False, f"Archivo no encontrado: {path}"

    if not path.is_file():
        return False, f"La ruta no corresponde a un archivo: {path}"

    if path.suffix.lower() not in SUPPORTED_IMAGE_TYPES:
        return False, (
            f"Tipo de archivo no soportado: {path.suffix}. "
            f"Tipos permitidos: {', '.join(sorted(SUPPORTED_IMAGE_TYPES))}"
        )

    return True, ""


def extract_text_from_image(file_path: str | Path) -> dict[str, Any]:
    """
    Extrae texto visible de una imagen mediante OCR.

    Devuelve:
    - text: texto reconocido;
    - word_count: cantidad de palabras reconocidas;
    - ocr_confidence: confianza media del OCR (0-100);
    - has_text: indica si se obtuvo texto.
    """
    valid, error = validate_attachment(file_path)

    if not valid:
        raise ValueError(error)

    path = Path(file_path)

    try:
        image = Image.open(path)
        image.load()

        ocr_data = pytesseract.image_to_data(
            image,
            lang="spa",
            output_type=pytesseract.Output.DICT,
        )
    except Exception as error:
        raise RuntimeError(
            f"No fue posible procesar la imagen mediante OCR: {error}"
        ) from error

    words: list[str] = []
    confidences: list[float] = []

    for text, confidence in zip(
        ocr_data.get("text", []),
        ocr_data.get("conf", []),
    ):
        text = text.strip()

        if not text:
            continue

        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            continue

        words.append(text)

        if confidence_value >= 0:
            confidences.append(confidence_value)

    extracted_text = " ".join(words).strip()

    average_confidence = (
        sum(confidences) / len(confidences)
        if confidences
        else 0.0
    )

    return {
        "text": extracted_text,
        "word_count": len(words),
        "ocr_confidence": round(average_confidence, 2),
        "has_text": bool(extracted_text),
    }


def validate_extracted_text(
    extraction: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Valida la estructura y utilidad mínima de la extracción OCR.

    La aplicación comprueba que:
    - existan todos los campos esperados;
    - el texto sea una cadena no vacía;
    - word_count sea entero no negativo;
    - la confianza esté entre 0 y 100;
    - has_text sea booleano.
    """
    errors: list[str] = []

    if not isinstance(extraction, dict):
        return False, ["La extracción OCR no tiene formato de diccionario."]

    required_fields = {
        "text",
        "word_count",
        "ocr_confidence",
        "has_text",
    }

    missing_fields = required_fields - extraction.keys()

    if missing_fields:
        errors.append(
            "Faltan campos en la extracción: "
            + ", ".join(sorted(missing_fields))
        )

    text = extraction.get("text")
    word_count = extraction.get("word_count")
    ocr_confidence = extraction.get("ocr_confidence")
    has_text = extraction.get("has_text")

    if not isinstance(text, str):
        errors.append("El texto extraído debe ser una cadena.")
    elif not text.strip():
        errors.append(
            "No se pudo extraer texto visible de la imagen."
        )

    if not isinstance(word_count, int) or word_count < 0:
        errors.append(
            "La cantidad de palabras reconocidas no es válida."
        )

    if (
        not isinstance(ocr_confidence, (int, float))
        or not 0.0 <= ocr_confidence <= 100.0
    ):
        errors.append(
            "La confianza del OCR debe estar entre 0 y 100."
        )

    if not isinstance(has_text, bool):
        errors.append(
            "El indicador has_text debe ser booleano."
        )

    return not errors, errors


def prepare_multimodal_input(
    user_text: str,
    file_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Prepara una entrada textual o multimodal.

    Si existe una imagen:
    1. valida el archivo;
    2. extrae texto visible mediante OCR;
    3. valida la extracción;
    4. conserva la evidencia extraída;
    5. devuelve la información lista para continuar el flujo.

    Este módulo no determina por sí mismo la causa del problema
    ni inventa hechos que no estén presentes en la entrada.
    """
    result: dict[str, Any] = {
        "text": user_text.strip(),
        "has_attachment": False,
        "attachment": None,
        "extracted_text": None,
        "extraction": None,
        "extraction_valid": True,
        "extraction_errors": [],
    }

    if file_path is None:
        return result

    valid, error = validate_attachment(file_path)

    if not valid:
        raise ValueError(error)

    path = Path(file_path).expanduser()
    extraction = extract_text_from_image(path)

    extraction_valid, extraction_errors = validate_extracted_text(
        extraction
    )

    result["has_attachment"] = True
    result["attachment"] = {
        "path": str(path),
        "filename": path.name,
        "extension": path.suffix.lower(),
    }
    result["extraction"] = extraction
    result["extracted_text"] = extraction["text"]
    result["extraction_valid"] = extraction_valid
    result["extraction_errors"] = extraction_errors

    return result
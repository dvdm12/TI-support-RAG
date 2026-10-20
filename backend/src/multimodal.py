from pathlib import Path
from typing import Any

from .ocr import OCRExtractor, OCRFactory


def prepare_multimodal_input(
    user_text: str,
    file_path: str | Path | None = None,
    *,
    ocr_engine: str = "easyocr",
    **ocr_options: Any,
) -> dict[str, Any]:
    """
    Prepara una entrada textual o multimodal para el pipeline.

    La responsabilidad de este módulo es orquestar la integración
    entre la solicitud del usuario y la evidencia obtenida desde
    una imagen mediante la capa OCR.

    La implementación concreta del OCR se resuelve mediante
    OCRFactory y OCRExtractor.
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

    path = Path(file_path)

    strategy = OCRFactory.create(
        ocr_engine,
        **ocr_options,
    )

    extractor = OCRExtractor(strategy)
    ocr_result = extractor.extract(path)

    extraction_valid = ocr_result.has_text
    extraction_errors: list[str] = []

    if not extraction_valid:
        extraction_errors.append(
            "No se pudo extraer texto visible de la imagen."
        )

    result["has_attachment"] = True
    result["attachment"] = {
        "path": str(path),
        "filename": path.name,
        "extension": path.suffix.lower(),
    }
    result["extraction"] = ocr_result.to_dict()
    result["extracted_text"] = ocr_result.text
    result["extraction_valid"] = extraction_valid
    result["extraction_errors"] = extraction_errors

    return result


__all__ = [
    "prepare_multimodal_input",
]
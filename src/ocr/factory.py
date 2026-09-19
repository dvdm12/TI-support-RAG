from __future__ import annotations

from typing import Any

from .easyocr_strategy import EasyOCRStrategy
from .exceptions import OCRConfigurationError
from .strategy import OCRStrategy
from .tesseract_strategy import TesseractStrategy


class OCRFactory:
    """Fábrica para crear estrategias OCR a partir de una configuración."""

    _STRATEGIES: dict[str, type[OCRStrategy]] = {
        "tesseract": TesseractStrategy,
        "easyocr": EasyOCRStrategy,
    }

    @classmethod
    def create(cls, engine: str, **kwargs: Any) -> OCRStrategy:
        """Crea una estrategia OCR según el motor solicitado.

        Args:
            engine: Identificador del motor OCR.
            **kwargs: Configuración específica de la estrategia.

        Returns:
            Una instancia de ``OCRStrategy``.

        Raises:
            OCRConfigurationError: Si el motor no está soportado o el nombre
                no es válido.
        """
        if not isinstance(engine, str) or not engine.strip():
            raise OCRConfigurationError(
                "Debe especificarse un motor OCR válido."
            )

        normalized_engine = engine.strip().lower()

        strategy_class = cls._STRATEGIES.get(normalized_engine)

        if strategy_class is None:
            supported = ", ".join(sorted(cls._STRATEGIES))
            raise OCRConfigurationError(
                f"Motor OCR no soportado: {engine!r}. "
                f"Disponibles: {supported}"
            )

        try:
            return strategy_class(**kwargs)
        except TypeError as exc:
            raise OCRConfigurationError(
                f"Configuración inválida para el motor OCR "
                f"'{normalized_engine}': {exc}"
            ) from exc

    @classmethod
    def supported_engines(cls) -> tuple[str, ...]:
        """Devuelve los motores OCR registrados en la fábrica."""
        return tuple(sorted(cls._STRATEGIES))


def create_ocr_strategy(
    engine: str,
    **kwargs: Any,
) -> OCRStrategy:
    """Función de conveniencia para crear una estrategia OCR."""
    return OCRFactory.create(engine, **kwargs)


__all__ = [
    "OCRFactory",
    "create_ocr_strategy",
]

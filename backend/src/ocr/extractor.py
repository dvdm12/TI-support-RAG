from __future__ import annotations

from pathlib import Path

from .models import OCRResult
from .strategy import OCRStrategy


class OCRExtractor:
    """Contexto del patrón Strategy para la extracción OCR.

    ``OCRExtractor`` delega la extracción concreta en una estrategia
    ``OCRStrategy``. El extractor no depende de ningún motor OCR específico.
    """

    def __init__(self, strategy: OCRStrategy) -> None:
        if not isinstance(strategy, OCRStrategy):
            raise TypeError(
                "strategy debe ser una instancia de OCRStrategy."
            )

        self._strategy = strategy

    @property
    def strategy(self) -> OCRStrategy:
        """Devuelve la estrategia OCR actualmente seleccionada."""
        return self._strategy

    def set_strategy(self, strategy: OCRStrategy) -> None:
        """Cambia la estrategia OCR en tiempo de ejecución.

        Args:
            strategy: Nueva implementación de ``OCRStrategy``.
        """
        if not isinstance(strategy, OCRStrategy):
            raise TypeError(
                "strategy debe ser una instancia de OCRStrategy."
            )

        self._strategy = strategy

    def extract(self, image_path: Path) -> OCRResult:
        """Extrae texto delegando la operación a la estrategia actual."""
        return self._strategy.extract(Path(image_path))

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .constants import SUPPORTED_IMAGE_EXTENSIONS
from .exceptions import OCRInputError
from .models import OCRResult


class OCRStrategy(ABC):
    """Contrato común para las estrategias de extracción OCR.

    La validación de entrada y la definición del contrato son comunes
    a todos los motores OCR; la implementación concreta de ``extract``
    pertenece a cada estrategia.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre lógico de la estrategia OCR."""
        raise NotImplementedError

    @staticmethod
    def validate_image(image_path: Path) -> None:
        """Valida una imagen antes de enviarla al motor OCR."""
        image_path = Path(image_path)

        if not image_path.exists():
            raise OCRInputError(
                f"La imagen no existe: {image_path}"
            )

        if not image_path.is_file():
            raise OCRInputError(
                f"La ruta no corresponde a un archivo: {image_path}"
            )

        if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            raise OCRInputError(
                "Formato de imagen no soportado: "
                f"{image_path.suffix or '<sin extensión>'}"
            )

    @abstractmethod
    def extract(self, image_path: Path) -> OCRResult:
        """Extrae y normaliza el texto de una imagen.

        Args:
            image_path: Ruta de la imagen que será procesada.

        Returns:
            Resultado OCR normalizado mediante ``OCRResult``.

        Raises:
            OCRInputError: Si la entrada no es válida.
            OCRException: Si ocurre un error propio del subsistema OCR.
        """
        raise NotImplementedError

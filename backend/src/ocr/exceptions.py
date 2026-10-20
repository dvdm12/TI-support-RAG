class OCRException(Exception):
    """Excepción base del subsistema OCR."""


class OCRConfigurationError(OCRException):
    """Error en la configuración del extractor OCR."""


class OCRDependencyError(OCRException):
    """Dependencia necesaria para el motor OCR no disponible."""


class OCRInputError(OCRException):
    """Entrada inválida para el procesamiento OCR."""


class OCRExtractionError(OCRException):
    """Error durante la extracción del texto mediante OCR."""
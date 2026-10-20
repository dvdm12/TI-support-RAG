from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from src.ocr import OCRFactory, OCRExtractor


SUPPORTED_FILE_TYPES = [
    (
        "Imágenes",
        "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff",
    ),
    ("Todos los archivos", "*.*"),
]


def select_image() -> Path | None:
    """Permite al usuario seleccionar una imagen desde la interfaz gráfica."""
    root = tk.Tk()
    root.withdraw()

    image_path = filedialog.askopenfilename(
        title="Selecciona una captura para analizar",
        filetypes=SUPPORTED_FILE_TYPES,
    )

    root.destroy()

    if not image_path:
        return None

    return Path(image_path)


def main() -> None:
    image = select_image()

    if image is None:
        print("No se seleccionó ninguna imagen.")
        return

    if not image.exists():
        messagebox.showerror(
            "Error",
            f"La imagen seleccionada no existe:\n{image}",
        )
        return

    print(f"Imagen seleccionada: {image}")
    print()

    for engine in OCRFactory.supported_engines():
        print(f"=== {engine} ===")

        try:
            strategy = OCRFactory.create(engine)
            extractor = OCRExtractor(strategy)
            result = extractor.extract(image)

        except Exception as exc:
            print("Estado: ERROR")
            print(f"Detalle: {exc}")
            print()
            continue

        print(f"Motor      : {result.engine}")
        print(f"Palabras   : {result.word_count}")
        print(f"Confianza  : {result.ocr_confidence:.2f}")
        print(f"Con texto  : {result.has_text}")
        print("Texto:")
        print(result.text)
        print()


if __name__ == "__main__":
    main()

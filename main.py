from tkinter import Tk, filedialog

from src.multimodal import prepare_multimodal_input


def select_image() -> str | None:
    root = Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Seleccionar imagen",
        filetypes=[
            ("Imágenes", "*.jpg *.jpeg *.png *.webp"),
        ],
    )

    root.destroy()

    return file_path or None


user_text = input("Ingrese la solicitud: ").strip()

attach = input(
    "¿Desea adjuntar una imagen? [s/N]: "
).strip().lower()

file_path = None

if attach == "s":
    file_path = select_image()

    if not file_path:
        print("No se seleccionó ninguna imagen.")
        raise SystemExit(0)

try:
    result = prepare_multimodal_input(
        user_text=user_text,
        file_path=file_path,
    )

    print("\n=== RESULTADO ===")

    print("\nTexto del usuario:")
    print(result["text"])

    if result["has_attachment"]:
        print("\nArchivo adjunto:")
        print(result["attachment"]["filename"])

        print("\nTexto extraído por OCR:")
        print(result["extracted_text"])

        print("\nConfianza OCR:")
        print(result["extraction"]["ocr_confidence"])

        print("\nExtracción válida:")
        print(result["extraction_valid"])

        print("\nErrores de extracción:")
        print(result["extraction_errors"])
    else:
        print("\nSin imagen adjunta.")

except (ValueError, RuntimeError) as error:
    print(f"\nERROR: {error}")
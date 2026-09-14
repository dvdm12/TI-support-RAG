import tempfile
import unittest
from pathlib import Path

from src.multimodal import (
    SUPPORTED_IMAGE_TYPES,
    prepare_multimodal_input,
    validate_attachment,
)


class TestValidateAttachment(unittest.TestCase):

    def test_archivo_png_valido(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "imagen.png"
            path.touch()

            valid, error = validate_attachment(path)

            self.assertTrue(valid)
            self.assertEqual(error, "")

    def test_archivo_jpg_valido(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "imagen.jpg"
            path.touch()

            valid, error = validate_attachment(path)

            self.assertTrue(valid)
            self.assertEqual(error, "")

    def test_archivo_jpeg_valido(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "imagen.jpeg"
            path.touch()

            valid, error = validate_attachment(path)

            self.assertTrue(valid)
            self.assertEqual(error, "")

    def test_archivo_webp_valido(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "imagen.webp"
            path.touch()

            valid, error = validate_attachment(path)

            self.assertTrue(valid)
            self.assertEqual(error, "")

    def test_extension_mayuscula_valida(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "imagen.PNG"
            path.touch()

            valid, error = validate_attachment(path)

            self.assertTrue(valid)
            self.assertEqual(error, "")

    def test_todas_las_extensiones_soportadas(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for extension in SUPPORTED_IMAGE_TYPES:
                path = Path(temp_dir) / f"imagen{extension}"
                path.touch()

                valid, error = validate_attachment(path)

                self.assertTrue(valid)
                self.assertEqual(error, "")

    def test_archivo_inexistente(self):
        path = Path("/tmp/archivo_que_no_existe_123456.png")

        valid, error = validate_attachment(path)

        self.assertFalse(valid)
        self.assertIn("Archivo no encontrado", error)

    def test_ruta_de_directorio(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            valid, error = validate_attachment(Path(temp_dir))

            self.assertFalse(valid)
            self.assertIn(
                "La ruta no corresponde a un archivo",
                error,
            )

    def test_extension_no_soportada_txt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "archivo.txt"
            path.touch()

            valid, error = validate_attachment(path)

            self.assertFalse(valid)
            self.assertIn("Tipo de archivo no soportado", error)

    def test_extension_no_soportada_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "archivo.pdf"
            path.touch()

            valid, error = validate_attachment(path)

            self.assertFalse(valid)
            self.assertIn("Tipo de archivo no soportado", error)


class TestPrepareMultimodalInput(unittest.TestCase):

    def test_entrada_solo_textual(self):
        result = prepare_multimodal_input(
            "Mi computador no enciende."
        )

        expected = {
            "text": "Mi computador no enciende.",
            "has_attachment": False,
            "attachment": None,
        }

        self.assertEqual(result, expected)

    def test_texto_con_espacios(self):
        result = prepare_multimodal_input(
            "   Mi computador no enciende.   "
        )

        self.assertEqual(
            result["text"],
            "Mi computador no enciende.",
        )

    def test_entrada_con_png(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "error.png"
            path.touch()

            result = prepare_multimodal_input(
                "Aparece este error.",
                path,
            )

            self.assertEqual(
                result["text"],
                "Aparece este error.",
            )
            self.assertTrue(result["has_attachment"])
            self.assertIsNotNone(result["attachment"])

            self.assertEqual(
                result["attachment"]["path"],
                str(path),
            )
            self.assertEqual(
                result["attachment"]["filename"],
                "error.png",
            )
            self.assertEqual(
                result["attachment"]["extension"],
                ".png",
            )

    def test_entrada_con_jpg(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "foto.jpg"
            path.touch()

            result = prepare_multimodal_input(
                "Adjunto evidencia.",
                path,
            )

            self.assertTrue(result["has_attachment"])
            self.assertEqual(
                result["attachment"]["filename"],
                "foto.jpg",
            )

    def test_ruta_como_string(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "captura.webp"
            path.touch()

            result = prepare_multimodal_input(
                "Captura del problema.",
                str(path),
            )

            self.assertTrue(result["has_attachment"])
            self.assertEqual(
                result["attachment"]["extension"],
                ".webp",
            )

    def test_archivo_inexistente_lanza_error(self):
        path = Path("/tmp/no_existe_multimodal_987654.png")

        with self.assertRaises(ValueError) as context:
            prepare_multimodal_input(
                "Problema.",
                path,
            )

        self.assertIn(
            "Archivo no encontrado",
            str(context.exception),
        )

    def test_archivo_no_soportado_lanza_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "documento.txt"
            path.touch()

            with self.assertRaises(ValueError) as context:
                prepare_multimodal_input(
                    "Tengo un documento.",
                    path,
                )

            self.assertIn(
                "Tipo de archivo no soportado",
                str(context.exception),
            )

    def test_directorio_lanza_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError) as context:
                prepare_multimodal_input(
                    "Problema.",
                    temp_dir,
                )

            self.assertIn(
                "La ruta no corresponde a un archivo",
                str(context.exception),
            )


class TestContratoMultimodal(unittest.TestCase):

    def test_claves_exactas_sin_adjunto(self):
        result = prepare_multimodal_input(
            "No tengo acceso al sistema."
        )

        self.assertEqual(
            set(result.keys()),
            {
                "text",
                "has_attachment",
                "attachment",
            },
        )

    def test_claves_exactas_con_adjunto(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "captura.png"
            path.touch()

            result = prepare_multimodal_input(
                "Error de conexión.",
                path,
            )

            self.assertEqual(
                set(result.keys()),
                {
                    "text",
                    "has_attachment",
                    "attachment",
                },
            )

    def test_adjunto_tiene_claves_exactas(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "captura.png"
            path.touch()

            result = prepare_multimodal_input(
                "Error.",
                path,
            )

            self.assertEqual(
                set(result["attachment"].keys()),
                {
                    "path",
                    "filename",
                    "extension",
                },
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
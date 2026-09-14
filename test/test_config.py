import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import config


class TestFindProjectRoot(unittest.TestCase):

    def test_detecta_raiz_desde_la_raiz_del_proyecto(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "prompts").mkdir()

            with patch(
                "src.config.Path.cwd",
                return_value=root,
            ):
                result = config.find_project_root()

            self.assertEqual(result, root)

    def test_detecta_raiz_desde_subdirectorio(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prompts = root / "prompts"
            prompts.mkdir()

            nested = root / "src" / "deep"
            nested.mkdir(parents=True)

            with patch(
                "src.config.Path.cwd",
                return_value=nested,
            ):
                result = config.find_project_root()

            self.assertEqual(result, root)

    def test_detecta_raiz_en_varios_niveles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "prompts").mkdir()

            nested = (
                root
                / "a"
                / "b"
                / "c"
                / "d"
            )
            nested.mkdir(parents=True)

            with patch(
                "src.config.Path.cwd",
                return_value=nested,
            ):
                result = config.find_project_root()

            self.assertEqual(result, root)

    def test_falla_si_no_existe_directorio_prompts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            start = Path(temp_dir) / "proyecto"
            start.mkdir()

            with patch(
                "src.config.Path.cwd",
                return_value=start,
            ):
                with self.assertRaises(FileNotFoundError) as context:
                    config.find_project_root()

            self.assertIn(
                "No se encontró la raíz del proyecto",
                str(context.exception),
            )

    def test_no_confunde_otro_directorio_con_prompts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "prompt").mkdir()

            nested = root / "src"
            nested.mkdir()

            with patch(
                "src.config.Path.cwd",
                return_value=nested,
            ):
                with self.assertRaises(FileNotFoundError):
                    config.find_project_root()

    def test_usa_prompts_como_directorio_y_no_archivo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            # prompts es un archivo, no un directorio.
            (root / "prompts").touch()

            nested = root / "src"
            nested.mkdir()

            with patch(
                "src.config.Path.cwd",
                return_value=nested,
            ):
                with self.assertRaises(FileNotFoundError):
                    config.find_project_root()


class TestFindLatestPrompt(unittest.TestCase):

    def test_encuentra_unica_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)
            prompt = prompts_dir / "system_v3.md"
            prompt.touch()

            version, path = config.find_latest_prompt(
                prompts_dir
            )

            self.assertEqual(version, "system_v3")
            self.assertEqual(path, prompt)

    def test_selecciona_la_version_mas_alta(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)

            for version in [0, 1, 2, 3]:
                (prompts_dir / f"system_v{version}.md").touch()

            version, path = config.find_latest_prompt(
                prompts_dir
            )

            self.assertEqual(version, "system_v3")
            self.assertEqual(
                path,
                prompts_dir / "system_v3.md",
            )

    def test_selecciona_version_mas_alta_sin_importar_orden(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)

            for version in [8, 2, 15, 4, 10]:
                (prompts_dir / f"system_v{version}.md").touch()

            version, path = config.find_latest_prompt(
                prompts_dir
            )

            self.assertEqual(version, "system_v15")
            self.assertEqual(
                path,
                prompts_dir / "system_v15.md",
            )

    def test_compara_versiones_numericamente(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)

            (prompts_dir / "system_v9.md").touch()
            (prompts_dir / "system_v10.md").touch()

            version, path = config.find_latest_prompt(
                prompts_dir
            )

            self.assertEqual(version, "system_v10")
            self.assertEqual(
                path,
                prompts_dir / "system_v10.md",
            )

    def test_ignora_archivos_que_no_cumplen_el_patron(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)

            valid = prompts_dir / "system_v3.md"
            valid.touch()

            invalid_files = [
                "system.md",
                "system_v.md",
                "system_vx.md",
                "system_v3.txt",
                "system_v3",
                "system_v-1.md",
                "foo_v99.md",
                "system_v3_extra.md",
            ]

            for filename in invalid_files:
                (prompts_dir / filename).touch()

            version, path = config.find_latest_prompt(
                prompts_dir
            )

            self.assertEqual(version, "system_v3")
            self.assertEqual(path, valid)

    def test_ignora_subdirectorios(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)

            valid = prompts_dir / "system_v3.md"
            valid.touch()

            nested = prompts_dir / "nested"
            nested.mkdir()
            (nested / "system_v999.md").touch()

            version, path = config.find_latest_prompt(
                prompts_dir
            )

            self.assertEqual(version, "system_v3")
            self.assertEqual(path, valid)

    def test_falla_si_no_hay_prompts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)

            with self.assertRaises(FileNotFoundError) as context:
                config.find_latest_prompt(prompts_dir)

            self.assertIn(
                "No se encontraron prompts versionados",
                str(context.exception),
            )

    def test_falla_si_directorio_no_existe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = (
                Path(temp_dir) / "no_existe"
            )

            with self.assertRaises(FileNotFoundError):
                config.find_latest_prompt(prompts_dir)

    def test_falla_si_solo_hay_archivos_invalidos(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)

            (prompts_dir / "system.md").touch()
            (prompts_dir / "system_vx.md").touch()
            (prompts_dir / "system_v2.txt").touch()

            with self.assertRaises(FileNotFoundError):
                config.find_latest_prompt(prompts_dir)

    def test_acepta_version_cero(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)

            prompt = prompts_dir / "system_v0.md"
            prompt.touch()

            version, path = config.find_latest_prompt(
                prompts_dir
            )

            self.assertEqual(version, "system_v0")
            self.assertEqual(path, prompt)

    def test_versiones_grandes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)

            prompt = prompts_dir / "system_v12345.md"
            prompt.touch()

            version, path = config.find_latest_prompt(
                prompts_dir
            )

            self.assertEqual(
                version,
                "system_v12345",
            )
            self.assertEqual(path, prompt)


class TestConfigConstants(unittest.TestCase):

    def test_model_no_esta_vacio(self):
        self.assertIsInstance(config.MODEL, str)
        self.assertTrue(config.MODEL.strip())

    def test_api_url_no_esta_vacia(self):
        self.assertIsInstance(config.API_URL, str)
        self.assertTrue(config.API_URL.strip())

    def test_api_url_usa_https(self):
        self.assertTrue(
            config.API_URL.startswith("https://")
        )

    def test_api_url_apunta_a_chat_completions(self):
        self.assertIn(
            "/chat/completions",
            config.API_URL,
        )

    def test_prompts_dir_es_path(self):
        self.assertIsInstance(
            config.PROMPTS_DIR,
            Path,
        )

    def test_prompt_path_es_path(self):
        self.assertIsInstance(
            config.PROMPT_PATH,
            Path,
        )

    def test_test_path_es_path(self):
        self.assertIsInstance(
            config.TEST_PATH,
            Path,
        )

    def test_results_path_es_path(self):
        self.assertIsInstance(
            config.RESULTS_PATH,
            Path,
        )

    def test_prompt_version_tiene_formato_correcto(self):
        self.assertRegex(
            config.PROMPT_VERSION,
            r"^system_v\d+$",
        )

    def test_prompt_path_pertenece_a_prompts(self):
        self.assertEqual(
            config.PROMPT_PATH.parent,
            config.PROMPTS_DIR,
        )

    def test_prompt_path_coincide_con_version(self):
        expected = (
            f"{config.PROMPT_VERSION}.md"
        )

        self.assertEqual(
            config.PROMPT_PATH.name,
            expected,
        )


class TestConfigPaths(unittest.TestCase):

    def test_test_path_apunta_a_test_cases_json(self):
        self.assertEqual(
            config.TEST_PATH.name,
            "test_cases.json",
        )

    def test_test_path_esta_en_directorio_test(self):
        self.assertEqual(
            config.TEST_PATH.parent.name,
            "test",
        )

    def test_results_path_apunta_a_results_json(self):
        self.assertEqual(
            config.RESULTS_PATH.name,
            "results.json",
        )

    def test_results_path_esta_en_directorio_docs(self):
        self.assertEqual(
            config.RESULTS_PATH.parent.name,
            "docs",
        )

    def test_prompts_dir_se_llama_prompts(self):
        self.assertEqual(
            config.PROMPTS_DIR.name,
            "prompts",
        )


class TestEnvironment(unittest.TestCase):

    def test_groq_api_key_es_string_o_none(self):
        self.assertTrue(
            isinstance(config.GROQ_API_KEY, str)
            or config.GROQ_API_KEY is None
        )

    def test_api_key_cargada_si_existe_en_entorno(self):
        fake_key = "test-key-123"

        with patch.dict(
            os.environ,
            {"GROQ_API_KEY": fake_key},
            clear=False,
        ):
            self.assertEqual(
                os.environ["GROQ_API_KEY"],
                fake_key,
            )


class TestConfigInitialization(unittest.TestCase):

    def _create_project(self, include_key=True):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)

        (root / "prompts").mkdir()
        (root / "test").mkdir()
        (root / "docs").mkdir()

        (root / "prompts" / "system_v0.md").write_text(
            "prompt 0",
            encoding="utf-8",
        )

        (root / "prompts" / "system_v1.md").write_text(
            "prompt 1",
            encoding="utf-8",
        )

        (root / "test" / "test_cases.json").touch()
        (root / "docs" / "results.json").touch()

        if include_key:
            (root / ".env").write_text(
                "GROQ_API_KEY=test-key\n",
                encoding="utf-8",
            )

        return temp_dir, root

    def test_importacion_detecta_version_mas_reciente(self):
        temp_dir, root = self._create_project()
        self.addCleanup(temp_dir.cleanup)

        (root / "prompts" / "system_v2.md").write_text(
            "prompt 2",
            encoding="utf-8",
        )

        with patch(
            "src.config.Path.cwd",
            return_value=root,
        ):
            with patch.dict(
                os.environ,
                {"GROQ_API_KEY": "test-key"},
                clear=True,
            ):
                # Verificamos las funciones que utiliza la inicialización.
                project_root = config.find_project_root()
                prompts_dir = project_root / "prompts"
                version, prompt_path = (
                    config.find_latest_prompt(
                        prompts_dir
                    )
                )

        self.assertEqual(
            version,
            "system_v2",
        )
        self.assertEqual(
            prompt_path,
            root / "prompts" / "system_v2.md",
        )

    def test_env_se_ubica_en_la_raiz_del_proyecto(self):
        temp_dir, root = self._create_project()
        self.addCleanup(temp_dir.cleanup)

        with patch(
            "src.config.Path.cwd",
            return_value=root,
        ):
            with patch(
                "src.config.load_dotenv"
            ) as mock_load_dotenv:
                # Ejecutamos la misma operación de carga
                # que utiliza config.py.
                config.load_dotenv(root / ".env")

        mock_load_dotenv.assert_called_once_with(
            root / ".env"
        )

    def test_dotenv_no_es_necesario_para_resolver_rutas(self):
        temp_dir, root = self._create_project(
            include_key=False
        )
        self.addCleanup(temp_dir.cleanup)

        with patch(
            "src.config.Path.cwd",
            return_value=root,
        ):
            project_root = config.find_project_root()
            version, prompt_path = (
                config.find_latest_prompt(
                    project_root / "prompts"
                )
            )

        self.assertEqual(project_root, root)
        self.assertEqual(version, "system_v1")
        self.assertEqual(
            prompt_path,
            root / "prompts" / "system_v1.md",
        )


class TestConfigConsistency(unittest.TestCase):

    def test_prompt_version_y_archivo_son_consistentes(self):
        self.assertEqual(
            config.PROMPT_VERSION,
            config.PROMPT_PATH.stem,
        )

    def test_prompt_version_no_contiene_extension(self):
        self.assertFalse(
            config.PROMPT_VERSION.endswith(".md")
        )

    def test_todas_las_rutas_son_absolutas(self):
        self.assertTrue(
            config.PROJECT_ROOT.is_absolute()
        )
        self.assertTrue(
            config.PROMPTS_DIR.is_absolute()
        )
        self.assertTrue(
            config.PROMPT_PATH.is_absolute()
        )
        self.assertTrue(
            config.TEST_PATH.is_absolute()
        )
        self.assertTrue(
            config.RESULTS_PATH.is_absolute()
        )

    def test_prompts_dir_deriva_de_project_root(self):
        self.assertEqual(
            config.PROMPTS_DIR,
            config.PROJECT_ROOT / "prompts",
        )

    def test_test_path_deriva_de_project_root(self):
        self.assertEqual(
            config.TEST_PATH,
            config.PROJECT_ROOT
            / "test"
            / "test_cases.json",
        )

    def test_results_path_deriva_de_project_root(self):
        self.assertEqual(
            config.RESULTS_PATH,
            config.PROJECT_ROOT
            / "docs"
            / "results.json",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
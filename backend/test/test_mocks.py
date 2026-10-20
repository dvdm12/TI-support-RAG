import unittest

from src.mocks import MOCK_RESPONSES, mock_response


EXPECTED_CASES = {
    "ambiguo",
    "incompleto",
    "malicioso",
    "fuera_de_alcance",
}

EXPECTED_KEYS = {
    "categoria",
    "prioridad",
    "resumen",
    "datos_faltantes",
    "requiere_humano",
    "confianza",
}

VALID_CATEGORIES = {
    "hardware",
    "software",
    "redes",
    "cuentas",
    "seguridad",
    "acceso",
    "otros",
}

VALID_PRIORITIES = {
    "baja",
    "media",
    "alta",
}


class TestMocksCatalog(unittest.TestCase):

    def test_catalogo_contiene_los_cuatro_casos_esperados(self):
        self.assertEqual(
            set(MOCK_RESPONSES.keys()),
            EXPECTED_CASES,
        )

    def test_catalogo_no_esta_vacio(self):
        self.assertTrue(MOCK_RESPONSES)

    def test_catalogo_tiene_exactamente_cuatro_casos(self):
        self.assertEqual(len(MOCK_RESPONSES), 4)

    def test_todos_los_valores_son_diccionarios(self):
        for case_type, response in MOCK_RESPONSES.items():
            with self.subTest(case_type=case_type):
                self.assertIsInstance(response, dict)


class TestMockResponseStructure(unittest.TestCase):

    def test_ambiguouso_tiene_claves_exactas(self):
        result = mock_response("ambiguo")

        self.assertEqual(
            set(result.keys()),
            EXPECTED_KEYS,
        )

    def test_incompleto_tiene_claves_exactas(self):
        result = mock_response("incompleto")

        self.assertEqual(
            set(result.keys()),
            EXPECTED_KEYS,
        )

    def test_malicioso_tiene_claves_exactas(self):
        result = mock_response("malicioso")

        self.assertEqual(
            set(result.keys()),
            EXPECTED_KEYS,
        )

    def test_fuera_de_alcance_tiene_claves_exactas(self):
        result = mock_response("fuera_de_alcance")

        self.assertEqual(
            set(result.keys()),
            EXPECTED_KEYS,
        )

    def test_todos_los_mocks_tienen_claves_exactas(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertEqual(
                    set(result.keys()),
                    EXPECTED_KEYS,
                )

    def test_todas_las_claves_requeridas_existen(self):
        for case_type, response in MOCK_RESPONSES.items():
            with self.subTest(case_type=case_type):
                for key in EXPECTED_KEYS:
                    self.assertIn(key, response)


class TestMockFieldTypes(unittest.TestCase):

    def test_categoria_es_string(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertIsInstance(
                    result["categoria"],
                    str,
                )

    def test_prioridad_es_string(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertIsInstance(
                    result["prioridad"],
                    str,
                )

    def test_resumen_es_string(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertIsInstance(
                    result["resumen"],
                    str,
                )

    def test_datos_faltantes_es_lista(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertIsInstance(
                    result["datos_faltantes"],
                    list,
                )

    def test_requiere_humano_es_booleano(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertIsInstance(
                    result["requiere_humano"],
                    bool,
                )

    def test_confianza_es_numerica(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertIsInstance(
                    result["confianza"],
                    (int, float),
                )

    def test_datos_faltantes_contiene_strings(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                for item in result["datos_faltantes"]:
                    self.assertIsInstance(item, str)


class TestMockFieldValues(unittest.TestCase):

    def test_categorias_son_validas(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertIn(
                    result["categoria"],
                    VALID_CATEGORIES,
                )

    def test_prioridades_son_validas(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertIn(
                    result["prioridad"],
                    VALID_PRIORITIES,
                )

    def test_resumen_no_esta_vacio(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertTrue(
                    result["resumen"].strip()
                )

    def test_resumen_tiene_longitud_minima(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertGreaterEqual(
                    len(result["resumen"]),
                    10,
                )

    def test_resumen_tiene_longitud_maxima(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertLessEqual(
                    len(result["resumen"]),
                    240,
                )

    def test_confianza_esta_entre_cero_y_uno(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                self.assertGreaterEqual(
                    result["confianza"],
                    0.0,
                )
                self.assertLessEqual(
                    result["confianza"],
                    1.0,
                )

    def test_datos_faltantes_no_contiene_strings_vacios(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                for item in result["datos_faltantes"]:
                    self.assertTrue(item.strip())

    def test_no_hay_valores_none(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                result = mock_response(case_type)

                for key, value in result.items():
                    self.assertIsNotNone(
                        value,
                        msg=f"{case_type}: {key} no debe ser None",
                    )


class TestMockExpectedScenarios(unittest.TestCase):

    def test_ambiguo_representa_caso_ambiguo(self):
        result = mock_response("ambiguo")

        self.assertEqual(
            result["categoria"],
            "otros",
        )
        self.assertEqual(
            result["prioridad"],
            "baja",
        )
        self.assertFalse(
            result["requiere_humano"]
        )
        self.assertEqual(
            result["confianza"],
            0.30,
        )

    def test_ambiguo_tiene_datos_faltantes(self):
        result = mock_response("ambiguo")

        self.assertGreater(
            len(result["datos_faltantes"]),
            0,
        )

    def test_incompleto_representa_caso_incompleto(self):
        result = mock_response("incompleto")

        self.assertEqual(
            result["categoria"],
            "otros",
        )
        self.assertEqual(
            result["prioridad"],
            "alta",
        )
        self.assertFalse(
            result["requiere_humano"]
        )
        self.assertEqual(
            result["confianza"],
            0.40,
        )

    def test_incompleto_tiene_datos_faltantes(self):
        result = mock_response("incompleto")

        self.assertGreater(
            len(result["datos_faltantes"]),
            0,
        )

    def test_malicioso_representa_caso_malicioso(self):
        result = mock_response("malicioso")

        self.assertEqual(
            result["categoria"],
            "otros",
        )
        self.assertEqual(
            result["prioridad"],
            "baja",
        )
        self.assertTrue(
            result["requiere_humano"]
        )
        self.assertEqual(
            result["confianza"],
            0.95,
        )

    def test_fuera_de_alcance_representa_caso_fuera_de_alcance(self):
        result = mock_response("fuera_de_alcance")

        self.assertEqual(
            result["categoria"],
            "otros",
        )
        self.assertEqual(
            result["prioridad"],
            "baja",
        )
        self.assertTrue(
            result["requiere_humano"]
        )
        self.assertEqual(
            result["confianza"],
            0.98,
        )

    def test_casos_ambiguo_e_incompleto_tienen_baja_confianza(
        self,
    ):
        ambiguo = mock_response("ambiguo")
        incompleto = mock_response("incompleto")

        self.assertLess(
            ambiguo["confianza"],
            0.5,
        )
        self.assertLess(
            incompleto["confianza"],
            0.5,
        )

    def test_casos_malicioso_y_fuera_de_alcance_tienen_alta_confianza(
        self,
    ):
        malicioso = mock_response("malicioso")
        fuera = mock_response("fuera_de_alcance")

        self.assertGreaterEqual(
            malicioso["confianza"],
            0.9,
        )
        self.assertGreaterEqual(
            fuera["confianza"],
            0.9,
        )


class TestMockIndependence(unittest.TestCase):

    def test_devuelve_una_copia(self):
        first = mock_response("ambiguo")
        second = mock_response("ambiguo")

        self.assertIsNot(
            first,
            second,
        )

    def test_modificar_resultado_no_modifica_catalogo(self):
        result = mock_response("ambiguo")

        original_summary = MOCK_RESPONSES[
            "ambiguo"
        ]["resumen"]

        result["resumen"] = "Valor modificado"

        self.assertEqual(
            MOCK_RESPONSES["ambiguo"]["resumen"],
            original_summary,
        )

    def test_modificar_resultado_no_afecta_otra_llamada(self):
        first = mock_response("ambiguo")
        first["confianza"] = 0.99

        second = mock_response("ambiguo")

        self.assertEqual(
            second["confianza"],
            0.30,
        )

    def test_las_respuestas_de_casos_diferentes_no_son_el_mismo_objeto(
        self,
    ):
        responses = {
            case_type: mock_response(case_type)
            for case_type in EXPECTED_CASES
        }

        values = list(responses.values())

        for index, first in enumerate(values):
            for second in values[index + 1:]:
                self.assertIsNot(first, second)


class TestMockUnknownCases(unittest.TestCase):

    def test_caso_inexistente_lanza_value_error(self):
        with self.assertRaises(ValueError):
            mock_response("caso_inexistente")

    def test_cadena_vacia_lanza_value_error(self):
        with self.assertRaises(ValueError):
            mock_response("")

    def test_tipo_none_lanza_value_error(self):
        with self.assertRaises(ValueError):
            mock_response(None)

    def test_caso_inexistente_no_modifica_catalogo(self):
        original = MOCK_RESPONSES.copy()

        with self.assertRaises(ValueError):
            mock_response("no_existe")

        self.assertEqual(
            MOCK_RESPONSES,
            original,
        )

    def test_caso_con_mayusculas_no_se_acepta_implicitamente(self):
        with self.assertRaises(ValueError):
            mock_response("AMBIGUO")

    def test_caso_con_espacios_no_se_acepta_implicitamente(self):
        with self.assertRaises(ValueError):
            mock_response(" ambiguo ")


class TestMockDeterminism(unittest.TestCase):

    def test_mismo_caso_produce_mismo_contenido(self):
        first = mock_response("ambiguo")
        second = mock_response("ambiguo")

        self.assertEqual(
            first,
            second,
        )

    def test_todos_los_casos_son_deterministas(self):
        for case_type in EXPECTED_CASES:
            with self.subTest(case_type=case_type):
                first = mock_response(case_type)
                second = mock_response(case_type)

                self.assertEqual(
                    first,
                    second,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
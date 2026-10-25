import json
import unittest

from schemas.request_v1 import SolicitudTI
from src.validator import validate_output


def valid(**changes):
    data = {'categoria': 'redes', 'prioridad': 'media', 'resumen': 'Sin conexión Wi-Fi en la sala 3',
            'datos_faltantes': ['identificador del equipo'], 'requiere_humano': False, 'confianza': 0.8}
    data.update(changes)
    return data


class ValidOutputTests(unittest.TestCase):
    def test_valid_output_returns_model_and_no_errors(self):
        ok, errors, model = validate_output(valid())
        self.assertTrue(ok)
        self.assertEqual(errors, [])
        self.assertIsInstance(model, SolicitudTI)
        self.assertEqual(model.model_dump(), valid())

    def test_every_category_and_priority_is_accepted(self):
        for categoria in ('hardware', 'software', 'redes', 'cuentas', 'seguridad', 'acceso', 'otros'):
            for prioridad in ('baja', 'media', 'alta'):
                with self.subTest(categoria=categoria, prioridad=prioridad):
                    self.assertTrue(validate_output(valid(categoria=categoria, prioridad=prioridad))[0])

    def test_strings_are_stripped_before_validation_and_returned_normalized(self):
        ok, _, model = validate_output(valid(resumen='   ' + 'x' * 10 + '   ', datos_faltantes=['  serie  ']))
        self.assertTrue(ok)
        self.assertEqual((model.resumen, model.datos_faltantes), ('x' * 10, ['serie']))

    def test_empty_missing_data_list_is_valid(self):
        self.assertTrue(validate_output(valid(datos_faltantes=[]))[0])

    def test_summary_length_bounds_are_inclusive(self):
        for resumen in ('x' * 10, 'x' * 240):
            with self.subTest(length=len(resumen)):
                self.assertTrue(validate_output(valid(resumen=resumen))[0])

    def test_confidence_bounds_and_integer_numbers_are_accepted(self):
        for confianza in (0, 1, 0.0, 1.0, 0.5):
            with self.subTest(confianza=confianza):
                ok, _, model = validate_output(valid(confianza=confianza))
                self.assertTrue(ok)
                self.assertIsInstance(model.confianza, float)

    def test_confidence_from_parsed_json_number(self):
        self.assertTrue(validate_output(json.loads(json.dumps(valid(confianza=0.95))))[0])

    def test_input_dictionary_is_not_mutated(self):
        data = valid(resumen='  Sin conexión Wi-Fi  ')
        snapshot = json.dumps(data, sort_keys=True)
        validate_output(data)
        self.assertEqual(json.dumps(data, sort_keys=True), snapshot)


class InvalidOutputTests(unittest.TestCase):
    def assert_rejected(self, data, expected):
        ok, errors, model = validate_output(data)
        self.assertFalse(ok)
        self.assertIsNone(model)
        self.assertEqual(errors, expected)

    def test_non_object_input_reports_message_without_empty_location(self):
        for data in (None, [valid()], '{"categoria": "redes"}', 3, True):
            with self.subTest(data=data):
                ok, errors, model = validate_output(data)
                self.assertEqual((ok, model), (False, None))
                self.assertEqual(len(errors), 1)
                self.assertFalse(errors[0].startswith(':'))
                self.assertIn('valid dictionary', errors[0])

    def test_all_missing_fields_are_reported_in_schema_order(self):
        ok, errors, _ = validate_output({})
        self.assertFalse(ok)
        self.assertEqual(errors, [f'{field}: Field required' for field in
                                  ('categoria', 'prioridad', 'resumen', 'datos_faltantes', 'requiere_humano', 'confianza')])

    def test_extra_fields_are_forbidden(self):
        self.assert_rejected(valid(estado='OK'), ['estado: Extra inputs are not permitted'])

    def test_unknown_or_differently_cased_category_is_rejected(self):
        for categoria in ('Redes', 'impresoras', '', None):
            with self.subTest(categoria=categoria):
                ok, errors, _ = validate_output(valid(categoria=categoria))
                self.assertFalse(ok)
                self.assertTrue(errors[0].startswith('categoria: '))

    def test_unknown_priority_is_rejected(self):
        for prioridad in ('urgente', 'Alta', 1):
            with self.subTest(prioridad=prioridad):
                ok, errors, _ = validate_output(valid(prioridad=prioridad))
                self.assertFalse(ok)
                self.assertTrue(errors[0].startswith('prioridad: '))

    def test_summary_length_limits(self):
        self.assert_rejected(valid(resumen='x' * 9), ['resumen: String should have at least 10 characters'])
        self.assert_rejected(valid(resumen='x' * 241), ['resumen: String should have at most 240 characters'])

    def test_summary_of_spaces_is_too_short_after_stripping(self):
        self.assert_rejected(valid(resumen='   corto    '), ['resumen: String should have at least 10 characters'])

    def test_summary_must_be_a_string(self):
        self.assert_rejected(valid(resumen=1234567890), ['resumen: Input should be a valid string'])

    def test_missing_data_must_be_a_list(self):
        for datos in ('serie', None, {'serie': True}):
            with self.subTest(datos=datos):
                ok, errors, _ = validate_output(valid(datos_faltantes=datos))
                self.assertFalse(ok)
                self.assertTrue(errors[0].startswith('datos_faltantes: '))

    def test_missing_data_items_must_be_strings_and_report_their_index(self):
        self.assert_rejected(valid(datos_faltantes=['serie', 3]), ['datos_faltantes.1: Input should be a valid string'])

    def test_blank_missing_data_items_are_rejected(self):
        for item in ('', ' ', '\t\n'):
            with self.subTest(item=repr(item)):
                self.assert_rejected(valid(datos_faltantes=['serie', item]),
                                     ['datos_faltantes.1: String should have at least 1 character'])

    def test_every_invalid_missing_data_item_is_reported(self):
        ok, errors, _ = validate_output(valid(datos_faltantes=['', 'serie', 7]))
        self.assertFalse(ok)
        self.assertEqual([e.split(':')[0] for e in errors], ['datos_faltantes.0', 'datos_faltantes.2'])

    def test_human_flag_is_strict_boolean(self):
        for flag in ('false', 'true', 0, 1, None):
            with self.subTest(flag=flag):
                self.assert_rejected(valid(requiere_humano=flag), ['requiere_humano: Input should be a valid boolean'])

    def test_confidence_rejects_strings_booleans_and_none(self):
        for confianza in ('0.9', '1', True, False, None, [0.5]):
            with self.subTest(confianza=confianza):
                self.assert_rejected(valid(confianza=confianza), ['confianza: Input should be a valid number'])

    def test_confidence_rejects_nan_and_infinity_as_non_finite(self):
        for confianza in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(confianza=confianza):
                self.assert_rejected(valid(confianza=confianza), ['confianza: Input should be a finite number'])

    def test_confidence_outside_range_is_rejected(self):
        self.assert_rejected(valid(confianza=-0.0001), ['confianza: Input should be greater than or equal to 0'])
        self.assert_rejected(valid(confianza=1.0001), ['confianza: Input should be less than or equal to 1'])
        self.assert_rejected(valid(confianza=2), ['confianza: Input should be less than or equal to 1'])

    def test_multiple_field_errors_are_all_returned(self):
        ok, errors, _ = validate_output(valid(categoria='x', confianza='alta', extra=1))
        self.assertFalse(ok)
        self.assertEqual([e.split(':')[0] for e in errors], ['categoria', 'confianza', 'extra'])


if __name__ == '__main__':
    unittest.main()

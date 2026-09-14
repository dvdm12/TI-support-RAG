import unittest
from unittest.mock import Mock, patch

import requests

from src import groq_client


class TestBuildHeaders(unittest.TestCase):

    def test_headers_contienen_autorizacion(self):
        headers = groq_client.build_headers()

        self.assertIn("Authorization", headers)
        self.assertEqual(
            headers["Authorization"],
            f"Bearer {groq_client.GROQ_API_KEY}",
        )

    def test_headers_contienen_content_type(self):
        headers = groq_client.build_headers()

        self.assertEqual(
            headers["Content-Type"],
            "application/json",
        )

    def test_headers_contienen_accept(self):
        headers = groq_client.build_headers()

        self.assertEqual(
            headers["Accept"],
            "application/json",
        )

    def test_headers_contienen_groq_beta(self):
        headers = groq_client.build_headers()

        self.assertEqual(
            headers["Groq-Beta"],
            "inference-metrics",
        )

    def test_no_hay_headers_extra(self):
        headers = groq_client.build_headers()

        self.assertEqual(
            set(headers.keys()),
            {
                "Authorization",
                "Content-Type",
                "Accept",
                "Groq-Beta",
            },
        )


class TestBuildPayload(unittest.TestCase):

    def test_payload_contiene_modelo(self):
        payload = groq_client.build_payload(
            "Prompt del sistema",
            "Problema del usuario",
        )

        self.assertEqual(
            payload["model"],
            groq_client.MODEL,
        )

    def test_payload_temperature_cero(self):
        payload = groq_client.build_payload(
            "Prompt",
            "Texto",
        )

        self.assertEqual(payload["temperature"], 0)

    def test_payload_max_completion_tokens(self):
        payload = groq_client.build_payload(
            "Prompt",
            "Texto",
        )

        self.assertEqual(
            payload["max_completion_tokens"],
            1500,
        )

    def test_payload_tiene_messages(self):
        payload = groq_client.build_payload(
            "Prompt",
            "Texto",
        )

        self.assertIn("messages", payload)
        self.assertEqual(len(payload["messages"]), 2)

    def test_message_system(self):
        payload = groq_client.build_payload(
            "Prompt del sistema",
            "Texto",
        )

        self.assertEqual(
            payload["messages"][0],
            {
                "role": "system",
                "content": "Prompt del sistema",
            },
        )

    def test_message_usuario(self):
        payload = groq_client.build_payload(
            "Prompt",
            "No puedo conectarme",
        )

        self.assertEqual(
            payload["messages"][1]["role"],
            "user",
        )

        self.assertEqual(
            payload["messages"][1]["content"],
            "<texto_usuario>\n"
            "No puedo conectarme\n"
            "</texto_usuario>",
        )

    def test_payload_contiene_response_format(self):
        payload = groq_client.build_payload(
            "Prompt",
            "Texto",
        )

        self.assertIs(
            payload["response_format"],
            groq_client.RESPONSE_SCHEMA,
        )

    def test_texto_usuario_vacio(self):
        payload = groq_client.build_payload(
            "Prompt",
            "",
        )

        self.assertEqual(
            payload["messages"][1]["content"],
            "<texto_usuario>\n"
            "\n"
            "</texto_usuario>",
        )

    def test_texto_usuario_con_salto_de_linea(self):
        texto = "Línea 1\nLínea 2"

        payload = groq_client.build_payload(
            "Prompt",
            texto,
        )

        self.assertEqual(
            payload["messages"][1]["content"],
            f"<texto_usuario>\n{texto}\n</texto_usuario>",
        )


class TestSafeHeaders(unittest.TestCase):

    def _response(self):
        response = Mock(spec=requests.Response)
        response.headers = {
            "x-groq-region": "yul",
            "cf-ray": "abc123",
            "retry-after": "10",
            "x-ratelimit-limit-tokens": "8000",
            "x-ratelimit-remaining-tokens": "7000",
            "x-ratelimit-reset-tokens": "5s",
            "x-ratelimit-limit-requests": "100",
            "x-ratelimit-remaining-requests": "99",
            "x-ratelimit-reset-requests": "1s",
            "Authorization": "Bearer SECRETO",
            "Cookie": "secreto",
        }
        return response

    def test_extrae_headers_permitidos(self):
        result = groq_client.safe_headers(self._response())

        self.assertEqual(result["x-groq-region"], "yul")
        self.assertEqual(result["cf-ray"], "abc123")
        self.assertEqual(result["retry-after"], "10")

    def test_no_expone_authorization(self):
        result = groq_client.safe_headers(self._response())

        self.assertNotIn("Authorization", result)

    def test_no_expone_cookie(self):
        result = groq_client.safe_headers(self._response())

        self.assertNotIn("Cookie", result)

    def test_omite_headers_ausentes(self):
        response = Mock(spec=requests.Response)
        response.headers = {
            "x-groq-region": "yul",
        }

        result = groq_client.safe_headers(response)

        self.assertEqual(
            result,
            {
                "x-groq-region": "yul",
            },
        )


class TestParseErrorBody(unittest.TestCase):

    def test_error_json(self):
        response = Mock(spec=requests.Response)

        response.json.return_value = {
            "error": {
                "message": "Rate limit exceeded",
            }
        }

        result = groq_client.parse_error_body(response)

        self.assertEqual(
            result,
            {
                "error": {
                    "message": "Rate limit exceeded",
                }
            },
        )

    def test_error_text_si_json_falla(self):
        response = Mock(spec=requests.Response)

        response.json.side_effect = ValueError()
        response.text = "Internal server error"

        result = groq_client.parse_error_body(response)

        self.assertEqual(
            result,
            "Internal server error",
        )


class TestParseRetryDelay(unittest.TestCase):

    def test_extrae_segundos_enteros(self):
        delay = groq_client.parse_retry_delay(
            "Please try again in 7s"
        )

        self.assertEqual(delay, 7.0)

    def test_extrae_segundos_decimales(self):
        delay = groq_client.parse_retry_delay(
            "Please try again in 2.75s"
        )

        self.assertEqual(delay, 2.75)

    def test_acepta_mayusculas(self):
        delay = groq_client.parse_retry_delay(
            "PLEASE TRY AGAIN IN 9S"
        )

        self.assertEqual(delay, 9.0)

    def test_acepta_mixto(self):
        delay = groq_client.parse_retry_delay(
            "Please Try Again In 4.5S"
        )

        self.assertEqual(delay, 4.5)

    def test_toma_cero(self):
        delay = groq_client.parse_retry_delay(
            "Please try again in 0s"
        )

        self.assertEqual(delay, 0.0)

    def test_usa_default_si_no_hay_coincidencia(self):
        delay = groq_client.parse_retry_delay(
            "Rate limit exceeded",
            default_delay=13,
        )

        self.assertEqual(delay, 13)

    def test_usa_default_si_error_body_es_dict(self):
        body = {
            "error": {
                "message": "Rate limit exceeded"
            }
        }

        delay = groq_client.parse_retry_delay(
            body,
            default_delay=11,
        )

        self.assertEqual(delay, 11)

    def test_no_devuelve_valor_negativo(self):
        delay = groq_client.parse_retry_delay(
            "Please try again in 0s"
        )

        self.assertGreaterEqual(delay, 0.0)


class TestGetRetryDelay(unittest.TestCase):

    def test_prioriza_retry_after(self):
        response = Mock(spec=requests.Response)
        response.headers = {
            "retry-after": "5.5",
        }

        delay = groq_client.get_retry_delay(
            response,
            "Please try again in 20s",
        )

        self.assertEqual(delay, 5.5)

    def test_retry_after_entero(self):
        response = Mock(spec=requests.Response)
        response.headers = {
            "retry-after": "8",
        }

        delay = groq_client.get_retry_delay(
            response,
            "Please try again in 20s",
        )

        self.assertEqual(delay, 8.0)

    def test_fallback_al_body(self):
        response = Mock(spec=requests.Response)
        response.headers = {}

        delay = groq_client.get_retry_delay(
            response,
            "Please try again in 6.25s",
        )

        self.assertEqual(delay, 6.25)

    def test_fallback_al_default(self):
        response = Mock(spec=requests.Response)
        response.headers = {}

        delay = groq_client.get_retry_delay(
            response,
            "Rate limit exceeded",
            default_delay=17,
        )

        self.assertEqual(delay, 17)

    def test_retry_after_invalido_usa_body(self):
        response = Mock(spec=requests.Response)
        response.headers = {
            "retry-after": "abc",
        }

        delay = groq_client.get_retry_delay(
            response,
            "Please try again in 4s",
        )

        self.assertEqual(delay, 4.0)

    def test_retry_after_negativo_se_normaliza(self):
        response = Mock(spec=requests.Response)
        response.headers = {
            "retry-after": "-3",
        }

        delay = groq_client.get_retry_delay(
            response,
            "Please try again in 8s",
        )

        self.assertEqual(delay, 0.0)


class TestExtractUsage(unittest.TestCase):

    def test_extrae_todos_los_tokens(self):
        data = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 40,
                "total_tokens": 140,
            }
        }

        result = groq_client.extract_usage(data)

        self.assertEqual(
            result,
            {
                "prompt_tokens": 100,
                "completion_tokens": 40,
                "total_tokens": 140,
            },
        )

    def test_usage_ausente(self):
        result = groq_client.extract_usage({})

        self.assertEqual(
            result,
            {
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
            },
        )

    def test_usage_none(self):
        result = groq_client.extract_usage(
            {"usage": None}
        )

        self.assertEqual(
            result,
            {
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
            },
        )

    def test_uso_parcial(self):
        result = groq_client.extract_usage(
            {
                "usage": {
                    "prompt_tokens": 100,
                }
            }
        )

        self.assertEqual(result["prompt_tokens"], 100)
        self.assertIsNone(result["completion_tokens"])
        self.assertIsNone(result["total_tokens"])


class TestExtractMetrics(unittest.TestCase):

    def test_extrae_metricas_completas(self):
        data = {
            "usage": {
                "queue_time": 0.1,
                "prompt_time": 0.02,
                "completion_time": 0.2,
                "total_time": 0.32,
                "prompt_tokens_details": {
                    "cached_tokens": 10,
                },
            }
        }

        result = groq_client.extract_metrics(data)

        self.assertEqual(
            result,
            {
                "queue_time": 0.1,
                "prompt_time": 0.02,
                "completion_time": 0.2,
                "total_time": 0.32,
                "cached_tokens": 10,
            },
        )

    def test_metricas_ausentes(self):
        result = groq_client.extract_metrics({})

        self.assertEqual(
            result,
            {
                "queue_time": None,
                "prompt_time": None,
                "completion_time": None,
                "total_time": None,
                "cached_tokens": None,
            },
        )

    def test_prompt_tokens_details_ausente(self):
        data = {
            "usage": {
                "queue_time": 0.1,
            }
        }

        result = groq_client.extract_metrics(data)

        self.assertIsNone(result["cached_tokens"])

    def test_prompt_tokens_details_no_es_dict(self):
        data = {
            "usage": {
                "prompt_tokens_details": "invalid",
            }
        }

        result = groq_client.extract_metrics(data)

        self.assertIsNone(result["cached_tokens"])

    def test_cached_tokens_ausente(self):
        data = {
            "usage": {
                "prompt_tokens_details": {},
            }
        }

        result = groq_client.extract_metrics(data)

        self.assertIsNone(result["cached_tokens"])


class TestCalculateNetworkOverhead(unittest.TestCase):

    def test_calcula_overhead(self):
        result = groq_client.calculate_network_overhead(
            0.60,
            0.25,
        )

        self.assertEqual(result, 0.35)

    def test_redondea_a_cuatro_decimales(self):
        result = groq_client.calculate_network_overhead(
            1.123456,
            0.123456,
        )

        self.assertEqual(result, 1.0)

    def test_server_total_none(self):
        result = groq_client.calculate_network_overhead(
            0.60,
            None,
        )

        self.assertIsNone(result)

    def test_overhead_negativo_es_posible(self):
        result = groq_client.calculate_network_overhead(
            0.10,
            0.20,
        )

        self.assertEqual(result, -0.10)


class TestSendRequest(unittest.TestCase):

    def test_realiza_post_con_payload_y_timeout(self):
        http = Mock()
        response = Mock()
        http.post.return_value = response

        payload = {
            "model": "modelo",
            "messages": [],
        }

        result = groq_client.send_request(http, payload)

        http.post.assert_called_once_with(
            groq_client.API_URL,
            json=payload,
            timeout=groq_client.HTTP_TIMEOUT,
        )

        self.assertIs(result, response)


class TestCallGroq(unittest.TestCase):

    @staticmethod
    def _success_response():
        response = Mock(spec=requests.Response)

        response.status_code = 200
        response.ok = True
        response.headers = {
            "x-groq-region": "yul",
            "cf-ray": "ray123",
            "x-ratelimit-remaining-tokens": "7000",
        }

        response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"categoria":"hardware",'
                            '"prioridad":"alta",'
                            '"resumen":"El equipo no enciende",'
                            '"datos_faltantes":[],' 
                            '"requiere_humano":true,'
                            '"confianza":0.95}'
                        )
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "queue_time": 0.01,
                "prompt_time": 0.02,
                "completion_time": 0.03,
                "total_time": 0.06,
                "prompt_tokens_details": {
                    "cached_tokens": 0,
                },
            },
        }

        return response

    @patch("src.groq_client.time.perf_counter")
    @patch("src.groq_client.requests.Session")
    def test_llamada_exitosa(self, mock_session_class, mock_perf_counter):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response = self._success_response()
        mock_http.post.return_value = response

        mock_perf_counter.side_effect = [10.0, 10.7]

        result = groq_client.call_groq(
            "Prompt de sistema",
            "Mi computador no enciende.",
        )

        mock_http.headers.update.assert_called_once_with(
            groq_client.build_headers()
        )

        self.assertEqual(
            result["raw_output"],
            response.json.return_value["choices"][0]["message"]["content"],
        )
        self.assertEqual(
            result["finish_reason"],
            "stop",
        )
        self.assertEqual(
            result["latency_seconds"],
            0.7,
        )
        self.assertEqual(
            result["usage"]["prompt_tokens"],
            100,
        )
        self.assertEqual(
            result["usage"]["completion_tokens"],
            50,
        )
        self.assertEqual(
            result["usage"]["total_tokens"],
            150,
        )
        self.assertEqual(
            result["metrics"]["queue_time"],
            0.01,
        )
        self.assertEqual(
            result["metrics"]["cached_tokens"],
            0,
        )
        self.assertEqual(
            result["http"]["status_code"],
            200,
        )
        self.assertEqual(
            result["http"]["url"],
            groq_client.API_URL,
        )
        self.assertEqual(
            result["http"]["attempts"],
            1,
        )
        self.assertEqual(
            result["http"]["retry_delays"],
            [],
        )
        self.assertEqual(
            result["http"]["network_overhead_seconds"],
            0.64,
        )

    @patch("src.groq_client.time.perf_counter")
    @patch("src.groq_client.requests.Session")
    def test_429_reintenta_y_luego_tiene_exito(
        self,
        mock_session_class,
        mock_perf_counter,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response_429 = Mock(spec=requests.Response)
        response_429.status_code = 429
        response_429.ok = False
        response_429.headers = {
            "retry-after": "2",
        }
        response_429.json.return_value = {
            "error": {
                "message": "Rate limit exceeded",
            }
        }

        response_ok = self._success_response()

        mock_http.post.side_effect = [
            response_429,
            response_ok,
        ]

        mock_perf_counter.side_effect = [10.0, 10.1]

        with patch("src.groq_client.time.sleep") as mock_sleep:
            result = groq_client.call_groq(
                "Prompt",
                "Texto",
            )

        mock_sleep.assert_called_once_with(2.0)

        self.assertEqual(
            mock_http.post.call_count,
            2,
        )
        self.assertEqual(
            result["http"]["attempts"],
            2,
        )
        self.assertEqual(
            result["http"]["retry_delays"],
            [2.0],
        )
        self.assertEqual(
            result["http"]["status_code"],
            200,
        )

    @patch("src.groq_client.requests.Session")
    def test_429_usa_delay_del_body(
        self,
        mock_session_class,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response_429 = Mock(spec=requests.Response)
        response_429.status_code = 429
        response_429.ok = False
        response_429.headers = {}

        response_429.json.return_value = {
            "error": {
                "message": "Please try again in 3.5s",
            }
        }

        response_ok = self._success_response()

        mock_http.post.side_effect = [
            response_429,
            response_ok,
        ]

        with patch("src.groq_client.time.sleep") as mock_sleep:
            result = groq_client.call_groq(
                "Prompt",
                "Texto",
            )

        mock_sleep.assert_called_once_with(3.5)
        self.assertEqual(
            result["http"]["retry_delays"],
            [3.5],
        )

    @patch("src.groq_client.requests.Session")
    def test_429_usa_delay_default(
        self,
        mock_session_class,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response_429 = Mock(spec=requests.Response)
        response_429.status_code = 429
        response_429.ok = False
        response_429.headers = {}
        response_429.json.return_value = {
            "error": {
                "message": "Rate limit exceeded",
            }
        }

        response_ok = self._success_response()

        mock_http.post.side_effect = [
            response_429,
            response_ok,
        ]

        with patch("src.groq_client.time.sleep") as mock_sleep:
            result = groq_client.call_groq(
                "Prompt",
                "Texto",
            )

        mock_sleep.assert_called_once_with(
            groq_client.DEFAULT_RETRY_DELAY
        )

        self.assertEqual(
            result["http"]["retry_delays"],
            [groq_client.DEFAULT_RETRY_DELAY],
        )

    @patch("src.groq_client.requests.Session")
    def test_429_agota_reintentos(
        self,
        mock_session_class,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response_429 = Mock(spec=requests.Response)
        response_429.status_code = 429
        response_429.ok = False
        response_429.headers = {
            "retry-after": "1",
        }
        response_429.json.return_value = {
            "error": {
                "message": "Rate limit exceeded",
            }
        }

        mock_http.post.return_value = response_429

        with patch("src.groq_client.time.sleep") as mock_sleep:
            with self.assertRaises(RuntimeError) as context:
                groq_client.call_groq(
                    "Prompt",
                    "Texto",
                    max_retries=2,
                )

        self.assertIn(
            "HTTP 429 después de 3 intentos",
            str(context.exception),
        )

        self.assertEqual(
            mock_http.post.call_count,
            3,
        )

        self.assertEqual(
            mock_sleep.call_count,
            2,
        )

    @patch("src.groq_client.requests.Session")
    def test_error_http_500(
        self,
        mock_session_class,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response = Mock(spec=requests.Response)
        response.status_code = 500
        response.ok = False
        response.headers = {}
        response.json.return_value = {
            "error": {
                "message": "Internal Server Error",
            }
        }

        mock_http.post.return_value = response

        with self.assertRaises(RuntimeError) as context:
            groq_client.call_groq(
                "Prompt",
                "Texto",
            )

        self.assertIn(
            "HTTP 500",
            str(context.exception),
        )

        self.assertEqual(
            mock_http.post.call_count,
            1,
        )

    @patch("src.groq_client.requests.Session")
    def test_error_http_400(
        self,
        mock_session_class,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response = Mock(spec=requests.Response)
        response.status_code = 400
        response.ok = False
        response.headers = {}
        response.json.return_value = {
            "error": {
                "message": "Bad Request",
            }
        }

        mock_http.post.return_value = response

        with self.assertRaises(RuntimeError) as context:
            groq_client.call_groq(
                "Prompt",
                "Texto",
            )

        self.assertIn(
            "HTTP 400",
            str(context.exception),
        )

    @patch("src.groq_client.requests.Session")
    def test_request_exception_se_convierte_en_runtime_error(
        self,
        mock_session_class,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        mock_http.post.side_effect = requests.ConnectionError(
            "Connection refused"
        )

        with patch(
            "src.groq_client.time.perf_counter",
            side_effect=[10.0, 10.5],
        ):
            with self.assertRaises(RuntimeError) as context:
                groq_client.call_groq(
                    "Prompt",
                    "Texto",
                )

        self.assertIn(
            "Error HTTP después de 0.5000 s",
            str(context.exception),
        )

        self.assertIn(
            "Connection refused",
            str(context.exception),
        )

    @patch("src.groq_client.requests.Session")
    def test_max_retries_cero(
        self,
        mock_session_class,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response = Mock(spec=requests.Response)
        response.status_code = 429
        response.ok = False
        response.headers = {
            "retry-after": "1",
        }
        response.json.return_value = {
            "error": {
                "message": "Rate limit exceeded",
            }
        }

        mock_http.post.return_value = response

        with patch("src.groq_client.time.sleep") as mock_sleep:
            with self.assertRaises(RuntimeError):
                groq_client.call_groq(
                    "Prompt",
                    "Texto",
                    max_retries=0,
                )

        self.assertEqual(
            mock_http.post.call_count,
            1,
        )
        mock_sleep.assert_not_called()

    @patch("src.groq_client.requests.Session")
    def test_no_hay_sleep_si_no_hay_429(
        self,
        mock_session_class,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response = self._success_response()
        mock_http.post.return_value = response

        with patch("src.groq_client.time.sleep") as mock_sleep:
            groq_client.call_groq(
                "Prompt",
                "Texto",
            )

        mock_sleep.assert_not_called()

    @patch("src.groq_client.requests.Session")
    def test_headers_diagnostico_se_conservan(
        self,
        mock_session_class,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response = self._success_response()
        mock_http.post.return_value = response

        result = groq_client.call_groq(
            "Prompt",
            "Texto",
        )

        self.assertEqual(
            result["http"]["headers"]["x-groq-region"],
            "yul",
        )

        self.assertNotIn(
            "Authorization",
            result["http"]["headers"],
        )

    @patch("src.groq_client.requests.Session")
    def test_salida_no_expone_api_key_en_headers_diagnostico(
        self,
        mock_session_class,
    ):
        mock_http = Mock()
        mock_session_class.return_value = mock_http

        response = self._success_response()
        mock_http.post.return_value = response

        result = groq_client.call_groq(
            "Prompt",
            "Texto",
        )

        diagnostic_headers = result["http"]["headers"]

        for value in diagnostic_headers.values():
            if value is not None:
                self.assertNotIn(
                    groq_client.GROQ_API_KEY,
                    str(value),
                )


class TestResponseSchema(unittest.TestCase):

    def test_schema_es_strict(self):
        self.assertTrue(
            groq_client.RESPONSE_SCHEMA[
                "json_schema"
            ]["strict"]
        )

    def test_schema_tiene_seis_campos_requeridos(self):
        required = groq_client.RESPONSE_SCHEMA[
            "json_schema"
        ]["schema"]["required"]

        self.assertEqual(
            set(required),
            {
                "categoria",
                "prioridad",
                "resumen",
                "datos_faltantes",
                "requiere_humano",
                "confianza",
            },
        )

    def test_schema_no_permite_campos_adicionales(self):
        additional = groq_client.RESPONSE_SCHEMA[
            "json_schema"
        ]["schema"]["additionalProperties"]

        self.assertFalse(additional)

    def test_schema_confianza_tiene_rango(self):
        confianza = groq_client.RESPONSE_SCHEMA[
            "json_schema"
        ]["schema"]["properties"]["confianza"]

        self.assertEqual(confianza["minimum"], 0.0)
        self.assertEqual(confianza["maximum"], 1.0)

    def test_schema_categoria_tiene_valores_validos(self):
        categoria = groq_client.RESPONSE_SCHEMA[
            "json_schema"
        ]["schema"]["properties"]["categoria"]

        self.assertEqual(
            set(categoria["enum"]),
            {
                "hardware",
                "software",
                "redes",
                "cuentas",
                "seguridad",
                "acceso",
                "otros",
            },
        )

    def test_schema_prioridad_tiene_valores_validos(self):
        prioridad = groq_client.RESPONSE_SCHEMA[
            "json_schema"
        ]["schema"]["properties"]["prioridad"]

        self.assertEqual(
            set(prioridad["enum"]),
            {
                "baja",
                "media",
                "alta",
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
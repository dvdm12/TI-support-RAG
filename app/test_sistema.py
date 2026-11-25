"""Pruebas del enrutador de sistema.py (sin red, sin MCP, sin backend)."""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from sistema import _enrutar, procesar


class TestEnrutamiento(unittest.TestCase):
    CASOS = [
        # (pregunta, ruta esperada, código esperado)
        ("hola", "respuesta_directa", None),
        ("¿quién pintó la Mona Lisa?", "respuesta_directa", "fuera_de_alcance"),
        ("por favor cierra el ticket TI-1002", "operacion_prohibida", None),
        ("¿cuál es el estado del ticket TI-1001?", "consulta_ticket", "TI-1001"),
        ("¿cómo va el ticket TI-1003?", "consulta_ticket", "TI-1003"),
        ("¿cuál es el estado de mi ticket?", "aclaracion", None),
        ("¿Cómo configuro la VPN institucional?", "consulta_documental", None),
        # Quejas de avance sin código: pedir el código, no consultar manuales.
        ("mi ticket no avanza", "aclaracion", None),
        ("Mi ticket no ha avanzado", "aclaracion", None),
        ("el ticket sigue pendiente", "aclaracion", None),
        ("no me han respondido el ticket", "aclaracion", None),
        ("mi ticket está estancado", "aclaracion", None),
        # Con código: consultar ese ticket.
        ("mi ticket TI-1001 no avanza", "consulta_ticket", "TI-1001"),
        ("el ticket TI-1002 sigue sin respuesta", "consulta_ticket", "TI-1002"),
        # Sin la palabra ticket sigue siendo documental.
        ("mi wifi sigue sin conectar", "consulta_documental", None),
        ("la impresora está atascada", "consulta_documental", None),
    ]

    def test_casos(self):
        for pregunta, ruta, codigo in self.CASOS:
            with self.subTest(pregunta=pregunta):
                self.assertEqual(_enrutar(pregunta), (ruta, codigo))


class TestConsultaDocumental(unittest.TestCase):
    """Regresión 25-11-2026 (Render): el historial pegado a la pregunta hacía que
    el enrutador del backend consultara el TI-1001 del ejemplo del asistente."""

    def _enviar(self, pregunta, historial):
        respuesta = MagicMock(is_error=False, status_code=200)
        respuesta.json.return_value = {"respuesta": "ok", "fuentes": [], "estado": "OK_EVIDENCIA_INSUFICIENTE"}
        cliente = MagicMock()
        cliente.post = AsyncMock(return_value=respuesta)
        contexto = MagicMock()
        contexto.__aenter__ = AsyncMock(return_value=cliente)
        contexto.__aexit__ = AsyncMock(return_value=False)
        with patch("sistema.httpx.AsyncClient", return_value=contexto):
            asyncio.run(procesar(pregunta, historial, "http://backend", "token"))
        return cliente.post.await_args.kwargs["json"]

    def test_solo_envia_la_pregunta_actual(self):
        historial = [
            ("hola", "Puedo consultar manuales de soporte TI y el estado de tickets de demostración."),
            ("mi mama no me quiere", "Indica un único código de ticket válido, por ejemplo TI-1001."),
        ]
        self.assertEqual(self._enviar("no entiendo", historial), {"pregunta": "no entiendo"})


if __name__ == "__main__":
    unittest.main()

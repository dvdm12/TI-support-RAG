"""Pruebas del enrutador de sistema.py (sin red, sin MCP, sin backend)."""
import unittest

from sistema import _enrutar


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


if __name__ == "__main__":
    unittest.main()

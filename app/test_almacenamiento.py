"""Pruebas unitarias de almacenamiento.py.

Todas las operaciones de red se reemplazan con mocks; no se necesita conexión
a Supabase ni variables de entorno configuradas (salvo los tests de
construir_cliente, que usan patch.dict).
"""
import os
import unittest
from unittest.mock import MagicMock, call, patch

from almacenamiento import (
    AlmacenamientoError,
    Conversacion,
    Mensaje,
    autenticar,
    cargar_mensajes,
    cerrar_sesion,
    construir_cliente,
    crear_conversacion,
    eliminar_conversacion,
    guardar_turno,
    historial_como_pares,
    listar_conversaciones,
    renombrar_conversacion,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _cliente():
    """Mock de supabase.Client con cadena de métodos fluidos."""
    c = MagicMock()
    # table(...).select(...).order(...).execute().data  → []
    # table(...).insert(...).execute().data             → []
    # etc.
    _chain = c.table.return_value
    for method in ("select", "insert", "update", "delete", "eq", "order"):
        getattr(_chain, method).return_value = _chain
    _chain.execute.return_value = MagicMock(data=[])
    return c


def _fila_conversacion(id="conv-1", titulo="Soporte", actualizada_en="2026-11-24T10:00:00"):
    return {"id": id, "titulo": titulo, "actualizada_en": actualizada_en}


def _fila_mensaje(id="msg-1", rol="usuario", contenido="Pregunta", fuentes=None, creado_en="2026-11-24T10:00:00"):
    return {"id": id, "rol": rol, "contenido": contenido,
            "fuentes": fuentes if fuentes is not None else [], "creado_en": creado_en}


# ── construir_cliente ─────────────────────────────────────────────────────────

class ConstruirClienteTests(unittest.TestCase):

    @patch("almacenamiento.create_client")
    def test_crea_cliente_con_ambas_variables(self, mock_create):
        with patch.dict(os.environ, {"SUPABASE_URL": "https://x.supabase.co",
                                     "SUPABASE_PUBLISHABLE_KEY": "sb_key"}):
            construir_cliente()
        mock_create.assert_called_once()
        args = mock_create.call_args
        self.assertEqual(args[0][0], "https://x.supabase.co")
        self.assertEqual(args[0][1], "sb_key")

    def test_falla_sin_url(self):
        with patch.dict(os.environ, {"SUPABASE_PUBLISHABLE_KEY": "k"}, clear=True):
            os.environ.pop("SUPABASE_URL", None)
            with self.assertRaises(AlmacenamientoError):
                construir_cliente()

    def test_falla_sin_key(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "https://x.supabase.co"}, clear=True):
            os.environ.pop("SUPABASE_PUBLISHABLE_KEY", None)
            with self.assertRaises(AlmacenamientoError):
                construir_cliente()

    def test_falla_con_ambas_variables_vacias(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_PUBLISHABLE_KEY": ""}):
            with self.assertRaises(AlmacenamientoError):
                construir_cliente()

    def test_falla_con_url_solo_espacios(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "   ", "SUPABASE_PUBLISHABLE_KEY": "k"}):
            with self.assertRaises(AlmacenamientoError):
                construir_cliente()


# ── autenticar ────────────────────────────────────────────────────────────────

class AutenticarTests(unittest.TestCase):

    def _mock_ok(self):
        c = MagicMock()
        c.auth.sign_in_with_password.return_value = MagicMock(
            user=MagicMock(id="uid-abc"), session=MagicMock()
        )
        return c

    def test_devuelve_user_id_en_exito(self):
        self.assertEqual(autenticar(self._mock_ok(), "u@e.com", "pass"), "uid-abc")

    def test_email_es_stripped_antes_de_enviar(self):
        c = self._mock_ok()
        autenticar(c, "  u@e.com  ", "pass")
        payload = c.auth.sign_in_with_password.call_args[0][0]
        self.assertEqual(payload["email"], "u@e.com")

    def test_sin_user_en_respuesta_lanza_error(self):
        c = MagicMock()
        c.auth.sign_in_with_password.return_value = MagicMock(user=None, session=MagicMock())
        with self.assertRaises(AlmacenamientoError):
            autenticar(c, "u@e.com", "pass")

    def test_sin_session_en_respuesta_lanza_error(self):
        c = MagicMock()
        c.auth.sign_in_with_password.return_value = MagicMock(user=MagicMock(id="x"), session=None)
        with self.assertRaises(AlmacenamientoError):
            autenticar(c, "u@e.com", "pass")

    def test_excepcion_de_supabase_lanza_almacenamiento_error(self):
        c = MagicMock()
        c.auth.sign_in_with_password.side_effect = RuntimeError("network error")
        with self.assertRaises(AlmacenamientoError):
            autenticar(c, "u@e.com", "pass")

    def test_excepcion_no_filtra_mensaje_original(self):
        c = MagicMock()
        c.auth.sign_in_with_password.side_effect = RuntimeError("secret_password=1234")
        try:
            autenticar(c, "u@e.com", "pass")
        except AlmacenamientoError as exc:
            self.assertNotIn("secret_password", str(exc))


# ── cerrar_sesion ─────────────────────────────────────────────────────────────

class CerrarSesionTests(unittest.TestCase):

    def test_llama_sign_out(self):
        c = MagicMock()
        cerrar_sesion(c)
        c.auth.sign_out.assert_called_once()

    def test_excepcion_es_silenciosa(self):
        c = MagicMock()
        c.auth.sign_out.side_effect = RuntimeError("fallo")
        cerrar_sesion(c)  # no debe propagar


# ── crear_conversacion ────────────────────────────────────────────────────────

class CrearConversacionTests(unittest.TestCase):

    def _cliente_con_insert(self, data):
        c = _cliente()
        c.table.return_value.insert.return_value.execute.return_value = MagicMock(data=data)
        return c

    def test_devuelve_id_de_fila_insertada(self):
        c = self._cliente_con_insert([{"id": "uuid-1"}])
        self.assertEqual(crear_conversacion(c, "Mi conversación"), "uuid-1")

    def test_titulo_vacio_usa_default(self):
        c = self._cliente_con_insert([{"id": "x"}])
        crear_conversacion(c, "")
        payload = c.table.return_value.insert.call_args[0][0]
        self.assertEqual(payload["titulo"], "Nueva conversación")

    def test_titulo_espacios_usa_default(self):
        c = self._cliente_con_insert([{"id": "x"}])
        crear_conversacion(c, "   ")
        payload = c.table.return_value.insert.call_args[0][0]
        self.assertEqual(payload["titulo"], "Nueva conversación")

    def test_titulo_sobre_200_chars_es_truncado(self):
        c = self._cliente_con_insert([{"id": "x"}])
        largo = "A" * 250
        crear_conversacion(c, largo)
        payload = c.table.return_value.insert.call_args[0][0]
        self.assertEqual(len(payload["titulo"]), 200)
        self.assertTrue(payload["titulo"].endswith("..."))

    def test_titulo_exactamente_200_chars_no_se_trunca(self):
        c = self._cliente_con_insert([{"id": "x"}])
        titulo = "B" * 200
        crear_conversacion(c, titulo)
        payload = c.table.return_value.insert.call_args[0][0]
        self.assertEqual(payload["titulo"], titulo)

    def test_insert_en_tabla_conversaciones(self):
        c = self._cliente_con_insert([{"id": "x"}])
        crear_conversacion(c, "Test")
        c.table.assert_called_with("conversaciones")

    def test_filas_vacias_lanza_error(self):
        c = self._cliente_con_insert([])
        with self.assertRaises(AlmacenamientoError):
            crear_conversacion(c, "Test")

    def test_excepcion_de_supabase_lanza_error(self):
        c = _cliente()
        c.table.return_value.insert.return_value.execute.side_effect = RuntimeError("DB error")
        with self.assertRaises(AlmacenamientoError):
            crear_conversacion(c, "Test")


# ── listar_conversaciones ─────────────────────────────────────────────────────

class ListarConversacionesTests(unittest.TestCase):

    def _cliente_con_filas(self, filas):
        c = _cliente()
        c.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(data=filas)
        return c

    def test_lista_vacia_devuelve_lista_vacia(self):
        self.assertEqual(listar_conversaciones(self._cliente_con_filas([])), [])

    def test_devuelve_lista_de_conversaciones(self):
        filas = [_fila_conversacion("c1", "A"), _fila_conversacion("c2", "B")]
        result = listar_conversaciones(self._cliente_con_filas(filas))
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Conversacion)
        self.assertEqual(result[0].id, "c1")
        self.assertEqual(result[0].titulo, "A")

    def test_consulta_tabla_conversaciones(self):
        c = self._cliente_con_filas([])
        listar_conversaciones(c)
        c.table.assert_called_with("conversaciones")

    def test_ordena_por_actualizada_en_descendente(self):
        c = self._cliente_con_filas([])
        listar_conversaciones(c)
        c.table.return_value.select.return_value.order.assert_called_with("actualizada_en", desc=True)

    def test_excepcion_de_supabase_lanza_error(self):
        c = _cliente()
        c.table.return_value.select.return_value.order.return_value.execute.side_effect = RuntimeError
        with self.assertRaises(AlmacenamientoError):
            listar_conversaciones(c)

    def test_respuesta_none_devuelve_lista_vacia(self):
        c = _cliente()
        c.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(data=None)
        self.assertEqual(listar_conversaciones(c), [])


# ── renombrar_conversacion ────────────────────────────────────────────────────

class RenombrarConversacionTests(unittest.TestCase):

    def test_llama_update_con_nuevo_titulo(self):
        c = _cliente()
        renombrar_conversacion(c, "conv-1", "Nuevo nombre")
        c.table.return_value.update.assert_called_with({"titulo": "Nuevo nombre"})

    def test_titulo_vacio_usa_sin_titulo(self):
        c = _cliente()
        renombrar_conversacion(c, "conv-1", "   ")
        c.table.return_value.update.assert_called_with({"titulo": "Sin título"})

    def test_filtra_por_id_correcto(self):
        c = _cliente()
        renombrar_conversacion(c, "conv-99", "Título")
        c.table.return_value.update.return_value.eq.assert_called_with("id", "conv-99")

    def test_excepcion_de_supabase_lanza_error(self):
        c = _cliente()
        c.table.return_value.update.return_value.eq.return_value.execute.side_effect = RuntimeError
        with self.assertRaises(AlmacenamientoError):
            renombrar_conversacion(c, "conv-1", "Título")


# ── eliminar_conversacion ─────────────────────────────────────────────────────

class EliminarConversacionTests(unittest.TestCase):

    def test_llama_delete_en_tabla_conversaciones(self):
        c = _cliente()
        eliminar_conversacion(c, "conv-1")
        c.table.assert_called_with("conversaciones")
        c.table.return_value.delete.assert_called_once()

    def test_filtra_por_id_correcto(self):
        c = _cliente()
        eliminar_conversacion(c, "conv-42")
        c.table.return_value.delete.return_value.eq.assert_called_with("id", "conv-42")

    def test_excepcion_de_supabase_lanza_error(self):
        c = _cliente()
        c.table.return_value.delete.return_value.eq.return_value.execute.side_effect = RuntimeError
        with self.assertRaises(AlmacenamientoError):
            eliminar_conversacion(c, "conv-1")


# ── cargar_mensajes ───────────────────────────────────────────────────────────

class CargarMensajesTests(unittest.TestCase):

    def _cliente_con_filas(self, filas):
        c = _cliente()
        (c.table.return_value.select.return_value
         .eq.return_value.order.return_value
         .execute.return_value) = MagicMock(data=filas)
        return c

    def test_lista_vacia_devuelve_lista_vacia(self):
        self.assertEqual(cargar_mensajes(self._cliente_con_filas([]), "conv-1"), [])

    def test_devuelve_lista_de_mensajes(self):
        filas = [
            _fila_mensaje("m1", "usuario", "Pregunta"),
            _fila_mensaje("m2", "asistente", "Respuesta", fuentes=[{"src": "doc"}]),
        ]
        result = cargar_mensajes(self._cliente_con_filas(filas), "conv-1")
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Mensaje)
        self.assertEqual(result[0].rol, "usuario")
        self.assertEqual(result[1].fuentes, [{"src": "doc"}])

    def test_fuentes_none_devuelve_lista_vacia(self):
        filas = [_fila_mensaje("m1", "asistente", "Resp", fuentes=None)]
        result = cargar_mensajes(self._cliente_con_filas(filas), "conv-1")
        self.assertEqual(result[0].fuentes, [])

    def test_filtra_por_conversacion_id(self):
        c = self._cliente_con_filas([])
        cargar_mensajes(c, "conv-99")
        c.table.return_value.select.return_value.eq.assert_called_with("conversacion_id", "conv-99")

    def test_ordena_por_creado_en_ascendente(self):
        c = self._cliente_con_filas([])
        cargar_mensajes(c, "conv-1")
        (c.table.return_value.select.return_value
         .eq.return_value.order.assert_called_with("creado_en", desc=False))

    def test_respuesta_none_devuelve_lista_vacia(self):
        c = _cliente()
        (c.table.return_value.select.return_value
         .eq.return_value.order.return_value
         .execute.return_value) = MagicMock(data=None)
        self.assertEqual(cargar_mensajes(c, "conv-1"), [])

    def test_excepcion_de_supabase_lanza_error(self):
        c = _cliente()
        (c.table.return_value.select.return_value
         .eq.return_value.order.return_value
         .execute.side_effect) = RuntimeError
        with self.assertRaises(AlmacenamientoError):
            cargar_mensajes(c, "conv-1")


# ── guardar_turno ─────────────────────────────────────────────────────────────

class GuardarTurnoTests(unittest.TestCase):

    def test_inserta_dos_filas_en_mensajes(self):
        c = _cliente()
        guardar_turno(c, "conv-1", "Pregunta", "Respuesta", [{"src": "doc"}])
        c.table.assert_called_with("mensajes")
        filas = c.table.return_value.insert.call_args[0][0]
        self.assertEqual(len(filas), 2)

    def test_primera_fila_es_usuario(self):
        c = _cliente()
        guardar_turno(c, "conv-1", "Pregunta", "Respuesta")
        filas = c.table.return_value.insert.call_args[0][0]
        self.assertEqual(filas[0]["rol"], "usuario")
        self.assertEqual(filas[0]["contenido"], "Pregunta")

    def test_segunda_fila_es_asistente(self):
        c = _cliente()
        guardar_turno(c, "conv-1", "Pregunta", "Respuesta")
        filas = c.table.return_value.insert.call_args[0][0]
        self.assertEqual(filas[1]["rol"], "asistente")
        self.assertEqual(filas[1]["contenido"], "Respuesta")

    def test_fuentes_en_fila_asistente(self):
        c = _cliente()
        fuentes = [{"chunk_id": "c1", "source": "doc.pdf"}]
        guardar_turno(c, "conv-1", "P", "R", fuentes)
        filas = c.table.return_value.insert.call_args[0][0]
        self.assertEqual(filas[1]["fuentes"], fuentes)

    def test_fuentes_none_usa_lista_vacia(self):
        c = _cliente()
        guardar_turno(c, "conv-1", "P", "R", None)
        filas = c.table.return_value.insert.call_args[0][0]
        self.assertEqual(filas[1]["fuentes"], [])

    def test_fila_usuario_siempre_tiene_fuentes_vacias(self):
        c = _cliente()
        guardar_turno(c, "conv-1", "P", "R", [{"src": "doc"}])
        filas = c.table.return_value.insert.call_args[0][0]
        self.assertEqual(filas[0]["fuentes"], [])

    def test_ambas_filas_llevan_conversacion_id(self):
        c = _cliente()
        guardar_turno(c, "conv-77", "P", "R")
        filas = c.table.return_value.insert.call_args[0][0]
        self.assertTrue(all(f["conversacion_id"] == "conv-77" for f in filas))

    def test_excepcion_de_supabase_lanza_error(self):
        c = _cliente()
        c.table.return_value.insert.return_value.execute.side_effect = RuntimeError
        with self.assertRaises(AlmacenamientoError):
            guardar_turno(c, "conv-1", "P", "R")


# ── historial_como_pares ──────────────────────────────────────────────────────

def _msg(rol, contenido):
    return Mensaje(id="x", rol=rol, contenido=contenido)


class HistorialComoPares(unittest.TestCase):

    def test_lista_vacia_devuelve_lista_vacia(self):
        self.assertEqual(historial_como_pares([]), [])

    def test_un_par_completo(self):
        msgs = [_msg("usuario", "P"), _msg("asistente", "R")]
        self.assertEqual(historial_como_pares(msgs), [("P", "R")])

    def test_varios_pares_completos(self):
        msgs = [
            _msg("usuario", "P1"), _msg("asistente", "R1"),
            _msg("usuario", "P2"), _msg("asistente", "R2"),
        ]
        self.assertEqual(historial_como_pares(msgs), [("P1", "R1"), ("P2", "R2")])

    def test_asistente_huerfano_sin_usuario_previo_es_ignorado(self):
        msgs = [_msg("asistente", "R")]
        self.assertEqual(historial_como_pares(msgs), [])

    def test_usuario_huerfano_sin_asistente_siguiente_no_genera_par(self):
        msgs = [_msg("usuario", "P")]
        self.assertEqual(historial_como_pares(msgs), [])

    def test_dos_usuarios_consecutivos_el_segundo_reemplaza_al_primero(self):
        msgs = [_msg("usuario", "P1"), _msg("usuario", "P2"), _msg("asistente", "R")]
        pares = historial_como_pares(msgs)
        self.assertEqual(len(pares), 1)
        self.assertEqual(pares[0], ("P2", "R"))

    def test_par_incompleto_al_final_no_aparece(self):
        msgs = [
            _msg("usuario", "P1"), _msg("asistente", "R1"),
            _msg("usuario", "P2"),
        ]
        self.assertEqual(historial_como_pares(msgs), [("P1", "R1")])

    def test_asistente_huerfano_entre_pares_validos_es_ignorado(self):
        msgs = [
            _msg("usuario", "P1"), _msg("asistente", "R1"),
            _msg("asistente", "extra"),
            _msg("usuario", "P2"), _msg("asistente", "R2"),
        ]
        self.assertEqual(historial_como_pares(msgs), [("P1", "R1"), ("P2", "R2")])

    def test_solo_usuarios_sin_asistentes_devuelve_lista_vacia(self):
        msgs = [_msg("usuario", f"P{i}") for i in range(5)]
        self.assertEqual(historial_como_pares(msgs), [])


if __name__ == "__main__":
    unittest.main()

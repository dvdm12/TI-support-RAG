"""Interfaz Gradio para la mesa de ayuda TI — Clase 12.

Flujo:
  1. Login con Supabase Auth (correo + contraseña)
  2. Selector de conversaciones con historial persistente en Supabase
  3. Chat con enrutamiento via sistema.py  (MCP tickets / RAG documental)
  4. Cierre de sesión limpio

Variables de entorno requeridas (ver .env.example):
  SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY
  BACKEND_URL, BACKEND_API_TOKEN
"""
from __future__ import annotations

import os
from pathlib import Path

import gradio as gr

from almacenamiento import (
    AlmacenamientoError,
    Conversacion,
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
from sistema import Resultado, SistemaError, procesar


# ── Configuración ─────────────────────────────────────────────────────────────

def _cargar_env() -> None:
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
        return
    except ImportError:
        pass
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_cargar_env()

_BACKEND_URL   = os.environ.get("BACKEND_URL",        "http://127.0.0.1:8000")
_BACKEND_TOKEN = os.environ.get("BACKEND_API_TOKEN",  "")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _choices(convs: list[Conversacion]) -> list[tuple[str, str]]:
    return [(c.titulo, c.id) for c in convs]


def _a_mensajes(historial: list[tuple[str, str]]) -> list[dict]:
    """Convierte pares (usuario, asistente) al formato Messages de Gradio 6."""
    msgs = []
    for user, assistant in historial:
        if user:
            msgs.append({"role": "user", "content": user})
        if assistant:
            msgs.append({"role": "assistant", "content": assistant})
    return msgs


# ── Handlers de eventos ───────────────────────────────────────────────────────

def _hacer_login(email: str, password: str):
    """Autentica y prepara la vista principal. Si no hay conversaciones crea una."""
    try:
        client = construir_cliente()
        autenticar(client, email, password)
        convs = listar_conversaciones(client)
        if not convs:
            crear_conversacion(client, "Nueva conversación")
            convs = listar_conversaciones(client)
        choices = _choices(convs)
        conv_id = choices[0][1]
        mensajes = cargar_mensajes(client, conv_id)
        historial = historial_como_pares(mensajes)
        return (
            client,
            conv_id,
            historial,
            gr.update(visible=False),                   # panel_login
            gr.update(visible=True),                    # panel_principal
            gr.update(choices=choices, value=conv_id),  # convs_dd
            _a_mensajes(historial),                     # chatbot (Messages format)
            "",                                         # login_error
        )
    except AlmacenamientoError as exc:
        return (
            None, None, [],
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(choices=[], value=None),
            [],
            f"⚠ {exc}",
        )


def _seleccionar_conversacion(conv_id: str | None, client):
    """Carga los mensajes de la conversación seleccionada."""
    if client is None or not conv_id:
        return conv_id, [], []
    try:
        mensajes  = cargar_mensajes(client, conv_id)
        historial = historial_como_pares(mensajes)
        return conv_id, historial, _a_mensajes(historial)
    except AlmacenamientoError:
        return conv_id, [], []


def _nueva_conversacion(client):
    """Crea una conversación vacía y la selecciona."""
    if client is None:
        return None, [], gr.update(), []
    try:
        conv_id = crear_conversacion(client, "Nueva conversación")
        convs   = listar_conversaciones(client)
        return conv_id, [], gr.update(choices=_choices(convs), value=conv_id), []  # chatbot vacío = []
    except AlmacenamientoError:
        return None, [], gr.update(), []


async def _enviar_pregunta(
    pregunta: str,
    historial: list[tuple[str, str]],
    client,
    conv_id: str | None,
):
    """Enruta la pregunta, persiste el turno y devuelve el historial actualizado."""
    pregunta = pregunta.strip()
    if not pregunta or client is None or not conv_id:
        return historial, historial, [], {}, ""

    try:
        resultado: Resultado = await procesar(
            pregunta, historial, _BACKEND_URL, _BACKEND_TOKEN
        )
    except SistemaError as exc:
        resultado = Resultado(
            respuesta=f"[Error del sistema] {exc}",
            estado="ERROR",
        )
    except Exception as exc:
        resultado = Resultado(
            respuesta=f"[Error inesperado] {type(exc).__name__}",
            estado="ERROR",
        )

    nuevo_historial = historial + [(pregunta, resultado.respuesta)]

    try:
        guardar_turno(client, conv_id, pregunta, resultado.respuesta, resultado.fuentes)
    except AlmacenamientoError:
        pass  # no bloquear la UI si falla el guardado

    return _a_mensajes(nuevo_historial), nuevo_historial, resultado.fuentes, resultado.traza, ""


def _renombrar(client, conv_id: str | None, nuevo_titulo: str):
    if client is None or not conv_id or not nuevo_titulo.strip():
        return gr.update()
    try:
        renombrar_conversacion(client, conv_id, nuevo_titulo.strip())
        convs = listar_conversaciones(client)
        return gr.update(choices=_choices(convs), value=conv_id)
    except AlmacenamientoError:
        return gr.update()


def _eliminar(client, conv_id: str | None):
    """Elimina la conversación activa (cascade en BD) y abre la siguiente."""
    if client is None or not conv_id:
        return None, [], gr.update(), []
    try:
        eliminar_conversacion(client, conv_id)
        convs   = listar_conversaciones(client)
        choices = _choices(convs)
        new_id  = choices[0][1] if choices else None
        historial = []
        if new_id:
            mensajes  = cargar_mensajes(client, new_id)
            historial = historial_como_pares(mensajes)
        return new_id, historial, gr.update(choices=choices, value=new_id), _a_mensajes(historial)
    except AlmacenamientoError:
        return conv_id, [], gr.update(), []


def _cerrar_sesion(client):
    if client is not None:
        cerrar_sesion(client)
    return (
        None, None, [],
        gr.update(visible=True),                    # panel_login
        gr.update(visible=False),                   # panel_principal
        gr.update(choices=[], value=None),          # convs_dd
        [],                                         # chatbot (vacío)
    )


# ── Interfaz ──────────────────────────────────────────────────────────────────

def crear_interfaz() -> gr.Blocks:
    with gr.Blocks(title="Mesa de ayuda TI") as app:

        # Estado por pestaña (Gradio crea una instancia por conexión)
        s_client  = gr.State(None)
        s_conv_id = gr.State(None)
        s_hist    = gr.State([])

        # ── Panel de login ────────────────────────────────────────────────────
        with gr.Group(visible=True) as panel_login:
            gr.Markdown("# Mesa de ayuda TI\n\nIniciar sesión con tu cuenta Supabase.")
            email_inp    = gr.Textbox(label="Correo electrónico")
            password_inp = gr.Textbox(label="Contraseña", type="password")
            login_btn    = gr.Button("Entrar", variant="primary")
            login_error  = gr.Markdown(value="")

        # ── Panel principal ───────────────────────────────────────────────────
        with gr.Group(visible=False) as panel_principal:
            with gr.Row():

                # Barra lateral: lista de conversaciones
                with gr.Column(scale=1, min_width=240):
                    gr.Markdown("### Conversaciones")
                    nueva_btn = gr.Button("+ Nueva", variant="secondary", size="sm")
                    convs_dd  = gr.Dropdown(
                        choices=[],
                        label="Activa",
                        interactive=True,
                        allow_custom_value=False,
                    )
                    nuevo_titulo_inp = gr.Textbox(
                        label="Renombrar",
                        placeholder="Escribe un nuevo título…",
                        max_lines=1,
                    )
                    renombrar_btn = gr.Button("Renombrar", size="sm")
                    eliminar_btn  = gr.Button("Eliminar", variant="stop", size="sm")
                    gr.Markdown("---")
                    logout_btn = gr.Button("Cerrar sesión", size="sm")

                # Área de chat
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(label="Conversación", height=460)
                    pregunta_inp = gr.Textbox(
                        label="",
                        placeholder="Escribe tu pregunta de soporte…",
                        lines=2,
                        max_lines=5,
                        max_length=8000,
                    )
                    enviar_btn = gr.Button("Enviar", variant="primary")

                    with gr.Accordion("Fuentes documentales", open=False):
                        fuentes_json = gr.JSON(label="")
                    with gr.Accordion("Traza de enrutamiento", open=False):
                        traza_json = gr.JSON(label="")

        # ── Eventos ───────────────────────────────────────────────────────────

        _login_out = [
            s_client, s_conv_id, s_hist,
            panel_login, panel_principal,
            convs_dd, chatbot, login_error,
        ]
        login_btn.click(_hacer_login, [email_inp, password_inp], _login_out)
        password_inp.submit(_hacer_login, [email_inp, password_inp], _login_out)

        nueva_btn.click(
            _nueva_conversacion,
            inputs=[s_client],
            outputs=[s_conv_id, s_hist, convs_dd, chatbot],
        )

        convs_dd.change(
            _seleccionar_conversacion,
            inputs=[convs_dd, s_client],
            outputs=[s_conv_id, s_hist, chatbot],
        )

        _enviar_out = [chatbot, s_hist, fuentes_json, traza_json, pregunta_inp]
        enviar_btn.click(
            _enviar_pregunta,
            inputs=[pregunta_inp, s_hist, s_client, s_conv_id],
            outputs=_enviar_out,
        )
        pregunta_inp.submit(
            _enviar_pregunta,
            inputs=[pregunta_inp, s_hist, s_client, s_conv_id],
            outputs=_enviar_out,
        )

        renombrar_btn.click(
            _renombrar,
            inputs=[s_client, s_conv_id, nuevo_titulo_inp],
            outputs=[convs_dd],
        )

        eliminar_btn.click(
            _eliminar,
            inputs=[s_client, s_conv_id],
            outputs=[s_conv_id, s_hist, convs_dd, chatbot],
        )

        logout_btn.click(
            _cerrar_sesion,
            inputs=[s_client],
            outputs=[s_client, s_conv_id, s_hist, panel_login, panel_principal, convs_dd, chatbot],
        )

    return app


def _puerto() -> int:
    """Render (y otros alojamientos) asignan el puerto en PORT; en local se usa
    GRADIO_SERVER_PORT o 7860."""
    valor = os.environ.get("PORT") or os.environ.get("GRADIO_SERVER_PORT") or "7860"
    return int(valor)


if __name__ == "__main__":
    crear_interfaz().launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=_puerto(),
        share=False,
    )

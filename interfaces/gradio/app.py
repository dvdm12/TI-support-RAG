"""Local Gradio client for the TI Support API."""

import os

import gradio as gr
import httpx


def consultar(pregunta: str):
    pregunta = pregunta.strip()
    if not pregunta:
        return "Escribe una pregunta de soporte.", {}, []

    token = os.environ.get("DJANGO_API_TOKEN", "").strip()
    if not token:
        return "Configura DJANGO_API_TOKEN antes de iniciar Gradio.", {}, []

    base_url = os.environ.get("DJANGO_API_URL", "http://127.0.0.1:8000").rstrip("/")
    try:
        response = httpx.post(
            f"{base_url}/api/v1/rag/query/",
            json={"pregunta": pregunta},
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(120, connect=5),
        )
    except httpx.TimeoutException:
        return "Django tardó demasiado en responder. Intenta de nuevo.", {}, []
    except (httpx.RequestError, httpx.InvalidURL):
        return "No se pudo conectar con Django. Comprueba la URL y el servicio.", {}, []

    try:
        data = response.json()
    except ValueError:
        return f"Django devolvió una respuesta inesperada (HTTP {response.status_code}).", {}, []
    if not isinstance(data, dict):
        return f"Django devolvió una respuesta inesperada (HTTP {response.status_code}).", {}, []

    trace = {
        **(data.get("traza") or {}),
        "estado": data.get("estado"),
        "request_id": data.get("request_id"),
    }
    trace = {key: value for key, value in trace.items() if value is not None}
    if response.is_error or response.is_redirect:
        error = data.get("error") or {}
        message = error.get("message") or "No se pudo completar la consulta."
        return f"{message} (HTTP {response.status_code})", trace, []

    return data.get("respuesta") or "Django no devolvió una respuesta.", trace, data.get("fuentes") or []


def crear_interfaz():
    with gr.Blocks(title="Mesa de ayuda TI") as interfaz:
        gr.Markdown("# Mesa de ayuda TI")
        pregunta = gr.Textbox(label="Pregunta de soporte", lines=3, max_length=8000)
        consultar_btn = gr.Button("Consultar", variant="primary")
        respuesta = gr.Textbox(label="Respuesta", interactive=False)
        traza = gr.JSON(label="Traza de Django")
        fuentes = gr.JSON(label="Fuentes documentales")
        consultar_btn.click(consultar, pregunta, [respuesta, traza, fuentes], api_name="consultar")
    return interfaz


if __name__ == "__main__":
    crear_interfaz().launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1"),
        share=False,
    )

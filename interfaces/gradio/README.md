# Mesa de ayuda TI en Gradio

La interfaz llama a `POST /api/v1/rag/query/` en Django. Muestra la respuesta, la traza con la ruta elegida y las fuentes de las consultas documentales.

## Docker Compose

Desde la raíz del repositorio, inicia Django y Gradio con la configuración de Django que ya usa el proyecto:

```bash
docker compose --env-file backend/.env -f infra/compose.yaml up -d --build gradio
```

Compose pasa `DJANGO_API_TOKEN` a Gradio y lo conecta a Django por la red interna. Abre [Gradio local](http://127.0.0.1:7860).

## Ejecución directa

Con Django activo, ejecuta estos comandos desde la raíz del repositorio:

```bash
python3 -m venv .venv-gradio
.venv-gradio/bin/python -m pip install -r interfaces/gradio/requirements.txt
read -rs DJANGO_API_TOKEN
export DJANGO_API_TOKEN
.venv-gradio/bin/python interfaces/gradio/app.py
```

Cuando el comando `read` espere la entrada, pega el mismo token configurado en Django y presiona Enter. Abre [Gradio local](http://127.0.0.1:7860). Puedes definir `DJANGO_API_URL` si Django escucha en una dirección distinta a `http://127.0.0.1:8000`.

| Pregunta | Qué verificar |
|---|---|
| ¿Cuál es el estado del ticket TI-1002? | Ruta `consulta_ticket`, estado pendiente de información y operación `consultar_estado_ticket` |
| ¿Cuál es el estado del ticket TI-9998? | Ruta `consulta_ticket` y resultado `TICKET_NO_ENCONTRADO` |
| ¿Qué indica el manual si una instalación autorizada pide privilegios que no tengo? | Ruta `consulta_documental` y fuentes si la consulta documental se completa |

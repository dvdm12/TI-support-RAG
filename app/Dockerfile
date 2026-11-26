FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRADIO_ANALYTICS_ENABLED=False \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860

RUN useradd --create-home gradio
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# sistema.py lanza servidor_mcp.py por stdio con el mismo intérprete.
COPY app.py sistema.py almacenamiento.py servidor_mcp.py ./

USER gradio
EXPOSE 7860
CMD ["python", "app.py"]

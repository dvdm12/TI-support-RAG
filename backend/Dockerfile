# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.12-slim-bookworm
FROM ${PYTHON_IMAGE} AS dependencies

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
RUN python -m venv /opt/venv
COPY requirements-runtime.txt .
# Use the CPU index exclusively for torch to avoid CUDA/NVIDIA packages.
RUN /opt/venv/bin/pip install --only-binary=:all: \
        --index-url https://download.pytorch.org/whl/cpu torch==2.14.1+cpu \
    && /opt/venv/bin/pip install --only-binary=:all: -r requirements-runtime.txt \
    && /opt/venv/bin/pip check \
    && find /opt/venv -type d -name __pycache__ -prune -exec rm -rf '{}' +

FROM ${PYTHON_IMAGE} AS runtime
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/app \
    HF_HOME=/home/app/.cache/huggingface \
    TIKTOKEN_CACHE_DIR=/home/app/.cache/tiktoken \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    DJANGO_DEBUG=false

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app \
    && mkdir -p /home/app/.cache/huggingface /home/app/.cache/tiktoken \
    && chown -R app:app /home/app/.cache
COPY --from=dependencies /opt/venv /opt/venv
WORKDIR /app
COPY api/ api/
COPY ti_api/ ti_api/
COPY src/ src/
COPY schemas/ schemas/
COPY prompts/ prompts/
COPY manage.py .
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/', timeout=3).close()"]
# One process shares the model and the existing RAG semaphore. Threads keep
# health/docs responsive while a provider request is in progress.
CMD ["gunicorn", "ti_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--worker-class", "gthread", "--threads", "4", "--timeout", "300", "--graceful-timeout", "30", "--access-logfile", "-", "--error-logfile", "-"]

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
# Drop files never used at runtime (~200 MB): torch C++ test binaries and test
# fixtures, protoc, C++ headers for building extensions, and the installers.
# torch/bin/torch_shm_manager must stay: `import torch` checks for it.
RUN SITE=/opt/venv/lib/python3.12/site-packages \
    && rm -rf "$SITE/torch/test" "$SITE/torch/include" \
    && find "$SITE/torch/bin" -maxdepth 1 -type f ! -name torch_shm_manager -delete \
    && rm -rf "$SITE"/pip "$SITE"/pip-*.dist-info "$SITE"/setuptools "$SITE"/setuptools-*.dist-info \
              /opt/venv/bin/pip /opt/venv/bin/pip3*
# Write bytecode only for the modules the API imports (the runtime user cannot
# write __pycache__, so each start recompiled ~11 s of imports). Compiling all of
# site-packages would add ~275 MB; importing the real model stack adds ~90 MB.
# The model weights are not downloaded here: imports only.
RUN /opt/venv/bin/python -c "\
import torch, numpy, scipy, sklearn, sympy, tokenizers, safetensors.torch, huggingface_hub; \
import transformers, sentence_transformers, httpx, supabase, django, tiktoken, gunicorn; \
import requests, PIL, pytesseract, pydantic, yaml, rich, jinja2, joblib; \
from sentence_transformers import SentenceTransformer; \
from sentence_transformers.models import Transformer, Pooling; \
from transformers import AutoConfig, AutoModel, AutoTokenizer; \
import transformers.models.bert.modeling_bert, transformers.models.bert.configuration_bert"

FROM ${PYTHON_IMAGE} AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && tesseract --list-langs | grep -qx spa \
    && tesseract --list-langs | grep -qx eng
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
# Same for the project and the Django stack it loads (PYTHONDONTWRITEBYTECODE
# is cleared only for this build step; the running container never writes).
RUN PYTHONDONTWRITEBYTECODE= DJANGO_SETTINGS_MODULE=ti_api.settings python -c "\
import django; django.setup(); \
import api.urls, api.controllers, api.documentation, api.services; \
import src.rag.pipeline, src.rag.repository, src.rag.retrieval, src.groq_client"
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/', timeout=3).close()"]
# One process shares the model and the existing RAG semaphore. Threads keep
# health/docs responsive while a provider request is in progress.
CMD ["gunicorn", "ti_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--worker-class", "gthread", "--threads", "4", "--timeout", "300", "--graceful-timeout", "30", "--access-logfile", "-", "--error-logfile", "-"]

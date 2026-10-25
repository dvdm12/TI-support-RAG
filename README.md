# TI-support-RAG

Mesa de Ayuda TI con recuperación documental en Supabase, generación con Groq y API Django.

## Parcial 2 en Colab

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dvdm12/TI-support-RAG/blob/codex/backend-infra-ricoh-local/backend/notebooks/parcial2.ipynb)

Ejecuta el notebook y usa el **Panel del profesor** al final: trece casos guardados,
preguntas nuevas al corpus y generación opcional con **secretos propios de Colab**.
El ZIP de recursos se descarga automáticamente desde la misma rama y se verifica
por SHA256; también se puede subir manualmente. La reproducción y búsqueda BM25
no necesitan claves. [Instrucciones para el profesor](backend/notebooks/GUIA_PROFESOR.md).

```text
backend/   API, código Python, notebooks, corpus, pruebas y documentación
frontend/  Aplicación web (pendiente de implementación)
infra/     Migraciones de Supabase y futura configuración de infraestructura
```

El entorno virtual se mantiene en `.venv/`, en la raíz del repositorio. Ejecuta los comandos Python desde `backend/`.

## Desarrollo local

Desde la raíz del repositorio, con Python 3.12:

```bash
python3 -m venv .venv
source .venv/bin/activate
cd backend
python -m pip install -r requirements.txt
cp .env.example .env
# Completar backend/.env con las credenciales locales.
python manage.py runserver 127.0.0.1:8000
```

Si ya tienes `backend/.env` configurado, conserva sus valores.

Swagger: <http://127.0.0.1:8000/api/v1/docs/>.

## Verificación local

Con el entorno activo y desde `backend/`:

```bash
python manage.py check
python manage.py test api
python -m unittest discover -s test
```

Documentación: [backend](backend/README.md), [API](backend/docs/API.md), [RAG](backend/docs/RAG.md) e [infraestructura](infra/README.md).

## Docker

```bash
docker build -t ti-support-rag-backend:local backend
docker compose -f infra/compose.yaml up -d
```

Usa `backend/.env` y el índice local existente. Detalles de dependencias, modelos
y volúmenes: [backend en Docker](backend/docs/DOCKER.md).

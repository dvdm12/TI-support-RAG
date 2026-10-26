# TI-support-RAG

Mesa de ayuda TI con clasificación, OCR, búsqueda documental en Supabase,
generación con Groq, API Django y notebook de demostración.

**Para el profesor, empezar por el [notebook de Parcial 2](backend/notebooks/parcial2.ipynb).**
Incluye las ejecuciones guardadas para revisar los resultados sin configurar secretos.
Para consultas nuevas, seguir la preparación indicada en el notebook. Se entrega junto al
[ZIP de recursos](backend/notebooks/parcial2_recursos.zip).
También se pueden revisar directamente el
[PDF de resultados](backend/docs/parcial2/ejecuciones/20261025T183222Z/resultados/comparacion_hibrida_desarrollo.pdf)
y el [material para el profesor](backend/docs/parcial2/README.md).

Para **ejecutar el notebook en local**, seguir los pasos **1–5**. Después, el
**paso 6** permite levantar la API y probar Swagger. El notebook utiliza los
componentes Python directamente y funciona sin arrancar Django ni Docker.
El frontend web todavía no está implementado.

## 1. Preparar el equipo y descargar el proyecto

Se necesita **Python 3.12**, Git, Internet y cuentas propias en Groq y Supabase.
Los comandos siguientes son para Linux con Bash/Zsh. En Ubuntu/Debian, instalar
Tesseract y los recursos del ejemplo OCR:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-spa fonts-dejavu-core
```

Clonar `main`, que contiene la entrega. Si ya tienes el repositorio, omite estos
comandos y abre una terminal en su raíz:

```bash
git clone --branch main https://github.com/dvdm12/TI-support-RAG.git
cd TI-support-RAG
```

## 2. Crear y activar el entorno Python

Desde la raíz del repositorio:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
cd backend
python -m pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip install jupyterlab
```

Usar siempre **`.venv`**, también si la terminal tenía `.venv-test` activado.
La instalación de PyTorch es para CPU; no requiere GPU. Los comandos siguientes
se ejecutan desde **`backend/`**, salvo que se indique otra cosa.

## 3. Configurar las credenciales del notebook

Crear `.env` sin reemplazar uno existente:

```bash
cp -n .env.example .env
```

Obtener una clave propia desde la [consola de Groq](https://console.groq.com/).
Editar **`backend/.env`** y completar estos cinco campos:

| Variable | Valor que debe colocar el profesor |
|---|---|
| `GROQ_API_KEY` | Su clave de API Groq |
| `SUPABASE_URL` | URL HTTPS de su proyecto Supabase |
| `SUPABASE_PUBLISHABLE_KEY` | Clave publicable de ese proyecto, comienza por `sb_publishable_` |
| `SUPABASE_EMAIL` | Correo del usuario que creará en Supabase Auth |
| `SUPABASE_PASSWORD` | Contraseña de ese usuario |

No publicar `.env` ni pegar las claves en el notebook. Los valores Django se
configuran más adelante, al levantar la API en el paso 6.

## 4. Preparar el proyecto Supabase

1. Crear un proyecto propio en [Supabase](https://supabase.com/).
2. En su editor SQL, ejecutar el contenido de
   [20261014_documentary_rag.sql](infra/supabase/migrations/20261014_documentary_rag.sql).
   Crea la tabla, las políticas RLS y la función de búsqueda.
3. Crear un usuario de correo y contraseña en **Supabase Auth**, con correo
   confirmado. Usar esos mismos datos en `.env`; no son necesariamente los del
   acceso al panel administrativo de Supabase.
4. Completar la URL y clave publicable del mismo proyecto en `.env`.

El notebook restaura automáticamente el índice desde su ZIP: **70 fragmentos de
siete manuales simulados**. Para un proyecto Supabase nuevo, el paso siguiente
indica cómo habilitar su primera carga desde el propio notebook.

## 5. Ejecutar el notebook del profesor

Con `.venv` activo y desde `backend/`:

```bash
python -m ipykernel install --user --name ti-support-rag --display-name "Python (TI-support-RAG)"
python -m jupyterlab notebooks/parcial2.ipynb
```

En JupyterLab:

1. Seleccionar el kernel **Python (TI-support-RAG)**.
2. Mantener `MODE='consulta_real'` y `USE_SUPABASE=True`; leerá el `.env` local.
3. Si el usuario de Supabase aún no tiene el corpus, poner
   `ALLOW_SUPABASE_UPSERT=True` en la primera celda para la carga inicial.
   Si ya lo tiene, dejarlo en `False`.
4. Ejecutar todas las celdas en orden. Incluye extracción de PDF, OCR, modelo,
   conexión a Supabase, clasificación, recuperación y generación con Groq.
5. Tras la primera carga correcta, volver a dejar `ALLOW_SUPABASE_UPSERT=False`
   para las siguientes ejecuciones.
6. Al final, cambiar `PREGUNTA` en el **Panel del profesor** y ejecutar esa celda.
   Mantener `ACCION="Consultar con Groq"`, `USAR_SUPABASE=True` y
   `CARGAR_CORPUS_PROPIO=False`, porque el corpus ya está cargado.

Ejecutar todo hace dos consultas nuevas, una en el punto 10 y otra en el panel;
consumen cuota Groq. La primera ejecución descarga el modelo y puede tardar.
Revisar la respuesta, sus fuentes y el estado: puede pedir aclaración o
intervención humana.

Los resultados quedan en **`backend/docs/parcial2/ejecuciones/<fecha-UTC>/`**:
`resultados/` contiene PDF, JSON y CSV; `parcial2_resultados.zip` reúne las salidas.
Ver la [guía de interpretación](backend/docs/parcial2/guias/RESULTADOS.md).
El PDF compara recuperación histórica; las consultas nuevas se guardan en JSON.

## 6. Después del notebook: levantar la API Django

La API expone el mismo sistema por HTTP. Para probarla, abrir **otra terminal en
la raíz del repositorio**:

```bash
source .venv/bin/activate
cd backend
python -m django --version
```

### Configurar los dos valores de Django

Generar valores distintos:

```bash
python - <<'PY'
import secrets
print('DJANGO_SECRET_KEY=' + secrets.token_urlsafe(48))
print('DJANGO_API_TOKEN=' + secrets.token_urlsafe(48))
PY
```

Copiar las dos líneas a los campos correspondientes de **`backend/.env`**.
Mantener `DJANGO_DEBUG=false` y `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`.
El token Django protege la API; el notebook no necesita ese token.

### Restaurar el índice para la API

El notebook trabaja con una copia aislada de los recursos. La API necesita su
índice en `backend/data/indexes/sections/`, que no se descarga con Git.
Desde `backend/`, ejecutar este comando: verifica las huellas del ZIP y conserva
un índice existente.

```bash
python - <<'PY'
import hashlib
import json
import zipfile
from pathlib import Path
from src.rag.index import load_index

bundle = Path('notebooks/parcial2_recursos.zip').read_bytes()
notebook = json.loads(Path('notebooks/parcial2.ipynb').read_text())
assert hashlib.sha256(bundle).hexdigest() == notebook['metadata']['parcial2']['bundle_sha256']
index = Path('data/indexes/sections')
if not index.exists():
    import io
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        manifest = json.loads(archive.read('bundle_manifest.json'))
        files = {}
        for name in ('config.json', 'records.json', 'vectors.npy'):
            member = 'backend/data/indexes/sections/' + name
            data = archive.read(member)
            assert hashlib.sha256(data).hexdigest() == manifest[member]
            files[name] = data
        index.mkdir(parents=True)
        for name, data in files.items():
            (index / name).write_bytes(data)
corpus_id, chunks, _, _ = load_index(index)
print('Índice disponible:', corpus_id, '| fragmentos:', len(chunks))
PY
```

Debe informar **70 fragmentos**. Si ya se ejecutó la carga desde el notebook,
no hace falta cargar otra vez Supabase. Si se omitió el notebook y el usuario aún
no tiene el corpus, cargarlo una vez:

```bash
python -m scripts.index_manuals --existing --output data/indexes/sections --upload
```

Comprobar las filas, autenticación, RPC y persistencia:

```bash
python -m scripts.verify_supabase --output docs/parcial2/verificaciones/supabase_local.json
```

El resultado debe incluir `rows_verified: 70`, `authenticated: true`,
`rpc_verified: true` y `persistence_new_client: true`.

### Iniciar y probar Django

Con `.venv` activo y desde `backend/`:

```bash
python manage.py check
python manage.py test api
python -m unittest discover -s test -t .
python manage.py runserver 127.0.0.1:8000
```

Dejar esa terminal abierta. No se necesita `manage.py migrate`: la aplicación
no usa una base de datos Django; los documentos están en Supabase.
Algunas pruebas utilizan evidencias locales que no se incluyen en otros clones.

Abrir [Swagger](http://127.0.0.1:8000/api/v1/docs/) y probar en este orden:

1. `GET /api/v1/health/`: debe responder HTTP 200. Comprueba el proceso, no Groq/Supabase.
2. Pulsar **Authorize** y pegar `DJANGO_API_TOKEN` de `.env`, sin escribir `Bearer`.
3. `GET /api/v1/categories/`: comprobar autenticación.
4. `POST /api/v1/rag/search/`: comprobar recuperación desde Supabase.
5. `POST /api/v1/rag/query/`: comprobar el recorrido completo con Groq.

Para los dos POST, usar **Try it out**, este JSON y después **Execute**:

```json
{"pregunta": "¿Qué debo comprobar si no puedo conectarme al Wi-Fi?"}
```

Las consultas nuevas de Swagger también consumen cuota Groq cuando se utiliza
`rag/query`. Revisar el estado, la respuesta y sus fuentes.

## Alternativa: levantar la API con Docker

Después de configurar los valores Django y restaurar el índice en el paso 6,
se puede usar Docker Engine/Desktop con Compose en lugar de `runserver`.
Desde `backend/`:

```bash
docker compose -f ../infra/compose.yaml up -d --build
docker compose -f ../infra/compose.yaml ps
```

Swagger usa la misma dirección. Ejecutar el notebook en el entorno local del
paso 5; la imagen Docker contiene la API, no Jupyter ni el ejecutable Tesseract.
Usar una sola API en el puerto 8000. Para pasar desde `runserver`, detenerlo con
**Ctrl+C** antes de iniciar Docker.

Tras cambiar `.env`, recrear el contenedor:

```bash
docker compose -f ../infra/compose.yaml up -d --force-recreate backend
```

Para detenerlo conservando las cachés:

```bash
docker compose -f ../infra/compose.yaml down
```

## Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| `No module named 'django'` | Desde `backend/`, activar `source ../.venv/bin/activate` e instalar `python -m pip install -r requirements.txt`. Docker tiene su propio entorno. |
| HTTP 401 | En Swagger usar `DJANGO_API_TOKEN`, sin prefijo `Bearer`. Reiniciar Django o recrear Docker si cambió `.env`. |
| Supabase sin filas o sin autenticación | Revisar proyecto, usuario Auth confirmado, contraseña y SQL del paso 4; cargar el corpus como indica el paso 5 o 6. |
| Falta `data/indexes/sections` | Restaurar el índice desde el ZIP siguiendo el paso 6 antes de iniciar la API. |
| No encuentra credenciales en el notebook | Iniciarlo como en el paso 5, o definir `PARCIAL2_ENV_FILE` con la ruta absoluta al `.env` antes de ejecutar. |
| Error de OCR | Comprobar Tesseract y el idioma español instalados en el sistema del notebook. |
| Puerto 8000 ocupado | Detener la API anterior; elegir `runserver` o Docker. |
| HTTP 429 de Groq | Esperar a que se libere la cuota de la cuenta y repetir la consulta. |

## Validación del laboratorio con GitHub Actions

El [workflow de reconstrucción](backend/docs/parcial2/guias/GITHUB_ACTIONS.md)
instala el entorno desde cero, restaura el corpus, ejecuta pruebas y las 18 celdas,
construye Docker y comprueba la API. Por defecto los push y PR prueban el modo sin proveedores;
la ejecución manual permite Groq y Supabase reales con cinco secretos propios.
Genera artifacts e informa por separado los pendientes académicos: una prueba
exitosa del software no equivale a una aprobación completa del laboratorio.

## Colab y documentación

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dvdm12/TI-support-RAG/blob/main/backend/notebooks/parcial2.ipynb)

En Colab se usa el mismo notebook, con los cinco secretos Groq/Supabase propios
en **Secrets**. El ZIP se descarga y verifica automáticamente, con subida manual
alternativa. La ejecución local está comprobada; Colab sigue pendiente de validación.
Ver la [guía del profesor](backend/notebooks/GUIA_PROFESOR.md).

[Índice de documentación](backend/docs/README.md) ·
[API](backend/docs/api/API.md) ·
[Docker](backend/docs/infraestructura/DOCKER.md) ·
[RAG](backend/docs/rag/RAG.md)

```text
backend/   API, componentes Python, corpus, notebook, pruebas y documentos
frontend/  Reservado para una futura aplicación web
infra/     Docker Compose y migración SQL de Supabase
```

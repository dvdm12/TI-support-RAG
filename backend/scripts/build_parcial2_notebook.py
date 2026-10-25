"""Build a readable Parcial 2 notebook and a separate, inspectable resource ZIP."""
import argparse
import hashlib
import io
import json
import textwrap
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'backend'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bundled_files():
    files = {}
    for folder, pattern in [('src', '*.py'), ('schemas', '*.py'), ('prompts', '*.md'), ('data/corpus/v2', '*')]:
        for path in sorted((BACKEND / folder).rglob(pattern)):
            if path.is_file():
                files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    names = ['requirements-parcial2.txt', 'data/indexes/sections/config.json',
        'data/indexes/sections/records.json', 'data/indexes/sections/vectors.npy',
        'cases/test_cases.json', 'cases/rag_regression.json', 'cases/rag_evidence.json',
        'docs/evaluacion/recuperacion/retrieval_metrics_20261021.json', 'docs/evaluacion/recuperacion/coverage_improvements_20261021.json',
        'docs/evaluacion/generacion/generation_tokens_20261021.json', 'docs/evaluacion/recuperacion/rrf_traces_20261025.json',
        'docs/human_review/class09_review_v1.json', 'docs/human_review/class09_review_v1.csv']
    for name in names:
        files['backend/' + name] = (BACKEND / name).read_bytes()
    for path in sorted((ROOT / 'infra/supabase/migrations').glob('*.sql')):
        files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    # Persist only explicit non-secret fields, never raw request headers or .env.
    api_path = BACKEND / 'docs/rag_runs/backend_check_20261025/phase_b_v8.json'
    original = json.loads(api_path.read_text())
    safe = {'scope': 'Saved HTTP observations, 2026-10-25; not new calls from this notebook',
            'source_sha256': sha(api_path.read_bytes()), 'cases': []}
    for row in original:
        response = row['response']
        safe['cases'].append({'id': row['id'], 'status': row['status'],
            'http_seconds': row['http_seconds'], 'expected_states': row['expected_states'],
            **{key: response.get(key) for key in ('estado', 'clasificacion', 'respuesta_documental',
                                                 'fuentes', 'tiempos_segundos')}})
    files['backend/docs/parcial2/evidencias/parcial2_saved_api.json'] = json.dumps(safe, ensure_ascii=False).encode()
    files['bundle_manifest.json'] = json.dumps({p: sha(b) for p, b in files.items()}, sort_keys=True).encode()
    return files


def payload(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path, content in sorted(files.items()):
            item = zipfile.ZipInfo(path, date_time=(2026, 10, 25, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, content)
    return stream.getvalue()


def build_notebook(raw=None):
    cells = []
    def cell(kind, source, ident):
        body = textwrap.dedent(source).strip() + '\n'
        result = dict(cell_type=kind, id=ident, metadata={}, source=body.splitlines(keepends=True))
        if kind == 'code':
            result.update(execution_count=None, outputs=[])
        cells.append(result)
    def md(source, ident): cell('markdown', source, ident)
    def code(source, ident): cell('code', source, ident)

    md('''
    # Parcial 2 · TI-support-RAG
    **Mesa de ayuda TI con clasificación, OCR y respuestas documentadas.**

    Equipo: **pendiente de registrar los nombres de los integrantes**.

    El usuario describe un incidente; el sistema clasifica la solicitud, aplica reglas
    locales, recupera evidencia y responde con citas o reconoce sus límites. Los documentos
    son **siete manuales académicos simulados**, no políticas de una organización real.

    Este notebook sigue los **12 puntos de la diapositiva 17 de Clase 09**, integra el
    primer corte y permite ejecutarse de principio a fin en Colab sin otros notebooks
    ni clonar el repositorio. Acompañarlo con **parcial2_recursos.zip**, que
    incluye código, PDF, índice y evidencias en archivos inspeccionables. El manifiesto
    y los hashes verifican su integridad. No contiene credenciales, reserva ni manual Ricoh.

    **Estado:** reproducción de desarrollo disponible; revisión humana y reserva
    pendientes. Un contrato válido o una métrica alta no demuestra fidelidad.

    **Para el profesor:** usar **Entorno de ejecución → Ejecutar todo**. Los recursos
    se descargan del repositorio público y se verifican; si no están disponibles,
    se puede subir el ZIP adjunto. Al final aparece **Panel del profesor**, con
    consulta real con Groq y recuperación en Supabase activadas desde el inicio.
    No hay que editar funciones. Para generación se usan **sus propios secretos**.
    ''', 'portada')
    md('''
    ## Preparación · decisiones de ejecución
    Abrir este notebook y subir **parcial2_recursos.zip** cuando la celda de recursos
    lo solicite. También se puede subir antes al explorador de archivos de Colab.
    En local, colocar el ZIP junto al notebook o indicar su ruta en `RESOURCE_ZIP`.
    Así el código del notebook es legible y los recursos se pueden inspeccionar
    sin decodificar Base64. Ejecutar las celdas en orden.
    El modo inicial es **`consulta_real` con `USE_SUPABASE=True`**: conecta a
    Supabase y consulta Groq. Preparar las credenciales propias antes de ejecutar todo.
    Se descarga el modelo de embeddings fijado y cada consulta puede consumir varias
    llamadas (clasificación, generación, revisión y corrección).

    **En local:** usar el kernel Python 3.12 del proyecto con dependencias instaladas
    y Tesseract disponible. Se lee `.env` en la carpeta de inicio, `backend/.env`
    desde la raíz, o `../.env` desde `backend/notebooks`, sin copiarlo al ZIP.
    Para otra ubicación, definir `PARCIAL2_ENV_FILE` antes de ejecutar las celdas.
    Las variables ya presentes en el entorno tienen prioridad.
    **En Colab:** registrar `GROQ_API_KEY`, `SUPABASE_URL`,
    `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_EMAIL` y `SUPABASE_PASSWORD` en Secrets.
    El proyecto Supabase necesita usuario Auth, la migración SQL incluida y los
    70 fragmentos cargados para ese usuario. Si faltan, preparar SQL/usuario y activar
    `ALLOW_SUPABASE_UPSERT=True` solo para la primera carga del índice académico.
    La carga está desactivada por defecto; una conexión fallida no cambia a local.

    Para reproducir sin servicios, elegir explícitamente `MODE='evidencia_guardada'`
    y `USE_SUPABASE=False`; en el panel elegir `Caso guardado` y desactivar
    `USAR_SUPABASE`. Esto muestra observaciones históricas, no consultas nuevas.
    La reserva se ejecuta fuera de este notebook, después de aprobación y congelación.
    ''', 'preparacion')
    code('''
    import os, sys, json, hashlib, io, zipfile, subprocess, tempfile, shutil, time
    from pathlib import Path
    IN_COLAB = 'google.colab' in sys.modules or 'COLAB_RELEASE_TAG' in os.environ
    MODE = 'consulta_real'  # 'evidencia_guardada' solo para reproducción sin servicios
    USE_SUPABASE = True
    LOAD_EMBEDDING_MODEL = MODE == 'consulta_real'
    RUN_OCR = True
    INSTALL_DEPENDENCIES = IN_COLAB
    # Solo para un proyecto de práctica preparado; nunca se carga por defecto.
    ALLOW_SUPABASE_UPSERT = False
    TEAM = []  # Registrar nombres reales; no inventarlos.
    QUESTION = 'El portal de documentos devuelve error 403. ¿Eso demuestra que mi cuenta está suspendida? ¿Qué debe revisar soporte?'
    IMAGE_PATH = None  # Ruta de una imagen propia; la modalidad se muestra en el punto 4.
    # Capturar el .env local antes de cambiar a la carpeta temporal del ZIP.
    if os.environ.get('PARCIAL2_ENV_FILE'):
        LOCAL_ENV_FILE = Path(os.environ['PARCIAL2_ENV_FILE']).expanduser().resolve()
    else:
        env_candidates = [Path.cwd() / '.env', Path.cwd() / 'backend/.env', Path.cwd().parent / '.env']
        LOCAL_ENV_FILE = next((p.resolve() for p in env_candidates if p.is_file()), None)
    RESOURCE_ZIP = Path(os.environ.get('PARCIAL2_RESOURCES', 'parcial2_recursos.zip')).resolve()
    RESOURCE_URL = 'https://raw.githubusercontent.com/dvdm12/TI-support-RAG/refs/heads/codex/backend-infra-ricoh-local/backend/notebooks/parcial2_recursos.zip'
    WORKSPACE = Path(os.environ.get('PARCIAL2_WORKDIR', '/content/parcial2' if IN_COLAB else tempfile.mkdtemp(prefix='parcial2-'))).resolve()
    # Resultados permanentes separados de los recursos extraídos del ZIP.
    def results_root(start, in_colab):
        if os.environ.get('PARCIAL2_OUTPUT_DIR'):
            return Path(os.environ['PARCIAL2_OUTPUT_DIR']).expanduser().resolve()
        if in_colab:
            return Path('/content/parcial2/backend/docs/parcial2')
        start = Path(start).resolve()
        candidates = [start / 'backend', start, start.parent]
        local_backend = next((p for p in candidates
                              if (p / 'src/rag').is_dir() and (p / 'requirements-parcial2.txt').is_file()),
                             start / 'backend')
        return local_backend / 'docs/parcial2'

    from datetime import datetime, timezone
    OUTPUT_ROOT = results_root(Path.cwd(), IN_COLAB)
    RUN_ID = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    RUN_DIR = OUTPUT_ROOT / 'ejecuciones' / RUN_ID
    RESULTS_ZIP = RUN_DIR / 'parcial2_resultados.zip'
    assert MODE in {'evidencia_guardada', 'consulta_real'}
    if USE_SUPABASE or ALLOW_SUPABASE_UPSERT:
        assert MODE == 'consulta_real', 'La reproducción no accede a Supabase.'
    print({'modo': MODE, 'Colab': IN_COLAB, 'equipo_registrado': bool(TEAM)})
    ''', 'configuracion')
    raw = payload(bundled_files()) if raw is None else raw
    code('''
    # El código y los datos están en archivos normales dentro del ZIP adjunto.
    BUNDLE_SHA256 = %r

    def restore_resources(raw_bundle, expected_sha256, workspace):
        if hashlib.sha256(raw_bundle).hexdigest() != expected_sha256:
            raise ValueError('El ZIP no corresponde a esta versión del notebook.')
        workspace = Path(workspace).resolve()
        with zipfile.ZipFile(io.BytesIO(raw_bundle)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError('El ZIP repite nombres de archivos.')
            manifest = json.loads(archive.read('bundle_manifest.json'))
            if set(names) != set(manifest) | {'bundle_manifest.json'}:
                raise ValueError('El contenido no coincide con el manifiesto.')
            for name, expected in manifest.items():
                if not (workspace / name).resolve().is_relative_to(workspace):
                    raise ValueError('Ruta inválida en el paquete.')
                if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                    raise ValueError('Archivo distinto del manifiesto: ' + name)
            workspace.mkdir(parents=True, exist_ok=True)
            archive.extractall(workspace)
        return manifest

    if not RESOURCE_ZIP.is_file() and IN_COLAB:
        from urllib.request import urlopen
        try:
            with urlopen(RESOURCE_URL, timeout=20) as response:
                downloaded = response.read(20_000_001)
            if len(downloaded) > 20_000_000 or hashlib.sha256(downloaded).hexdigest() != BUNDLE_SHA256:
                raise ValueError('La descarga no coincide con la versión esperada.')
            RESOURCE_ZIP.write_bytes(downloaded)
            print('ZIP descargado y hash verificado desde GitHub.')
        except Exception:
            print('Descarga automática no disponible. Puedes subir el ZIP adjunto de esta versión.')
    if RESOURCE_ZIP.is_file():
        raw_bundle = RESOURCE_ZIP.read_bytes()
    elif IN_COLAB:
        from google.colab import files
        print('Subir solamente parcial2_recursos.zip, entregado junto al notebook.')
        uploaded = files.upload()
        if len(uploaded) != 1:
            raise ValueError('Selecciona un único ZIP de recursos.')
        raw_bundle = next(iter(uploaded.values()))
        RESOURCE_ZIP.write_bytes(raw_bundle)
    else:
        raise FileNotFoundError('Coloca parcial2_recursos.zip junto al notebook o configura PARCIAL2_RESOURCES.')
    bundle_manifest = restore_resources(raw_bundle, BUNDLE_SHA256, WORKSPACE)
    BACKEND = WORKSPACE / 'backend'
    print('Integridad verificada:', len(bundle_manifest), 'archivos; SHA256:', BUNDLE_SHA256)
    print('Recursos inspeccionables en:', WORKSPACE)
    ''' % sha(raw), 'paquete')
    code('''
    # No instala dentro del entorno del proyecto al ejecutar localmente.
    if INSTALL_DEPENDENCIES:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r',
                        str(BACKEND / 'requirements-parcial2.txt')], check=True)
        if RUN_OCR:
            subprocess.run(['apt-get', 'update', '-qq'], check=True, stdout=subprocess.DEVNULL)
            subprocess.run(['apt-get', 'install', '-y', '-qq', 'tesseract-ocr',
                            'tesseract-ocr-spa', 'fonts-dejavu-core'], check=True, stdout=subprocess.DEVNULL)
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    import numpy as np
    import pandas as pd
    from IPython.display import display, Markdown
    def read_json(name):
        return json.loads((BACKEND / name).read_text(encoding='utf-8'))
    from importlib.metadata import version
    display(pd.DataFrame([{'paquete': n, 'version': version(n)} for n in
                          ['pydantic', 'numpy', 'pypdf', 'sentence-transformers', 'supabase']]))
    ''', 'instalacion')
    md('''
    ## 1. Función original y entrada del usuario
    Clasificación de solicitudes TI en siete categorías, prioridad, resumen,
    datos faltantes y necesidad de intervención humana. `QUESTION` es la entrada
    editable. Una imagen puede complementar el texto mediante OCR. Se conserva
    la clasificación original y se amplía con evidencia documental.
    ''', 'punto-1')
    code('''
    from schemas.request_v1 import SolicitudTI
    from schemas.rag_response_v1 import RespuestaRAG
    from src.validator import validate_output
    from src.decision import run_decision_contract_checks
    from src.config import MODEL, PROMPT_VERSION, PROMPT_PATH
    from src.rag.config import RAGConfig
    api_saved = read_json('docs/parcial2/evidencias/parcial2_saved_api.json')
    annotations = read_json('cases/rag_evidence.json')
    case_map = {c['id']: c for c in annotations['cases']}
    saved_case = next(c for c in api_saved['cases'] if c['id'] == 'E06')
    print('Pregunta editable:', QUESTION)
    display(pd.DataFrame([saved_case['clasificacion']]))
    print('Clasificación mostrada: ejecución HTTP guardada, no una nueva inferencia.')
    ''', 'entrada')
    md('''
    ## 2. Integración con el modelo
    Proveedor Groq; modelo `openai/gpt-oss-20b`; clasificador `system_v8` y
    generador `rag_v6`. Temperatura 0, razonamiento low, máximo 800 tokens de
    salida; entrada limitada a 1000 tokens incluyendo esquema y reserva de formato.
    El contexto de generación reserva 150 tokens para una eventual corrección.

    Los secretos se leen únicamente cuando la integración se habilita. En Colab,
    registrar los nombres en el panel de secretos y dar acceso a este notebook.
    Nunca pegar valores en celdas ni mostrarlos.
    ''', 'punto-2')
    code('''
    def load_own_secrets(names):
        if not IN_COLAB and LOCAL_ENV_FILE is not None:
            from dotenv import load_dotenv
            if not LOCAL_ENV_FILE.is_file():
                raise RuntimeError('No existe el archivo indicado en PARCIAL2_ENV_FILE.')
            load_dotenv(LOCAL_ENV_FILE, override=False)
        for name in names:
            if IN_COLAB:
                from google.colab import userdata
                try:
                    value = userdata.get(name)
                except Exception:
                    raise RuntimeError('Configura el secreto ' + name + ' en Colab.') from None
                if not value:
                    raise RuntimeError('Falta el secreto ' + name)
                os.environ[name] = value
                del value
            elif not os.environ.get(name):
                raise RuntimeError('Configura ' + name + ' en el entorno o en tu .env (PARCIAL2_ENV_FILE).')
        print('Secretos propios disponibles; valores ocultos.')
    if MODE == 'consulta_real':
        required = ['GROQ_API_KEY']
        if USE_SUPABASE:
            required += ['SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY', 'SUPABASE_EMAIL', 'SUPABASE_PASSWORD']
        load_own_secrets(required)
    else:
        print('Reproducción: no se leen secretos.')
    assert PROMPT_VERSION == 'system_v8'
    print({'modelo': MODEL, 'clasificador': PROMPT_VERSION, 'generador': RAGConfig().prompt.stem})
    display(Markdown('**Prompt documental versionado:**'))
    print(RAGConfig().prompt.read_text())
    ''', 'modelo-secretos')
    md('''
    ## 3. Salida controlada
    `SolicitudTI` valida categorías, prioridad, longitud del resumen y confianza
    numérica finita. `RespuestaRAG` exige estado documental y correspondencia
    de citas. Las reglas locales conservan prioridad de atención humana y solicitan
    aclaración con datos faltantes o confianza menor que 0,60.
    Cumplir el esquema no acredita que una afirmación sea verdadera.
    ''', 'punto-3')
    code('''
    classification = SolicitudTI.model_validate(saved_case['clasificacion'])
    answer = RespuestaRAG.model_validate(saved_case['respuesta_documental'])
    invalid = classification.model_dump()
    invalid['confianza'] = '0.9'
    assert validate_output(invalid)[0] is False
    assert len(run_decision_contract_checks()) == 4
    display(pd.DataFrame([{'contrato': 'SolicitudTI', 'campos': ', '.join(SolicitudTI.model_fields)},
                          {'contrato': 'RespuestaRAG', 'campos': ', '.join(RespuestaRAG.model_fields)}]))
    print('Rechazo de confianza textual y cuatro reglas de decisión: correctos.')
    ''', 'contratos')
    md('''
    ## 4. Modalidad integrada: imagen y OCR
    Se conserva la interfaz OCR del primer corte, con motores intercambiables
    Tesseract/EasyOCR. La demostración usa una **imagen sintética** y Tesseract;
    EasyOCR permanece en el código, pero no se instala su modelo en este recorrido.
    Se valida extensión, dimensiones, legibilidad y texto antes de combinarlo con
    la solicitud. OCR extrae caracteres; no diagnostica el incidente.
    Para usar esta imagen en el recorrido real del punto 10, asignar
    `IMAGE_PATH = demo_image_path` al final de la siguiente celda y activar
    `consulta_real` en la configuración.
    ''', 'punto-4')
    code('''
    from src.multimodal import prepare_multimodal_input
    from src.pipeline import prepare_case_input
    ocr_demo = None
    demo_image_path = None
    if RUN_OCR:
        from PIL import Image, ImageDraw, ImageFont
        if not shutil.which('tesseract'):
            raise RuntimeError('Instala Tesseract o desactiva RUN_OCR de forma explícita.')
        demo_image_path = WORKSPACE / 'ticket_sintetico.png'
        image = Image.new('RGB', (1100, 250), 'white')
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        font = ImageFont.truetype(font_path, 36) if Path(font_path).exists() else ImageFont.load_default(size=36)
        ImageDraw.Draw(image).multiline_text((35, 40), 'No puedo conectarme al Wi-Fi.\\nAparece un mensaje de error.', font=font, fill='black', spacing=25)
        image.save(demo_image_path)
        display(image)
        ocr_demo = prepare_multimodal_input('Solicitud adjunta en imagen.', demo_image_path, ocr_engine='tesseract')
        assert ocr_demo['extraction_valid'] and 'error' in ocr_demo['extracted_text'].lower()
        combined, _ = prepare_case_input({'input': 'Solicitud adjunta en imagen.'}, ocr_demo)
        print(combined)
    else:
        print('OCR desactivado explícitamente; demostración de modalidad pendiente.')
    ''', 'ocr')
    md('''
    ## 5. Seguridad y manejo de errores
    No se muestran secretos ni cuerpos arbitrarios de errores de proveedores.
    Se diferencian `ERROR_FORMATO`, `ERROR_TECNICO`, abstención documental y
    aclaración. La evidencia recuperada es dato, nunca instrucciones para el sistema.
    La falta de cobertura no se convierte en un procedimiento inventado.
    ''', 'punto-5')
    code('''
    from src.rag.citations import validate_response
    try:
        validate_response({'estado': 'respondida', 'respuesta': 'Acción inventada [F99]',
                           'citas': ['F99'], 'limitacion': ''}, {})
    except ValueError:
        print('Referencia inexistente rechazada correctamente.')
    else:
        raise AssertionError('Se aceptó una cita inexistente.')
    for ident in ['E07', 'E08', 'E09', 'E10', 'E13']:
        row = next(c for c in api_saved['cases'] if c['id'] == ident)
        assert row['respuesta_documental']['estado'] in row['expected_states']
        print(ident, row['respuesta_documental']['estado'], row['respuesta_documental']['respuesta'])
    ''', 'seguridad')
    md('''
    ## 6. Pruebas, registros y bitácora
    Los 13 casos conocidos incluyen solicitudes normales, ambiguas, incompletas,
    maliciosas y fuera de alcance. Esta celda comprueba observaciones HTTP guardadas
    del 25-10-2026: no equivale a volver a consultar el servicio. Los tiempos son
    históricos y los tokens no disponibles se conservan como desconocidos.
    ''', 'punto-6')
    code('''
    behavior_rows = []
    for row in api_saved['cases']:
        ok = row['status'] == 200 and row['respuesta_documental']['estado'] in row['expected_states']
        assert ok
        behavior_rows.append({'caso': row['id'], 'tipo': case_map[row['id']]['type'],
            'estado_documental': row['respuesta_documental']['estado'], 'cumple_expectativa': ok,
            'tiempo_HTTP_guardado_s': row['http_seconds']})
    display(pd.DataFrame(behavior_rows))
    print('13/13 observaciones guardadas conformes; no son una revisión humana.')
    ''', 'regresion')
    md('''
    ## 7. Corpus documentado: extracción y limpieza
    Siete PDF simulados versión 2.0, compartibles como muestra académica, con hash,
    categoría, sección y páginas. Son hardware, software, redes, cuentas, seguridad,
    acceso y otros. Se extrae texto nativo, se excluyen pies conocidos y se normalizan
    espacios conservando párrafos. Un PDF sin texto requiere OCR revisado.
    Solo se admiten archivos inventariados: este perfil no es un extractor universal.
    ''', 'punto-7')
    code('''
    from src.rag.ingestion import load_corpus
    manifest_path = BACKEND / 'data/corpus/v2/manifest.json'
    manifest = read_json('data/corpus/v2/manifest.json')
    sections = load_corpus(manifest_path)
    display(pd.DataFrame([{k: d[k] for k in ['document_id', 'title', 'version', 'pages', 'simulated']}
                          for d in manifest['documents']]))
    print('PDF verificados:', len(manifest['documents']), '| secciones:', len(sections))
    print(sections[0].section, '\\n', sections[0].text)
    ''', 'corpus')
    md('''
    ## 8. Fragmentación y metadatos
    Configuración vigente: estructura por sección/párrafo, hasta 420 caracteres y
    80 tokens reales, **solapamiento 0**, encabezado y procedencia en cada fragmento.
    Se evita truncamiento silencioso frente al límite de 128 tokens del modelo.
    La alternativa `overlap` está disponible en el código; no se atribuye solapamiento
    a la configuración vigente. Se restaura el índice para no recalcular vectores
    en cada consulta. La reconstrucción con tokenizer real es opcional y verificable.
    ''', 'punto-8')
    code('''
    from src.rag.index import load_index, save_index
    from src.rag.embeddings import SentenceEmbedder
    from src.rag.chunking import fragment_sections
    corpus_id, chunks, vectors, cfg = load_index(BACKEND / 'data/indexes/sections')
    assert len(chunks) == 70 and vectors.shape == (70, 384)
    display(pd.DataFrame([cfg.model_dump()]))
    display(pd.DataFrame([{'chunk_id': c.chunk_id, 'seccion': c.section, 'paginas': c.pages,
                          'tokens': c.tokens, 'texto': c.text} for c in chunks[:3]]))
    embedder = None
    if LOAD_EMBEDDING_MODEL:
        embedder = SentenceEmbedder(cfg.revision)
        load_index(BACKEND / 'data/indexes/sections', embedder)
        rebuilt_chunks = fragment_sections(sections, embedder, cfg)
        assert [c.model_dump() for c in rebuilt_chunks] == [c.model_dump() for c in chunks]
        print('Fragmentación reproducida con tokenizer fijado; muestras de vectores verificadas.')
    else:
        print('Índice íntegro restaurado; reconstrucción del tokenizer/modelo no ejecutada.')
    ''', 'fragmentacion')
    md('''
    ## 9. Embeddings y Supabase
    Embedding multilingüe de 384 dimensiones, normalizado, similitud coseno y revisión
    exacta guardada. La copia local incluye `records.json`, `vectors.npy`, `config.json`;
    la huella de construcción comprueba su asociación.

    Supabase usa `clase08_fragmentos` y RPC `clase08_buscar_fragmentos`: los nombres
    internos conservan compatibilidad aunque la entrega sea Parcial 2. RLS delimita
    `owner_id`; autenticación con usuario y clave publicable, nunca `service_role`.
    El adaptador local **no demuestra RLS** y no sustituye silenciosamente un fallo remoto.

    Para reconstruir en un proyecto de práctica: crear el usuario autorizado, ejecutar
    el SQL incluido en SQL Editor, configurar secretos y habilitar conexión. El upsert
    requiere su bandera explícita. No borra filas ni restaura Auth: **no es backup completo**.
    ''', 'punto-9')
    code('''
    from src.rag.repository import LocalRepository, SupabaseRepository
    repository = LocalRepository()
    repository.upsert(corpus_id, chunks, vectors, cfg)
    sql_paths = sorted((WORKSPACE / 'infra/supabase/migrations').glob('*.sql'))
    print('Migración incluida:', sql_paths[0].name)
    print('Dimensión:', vectors.shape[1], '| normas:', np.linalg.norm(vectors, axis=1).min(), np.linalg.norm(vectors, axis=1).max())
    if USE_SUPABASE:
        repository = SupabaseRepository.connect()
        if ALLOW_SUPABASE_UPSERT:
            repository.upsert(corpus_id, chunks, vectors, cfg)
        visible = repository.lexical_candidates(corpus_id, cfg)
        assert {c.chunk_id for c in visible} == {c.chunk_id for c in chunks}, 'Inventario remoto distinto.'
        assert all(c.content == next(x.text for x in chunks if x.chunk_id == c.chunk_id) for c in visible)
        assert embedder is not None
        remote_check = repository.search(corpus_id, embedder.encode([QUESTION])[0], cfg, 3)
        print('Conexión Auth, inventario de 70 y RPC comprobados en esta ejecución.')
    else:
        print('Modo local explícito: conexión Supabase no ejecutada en esta sesión.')
    ''', 'persistencia')
    md('''
    ## 10. Recuperación y respuesta con fuentes
    La pregunta produce un vector; se recuperan hasta diez candidatos semánticos
    y diez BM25. RRF fusiona posiciones; se filtra aplicabilidad y se toman tres.
    El catálogo conserva documento, sección, páginas y hash. Generación, validación
    de citas, revisión de respaldo y decisión local completan el recorrido.

    En reproducción se muestra la respuesta guardada **de la misma pregunta**;
    cambiar la pregunta exige `consulta_real`. La consulta real conserva OCR y
    clasificación mediante `run_rag_case`; los tokens disponibles pertenecen a
    etapas concretas y no se presentan como total si hay llamadas sin contabilizar.
    ''', 'punto-10')
    code('''
    from src.rag.models import Candidate
    from src.rag.retrieval import Retriever, select_ranked_candidates
    from src.rag.lexical import rank
    from src.rag.context import build_context
    from src.rag.pipeline import run_rag_case
    from src.rag.token_comparison import response_format
    from src.groq_client import build_payload
    from src.token_budget import input_budget
    base = read_json('docs/evaluacion/recuperacion/retrieval_metrics_20261021.json')
    inventory = {c.chunk_id: Candidate(chunk_id=c.chunk_id, content=c.text,
                 metadata=c.model_dump(exclude={'chunk_id','text'}), similitud=0) for c in chunks}
    live_result = None
    if MODE == 'consulta_real':
        retriever = Retriever(repository, embedder, corpus_id, cfg, k=3)
        live_result = run_rag_case({'id': 'PARCIAL2-USUARIO', 'tipo': 'usuario', 'input': QUESTION},
                                  retriever, image_path=IMAGE_PATH, ocr_engine='tesseract')
        print('Estado:', live_result['state'], '| etapa de fallo:', live_result['failure_stage'])
        display(live_result['classification'])
        display(live_result['documentary_output'])
        display(pd.DataFrame(live_result['rag']['candidates']))
        print('Contexto enviado:', live_result['user_content_sent'])
        print('Tiempos:', live_result['rag']['timings'])
        print('Usage de la generación registrada (no total pipeline):', live_result.get('usage'))
    else:
        saved_question = next((c for c in base['cases'] if c['question'] == QUESTION), None)
        if saved_question is None:
            raise ValueError('No hay respuesta guardada para esta pregunta. Activa consulta_real.')
        sem = [inventory[r['chunk_id']].model_copy(update={'similitud': r['cosine']}) for r in saved_question['semantic_ranking']]
        selected, selection_trace = select_ranked_candidates(QUESTION, sem, rank(QUESTION, list(inventory.values()), 10))
        fits = lambda text: input_budget(build_payload(RAGConfig().prompt.read_text(), text, response_format=response_format()))['total_tokens'] <= 850
        context = build_context(QUESTION, selected, request_fits=fits)
        display(pd.DataFrame(selection_trace['rrf_union']))
        print('Contexto recalculado localmente:', context['user_content'])
        saved_api = next(c for c in api_saved['cases'] if c['id'] == saved_question['id'])
        display(saved_api['clasificacion'])
        display(saved_api['respuesta_documental'])
        display(pd.DataFrame(saved_api['fuentes']))
        print('Respuesta y clasificación HTTP históricas; su contexto original puede incluir políticas/categoría.')
    ''', 'recorrido')
    md('''
    ## 11. Mejora justificada: semántica frente a híbrida
    BM25 recupera coincidencias léxicas; RRF combina **posiciones**, no suma cosenos
    y puntajes BM25. La selección vigente pondera semántica 1 y léxico 2, normaliza
    términos técnicos y filtra pertinencia antes de Top-3. No se añadió reranker.

    El ejemplo de clase usa pesos 1/1 y c=60: A,C,B,D. Las trazas T7 explican la
    configuración 1/2 real. Las comparaciones históricas y la generación A/B tienen
    cortes distintos: la generación usa `rag_v6` igual en ambas variantes y política
    de pertinencia; no se presenta como comparación controlada del pipeline completo.
    ''', 'punto-11')
    code('''
    from src.rag.retrieval import fuse_rankings
    def toy(ids):
        return [Candidate(chunk_id=x, content=x, metadata={}, similitud=0) for x in ids]
    example = fuse_rankings(toy(['A','B','C']), toy(['C','A','D']), semantic_weight=1, lexical_weight=1)
    assert [r['chunk_id'] for r in example] == ['A','C','B','D']
    assert [round(r['rrf_score'],6) for r in example] == [.032522,.032266,.016129,.015873]
    display(pd.DataFrame(example))
    traces = read_json('docs/evaluacion/recuperacion/rrf_traces_20261025.json')
    for case in traces['cases']:
        sem = [inventory[r['chunk_id']].model_copy(update={'similitud': r['cosine']}) for r in case['semantic_ranking']]
        selected, reproduced = select_ranked_candidates(case['question'], sem, rank(case['question'], list(inventory.values()), 10))
        assert reproduced['selected_ids'] == case['selected_ids']
    print('13/13 selecciones híbridas v2 reproducidas localmente, sin categorías esperadas.')
    display(pd.DataFrame(next(c for c in traces['cases'] if c['id']=='E06')['rrf_union']))
    # Generación A/B efectivamente comparable: mismo rag_v6, modelo y parámetros.
    paired_generation = read_json('docs/evaluacion/generacion/generation_tokens_20261021.json')
    assert paired_generation['protocol']['prompt_version'] == 'rag_v6'
    assert paired_generation['protocol']['temperature'] == 0
    assert paired_generation['protocol']['classifier_run'] is False
    for pair in paired_generation['cases']:
        for variant in pair['variants'].values():
            observation = variant['observations'][0]
            validate_response(observation['documentary_output'], variant['catalog'])
    pair = next(c for c in paired_generation['cases'] if c['id'] == 'E06')
    print('Comparación generativa guardada, pregunta común:', pair['question'])
    print('Mismo modelo:', paired_generation['protocol']['model'], '| mismo prompt: rag_v6')
    for name, variant in pair['variants'].items():
        print(name, variant['observations'][0]['documentary_output']['respuesta'])
        display(pd.DataFrame([{'etiqueta': label, 'chunk_id': source['chunk_id'],
                              'pasaje_completo': source['content']} for label, source in variant['catalog'].items()]))
    ''', 'mejora')
    md('''
    ## 12. Evaluación integrada y conclusión
    Desarrollo: 13 casos, siete documentales y seis de comportamiento; 35 unidades
    anotadas por el agente y pendientes de validación humana. Precision@3 divide
    relevantes seleccionados entre 3; Recall@3, entre relevantes anotados; Hit@3
    indica al menos un acierto; MRR promedia el inverso del primer rango relevante.
    Cobertura cuenta unidades presentes, además de comprobar preguntas completas.

    Se distinguen candidatos y contexto. Las métricas siguientes corresponden a
    desarrollo conocido; no prueban generalización ni calidad generativa. No se
    abren los 12 candidatos de reserva ni se inventa una decisión aprobada.
    ''', 'punto-12')
    code('''
    from src.rag.retrieval_metrics import metrics, coverage
    improved = read_json('docs/evaluacion/recuperacion/coverage_improvements_20261021.json')
    evaluation_rows = []
    for label, report, variant in [('Semántica A histórica', base, 'A_semantic'),
                                  ('Híbrida v1 histórica', base, 'B_hybrid_rrf'),
                                  ('Híbrida v2', improved, 'Después: híbrida v2')]:
        measurements = []
        context_coverages = []
        for case in report['cases']:
            if case['retrieval_evaluable'] and not case['error']:
                units = case_map[case['id']]['required_information_units']
                observed = case['variants'][variant]
                measurements.append(metrics(observed['selected_ids'], units))
                context_coverages.append(coverage(observed['context_ids'], units))
        row = {'variante': label, 'preguntas_documentales': len(measurements)}
        row.update({key: float(np.mean([m[key] for m in measurements])) for key in ['precision','recall','hit','rr','coverage']})
        row['cobertura_contexto'] = float(np.mean(context_coverages))
        evaluation_rows.append(row)
    retrieval_table = pd.DataFrame(evaluation_rows)
    display(retrieval_table)
    assert evaluation_rows[-1]['recall'] == 1 and evaluation_rows[-1]['cobertura_contexto'] == 1
    token_report = read_json('docs/evaluacion/generacion/generation_tokens_20261021.json')
    token_rows = [{'variante': name, 'pares': value['paired_usage']['total_tokens']['n'],
                   'tokens_generacion': value['paired_usage']['total_tokens']['sum']}
                  for name,value in token_report['summary']['variants'].items()]
    display(pd.DataFrame(token_rows))
    print('Tokens reales guardados: solo generación directa, sin clasificación/revisión/corrección.')
    print('Mediana HTTP guardada:', float(np.median([r['http_seconds'] for r in api_saved['cases']])), 's')
    ''', 'metricas')
    md('''
    ### Revisión humana, fallos y decisión pendiente
    T1 aporta 27 respuestas con pasajes completos. Las casillas de corrección,
    fidelidad, respaldo y utilidad permanecen `null` hasta revisión por personas.
    Al menos tres casos requieren dos integrantes independientes y adjudicación.
    La corrección de referencias por software no sustituye esta evaluación.

    La híbrida v2 mejora cobertura de desarrollo, pero todavía no se declara ganadora
    definitiva: faltan revisión humana, aprobación/congelación y evaluación de reserva.
    La configuración de producción se conserva provisionalmente; no se ajustará con
    resultados de reserva. Tiempos y tokens se comparan solo con alcance equivalente.
    ''', 'revision-conclusion')
    code('''
    from schemas.human_review_v1 import ReviewSheet
    review = ReviewSheet.model_validate(read_json('docs/human_review/class09_review_v1.json'))
    display(pd.DataFrame([{'caso': r.case_id, 'variante': r.variant,
                          **r.human_review.model_dump(mode='json')} for r in review.rows]))
    # Fallo observable sin atribuir al agente una revisión humana:
    e05 = next(c for c in api_saved['cases'] if c['id'] == 'E05')
    print('E05 - pregunta:', case_map['E05']['question'])
    print('Respuesta HTTP guardada:', e05['respuesta_documental']['respuesta'])
    print('Unidades esperadas:', [u['statement'] for u in case_map['E05']['required_information_units']])
    print('Comparar manualmente omisiones: respaldo de una respuesta no implica completitud.')
    print({'revision_humana': review.status, 'reserva': 'sin abrir', 'decision_final': 'pendiente'})
    ''', 'revision')
    md('''
    ### Exportación y bitácora reproducible
    Se exportan métricas de recuperación recalculadas en JSON, CSV y PDF con los
    denominadores, y una traza de sesión permitida por campos explícitos. El reporte
    existente de tokens se conserva como evidencia histórica. No se exportan secretos
    ni encabezados HTTP. En local se guardan en
    `backend/docs/parcial2/ejecuciones/<fecha-UTC>/resultados/` y su ZIP al lado.
    Cada ejecución tiene su carpeta; repetir el panel actualiza su interacción y ZIP.
    `PARCIAL2_OUTPUT_DIR` permite elegir otra raíz. En Colab la raíz es
    `/content/parcial2/backend/docs/parcial2/`; descargar el ZIP antes de cerrar la sesión.
    En Colab limpiar salidas antes de publicar si se ensayan datos privados propios.
    ''', 'exportacion-texto')
    code('''
    from datetime import datetime, timezone
    from src.pdf_report import PDFReport
    from src.rag.complete_coverage import details
    export_dir = RUN_DIR / 'resultados'
    export_dir.mkdir(parents=True, exist_ok=True)
    retrieval_table.to_csv(export_dir / 'metricas_recuperacion.csv', index=False)
    (export_dir / 'metricas_recuperacion.json').write_text(json.dumps({
        'scope': 'Recalculated from saved known development selections; no new retrieval measurements',
        'rows': evaluation_rows, 'human_review_status': review.status, 'reserve_executed': False}, ensure_ascii=False, indent=2))
    # El formato PDF existente requiere el informe completo; deriva unidades completas.
    from copy import deepcopy
    pdf_report = deepcopy(improved)
    for case in pdf_report['cases']:
        units = case_map[case['id']]['required_information_units']
        for variant in case['variants'].values():
            variant['coverage_completeness'] = {'top_3': details(variant['selected_ids'], units),
                                               'context': details(variant['context_ids'], units)}
    source_report = export_dir / 'comparacion_hibrida_desarrollo.json'
    source_report.write_text(json.dumps(pdf_report, ensure_ascii=False, indent=2))
    PDFReport(export_dir / 'comparacion_hibrida_desarrollo.pdf').generate_retrieval_metrics(pdf_report, source_json=source_report)
    pd.DataFrame([{'case': c['id'], 'variant': name,
                   **v['metrics_at_3'], 'context_coverage': v['context_coverage']}
                  for c in improved['cases'] if c['retrieval_evaluable']
                  for name,v in c['variants'].items()]).to_csv(export_dir / 'comparacion_hibrida_desarrollo.csv', index=False)
    session_trace = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'mode': MODE,
        'bundle_sha256': BUNDLE_SHA256, 'corpus_id': corpus_id, 'config': cfg.model_dump(),
        'classifier_prompt': PROMPT_VERSION, 'generator_prompt': RAGConfig().prompt.stem,
        'team': TEAM, 'ocr_executed': ocr_demo is not None,
        'human_review': review.status, 'reserve_executed': False}
    if live_result is not None:
        session_trace['query'] = {key: live_result.get(key) for key in
            ['input','state','classification','documentary_output','usage','failure_stage','latency_seconds']}
        session_trace['query']['rag'] = {key: live_result['rag'].get(key) for key in
            ['candidates','catalog','omitted','timings','semantic_support_review','safe_fallback']}
        session_trace['query']['context'] = live_result.get('user_content_sent')
    (export_dir / 'traza_sesion.json').write_text(json.dumps(session_trace, ensure_ascii=False, indent=2))
    shutil.make_archive(str(RESULTS_ZIP.with_suffix('')), 'zip', export_dir)
    print('Carpeta de resultados:', export_dir)
    print('ZIP de resultados:', RESULTS_ZIP)
    print('Resultados disponibles:', sorted(p.name for p in export_dir.iterdir()))
    if IN_COLAB:
        from google.colab import files
        print('Para descargar: files.download(str(RESULTS_ZIP))')
    ''', 'exportacion')
    md('''
    ## Panel del profesor
    El panel inicia en **Consultar con Groq** y **USAR_SUPABASE=True**.
    Ejecutarlo realiza una consulta nueva con las credenciales propias configuradas.
    Después de ejecutar el notebook, cambiar la pregunta y ejecutar esta celda de
    nuevo para cada interacción. La consulta del punto 10 y la del panel son dos
    ejecuciones reales independientes y ambas consumen cuota.

    | Acción | Qué hace | Credenciales |
    |---|---|---|
    | Caso guardado | Muestra pregunta, respuesta y pasajes de E01-E13 | Ninguna |
    | Buscar en corpus | Busca una pregunta nueva por BM25; híbrida opcional | Ninguna |
    | Consultar con Groq | Ejecuta clasificación, recuperación, generación y revisión | GROQ_API_KEY propia |

    La búsqueda BM25 funciona sin descargar un modelo ni usar cuota Groq. La
    búsqueda híbrida descarga la revisión fijada del embedder en su primera ejecución.
    La búsqueda sola muestra evidencia, **no genera una respuesta**.

    Para el recorrido remoto de Clase 08, `USAR_SUPABASE` ya está habilitado.
    Crear el esquema SQL incluido en un proyecto propio y registrar los cuatro
    secretos Supabase además de Groq. Si ese usuario todavía no tiene el corpus, habilitar
    `CARGAR_CORPUS_PROPIO` para cargar únicamente su índice académico. Se verifican
    inventario y persistencia desde un segundo cliente **sin segunda carga**.
    No se comparten credenciales ni se concede acceso al corpus del equipo por nombre.
    La carga es una operación explícita sobre el proyecto del profesor.

    Cada interacción actualiza `interaccion_profesor.json` y el ZIP dentro de
    la carpeta permanente de la ejecución (`RUN_DIR`). Son consultas exploratorias, no una ejecución de reserva.
    ''', 'panel-profesor-texto')
    code('''
    #@title Panel del profesor · cambiar campos y ejecutar esta celda
    ACCION = "Consultar con Groq" #@param ["Caso guardado", "Buscar en corpus", "Consultar con Groq"]
    CASO = "E06" #@param ["E01","E02","E03","E04","E05","E06","E07","E08","E09","E10","E11","E12","E13"]
    PREGUNTA = "¿Qué debo comprobar si no puedo conectarme al Wi-Fi?" #@param {type:"string"}
    BUSQUEDA_HIBRIDA = False #@param {type:"boolean"}
    USAR_SUPABASE = True #@param {type:"boolean"}
    CARGAR_CORPUS_PROPIO = False #@param {type:"boolean"}
    DESCARGAR_RESULTADOS = False #@param {type:"boolean"}

    from src.parcial2_demo import ProfessorDemo
    if 'professor_demo' not in globals():
        professor_demo = ProfessorDemo(BACKEND)
    try:
        if CARGAR_CORPUS_PROPIO and (not USAR_SUPABASE or ACCION != 'Consultar con Groq'):
            raise ValueError('La carga requiere elegir Consultar con Groq y habilitar Supabase.')
        if ACCION == 'Caso guardado':
            interaction = professor_demo.saved_case(CASO)
        elif ACCION == 'Buscar en corpus':
            interaction = professor_demo.search(PREGUNTA, hybrid=BUSQUEDA_HIBRIDA)
        elif ACCION == 'Consultar con Groq':
            professor_demo.validate_question(PREGUNTA)
            names = ['GROQ_API_KEY']
            if USAR_SUPABASE:
                names += ['SUPABASE_URL','SUPABASE_PUBLISHABLE_KEY','SUPABASE_EMAIL','SUPABASE_PASSWORD']
            load_own_secrets(names)
            if USAR_SUPABASE:
                display(professor_demo.prepare_supabase(PREGUNTA, upload=CARGAR_CORPUS_PROPIO))
            interaction = professor_demo.query(PREGUNTA, use_supabase=USAR_SUPABASE)
        else:
            raise ValueError('Selecciona una acción del formulario.')
        print('Modo:', interaction['mode'])
        print('Pregunta:', interaction['question'])
        if interaction.get('response') is not None:
            display(interaction['response'])
        if interaction.get('classification') is not None:
            display(interaction['classification'])
        if interaction.get('candidates'):
            display(pd.DataFrame(interaction['candidates']))
        if interaction.get('sources'):
            display(interaction['sources'])
        if interaction.get('context'):
            print('Contexto:', interaction['context'])
        if interaction.get('failure_stage'):
            print('Fallo técnico en:', interaction['failure_stage'])
        (export_dir / 'interaccion_profesor.json').write_text(json.dumps(interaction, ensure_ascii=False, indent=2))
        shutil.make_archive(str(RESULTS_ZIP.with_suffix('')), 'zip', export_dir)
        if DESCARGAR_RESULTADOS and IN_COLAB:
            from google.colab import files
            files.download(str(RESULTS_ZIP))
    except Exception as error:
        print('Operación no completada:', type(error).__name__)
        print('Comprueba pregunta, secretos propios, SQL, corpus, cuota y conexión. No se muestra el cuerpo del error.')
    ''', 'panel-profesor')
    md('''
    ### Lista de cierre del Parcial 2
    - [x] Doce puntos integrados; corpus, contratos, OCR, recuperación y trazas disponibles.
    - [x] Reproducción de evidencias separada de consultas nuevas y métricas recalculadas.
    - [ ] Registrar nombres del equipo y completar revisión humana T2/T3.
    - [ ] Aprobar reserva, decidir y congelar antes de una única evaluación T4-T6.
    - [ ] Incorporar resultados finales, decisión, bitácora y presentación PDF T8/T10/T11.
    - [ ] Ejecutar este archivo en una sesión nueva de Colab; verificar conexión autorizada
      a Supabase y recorrido real con Groq. Una ejecución local no acredita Colab.

    **Fuentes docentes:** Clase 09, diapositivas 6-17 (en particular 16 y 17).
    **Evidencias del proyecto:** los JSON con hashes incluidos en el paquete.
    Ricoh se conserva en el repositorio como regresión del extractor y queda fuera
    del corpus de esta entrega. No hay métricas de reserva ni revisión humana simuladas.
    ''', 'cierre')
    return dict(nbformat=4, nbformat_minor=5, metadata={
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python', 'version': '3.12'},
        'colab': {'name': 'parcial2.ipynb', 'provenance': []},
        'parcial2': {'bundle_sha256': sha(raw), 'reference': 'Clase 09, diapositiva 17',
                     'resources_file': 'parcial2_recursos.zip',
                     'human_review_completed': False, 'reserve_executed': False}}, cells=cells)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BACKEND / 'notebooks/parcial2.ipynb')
    args = parser.parse_args()
    raw = payload(bundled_files())
    notebook = build_notebook(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    resource_path = args.output.parent / 'parcial2_recursos.zip'
    resource_path.write_bytes(raw)
    args.output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n')
    print(f"Notebook Parcial 2: {len(notebook['cells'])} celdas. {args.output}")
    print(f"Recursos: {resource_path} | SHA256: {sha(raw)}")


if __name__ == '__main__':
    main()

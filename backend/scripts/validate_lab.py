"""Rebuild checks for Actions. Reports technical evidence, never human approval."""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import queue
import sys
import time
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SECRETS = ('GROQ_API_KEY', 'SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY',
                    'SUPABASE_EMAIL', 'SUPABASE_PASSWORD')


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def read_json(path):
    return json.loads(Path(path).read_text())


def prepare(root=ROOT):
    """Restore only the academic index; verify the whole bundle before writing."""
    notebook = read_json(root / 'notebooks/parcial2.ipynb')
    raw = (root / 'notebooks/parcial2_recursos.zip').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != notebook['metadata']['parcial2']['bundle_sha256']:
        raise ValueError('Notebook y ZIP tienen huellas distintas.')
    cells = {c['id']: c for c in notebook['cells']}
    assignment = next(n for n in ast.parse(''.join(cells['paquete']['source'])).body
                      if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'BUNDLE_SHA256' for t in n.targets))
    if ast.literal_eval(assignment.value) != digest:
        raise ValueError('La celda de restauración declara otro ZIP.')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read('bundle_manifest.json'))
        if len(names) != len(set(names)) or set(names) != set(manifest) | {'bundle_manifest.json'}:
            raise ValueError('Manifiesto ZIP inválido.')
        for name, expected in manifest.items():
            path = Path(name)
            if path.is_absolute() or '..' in path.parts or any(p.startswith('.env') or p in {'.agents', '.git', '.aws'} for p in path.parts):
                raise ValueError('Ruta no permitida en el ZIP.')
            if 'rag_reserve' in name or hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError('Recurso reservado o huella incorrecta.')
            if name.startswith(('backend/src/', 'backend/schemas/', 'backend/prompts/')):
                local = root / path.relative_to('backend')
                if not local.is_file() or local.read_bytes() != archive.read(name):
                    raise ValueError('El ZIP no coincide con el código del checkout: ' + name)
        # Also detect new source modules omitted from a stale ZIP.
        for folder, pattern in [('src', '*.py'), ('schemas', '*.py'), ('prompts', '*.md')]:
            for path in (root / folder).rglob(pattern):
                if 'backend/' + path.relative_to(root).as_posix() not in manifest:
                    raise ValueError('El ZIP omite código del checkout.')
        files = {name: archive.read('backend/data/indexes/sections/' + name)
                 for name in ('config.json', 'records.json', 'vectors.npy')}
    index = root / 'data/indexes/sections'
    if index.exists() and any(index.iterdir()):
        if any(not (index / n).is_file() or (index / n).read_bytes() != data for n, data in files.items()):
            raise ValueError('No se sobrescribe un índice local distinto del paquete.')
    index.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (index / name).write_bytes(data)
    from src.rag.index import load_index
    corpus, chunks, vectors, _ = load_index(index)
    if len(chunks) != 70 or vectors.shape != (70, 384):
        raise ValueError('Índice académico inesperado.')
    if any('punto-' + str(i) not in cells for i in range(1, 13)):
        raise ValueError('Falta un apartado de Clase 09.')
    return dict(passed=True, bundle_sha256=digest, files_verified=len(manifest),
                corpus_id=corpus, chunks=len(chunks), notebook_sections=12)


def unit_checks():
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'test'), top_level_dir=str(ROOT))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    # Original HTTP/Ricoh traces are deliberately local and outside the delivery.
    # Record those exact omissions; any new unexpected skip fails the check.
    expected_skips = {
        'test.test_class09_review.Class09ReviewTests.test_build_matches_saved_observations_and_full_source_text',
        'test.test_extraction_contracts.ExtractionContractTests.test_current_ricoh_extraction_passes_without_reserialization',
        'test.test_extraction_validation.ExtractionValidationTests.test_current_ricoh_report_and_units_keep_baseline',
    }
    unexpected = [t.id() for t, _ in result.skipped if t.id() not in expected_skips]
    return dict(passed=result.wasSuccessful() and not unexpected, tests=result.testsRun,
                failures=len(result.failures), errors=len(result.errors),
                skipped=[{'test': t.id(), 'reason': reason} for t, reason in result.skipped],
                unexpected_skips=unexpected)


def execute_notebook(output, live=False):
    from jupyter_client import KernelManager
    if live:
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
    if live and any(not os.environ.get(n) for n in REQUIRED_SECRETS):
        raise ValueError('Faltan secretos de Groq/Supabase para la ejecución real.')
    nb = read_json(ROOT / 'notebooks/parcial2.ipynb')
    output = output.resolve()
    env = dict(os.environ, PARCIAL2_OUTPUT_DIR=str(output / 'exports'),
               PARCIAL2_WORKDIR=str(output / 'workspace'),
               PARCIAL2_ENV_FILE=str(ROOT / '.env'))
    km = KernelManager(kernel_name='python3')
    km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
    km.start_kernel(cwd=str(ROOT / 'notebooks'), env=env)
    client = km.client()
    client.start_channels()
    executed = []

    def execute(source):
        ident = client.execute(source, store_history=False)
        start = time.monotonic()
        streams = []
        while True:
            if time.monotonic() - start > 600:
                raise TimeoutError('Celda superior a diez minutos.')
            try:
                message = client.get_iopub_msg(timeout=1)
            except queue.Empty:
                continue
            if message['parent_header'].get('msg_id') != ident:
                continue
            kind, content = message['header']['msg_type'], message['content']
            if kind == 'error':
                # Do not print provider bodies or notebook tracebacks.
                raise RuntimeError('Fallo de celda: ' + content['ename'])
            if kind == 'stream':
                streams.append(content['text'])
            if kind == 'status' and content['execution_state'] == 'idle':
                return ''.join(streams)

    try:
        client.wait_for_ready(timeout=90)
        for cell in nb['cells']:
            if cell['cell_type'] != 'code':
                continue
            source = ''.join(cell['source'])
            if not live:
                if cell['id'] == 'configuracion':
                    source = source.replace("MODE = 'consulta_real'", "MODE = 'evidencia_guardada'").replace('USE_SUPABASE = True', 'USE_SUPABASE = False')
                elif cell['id'] == 'panel-profesor':
                    source = source.replace('ACCION = "Consultar con Groq"', 'ACCION = "Caso guardado"').replace('USAR_SUPABASE = True', 'USAR_SUPABASE = False')
            try:
                execute(source)
            except Exception as error:
                error.cell_id = cell['id']
                raise
            executed.append(cell['id'])
        # A panel catches exceptions internally; absence of a cell error is insufficient.
        checks = execute("""print('LAB_CHECKS:' + json.dumps({
            'ocr': ocr_demo is not None,
            'rows': len(chunks),
            'mode': MODE,
            'point10_state': live_result['state'] if live_result else None,
            'point10_failure': live_result['failure_stage'] if live_result else None,
            'point10_remote': isinstance(repository, SupabaseRepository),
            'panel_mode': interaction['mode'],
            'panel_state': interaction.get('state'),
            'panel_failure': interaction.get('failure_stage'),
            'panel_remote': interaction.get('backend') == 'supabase',
            'persistence': (interaction.get('supabase_check') or {}).get('persistence_new_client', False),
            'uploads_disabled': not ALLOW_SUPABASE_UPSERT and not CARGAR_CORPUS_PROPIO,
            'exports': all((export_dir / n).is_file() for n in ['metricas_recuperacion.json',
                'metricas_recuperacion.csv', 'comparacion_hibrida_desarrollo.pdf', 'interaccion_profesor.json']),
            'zip': RESULTS_ZIP.is_file()
        }))""")
        values = [json.loads(line[len('LAB_CHECKS:'):]) for line in checks.splitlines() if line.startswith('LAB_CHECKS:')]
        if len(values) != 1:
            raise ValueError('No se obtuvo la verificación de resultados.')
        data = values[0]
        ok = len(executed) == 18 and data['ocr'] and data['rows'] == 70 and data['exports'] and data['zip'] and data['uploads_disabled']
        if live:
            ok = ok and data['point10_remote'] and data['panel_remote'] and data['persistence']
            ok = ok and data['point10_state'] in {'OK_VALIDADO', 'OK_REQUIERE_HUMANO', 'OK_PIDE_ACLARACION'}
            ok = ok and data['panel_state'] in {'OK_VALIDADO', 'OK_REQUIERE_HUMANO', 'OK_PIDE_ACLARACION'}
            ok = ok and data['point10_failure'] is None and data['panel_failure'] is None
        else:
            ok = ok and data['mode'] == 'evidencia_guardada' and data['panel_mode'] == 'saved_observation'
        return dict(passed=bool(ok), live=live, executed_cells=executed, checks=data,
                    source_sha256=hashlib.sha256((ROOT / 'notebooks/parcial2.ipynb').read_bytes()).hexdigest(),
                    offline_test_overrides=not live)
    finally:
        client.stop_channels()
        km.shutdown_kernel(now=True)
        # Extracted resources are inputs, not CI evidence; only exports are uploaded.
        import shutil
        shutil.rmtree(output / 'workspace', ignore_errors=True)


def http_checks(base, live=False):
    import requests
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    token = os.environ['DJANGO_API_TOKEN']
    checks = []
    session = requests.Session()
    session.trust_env = False
    for _ in range(60):
        try:
            if session.get(base + '/health/', timeout=5).status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(2)
    else:
        raise TimeoutError('La API Docker no arrancó.')
    def request(name, method, path, status=200, protected=False, data=None):
        headers = {'Authorization': 'Bearer ' + token} if protected else {}
        response = session.request(method, base + path, headers=headers, json=data, timeout=300)
        ok = response.status_code == status
        checks.append({'name': name, 'status': response.status_code, 'passed': ok})
        if not ok:
            raise RuntimeError('Contrato HTTP no conforme: ' + name)
        return response
    request('health', 'GET', '/health/')
    request('swagger', 'GET', '/docs/')
    request('openapi', 'GET', '/openapi.json')
    request('missing_token', 'GET', '/categories/', status=401)
    request('categories', 'GET', '/categories/', protected=True)
    if live:
        question = {'pregunta': '¿Qué debo comprobar si no puedo conectarme al Wi-Fi?'}
        search = request('supabase_search', 'POST', '/rag/search/', protected=True, data=question).json()
        if not search.get('pasajes') or any(not p.get('texto') or not p.get('chunk_id') for p in search['pasajes']):
            raise ValueError('La búsqueda real no devolvió pasajes completos.')
        answer = request('groq_query', 'POST', '/rag/query/', protected=True, data=question).json()
        if not answer.get('respuesta_documental') or not answer.get('clasificacion'):
            raise ValueError('Falta respuesta o clasificación en la consulta real.')
        from schemas.request_v1 import SolicitudTI
        from src.rag.citations import validate_response
        SolicitudTI.model_validate(answer['clasificacion'])
        validate_response(answer['respuesta_documental'], {s['id']: s for s in answer['fuentes']})
    return dict(passed=True, live=live, checks=checks)


def compliance(output):
    stages = {n: read_json(output / (n + '.json')) for n in ('prepare', 'unit', 'notebook', 'http') if (output / (n + '.json')).is_file()}
    technical = all(stages.get(n, {}).get('passed', False) for n in ('prepare', 'unit', 'notebook', 'http'))
    required_steps = ['INSTALL', 'DJANGO', 'API_TESTS', 'DOCKER_BUILD', 'DOCKER_START']
    outcomes = {n: os.environ.get('LAB_' + n + '_OUTCOME', 'not_recorded') for n in required_steps}
    technical = technical and all(v == 'success' for v in outcomes.values())
    nb = stages.get('notebook', {})
    human = read_json(ROOT / 'docs/human_review/class09_review_v1.json')
    source = read_json(ROOT / 'notebooks/parcial2.ipynb')
    config = next(c for c in source['cells'] if c['id'] == 'configuracion')
    team = []
    for node in ast.parse(''.join(config['source'])).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'TEAM' for t in node.targets):
            try:
                team = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                team = []
    def reviewed(judgment):
        return (all(isinstance(judgment.get(k), bool) for k in ('correccion', 'fidelidad', 'respaldo', 'utilidad'))
                and all(judgment.get(k) for k in ('revisor', 'fecha', 'justificacion')))
    rows = human.get('rows', [])
    independent = sum(all(reviewed(j) for j in row.get('independent_reviews', []))
                      and len(row.get('independent_reviews', [])) >= 2
                      and len({j.get('revisor') for j in row.get('independent_reviews', [])}) >= 2
                      and reviewed(row.get('adjudication', {})) for row in rows)
    attest_path = ROOT / 'docs/parcial2/cumplimiento_humano.json'
    attest = read_json(attest_path) if attest_path.is_file() else {}
    def attested(name):
        # Declarations belong to named people, never to this automated checker.
        item = attest.get(name, {})
        paths = item.get('evidence', [])
        return bool(item.get('approved') is True and item.get('reviewer') and item.get('date') and paths
                    and all((ROOT / p).resolve().is_relative_to(ROOT)
                            and (ROOT / p).is_file() for p in paths))
    external = bool(nb.get('live') and nb.get('passed') and stages.get('http', {}).get('live') and stages.get('http', {}).get('passed'))
    requirements = [
        ('Groq y Supabase reales desde notebook y API', external, 'measured'),
        ('Nombres del equipo en el notebook', isinstance(team, list) and bool(team) and all(isinstance(n, str) and n.strip() for n in team), 'source'),
        ('Revisión humana completa con doble revisión y adjudicación de al menos tres casos', human.get('status') == 'completed' and bool(rows) and all(reviewed(r.get('human_review', {})) for r in rows) and independent >= 3, 'human_sheet'),
        ('Métricas de respuesta revisadas', attested('answer_metrics'), 'human_declaration'),
        ('Reserva aprobada, congelada y evaluada fuera del workflow', attested('reserve'), 'human_declaration'),
        ('Decisión comparativa final', attested('decision'), 'human_declaration'),
        ('Bitácora y presentación del segundo corte', attested('deliverables'), 'human_declaration'),
        ('Ejecución real en Colab', attested('colab'), 'human_declaration'),
    ]
    pending = [name for name, passed, _ in requirements if not passed]
    complete = bool(technical and not pending)
    result = dict(technical_passed=bool(technical), laboratory_status='evidence_complete' if complete else 'partial',
                  complete_lab=complete, human_review_status=human.get('status'), pending=pending,
                  requirements=[dict(name=n, passed=bool(ok), evidence_type=kind) for n, ok, kind in requirements],
                  external_services_verified=external, step_outcomes=outcomes, stages=stages,
                  scope='Technical reconstruction and evidence completeness; human declarations are not independently verified. No official grading or reserve execution.')
    write_json(output / 'laboratorio.json', result)
    lines = ['# Validación del laboratorio', '',
             '**Reconstrucción técnica:** ' + ('correcta' if technical else 'incompleta o fallida'),
             '', '**Entrega Clase 09:** ' + ('evidencias completas' if complete else 'parcial') + '; no es una calificación oficial.',
             '', '## Comprobaciones', '']
    for name in ('prepare', 'unit', 'notebook', 'http'):
        lines.append('- ' + name + ': ' + ('correcto' if stages.get(name, {}).get('passed') else 'fallido/no ejecutado'))
    lines += ['', '## Pendientes', ''] + ['- ' + value for value in pending]
    lines += ['', 'La matriz cubre presencia de los doce apartados y ejecución técnica; la calidad de las respuestas requiere revisión humana.']
    text = '\n'.join(lines) + '\n'
    (output / 'laboratorio.md').write_text(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write(text)
    return result


def scan_artifacts(output):
    """Never upload an artifact containing a configured credential, including ZIPs."""
    if (ROOT / '.env').is_file():
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
    values = [os.environ[n].encode() for n in (*REQUIRED_SECRETS, 'DJANGO_API_TOKEN', 'DJANGO_SECRET_KEY')
              if os.environ.get(n) and len(os.environ[n]) >= 8]
    def check(data):
        if any(value in data for value in values):
            raise ValueError('Credencial detectada en evidencia; no publicar artifacts.')
        if data.startswith(b'PK\x03\x04'):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for name in archive.namelist():
                    check(archive.read(name))
    for path in output.rglob('*'):
        if path.is_file():
            check(path.read_bytes())
    return dict(passed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'unit', 'notebook', 'http', 'report', 'scan'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    try:
        if args.stage == 'prepare': result = prepare()
        elif args.stage == 'unit': result = unit_checks()
        elif args.stage == 'notebook': result = execute_notebook(output / 'notebook', args.live)
        elif args.stage == 'http': result = http_checks('http://127.0.0.1:8000/api/v1', args.live)
        elif args.stage == 'report':
            result = compliance(output)
            if not result['technical_passed'] or args.require_complete and not result['complete_lab']:
                raise SystemExit(1)
            return
        else: result = scan_artifacts(output)
        write_json(output / (args.stage + '.json'), result)
        if not result.get('passed'):
            raise SystemExit(1)
    except Exception as error:
        write_json(output / (args.stage + '.json'), {'passed': False, 'error_type': type(error).__name__,
                                                        'failed_cell': getattr(error, 'cell_id', None)})
        print('Validación fallida:', args.stage, type(error).__name__)
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()

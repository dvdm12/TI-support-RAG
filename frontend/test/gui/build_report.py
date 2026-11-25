"""Build auditable JSON/CSV/Markdown and a PDF from saved GUI observations.

Requires reportlab. Does not contact the application or any provider.
"""
import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('--run-dir', type=Path, required=True)
args = parser.parse_args()
run = args.run_dir.resolve()
records = json.loads((run / 'observations.json').read_text())
secondary = json.loads((run / 'concurrency-client/observations.json').read_text())
for record in secondary:
    if record.get('screenshot'):
        record['screenshot'] = 'concurrency-client/' + record['screenshot']
all_records = sorted(records + secondary, key=lambda r: r.get('finishedAt', r.get('startedAt', '')))
index = {r['id']: r for r in all_records}
assessment = json.loads((run / 'assessment.json').read_text())
cases = json.loads((ROOT / 'backend/cases/rag_regression.json').read_text())
labels = {'respondida': 'Respuesta documental', 'parcial': 'Respuesta parcial',
          'aclaracion': 'Por aclarar', 'evidencia_insuficiente': 'Evidencia insuficiente'}


def evaluate(case, observed):
    checks = {
        'completed_without_error': bool(observed['reply']) and not observed['error'],
        'expected_documentary_state': any(labels[s] in observed['badges'] for s in case['expected_documentary_states']),
        'single_editor': observed['editors'] == 1,
    }
    if case.get('expected_category'):
        checks['expected_category'] = f"{case['expected_category']} · prioridad" in observed['badges']
    if case.get('expected_human'):
        checks['human_required_visible'] = 'Requiere soporte humano' in observed['badges']
    if case.get('expected_missing_data') is not None:
        checks['missing_data_as_expected'] = bool(observed['missing']) == case['expected_missing_data']
    if case.get('expected_section') and 'Respuesta documental' in observed['badges']:
        checks['expected_source_section'] = any(case['expected_section'] in s for s in observed['sources'])
    return checks


business = []
for case in cases:
    first = index[case['id']]
    initial_checks = evaluate(case, first['observed'])
    retry = index.get(case['id'] + '-R1')
    final = retry or first
    final_checks = evaluate(case, final['observed'])
    business.append({
        'id': case['id'], 'type': case['tipo'], 'question': case['input'],
        'initial_status': 'conforme' if all(initial_checks.values()) else 'fallo',
        'final_status': 'recuperado' if retry and all(final_checks.values()) else ('conforme' if all(final_checks.values()) else 'fallo'),
        'initial_checks': initial_checks, 'final_checks': final_checks,
        'attempts': [case['id']] + ([retry['id']] if retry else []),
        'agent_review': assessment['case_reviews'][case['id']],
        'response': final['observed']['reply'], 'badges': final['observed']['badges'],
        'sources': final['observed']['sources'], 'evidence': [first.get('screenshot'), final.get('screenshot')],
    })

expected_sections = {'S-HW': 'HW-03', 'S-SW': 'SW-03', 'S-RED': 'RED-02', 'S-CTA': 'CTA-03', 'S-SEG': 'SEG-02', 'S-ACS': 'ACS-03'}
searches = []
for identifier in [*expected_sections, 'S-OTR']:
    record = index[identifier]
    observed = record['observed']
    checks = {'three_passages': len(observed['sources']) == 3,
              'full_passages_opened': len(record.get('visiblePassages', [])) == 3,
              'no_error': not observed['error']}
    if identifier in expected_sections:
        checks['expected_section_present'] = any(expected_sections[identifier] in s for s in observed['sources'])
    status = 'parcial' if identifier == 'S-OTR' else ('conforme' if all(checks.values()) else 'fallo')
    searches.append({'id': identifier, 'category': record['category'], 'question': record['question'],
                     'status': status, 'checks': checks, 'sources': observed['sources'],
                     'passages': record.get('visiblePassages', []), 'evidence': record.get('screenshot'),
                     'note': 'Pasajes genéricos; no responden qué datos incluir.' if identifier == 'S-OTR' else 'Incluye la sección esperada; no se interpreta la categoría como filtro estricto.'})

gui = []
for number in range(1, 26):
    identifier = f'UI{number:02d}'
    selected = {'UI09': 'UI09-confirmacion', 'UI21': 'UI21-400'}.get(identifier, identifier)
    record = index[selected]
    checks = dict(record['checks'])
    if identifier == 'UI09':
        checks = {'copy_confirmed_after_wait': checks['confirmed'], 'no_copy_error': not checks['failureMessage']}
    gui.append({'id': identifier, 'observation': selected, 'description': record['description'],
                'status': 'conforme' if all(checks.values()) else 'fallo', 'checks': checks,
                'evidence': record.get('screenshot'), 'notes': record.get('notes', '')})

tested_files = [ROOT / 'frontend/package.json', ROOT / 'frontend/package-lock.json', ROOT / 'frontend/vite.config.js']
tested_files += list((ROOT / 'frontend/src').rglob('*'))
snapshot_path = run / 'source_snapshot.json'
if not snapshot_path.exists():
    snapshot = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(tested_files) if p.is_file()}
    snapshot_path.write_text(json.dumps(snapshot, indent=2))
# Rebuilding an old report must preserve the originally tested source identity.
previous_summary = json.loads((run / 'results.json').read_text()) if (run / 'results.json').exists() else {}
head = previous_summary.get('base_commit') or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
pdf_path = ROOT / 'output/pdf/pruebas-gui-20261027.pdf'
pdf_path.parent.mkdir(parents=True, exist_ok=True)
summary = {
    'method': 'Interacción real por GUI mediante cua_repl; sin HTTP directo, mocks ni React internals.',
    'reviewer': assessment['reviewer'], 'timezone': 'America/Bogota', 'base_commit': head,
    'uncommitted_frontend': True, 'source_snapshot': 'source_snapshot.json',
    'first_observation': all_records[0].get('finishedAt'), 'last_observation': all_records[-1].get('finishedAt'),
    'counts': {'business_cases': len(business), 'business_initial_expected': sum(r['initial_status'] == 'conforme' for r in business),
               'business_recovered': sum(r['final_status'] == 'recuperado' for r in business),
               'search_cases': len(searches), 'search_conforming': sum(r['status'] == 'conforme' for r in searches),
               'search_partial': sum(r['status'] == 'parcial' for r in searches),
               'gui_cases': len(gui), 'gui_conforming': sum(r['status'] == 'conforme' for r in gui),
               'gui_failed': sum(r['status'] == 'fallo' for r in gui),
               'distinct_tests': len(business) + len(searches) + len(gui), 'raw_observations': len(all_records)},
    'business': business, 'searches': searches, 'gui': gui,
    'findings': assessment['findings'], 'coverage_gaps': assessment['coverage_gaps'],
    'pdf': str(pdf_path.relative_to(ROOT)),
}
(run / 'results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
with (run / 'results.csv').open('w', newline='') as stream:
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['id', 'area', 'estado_inicial', 'estado_final', 'descripcion', 'evidencia'])
    for row in business:
        writer.writerow([row['id'], 'soporte', row['initial_status'], row['final_status'], row['agent_review'], '|'.join(filter(None, row['evidence']))])
    for row in searches:
        writer.writerow([row['id'], 'busqueda', row['status'], row['status'], row['note'], row['evidence']])
    for row in gui:
        writer.writerow([row['id'], 'GUI', row['status'], row['status'], row['description'], row['evidence']])

counts = summary['counts']
lines = ['# Pruebas GUI de TI Support', '', 'Fecha: 27 de octubre de 2026, America/Bogota.', '',
         '**Revisión del agente; no revisión humana.** Interacciones sobre la GUI real, sin mocks ni llamadas HTTP directas.', '',
         f"- Soporte: {counts['business_initial_expected']}/13 con estado y categoría esperados al primer intento; 1 fallo transitorio recuperado con un reintento.",
         '- Búsqueda: 6 conformes y 1 con cobertura parcial. Devolver tres pasajes no acredita relevancia suficiente.',
         '- GUI: 24 controles conformes y 1 fallo de teclado móvil.',
         '- 45 pruebas distintas y 48 observaciones, conservando reintento y comprobaciones preliminares.', '',
         '## Hallazgos', '']
for finding in assessment['findings']:
    lines += [f"### {finding['id']} · {finding['priority']} · {finding['title']}", '', finding['detail'], '',
              'Recomendación: ' + finding['recommendation'], '', 'Evidencia: ' + ', '.join(finding['evidence']) + '.', '']
lines += ['## Escenarios de soporte', '', '| Caso | Inicial | Final | Evaluación del agente |', '|---|---|---|---|']
for row in business:
    lines.append(f"| {row['id']} | {row['initial_status']} | {row['final_status']} | {row['agent_review']} |")
lines += ['', '## Controles de interfaz', '', '| Caso | Resultado | Descripción |', '|---|---|---|']
for row in gui:
    lines.append(f"| {row['id']} | {row['status']} | {row['description']} |")
lines += ['', '## Alcance y límites', ''] + ['- ' + text for text in assessment['coverage_gaps']]
lines += ['', '## Archivos', '', '- `results.json`: resultados consolidados, criterios y hallazgos.',
          '- `results.csv`: 45 filas comparables por prueba.', '- `observations.json`: texto visible y resultados originales, sin sobrescribir fallos.',
          '- `concurrency-client/observations.json`: pruebas del segundo cliente gráfico.',
          '- `assessment.json`: valoración explícita del agente.', '- `source_snapshot.json`: huellas SHA-256 del frontend probado.',
          '- `*.png`: capturas de evidencias; cliente secundario en su subcarpeta.',
          '- PDF: `output/pdf/pruebas-gui-20261027.pdf`, desde la raíz del proyecto.', '',
          'No se modificó el comportamiento del producto para corregir los hallazgos. El controlador reutilizable está en `frontend/test/gui/driver.mjs`.', '']
(run / 'REPORT.md').write_text('\n'.join(lines))

# Print report: deliberately separates operational completion from RAG quality.
font_dir = Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('GUI', str(font_dir / 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('GUIBold', str(font_dir / 'DejaVuSans-Bold.ttf')))
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportTitle', fontName='GUIBold', fontSize=24, leading=30, textColor=colors.HexColor('#17242b'), spaceAfter=14))
styles.add(ParagraphStyle(name='Section', fontName='GUIBold', fontSize=15, leading=21, textColor=colors.HexColor('#17242b'), spaceAfter=13))
styles.add(ParagraphStyle(name='CopyGUI', fontName='GUI', fontSize=9, leading=13.2, textColor=colors.HexColor('#35434b'), spaceAfter=9))
styles.add(ParagraphStyle(name='SmallGUI', fontName='GUI', fontSize=7.7, leading=10.6, textColor=colors.HexColor('#35434b'), spaceAfter=0))
styles.add(ParagraphStyle(name='HeadGUI', fontName='GUIBold', fontSize=8.2, leading=11, textColor=colors.white))
styles.add(ParagraphStyle(name='FindingGUI', fontName='GUIBold', fontSize=10.5, leading=15, textColor=colors.HexColor('#17242b'), spaceAfter=6))


def p(text, style='CopyGUI'):
    text = str(text).replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-')
    return Paragraph(escape(text).replace('\n', '<br/>'), styles[style])


def table(headers, rows, widths):
    data = [[p(cell, 'HeadGUI') for cell in headers]]
    data += [[p(cell, 'SmallGUI') for cell in row] for row in rows]
    item = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    item.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#263840')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f1f4f5'), colors.white]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#263840')),
    ]))
    return item


def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor('#d3dce0'))
    canvas.line(38, 34, A4[0] - 38, 34)
    canvas.setFont('GUI', 8)
    canvas.setFillColor(colors.HexColor('#68747a'))
    canvas.drawString(38, 22, 'TI Support | Pruebas GUI | 27 oct 2026 | Revisión del agente')
    canvas.drawRightString(A4[0] - 38, 22, str(doc.page))


story = [p('Pruebas GUI\nTI Support', 'ReportTitle'), p('Ejecución del 27 de octubre de 2026 · America/Bogota'),
         p('45 pruebas de propósito e interfaz', 'Section'),
         p('Se probó el frontend real mediante botones, campos, teclado y referencias. No se usaron mocks, llamadas HTTP directas ni acceso al estado interno de React.'),
         table(['Área', 'Resultado observado'], [
             ['Soporte: 13 escenarios', '12 con estado/categoría esperados al primer intento; 1 fallo transitorio recuperado con un único reintento.'],
             ['Búsqueda: 7 categorías', '6 conformes; 1 con cobertura parcial para una pregunta general.'],
             ['Interfaz: 25 controles', '24 conformes; 1 fallo de teclado del menú móvil.'],
             ['Evidencias', '48 observaciones con capturas, texto visible, reintento y controles preliminares conservados.'],
         ], [145, 374]), Spacer(1, 20), p('Prioridades de corrección', 'Section'),
         table(['ID', 'Nivel', 'Hallazgo'], [[f['id'], f['priority'], f['title']] for f in assessment['findings']], [40, 40, 439]),
         Spacer(1, 17), p('Interpretación: estas cifras describen esta ejecución sobre desarrollo conocido. No son una tasa global de calidad, fidelidad o seguridad del RAG. Las valoraciones son del agente y no sustituyen la revisión humana.'),
         p('Base Git: ' + head[:12] + '. El frontend tiene cambios locales sin commit; source_snapshot.json identifica los archivos probados.', 'SmallGUI'), PageBreak()]

story += [p('Escenarios de soporte', 'Section'), p('Criterios básicos: resultado sin error, estado documental esperado, categoría cuando corresponde, intervención humana y datos faltantes. Se revisó el texto visible por separado.'),
          table(['Caso', 'Primer intento / final', 'Valoración del agente'], [[r['id'], r['initial_status'] + ' / ' + r['final_status'], r['agent_review']] for r in business], [42, 105, 372]),
          Spacer(1, 14), p('E06 conserva la ejecución fallida y el reintento. E03 y E09 cumplen el estado básico, pero tienen hallazgos de presentación. No se evaluaron campos del clasificador que la GUI no muestra.'), PageBreak()]

story += [p('Búsqueda y respaldo documental', 'Section'), p('Se abrieron los tres pasajes en cada búsqueda. La categoría es una preferencia de ranking, no un filtro estricto. No se midieron Precision, Recall ni generalización.'),
          table(['Caso', 'Categoría', 'Resultado', 'Evidencia'], [[r['id'], r['category'], r['status'], r['note']] for r in searches], [55, 70, 70, 324]),
          Spacer(1, 18), p('Ejemplo: falta de cobertura de VPN', 'FindingGUI'),
          p('El sistema se abstuvo de inventar configuración. La captura también documenta el badge interno que debe traducirse.'),
          Image(str(run / 'E09.png'), width=350, height=350 * 663 / 759), Spacer(1, 5), p('Evidencia E09. La captura muestra solo el área visible de la GUI.', 'SmallGUI'), PageBreak()]

story += [p('Controles de interfaz', 'Section'), p('Las observaciones preliminares de copiado y ancho de pantalla no se contabilizan como fallos: se esperó la confirmación asíncrona y se verificaron 400 px CSS reales.'),
          table(['Caso', 'Resultado', 'Control'], [[r['id'], r['status'], r['description']] for r in gui], [43, 70, 406]), PageBreak()]

story += [p('Hallazgos reproducibles', 'Section')]
for finding in assessment['findings']:
    story.append(KeepTogether([p(f"{finding['id']} · {finding['priority']} · {finding['title']}", 'FindingGUI'),
                               p(finding['detail']), p('Acción sugerida: ' + finding['recommendation']),
                               p('Evidencias: ' + ', '.join(finding['evidence']) + '.', 'SmallGUI'), Spacer(1, 14)]))
story.append(PageBreak())
story += [p('Alcance, límites y reproducción', 'Section')]
for gap in assessment['coverage_gaps']:
    story.append(p('- ' + gap))
story += [Spacer(1, 15), p('Reproducir las pruebas', 'FindingGUI'),
          p('1. Arrancar Django y el frontend local con su configuración habitual.\n2. Vincular la pestaña en cua_repl y cargar frontend/test/gui/driver.mjs.\n3. Ejecutar E01-E13 de backend/cases/rag_regression.json. No abrir la reserva.\n4. Repetir los controles de la matriz GUI y las búsquedas de results.json.\n5. Registrar cada intento y conservar los fallos antes de reintentar.'),
          p('Artefactos', 'FindingGUI'),
          p('results.json y results.csv: resultados consolidados. observations.json: observaciones originales. assessment.json: valoraciones del agente. source_snapshot.json: hashes del frontend. Las capturas se guardan junto a los resultados; las del segundo cliente están en concurrency-client/.'),
          p('Este informe se regenera sin proveedores mediante frontend/test/gui/build_report.py --run-dir RUTA_DE_EJECUCION. El producto no se modificó para corregir los defectos encontrados.')]

doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=38, rightMargin=38, topMargin=38, bottomMargin=46,
                        title='Pruebas GUI de TI Support - 27 octubre 2026', author='Codex - evaluación del agente')
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(json.dumps({'counts': counts, 'pdf': str(pdf_path), 'run': str(run)}, ensure_ascii=False))

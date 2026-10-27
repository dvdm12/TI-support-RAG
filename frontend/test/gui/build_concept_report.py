"""Export the independent conceptual GUI battery; no application/provider calls."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('--run-dir', type=Path, required=True)
args = parser.parse_args()
run = args.run_dir.resolve()
plan_bytes = (run / 'test-plan.json').read_bytes()
plan = json.loads(plan_bytes)
assert hashlib.sha256(plan_bytes).hexdigest() == (run / 'test-plan.sha256').read_text().strip()
observations = json.loads((run / 'observations.json').read_text())
assert len(observations) == len(plan['cases']) == 12
index = {r['id']: r for r in observations}
assert all(index[c['id']]['question'] == c['question'] for c in plan['cases'])

assessments = {
    'C01': ('satisfactoria', 'Explica punto de contacto, recepción, clasificación, derivación y seguimiento en lenguaje accesible.'),
    'C02': ('satisfactoria', 'Amplía el alcance más allá de reparación: cuentas, seguridad y clasificación. No afirma ejecutar una acción real.'),
    'C03': ('satisfactoria', 'Relaciona el ticket con registro, prioridades y trazabilidad; explica pérdidas del manejo informal.'),
    'C04': ('abstencion', 'No distingue los conceptos ni da ejemplos. La abstención evita inventar, pero no satisface la pregunta.'),
    'C05': ('parcial', 'Incluye atención y comprobación con el usuario, pero omite registro/prioridad y mezcla cierre definitivo con documentar por qué sigue abierto.'),
    'C06': ('parcial', 'Define transferencia y continuidad, pero presenta actualizar la categoría como obligación al escalar y no explica bien la entrega del contexto.'),
    'C07': ('abstencion', 'No explica impacto ni urgencia. Remite a falta de evidencia y soporte humano sin resolver la comparación conceptual.'),
    'C08': ('abstencion', 'No define SLA ni distingue primera respuesta de resolución. No inventa plazos.'),
    'C09': ('abstencion', 'No diferencia el registro de casos de los artículos de conocimiento reutilizables.'),
    'C10': ('abstencion', 'No explica correlación de contactos ni seguimiento unificado entre canales.'),
    'C11': ('abstencion', 'No distingue la función de mesa de ayuda de una herramienta chatbot ni sus responsabilidades humanas.'),
    'C12': ('parcial', 'Propone verificar resolución y clasificación, pero no desarrolla indicadores de oportunidad, calidad o satisfacción. Repite la ambigüedad entre cerrar y quedar pendiente.'),
}
rows = []
for case in plan['cases']:
    record = index[case['id']]
    observed = record['observed']
    assert not observed['loading']
    status, note = assessments[case['id']]
    rows.append({**case, 'conceptual_assessment': status, 'agent_note': note,
                 'technical_error': bool(observed['error']), 'answer': observed['reply'],
                 'documentary_state_visible': observed['badges'], 'limitation': observed['limitation'],
                 'sources_visible': observed['sources'], 'grounding_assessment': 'no_verificada',
                 'screenshot': record.get('screenshot'), 'pipeline_label': observed['timingLabel']})

counts = dict(Counter(row['conceptual_assessment'] for row in rows))
counts['total'] = len(rows)
counts['technical_errors'] = sum(row['technical_error'] for row in rows)
method = {
    'reviewer': 'Codex, agente; no revisión humana',
    'question_basis': 'Criterios externos y preguntas redactadas antes de observar las respuestas. No se usaron los casos ni manuales existentes para redactarlos.',
    'execution': 'GUI real; una nueva consulta por pregunta. Solo se reutilizó el controlador técnico de interacción.',
    'retrieval': 'El producto conservó su recuperación habitual. Las referencias externas no se incluyeron en prompts ni se incorporaron al corpus.',
    'plan_sha256': hashlib.sha256(plan_bytes).hexdigest(),
    'plan_file_mtime_utc': datetime.fromtimestamp((run / 'test-plan.json').stat().st_mtime, timezone.utc).isoformat(),
    'first_query_utc': observations[0]['startedAt'],
    'independence': 'Batería exploratoria nueva, separada del desarrollo anterior. No es la reserva formal ni prueba de independencia estadística.',
    'grounding': 'Las etiquetas documentales se transcriben de la GUI; no certifican que cada cita sustente cada afirmación. No se reutilizaron los manuales para formar el criterio conceptual.',
    'latency': 'elapsedSeconds incluye coordinación del controlador. No se usó como benchmark ni se compararon tiempos.',
}
result = {'counts': counts, 'method': method, 'sources': plan['sources'], 'cases': rows}
(run / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
with (run / 'results.csv').open('w', newline='') as stream:
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['id', 'tema', 'pregunta', 'criterio_previo', 'valoracion_agente', 'respuesta', 'limitacion', 'observacion', 'evidencia'])
    for row in rows:
        writer.writerow([row['id'], row['topic'], row['question'], row['expected'], row['conceptual_assessment'], row['answer'], row['limitation'], row['agent_note'], row['screenshot']])

lines = ['# Pruebas nuevas: concepto de mesa de ayuda TI', '',
         'Resultado de la revisión del agente: 3 satisfactorias, 3 parciales y 6 abstenciones; 0 errores técnicos visibles.', '',
         'Las preguntas se fijaron antes de ejecutar y sus criterios se basaron en referencias externas. No se usaron los manuales ni casos existentes para redactar esta batería. Se reutilizó únicamente el controlador GUI. El producto consultó su corpus habitual, sin ampliarlo ni recibir las referencias externas.', '',
         'Una abstención documental puede ser prudente y, a la vez, no demostrar el concepto preguntado. Una explicación plausible con citas tampoco acredita por sí sola fidelidad documental.', '',
         '| Caso | Tema | Valoración | Observación del agente |', '|---|---|---|---|']
for row in rows:
    lines.append(f"| {row['id']} | {row['topic']} | {row['conceptual_assessment']} | {row['agent_note']} |")
lines += ['', '## Hallazgos', '',
          '- El sistema explica definición, alcance y valor del ticket con claridad suficiente.',
          '- No desarrolla incidente/solicitud, prioridades, SLA, conocimiento, canales y chatbot en esta ejecución: seis abstenciones.',
          '- La explicación de cierre mezcla resolver y mantener pendiente un caso. La de escalamiento confunde la transferencia con reclasificar obligatoriamente.',
          '- La respuesta de calidad del servicio ofrece comprobaciones útiles, pero no un conjunto suficiente de indicadores.',
          '- Persisten textos internos como OK_EVIDENCIA_INSUFICIENTE y Respuesta dentro de 90 palabras. Son defectos de presentación separados del conocimiento conceptual.', '',
          '## Criterio externo y trazabilidad', '']
for key, value in method.items(): lines.append(f'- **{key}:** {value}')
lines += ['', '## Referencias', '']
for key, value in plan['sources'].items(): lines.append(f'- [{key}]({value})')
lines += ['', '## Archivos', '', '- QUESTIONS.md: las doce preguntas y sus criterios previos.',
          '- test-plan.json y test-plan.sha256: plan fijado antes de la primera consulta.',
          '- observations.json: texto visible original y metadatos de la ejecución.',
          '- results.json y results.csv: valoraciones separadas de lo que el sistema publicó.',
          '- C01.png a C12.png: capturas de las respuestas.',
          '- PDF: output/pdf/concepto-mesa-ayuda-ti-20261027.pdf, desde la raíz del proyecto.', '',
          'Al ser expuesta y revisada, esta batería puede usarse como desarrollo posterior, pero no debe presentarse como reserva independiente. No se cambió el producto para mejorar estos resultados.', '']
(run / 'REPORT.md').write_text('\n'.join(lines))

font_dir = Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('Concept', str(font_dir / 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('ConceptBold', str(font_dir / 'DejaVuSans-Bold.ttf')))
styles = {
    'title': ParagraphStyle('ConceptTitle', fontName='ConceptBold', fontSize=22, leading=29, spaceAfter=16, textColor=colors.HexColor('#17242b')),
    'heading': ParagraphStyle('ConceptHeading', fontName='ConceptBold', fontSize=15, leading=21, spaceAfter=14, textColor=colors.HexColor('#17242b')),
    'body': ParagraphStyle('ConceptBody', fontName='Concept', fontSize=9.3, leading=14, spaceAfter=10, textColor=colors.HexColor('#35434b')),
    'small': ParagraphStyle('ConceptSmall', fontName='Concept', fontSize=8, leading=11.5, textColor=colors.HexColor('#35434b')),
    'th': ParagraphStyle('ConceptTH', fontName='ConceptBold', fontSize=8, leading=12, textColor=colors.white),
}


def paragraph(text, style='body'):
    text = text.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-')
    return Paragraph(escape(text).replace('\n', '<br/>'), styles[style])


def table(headers, data, widths):
    cells = [[paragraph(h, 'th') for h in headers]]
    cells += [[paragraph(str(c), 'small') for c in row] for row in data]
    item = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
    item.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#263840')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f1f4f5'), colors.white]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
    ]))
    return item


def footer(canvas, doc):
    canvas.setFont('Concept', 8)
    canvas.setFillColor(colors.HexColor('#68747a'))
    canvas.drawString(38, 23, 'Mesa de ayuda TI | Batería conceptual nueva | Revisión del agente')
    canvas.drawRightString(A4[0] - 38, 23, str(doc.page))


story = [paragraph('¿Qué es una mesa\nde ayuda TI?', 'title'),
         paragraph('12 preguntas nuevas probadas desde la GUI · 27 octubre 2026'),
         paragraph('Resultado conceptual', 'heading'),
         paragraph('3 respuestas satisfactorias · 3 parciales · 6 abstenciones. No hubo errores técnicos visibles. Las abstenciones no se cuentan como respuestas conceptuales correctas, aunque eviten inventar.'),
         table(['Caso', 'Tema', 'Valoración del agente'], [[r['id'], r['topic'], r['conceptual_assessment']] for r in rows], [45, 235, 239]),
         Spacer(1, 16), paragraph('Cómo se evitó reutilizar el contenido anterior', 'heading'),
         paragraph('Las preguntas y sus criterios se redactaron con referencias externas de IBM y Atlassian antes de observar las respuestas. No se consultaron los casos ni manuales existentes para construir la batería. El SHA-256 del plan se verificó después de ejecutar.'),
         paragraph('Solo se reutilizó el controlador de interacción GUI. El producto mantuvo su recuperación normal: no se agregaron referencias externas al corpus ni se suministraron en los prompts.'), PageBreak()]
for group in [rows[:6], rows[6:]]:
    story += [paragraph('Preguntas y criterios previos', 'heading'),
              table(['Caso', 'Pregunta nueva', 'Qué debía demostrar'], [[r['id'] + '\n' + r['topic'], r['question'], r['expected'] + '\nRef.: ' + ', '.join(r['sources'])] for r in group], [65, 239, 215]),
              Spacer(1, 16), paragraph('Los criterios describen conceptos, no frases exactas. Una respuesta se considera parcial cuando aporta una explicación útil pero omite un elemento sustancial o añade una confusión. Se mantiene separada la utilidad conceptual de la fidelidad de las citas.', 'small'), PageBreak()]
story += [paragraph('Qué revelaron las respuestas', 'heading')]
for text in [
    'Definición, alcance y tickets (C01-C03): explicaciones comprensibles sobre atención, coordinación y trazabilidad.',
    'Ciclo de atención (C05): se presenta cierre definitivo incluso cuando se documenta la razón de permanecer abierto. Esa formulación confunde estados del caso.',
    'Escalamiento (C06): reconoce transferencia y responsable, pero añade que debe actualizarse la categoría. Escalar no exige reclasificar un caso que ya esté bien clasificado.',
    'Valor del servicio (C12): incluye comprobaciones de resolución y clasificación, pero no desarrolla indicadores de oportunidad, calidad o satisfacción suficientes.',
    'Ausencia de explicación (C04, C07-C11): la GUI devuelve falta de evidencia, incluso para preguntas conceptuales. No se observa una explicación de incidente/solicitud, impacto/urgencia, SLA, conocimiento, multicanalidad o chatbot.',
]:
    story.append(paragraph('- ' + text))
story += [paragraph('Interpretación y límites', 'heading'),
          paragraph('Se evaluó utilidad conceptual por el agente, no por un revisor humano. No se certificó el respaldo de cada cita del corpus: las etiquetas Respuesta documental y Validación automática superada son salidas observadas, no evidencia independiente de fidelidad.'),
          paragraph('Esta prueba exploratoria no es la reserva formal, no demuestra generalización y no sustituye una evaluación con personas. El sistema no se ajustó con estas respuestas. Los originales y las doce capturas se conservan en el paquete de evidencias.'),
          paragraph('Referencias externas para los criterios', 'heading')]
for key, url in plan['sources'].items():
    story.append(Paragraph(f'<link href="{escape(url)}" color="#28628a">{escape(key)} - {escape(url.split("/")[2])}</link>', styles['body']))
pdf_path = ROOT / 'output/pdf/concepto-mesa-ayuda-ti-20261027.pdf'
pdf_path.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=38, rightMargin=38, topMargin=38, bottomMargin=44,
                        title='Concepto de mesa de ayuda TI - pruebas nuevas', author='Codex - revisión del agente')
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(json.dumps({'counts': counts, 'pdf': str(pdf_path), 'plan_hash': method['plan_sha256']}, ensure_ascii=False))

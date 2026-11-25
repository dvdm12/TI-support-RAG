"""Export a completed synthetic OCR run as CSV, JSON metrics and a reviewed PDF.

Uses reportlab and Pillow from the bundled document runtime. Does not call APIs.
"""
from __future__ import annotations

import argparse
import csv
from html import escape
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as PDFImage


ROOT = Path(__file__).resolve().parents[2]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def build(directory, output):
    run = json.loads((directory/'results.json').read_text())
    manifest = json.loads((directory/'manifest.json').read_text())
    assert hashlib.sha256((directory/'manifest.json').read_bytes()).hexdigest() == run['plan_sha256']
    for name, metadata in manifest['files'].items():
        assert hashlib.sha256((directory/'fixtures'/name).read_bytes()).hexdigest() == metadata['sha256']
    results = run['results']
    by_id = {r['id']:r for r in results}
    cases = {r['id']:r for r in manifest['cases']}
    # A report needs recorded test execution and a separate, curated review.
    # Never reuse a previous review for a different manifest.
    review = json.loads((directory/'agent_review.json').read_text())
    assert review['plan_sha256'] == run['plan_sha256']
    suites = json.loads((directory/'automated_tests.json').read_text())
    quality = [r for r in results if 'quality' in r]
    regular = [r for r in quality if not r['challenge']]
    challenges = [r for r in quality if r['challenge']]
    metrics = {
        'schema':'synthetic-ocr-validation-v1', 'plan_sha256':run['plan_sha256'],
        'image':run['image'], 'synthetic_files':len(manifest['files']),
        'checks':len(results), 'checks_passed':sum(r['contract_pass'] for r in results),
        'quality_cases':len(quality), 'quality_passed':sum(r['quality']['passed'] for r in quality),
        'regular_quality_cases':len(regular), 'regular_quality_passed':sum(r['quality']['passed'] for r in regular),
        'challenge_quality_cases':len(challenges), 'challenge_quality_passed':sum(r['quality']['passed'] for r in challenges),
        'quality_failures':[r['id'] for r in quality if not r['quality']['passed']],
        'automated_suites':suites['suites'],
        'provider_queries':2, 'remaining_temporaries':by_id['CLEANUP']['remaining_temporaries'],
        'concurrent_statuses':by_id['C-SUMMARY']['statuses'],
        'quality_rule':manifest['quality_rule'],
        'limitations':[
            'Muestra sintética dirigida; no estima exactitud de producción ni sustituye una reserva.',
            'No incluye escritura a mano, fotos reales, cámaras móviles ni idiomas adicionales.',
            'Los errores de lectura de giro y EXIF llegan con presupuesto admisible: este mide longitud, no calidad.',
            'Concurrencia probada con cuatro solicitudes y un contenedor; no es una prueba de carga sostenida.',
            'Timeout y carga interrumpida se verificaron con simulaciones unitarias, sin agotar procesos reales.',
            'La interfaz React actual no tiene selector de imagen ni invoca OCR; pruebas de integración por HTTP.',
            'Una única consulta con instrucciones maliciosas no constituye una evaluación general de seguridad.',
        ],
    }
    assert hashlib.sha256((ROOT/review['reference']['file']).read_bytes()).hexdigest() == review['reference']['sha256']
    (directory/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2))
    fields=['id','fixture','status','code','contract_pass','quality_pass','cer','wer','missing_anchors','ocr_confidence','budget_admissible','duration_seconds','expected_text','actual_text']
    with (directory/'results.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        for r in results:
            q=r.get('quality',{}); body=r.get('response',{})
            writer.writerow({'id':r['id'],'fixture':r.get('fixture',''),'status':r.get('status',''),'code':r.get('code',''),
                'contract_pass':r['contract_pass'],'quality_pass':q.get('passed',''),'cer':q.get('cer',''),'wer':q.get('wer',''),
                'missing_anchors':'; '.join(q.get('missing_anchors',[])),'ocr_confidence':body.get('confianza_ocr',''),
                'budget_admissible':body.get('presupuesto',{}).get('admisible',''),'duration_seconds':r.get('duration_seconds',''),
                'expected_text':cases.get(r['id'],{}).get('truth') or '', 'actual_text':body.get('texto_ocr','')})
    with (directory/'metrics.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['metric','value'])
        for key,value in metrics.items():
            writer.writerow([key,json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else value])

    # Show original pixels, with alpha composited only for this labelled preview.
    sheet=Image.new('RGB',(1400,920),'#f1f4f8'); draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype(FONT,21)
    previews=[('clear.png','I01 - PNG legible'),('dark.png','I05 - Fondo oscuro'),
              ('accents.png','I08 - Acentos y código técnico'),('rotated.png','I11 - Giro de 90 grados'),
              ('transparent-reference.png','I12 - Transparencia sobre blanco (vista)'),('exif-rotated.jpg','I13 - JPEG aplicando EXIF (vista)')]
    for index,(filename,label) in enumerate(previews):
        x=20+(index%2)*690;y=20+(index//2)*300
        draw.text((x,y),label,font=font,fill='#172237')
        with Image.open(directory/'fixtures'/filename) as image:
            preview=ImageOps.exif_transpose(image).convert('RGB')
            preview.thumbnail((660,245))
            sheet.paste(preview,(x,y+36))
    sheet.save(directory/'image-evidence.png')

    pdfmetrics.registerFont(TTFont('DV',FONT))
    pdfmetrics.registerFont(TTFont('DV-Bold','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    styles=getSampleStyleSheet()
    for name in ('Normal','BodyText','Title','Heading1','Heading2'):
        styles[name].fontName='DV'
    styles['Normal'].fontSize=9;styles['Normal'].leading=13
    styles['Title'].fontSize=25;styles['Title'].leading=31;styles['Title'].alignment=0
    styles['Heading1'].fontSize=18;styles['Heading1'].leading=23
    styles['Heading2'].fontSize=12;styles['Heading2'].leading=17
    styles.add(ParagraphStyle('Small',fontName='DV',fontSize=7.5,leading=10))
    styles.add(ParagraphStyle('Tiny',fontName='DV',fontSize=7,leading=9))
    def p(text,style='Normal'):return Paragraph(escape(str(text)).replace('\n','<br/>'),styles[style])
    def table(rows,widths,small=False):
        grid=Table([[p(c,'Tiny' if small else 'Small') for c in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
        grid.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5edf8')),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#9cb4d6')),
            ('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#dce3ed')),
            ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
            ('TOPPADDING',(0,0),(-1,-1),5 if not small else 3),('BOTTOMPADDING',(0,0),(-1,-1),5 if not small else 3),
        ]));return grid
    output.parent.mkdir(parents=True,exist_ok=True)
    story=[]
    def add(text,style='Normal'):
        story.append(p(text,style));story.append(Spacer(1,3*mm))
    add('OCR para soporte TI\nPruebas funcionales y de precisión','Title')
    add('27 de octubre de 2026 | Ejecución local sobre Docker | Revisión del agente','Small')
    add('Resultado: validación correcta; tres limitaciones de lectura','Heading1')
    add('Los 64 controles de contrato y operación pasaron. El OCR reprodujo correctamente 17 de las 20 entradas con texto conocido. Fallaron el giro de 90 grados, la transparencia y la orientación EXIF. No se modificó el OCR para ocultar estos resultados.')
    story.append(table([
        ['Medición','Resultado','Interpretación'],
        ['Controles HTTP y operación','64 / 64','Incluye presupuestos, concurrencia y limpieza; no son 64 lecturas.'],
        ['Calidad sobre texto esperado','17 / 20','15 / 15 casos ordinarios; 2 / 5 casos difíciles.'],
        ['Pruebas automatizadas','566 / 566','506 backend + 54 API + 6 frontend.'],
        ['Consultas reales al RAG','2 / 2 HTTP 200','Revisadas por el agente; no equivalen a revisión humana.'],
        ['Solicitudes simultáneas','1 HTTP 200; 3 HTTP 503','El servicio comunica ocupación sin ejecutar cuatro OCR a la vez.'],
        ['Temporales tras finalizar','0','No quedaron directorios ti-support-ocr-* en /tmp del contenedor.'],
    ],[49*mm,39*mm,88*mm]))
    story.append(Spacer(1,5*mm))
    add('Alcance y reproducibilidad','Heading2')
    add(f'Se crearon {len(manifest["files"])} archivos sintéticos nuevos. Antes del primer envío se guardaron el texto esperado, los criterios, el manifiesto y los SHA256. Motor real: Tesseract spa+eng. Imagen Docker: {run["image"]}.','Small')
    add('No se abrió ni ejecutó la reserva y no se modificó el corpus. La extracción y las consultas RAG se verificaron por HTTP: el frontend actual todavía no ofrece carga de imágenes.','Small')
    story.append(PageBreak())
    add('Precisión: qué se leyó y qué falló','Heading1')
    add('Criterio fijado antes de la ejecución: CER <= 8% y presencia de todos los términos obligatorios. CER mide distancia de edición de caracteres / longitud esperada; WER aplica la misma medida a palabras. Se normalizan Unicode NFC, mayúsculas y espacios; se conservan acentos y códigos. Los cocientes pueden superar el 100% si hay muchas inserciones.','Small')
    rows=[['Caso','Entrada','CER','WER','Lectura']]
    for r in quality:
        q=r['quality'];rows.append([r['id'],r['fixture'],f'{q["cer"]*100:.2f}%',f'{q["wer"]*100:.2f}%','Correcta' if q['passed'] else 'Falla'])
    story.append(table(rows,[17*mm,72*mm,27*mm,27*mm,33*mm],small=True))
    story.append(Spacer(1,4*mm))
    add('Un HTTP 200 y un presupuesto admisible no certifican legibilidad. I11 e I13 devolvieron texto incoherente y perdieron el código 403; I12 devolvió 422 sin texto. La confianza del motor fue 55,58% y 58,12% en las dos lecturas giradas.','Small')
    add('Los límites exactos de 5 MiB, 4.000.000 píxeles y 4096 píxeles de lado se aceptaron; los archivos que exceden cada límite se rechazaron.','Small')
    story.append(PageBreak())
    add('Evidencia visual y causas identificadas','Heading1')
    story.append(PDFImage(str(directory/'image-evidence.png'),width=176*mm,height=115.66*mm))
    story.append(Spacer(1,5*mm))
    add('Transparencia: el preprocesado usa convert("RGB") sin componer el canal alfa. En la prueba de negro sobre transparencia, el resultado pierde el contraste y no se reconoce texto. La vista de arriba compone sobre blanco únicamente para mostrar el contenido.','Small')
    add('Orientación EXIF: el JPEG se ve derecho cuando el visor aplica su metadato, pero el extractor no ejecuta exif_transpose. El OCR procesa píxeles girados.','Small')
    add('Giro de 90 grados: se utiliza PSM 6 y no hay detección o corrección de orientación. La API acepta el texto residual aunque se pierdan los términos esenciales.','Small')
    add('Ajustes recomendados','Heading2')
    add('Aplicar EXIF antes del preprocesado y componer transparencias sobre un fondo definido. Evaluar corrección de giro y una validación de legibilidad antes de enviar OCR al RAG. Conservar siempre una revisión editable del texto. Estas correcciones quedan pendientes; esta ejecución añade pruebas e informes.','Small')
    story.append(PageBreak())
    add('Integración, presupuestos y límites de la prueba','Heading1')
    add('RAG01 - Mensaje de error 403','Heading2')
    add(review['RAG01']['findings'],'Small')
    add('RAG02 - Instrucciones maliciosas dentro de la imagen','Heading2')
    add(review['RAG02']['findings'],'Small')
    add('La revisión se realizó leyendo las respuestas completas guardadas y cotejando las acciones con ACS-03 y ACS-05 del manual de acceso v2. Se registró como revisión del agente, no humana.','Small')
    add('Presupuestos antes de los proveedores','Heading2')
    add('B01 conserva sus 200 palabras, pero devuelve admisible=false: 246 tokens de búsqueda frente al límite de 128. Las peticiones Q01 y Q02 devuelven 422 por presupuesto; Q03 y Q04 rechazan OCR demasiado largo o vacío. Las pruebas unitarias verifican que el rechazo ocurre antes de Supabase/Groq. No se recorta silenciosamente el texto.','Small')
    add('Pruebas automatizadas','Heading2')
    for suite in metrics['automated_suites']:
        add(f'{suite["scope"]}: {suite["passed"]}/{suite["count"]}. {suite["command"]}','Small')
    add('Se añadieron regresiones para el timeout en la segunda fase del OCR y para la liberación del buffer al interrumpir una carga. Los mensajes de cuota y errores presentes en la suite unitaria son simulaciones de prueba; no consultas reales adicionales.','Small')
    add('Límites de estas conclusiones','Heading2')
    for limitation in metrics['limitations']:
        add('- '+limitation,'Small')
    story.append(PageBreak())
    labels={
        'H01':'Salud inicial','P01':'Método GET','P02':'JSON en endpoint multipart','P03':'Multipart mal formado',
        'Q01':'Exceso presupuesto generador','Q02':'Exceso presupuesto búsqueda','Q03':'OCR >8000 caracteres','Q04':'OCR vacío','Q05':'Búsqueda rechaza OCR',
        'C-HEALTH':'Salud durante concurrencia','C-SUMMARY':'Resultado agregado concurrencia','CLEANUP':'Limpieza final',
        'RAG01':'OCR a RAG: acceso 403','RAG02':'OCR a RAG: instrucciones maliciosas',
    }
    for page,start in enumerate(range(0,len(results),29),1):
        if start:story.append(PageBreak())
        add(f'Anexo: matriz completa ({page}/3)','Heading1')
        add('OK significa que el contrato esperado se cumplió. Para la calidad de lectura consultar la tabla de precisión; una respuesta 422 permitida en un caso difícil no cuenta como lectura correcta.','Small')
        rows=[['ID','Entrada / comprobación','HTTP','Contrato','Código / detalle']]
        for r in results[start:start+29]:
            c=cases.get(r['id'],{})
            detail=r.get('code') or ('Calidad: '+('OK' if r['quality']['passed'] else 'FALLA') if 'quality' in r else '')
            if r['id']=='C-SUMMARY':detail=str(r['statuses'])
            if r['id']=='CLEANUP':detail='0 temporales'
            label=r.get('fixture') or labels.get(r['id'],'OCR simultáneo')
            if c.get('auth'):label+=' / auth '+c['auth']
            if c.get('extra_fields'):label+=' / campo '+', '.join(c['extra_fields'])
            if c.get('duplicate_question'):label+=' / pregunta duplicada'
            if c.get('duplicate_file'):label+=' / archivo duplicado'
            if c.get('missing_file'):label+=' / sin imagen'
            if c.get('question') and len(c['question'])>8000:label+=' / pregunta larga'
            if c.get('filename'):label+=' / '+c['filename']
            if c.get('mime')=='text/plain':label+=' / MIME falso'
            rows.append([r['id'],label,r.get('status','-'),'OK' if r['contract_pass'] else 'FALLA',detail])
        story.append(table(rows,[20*mm,70*mm,16*mm,22*mm,48*mm],small=True))
        if start+29>=len(results):
            story.append(Spacer(1,5*mm))
            add('Evidencias: manifest.json / manifest.sha256, results.json, results.csv, metrics.json, metrics.csv, agent_review.json, source_snapshot.json, image-evidence.png y fixtures/.','Small')
            add('Repetir en un directorio nuevo: ../.venv/bin/python -m scripts.validate_ocr_images --output docs/evaluacion/ocr/NUEVA_EJECUCION. La opción --run-rag habilita dos consultas reales; sin ella no se llaman proveedores.','Small')
            add('Manifiesto SHA256: '+run['plan_sha256'],'Small')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#dce3ed'));canvas.line(17*mm,16*mm,193*mm,16*mm)
        canvas.setFont('DV',7);canvas.setFillColor(colors.HexColor('#536078'))
        canvas.drawString(17*mm,11*mm,'TI-support-RAG | OCR sintético | Revisión del agente | 27/10/2026')
        canvas.drawRightString(193*mm,11*mm,str(doc.page))
    SimpleDocTemplate(str(output),pagesize=(210*mm,297*mm),leftMargin=17*mm,rightMargin=17*mm,
                      topMargin=17*mm,bottomMargin=22*mm,title='Pruebas exhaustivas del OCR - TI-support-RAG',author='Codex - revisión del agente').build(story,onFirstPage=footer,onLaterPages=footer)
    print(json.dumps({'pdf':str(output),'metrics':str(directory/'metrics.json'),'checks':metrics['checks'],
                      'quality_passed':metrics['quality_passed'],'quality_cases':metrics['quality_cases']},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.input.resolve(),args.output.resolve())

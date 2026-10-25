"""T7: replay saved semantic Top-10 and current local BM25, without providers."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from src.rag.lexical import rank, STOP
from src.rag.models import Candidate
from src.rag.retrieval import fuse_rankings, select_ranked_candidates

ROOT = Path(__file__).resolve().parents[1]
BASE = 'docs/evaluacion/recuperacion/retrieval_metrics_20261021.json'
IMPROVED = 'docs/evaluacion/recuperacion/coverage_improvements_20261021.json'
ANNOTATIONS = 'cases/rag_evidence.json'
RECORDS = 'data/indexes/sections/records.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classroom_example():
    def candidates(ids):
        return [Candidate(chunk_id=i, content=i, metadata={}, similitud=0) for i in ids]
    rows = fuse_rankings(candidates(['A', 'B', 'C']), candidates(['C', 'A', 'D']),
                         constant=60, semantic_weight=1, lexical_weight=1)
    expected = [('A', .032522), ('C', .032266), ('B', .016129), ('D', .015873)]
    if [(r['chunk_id'], round(r['rrf_score'], 6)) for r in rows] != expected:
        raise ValueError('El ejemplo de la diapositiva 3 no coincide.')
    return rows


def build_report(root=ROOT):
    def read(path):
        return json.loads((root / path).read_text(encoding='utf-8'))
    source, improved, annotations = read(BASE), read(IMPROVED), read(ANNOTATIONS)
    if digest(root / RECORDS) != source['active_index_hashes']['records.json']:
        raise ValueError('Índice distinto del usado en los rankings semánticos.')
    if digest(root / ANNOTATIONS) != source['annotation_validation']['annotation_sha256']:
        raise ValueError('Anotaciones distintas del desarrollo registrado.')
    if digest(root / BASE) != improved['source_sha256']:
        raise ValueError('La mejora no corresponde al informe base.')
    inventory = {r['chunk_id']: Candidate(chunk_id=r['chunk_id'], content=r['text'],
        metadata={k: v for k, v in r.items() if k not in ('chunk_id', 'text')}, similitud=0)
        for r in read(RECORDS)}
    annotated = {c['id']: c for c in annotations['cases']}
    previous = {c['id']: c for c in improved['cases']}
    if len(source['cases']) != 13 or {c['id'] for c in source['cases']} != set(annotated):
        raise ValueError('Se requieren los trece casos de desarrollo, sin reserva.')
    cases = []
    for original in source['cases']:
        case = annotated[original['id']]
        if original['error'] or case['split'] != 'development' or case['question'] != original['question']:
            raise ValueError('Caso inválido o ajeno al desarrollo.')
        semantic = [inventory[r['chunk_id']].model_copy(update={'similitud': r['cosine']})
                    for r in original['semantic_ranking']]
        for candidate in semantic:
            if source['candidate_catalog'][candidate.chunk_id]['text'] != candidate.content:
                raise ValueError('Pasaje semántico distinto del índice registrado.')
        lexical = rank(case['question'], list(inventory.values()), 10)
        selected, trace = select_ranked_candidates(case['question'], semantic, lexical, k=3, category=None)
        expected = previous[case['id']]['variants']['Después: híbrida v2']['selected_ids']
        if trace['selected_ids'] != expected:
            raise ValueError(f"Selección distinta de la híbrida v2 guardada: {case['id']}")
        cases.append(dict(id=case['id'], question=case['question'], split='development',
            retrieval_evaluable=case['retrieval_evaluable'], semantic_origin='saved_real_top_10',
            bm25_origin='recomputed_local_frozen_70_chunks',
            matches_saved_hybrid_v2=True, **trace))
    return dict(schema_version='rrf-traces-v1', status='complete',
        scope='Offline development replay, not a new HTTP/Supabase measurement or independent evaluation.',
        corpus_id=source['corpus_id'], corpus_size=len(inventory),
        sources=[dict(path=p, sha256=digest(root / p)) for p in (BASE, IMPROVED, ANNOTATIONS, RECORDS)],
        code_sha256={p: digest(root / p) for p in ('src/rag/retrieval.py', 'src/rag/lexical.py',
                                                'src/rag/applicability.py', 'scripts/export_rrf_traces.py')},
        protocol=dict(search_depth_per_branch=10, k=3, rrf_constant=60,
            semantic_weight=1, lexical_weight=2, category_boost=False,
            tie_break='chunk_id ascending', applicability='filter full union before Top-3',
            bm25=dict(k1=1.5, b=.75, stopwords=sorted(STOP),
                      implementation='src/rag/lexical.py; Spanish normalization and plural reduction'),
            cosine_note='Saved cosine is not a BM25 score or RRF contribution.',
            limits='Known development cases; behavior cases have no retrieval quality denominator. No generation, no new latency or quality metrics.'),
        classroom=dict(semantic_ranking=['A', 'B', 'C'], bm25_ranking=['C', 'A', 'D'],
                       semantic_weight=1, lexical_weight=1, rrf_constant=60,
                       expected_order=['A', 'C', 'B', 'D'], verified=True, rrf_union=classroom_example()),
        candidate_catalog={ident: {'section': c.metadata['section'], 'document_id': c.metadata['document_id']}
                           for ident, c in inventory.items()},
        cases=cases, provider_calls=0, supabase_writes=0, reserve_executed=False)


def write_pdf(report, path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    styles = getSampleStyleSheet()
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, leading=10)
    def p(text, style=small):
        return Paragraph(escape(str(text)), style)
    def table(rows, widths):
        result = Table([[p(cell) for cell in row] for row in rows], colWidths=widths, repeatRows=1)
        result.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8eef8')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, 0), .6, colors.HexColor('#8899aa')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7fa')]),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
        return result
    story = [p('T7 - Rankings y aportes RRF', styles['Title']), Spacer(1, 14)]
    for text in (
        '13 casos de desarrollo: siete documentales y seis de comportamiento. Reproducción offline de rankings semánticos reales guardados; BM25 recalculado sobre 70 fragmentos congelados.',
        'No se realizaron llamadas a proveedores, escrituras en Supabase ni apertura de reserva. La selección coincide con la híbrida v2 guardada en los trece casos.',
        'Ejemplo de clase: c=60, peso semántico=1 y léxico=1. Una lista ausente aporta cero; posiciones desde uno. El resultado no es una probabilidad.',
    ):
        story.extend([p(text), Spacer(1, 10)])
    rows = [['ID', 'Pos. sem.', 'Pos. BM25', 'Aporte sem.', 'Aporte BM25', 'RRF']]
    for r in report['classroom']['rrf_union']:
        rows.append([r['chunk_id'], r['semantic_rank'] or '-', r['bm25_rank'] or '-',
                     f"{r['semantic_contribution']:.6f}", f"{r['bm25_contribution']:.6f}", f"{r['rrf_score']:.6f}"])
    story.extend([table(rows, [40, 65, 65, 95, 95, 135]), Spacer(1, 16)])
    for text in (
        'Configuración vigente: c=60; peso semántico=1; peso BM25=2; profundidad 10 por rama; Top-3; sin categoría. Se filtra aplicabilidad antes de Top-3. Desempate por chunk_id.',
        'Cada tabla muestra la unión completa. S y B son posiciones semántica y BM25; aportes se calculan como peso/(60+posición). Final indica el puesto seleccionado; "excluido" señala filtro de aplicabilidad.',
        'Los IDs completos, cosenos guardados, parámetros, hashes, rankings, exclusiones y selección están en JSON/CSV. Aquí se muestran sección y últimos ocho caracteres del ID para facilitar lectura.',
        'Las trazas explican selección; no prueban calidad de respuesta ni generalización. Los seis casos de comportamiento se incluyen para inspección, sin denominador de calidad de recuperación.',
    ):
        story.extend([p(text), Spacer(1, 12)])
    for case in report['cases']:
        story.extend([PageBreak(), p(case['id'] + ' - ' + ('Documental' if case['retrieval_evaluable'] else 'Comportamiento'), styles['Heading1']),
                      p(case['question'], styles['Normal']), Spacer(1, 12)])
        rows = [['Candidato (sección / ID)', 'S', 'B', 'Aporte sem.', 'Aporte BM25', 'RRF', 'Final']]
        for r in case['rrf_union']:
            rows.append([report['candidate_catalog'][r['chunk_id']]['section'] + ' / ' + r['chunk_id'][-8:],
                         r['semantic_rank'] or '-', r['bm25_rank'] or '-',
                         f"{r['semantic_contribution']:.6f}", f"{r['bm25_contribution']:.6f}",
                         f"{r['rrf_score']:.6f}", r['selected_rank'] or ('excluido' if not r['applicable'] else '-')])
        story.append(table(rows, [190, 25, 30, 65, 65, 65, 55]))
        for omitted in case['applicability_omitted']:
            story.extend([Spacer(1, 8), p(omitted['chunk_id'] + ': ' + omitted['reason'])])
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.drawString(30, 20, 'TI-support-RAG | T7 | Desarrollo conocido | Reproducción offline')
        canvas.drawRightString(A4[0] - 30, 20, str(doc.page))
        canvas.restoreState()
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=30, rightMargin=30,
                      topMargin=32, bottomMargin=36).build(story, onFirstPage=footer, onLaterPages=footer)


def write_outputs(report, output):
    paths = [output.with_suffix(s) for s in ('.json', '.csv', '.pdf')]
    if any(p.exists() for p in paths):
        raise FileExistsError('Las salidas ya existen; elija otro nombre para conservar evidencias.')
    output.parent.mkdir(parents=True, exist_ok=True)
    paths[0].write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    fields = ['case', 'question', 'retrieval_evaluable', 'chunk_id', 'semantic_rank', 'bm25_rank',
              'semantic_contribution', 'bm25_contribution', 'rrf_score', 'category_boost',
              'selection_score', 'applicable', 'exclusion_reason', 'selected_rank']
    with paths[1].open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for case in report['cases']:
            for row in case['rrf_union']:
                writer.writerow(dict(case=case['id'], question=case['question'],
                                     retrieval_evaluable=case['retrieval_evaluable'], **row))
    write_pdf(report, paths[2])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/evaluacion/recuperacion/rrf_traces_20261025.json')
    args = parser.parse_args()
    if args.output.suffix != '.json':
        raise ValueError('La salida debe terminar en .json.')
    report = build_report()
    write_outputs(report, args.output)
    print(f"T7: {len(report['cases'])}/13 selecciones reproducidas; ejemplo RRF verificado. {args.output}")


if __name__ == '__main__':
    main()

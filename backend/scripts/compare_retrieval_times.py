"""Compare saved A/B stage times and always export JSON, CSV and PDF."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from src.rag.config import ROOT
from src.rag.timing_comparison import compare_timings, STAGES, VARIANTS


def write_outputs(report, output):
    from src.pdf_report import PDFReport
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    with output.with_suffix('.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['case','group','status','variant','total_seconds',
                                               *STAGES,'difference_seconds','relative_change_percent'])
        writer.writeheader()
        for case in report['cases']:
            for name in VARIANTS:
                variant=case['variants'].get(name,{})
                writer.writerow({'case':case['id'],'group':case['group'],'status':case['status'],'variant':name,
                    'total_seconds':variant.get('total_seconds'),**variant.get('stages',{}),
                    'difference_seconds':case['difference_seconds'],'relative_change_percent':case['relative_change_percent']})
    return PDFReport(output.with_suffix('.pdf')).generate_timing_comparison(report,source_json=output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'docs/evaluacion/recuperacion/retrieval_metrics_20261021.json')
    parser.add_argument('--output',type=Path,help='Nombre base JSON; CSV y PDF se crean junto a él.')
    args=parser.parse_args()
    output=args.output or args.input.with_name(args.input.stem+'_times.json')
    if output.suffix.lower()!='.json':
        raise ValueError('La salida base debe tener extensión .json.')
    if output.resolve()==args.input.resolve():
        raise ValueError('La comparación no debe reemplazar las mediciones originales.')
    raw=args.input.read_bytes();source=json.loads(raw)
    report=compare_timings(source)
    report['source']={'filename':args.input.name,'sha256':hashlib.sha256(raw).hexdigest()}
    report['code_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        for name in ('src/rag/timing_comparison.py','scripts/compare_retrieval_times.py','src/pdf_report.py')}
    pdf=write_outputs(report,output)
    print(json.dumps({'status':report['status'],'valid_pairs':report['groups']['all']['valid_pairs'],
        'totals_seconds':{name:report['groups']['all']['variants'][name]['total_seconds'] for name in VARIANTS},
        'paired_difference_seconds':report['groups']['all']['paired_difference_seconds'],
        'pdf':str(pdf)},ensure_ascii=False,indent=2))
    if report['status']!='complete':
        raise SystemExit(1)


if __name__=='__main__':
    main()

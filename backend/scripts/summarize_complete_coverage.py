"""Export complete/incomplete coverage from saved development observations."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from src.rag.config import ROOT
from src.rag.complete_coverage import enrich_saved_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'docs/evaluacion/recuperacion/retrieval_metrics_20261021.json')
    parser.add_argument('--annotations', type=Path, default=ROOT/'cases/rag_evidence.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or args.input.with_name(args.input.stem+'_coverage.json')
    if output.suffix.lower() != '.json' or output.resolve() in {args.input.resolve(), args.annotations.resolve()}:
        raise ValueError('Usa una salida JSON nueva, distinta de las fuentes.')
    raw = args.input.read_bytes()
    annotation_bytes = args.annotations.read_bytes()
    source = json.loads(raw)
    if hashlib.sha256(annotation_bytes).hexdigest() != source['annotation_validation']['annotation_sha256']:
        raise ValueError('Las anotaciones difieren de las utilizadas en el experimento original.')
    report = enrich_saved_report(source, json.loads(annotation_bytes))
    report['complete_coverage_derivation'] = {
        'derived_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_filename': args.input.name, 'source_sha256': hashlib.sha256(raw).hexdigest(),
        'annotations_sha256': hashlib.sha256(annotation_bytes).hexdigest(),
        'provider_calls': 0, 'retrieval_executed': False,
        'definition': 'Complete iff every required unit has at least one evidence ID in the evaluated stage; behavior is null and technical errors are excluded.',
        'code_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
            ('src/rag/complete_coverage.py', 'scripts/summarize_complete_coverage.py',
             'scripts/evaluate_retrieval_metrics.py', 'src/pdf_report.py')}}
    # Uses the existing JSON/CSV/PDF exporter; no model/provider initialization.
    from scripts.evaluate_retrieval_metrics import write_outputs
    pdf = write_outputs(report, output)
    print(json.dumps({name: value['coverage_completeness'] for name, value in report['aggregate'].items()},
                     ensure_ascii=False, indent=2))
    print(f'PDF: {pdf}')
    if report['status'] != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

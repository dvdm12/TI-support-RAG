"""Freeze or verify the Ricoh extraction baseline locally, without overwriting references."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from src.rag.extraction_baseline import (
    check_inputs, check_references, compare, create_baseline, runtime, sha256, write_new_json,
)
from src.rag.external_ingestion import extract_real_document

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ID = 'RICOH-MP4002-USER-GUIDE-EN'
BASELINE = ROOT / 'docs/extractor/baselines/ricoh_extraction_v1.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=BASELINE)
    parser.add_argument('--create', action='store_true', help='Fija una referencia nueva, nunca sobrescribe otra.')
    parser.add_argument('--output', type=Path, help='Informe nuevo de verificación; no reemplaza archivos existentes.')
    args = parser.parse_args()
    if args.create and args.output:
        parser.error('--create no admite --output; la salida es --baseline.')
    manifest = ROOT / 'manuals/manifest.real.json'
    now = datetime.now(timezone.utc)
    if args.create:
        if args.baseline.exists():
            parser.error('La línea base ya existe; no se sobrescribe.')
        result = extract_real_document(manifest, DOCUMENT_ID)
        baseline = create_baseline(ROOT, manifest, DOCUMENT_ID, result,
            created_at_utc=now.isoformat(),
            git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
        write_new_json(args.baseline, baseline)
        print(f'Línea base creada: {args.baseline}')
        return
    output = args.output or ROOT / 'docs/rag_runs/extraction_baseline' / (now.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    if output.resolve() == args.baseline.resolve() or output.exists():
        parser.error('El informe debe ser un archivo nuevo distinto de la línea base.')
    baseline = json.loads(args.baseline.read_text())
    check_inputs(baseline, manifest, DOCUMENT_ID)
    changed_references = check_references(ROOT, baseline)
    result = extract_real_document(manifest, DOCUMENT_ID)
    report = compare(baseline, result)
    report.update(created_at_utc=now.isoformat(), baseline_sha256=sha256(args.baseline.read_bytes()),
        changed_reference_files=changed_references,
        runtime=runtime(), runtime_changed=runtime() != baseline['provenance']['runtime'],
        changed_code_files=[name for name, expected in baseline['provenance']['code_sha256'].items()
                            if not (ROOT / name).is_file() or sha256((ROOT / name).read_bytes()) != expected],
        providers_called=False, human_review_performed=False)
    report['passed'] = report['passed'] and not changed_references
    write_new_json(output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'Informe: {output}')
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

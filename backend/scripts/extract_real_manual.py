"""Extract a registered real manual locally; never builds or uploads an index."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from src.rag.external_ingestion import extract_real_document, review_markdown
from src.rag.extraction_validation import execution_failure_report, require_valid_extraction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('manuals/manifest.real.json'))
    parser.add_argument('--document-id', default='RICOH-MP4002-USER-GUIDE-EN')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    strategy_trace = []
    output = args.output or Path('data/extracted') / args.document_id
    try:
        result = extract_real_document(args.manifest, args.document_id, strategy_trace=strategy_trace)
        validation = require_valid_extraction(result, strategy_trace)
    except Exception as error:
        output.mkdir(parents=True, exist_ok=True)
        failure = execution_failure_report(error, args.document_id)
        name = 'validation_failure_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'
        with (output / name).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(failure, ensure_ascii=False, indent=2) + '\n')
        raise
    blocks = [b for s in result['sections'] for b in s['blocks']]
    tables = [b for b in blocks if b['type'] == 'table']
    output.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    (output / 'extraction.json').write_text(payload, encoding='utf-8')
    (output / 'review.md').write_text(review_markdown(result), encoding='utf-8')
    trace_payload = json.dumps(strategy_trace, ensure_ascii=False, indent=2) + '\n'
    (output / 'strategy_trace.json').write_text(trace_payload, encoding='utf-8')
    validation_payload = json.dumps(validation, ensure_ascii=False, indent=2) + '\n'
    (output / 'validation_report.json').write_text(validation_payload, encoding='utf-8')
    summary = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'document_id': args.document_id,
        'source_sha256': result['document']['sha256'],
        'parser_version': result['parser_version'],
        'pages_total': len(result['pages']),
        'pages_by_status': dict(Counter(p['status'] for p in result['pages'])),
        'sections': len(result['sections']),
        'blocks_by_type': dict(Counter(b['type'] for b in blocks)),
        'table_rows': sum(len(t['rows']) for t in tables),
        'table_continuation_candidates': sum('continuation_candidate_of' in t for t in tables),
        'tables_with_review_flags': [t['id'] for t in tables if t['review_flags']],
        'extraction_sha256': hashlib.sha256(payload.encode()).hexdigest(),
        'output_directory': str(output),
        'embeddings_generated': False,
        'supabase_writes': False,
        'active_index_changed': False,
        'strategy_trace_records': len(strategy_trace),
        'strategy_trace_sha256': hashlib.sha256(trace_payload.encode()).hexdigest(),
        'validation_status': validation['status'],
        'validation_block_counts': validation['block_counts'],
        'validation_report_sha256': hashlib.sha256(validation_payload.encode()).hexdigest(),
        'limitations': result['limitations'],
    }
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

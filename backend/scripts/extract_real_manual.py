"""Extract a registered real manual locally; never builds or uploads an index."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from src.rag.external_ingestion import extract_real_document, review_markdown


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('manuals/manifest.real.json'))
    parser.add_argument('--document-id', default='RICOH-MP4002-USER-GUIDE-EN')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = extract_real_document(args.manifest, args.document_id)
    blocks = [b for s in result['sections'] for b in s['blocks']]
    tables = [b for b in blocks if b['type'] == 'table']
    output = args.output or Path('data/extracted') / args.document_id
    output.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    (output / 'extraction.json').write_text(payload, encoding='utf-8')
    (output / 'review.md').write_text(review_markdown(result), encoding='utf-8')
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
        'limitations': result['limitations'],
    }
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

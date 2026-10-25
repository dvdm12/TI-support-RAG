"""Create a local review-only OCR candidate, never an extraction v1 or index."""
import argparse
from pathlib import Path

from src.rag.extraction_baseline import write_new_json
from src.rag.pdf_ocr_review import review_scan_page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--page', type=int, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--language', default='spa+eng')
    parser.add_argument('--dpi', type=int, default=200)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = review_scan_page(args.pdf, args.page, source_sha256=args.source_sha256,
                              language=args.language, dpi=args.dpi)
    write_new_json(args.output, result)


if __name__ == '__main__':
    main()

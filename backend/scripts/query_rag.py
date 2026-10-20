import argparse
import json
from pathlib import Path
from src.rag.embeddings import SentenceEmbedder
from src.rag.index import load_index
from src.rag.repository import LocalRepository, SupabaseRepository
from src.rag.retrieval import Retriever
from src.rag.pipeline import run_rag_case


def main():
    parser = argparse.ArgumentParser(description='Consultar un índice existente sin recalcular el corpus.')
    parser.add_argument('question')
    parser.add_argument('--index', type=Path, default=Path('data/indexes/sections'))
    parser.add_argument('--repository', choices=['local', 'supabase'], default='supabase')
    parser.add_argument('--mode', choices=['mock', 'groq'], default='groq')
    parser.add_argument('--mock-type', choices=['ambiguo', 'incompleto', 'malicioso', 'fuera_de_alcance'], default='ambiguo')
    parser.add_argument('--image', type=Path)
    parser.add_argument('--ocr-engine', choices=['easyocr', 'tesseract'], default='easyocr')
    parser.add_argument('--output', type=Path, default=Path('docs/rag_runs/latest.json'))
    parser.add_argument('--pdf', type=Path)
    args = parser.parse_args()
    _, _, _, config = load_index(args.index)
    embedder = SentenceEmbedder(config.revision)
    corpus_id, chunks, vectors, config = load_index(args.index, embedder)
    if args.repository == 'local':
        repository = LocalRepository()
        repository.upsert(corpus_id, chunks, vectors, config)
    else:
        repository = SupabaseRepository.connect()
    case = {'id': 'RAG-MANUAL', 'tipo': args.mock_type if args.mode == 'mock' else 'manual', 'input': args.question}
    fixture = {'estado': 'evidencia_insuficiente', 'respuesta': 'Respuesta simulada para verificar el flujo.',
               'citas': [], 'limitacion': 'Este mock no evalúa comprensión ni respaldo semántico.'}
    result = run_rag_case(case, Retriever(repository, embedder, corpus_id, config), mode=args.mode,
                          image_path=args.image, ocr_engine=args.ocr_engine, documentary_fixture=fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'state': result['state'], 'classification': result['classification'],
                      'documentary_output': result['documentary_output'],
                      'semantic_support_review': result['rag']['semantic_support_review']}, ensure_ascii=False, indent=2))
    if args.pdf:
        from src.pdf_report import PDFReport
        report = PDFReport(args.pdf, subtitle='Evidencia RAG documental')
        report.register_test_case(case=case, result=result)
        report.generate()
    if result['state'] in {'ERROR_TECNICO', 'ERROR_FORMATO'}:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
